from fastapi import APIRouter
from src.settings import settings


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    if settings.SERVICE_TYPE in {"all", "releases"}:
        from src.routes.v1.lookup.router import router as lookup_router
        from src.routes.v1.webhooks.router import router as webhooks_router

        router.include_router(webhooks_router)
        router.include_router(lookup_router)

    # if settings.SERVICE_TYPE in {"all", "user"}:
    #     from src.routes.v1.users.router import router as user_router
    #     from src.routes.v1.apikeys.router import router as api_key_router
    #     router.include_router(user_router)
    #     router.include_router(api_key_router)

    return router


router = create_router()
