from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    hermes_env: str = "development"
    database_url: str = "postgresql+asyncpg://agentai:password@localhost:5432/agentai"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""
    encryption_key: str = ""  # 32 bytes base64-encoded
    upload_dir: str = "/uploads"

    # ── Frontend (Caddy reverse proxy) ──
    next_public_api_url: str = "http://localhost:8000/api"
    frontend_url: str = "http://localhost:3000"

    # ── Bootstrap (Premier SuperAdmin) ──
    superadmin_email: str = ""

    @property
    def llm_proxy_url(self) -> str:
        return "http://llm-proxy:8001"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
