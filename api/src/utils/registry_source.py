"""Registry source utilities — sdist/tarball downloads from PyPI and npm."""

import gzip

import aiohttp
from src.utils.google_bucket import nfs_gcs_cache

TEN_YEARS = 10 * 365 * 24 * 60 * 60


@nfs_gcs_cache(bucket_name="pydocs-repo-cache", path="cache/registry-tarballs", ttl=TEN_YEARS, version=1)
async def get_pypi_tarball(package_name: str, version: str) -> bytes:
    """Fetch a PyPI package's sdist tarball for a specific version.

    PyPI sdists are .tar.gz — we decompress gzip here so the cache stores
    raw tar bytes (same convention as GitHub tarballs).
    """
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()

    sdist = next((u for u in data.get("urls", []) if u["packagetype"] == "sdist"), None)
    if sdist is None:
        raise FileNotFoundError(f"No sdist found for {package_name}=={version}")

    async with aiohttp.ClientSession() as session:
        async with session.get(sdist["url"]) as response:
            response.raise_for_status()
            gz_bytes = await response.read()
            return gzip.decompress(gz_bytes)


@nfs_gcs_cache(bucket_name="pydocs-repo-cache", path="cache/registry-tarballs", ttl=TEN_YEARS, version=1)
async def get_npm_tarball(package_name: str, version: str) -> bytes:
    """Fetch an npm package's tarball for a specific version.

    npm tarballs are .tgz — we decompress gzip here so the cache stores
    raw tar bytes (same convention as GitHub tarballs).
    """
    url = f"https://registry.npmjs.org/{package_name}/-/{package_name.split('/')[-1]}-{version}.tgz"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            gz_bytes = await response.read()
            return gzip.decompress(gz_bytes)
