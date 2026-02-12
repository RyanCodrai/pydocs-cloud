import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from urllib.parse import quote

import aiohttp
from src.db.operations import managed_session
from src.routes.v1.kv_store.service import KeyNotFound, KvStoreService
from src.routes.v1.npm_sync.operations import NpmSyncService
from src.routes.v1.packages.service import PackageService
from src.settings import settings

logger = logging.getLogger(__name__)


class NpmChangesStream:
    def __init__(self):
        self.state_key = "npm_changes_last_seq"
        self.http: aiohttp.ClientSession = None
        self.since = str(0)

    async def __aenter__(self):
        self.http = aiohttp.ClientSession()
        await self.restore()
        return self

    async def __aexit__(self, *exc):
        await self.http.close()

    async def save(self):
        async with managed_session() as session:
            await KvStoreService(session).upsert(self.state_key, self.since)

    async def restore(self):
        async with managed_session() as session:
            with suppress(KeyNotFound):
                result = await KvStoreService(session).retrieve(self.state_key)
                self.since = result.value

    def __aiter__(self):
        return self

    async def __anext__(self) -> list[str]:
        async with self.http.get(
            "https://replicate.npmjs.com/registry/_changes",
            params={"since": self.since, "limit": 10000},
            headers={
                "User-Agent": "pydocs-npm-sync/1.0 (registry mirror; +https://github.com/RyanCodrai/pydocs-cloud)",
                "Accept": "application/json",
                "npm-replication-opt-in": "true",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        changes = [r["id"] for r in data.get("results", [])]
        names = [name for name in changes if not name.startswith("_design/")]
        self.since = str(data.get("last_seq"))
        if not names:
            raise StopAsyncIteration
        return names


async def _process_package(http: aiohttp.ClientSession, sem: asyncio.Semaphore, package_name: str):
    try:
        async with (
            sem,
            managed_session() as session,
            http.get(
                f"https://registry.npmjs.org/{quote(package_name, safe='')}",
                headers={
                    "User-Agent": "pydocs-npm-sync/1.0 (registry mirror; +https://github.com/RyanCodrai/pydocs-cloud)",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp,
        ):
            if resp.status == 404:
                return
            resp.raise_for_status()
            packument = await resp.json(content_type=None)
            await NpmSyncService(session).upsert_packument(packument)
    except Exception as e:
        logger.warning(f"Failed to process {package_name}: {e}")


async def _run_sync_loop():
    try:
        async with NpmChangesStream() as stream:
            # Phase 1: Register all package names from changes feed
            logger.info(f"npm sync phase 1: starting from seq {stream.since}")
            async for names in stream:
                async with managed_session() as session:
                    service = PackageService(session)
                    for name in names:
                        await service.register("npm", name, commit=False)
                    await session.commit()
                await stream.save()
                logger.info(f"npm sync phase 1: registered {len(names)} packages, seq now {stream.since}")
            logger.info("npm sync phase 1: caught up with changes feed")

            # Phase 2: Process unprocessed packages (fetch packument + upsert metadata)
            logger.info("npm sync phase 2: processing unprocessed packages")
            sem = asyncio.Semaphore(25)
            while True:
                async with managed_session() as session:
                    names = await PackageService(session).retrieve_unprocessed("npm")
                if not names:
                    break
                async with asyncio.TaskGroup() as tg:
                    for name in names:
                        tg.create_task(_process_package(stream.http, sem, name))
                logger.info(f"npm sync phase 2: processed {len(names)} packages")
            logger.info("npm sync phase 2: complete")
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("npm sync: sync loop crashed")


@asynccontextmanager
async def npm_sync_lifespan():
    logger.info("Starting npm sync background task")
    task = asyncio.create_task(_run_sync_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("npm sync background task stopped")


lifespans = [npm_sync_lifespan] if settings.SERVICE_TYPE in {"all", "npm_sync"} else []
