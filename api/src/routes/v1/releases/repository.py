from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBRelease
from src.routes.v1.releases.schema import ReleaseInput


class ReleaseRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: ReleaseInput, commit: bool = True) -> DBRelease:
        release = DBRelease(**data.model_dump())
        self.db_session.add(release)
        if commit:
            await self.db_session.commit()
            await self.db_session.refresh(release)
        return release

    async def retrieve(self, release_id: UUID) -> DBRelease:
        stmt = select(DBRelease).where(DBRelease.id == release_id)
        result = await self.db_session.exec(stmt)
        return result.scalar_one()

    async def retrieve_by_package(self, ecosystem: str, package_name: str, limit: int | None = None) -> list[DBRelease]:
        stmt = (
            select(DBRelease)
            .where(
                DBRelease.ecosystem == ecosystem,
                DBRelease.package_name == package_name,
            )
            .order_by(DBRelease.first_seen.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db_session.exec(stmt)
        return list(result.scalars().all())

    async def upsert(self, data: ReleaseInput, commit: bool = True) -> DBRelease:
        stmt = (
            insert(DBRelease)
            .values(**data.model_dump(exclude_unset=True))
            .on_conflict_do_update(
                constraint="unique_release",
                set_={
                    "first_seen": func.least(DBRelease.first_seen, data.first_seen),
                    "last_seen": func.greatest(DBRelease.last_seen, data.last_seen),
                },
            )
            .returning(DBRelease)
        )

        result = await self.db_session.exec(stmt)
        if commit:
            await self.db_session.commit()
        return result.scalar_one()
