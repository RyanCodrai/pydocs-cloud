from enum import Enum


class ServiceType(str, Enum):
    """Service types for conditional route deployment."""
    USER = "user"
    RELEASES = "releases"
    NPM_SYNC = "npm_sync"
    ALL = "all"


def service_tag(*services: ServiceType):
    """
    Decorator to mark routes with their service type(s).

    Routes can be tagged with one or more service types to control
    which deployments include them.

    Example:
        @service_tag(ServiceType.USER)
        @router.get("/packages")
        async def search_packages():
            ...
    """
    def decorator(func):
        func.services = set(services)
        return func
    return decorator
