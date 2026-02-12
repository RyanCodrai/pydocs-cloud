from fastapi import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBKvStore
from src.routes.v1.kv_store.repository import KvStoreRepository


class KeyNotFound(HTTPException):
    def __init__(self, key: str) -> None:
        super().__init__(status_code=404, detail=f"Key '{key}' not found")


class KvStoreService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = KvStoreRepository(db_session=db_session)

    async def retrieve(self, key: str) -> DBKvStore:
        try:
            return await self.repository.retrieve(key)
        except NoResultFound as exc:
            raise KeyNotFound(key) from exc

    async def upsert(self, key: str, value: str) -> None:
        await self.repository.upsert(key=key, value=value)
