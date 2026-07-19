from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    hermes_env: str = "production"
    database_url: str = "postgresql+asyncpg://agentai:password@postgres:5432/agentai"
    encryption_key: str = ""  # 32 bytes base64-encoded

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
