"""
hermes-llm-proxy/providers/minimax.py

Implémentation Minimax (compatible OpenAI).
Réutilise la structure httpx du daemon original.
"""

from typing import AsyncIterator, List, Dict, Any, Optional
import httpx

from .base import Provider, ProviderError, ProviderUnavailable


# Modèles Minimax exposés (alignés sur la liste UI actuelle dans chat/page.tsx)
MINIMAX_MODELS: List[Dict[str, Any]] = [
    {"id": "MiniMax-M3", "object": "model", "owned_by": "minimax"},
    {"id": "MiniMax-M2.7", "object": "model", "owned_by": "minimax"},
    {"id": "MiniMax-M2.7-highspeed", "object": "model", "owned_by": "minimax"},
    {"id": "MiniMax-M2.5", "object": "model", "owned_by": "minimax"},
    {"id": "MiniMax-M2.1", "object": "model", "owned_by": "minimax"},
    {"id": "MiniMax-M2", "object": "model", "owned_by": "minimax"},
]


class MinimaxProvider(Provider):
    """Provider Minimax (compatible OpenAI)."""

    name = "minimax"

    def __init__(self, api_key: str, base_url: str, default_model: str = "MiniMax-M2.7"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        # Le client httpx sera injecté via set_http_client() au startup (pool partagé)
        self._client: Optional[httpx.AsyncClient] = None

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Injecte le client httpx partagé (lifespan)."""
        self._client = client

    def _ensure_configured(self) -> None:
        if not self.api_key or "PLACEHOLDER" in self.api_key or "__" in self.api_key:
            raise ProviderUnavailable(
                "Minimax non configuré : MINIMAX_API_KEY manquante ou placeholder. "
                "Définir la vraie clé via /api/settings/update côté hermes-core."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> List[Dict[str, Any]]:
        """Retourne la liste statique des modèles Minimax."""
        self._ensure_configured()
        return list(MINIMAX_MODELS)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self._ensure_configured()
        assert self._client is not None, "HTTP client not initialized"

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Minimax HTTP {e.response.status_code}: {e.response.text[:200]}")
        except httpx.HTTPError as e:
            raise ProviderError(f"Minimax network error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        self._ensure_configured()
        assert self._client is not None, "HTTP client not initialized"

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()  # strip "data: "
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        yield chunk
                    except json.JSONDecodeError:
                        # Skip malformed chunks
                        continue
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Minimax HTTP {e.response.status_code}: {e.response.text[:200]}")
        except httpx.HTTPError as e:
            raise ProviderError(f"Minimax network error: {e}")