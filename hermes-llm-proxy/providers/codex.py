"""
hermes-llm-proxy/providers/codex.py

Stub Codex (placeholder). Pourra être activé quand CODEX_API_KEY sera fournie
(probablement même base URL qu'OpenAI, modèles codex-*).
"""

from typing import AsyncIterator, List, Dict, Any, Optional

from .base import Provider, ProviderUnavailable


class CodexProvider(Provider):
    """Stub Codex (OpenAI-compatible). Pas encore activé en MVP."""

    name = "codex"

    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def list_models(self) -> List[Dict[str, Any]]:
        raise ProviderUnavailable(
            "Codex provider not yet configured. "
            "Add CODEX_API_KEY to .env and uncomment CodexProvider in router.py."
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise ProviderUnavailable("Codex not configured")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        raise ProviderUnavailable("Codex not configured")
        yield {}