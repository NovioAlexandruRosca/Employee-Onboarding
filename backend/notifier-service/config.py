from pydantic import field_validator

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str = "key"
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SECRET: str = "internal-secret"

    @field_validator("INTERNAL_SECRET", mode="before")
    @classmethod
    def strip_internal_secret(cls, v: str) -> str:
        return v.strip()

    model_config = {"env_file": ".env"}


settings = Settings()
