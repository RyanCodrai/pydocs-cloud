"""GitHub URL extraction utilities for PyPI packages"""

import re
from urllib.parse import urlparse


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text using regex."""
    if not text:
        return []

    url_pattern = r"(?:(?:https?|ftp|file):\/\/|www\.|ftp\.)(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[-A-Z0-9+&@#\/%=~_|$?!:,.])*(?:\([-A-Z0-9+&@#\/%=~_|$?!:,.]*\)|[A-Z0-9+&@#\/%=~_|$])"
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    return urls


def extract_urls_from_pypi_data(description: str | None, project_urls: dict[str, str]) -> list[str]:
    """Extract and deduplicate URLs from PyPI description and project URLs."""
    all_urls = []

    # Collect URLs from project URLs dict
    if project_urls:
        all_urls.extend(project_urls.values())

    # Extract URLs from description
    if description:
        desc_urls = extract_urls_from_text(description)
        all_urls.extend(desc_urls)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in all_urls:
        if url and url not in seen:
            unique_urls.append(url)
            seen.add(url)

    return unique_urls


def filter_for_source_code_urls(urls: list[str]) -> list[str]:
    """Filter URLs to only include GitHub and GitLab URLs."""
    source_code_urls = []
    for url in urls:
        if "github.com" in url or "gitlab.com" in url:
            source_code_urls.append(url)
    return source_code_urls


def extract_repo_path_from_source_url(url: str) -> str | None:
    """Extract the repository path from a GitHub or GitLab URL."""
    # Remove any fragment or query parameters
    url = url.split("#")[0].split("?")[0].split("@")[0]

    # Remove .git suffix
    url = url.removesuffix(".git")

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    segments = path.split("/")

    # Need at least 2 segments for user/repo or group/project
    if len(segments) < 2:
        return None

    # Return just the first two segments (user/repo or group/project)
    return f"{segments[0]}/{segments[1]}"


def clean_source_urls(source_urls: list[str]) -> list[str]:
    """Clean GitHub and GitLab URLs to extract just the repository paths."""
    cleaned_repos = set()

    for url in source_urls:
        if "github.com" in url or "gitlab.com" in url:
            repo_path = extract_repo_path_from_source_url(url)
            if repo_path:
                base_url = "https://github.com" if "github.com" in url else "https://gitlab.com"
                cleaned_repos.add(f"{base_url}/{repo_path}")

    return sorted(list(cleaned_repos))


def filter_out_reserved_paths(source_urls: list[str]) -> list[str]:
    """Filter out GitHub and GitLab URLs that point to reserved paths, not repositories."""
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

    gitlab_reserved = {
        "about",
        "admin",
        "api",
        "assets",
        "dashboard",
        "explore",
        "groups",
        "help",
        "import",
        "invites",
        "issues",
        "login",
        "merge_requests",
        "new",
        "notifications",
        "oauth",
        "profile",
        "projects",
        "public",
        "search",
        "settings",
        "snippets",
        "users",
        "groups",
        "s",
        "-",
    }

    valid_repos = []
    for url in source_urls:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        segments = path.split("/")

        if len(segments) >= 2:
            first_segment = segments[0]

            if "github.com" in url:
                reserved = github_reserved
            elif "gitlab.com" in url:
                reserved = gitlab_reserved
            else:
                continue

            if first_segment not in reserved and not first_segment.isdigit():
                valid_repos.append(url)

    return valid_repos


def extract_github_candidates(description: str | None, project_urls: dict[str, str]) -> list[str]:
    """
    Main function to extract GitHub/GitLab repository candidates from PyPI package data.

    Args:
        description: Package description text
        project_urls: Dictionary of project URLs

    Returns:
        List of cleaned, valid GitHub/GitLab repository URLs
    """
    # Extract all URLs
    all_urls = extract_urls_from_pypi_data(description, project_urls)

    # Filter for source code URLs
    source_code_urls = filter_for_source_code_urls(all_urls)

    if not source_code_urls:
        return []

    # Clean and normalize URLs
    clean_repos = clean_source_urls(source_code_urls)

    # Filter out reserved paths
    valid_repos = filter_out_reserved_paths(clean_repos)

    return valid_repos
