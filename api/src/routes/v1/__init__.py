from fastapi import APIRouter
from src.settings import settings


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    if settings.SERVICE_TYPE in {"all", "releases"}:
        from src.routes.v1.lookup.router import router as lookup_router
        from src.routes.v1.webhooks.router import router as webhooks_router

        router.include_router(webhooks_router)
        router.include_router(lookup_router)

    return router


router = create_router()
