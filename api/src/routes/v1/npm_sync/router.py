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
        self.buffer: list[str] = []
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
            await KvStoreService(session).upsert(self.state_key, str(self.since))

    async def restore(self):
        async with managed_session() as session:
            with suppress(KeyNotFound):
                result = await KvStoreService(session).retrieve(self.state_key)
                self.since = result.value

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        # Populate buffer
        if not self.buffer:
            await self._fetch_batch()

        # If buffer could not be populated we've reached the end of the stream
        if not self.buffer:
            raise StopAsyncIteration

        # Yield an item of the stream
        return self.buffer.pop(0)

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
        self.buffer.extend(names)
        await self.save(data.get("last_seq"))

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
            return


async def _run_sync_loop():
    async with NpmChangesStream() as stream:
        async with asyncio.TaskGroup() as tg:
            async for package_name in stream:
                tg.create_task(stream.process_package(package_name))


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
