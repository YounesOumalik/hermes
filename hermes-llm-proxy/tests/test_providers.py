"""
Tests des providers individuels.

Vérifie la conformité à l'interface Provider et la gestion d'erreurs.
"""

import pytest

from providers import (
    MinimaxProvider,
    OpenAIProvider,
    CodexProvider,
    ProviderUnavailable,
)


def test_minimax_lists_static_models_when_configured():
    """Quand la clé est valide, list_models doit retourner les 6 modèles hardcodés."""
    import asyncio

    minimax = MinimaxProvider(api_key="valid-key", base_url="https://api.example.com")

    async def check():
        models = await minimax.list_models()
        assert len(models) == 6
        ids = [m["id"] for m in models]
        assert ids == ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"]

    asyncio.run(check())


def test_openai_stub_raises_unavailable():
    """OpenAIProvider stub doit lever ProviderUnavailable sur toutes les méthodes."""
    openai = OpenAIProvider(api_key="")
    import asyncio

    async def check():
        with pytest.raises(ProviderUnavailable):
            await openai.list_models()
        with pytest.raises(ProviderUnavailable):
            async for _ in openai.stream_chat([], "gpt-4"):
                pass

    asyncio.run(check())


def test_codex_stub_raises_unavailable():
    """CodexProvider stub doit lever ProviderUnavailable."""
    codex = CodexProvider(api_key="")
    import asyncio

    async def check():
        with pytest.raises(ProviderUnavailable):
            await codex.list_models()

    asyncio.run(check())


def test_provider_name_attribute():
    """Chaque provider doit exposer son nom."""
    assert MinimaxProvider(api_key="k", base_url="u").name == "minimax"
    assert OpenAIProvider(api_key="k").name == "openai"
    assert CodexProvider(api_key="k").name == "codex"