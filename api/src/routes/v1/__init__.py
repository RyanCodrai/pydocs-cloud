from fastapi import APIRouter
from src.settings import settings

router = APIRouter(prefix="/api/v1")

if settings.SERVICE_TYPE in ("releases", "all"):
    from src.routes.v1.lookup.router import router as lookup_router
    from src.routes.v1.webhooks.router import router as webhooks_router

    router.include_router(webhooks_router)
    router.include_router(lookup_router)

# User routes - uncomment when queries service is implemented
# if settings.SERVICE_TYPE in ("user", "all"):
#     from src.routes.v1.users.router import router as user_router
#     from src.routes.v1.apikeys.router import router as api_key_router
#     router.include_router(user_router)
#     router.include_router(api_key_router)
