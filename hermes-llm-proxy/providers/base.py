"""
hermes-llm-proxy/providers/base.py

Interface abstraite qu'implémente chaque provider LLM (Minimax, OpenAI, Codex).
Toutes les méthodes sont async ; les implémentations concrètes utilisent httpx.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Optional


class ProviderError(Exception):
    """Erreur générique d'un provider (réseau, parsing, etc.)."""
    pass


class ProviderUnavailable(ProviderError):
    """Provider non configuré (clé API manquante ou provider désactivé)."""
    pass


class Provider(ABC):
    """
    Interface Provider.

    Tous les providers exposent :
      - list_models()         : catalogue statique ou dynamique
      - chat(...)             : appel non-streaming (JSON)
      - stream_chat(...)      : appel streaming (SSE chunks)
      - embed(...)            : embeddings (stub MVP)
    """

    name: str = "abstract"

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """Retourne la liste des modèles exposés par ce provider.

        Format attendu (compatible OpenAI) :
          [
            {"id": "model-name", "object": "model", "owned_by": "<provider>"},
            ...
          ]
        """
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Appel chat non-streaming.

        Retourne un dict compatible OpenAI :
          {
            "id": "chatcmpl-...",
            "object": "chat.completion",
            "model": "...",
            "choices": [{"index": 0, "message": {...}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
          }
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Appel chat streaming.

        Yield des chunks au format OpenAI SSE (déjà parsés en dict) :
          {"id": "...", "object": "chat.completion.chunk", "choices": [{"delta": {...}}]}
        Le main.py formate ces dicts en `data: {...}\\n\\n` pour SSE.
        """
        raise NotImplementedError

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """Embeddings (stub MVP, surchargeable par provider)."""
        raise ProviderUnavailable(f"{self.name}.embed() not implemented")