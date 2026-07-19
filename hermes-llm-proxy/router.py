import base64
import json
import httpx
import uuid
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import get_settings

router = APIRouter(prefix="/v1", tags=["llm"])
settings = get_settings()

# Engine et Session localisés pour le proxy
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def decrypt(ciphertext: str) -> str:
    """Déchiffre la clé API avec AES-256-GCM."""
    key = base64.urlsafe_b64decode(settings.encryption_key)
    raw = base64.urlsafe_b64decode(ciphertext)
    nonce = raw[:12]
    ct = raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


class ChatCompletionRequest(BaseModel):
    model_config_id: uuid.UUID
    messages: list
    temperature: float = 0.7
    max_tokens: int = 4096


@router.post("/chat/completions")
async def proxy_chat_completion(payload: ChatCompletionRequest):
    async with AsyncSessionLocal() as db:
        # 1. Charger la config du modèle
        from sqlalchemy.sql import text
        # Pour éviter les imports cycliques, on fait une requête SQL brute ou SQLAlchemy core
        config_stmt = text("SELECT provider, model_name FROM model_configs WHERE id = :id AND enabled = true")
        config_res = await db.execute(config_stmt, {"id": payload.model_config_id})
        model_config = config_res.fetchone()

        if not model_config:
            raise HTTPException(status_code=404, detail="Model configuration not found or disabled")

        provider, model_name = model_config[0], model_config[1]

        # 2. Charger la clé API du provider
        key_stmt = text("SELECT encrypted_key, base_url FROM api_keys WHERE provider = :provider AND is_active = true")
        key_res = await db.execute(key_stmt, {"provider": provider.lower()})
        api_key_record = key_res.fetchone()

        if not api_key_record:
            raise HTTPException(
                status_code=400,
                detail=f"No active global API Key found for provider: {provider}. Contact your administrator."
            )

        encrypted_key, base_url = api_key_record[0], api_key_record[1]

    # 3. Déchiffrer la clé API
    try:
        raw_api_key = decrypt(encrypted_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt API key: {str(e)}")

    # 4. Préparer l'URL et les en-têtes
    url = f"{base_url}/chat/completions" if base_url else ""
    if not url:
        if provider == "minimax":
            url = "https://api.minimax.chat/v1/chat/completions"
        elif provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
        elif provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"  # Format différent
        elif provider == "google_gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={raw_api_key}"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported or unconfigured provider base URL: {provider}")

    # Formater la requête selon le provider
    headers = {"Content-Type": "application/json"}
    
    # Pour format standard OpenAI (MiniMax v2, OpenAI, OpenCode Zen, etc.)
    openai_headers = {**headers, "Authorization": f"Bearer {raw_api_key}"}
    openai_payload = {
        "model": model_name,
        "messages": payload.messages,
        "temperature": payload.temperature,
        "max_tokens": payload.max_tokens,
        "stream": True
    }

    # 5. Streamer vers le provider
    async def openai_stream_generator():
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    url,
                    headers=openai_headers,
                    json=openai_payload
                ) as response:
                    if response.status_code != 200:
                        error_detail = await response.aread()
                        yield f"data: {json.dumps({'error': f'LLM Provider error {response.status_code}: {error_detail.decode()}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # Gérer Gemini ou Anthropic si nécessaire (ici on met l'implémentation standard compatible OpenAI)
    return StreamingResponse(openai_stream_generator(), media_type="text/event-stream")