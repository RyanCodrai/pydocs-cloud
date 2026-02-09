import asyncio
import signal
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel
from src.db.operations import async_engine
from src.settings import settings
from src.utils.logger import logger
from src.utils.service_tag import ServiceType

# Store the fastapi signal handler before ray replaces it
fastapi_signal_handler = signal.getsignal(signal.SIGTERM)


class DatabaseConnectionError(Exception):
    """Raised when unable to establish database connection."""


# class GracefulShutdownHandler:
#     def __init__(self, app: FastAPI, original_handler: Callable[[int, Any], Any]) -> None:
#         self.app = app
#         self.original_handler = original_handler

#     async def _perform_graceful_shutdown(self, signum: int, frame: Any) -> None:
#         logger.info(f"Intercepted termination signal {signum}. Initiating graceful shutdown.")
#         await GlobalWebSocketSessionManager.wait_for_all_closed(timeout=settings.AGENT_SESSION_GRACE_PERIOD)
#         await BackgroundTaskManager.wait_for_all(timeout=settings.AGENT_SESSION_GRACE_PERIOD)
#         logger.info("Graceful shutdown completed.")
#         self.original_handler(signum, frame)

#     def _initiate_graceful_shutdown(self, signum: int, frame: Any) -> None:
#         asyncio.create_task(self._perform_graceful_shutdown(signum, frame))

#     def setup_graceful_shutdown(self) -> None:
#         loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
#         loop.add_signal_handler(signal.SIGTERM, lambda: self._initiate_graceful_shutdown(signal.SIGTERM, None))
#         logger.info("Graceful shutdown handler set up successfully.")


@asynccontextmanager
async def database() -> AsyncIterator[None]:
    # Initialisation phase
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(f'Database tables created successfully for "{settings.POSTGRES_DB}".')
    except Exception as exc:
        error_msg = "Failed to connect to database with settings."
        raise DatabaseConnectionError(error_msg) from exc
    yield

    # Cleanup phase
    await async_engine.dispose()
    logger.info("Database connection closed.")


# Collect lifespans from all service modules.
# Each module exports `lifespans` as a list of (ServiceType, coroutine_factory) tuples.
from src.utils.npm_sync import lifespans as npm_sync_lifespans

all_lifespans = [
    *npm_sync_lifespans,
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stack = AsyncExitStack()
    await stack.enter_async_context(database())

    # Start lifespans matching the current SERVICE_TYPE
    running_tasks = []
    for service_type, task_fn in all_lifespans:
        if settings.SERVICE_TYPE in (service_type, ServiceType.ALL):
            logger.info(f"Starting background task: {task_fn.__name__}")
            running_tasks.append(asyncio.create_task(task_fn()))

    async with stack:
        yield

    # Cancel all background tasks on shutdown
    for task in running_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    if running_tasks:
        logger.info(f"Stopped {len(running_tasks)} background task(s)")
