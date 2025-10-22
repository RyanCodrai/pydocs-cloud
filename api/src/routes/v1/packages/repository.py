from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage
from src.routes.v1.packages.schema import PackageInput


class PackageRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: PackageInput, commit: bool = True) -> DBPackage:
        package = DBPackage(**data.model_dump())
        self.db_session.add(package)
        if commit:
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

    async def upsert(self, data: PackageInput, commit: bool = True) -> DBPackage:
        # Build the update set dynamically, excluding unset fields and unique keys
        update_dict = data.model_dump(exclude_unset=True, exclude={"ecosystem", "package_name"})

        # Always update first_seen and last_seen with min/max logic
        update_dict["first_seen"] = func.least(DBPackage.first_seen, data.first_seen)
        update_dict["last_seen"] = func.greatest(DBPackage.last_seen, data.last_seen)

        stmt = (
            insert(DBPackage)
            .values(**data.model_dump())
            .on_conflict_do_update(
                constraint="unique_package",
                set_=update_dict,
            )
            .returning(DBPackage)
        )

        result = await self.db_session.exec(stmt)
        if commit:
            await self.db_session.commit()
        return result.scalar_one()
