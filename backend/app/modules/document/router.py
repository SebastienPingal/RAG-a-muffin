from fastapi import APIRouter, HTTPException

from .service import get_document_embedding_debug

router = APIRouter()


@router.get("/{document_id}/debug/embeddings", description="Debug chunk embedding storage for a document")
async def debug_document_embeddings(document_id: int):
    try:
        return await get_document_embedding_debug(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
