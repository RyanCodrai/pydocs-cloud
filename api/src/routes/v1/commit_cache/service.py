from datetime import datetime

from fastapi import Depends
from sqlalchemy.exc import NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.operations import get_db_session
from src.routes.v1.commit_cache.repository import CommitCacheRepository
from src.routes.v1.commit_cache.schema import CommitCacheInput
from src.utils.github_commits import get_commit_at_timestamp


async def get_commit_cache_service(db_session: AsyncSession = Depends(get_db_session)) -> "CommitCacheService":
    return CommitCacheService(db_session=db_session)


class CommitCacheService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = CommitCacheRepository(db_session=db_session)

    async def get_commit_sha(self, github_url: str, timestamp: datetime, github_token: str) -> str:
        try:
            cached = await self.repository.retrieve(github_url=github_url, timestamp=timestamp)
            return cached.commit_sha
        except NoResultFound:
            commit_sha = await get_commit_at_timestamp(
                github_url=github_url, timestamp=timestamp, github_token=github_token
            )
            await self.repository.create(
                CommitCacheInput(github_url=github_url, timestamp=timestamp, commit_sha=commit_sha)
            )
            return commit_sha
