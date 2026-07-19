"""
hermes-llm-proxy/providers/__init__.py

Abstraction Provider pour le Model Router.
Chaque provider implémente l'interface Provider (base.py) et expose ses modèles.
Le router dispatche par préfixe du nom de modèle.
"""

from .base import Provider, ProviderError, ProviderUnavailable
from .minimax import MinimaxProvider
from .openai import OpenAIProvider
from .codex import CodexProvider

__all__ = [
    "Provider",
    "ProviderError",
    "ProviderUnavailable",
    "MinimaxProvider",
    "OpenAIProvider",
    "CodexProvider",
]