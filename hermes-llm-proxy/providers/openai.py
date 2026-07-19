"""
hermes-llm-proxy/providers/openai.py

Stub OpenAI (placeholder). Sera activé quand OPENAI_API_KEY sera fournie.
Architecture déjà en place : ajouter OPENAI_API_KEY dans .env + activer dans router.py.
"""

from typing import AsyncIterator, List, Dict, Any, Optional

from .base import Provider, ProviderUnavailable


class OpenAIProvider(Provider):
    """Stub OpenAI. Pas encore activé en MVP."""

    name = "openai"

    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def list_models(self) -> List[Dict[str, Any]]:
        raise ProviderUnavailable(
            "OpenAI provider not yet configured. "
            "Add OPENAI_API_KEY to .env and uncomment OpenAIProvider in router.py."
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise ProviderUnavailable("OpenAI not configured")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        raise ProviderUnavailable("OpenAI not configured")
        yield {}  # noqa: unreachable — satisfies type checker