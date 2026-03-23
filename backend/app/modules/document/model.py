from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    documentId: int | None = None
    chunkIndex: int
    text: str
    sectionTitle: str | None = None
    pages: list[int]
    blockRefs: list[dict[str, Any]]
    tokenCount: int
    embedding: list[float] | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    extractedBlocks: list[dict[str, Any]] | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    collectionId: int
    createdAt: datetime
    updatedAt: datetime


class DocumentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    content: str
    extractedBlocks: list[dict[str, Any]] | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
    collectionId: int
