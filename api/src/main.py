from itertools import chain

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute, APIWebSocketRoute
from src.routes.health import router as health_router
from src.routes.v1 import router as user_router
from src.settings import settings
from src.utils.app_lifespan import lifespan
from src.utils.logger import logger
from src.utils.service_tag import ServiceType


def get_application() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT == "LOCAL" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "LOCAL" else None,
    )
    logger.info(f"FastAPI application initialising for SERVICE_TYPE={settings.SERVICE_TYPE}")

    # Add compression middleware to compress larger responses
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Don't compress tiny responses
    )

    # Collect all routes from all routers
    routers = [health_router, user_router]
    routes = list(chain.from_iterable(router.routes for router in routers))

    # Validate that all routes have service type tags
    for route in routes:
        if hasattr(route.endpoint, "services"):
            continue
        raise ValueError(f"Route {route.path} has no service type tags. Add @service_tag() decorator.")

    # Filter routes based on SERVICE_TYPE
    filtered_routes = []
    for route in routes:
        # If the service type is all, include all routes
        if settings.SERVICE_TYPE == ServiceType.ALL:
            filtered_routes.append(route)
            continue

        # If the service type is not all, include only routes with the correct service type tag
        if settings.SERVICE_TYPE in route.endpoint.services:
            filtered_routes.append(route)
            continue

    # Add filtered routes to the app
    app.include_router(APIRouter(routes=filtered_routes))

    # Log the addition of each route for this service type
    for route in filtered_routes:
        if isinstance(route, APIRoute):
            logger.info(f"HTTP Route added: {route.path} - {route.methods}")
        elif isinstance(route, APIWebSocketRoute):
            logger.info(f"WebSocket Route added: {route.path}")

    logger.info(f"FastAPI application initialised with {len(filtered_routes)} routes for SERVICE_TYPE={settings.SERVICE_TYPE}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    return app


application = get_application()
