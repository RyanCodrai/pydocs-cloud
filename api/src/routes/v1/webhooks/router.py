import io
import json
import logging

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends
from google.cloud import storage
from pydantic import BaseModel
from src.routes.v1.packages.schema import PackageInput
from src.routes.v1.packages.service import PackageService, get_package_service
from src.routes.v1.releases.schema import ReleaseInput
from src.routes.v1.releases.service import ReleaseService, get_release_service
from src.utils.pypi import normalize_package_name
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()
logger = logging.getLogger(__name__)


class GCSFilePayload(BaseModel):
    file_path: str
    bucket_name: str


@service_tag(ServiceType.RELEASES)
@router.post("/webhooks/releases")
async def process_releases_webhook(
    payload: GCSFilePayload,
    release_service: ReleaseService = Depends(get_release_service),
    package_service: PackageService = Depends(get_package_service),
) -> dict:
    logger.info(f"Processing releases from GCS file: {payload.file_path}")

    # Read CSV from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(payload.bucket_name)
    blob = bucket.blob(payload.file_path)

    # Check if file exists
    try:
        csv_bytes = blob.download_as_bytes()
    except Exception as e:
        if "404" in str(e):
            logger.info(f"File {payload.file_path} not found")
            return {"status": "success"}
        raise

    d_types = {"version": str, "description": str, "home_page": str, "project_urls": str}
    df = pd.read_csv(io.BytesIO(csv_bytes), dtype=d_types)

    # Filter out rows with missing required fields
    df = df.dropna(subset=["name", "version"])
    # Convert to list of dicts, replacing NaN with None
    releases_data = df.replace({np.nan: None}).to_dict(orient="records")

    for release_data in releases_data:
        package_name = release_data["name"]
        if release_data["ecosystem"] == "pypi":
            package_name = normalize_package_name(package_name)

        # Upsert release
        await release_service.upsert(
            data=ReleaseInput(
                ecosystem=release_data["ecosystem"],
                package_name=package_name,
                version=release_data["version"],
                first_seen=release_data["timestamp"],
                last_seen=release_data["timestamp"],
            ),
            commit=False,  # Don't commit the release yet, commit at the same time the package is upserted
        )

        # Transform project_urls from array format ["Label, URL"] to dict {"Label": "URL"}
        project_urls_dict = {}
        project_urls_raw = release_data.get("project_urls") or "[]"
        for entry in json.loads(project_urls_raw):
            if "," not in entry:
                continue
            key, value = entry.split(",", 1)
            value = value.strip()
            if not value:
                continue
            project_urls_dict[key.strip()] = value

        # Upsert package with description, home_page, and project_urls
        await package_service.upsert(
            data=PackageInput(
                ecosystem=release_data["ecosystem"],
                package_name=package_name,
                description=release_data.get("description"),
                home_page=release_data.get("home_page"),
                project_urls=project_urls_dict,
                first_seen=release_data["timestamp"],
                last_seen=release_data["timestamp"],
            ),
            commit=True,
        )

    # Delete the file after successful processing
    blob.delete()
    logger.info(f"Deleted processed file: {payload.file_path}")

    return {"status": "success"}
