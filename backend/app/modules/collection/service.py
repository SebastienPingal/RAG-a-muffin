from app.db import db
from .model import Collection, CollectionCreate


async def get_all() -> list[Collection]:
    collections = await db.collection.find_many()
    return [Collection.model_validate(c) for c in collections]

async def get_by_id(collection_id: int) -> Collection | None:
    collection = await db.collection.find_unique(where={"id": collection_id})
    return Collection.model_validate(collection) if collection else None

async def create(collection: CollectionCreate) -> Collection:
    collection = await db.collection.create(data=collection.model_dump())
    return Collection.model_validate(collection)