import re
from typing import Annotated

from pydantic import BeforeValidator


def normalize_package_name(name: str) -> str:
    """Normalize a PyPI package name per PEP 503.

    Lowercases the name and replaces all runs of [-_.] with a single hyphen.
    e.g. "My_Package.Name" -> "my-package-name"
    """
    return re.sub(r"[-_.]+", "-", name).lower()


NormalizedPypiPackageName = Annotated[str, BeforeValidator(normalize_package_name)]
