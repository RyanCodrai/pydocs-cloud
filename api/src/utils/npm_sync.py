"""
npm Registry Sync Service

A continuously-running background service that walks the npm registry's CouchDB
_changes feed to discover new/updated packages, fetches their packuments, and
upserts release and package data directly into the database.

The _changes feed is a sequential log of every modification to every package
in the npm registry. Each response includes a `last_seq` cursor that becomes
the `since` parameter for the next request, forming a chain through all changes.

This service runs as an asyncio background task within a FastAPI application
deployed with SERVICE_TYPE=npm_sync.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import aiohttp
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBPackage, DBRelease, DBSyncState
from src.db.operations import managed_session
from src.settings import settings

logger = logging.getLogger(__name__)

NPM_REPLICATE_URL = "https://replicate.npmjs.com/registry"
NPM_REGISTRY_URL = "https://registry.npmjs.org"

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
STATE_KEY = "npm_changes_last_seq"
# Maximum allowed by the _changes API
CHANGES_PAGE_SIZE = 10_000

# Headers required for the npm replication API (post-2025 migration)
# and to avoid Cloudflare bot detection on registry endpoints.
REPLICATE_HEADERS = {
    "npm-replication-opt-in": "true",
    "User-Agent": "pydocs-npm-sync/1.0 (registry mirror; +https://github.com/RyanCodrai/pydocs-cloud)",
    "Accept": "application/json",
}
REGISTRY_HEADERS = {
    "User-Agent": "pydocs-npm-sync/1.0 (registry mirror; +https://github.com/RyanCodrai/pydocs-cloud)",
    "Accept": "application/json",
}


async def load_last_seq(session: AsyncSession) -> str:
    """Load the last processed sequence number from the database."""
    result = await session.get(DBSyncState, STATE_KEY)
    if result:
        return result.value
    return "0"


async def save_last_seq(session: AsyncSession, last_seq: str):
    """Persist the last processed sequence number to the database."""
    stmt = (
        insert(DBSyncState)
        .values(key=STATE_KEY, value=str(last_seq), updated_at=datetime.now(timezone.utc))
        .on_conflict_do_update(
            index_elements=["key"],
            set_={"value": str(last_seq), "updated_at": datetime.now(timezone.utc)},
        )
    )
    await session.exec(stmt)
    await session.commit()


async def fetch_changes(http_session: aiohttp.ClientSession, since: str) -> dict:
    """
    Fetch a batch of changes from the npm registry _changes feed.

    Each response includes `last_seq` which becomes the `since` cursor
    for the next request — this is the chain traversal.
    """
    url = f"{NPM_REPLICATE_URL}/_changes"
    params = {"since": since, "limit": CHANGES_PAGE_SIZE}

    async with http_session.get(url, params=params, headers=REPLICATE_HEADERS, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        return await resp.json()


async def fetch_packument(http_session: aiohttp.ClientSession, package_name: str) -> dict | None:
    """
    Fetch the packument (package document) for a single npm package.

    The packument contains all versions, their timestamps, description,
    repository info, and more. Retries on 429 with exponential backoff.
    """
    encoded_name = package_name.replace("/", "%2f")
    url = f"{NPM_REGISTRY_URL}/{encoded_name}"

    for attempt in range(4):
        try:
            async with http_session.get(url, headers=REGISTRY_HEADERS, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 404:
                    return None
                if resp.status == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited fetching {package_name}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch packument for {package_name}: {e}")
            return None

    logger.warning(f"Gave up fetching {package_name} after rate limiting")
    return None


def extract_project_urls(packument: dict) -> dict[str, str]:
    """
    Extract URLs from an npm packument and return as a dict.

    npm packages store URLs in:
    - repository: {type: "git", url: "git+https://github.com/user/repo.git"}
    - homepage: "https://example.com"
    - bugs: {url: "https://github.com/user/repo/issues"}
    """
    urls = {}

    repository = packument.get("repository")
    if isinstance(repository, dict):
        repo_url = repository.get("url", "")
        repo_url = repo_url.removeprefix("git+").removeprefix("git://")
        repo_url = repo_url.removesuffix(".git")
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        if repo_url:
            urls["Repository"] = repo_url
    elif isinstance(repository, str):
        repo_url = repository
        if repo_url.startswith("github:"):
            repo_url = f"https://github.com/{repo_url.removeprefix('github:')}"
        elif "/" in repo_url and not repo_url.startswith("http"):
            repo_url = f"https://github.com/{repo_url}"
        if repo_url:
            urls["Repository"] = repo_url

    homepage = packument.get("homepage")
    if homepage and isinstance(homepage, str):
        urls["Homepage"] = homepage

    bugs = packument.get("bugs")
    if isinstance(bugs, dict):
        bugs_url = bugs.get("url", "")
        if bugs_url:
            urls["Bug Tracker"] = bugs_url
    elif isinstance(bugs, str):
        urls["Bug Tracker"] = bugs

    return urls


async def process_packument(session: AsyncSession, packument: dict):
    """
    Process a single packument: upsert all its releases and the package record.
    """
    name = packument.get("name")
    if not name:
        return 0

    versions = packument.get("versions", {})
    time_map = packument.get("time", {})
    description = packument.get("description")
    homepage = packument.get("homepage")
    project_urls = extract_project_urls(packument)

    release_count = 0

    for version_str in versions:
        timestamp_str = time_map.get(version_str)
        if not timestamp_str:
            continue

        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).replace(tzinfo=None)

        # Upsert release
        release_stmt = (
            insert(DBRelease)
            .values(
                ecosystem="npm",
                package_name=name,
                version=version_str,
                first_seen=timestamp,
                last_seen=timestamp,
            )
            .on_conflict_do_update(
                constraint="unique_release",
                set_={
                    "first_seen": func.least(DBRelease.first_seen, timestamp),
                    "last_seen": func.greatest(DBRelease.last_seen, timestamp),
                },
            )
        )
        await session.exec(release_stmt)
        release_count += 1

    # Determine first_seen and last_seen from the time map
    version_times = [
        datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None)
        for v, t in time_map.items()
        if v in versions
    ]

    if version_times:
        first_seen = min(version_times)
        last_seen = max(version_times)
    else:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        first_seen = now
        last_seen = now

    # Upsert package
    package_data = {
        "ecosystem": "npm",
        "package_name": name,
        "description": description,
        "home_page": homepage,
        "project_urls": project_urls,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }

    package_stmt = (
        insert(DBPackage)
        .values(**package_data)
        .on_conflict_do_update(
            constraint="unique_package",
            set_={
                "description": description,
                "home_page": homepage,
                "project_urls": project_urls,
                "first_seen": func.least(DBPackage.first_seen, first_seen),
                "last_seen": func.greatest(DBPackage.last_seen, last_seen),
            },
        )
    )
    await session.exec(package_stmt)

    return release_count


async def sync_once(http_session: aiohttp.ClientSession) -> dict:
    """
    Run a single sync cycle:
    1. Load last_seq from DB
    2. Fetch a batch of changes from the _changes feed
    3. Fetch packuments for changed packages
    4. Upsert releases and packages directly into DB
    5. Save new last_seq
    """
    async with managed_session() as session:
        last_seq = await load_last_seq(session)

    logger.info(f"npm sync: fetching changes since seq {last_seq}")

    # Fetch changes from the _changes feed
    changes_data = await fetch_changes(http_session, since=last_seq)
    results = changes_data.get("results", [])
    new_last_seq = changes_data.get("last_seq", last_seq)

    if not results:
        logger.info("npm sync: no new changes")
        return {"changes": 0, "packages": 0, "releases": 0}

    # Deduplicate package names, filter out design documents
    package_names = list(
        {r["id"] for r in results if not r["id"].startswith("_design/")}
    )

    logger.info(f"npm sync: {len(results)} changes, {len(package_names)} unique packages")

    # Fetch packuments concurrently with a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(settings.NPM_SYNC_PACKUMENT_CONCURRENCY)

    async def fetch_with_limit(name: str):
        async with semaphore:
            return name, await fetch_packument(http_session, name)

    tasks = [fetch_with_limit(name) for name in package_names]
    packument_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process packuments and upsert to DB
    total_releases = 0
    packages_processed = 0

    async with managed_session() as session:
        for result in packument_results:
            if isinstance(result, Exception):
                logger.warning(f"npm sync: packument fetch error: {result}")
                continue

            name, packument = result
            if packument is None:
                continue

            try:
                releases = await process_packument(session, packument)
                total_releases += releases
                packages_processed += 1
            except Exception as e:
                logger.warning(f"npm sync: error processing {name}: {e}")
                continue

        # Commit all upserts in one transaction
        await session.commit()

        # Save cursor position
        await save_last_seq(session, new_last_seq)

    logger.info(
        f"npm sync: processed {packages_processed} packages, "
        f"{total_releases} releases, new seq {new_last_seq}"
    )

    return {
        "changes": len(results),
        "packages": packages_processed,
        "releases": total_releases,
        "last_seq": str(new_last_seq),
    }


async def run_sync_loop():
    """
    Main polling loop. Runs forever, fetching changes from the npm registry
    and upserting into the database.

    Processes batches back-to-back while catching up. Only sleeps when
    there are no new changes (i.e. we've reached the head of the feed).
    """
    logger.info("npm sync: starting continuous polling loop")

    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                result = await sync_once(http_session)
                if result["changes"] == 0:
                    # We're at the head of the feed, wait before polling again
                    await asyncio.sleep(settings.NPM_SYNC_POLL_INTERVAL)
            except asyncio.CancelledError:
                logger.info("npm sync: loop cancelled, shutting down")
                raise
            except Exception as e:
                logger.error(f"npm sync: error in sync cycle: {e}", exc_info=True)
                # Back off on errors to avoid hammering a failing endpoint
                await asyncio.sleep(settings.NPM_SYNC_POLL_INTERVAL)
