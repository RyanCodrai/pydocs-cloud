import io
import json
import logging
import math
from pathlib import Path

import functions_framework
import pandas as pd
from google.cloud import storage, tasks_v2
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    QUEUE_PATH: str
    PYPI_PROCESSOR_URL: str

    @property
    def PROCESSOR_URLS(self):
        return {
            "pypi": self.PYPI_PROCESSOR_URL,
            # Add more ecosystems as needed:
            # 'npm': self.NPM_PROCESSOR_URL,
        }

    def get_processor_url(self, ecosystem):
        processor_url = self.PROCESSOR_URLS.get(ecosystem)
        if not processor_url:
            raise ValueError(f"No processor URL configured for ecosystem: {ecosystem}")
        return processor_url


settings = Settings()


def split_dataframe(df, chunk_size=100):
    chunks = []
    num_chunks = math.ceil(len(df) / chunk_size)
    for i in range(num_chunks):
        chunk = df[i * chunk_size : (i + 1) * chunk_size]
        if not chunk.empty:
            chunks.append(chunk)
    return chunks


def extract_ecosystem_from_path(file_path):
    ecosystem = Path(file_path).parts[1]
    if ecosystem not in settings.PROCESSOR_URLS:
        raise ValueError(f"No processor URL configured for ecosystem: {ecosystem}")
    return ecosystem


def create_cloud_task(client, releases, ecosystem):
    """Create a Cloud Task for processing a chunk of releases."""
    # Create the task
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": settings.get_processor_url(ecosystem),
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(releases).encode(),
        }
    }

    # Send the task
    response = client.create_task(request={"parent": settings.QUEUE_PATH, "task": task})
    return response


@functions_framework.cloud_event
def split_and_enqueue(cloud_event):
    """
    Triggered by Cloud Storage when a file is uploaded to releases/.
    Splits the CSV into chunks and enqueues each chunk to Cloud Tasks.
    """
    bucket_name = cloud_event.data.get("bucket")
    file_name = cloud_event.data.get("name")
    path = Path(file_name)

    # Only process files in releases/ directory with correct ecosystem
    if path.parts[0] != "releases":
        logger.info(f"Ignoring file outside releases/: {file_name}")
        return {"status": "ignored", "reason": "not in releases/"}
    ecosystem = extract_ecosystem_from_path(file_name)
    logger.info(f"Processing {ecosystem} releases from {file_name}")

    # Download and parse CSV
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    csv_bytes = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(csv_bytes))
    logger.info(f"📥 Read {len(df)} rows from {file_name}")

    # Split into chunks
    chunks = split_dataframe(df, chunk_size=100)
    logger.info(f"Split into {len(chunks)} chunks, enqueueing to Cloud Tasks...")

    # Enqueue each chunk as a Cloud Task
    tasks_client = tasks_v2.CloudTasksClient()
    for chunk in chunks:
        create_cloud_task(client=tasks_client, releases=chunk.to_dict("records"), ecosystem=ecosystem)
    logger.info(f"✅ Successfully enqueued {len(chunks)} tasks")

    return {
        "status": "success",
        "ecosystem": ecosystem,
        "original_file": file_name,
        "total_rows": len(df),
        "tasks_enqueued": len(chunks),
    }
