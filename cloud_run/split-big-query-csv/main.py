import io
import logging
from pathlib import Path

import functions_framework
import pandas as pd
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def split_dataframe(df, chunk_size=100):
    chunks = list()
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        chunk = df[i * chunk_size : (i + 1) * chunk_size]
        if not chunk.empty:
            chunks.append(chunk)
    return chunks


@functions_framework.cloud_event
def split_csv_file(cloud_event):
    bucket_name = cloud_event.data.get("bucket")
    file_name = cloud_event.data.get("name")
    path = Path(file_name)

    # Only process files in bronze/ directory
    if "bronze" not in path.parts:
        logger.info(f"Ignoring file outside bronze/: {file_name}")
        return "Ignored: not in bronze/"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    csv_bytes = blob.download_as_bytes()

    df = pd.read_csv(io.BytesIO(csv_bytes))
    logger.info(f"📥 Read {len(df)} rows from {file_name}")

    chunks = split_dataframe(df)

    # Replace 'bronze' with 'silver' in the path
    # e.g. bronze/releases/x.csv -> silver/releases/x
    parts = list(path.parts)
    parts[parts.index("bronze")] = "silver"
    output_dir = Path(*parts[:-1])

    for chunk_num, chunk_df in enumerate(chunks):
        # Create a buffer to write the chunk to
        csv_buffer = io.StringIO()
        chunk_df.to_csv(csv_buffer, index=False)

        # Upload the chunk to the bucket
        chunk_blob = bucket.blob(f"{output_dir}-{path.stem}-{chunk_num:012d}.csv")
        chunk_blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")

    blob.delete()
    logger.info(f"✅ Uploaded {len(chunks)} chunks")
    logger.info(f"✅ Deleted original file: {file_name}")

    return {
        "status": "success",
        "original_file": file_name,
        "total_rows": len(df),
        "chunks_created": len(chunks),
    }
