from collections.abc import Sequence
from typing import Protocol

from openai import AsyncOpenAI

from app.core.config import settings


class EmbeddingProvider(Protocol):
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        ...


def _normalize_embedding_text(text: str) -> str:
    return " ".join(text.split()).strip()


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_api_key = api_key or settings.OPENAI_API_KEY
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY is required to generate embeddings")

        self._client = AsyncOpenAI(api_key=resolved_api_key)
        self._model = model or settings.OPENAI_EMBEDDING_MODEL
        self._dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        normalized_inputs = [_normalize_embedding_text(text) for text in texts]
        if not normalized_inputs:
            return []
        if any(not text for text in normalized_inputs):
            raise ValueError("Embedding inputs must be non-empty")

        response = await self._client.embeddings.create(
            model=self._model,
            input=normalized_inputs,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]


def build_chunk_embedding_input(chunk: dict) -> str:
    text = _normalize_embedding_text(chunk.get("text", ""))
    section_title = _normalize_embedding_text(chunk.get("sectionTitle", "") or "")

    # Repeating the section title in the embedding input makes short chunks less ambiguous.
    if section_title and not text.lower().startswith(section_title.lower()):
        return f"{section_title}\n\n{text}".strip()

    return text


def build_query_embedding_input(question: str) -> str:
    return _normalize_embedding_text(question)


def prepare_chunk_embedding_payloads(document_id: int, chunks: Sequence[dict]) -> list[dict]:
    return [
        {
            "documentId": document_id,
            "chunkIndex": chunk["chunkIndex"],
            "text": build_chunk_embedding_input(chunk),
            "sectionTitle": chunk.get("sectionTitle"),
            "pages": chunk.get("pages", []),
        }
        for chunk in chunks
    ]


async def embed_document_chunks(
    document_id: int,
    chunks: Sequence[dict],
    provider: EmbeddingProvider,
) -> list[dict]:
    payloads = prepare_chunk_embedding_payloads(document_id, chunks)
    if not payloads:
        return []

    embeddings = await provider.embed_texts([payload["text"] for payload in payloads])
    if len(embeddings) != len(payloads):
        raise ValueError("Embedding provider returned an unexpected number of vectors")

    return [
        {
            **payload,
            "embedding": embedding,
        }
        for payload, embedding in zip(payloads, embeddings, strict=True)
    ]


async def embed_query(question: str, provider: EmbeddingProvider) -> list[float]:
    embedding_inputs = [build_query_embedding_input(question)]
    embeddings = await provider.embed_texts(embedding_inputs)
    if len(embeddings) != 1:
        raise ValueError("Embedding provider returned an unexpected number of vectors")
    return embeddings[0]


def serialize_pgvector(vector: Sequence[float]) -> str:
    if not vector:
        raise ValueError("Embedding vectors must be non-empty")

    return "[" + ",".join(f"{value:.12g}" for value in vector) + "]"
