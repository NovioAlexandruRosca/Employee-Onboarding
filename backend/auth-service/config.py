from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql"
    JWT_SECRET: str = "key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def strip_db_url(cls, v: str) -> str:
        return v.strip()

    model_config = {"env_file": ".env"}


settings = Settings()
