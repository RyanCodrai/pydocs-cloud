from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute, APIWebSocketRoute
from src.routes.health import router as health_router
from src.routes.v1 import router as user_router
from src.settings import settings
from src.utils.app_lifespan import lifespan
from src.utils.logger import logger


def get_application() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT == "LOCAL" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "LOCAL" else None,
    )
    logger.info("FastAPI application initialised successfully.")

    # Add compression middleware to compress larger responses
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Don't compress tiny responses
        # exclude_paths=["/api/video-stream", "/ws"],  # Exclude streaming endpoints
    )

    # Add routers
    for router in [health_router, user_router]:
        app.include_router(router)
        for route in router.routes:
            if isinstance(route, APIRoute):
                logger.info(f"HTTP Route added: {route.path} - {route.methods}")
            elif isinstance(route, APIWebSocketRoute):
                logger.info(f"WebSocket Route added: {route.path}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    return app


application = get_application()
