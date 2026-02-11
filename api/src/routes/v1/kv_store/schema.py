from pydantic import BaseModel


class KvStoreInput(BaseModel):
    key: str
    value: str
