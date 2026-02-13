from sqlmodel.ext.asyncio.session import AsyncSession
from src.routes.v1.packages.schema import PackageInput
from src.routes.v1.packages.service import PackageService
from src.routes.v1.releases.schema import ReleaseInput
from src.routes.v1.releases.service import ReleaseService
from src.routes.v1.webhooks.schema import parse_timestamp


class NpmSyncService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.package_service = PackageService(db_session=db_session)
        self.release_service = ReleaseService(db_session=db_session)
        self.db_session = db_session

    async def delete_package(self, name: str):
        await self.release_service.delete_by_ecosystem_and_name("npm", name, commit=False)
        await self.package_service.delete_by_ecosystem_and_name("npm", name, commit=False)
        await self.db_session.commit()

    async def upsert_packument(self, packument: dict, requested_name: str):
        name = packument["name"]
        if name != requested_name:
            await self.delete_package(requested_name)
        time_field = packument.get("time", {})

        # If the package has been unpublished, remove it from our DB
        if "unpublished" in time_field:
            await self.delete_package(name)
            return

        versions = {
            k: parse_timestamp(v)
            for k, v in time_field.items()
            if k not in ("created", "modified") and isinstance(v, str)
        }
        if not versions:
            await self.delete_package(name)
            return

        # Only process releases newer than what we already have
        cutoff = await self.release_service.retrieve_latest_timestamp("npm", name)
        versions = {k: v for k, v in versions.items() if v > cutoff}
        if not versions:
            return

        project_urls = self._extract_project_urls(packument)
        timestamps = list(versions.values())

        await self.package_service.upsert(
            PackageInput(
                ecosystem="npm",
                package_name=name,
                description=self._sanitize(packument.get("readme")),
                home_page=project_urls.get("homepage"),
                project_urls=project_urls,
                first_seen=min(timestamps),
                last_seen=max(timestamps),
            ),
            commit=False,
        )

        for version, published_at in versions.items():
            await self.release_service.upsert(
                ReleaseInput(
                    ecosystem="npm",
                    package_name=name,
                    version=version,
                    first_seen=published_at,
                    last_seen=published_at,
                ),
                commit=False,
            )

        await self.db_session.commit()

    @staticmethod
    def _sanitize(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        return value.replace("\x00", "")

    def _extract_project_urls(self, packument: dict) -> dict[str, str]:
        urls = {}
        for key in ("repository", "homepage", "bugs"):
            value = packument.get(key)
            if isinstance(value, list):
                value = value[0] if value else None
            if isinstance(value, dict):
                value = value.get("url")
            if isinstance(value, str):
                urls[key] = value
        return urls
