from fastapi import HTTPException, UploadFile
from prisma.fields import Json
from starlette.concurrency import run_in_threadpool

from app.db import db

from .extraction import extract_pdf_content
from .model import Document


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

    document = await db.document.create(data=document_data)

    chunk_rows = _serialize_chunk_rows(extracted["chunks"])
    if chunk_rows:
        await db.documentchunk.create_many(
            data=[{"documentId": document.id, **chunk_row} for chunk_row in chunk_rows]
        )

    document = await db.document.find_unique(
        where={"id": document.id},
        include={"chunks": True},
    )
    return Document.model_validate(document)
