from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.routes.health import router as health_router
from src.routes.v1 import router as v1_router
from src.settings import settings
from src.utils.app_lifespan import lifespan
from src.utils.logger import logger


def get_application() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT == "LOCAL" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "LOCAL" else None,
    )
    logger.info(f"FastAPI application initialising for SERVICE_TYPE={settings.SERVICE_TYPE}")

    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,
    )

    app.include_router(health_router)
    app.include_router(v1_router)

    logger.info(
        f"FastAPI application initialised with {len(app.routes)} routes for SERVICE_TYPE={settings.SERVICE_TYPE}"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    return app


application = get_application()
