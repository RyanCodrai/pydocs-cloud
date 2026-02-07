import re


def normalize_package_name(name: str) -> str:
    """Normalize a PyPI package name per PEP 503.

    Lowercases the name and replaces all runs of [-_.] with a single hyphen.
    e.g. "My_Package.Name" -> "my-package-name"
    """
    return re.sub(r"[-_.]+", "-", name).lower()
