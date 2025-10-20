from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from src.settings import settings
from src.utils.logger import logger

# SQLAlchemy engine
# SQLAlchemy engine with custom pool settings
async_engine = create_async_engine(
    settings.DATABASE_URL, pool_size=settings.DATABASE_POOL_SIZE, max_overflow=settings.DATABASE_POOL_SIZE_OVERFLOW
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def managed_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            logger.info(f"Database session rollback due to exception: {exc}")
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with managed_session() as session:
        yield session
