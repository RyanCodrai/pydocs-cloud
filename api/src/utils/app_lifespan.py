from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel
from src.db.operations import async_engine
from src.settings import settings
from src.utils.logger import logger
from src.utils.npm_sync import lifespans as npm_sync_lifespans


class DatabaseConnectionError(Exception):
    """Raised when unable to establish database connection."""


@asynccontextmanager
async def database() -> AsyncIterator[None]:
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(f'Database tables created successfully for "{settings.POSTGRES_DB}".')
    except Exception as exc:
        error_msg = "Failed to connect to database with settings."
        raise DatabaseConnectionError(error_msg) from exc
    yield
    await async_engine.dispose()
    logger.info("Database connection closed.")


all_lifespans = [
    *npm_sync_lifespans,
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(database())

        for service_lifespan in all_lifespans:
            await stack.enter_async_context(service_lifespan())

        yield
