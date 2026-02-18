from fastapi import APIRouter
from src.settings import settings


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    if settings.SERVICE_TYPE in {"all", "releases"}:
        from src.routes.v1.webhooks.router import router as webhooks_router

        router.include_router(webhooks_router)

    return router


def collect_lifespans() -> list:
    lifespans = []

    if settings.SERVICE_TYPE in {"all", "npm_sync"}:
        from src.routes.v1.npm_sync.router import lifespans as npm_sync_lifespans

        lifespans.extend(npm_sync_lifespans)

    return lifespans


router = create_router()
lifespans = collect_lifespans()
