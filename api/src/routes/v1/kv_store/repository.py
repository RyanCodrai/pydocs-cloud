from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBKvStore


class KvStoreRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def retrieve(self, key: str) -> DBKvStore | None:
        return await self.db_session.get(DBKvStore, key)

    async def upsert(self, key: str, value: str, commit: bool = True) -> None:
        stmt = (
            insert(DBKvStore)
            .values(key=key, value=value, updated_at=datetime.now(timezone.utc))
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value, "updated_at": datetime.now(timezone.utc)},
            )
        )
        await self.db_session.exec(stmt)
        if commit:
            await self.db_session.commit()
