from sqlmodel.ext.asyncio.session import AsyncSession
from src.routes.v1.packages.schema import PackageInput
from src.routes.v1.packages.service import PackageService
from src.routes.v1.releases.schema import ReleaseInput
from src.routes.v1.releases.service import ReleaseService


class NpmSyncService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.package_service = PackageService(db_session=db_session)
        self.release_service = ReleaseService(db_session=db_session)
        self.db_session = db_session

    async def upsert_packument(self, packument: dict):
        name = packument["name"]
        versions = {
            k: v for k, v in packument.get("time", {}).items()
            if k not in ("created", "modified")
        }
        if not versions:
            return

        # Only process releases newer than what we already have
        cutoff = await self.release_service.retrieve_latest_timestamp("npm", name)
        versions = {k: v for k, v in versions.items() if v > cutoff}
        if not versions:
            return

        project_urls = self._extract_project_urls(packument)
        timestamps = list(versions.values())

        await self.package_service.upsert(PackageInput(
            ecosystem="npm",
            package_name=name,
            description=packument.get("description"),
            home_page=project_urls.get("homepage"),
            project_urls=project_urls,
            first_seen=min(timestamps),
            last_seen=max(timestamps),
        ), commit=False)

        for version, published_at in versions.items():
            await self.release_service.upsert(ReleaseInput(
                ecosystem="npm",
                package_name=name,
                version=version,
                first_seen=published_at,
                last_seen=published_at,
            ), commit=False)

        await self.db_session.commit()

    def _extract_project_urls(self, packument: dict) -> dict[str, str]:
        urls = {}
        for key in ("repository", "homepage", "bugs"):
            value = packument.get(key)
            if isinstance(value, dict):
                value = value.get("url")
            if value:
                urls[key] = value
        return urls
