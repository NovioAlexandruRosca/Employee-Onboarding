from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finance_db"
    JWT_SECRET: str = "dev-secret-key"
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SECRET: str = "internal-secret"
    HR_SERVICE_URL: str = "http://localhost:8002"

    @field_validator("INTERNAL_SECRET", mode="before")
    @classmethod
    def strip_internal_secret(cls, v: str) -> str:
        return v.strip()

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def strip_db_url(cls, v: str) -> str:
        return v.strip()

    model_config = {"env_file": ".env"}


settings = Settings()
