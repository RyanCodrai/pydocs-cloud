import io
import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import functions_framework
import pandas as pd
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def split_dataframe(df, chunk_size=100):
    """Split dataframe into chunks."""
    chunks = []
    num_chunks = math.ceil(len(df) / chunk_size)
    for i in range(num_chunks):
        chunk = df[i * chunk_size : (i + 1) * chunk_size]
        if not chunk.empty:
            chunks.append(chunk)
    return chunks


def extract_ecosystem_from_path(file_path):
    """Extract ecosystem from file path (e.g., releases/pypi/file.csv -> pypi)."""
    return Path(file_path).parts[1]


def upload_split_chunk(bucket, split_name, split_csv):
    """Upload a single split chunk to GCS if it doesn't already exist."""
    split_blob = bucket.blob(split_name)

    # Skip if file already exists
    if split_blob.exists():
        return (split_name, True)  # True = skipped

    split_blob.upload_from_string(split_csv, content_type="text/csv")
    return (split_name, False)  # False = uploaded


@functions_framework.cloud_event
def split_and_upload(cloud_event):
    """
    Triggered by Cloud Storage when a file is uploaded to releases/.
    Splits the CSV into chunks and uploads each to releases-chunked/.
    """
    bucket_name = cloud_event.data.get("bucket")
    file_name = cloud_event.data.get("name")
    path = Path(file_name)

    # Only process files in releases/ directory
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

    # Split into chunks of 100
    chunks = split_dataframe(df, chunk_size=100)
    logger.info(f"Split into {len(chunks)} chunks")

    # Upload splits in parallel (10 workers)
    base_name = path.stem  # Get filename without extension
    uploaded_count = 0
    skipped_count = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i, chunk in enumerate(chunks, 1):
            split_name = f"releases-split/{ecosystem}/{base_name}-split-{i:06d}.csv"
            split_csv = chunk.to_csv(index=False)
            future = executor.submit(upload_split_chunk, bucket, split_name, split_csv)
            futures.append((future, i, len(chunks)))

        # Wait for uploads to complete and log progress
        for future, i, total in futures:
            split_name, skipped = future.result()
            if skipped:
                skipped_count += 1
            else:
                uploaded_count += 1

            processed = uploaded_count + skipped_count
            if processed % 100 == 0 or processed == total:
                logger.info(f"📤 Progress: {processed}/{total} (uploaded: {uploaded_count}, skipped: {skipped_count})")

    logger.info(f"✅ Complete: uploaded {uploaded_count} new splits, skipped {skipped_count} existing splits")

    return {
        "status": "success",
        "ecosystem": ecosystem,
        "original_file": file_name,
        "total_rows": len(df),
        "splits_created": len(chunks),
    }
