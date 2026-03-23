import logging
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from prisma.fields import Json
from starlette.concurrency import run_in_threadpool

from app.db import db

from .embedding import OpenAIEmbeddingProvider, embed_document_chunks, embed_query, serialize_pgvector
from .extraction import extract_pdf_content
from .generation import answer_with_context
from .model import CollectionAnswerResponse, CollectionQueryResponse, Document

logger = logging.getLogger(__name__)


def _serialize_chunk_rows(chunks: list[dict]) -> list[dict]:
    # Chunk rows become the retrieval source of truth, so JSON metadata is normalized here.
    return [
        {
            "chunkIndex": chunk["chunkIndex"],
            "text": chunk["text"],
            "sectionTitle": chunk.get("sectionTitle"),
            "pages": Json(chunk["pages"]),
            "blockRefs": Json(chunk["blockRefs"]),
            "tokenCount": chunk["tokenCount"],
        }
        for chunk in chunks
    ]


async def extract_content(file: UploadFile) -> dict:
    await file.seek(0)
    return await run_in_threadpool(extract_pdf_content, file.file)


async def _store_chunk_embeddings(client, document_id: int, chunks: list[dict]) -> None:
    provider = OpenAIEmbeddingProvider()
    embedded_chunks = await embed_document_chunks(document_id, chunks, provider)

    for chunk in embedded_chunks:
        embedding_literal = serialize_pgvector(chunk["embedding"])
        await client.execute_raw(
            f"""
            UPDATE "DocumentChunk"
            SET "embedding" = '{embedding_literal}'
            WHERE "documentId" = {document_id} AND "chunkIndex" = {chunk["chunkIndex"]}
            """,
        )


def _chunk_records_to_embedding_inputs(chunk_records: list[object]) -> list[dict]:
    return [
        {
            "chunkIndex": chunk.chunkIndex,
            "text": chunk.text,
            "sectionTitle": getattr(chunk, "sectionTitle", None),
            "pages": getattr(chunk, "pages", []),
            "blockRefs": getattr(chunk, "blockRefs", []),
            "tokenCount": chunk.tokenCount,
        }
        for chunk in chunk_records
    ]


async def upload_document(file: UploadFile, collection_id: int) -> Document:
    extracted = None
    if file.content_type == "application/pdf":
        extracted = await extract_content(file)
    else:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    document_data = {
        "name": file.filename,
        "content": extracted["content"],
        "collectionId": collection_id,
    }

    if extracted["extractedBlocks"] is not None:
        document_data["extractedBlocks"] = Json(extracted["extractedBlocks"])

    chunk_rows = _serialize_chunk_rows(extracted["chunks"])
    try:
        async with db.tx() as tx:
            document = await tx.document.create(data=document_data)

            if chunk_rows:
                await tx.documentchunk.create_many(
                    data=[{"documentId": document.id, **chunk_row} for chunk_row in chunk_rows]
                )
                await _store_chunk_embeddings(tx, document.id, extracted["chunks"])
    except Exception as exc:
        logger.exception(
            "Document ingestion failed for collection_id=%s filename=%s",
            collection_id,
            file.filename,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    document = await db.document.find_unique(
        where={"id": document.id},
        include={"chunks": True},
    )
    return Document.model_validate(document)


async def backfill_document_embeddings(document_id: int) -> Document:
    document = await db.document.find_unique(
        where={"id": document_id},
        include={"chunks": True},
    )
    if document is None:
        raise ValueError(f"Document with id {document_id} not found")

    async with db.tx() as tx:
        await _store_chunk_embeddings(
            tx,
            document.id,
            _chunk_records_to_embedding_inputs(document.chunks),
        )

    document = await db.document.find_unique(
        where={"id": document.id},
        include={"chunks": True},
    )
    return Document.model_validate(document)


async def get_document_embedding_debug(document_id: int) -> dict:
    document = await db.document.find_unique(where={"id": document_id})
    if document is None:
        raise ValueError(f"Document with id {document_id} not found")

    rows = await db.query_raw(
        f"""
        SELECT
            "id",
            "chunkIndex",
            "tokenCount",
            "sectionTitle",
            "text",
            "embedding" IS NOT NULL AS "hasEmbedding"
        FROM "DocumentChunk"
        WHERE "documentId" = {document_id}
        ORDER BY "chunkIndex"
        """
    )

    chunk_count = len(rows)
    embedded_count = sum(1 for row in rows if row["hasEmbedding"])

    return {
        "documentId": document_id,
        "documentName": document.name,
        "chunkCount": chunk_count,
        "embeddedChunkCount": embedded_count,
        "allChunksEmbedded": chunk_count > 0 and embedded_count == chunk_count,
        "chunks": rows,
    }


async def query_collection_chunks(
    collection_id: int,
    question: str,
    top_k: int = 5,
) -> CollectionQueryResponse:
    collection = await db.collection.find_unique(where={"id": collection_id})
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found")

    normalized_top_k = max(1, min(top_k, 20))
    provider = OpenAIEmbeddingProvider()
    query_vector = await embed_query(question, provider)
    vector_literal = serialize_pgvector(query_vector)

    rows = await db.query_raw(
        f"""
        SELECT
            dc."id" AS "chunkId",
            dc."documentId",
            d."name" AS "documentName",
            dc."chunkIndex",
            dc."sectionTitle",
            dc."text",
            dc."pages",
            dc."tokenCount",
            dc."embedding" <=> '{vector_literal}'::vector AS "distance"
        FROM "DocumentChunk" dc
        INNER JOIN "Document" d ON d."id" = dc."documentId"
        WHERE d."collectionId" = {collection_id}
          AND dc."embedding" IS NOT NULL
        ORDER BY dc."embedding" <=> '{vector_literal}'::vector
        LIMIT {normalized_top_k}
        """
    )

    return CollectionQueryResponse(
        collectionId=collection_id,
        question=question,
        topK=normalized_top_k,
        matches=rows,
    )


async def answer_collection_question(
    collection_id: int,
    question: str,
    top_k: int = 5,
) -> CollectionAnswerResponse:
    retrieval = await query_collection_chunks(
        collection_id=collection_id,
        question=question,
        top_k=top_k,
    )
    matches_payload = [match.model_dump() for match in retrieval.matches]
    answer = await answer_with_context(question, matches_payload)
    response = CollectionAnswerResponse(
        collectionId=retrieval.collectionId,
        question=retrieval.question,
        topK=retrieval.topK,
        answer=answer,
        matches=retrieval.matches,
    )

    await db.collection.update(
        where={"id": collection_id},
        data={
            "lastQuestion": response.question,
            "lastAnswer": response.answer,
            "lastAnswerTopK": response.topK,
            "lastAnswerMatches": Json(matches_payload),
            "lastAnsweredAt": datetime.now(timezone.utc),
        },
    )

    return response
