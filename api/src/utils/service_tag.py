from enum import Enum


class ServiceType(str, Enum):
    """Service types for conditional route deployment."""
    USER = "user"
    RELEASES = "releases"
    NPM_SYNC = "npm_sync"
    ALL = "all"
