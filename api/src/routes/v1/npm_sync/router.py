import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from urllib.parse import quote

import aiohttp
from src.db.operations import managed_session
from src.routes.v1.kv_store.service import KeyNotFound, KvStoreService
from src.routes.v1.npm_sync.operations import NpmSyncService
from src.settings import settings

logger = logging.getLogger(__name__)


class NpmChangesStream:
    def __init__(self):
        self.state_key = "npm_changes_last_seq"
        self.http: aiohttp.ClientSession = None
        self.since = str(0)
        self.sem = asyncio.Semaphore(10)

    async def __aenter__(self):
        self.http = aiohttp.ClientSession()
        await self.restore()
        return self

    async def __aexit__(self, *exc):
        await self.http.close()

    async def save(self, value):
        self.since = value
        async with managed_session() as session:
            await KvStoreService(session).upsert(self.state_key, str(value))

    async def restore(self):
        async with managed_session() as session:
            with suppress(KeyNotFound):
                result = await KvStoreService(session).retrieve(self.state_key)
                self.since = result.value

    async def _fetch_batch(self):
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
        return names, data.get("last_seq")

    async def process_package(self, package_name: str):
        try:
            async with (
                self.sem,
                managed_session() as session,
                self.http.get(
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
                packument = await resp.json()
                await NpmSyncService(session).upsert_packument(packument)
        except Exception as e:
            logger.warning(f"Failed to process {package_name}: {e}")


async def _run_sync_loop():
    try:
        async with NpmChangesStream() as stream:
            logger.info(f"npm sync: starting from seq {stream.since}")
            while True:
                # Phase 1: Get 10k changes
                names, stream_progress_pointer = await stream._fetch_batch()
                if not names:
                    await asyncio.sleep(30)
                    continue
                # Phase 2: Process all changes
                async with asyncio.TaskGroup() as tg:
                    for name in names:
                        tg.create_task(stream.process_package(name))
                # Phase 3: Update stream pointer
                await stream.save(stream_progress_pointer)
            logger.info("npm sync: caught up with changes feed")
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
