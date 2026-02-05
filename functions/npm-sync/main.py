"""
npm Registry Sync Function

Walks the npm registry CouchDB _changes feed to discover new/updated packages,
fetches their packuments (package documents), and writes release data as CSVs
to GCS — feeding into the same split-and-upload -> enqueue-chunk -> webhook
pipeline used by PyPI.

The _changes feed is a sequential log of every modification to every package
in the npm registry. Each response includes a `last_seq` cursor that is used
as the `since` parameter for the next request, forming a chain through all
changes.

Triggered by Cloud Scheduler on a cron (e.g., every 5 minutes).
"""

import io
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import functions_framework
import pandas as pd
import requests
from google.cloud import storage
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NPM_REPLICATE_URL = "https://replicate.npmjs.com/registry"
NPM_REGISTRY_URL = "https://registry.npmjs.org"

# Timeout for individual HTTP requests (seconds)
REQUEST_TIMEOUT = 30


class Settings(BaseSettings):
    DATA_BUCKET: str = "pydocs-datalake"
    STATE_PREFIX: str = "npm-sync-state"
    CHANGES_BATCH_SIZE: int = 500
    MAX_PACKAGES_PER_RUN: int = 200
    PACKUMENT_WORKERS: int = 10


settings = Settings()


def get_storage_client():
    return storage.Client()


def load_last_seq(storage_client) -> str:
    """Load the last processed sequence number from GCS."""
    bucket = storage_client.bucket(settings.DATA_BUCKET)
    blob = bucket.blob(f"{settings.STATE_PREFIX}/last_seq.json")

    try:
        data = json.loads(blob.download_as_text())
        return data["last_seq"]
    except Exception:
        logger.info("No existing last_seq found, starting from 0")
        return "0"


def save_last_seq(storage_client, last_seq: str):
    """Persist the last processed sequence number to GCS."""
    bucket = storage_client.bucket(settings.DATA_BUCKET)
    blob = bucket.blob(f"{settings.STATE_PREFIX}/last_seq.json")
    blob.upload_from_string(
        json.dumps({"last_seq": last_seq, "updated_at": datetime.now(timezone.utc).isoformat()}),
        content_type="application/json",
    )
    logger.info(f"Saved last_seq: {last_seq}")


def fetch_changes(since: str, limit: int) -> dict:
    """
    Fetch a batch of changes from the npm registry _changes feed.

    The _changes feed returns a sequential log of package modifications.
    Each response includes `last_seq` which becomes the `since` cursor
    for the next request — this is the "chain" traversal.
    """
    url = f"{NPM_REPLICATE_URL}/_changes"
    params = {"since": since, "limit": limit}

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_packument(package_name: str) -> dict | None:
    """
    Fetch the packument (package document) for a single npm package.

    The packument contains all versions, their timestamps, description,
    repository info, and more. We request only the fields we need to
    reduce payload size.
    """
    # URL-encode scoped package names (@scope/name -> @scope%2fname)
    encoded_name = package_name.replace("/", "%2f")
    url = f"{NPM_REGISTRY_URL}/{encoded_name}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            logger.debug(f"Package not found (possibly deleted): {package_name}")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch packument for {package_name}: {e}")
        return None


def extract_project_urls(packument: dict) -> str:
    """
    Extract URLs from an npm packument and format them as a JSON array
    of "Label, URL" strings — matching the PyPI project_urls CSV format.

    npm packages store URLs in:
    - repository: {type: "git", url: "git+https://github.com/user/repo.git"}
    - homepage: "https://example.com"
    - bugs: {url: "https://github.com/user/repo/issues"}
    """
    urls = []

    # Repository URL
    repository = packument.get("repository")
    if isinstance(repository, dict):
        repo_url = repository.get("url", "")
        # Clean up git+ prefix and .git suffix
        repo_url = repo_url.removeprefix("git+").removeprefix("git://")
        repo_url = repo_url.removesuffix(".git")
        # Convert ssh URLs to https
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        if repo_url:
            urls.append(f"Repository, {repo_url}")
    elif isinstance(repository, str):
        # Some packages use shorthand like "github:user/repo"
        repo_url = repository
        if repo_url.startswith("github:"):
            repo_url = f"https://github.com/{repo_url.removeprefix('github:')}"
        elif "/" in repo_url and not repo_url.startswith("http"):
            # Bare "user/repo" shorthand
            repo_url = f"https://github.com/{repo_url}"
        if repo_url:
            urls.append(f"Repository, {repo_url}")

    # Homepage URL
    homepage = packument.get("homepage")
    if homepage and isinstance(homepage, str):
        urls.append(f"Homepage, {homepage}")

    # Bugs URL
    bugs = packument.get("bugs")
    if isinstance(bugs, dict):
        bugs_url = bugs.get("url", "")
        if bugs_url:
            urls.append(f"Bug Tracker, {bugs_url}")
    elif isinstance(bugs, str):
        urls.append(f"Bug Tracker, {bugs}")

    return json.dumps(urls)


