from collections.abc import Iterable

from app.db import db
from .model import Collection, CollectionCreate

_COLLECTION_INCLUDE = {"documents": {"include": {"chunks": True}}}


def _serialize_collection(collection: object) -> Collection:
    payload = {
        "id": collection.id,
        "name": collection.name,
        "userId": collection.userId,
        "documents": getattr(collection, "documents", []),
        "createdAt": collection.createdAt,
        "updatedAt": collection.updatedAt,
    }
    latest_answer = _extract_latest_answer(collection)
    if latest_answer is not None:
        payload["latestAnswer"] = latest_answer

    return Collection.model_validate(payload)


def _extract_latest_answer(collection: object) -> dict | None:
    if not getattr(collection, "lastAnswer", None) or not getattr(collection, "lastQuestion", None):
        return None

    raw_matches = getattr(collection, "lastAnswerMatches", None)
    matches = list(raw_matches) if isinstance(raw_matches, Iterable) and not isinstance(raw_matches, dict) else []

    return {
        "question": collection.lastQuestion,
        "topK": collection.lastAnswerTopK or 5,
        "answer": collection.lastAnswer,
        "matches": matches,
        "answeredAt": getattr(collection, "lastAnsweredAt", None),
    }


async def get_all() -> list[Collection]:
    collections = await db.collection.find_many(include=_COLLECTION_INCLUDE)
    return [_serialize_collection(c) for c in collections]

async def get_by_id(collection_id: int) -> Collection | None:
    collection = await db.collection.find_unique(
        where={"id": collection_id},
        include=_COLLECTION_INCLUDE,
    )
    return _serialize_collection(collection) if collection else None

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
    return _serialize_collection(collection)
