from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBKvStore
from src.routes.v1.kv_store.repository import KvStoreRepository


class KvStoreService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = KvStoreRepository(db_session=db_session)

    async def retrieve(self, key: str) -> DBKvStore | None:
        return await self.repository.retrieve(key)

    async def upsert(self, key: str, value: str) -> None:
        await self.repository.upsert(key=key, value=value)
