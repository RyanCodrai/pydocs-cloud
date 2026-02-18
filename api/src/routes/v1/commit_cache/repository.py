from datetime import datetime

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBCommitCache
from src.routes.v1.commit_cache.schema import CommitCacheInput


class CommitCacheRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def retrieve(self, github_url: str, timestamp: datetime) -> DBCommitCache:
        stmt = select(DBCommitCache).where(
            DBCommitCache.github_url == github_url,
            DBCommitCache.timestamp == timestamp,
        )
        result = await self.db_session.exec(stmt)
        return result.scalar_one()

    async def create(self, data: CommitCacheInput) -> DBCommitCache:
        record = DBCommitCache(**data.model_dump())
        self.db_session.add(record)
        await self.db_session.commit()
        await self.db_session.refresh(record)
        return record
