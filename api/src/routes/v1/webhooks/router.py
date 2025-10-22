import logging

from fastapi import APIRouter, Depends
from src.routes.v1.packages.service import PackageService, get_package_service
from src.routes.v1.releases.service import ReleaseService, get_release_service
from src.routes.v1.webhooks.schema import ReleaseWebhookPayload
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()
logger = logging.getLogger(__name__)


@service_tag(ServiceType.RELEASES)
@router.post("/webhooks/releases")
async def process_releases_webhook(
    releases: list[ReleaseWebhookPayload],
    release_service: ReleaseService = Depends(get_release_service),
    package_service: PackageService = Depends(get_package_service),
) -> dict:
    from src.routes.v1.packages.schema import PackageInput
    from src.routes.v1.releases.schema import ReleaseInput

    for release in releases:
        # Upsert release
        await release_service.upsert(
            data=ReleaseInput(
                ecosystem=release.ecosystem,
                package_name=release.name,
                version=release.version,
                first_seen=release.timestamp,
                last_seen=release.timestamp,
            ),
            commit=False,
        )

        # Upsert package with description, home_page, and project_urls
        await package_service.upsert(
            data=PackageInput(
                ecosystem=release.ecosystem,
                package_name=release.name,
                description=release.description,
                home_page=release.home_page,
                project_urls=release.project_urls,
                first_seen=release.timestamp,
                last_seen=release.timestamp,
            ),
            commit=False,
        )

    # Commit all changes at once
    await release_service.repository.db_session.commit()

    return {"status": "success"}
