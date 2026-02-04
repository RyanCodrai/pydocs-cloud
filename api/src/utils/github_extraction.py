"""GitHub URL extraction utilities for PyPI packages"""

import re
from urllib.parse import urlparse

github_reserved = {
    "about",
    "account",
    "admin",
    "api",
    "apps",
    "assets",
    "business",
    "codespaces",
    "collections",
    "contact",
    "customer-stories",
    "dashboard",
    "devices",
    "enterprise",
    "events",
    "explore",
    "features",
    "gist",
    "help",
    "home",
    "issues",
    "join",
    "login",
    "logout",
    "marketplace",
    "new",
    "notifications",
    "organizations",
    "orgs",
    "pricing",
    "pulls",
    "search",
    "security",
    "sessions",
    "settings",
    "signup",
    "site",
    "sponsors",
    "stars",
    "team",
    "topics",
    "trending",
    "users",
    "watching",
    "wiki",
}


def extract_repo_path_from_source_url(url: str) -> str | None:
    url = url.split("#")[0].split("?")[0].split("@")[0]
    url = url.removesuffix(".git")

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    segments = path.split("/")

    # Need at least 2 segments for user/repo or group/project
    if len(segments) < 2:
        return None

    # Return just the first two segments (user/repo or group/project)
    return f"https://github.com/{segments[0]}/{segments[1]}"


def filter_out_reserved_paths(source_urls: list[str]) -> list[str]:
    valid_repos = []
    for url in source_urls:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        segments = path.split("/")
        if len(segments) >= 2:
            first_segment = segments[0]
            if first_segment not in github_reserved and not first_segment.isdigit():
                valid_repos.append(url)
    return valid_repos


def extract_github_candidates(
    description: str | None, project_urls: dict[str, str], home_page: str | None = None
) -> list[str]:
    # Extract URLs from description
    url_pattern = r"(?:(?:https?|ftp|file):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])"
    description_urls = re.findall(url_pattern, description or "", re.IGNORECASE)
    # Extract URLs from project_urls and home_page
    all_urls = description_urls + list(project_urls.values())
    all_urls += [home_page] if home_page else []
    # Filter out URLs that are not GitHub URLs
    source_code_urls = [url for url in all_urls if "github.com" in url]
    # Extract repository path from GitHub URLs
    source_urls = [extract_repo_path_from_source_url(url) for url in source_code_urls]
    source_urls = [url for url in source_urls if url]
    # Filter out reserved paths
    valid_repos = filter_out_reserved_paths(source_urls)
    # Deduplicate
    return list(set(valid_repos))
