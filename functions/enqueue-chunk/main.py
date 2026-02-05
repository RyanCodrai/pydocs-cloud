import json
import logging
from pathlib import Path

import functions_framework
from google.cloud import storage, tasks_v2
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    QUEUE_PATH: str
    PYPI_PROCESSOR_URL: str
    NPM_PROCESSOR_URL: str = ""

    @property
    def PROCESSOR_URLS(self):
        urls = {
            "pypi": self.PYPI_PROCESSOR_URL,
        }
        if self.NPM_PROCESSOR_URL:
            urls["npm"] = self.NPM_PROCESSOR_URL
        return urls

    def get_processor_url(self, ecosystem):
        processor_url = self.PROCESSOR_URLS.get(ecosystem)
        if not processor_url:
            raise ValueError(f"No processor URL configured for ecosystem: {ecosystem}")
        return processor_url


settings = Settings()


def extract_ecosystem_from_path(file_path):
    """Extract ecosystem from file path (e.g., releases-split/pypi/file.csv -> pypi)."""
    return Path(file_path).parts[1]


def create_cloud_task(client, file_path, bucket_name, processor_url):
    """Create a Cloud Task with GCS file path instead of release data."""
    payload = {"file_path": file_path, "bucket_name": bucket_name}

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": processor_url,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(payload).encode(),
        }
    }

    response = client.create_task(request={"parent": settings.QUEUE_PATH, "task": task})
    return response


@functions_framework.cloud_event
def enqueue_chunk(cloud_event):
    bucket_name = cloud_event.data.get("bucket")
    file_name = cloud_event.data.get("name")
    path = Path(file_name)

    # Only process files in releases-split/ directory
    if path.parts[0] != "releases-split":
        logger.info(f"Ignoring file outside releases-split/: {file_name}")
        return {"status": "ignored", "reason": "not in releases-split/"}

    ecosystem = extract_ecosystem_from_path(file_name)
    processor_url = settings.get_processor_url(ecosystem)
    logger.info(f"Enqueueing task for {ecosystem} split file: {file_name}")

    # Create a single Cloud Task with the GCS file path
    tasks_client = tasks_v2.CloudTasksClient()
    create_cloud_task(tasks_client, file_name, bucket_name, processor_url)

    logger.info(f"✅ Enqueued task for split file: {file_name}")

    return {
        "status": "success",
        "split_file": file_name,
        "tasks_created": 1,
    }
