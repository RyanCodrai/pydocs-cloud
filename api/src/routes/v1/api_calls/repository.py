from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import DBApiCall
from src.routes.v1.api_calls.schema import ApiCallInput


class ApiCallRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create(self, data: ApiCallInput) -> DBApiCall:
        api_call = DBApiCall(**data.model_dump())
        self.db_session.add(api_call)
        await self.db_session.commit()
        await self.db_session.refresh(api_call)
        return api_call
