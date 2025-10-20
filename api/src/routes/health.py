from fastapi import APIRouter
from starlette import status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK, include_in_schema=False)
def health_endpoint() -> str:
    return "OK"
