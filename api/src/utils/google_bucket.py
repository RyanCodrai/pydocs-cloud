import hashlib
import pickle
import time
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

import aiohttp
import zstandard as zstd
from gcloud.aio.storage import Storage


class AsyncBucket:
    def __init__(self, bucket_name: str, base_path: str = "") -> None:
        self.bucket_name = bucket_name
        self.base_path = Path(base_path)

    async def upload(self, data: bytes, filename: str, content_type: Optional[str] = None) -> str:
        async with Storage() as client:
            full_path = str(self.base_path / filename)
            await client.upload(self.bucket_name, full_path, data, content_type=content_type)
            return full_path

    async def download(self, path: str) -> bytes:
        full_path = str(self.base_path / path)
        async with Storage() as client:
            try:
                return await client.download(self.bucket_name, full_path)
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    raise FileNotFoundError(f"File not found: {self.bucket_name}/{full_path}")
                raise

    async def delete(self, path: str) -> None:
        full_path = str(self.base_path / path)
        async with Storage() as async_client:
            await async_client.delete(self.bucket_name, full_path)

    async def list_files(self, path: str) -> list[str]:
        full_path = str(self.base_path / path)
        async with Storage() as async_client:
            objects = await async_client.list_objects(self.bucket_name, params={"prefix": full_path})
            file_paths = []
            for file_path in objects.get("items", []):
                file_path = file_path.get("name")
                if file_path.endswith("/"):
                    continue
                if file_path.startswith(full_path):
                    file_path = file_path[len(full_path) + 1 :]
                file_paths.append(Path(file_path))
        return file_paths


def gcs_cache(bucket_name: str, path: str, ttl: int, version: int = 1):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_bytes = f"{func.__name__}:{args}:{sorted(kwargs.items())}:{version}".encode()
            cache_key = hashlib.blake2b(cache_bytes, digest_size=16).hexdigest()
            cache_path = f"{path}/{cache_key}.pkl"
            async with Storage() as client:
                try:
                    blob_data = await client.download(bucket_name, cache_path)
                    cache_entry = pickle.loads(blob_data)
                    if time.time() - cache_entry["timestamp"] < ttl:
                        return cache_entry["result"]
                except Exception:
                    pass

                result = await func(*args, **kwargs)
                pkl_data = pickle.dumps({"result": result, "timestamp": time.time()})
                await client.upload(bucket_name, cache_path, pkl_data)
                return result

        return wrapper

    return decorator


_zstd_compressor = zstd.ZstdCompressor(level=5)
_zstd_decompressor = zstd.ZstdDecompressor()


def nfs_gcs_cache(bucket_name: str, path: str, ttl: int, nfs_mount: str = "/mnt/nfs-cache", version: int = 1):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_bytes = f"{func.__name__}:{args}:{sorted(kwargs.items())}:{version}".encode()
            cache_key = hashlib.blake2b(cache_bytes, digest_size=16).hexdigest()
            cache_path = f"{path}/{cache_key}.zst"
            nfs_file = Path(nfs_mount) / cache_path

            # 1. Try NFS (fastest — local SSD)
            try:
                raw = _zstd_decompressor.decompress(nfs_file.read_bytes())
                cache_entry = pickle.loads(raw)
                if time.time() - cache_entry["timestamp"] < ttl:
                    return cache_entry["result"]
            except Exception:
                pass

            # 2. Fall back to GCS
            async with Storage() as client:
                try:
                    blob_data = await client.download(bucket_name, cache_path)
                    raw = _zstd_decompressor.decompress(blob_data)
                    cache_entry = pickle.loads(raw)
                    if time.time() - cache_entry["timestamp"] < ttl:
                        return cache_entry["result"]
                except Exception:
                    pass

                # 3. Compute, then write to GCS (rclone syncs to NFS)
                result = await func(*args, **kwargs)
                pkl_data = pickle.dumps({"result": result, "timestamp": time.time()})
                compressed = _zstd_compressor.compress(pkl_data)
                await client.upload(bucket_name, cache_path, compressed)
                return result

        return wrapper

    return decorator
