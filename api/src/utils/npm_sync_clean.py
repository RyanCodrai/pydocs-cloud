"""npm Registry Sync Service"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiohttp
from sqlalchemy.dialects.postgresql import insert
from src.db.models import DBSyncState
from src.db.operations import managed_session
from src.settings import settings

logger = logging.getLogger(__name__)

NPM_REPLICATE_URL = "https://replicate.npmjs.com/registry"
NPM_REGISTRY_URL = "https://registry.npmjs.org"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
CHANGES_PAGE_SIZE = 10_000
STATE_KEY = "npm_changes_last_seq"

_BASE_HEADERS = {
    "User-Agent": "pydocs-npm-sync/1.0 (registry mirror; +https://github.com/RyanCodrai/pydocs-cloud)",
    "Accept": "application/json",
}


def _build_headers() -> tuple[dict, dict]:
    replicate = {**_BASE_HEADERS, "npm-replication-opt-in": "true"}
    registry = {**_BASE_HEADERS}
    if settings.NPM_TOKEN:
        registry["Authorization"] = f"Bearer {settings.NPM_TOKEN}"
    return replicate, registry


REPLICATE_HEADERS, REGISTRY_HEADERS = _build_headers()


class NpmChangesStream:
    """Async iterator over changed package names from the npm _changes feed.

    Manages cursor persistence and internal buffering. Fetches a new batch
    when the buffer drops below CHANGES_PAGE_SIZE.

    Usage:
        async with NpmChangesStream(http_session) as changes:
            async for package_name in changes:
                ...
    """

    def __init__(self, http_session: aiohttp.ClientSession):
        self._http_session = http_session
        self._since = "0"
        self._buffer: list[str] = []

    async def __aenter__(self):
        async with managed_session() as session:
            result = await session.get(DBSyncState, STATE_KEY)
            self._since = result.value if result else "0"
        logger.info(f"npm sync: starting from seq {self._since}")
        return self

    async def __aexit__(self, *exc):
        await self._save_cursor()

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if not self._buffer:
            await self._fetch_batch()

        if not self._buffer:
            raise StopAsyncIteration

        return self._buffer.pop(0)

    async def _fetch_batch(self):
        url = f"{NPM_REPLICATE_URL}/_changes"
        params = {"since": self._since, "limit": CHANGES_PAGE_SIZE}

        async with self._http_session.get(
            url, params=params, headers=REPLICATE_HEADERS, timeout=REQUEST_TIMEOUT
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        results = data.get("results", [])
        self._since = data.get("last_seq", self._since)

        if results:
            names = list({r["id"] for r in results if not r["id"].startswith("_design/")})
            self._buffer.extend(names)
            logger.info(f"npm sync: fetched {len(names)} packages (seq {self._since})")

        await self._save_cursor()

    async def _save_cursor(self):
        async with managed_session() as session:
            stmt = (
                insert(DBSyncState)
                .values(key=STATE_KEY, value=str(self._since), updated_at=datetime.now(timezone.utc))
                .on_conflict_do_update(
                    index_elements=["key"],
                    set_={"value": str(self._since), "updated_at": datetime.now(timezone.utc)},
                )
            )
            await session.exec(stmt)
            await session.commit()


async def fetch_packument(http_session: aiohttp.ClientSession, package_name: str) -> dict | None:
    """Fetch the packument for a single npm package. Retries on 429."""
    encoded_name = package_name.replace("/", "%2f")
    url = f"{NPM_REGISTRY_URL}/{encoded_name}"

    for attempt in range(4):
        try:
            async with http_session.get(url, headers=REGISTRY_HEADERS, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 404:
                    return None
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch packument for {package_name}: {e}")
            return None

    return None


async def process_change(http_session: aiohttp.ClientSession, package_name: str):
    """Fetch a packument and upsert its data into the database."""
    packument = await fetch_packument(http_session, package_name)
    if not packument:
        return

    # TODO: upsert releases and package into DB
    # async with managed_session() as session:
    #     await upsert_packument(session, packument)
    #     await session.commit()


async def _run_sync_loop():
    async with aiohttp.ClientSession() as http_session:
        async with NpmChangesStream(http_session) as changes:
            async for package_name in changes:
                try:
                    await process_change(http_session, package_name)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"npm sync: error processing {package_name}: {e}", exc_info=True)


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


lifespans = [npm_sync_lifespan]
