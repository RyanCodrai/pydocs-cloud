from fastapi import APIRouter
from src.routes.v1.releases.router import router as releases_router

# from src.routes.v1.apikeys.router import router as api_key_router
# from src.routes.v1.users.router import router as user_router

router = APIRouter(prefix="/api/v1")
router.include_router(releases_router)
# router.include_router(user_router)
# router.include_router(api_key_router)
