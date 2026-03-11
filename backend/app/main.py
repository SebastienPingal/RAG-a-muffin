from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.core.config import settings
from app.db import connect_db, disconnect_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await connect_db()
    try:
        yield
    finally:
        await disconnect_db()


app = FastAPI(title="RAG API", lifespan=lifespan)

# CORS (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
