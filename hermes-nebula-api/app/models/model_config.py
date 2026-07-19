from sqlalchemy import String, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class ModelProvider(str, enum.Enum):
    minimax = "minimax"
    opencode_zen = "opencode_zen"
    openai = "openai"
    anthropic = "anthropic"
    google_gemini = "google_gemini"
    custom = "custom"


class ModelConfig(BaseModel):
    __tablename__ = "model_configs"

    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    context_window: Mapped[int] = mapped_column(default=8192)
    input_price_per_1m: Mapped[float | None] = mapped_column(Float)
    output_price_per_1m: Mapped[float | None] = mapped_column(Float)
    capabilities: Mapped[list] = mapped_column(ARRAY(String), default=["text"])
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    agents: Mapped[list["Agent"]] = relationship("Agent", foreign_keys="Agent.model_config_id")
