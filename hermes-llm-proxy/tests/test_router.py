"""
Tests du Model Router.

Vérifie le dispatch par préfixe de modèle, le fallback, et la gestion
des providers non câblés (ProviderUnavailable).
"""

import pytest

from providers import (
    MinimaxProvider,
    OpenAIProvider,
    ProviderUnavailable,
)
from router import ModelRouter


def make_router():
    """Construit un router avec Minimax câblé + OpenAI stub."""
    router = ModelRouter()
    minimax = MinimaxProvider(api_key="test-key", base_url="https://api.example.com")
    openai_stub = OpenAIProvider(api_key="")  # stub
    router.register("minimax", minimax)
    router.register("openai", openai_stub)
    return router


def test_resolve_minimax_models():
    """Tous les modèles Minimax doivent router vers MinimaxProvider."""
    router = make_router()
    minimax_models = ["MiniMax-M3", "MiniMax-M2.7", "minimax-m2.7-highspeed"]
    for model in minimax_models:
        provider = router.resolve(model)
        assert provider.name == "minimax", f"Expected minimax for {model}, got {provider.name}"


def test_resolve_openai_models_not_routed_when_stub():
    """Les modèles OpenAI ne doivent PAS router vers OpenAIProvider stub."""
    router = make_router()
    # OpenAIProvider est enregistré mais lève ProviderUnavailable
    # Le router doit donc tomber sur le fallback (Minimax)
    provider = router.resolve("gpt-4")
    assert provider.name == "minimax", "Should fallback to minimax when openai stub is used"


def test_resolve_fallback():
    """Modèle inconnu doit fallback sur le premier provider enregistré."""
    router = make_router()
    provider = router.resolve("unknown-model-xyz")
    assert provider.name == "minimax"


def test_resolve_empty_model_fallback():
    """Model name vide doit fallback."""
    router = make_router()
    provider = router.resolve("")
    assert provider.name == "minimax"


def test_get_unregistered_provider():
    """Doit lever ProviderUnavailable pour un provider non enregistré."""
    router = ModelRouter()
    with pytest.raises(ProviderUnavailable):
        router.get("nonexistent")


def test_empty_router_resolve():
    """Router vide doit lever ProviderUnavailable."""
    router = ModelRouter()
    with pytest.raises(ProviderUnavailable):
        router.resolve("any-model")


@pytest.mark.asyncio
async def test_list_all_models_aggregates():
    """list_all_models doit agréger les modèles de tous les providers câblés."""
    router = make_router()
    models = await router.list_all_models()
    # Minimax doit renvoyer ses 6 modèles, OpenAI stub doit lever ProviderUnavailable (skip)
    assert len(models) == 6, f"Expected 6 models from Minimax, got {len(models)}"
    model_ids = [m["id"] for m in models]
    assert "MiniMax-M3" in model_ids
    assert "MiniMax-M2.7" in model_ids


def test_minimax_provider_rejects_placeholder_key():
    """Un placeholder ou clé vide doit lever ProviderUnavailable."""
    minimax = MinimaxProvider(api_key="", base_url="https://api.example.com")
    import asyncio

    async def check():
        with pytest.raises(ProviderUnavailable):
            await minimax.list_models()

    asyncio.run(check())


def test_minimax_provider_rejects_placeholder_marker():
    """Clé contenant 'PLACEHOLDER' doit lever ProviderUnavailable."""
    minimax = MinimaxProvider(api_key="__PLACEHOLDER__", base_url="https://api.example.com")
    import asyncio

    async def check():
        with pytest.raises(ProviderUnavailable):
            await minimax.list_models()

    asyncio.run(check())