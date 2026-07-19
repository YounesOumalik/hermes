import httpx
import json
from app.config import get_settings

settings = get_settings()


async def stream_chat(
    model_config_id: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """
    Proxy la requête vers hermes-llm-proxy qui gère le routage vers le bon provider.
    Retourne un async generator pour le streaming SSE.
    """
    payload = {
        "model_config_id": model_config_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.llm_proxy_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        yield "[DONE]"
                        return
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


async def test_api_key(provider: str, base_url: str, api_key: str) -> dict:
    """Teste une clé API en appelant le endpoint /v1/models du provider."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await client.get(f"{base_url}/v1/models", headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                return {"success": True, "models": models, "count": len(models)}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
