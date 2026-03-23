from fastapi import APIRouter, File, HTTPException, UploadFile

from .model import Collection, CollectionCreate
from .service import create, get_all, get_by_id
from app.modules.document.model import CollectionQueryRequest, CollectionQueryResponse
from app.modules.document.service import (
    query_collection_chunks,
    upload_document as upload_document_service,
)

router = APIRouter()

@router.get("", response_model=list[Collection], description="Get all collections")
async def get_all_collections():
  return await get_all()

@router.post("", response_model=Collection, description="Create Collection")
async def create_collection(collection: CollectionCreate):
    try:
        return await create(collection=collection)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/{collection_id}", response_model=Collection, description="Get collection by id")
async def get_collection_by_id(collection_id: int):
    try:
        return await get_by_id(collection_id=collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/{collection_id}/document/")
async def upload_collection_document(collection_id: int, file: UploadFile = File(...)):
  try:
    return await upload_document_service(file, collection_id)
  except ValueError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{collection_id}/ask", response_model=CollectionQueryResponse)
async def ask_collection(collection_id: int, payload: CollectionQueryRequest):
    try:
        return await query_collection_chunks(
            collection_id=collection_id,
            question=payload.question,
            top_k=payload.topK,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
