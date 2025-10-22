"""Router module for release webhook endpoints.

This module defines the FastAPI router for processing package releases sent from
Cloud Tasks. The endpoint receives batches of releases and processes them without
requiring authentication (internal VPC traffic only).
"""

import logging

from fastapi import APIRouter, Depends
from src.routes.v1.releases.schema import Release, ReleaseInput
from src.routes.v1.releases.service import ReleaseService, get_release_service
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()
logger = logging.getLogger(__name__)


@service_tag(ServiceType.RELEASES)
@router.post("/releases/webhook")
async def process_releases(
    releases: list[Release],
    release_service: ReleaseService = Depends(get_release_service),
) -> dict:
    for release in releases:
        release_input = ReleaseInput.from_release(release)
        await release_service.upsert(data=release_input, commit=False)
    await release_service.repository.db_session.commit()
    return {"status": "success"}
