from fastapi import APIRouter
from src.settings import settings


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    if settings.SERVICE_TYPE in {"all", "releases"}:
        from src.routes.v1.lookup.router import router as lookup_router
        from src.routes.v1.webhooks.router import router as webhooks_router

        router.include_router(webhooks_router)
        router.include_router(lookup_router)

    if settings.SERVICE_TYPE in {"all", "user"}:
        from src.routes.v1.apikeys.router import router as apikeys_router
        from src.routes.v1.users.router import router as users_router

        router.include_router(users_router)
        router.include_router(apikeys_router)

    return router


def collect_lifespans() -> list:
    lifespans = []

    if settings.SERVICE_TYPE in {"all", "npm_sync"}:
        from src.routes.v1.npm_sync.router import lifespans as npm_sync_lifespans

        lifespans.extend(npm_sync_lifespans)

    return lifespans


router = create_router()
lifespans = collect_lifespans()
