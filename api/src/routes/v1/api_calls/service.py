import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBApiCall
from src.routes.v1.api_calls.repository import ApiCallRepository
from src.routes.v1.api_calls.schema import ApiCallInput


class ApiCallService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.repository = ApiCallRepository(db_session=db_session)

    async def create(self, user_id: uuid.UUID, endpoint: str) -> DBApiCall:
        api_call_input = ApiCallInput(user_id=user_id, endpoint=endpoint)
        return await self.repository.create(api_call_input)