def packument_to_rows(packument: dict) -> list[dict]:
    """
    Convert an npm packument into a list of release rows matching
    the CSV format used by the PyPI pipeline.

    Each row represents one (package, version) pair with metadata.

    CSV columns: id, ecosystem, name, version, description, home_page, project_urls, timestamp
    """
    name = packument.get("name")
    if not name:
        return []

    versions = packument.get("versions", {})
    time_map = packument.get("time", {})
    description = packument.get("description", "")
    homepage = packument.get("homepage")
    project_urls = extract_project_urls(packument)

    rows = []
    for version_str, version_data in versions.items():
        timestamp = time_map.get(version_str)
        if not timestamp:
            continue

        rows.append(
            {
                "id": str(uuid.uuid4()),
                "ecosystem": "npm",
                "name": name,
                "version": version_str,
                "description": description,
                "home_page": homepage,
                "project_urls": project_urls,
                "timestamp": timestamp,
            }
        )

    return rows


def upload_csv_to_gcs(storage_client, rows: list[dict], batch_id: str):
    """Upload release rows as a CSV to GCS, triggering the existing pipeline."""
    if not rows:
        return

    df = pd.DataFrame(rows)
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)

    unix_ts = int(time.time())
    file_path = f"releases/npm/{unix_ts}-{batch_id}.csv"

    bucket = storage_client.bucket(settings.DATA_BUCKET)
    blob = bucket.blob(file_path)
    blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")

    logger.info(f"Uploaded {len(rows)} rows to gs://{settings.DATA_BUCKET}/{file_path}")


@functions_framework.http
def npm_sync(request):
    """
    Main entry point — triggered by Cloud Scheduler.

    1. Load last_seq from GCS (our position in the _changes chain)
    2. Fetch a batch of changes from the _changes feed
    3. Deduplicate changed package names
    4. Fetch packuments in parallel
    5. Transform to CSV rows and upload to GCS
    6. Save new last_seq to GCS (advancing our chain position)
    """
    storage_client = get_storage_client()
    last_seq = load_last_seq(storage_client)
    logger.info(f"Starting npm sync from seq: {last_seq}")

    # Step 1: Fetch changes from the _changes feed (walk the chain)
    changes_data = fetch_changes(since=last_seq, limit=settings.CHANGES_BATCH_SIZE)
    results = changes_data.get("results", [])
    new_last_seq = changes_data.get("last_seq", last_seq)

    if not results:
        logger.info("No new changes found")
        return {"status": "success", "changes": 0, "packages": 0, "rows": 0}

    logger.info(f"Fetched {len(results)} changes")

    # Step 2: Deduplicate — multiple changes may reference the same package
    # Filter out design documents (start with _design/)
    package_names = list(
        {r["id"] for r in results if not r["id"].startswith("_design/")}
    )

    # Cap the number of packages to fetch per run
    if len(package_names) > settings.MAX_PACKAGES_PER_RUN:
        logger.info(
            f"Capping packages from {len(package_names)} to {settings.MAX_PACKAGES_PER_RUN}"
        )
        package_names = package_names[: settings.MAX_PACKAGES_PER_RUN]

    logger.info(f"Fetching packuments for {len(package_names)} unique packages")

    # Step 3: Fetch packuments in parallel
    all_rows = []
    with ThreadPoolExecutor(max_workers=settings.PACKUMENT_WORKERS) as executor:
        future_to_name = {
            executor.submit(fetch_packument, name): name for name in package_names
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                packument = future.result()
                if packument:
                    rows = packument_to_rows(packument)
                    all_rows.extend(rows)
            except Exception as e:
                logger.warning(f"Error processing {name}: {e}")

    logger.info(f"Extracted {len(all_rows)} total release rows from {len(package_names)} packages")

    # Step 4: Upload CSV to GCS (triggers existing split-and-upload pipeline)
    if all_rows:
        batch_id = str(uuid.uuid4())[:8]
        upload_csv_to_gcs(storage_client, all_rows, batch_id)

    # Step 5: Advance our position in the changes chain
    save_last_seq(storage_client, new_last_seq)

    return {
        "status": "success",
        "changes": len(results),
        "packages": len(package_names),
        "rows": len(all_rows),
        "last_seq": str(new_last_seq),
    }
