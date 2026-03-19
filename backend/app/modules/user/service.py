from app.db import db
from .model import User, UserCreate


async def get_all() -> list[User]:
    users = await db.user.find_many()
    return [User.model_validate(u) for u in users]


async def get_by_id(user_id: int) -> User | None:
    user = await db.user.find_unique(where={"id": user_id})
    return User.model_validate(user) if user else None


async def get_by_email(email: str) -> User | None:
    user = await db.user.find_unique(where={"email": email})
    return User.model_validate(user) if user else None


async def get_by_google_id(google_id: str) -> User | None:
    user = await db.user.find_unique(where={"googleId": google_id})
    return User.model_validate(user) if user else None


async def get_or_create_by_google(
    *,
    google_id: str,
    email: str,
    name: str | None = None,
) -> User:
    user = await db.user.upsert(
        where={"googleId": google_id},
        data={"update": {"email": email, "name": name}},
        create={"googleId": google_id, "email": email, "name": name},
    )
    return User.model_validate(user)


async def create(user: UserCreate) -> User:
    user = await db.user.create(data=user.model_dump())
    return User.model_validate(user)


async def update(user_id: int, *, name: str | None = None) -> User | None:
    data = {k: v for k, v in (("name", name),) if v is not None}
    if not data:
        return await get_by_id(user_id)
    user = await db.user.update(where={"id": user_id}, data=data)
    return User.model_validate(user)
