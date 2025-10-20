from fastapi import APIRouter
from starlette import status
from src.utils.service_tag import ServiceType, service_tag

router = APIRouter()


@service_tag(ServiceType.USER, ServiceType.RELEASES)
@router.get("/health", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_endpoint() -> str:
    return "OK"
