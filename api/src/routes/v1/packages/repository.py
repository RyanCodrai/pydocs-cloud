from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage
from src.routes.v1.packages.schema import PackageInput


class PackageRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: PackageInput) -> DBPackage:
        package = DBPackage(**data.model_dump())
        self.db_session.add(package)
        await self.db_session.commit()
        await self.db_session.refresh(package)
        return package

    async def retrieve(self, package_id: UUID) -> DBPackage:
        stmt = select(DBPackage).where(DBPackage.id == package_id)
        result = await self.db_session.exec(stmt)
        return result.scalar_one()

    async def retrieve_by_name(self, ecosystem: str, package_name: str) -> DBPackage:
        stmt = select(DBPackage).where(
            DBPackage.ecosystem == ecosystem,
            DBPackage.package_name == package_name,
        )
        result = await self.db_session.exec(stmt)
        return result.scalar_one()

    async def retrieve_by_ecosystem(self, ecosystem: str, limit: int | None = None) -> list[DBPackage]:
        stmt = select(DBPackage).where(DBPackage.ecosystem == ecosystem).order_by(DBPackage.first_seen.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db_session.exec(stmt)
        return list(result.scalars().all())

    async def upsert(self, data: PackageInput) -> DBPackage:
        stmt = (
            insert(DBPackage)
            .values(**data.model_dump())
            .on_conflict_do_update(
                constraint="unique_package",
                set_={
                    "source_code": data.source_code,
                    "source_code_stars": data.source_code_stars,
                    "first_seen": func.least(DBPackage.first_seen, data.first_seen),
                    "last_seen": func.greatest(DBPackage.last_seen, data.last_seen),
                    "pydocs_rank": data.pydocs_rank,
                },
            )
            .returning(DBPackage)
        )

        result = await self.db_session.exec(stmt)
        await self.db_session.commit()
        return result.scalar_one()
