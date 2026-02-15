from pydantic import BaseModel


class GitHubCodeInput(BaseModel):
    code: str
    redirect_uri: str


class AuthTokenOutput(BaseModel):
    api_key: str
