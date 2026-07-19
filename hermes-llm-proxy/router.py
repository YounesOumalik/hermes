"""
hermes-llm-proxy/router.py

Model Router : dispatche les appels vers le bon provider selon le préfixe du modèle.

Règles de routage (par ordre de matching) :
  - "minimax-*"      → MinimaxProvider  (câblé MVP)
  - "MiniMax-*"      → MinimaxProvider  (alias UI)
  - "gpt-*" / "o1-*" → OpenAIProvider   (stub MVP, à activer)
  - "codex-*"        → CodexProvider    (stub MVP, à activer)
  - défaut           → MinimaxProvider (fallback, log warning)

Ajouter un nouveau provider = 1 import + 1 entrée dans PROVIDER_REGISTRY.
"""

from typing import Dict, Type
import logging

from providers import (
    Provider,
    MinimaxProvider,
    OpenAIProvider,
    CodexProvider,
    ProviderError,
    ProviderUnavailable,
)

logger = logging.getLogger("hermes.router")


# Table d'enregistrement (provider name → class).
# Pour activer OpenAI : ajouter import + entry ici + le router dispatchera auto.
PROVIDER_REGISTRY: Dict[str, Type[Provider]] = {
    "minimax": MinimaxProvider,
    # "openai": OpenAIProvider,   # décommenter quand OPENAI_API_KEY dispo
    # "codex":  CodexProvider,    # décommenter quand CODEX_API_KEY dispo
}


class ModelRouter:
    """Router principal. Maintient les instances provider et dispatche par préfixe."""

    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def register(self, name: str, provider: Provider) -> None:
        """Enregistre une instance provider."""
        self._providers[name] = provider
        logger.info(f"Provider registered: {name}")

    def get(self, name: str) -> Provider:
        """Récupère une instance provider par son nom."""
        if name not in self._providers:
            raise ProviderUnavailable(
                f"Provider '{name}' non enregistré. "
                f"Disponibles : {list(self._providers.keys())}"
            )
        return self._providers[name]

    def resolve(self, model_name: str) -> Provider:
        """Détermine le provider à utiliser pour un nom de modèle donné.

        Logique :
          1. Match par préfixe (insensible à la casse)
          2. Fallback sur le provider par défaut (premier enregistré)
        """
        if not model_name:
            return self._fallback()

        model_lower = model_name.lower()

        # Règles explicites (l'extension se fait ici, pas dans le provider)
        prefix_rules = [
            ("minimax", ["minimax-"]),  # Minimax-M2.7 etc.
            ("minimax", ["minimax-"]),  # alias minimax-*
            ("openai", ["gpt-", "o1-", "o3-", "o4-"]),
            ("codex", ["codex-"]),
        ]

        for provider_name, prefixes in prefix_rules:
            for prefix in prefixes:
                if model_lower.startswith(prefix):
                    if provider_name in self._providers:
                        return self._providers[provider_name]
                    # Provider pas câblé → on tombe sur la règle suivante
                    break

        # Fallback : premier provider enregistré
        return self._fallback()

    def _fallback(self) -> Provider:
        if not self._providers:
            raise ProviderUnavailable("Aucun provider enregistré dans le router")
        first_name = next(iter(self._providers))
        logger.warning(
            f"Fallback provider: '{first_name}' (modele non matché par préfixe)"
        )
        return self._providers[first_name]

    async def list_all_models(self) -> list:
        """Agrège la liste de modèles de tous les providers câblés.

        Skip silencieusement les providers non configurés (ProviderUnavailable).
        """
        all_models: list = []
        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                all_models.extend(models)
            except ProviderUnavailable as e:
                logger.debug(f"Provider '{name}' non configuré, skip: {e}")
            except ProviderError as e:
                logger.warning(f"Provider '{name}' erreur list_models: {e}")
        return all_models