from app.db import db
from .model import Collection, CollectionCreate


async def get_all() -> list[Collection]:
    collections = await db.collection.find_many()
    return [Collection.model_validate(c) for c in collections]

async def get_by_id(collection_id: int) -> Collection | None:
    collection = await db.collection.find_unique(where={"id": collection_id})
    return Collection.model_validate(collection) if collection else None

async def create(collection: CollectionCreate) -> Collection:
    data = collection.model_dump()
    user = await db.user.find_unique(where={"id": data["userId"]})
    if user is None:
        raise ValueError(f"User with id {data['userId']} not found")

    collection = await db.collection.create(
        data={
            "name": data["name"],
            "user": {"connect": {"id": data["userId"]}}
        }
    )
    return Collection.model_validate(collection)
