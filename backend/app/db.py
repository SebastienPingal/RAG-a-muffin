from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from prisma import Prisma

db = Prisma()


async def connect_db() -> Prisma:
    await db.connect()
    return db


async def disconnect_db() -> None:
    await db.disconnect()


@asynccontextmanager
async def prisma_session() -> AsyncIterator[Prisma]:
    await connect_db()
    try:
        yield db
    finally:
        await disconnect_db()
