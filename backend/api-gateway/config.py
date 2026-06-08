from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str = "key"
    JWT_ALGORITHM: str = "HS256"

    AUTH_SERVICE_URL: str = "http://localhost:8001"
    HR_SERVICE_URL: str = "http://localhost:8002"
    MANAGER_SERVICE_URL: str = "http://localhost:8003"
    FINANCE_SERVICE_URL: str = "http://localhost:8004"
    IT_SERVICE_URL: str = "http://localhost:8005"
    NOTIFIER_SERVICE_URL: str = "http://localhost:8006"
    NOTIFIER_SERVICE_WS_URL: str = "ws://localhost:8006"

    model_config = {"env_file": ".env"}


settings = Settings()
