"""
hermes-core/config.py — Configuration Pydantic Settings.

Toutes les valeurs sont surchargées par env vars ou par le fichier /app/.env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Service ---
    hermes_env: str = "production"
    hermes_core_port: int = 8002

    # --- Auth ---
    hermes_jwt_secret: str = ""

    # --- DB (Postgres hôte, user hermes_app limité) ---
    database_url: str = "postgresql+asyncpg://hermes_app:changeme@localhost:5432/hermes"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600  # 1h
    db_pool_pre_ping: bool = True

    # --- Upstream services ---
    hermes_llm_proxy_url: str = "http://hermes-llm-proxy:8001"
    hermes_llm_proxy_token: str = ""

    mcp_server_url: str = "http://mcp-server:3100"
    mcp_auth_token: str = ""

    n8n_webhook_base_url: str = "http://n8n:5678/webhook"

    # --- HTTP client ---
    http_timeout_seconds: float = 60.0
    http_max_connections: int = 100
    http_max_keepalive: int = 20

    # --- Storage ---
    attachments_dir: str = "/var/lib/hermes-core/attachments"

    # --- Tool execution ---
    tool_executor_max_iterations: int = 5
    tool_requires_approval_default: bool = False


settings = Settings()