from fastapi import APIRouter

from .model import Collection, CollectionCreate
from .service import create, get_all, get_by_id

router = APIRouter()

@router.get("", response_model=list[Collection], description="Get all collections")
async def get_all_collections():
  return await get_all()

@router.post("", response_model=Collection, description="Create Collection")
async def create_collection(collection: CollectionCreate):
    return await create(collection=collection)

@router.get("/{collection_id}", response_model=Collection, description="Get collection by id")
async def get_collection_by_id(collection_id: int):
    return await get_by_id(collection_id=collection_id)