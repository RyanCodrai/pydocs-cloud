from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")

    # Application Configuration
    LOGGING_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    ENVIRONMENT: Literal["LOCAL", "PROD", "TEST", "EVAL"]
    SERVICE_TYPE: Literal["user", "releases", "all"] = "all"

    # Database Configuration
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    DATABASE_POOL_SIZE: int = 100
    DATABASE_POOL_SIZE_OVERFLOW: int = 200

    # Optional Auth0 Configuration
    AUTH0_DOMAIN: Optional[str] = None
    AUTH0_CLIENT_ID: Optional[str] = None
    AUTH0_ISSUER: Optional[str] = None
    AUTH0_ALGORITHMS: Optional[str] = None

    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=int(self.POSTGRES_PORT),
            database=self.POSTGRES_DB,
        )


settings = Settings()
