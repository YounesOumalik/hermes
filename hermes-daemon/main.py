"""
Hermes Daemon — Backend agent IA (FastAPI)

Responsabilités :
  • Exposer une API REST pour Hermes Studio (chat, agents, tools)
  • Connecter Minimax via l'API compatible OpenAI
  • Déléguer des tâches complexes à n8n via webhooks
  • Coordonner les appels au serveur MCP (filesystem, GitHub)
"""

import asyncio
import base64
import hashlib
import ipaddress
import json
import logging
import mimetypes
import os
import re
import secrets
import shutil
import socket
import time
import httpx
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from docx import Document
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pypdf import PdfReader

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7"
LEGACY_MINIMAX_MODELS = {"abab6.5s-chat", "abab6.5t-chat"}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hermes_env: str = "production"
    hermes_port: int = 8001
    hermes_jwt_secret: str = ""
    minimax_api_key: str = ""
    minimax_base_url: str = DEFAULT_MINIMAX_BASE_URL
    minimax_model: str = DEFAULT_MINIMAX_MODEL
    telegram_bot_token: str = ""
    allowed_chat_id: str = ""
    telegram_agent_name: str = ""
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    mcp_server_url: str = "http://mcp-server:3100"
    mcp_auth_token: str = ""
    hermes_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    postgres_host: str = "host.docker.internal"
    postgres_port: int = 5432
    postgres_db: str = "hermes"
    postgres_user: str = "younes"
    postgres_password: str = ""
    upload_dir: str = "/data/uploads"
    max_upload_bytes: int = 20 * 1024 * 1024
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    web_search_url: str = "https://html.duckduckgo.com/html/"
    web_fetch_max_bytes: int = 2 * 1024 * 1024


settings = Settings()

app = FastAPI(
    title="Hermes Daemon",
    description="Backend d'orchestration multi-agents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.hermes_allowed_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modèles de données
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = Field(..., description="role: system, user, ou assistant")
    content: str = Field(..., description="Contenu du message")
    reasoning_details: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Raisonnement MiniMax conservé pour la continuité des échanges",
    )
    attachments: Optional[List["Attachment"]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class Attachment(BaseModel):
    id: str = Field(..., pattern=r"^[a-f0-9]{32}$")
    name: str = Field(..., min_length=1, max_length=180)
    mime_type: str = "application/octet-stream"
    size: int = Field(default=0, ge=0)
    extracted: bool = False


ChatMessage.model_rebuild()


class ConversationMessage(ChatMessage):
    time: str = "maintenant"


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Historique de conversation")
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: Optional[List[Dict[str, Any]]] = None
    tool_names: Optional[List[str]] = None
    context_tokens: int = Field(default=200_000, ge=8_192, le=1_000_000)
    agent_name: Optional[str] = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    agent_name: Optional[str] = None
    reasoning_details: Optional[List[Dict[str, Any]]] = None
    tool_events: List[Dict[str, Any]] = Field(default_factory=list)


def _normalise_usage(raw_usage: Any) -> Dict[str, int]:
    """Garde uniquement les compteurs numériques compatibles avec l'API Hermes.

    Certains fournisseurs compatibles OpenAI ajoutent des détails imbriqués,
    par exemple ``completion_tokens_details``. Ils ne correspondent pas au
    contrat ``Dict[str, int]`` exposé par Hermes et ne doivent pas faire
    échouer une réponse pourtant valide.
    """
    defaults = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if not isinstance(raw_usage, dict):
        return defaults

    usage = {
        key: value
        for key, value in raw_usage.items()
        if isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool)
    }
    return {**defaults, **usage}


def _trim_messages(messages: List[ChatMessage], context_tokens: int) -> List[ChatMessage]:
    """Garde les derniers messages dans la fenêtre choisie par la conversation.

    MiniMax ne demande pas un paramètre de fenêtre séparé : la limite est
    appliquée ici avant l’envoi, avec une estimation prudente de 4 caractères
    par token.
    """
    max_chars = max(32_768, context_tokens * 4)
    total_chars = 0
    kept: List[ChatMessage] = []
    for message in reversed(messages):
        message_chars = len(message.content)
        if kept and total_chars + message_chars > max_chars:
            break
        kept.append(message)
        total_chars += message_chars
    return list(reversed(kept))


TEXT_ATTACHMENT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".log", ".yaml", ".yml", ".xml", ".html", ".css", ".js", ".ts", ".py", ".sql"}
ALLOWED_ATTACHMENT_EXTENSIONS = TEXT_ATTACHMENT_EXTENSIONS | {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
MAX_ATTACHMENT_CONTEXT_CHARS = 120_000


def _attachment_path(attachment_id: str) -> Optional[Path]:
    if not re.fullmatch(r"[a-f0-9]{32}", attachment_id):
        return None
    root = Path(settings.upload_dir)
    matches = list(root.glob(f"*/{attachment_id}.*"))
    return matches[0] if matches else None


def _extract_attachment_text(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_ATTACHMENT_EXTENSIONS:
            return path.read_text(encoding="utf-8", errors="replace")[:MAX_ATTACHMENT_CONTEXT_CHARS]
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)[:MAX_ATTACHMENT_CONTEXT_CHARS]
        if suffix == ".docx":
            document = Document(str(path))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)[:MAX_ATTACHMENT_CONTEXT_CHARS]
    except Exception:
        LOGGER.exception("Impossible d’extraire le contenu de la pièce jointe %s", path.name)
    return ""


def _attachment_context(attachments: Optional[List[Attachment]]) -> str:
    if not attachments:
        return ""
    sections: List[str] = []
    for attachment in attachments:
        path = _attachment_path(attachment.id)
        if not path:
            sections.append(f"[Pièce jointe indisponible : {attachment.name}]")
            continue
        text = _extract_attachment_text(path)
        if text.strip():
            sections.append(f"[Contenu de la pièce jointe {attachment.name}]\n{text}")
        else:
            sections.append(f"[Pièce jointe {attachment.name} reçue, mais son contenu binaire n’est pas extrait automatiquement]")
    return "\n\n".join(sections)


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Nom du tool à appeler")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class N8nWebhookRequest(BaseModel):
    webhook_path: str = Field(..., description="Chemin du webhook n8n (ex: /my-flow)")
    method: str = "POST"
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    system_prompt: str
    description: str = Field(default="", max_length=240)
    model: Optional[str] = Field(default=None, max_length=120)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=256, le=16000)
    tools: List[str] = Field(default_factory=list)


class ConversationRecord(BaseModel):
    id: str
    title: str = "Nouvelle conversation"
    agent_name: Optional[str] = None
    model: Optional[str] = None
    tool_names: List[str] = Field(default_factory=list)
    context_tokens: int = Field(default=200_000, ge=8_192, le=1_000_000)
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationCreate(BaseModel):
    title: str = "Nouvelle conversation"
    agent_name: Optional[str] = None
    model: Optional[str] = None
    tool_names: List[str] = Field(default_factory=list)
    context_tokens: int = Field(default=200_000, ge=8_192, le=1_000_000)


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    agent_name: Optional[str] = None
    model: Optional[str] = None
    tool_names: Optional[List[str]] = None
    context_tokens: Optional[int] = Field(default=None, ge=8_192, le=1_000_000)
    messages: Optional[List[ConversationMessage]] = None


class SettingsUpdate(BaseModel):
    """Mise à jour des clés API (sécurisée côté serveur)."""
    minimax_api_key: Optional[str] = None
    minimax_base_url: Optional[str] = None
    minimax_model: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    allowed_chat_id: Optional[str] = None
    telegram_agent_name: Optional[str] = None
    github_token: Optional[str] = None

    @field_validator("*")
    @classmethod
    def reject_env_file_injection(cls, value: Optional[str]) -> Optional[str]:
        """Empêche une valeur de paramètre de créer des lignes .env supplémentaires."""
        if value is not None and ("\n" in value or "\r" in value):
            raise ValueError("Les paramètres ne peuvent pas contenir de retour à la ligne.")
        return value

    @field_validator("allowed_chat_id")
    @classmethod
    def validate_allowed_chat_id(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value.strip() and not re.fullmatch(r"-?\d{1,20}", value.strip()):
            raise ValueError("L’identifiant de chat Telegram doit être numérique.")
        return value.strip() if value is not None else value


class SettingsStatus(BaseModel):
    """État des clés configurées (renvoie juste présence, jamais la valeur)."""
    minimax_configured: bool
    telegram_configured: bool
    telegram_chat_configured: bool
    telegram_running: bool
    telegram_bot_username: Optional[str] = None
    telegram_last_error: Optional[str] = None
    telegram_agent_name: Optional[str] = None
    github_configured: bool
    model: str
    minimax_base_url: str
    mcp_ready: bool


# ---------------------------------------------------------------------------
# Auth (JWT simple)
# ---------------------------------------------------------------------------
def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Vérifie le secret de service sans jamais échouer ouvertement en production."""
    if not settings.hermes_jwt_secret:
        if settings.hermes_env.lower() in {"dev", "development", "test"}:
            return True
        raise HTTPException(status_code=503, detail="Authentification Hermes non configurée")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ", 1)[1]
    if not secrets.compare_digest(token, settings.hermes_jwt_secret):
        raise HTTPException(status_code=403, detail="Token invalide")
    return True


# ---------------------------------------------------------------------------
# Endpoints de santé
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "hermes-daemon",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {"message": "Hermes Daemon API", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Endpoints Chat (Minimax via OpenAI-compatible API)
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _: bool = Depends(verify_token)):
    """Envoie une conversation à MiniMax avec exécution réelle des outils autorisés."""
    api_key, base_url, configured_model = _get_minimax_config()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="MiniMax n’est pas configuré. Ajoutez une clé API valide dans Configuration.",
        )

    messages: List[Dict[str, Any]] = []
    for message in _trim_messages(req.messages, req.context_tokens):
        content = message.content
        attachment_context = _attachment_context(message.attachments)
        if attachment_context:
            content = f"{content}\n\n{attachment_context}".strip()
        provider_message: Dict[str, Any] = {"role": message.role, "content": content}
        if message.role == "assistant" and message.reasoning_details:
            provider_message["reasoning_details"] = message.reasoning_details
        if message.tool_calls:
            provider_message["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            provider_message["tool_call_id"] = message.tool_call_id
        if message.name:
            provider_message["name"] = message.name
        messages.append(provider_message)
    selected_agent: Optional[AgentConfig] = None
    effective_tool_names: List[str] = []
    if req.agent_name:
        selected_agent = AGENTS.get(req.agent_name)
        if not selected_agent:
            raise HTTPException(status_code=404, detail="Agent introuvable. Rechargez la liste des agents.")
        system_prompt = selected_agent.system_prompt.strip()
        effective_tool_names = req.tool_names if req.tool_names is not None else selected_agent.tools
        unknown_tools = sorted(set(effective_tool_names) - set(TOOL_REGISTRY))
        if unknown_tools:
            raise HTTPException(status_code=400, detail=f"Outils inconnus: {', '.join(unknown_tools)}")
        if effective_tool_names:
            system_prompt += f"\n\nOutils autorisés pour cette mission : {', '.join(effective_tool_names)}."
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
    elif req.tool_names:
        effective_tool_names = req.tool_names
        unknown_tools = sorted(set(req.tool_names) - set(TOOL_REGISTRY))
        if unknown_tools:
            raise HTTPException(status_code=400, detail=f"Outils inconnus: {', '.join(unknown_tools)}")
        messages.insert(0, {"role": "system", "content": f"Outils autorisés pour cette conversation : {', '.join(req.tool_names)}."})

    model = req.model or (selected_agent.model if selected_agent and selected_agent.model else None) or configured_model
    provider_tools = [
        {"type": "function", "function": {"name": name, "description": TOOL_REGISTRY[name]["description"], "parameters": TOOL_REGISTRY[name]["parameters"]}}
        for name in effective_tool_names
    ]
    tool_events: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            for _ in range(5):
                payload: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": selected_agent.temperature if selected_agent else req.temperature,
                    "max_completion_tokens": selected_agent.max_tokens if selected_agent else req.max_tokens,
                    "reasoning_split": True,
                }
                if provider_tools:
                    payload["tools"] = provider_tools
                    payload["tool_choice"] = "auto"
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                choice = data["choices"][0]
                response_message = choice.get("message", {})
                tool_calls = response_message.get("tool_calls") or []
                if tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": response_message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                    if response_message.get("reasoning_details"):
                        assistant_message["reasoning_details"] = response_message["reasoning_details"]
                    messages.append(assistant_message)
                    for call in tool_calls:
                        function = call.get("function") or {}
                        tool_name = str(function.get("name") or "")
                        raw_arguments = function.get("arguments") or {}
                        try:
                            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                        except json.JSONDecodeError:
                            arguments = {}
                        if tool_name not in effective_tool_names:
                            result: Dict[str, Any] = {"error": "Cet outil n’est pas autorisé pour cette conversation."}
                        else:
                            result = await _execute_tool(tool_name, arguments if isinstance(arguments, dict) else {})
                        tool_events.append({"tool": tool_name, "status": "error" if "error" in result else "success"})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.get("id") or uuid4().hex,
                            "name": tool_name,
                            "content": json.dumps(result, ensure_ascii=False, default=str)[:120_000],
                        })
                    continue
                content = response_message.get("content")
                if not content:
                    raise HTTPException(status_code=502, detail="MiniMax a renvoyé une réponse vide.")
                reasoning_details = response_message.get("reasoning_details")
                return ChatResponse(
                    content=content,
                    model=data.get("model", model),
                    usage=_normalise_usage(data.get("usage")),
                    finish_reason=choice.get("finish_reason", "stop"),
                    agent_name=selected_agent.name if selected_agent else None,
                    reasoning_details=reasoning_details if isinstance(reasoning_details, list) else None,
                    tool_events=tool_events,
                )
            raise HTTPException(status_code=502, detail="MiniMax n’a pas produit de réponse finale après les appels d’outils.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax a refusé la clé API. Remplacez-la dans Configuration avec une clé créée sur la plateforme MiniMax.",
                ) from e
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=502,
                    detail=f"MiniMax ne trouve pas le modèle ou l’endpoint demandé ({model}). Vérifiez la configuration.",
                ) from e
            if e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="MiniMax limite temporairement les requêtes. Réessayez dans un instant.") from e
            raise HTTPException(status_code=502, detail=f"MiniMax a renvoyé HTTP {e.response.status_code}.") from e
        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail="MiniMax met trop de temps à répondre. Réessayez.") from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur Minimax: {e}")


# ---------------------------------------------------------------------------
# Streaming SSE (ChatGPT-style token-by-token with tool calls)
# ---------------------------------------------------------------------------
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, _: bool = Depends(verify_token)):
    """Envoie une conversation à MiniMax en streaming SSE, avec outils."""
    from fastapi import Request
    api_key, base_url, configured_model = _get_minimax_config()
    if not api_key:
        raise HTTPException(status_code=503, detail="MiniMax n'est pas configuré.")

    # Préparation des messages (identique à /api/chat)
    messages: List[Dict[str, Any]] = []
    for message in _trim_messages(req.messages, req.context_tokens):
        content = message.content
        attachment_context = _attachment_context(message.attachments)
        if attachment_context:
            content = f"{content}\n\n{attachment_context}".strip()
        provider_message: Dict[str, Any] = {"role": message.role, "content": content}
        if message.role == "assistant" and message.reasoning_details:
            provider_message["reasoning_details"] = message.reasoning_details
        if message.tool_calls:
            provider_message["tool_calls"] = message.tool_calls
        if message.tool_call_id:
            provider_message["tool_call_id"] = message.tool_call_id
        if message.name:
            provider_message["name"] = message.name
        messages.append(provider_message)

    selected_agent: Optional[AgentConfig] = None
    effective_tool_names: List[str] = []
    if req.agent_name:
        selected_agent = AGENTS.get(req.agent_name)
        if not selected_agent:
            raise HTTPException(status_code=404, detail="Agent introuvable.")
        system_prompt = selected_agent.system_prompt.strip()
        effective_tool_names = req.tool_names if req.tool_names is not None else selected_agent.tools
        if effective_tool_names:
            system_prompt += f"\n\nOutils autorisés pour cette mission : {', '.join(effective_tool_names)}."
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
    elif req.tool_names:
        effective_tool_names = req.tool_names
        messages.insert(0, {"role": "system", "content": f"Outils autorisés pour cette conversation : {', '.join(req.tool_names)}."})

    model = req.model or (selected_agent.model if selected_agent and selected_agent.model else None) or configured_model
    provider_tools = [
        {"type": "function", "function": {"name": name, "description": TOOL_REGISTRY[name]["description"], "parameters": TOOL_REGISTRY[name]["parameters"]}}
        for name in effective_tool_names
    ]

    async def generate():
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                for iteration in range(5):
                    payload: Dict[str, Any] = {
                        "model": model,
                        "messages": messages,
                        "temperature": selected_agent.temperature if selected_agent else req.temperature,
                        "max_completion_tokens": selected_agent.max_tokens if selected_agent else req.max_tokens,
                        "reasoning_split": True,
                        "stream": True,  # ← la clé : demande SSE à MiniMax
                    }
                    if provider_tools:
                        payload["tools"] = provider_tools
                        payload["tool_choice"] = "auto"

                    tool_calls_buffer: List[Dict[str, Any]] = []
                    assistant_content_parts: List[str] = []
                    finish_reason: Optional[str] = None
                    final_model: Optional[str] = None

                    async with client.stream(
                        "POST",
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        async for raw_line in response.aiter_lines():
                            line = raw_line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            finish_reason = choices[0].get("finish_reason") or finish_reason
                            final_model = chunk.get("model") or final_model

                            # Tool calls (streamés en fragments)
                            tool_deltas = delta.get("tool_calls") or []
                            for td in tool_deltas:
                                idx = td.get("index", 0)
                                while len(tool_calls_buffer) <= idx:
                                    tool_calls_buffer.append({"id": "", "function": {"name": "", "arguments": ""}})
                                if "id" in td and td["id"]:
                                    tool_calls_buffer[idx]["id"] = td["id"]
                                fn = td.get("function") or {}
                                if "name" in fn and fn["name"]:
                                    tool_calls_buffer[idx]["function"]["name"] = fn["name"]
                                if "arguments" in fn and fn["arguments"]:
                                    tool_calls_buffer[idx]["function"]["arguments"] += fn["arguments"]

                            # Contenu
                            content_delta = delta.get("content") or ""
                            if content_delta:
                                assistant_content_parts.append(content_delta)
                                yield f"data: {json.dumps({'event': 'delta', 'content': content_delta}, ensure_ascii=False)}\n\n"

                            # Reasoning (streamé)
                            reasoning = delta.get("reasoning_details") or None
                            if reasoning:
                                yield f"data: {json.dumps({'event': 'reasoning', 'details': reasoning}, ensure_ascii=False)}\n\n"

                    # Fin du stream MiniMax
                    if tool_calls_buffer:
                        # Un ou plusieurs tool calls ont été détectés
                        yield f"data: {json.dumps({'event': 'tool_calls_detected', 'count': len(tool_calls_buffer)}, ensure_ascii=False)}\n\n"
                        assistant_message = {
                            "role": "assistant",
                            "content": "".join(assistant_content_parts),
                            "tool_calls": tool_calls_buffer,
                        }
                        messages.append(assistant_message)
                        for call in tool_calls_buffer:
                            fn = call.get("function") or {}
                            tool_name = str(fn.get("name") or "")
                            raw_args = fn.get("arguments") or "{}"
                            try:
                                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                            except json.JSONDecodeError:
                                arguments = {}
                            yield f"data: {json.dumps({'event': 'tool_call', 'tool': tool_name, 'args': arguments}, ensure_ascii=False, default=str)}\n\n"
                            if tool_name not in effective_tool_names:
                                result = {"error": "Outil non autorisé pour cette conversation."}
                            else:
                                result = await _execute_tool(tool_name, arguments if isinstance(arguments, dict) else {})
                            yield f"data: {json.dumps({'event': 'tool_result', 'tool': tool_name, 'status': 'error' if 'error' in result else 'success', 'result': result}, ensure_ascii=False, default=str)}\n\n"
                            messages.append({
                                "role": "tool",
                                "tool_call_id": call.get("id") or uuid4().hex,
                                "name": tool_name,
                                "content": json.dumps(result, ensure_ascii=False, default=str)[:120_000],
                            })
                        # Continuer la boucle — le modèle va répondre après les tool results
                        continue
                    else:
                        # Réponse finale (sans tool calls)
                        content = "".join(assistant_content_parts)
                        if not content:
                            yield f"data: {json.dumps({'event': 'error', 'message': 'MiniMax a renvoyé une réponse vide.'}, ensure_ascii=False)}\n\n"
                            return
                        yield f'data: {json.dumps({"event": "done", "content": content, "model": final_model or model, "finish_reason": finish_reason or "stop"}, ensure_ascii=False)}\n\n'
                        return

                # Épuisé les 5 itérations
                yield f'data: {json.dumps({"event": "error", "message": "MiniMax n\'a pas produit de réponse finale après les appels d\'outils."}, ensure_ascii=False)}\n\n'
            except httpx.HTTPStatusError as e:
                detail = "MiniMax a refusé la requête."
                if e.response.status_code == 401:
                    detail = "Clé API MiniMax rejetée."
                elif e.response.status_code == 429:
                    detail = "Limite de requêtes MiniMax atteinte."
                yield f"data: {json.dumps({'event': 'error', 'message': detail}, ensure_ascii=False)}\n\n"
            except Exception as e:
                LOGGER.exception("Erreur streaming")
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


# ---------------------------------------------------------------------------
# Telegram — bridge de conversation sécurisé (long polling)
# ---------------------------------------------------------------------------
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
TELEGRAM_POLL_TIMEOUT_SECONDS = 25
TELEGRAM_REPLY_LIMIT = 4000
TELEGRAM_HISTORY_LIMIT = 512
LOGGER = logging.getLogger("hermes.telegram")

TELEGRAM_STATE: Dict[str, Any] = {
    "running": False,
    "bot_username": None,
    "last_error": None,
}
TELEGRAM_HISTORIES: Dict[str, List[ChatMessage]] = {}
TELEGRAM_UNAUTHORIZED_NOTICES: Dict[str, float] = {}


class TelegramAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _get_telegram_config() -> Tuple[str, str]:
    """Retourne le token et le chat autorisé, avec priorité aux réglages persistants."""
    persisted = _read_env_file()
    token = _usable_value(persisted.get("TELEGRAM_BOT_TOKEN")) or _usable_value(settings.telegram_bot_token)
    allowed_chat_id = _usable_value(persisted.get("ALLOWED_CHAT_ID")) or _usable_value(settings.allowed_chat_id)
    return token, allowed_chat_id


def _get_telegram_agent_name() -> str:
    persisted = _read_env_file()
    return _usable_value(persisted.get("TELEGRAM_AGENT_NAME")) or _usable_value(settings.telegram_agent_name)


async def _telegram_api(token: str, method: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 35.0) -> Any:
    """Appelle Telegram sans jamais inclure le token dans les erreurs ou les logs."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(f"{TELEGRAM_API_BASE_URL}/bot{token}/{method}", json=payload or {})
            try:
                data = response.json()
            except ValueError as exc:
                raise TelegramAPIError(response.status_code, "Telegram a renvoyé une réponse invalide.") from exc
        except httpx.TimeoutException as exc:
            raise TelegramAPIError(504, "Telegram ne répond pas dans le délai imparti.") from exc
        except httpx.HTTPError as exc:
            raise TelegramAPIError(502, "Impossible de joindre Telegram.") from exc

    if not response.is_success or not data.get("ok"):
        detail = str(data.get("description") or "Telegram a refusé la requête.")
        raise TelegramAPIError(response.status_code, detail)
    return data.get("result")


def _telegram_chunks(text: str) -> List[str]:
    """Découpe un texte pour respecter la limite de 4096 caractères de Telegram."""
    text = text.strip()
    if not text:
        return ["Hermes n’a pas produit de texte exploitable."]
    return [text[index:index + TELEGRAM_REPLY_LIMIT] for index in range(0, len(text), TELEGRAM_REPLY_LIMIT)]


async def _send_telegram_message(token: str, chat_id: str, text: str, message_thread_id: Optional[int] = None) -> None:
    for chunk in _telegram_chunks(text):
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": chunk}
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        await _telegram_api(token, "sendMessage", payload, timeout=15.0)


async def _handle_telegram_message(token: str, allowed_chat_id: str, message: Dict[str, Any], telegram_agent_name: str = "") -> None:
    telegram_chat = message.get("chat") or {}
    chat_id = str(telegram_chat.get("id") or "")
    text = str(message.get("text") or "").strip()
    message_thread_id = message.get("message_thread_id")
    if not chat_id or not text:
        return

    if not allowed_chat_id or chat_id != allowed_chat_id:
        # Une réponse espacée permet au propriétaire de récupérer son ID sans
        # transformer le bot public en passerelle vers MiniMax.
        last_notice = TELEGRAM_UNAUTHORIZED_NOTICES.get(chat_id, 0)
        if time.monotonic() - last_notice >= 60:
            TELEGRAM_UNAUTHORIZED_NOTICES[chat_id] = time.monotonic()
            await _send_telegram_message(
                token,
                chat_id,
                "🔒 Hermes est connecté, mais ce chat n’est pas encore autorisé.\n\n"
                f"Votre Telegram Chat ID : {chat_id}\n\n"
                "Copiez cet ID dans Hermes Studio → Configuration → Telegram Chat ID autorisé, "
                "puis envoyez à nouveau votre message.",
                message_thread_id if isinstance(message_thread_id, int) else None,
            )
        return

    if text.lower().startswith("/start"):
        await _send_telegram_message(
            token,
            chat_id,
            "✨ Hermes est prêt. Envoyez-moi une question ou utilisez /reset pour effacer le contexte de cette conversation.",
            message_thread_id if isinstance(message_thread_id, int) else None,
        )
        return

    if text.lower().startswith("/reset"):
        TELEGRAM_HISTORIES.pop(chat_id, None)
        await _send_telegram_message(
            token,
            chat_id,
            "Le contexte Telegram a été effacé.",
            message_thread_id if isinstance(message_thread_id, int) else None,
        )
        return

    history = TELEGRAM_HISTORIES.setdefault(chat_id, [])
    history.append(ChatMessage(role="user", content=text[:8000]))
    try:
        await _telegram_api(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"}, timeout=10.0)
        telegram_agent = AGENTS.get(telegram_agent_name) if telegram_agent_name else None
        telegram_model = (telegram_agent.model if telegram_agent and telegram_agent.model else _get_minimax_config()[2]).lower()
        telegram_context_tokens = 1_000_000 if "m3" in telegram_model else 200_000
        telegram_tools = telegram_agent.tools if telegram_agent else ["web_search", "web_fetch", "server_diagnostics", "mcp_terminal"]
        response = await chat(
            ChatRequest(
                messages=history,
                agent_name=telegram_agent_name or None,
                tool_names=telegram_tools,
                temperature=0.7,
                max_tokens=1200,
                context_tokens=telegram_context_tokens,
            ),
            True,
        )
    except HTTPException as exc:
        history.pop()
        LOGGER.warning("Telegram: Hermes n’a pas répondu (%s)", exc.status_code)
        if exc.status_code == 503:
            reply = "MiniMax n’est pas encore configuré dans Hermes. Ajoutez ou testez la clé dans Studio."
        else:
            reply = "Hermes ne peut pas répondre pour le moment. Réessayez dans un instant."
        await _send_telegram_message(token, chat_id, reply, message_thread_id if isinstance(message_thread_id, int) else None)
        return
    except Exception:
        history.pop()
        LOGGER.exception("Telegram: erreur de traitement du message")
        await _send_telegram_message(
            token,
            chat_id,
            "Hermes a rencontré une erreur temporaire. Réessayez dans un instant.",
            message_thread_id if isinstance(message_thread_id, int) else None,
        )
        return

    history.append(ChatMessage(role="assistant", content=response.content, reasoning_details=response.reasoning_details))
    if len(history) > TELEGRAM_HISTORY_LIMIT:
        del history[:-TELEGRAM_HISTORY_LIMIT]
    await _send_telegram_message(token, chat_id, response.content, message_thread_id if isinstance(message_thread_id, int) else None)


async def _telegram_polling_loop() -> None:
    """Récupère les messages Telegram par long polling, sans webhook public supplémentaire."""
    offset: Optional[int] = None
    active_token = ""
    while True:
        token, allowed_chat_id = _get_telegram_config()
        telegram_agent_name = _get_telegram_agent_name()
        if not token:
            TELEGRAM_STATE.update({"running": False, "bot_username": None, "last_error": None})
            active_token = ""
            offset = None
            await asyncio.sleep(5)
            continue

        if token != active_token:
            active_token = token
            offset = None
            TELEGRAM_HISTORIES.clear()
            TELEGRAM_UNAUTHORIZED_NOTICES.clear()
            try:
                bot = await _telegram_api(token, "getMe", timeout=12.0)
                TELEGRAM_STATE.update({
                    "running": True,
                    "bot_username": (bot or {}).get("username"),
                    "last_error": None,
                })
            except TelegramAPIError as exc:
                TELEGRAM_STATE.update({"running": False, "bot_username": None, "last_error": exc.detail})
                LOGGER.warning("Telegram: token ou connexion invalide (%s)", exc.status_code)
                await asyncio.sleep(15)
                continue

        payload: Dict[str, Any] = {
            "timeout": TELEGRAM_POLL_TIMEOUT_SECONDS,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset

        try:
            updates = await _telegram_api(token, "getUpdates", payload, timeout=TELEGRAM_POLL_TIMEOUT_SECONDS + 10)
            TELEGRAM_STATE.update({"running": True, "last_error": None})
            for update in updates if isinstance(updates, list) else []:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                message = update.get("message")
                if isinstance(message, dict):
                    await _handle_telegram_message(token, allowed_chat_id, message, telegram_agent_name)
        except asyncio.CancelledError:
            raise
        except TelegramAPIError as exc:
            if exc.status_code == 409:
                detail = "Un webhook Telegram est configuré. Supprimez-le avant d’utiliser le polling Hermes."
            else:
                detail = exc.detail
            TELEGRAM_STATE.update({"running": False, "last_error": detail})
            LOGGER.warning("Telegram polling interrompu (%s)", exc.status_code)
            await asyncio.sleep(10)
        except Exception:
            TELEGRAM_STATE.update({"running": False, "last_error": "Erreur interne du bridge Telegram."})
            LOGGER.exception("Telegram polling: erreur inattendue")
            await asyncio.sleep(10)


@app.on_event("startup")
async def start_telegram_bridge() -> None:
    app.state.telegram_task = asyncio.create_task(_telegram_polling_loop(), name="hermes-telegram-polling")


@app.on_event("shutdown")
async def stop_telegram_bridge() -> None:
    task = getattr(app.state, "telegram_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# Endpoints Tools (registre + exécution)
# ---------------------------------------------------------------------------

WEB_USER_AGENT = "HermesWorkspace/1.0 (+https://hermes.eaumalik.com)"
WEB_MAX_REDIRECTS = 3
WEB_MAX_TEXT_CHARS = 120_000
BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}


class _WebTextParser(HTMLParser):
    """Transforme une page HTML en texte lisible sans exécuter son contenu."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: List[str] = []
        self._in_title = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in {"p", "div", "li", "br", "h1", "h2", "h3", "section", "article"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "template", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in {"p", "div", "li", "br", "h1", "h2", "h3", "section", "article"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += f" {data}"
        if not self._ignored_depth:
            self.parts.append(data)


class _SearchResultParser(HTMLParser):
    """Parseur volontairement limité aux résultats DuckDuckGo publics."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: List[Dict[str, str]] = []
        self._current: Optional[Dict[str, str]] = None
        self._capture: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if tag == "div" and "result__snippet" in classes and self._current:
            self._capture = "snippet"
            return
        if tag != "a":
            return
        if "result__a" in classes:
            if self._current and self._current.get("url"):
                self.results.append(self._current)
            self._current = {"title": "", "url": self._decode_result_url(attr.get("href") or ""), "snippet": ""}
            self._capture = "title"
        elif "result__url" in classes and self._current:
            self._capture = "url"

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture in {"title", "url"}:
            self._capture = None
        elif tag == "div" and self._capture == "snippet":
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current and self._capture in {"title", "url"}:
            self._current[self._capture] += data
        elif self._current and self._capture == "snippet":
            self._current["snippet"] += data

    def close(self) -> None:
        super().close()
        if self._current and self._current.get("url"):
            self.results.append(self._current)
            self._current = None

    @staticmethod
    def _decode_result_url(raw_url: str) -> str:
        parsed = urlparse(unescape(raw_url))
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target or raw_url)


def _public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def _validate_public_url(url: str) -> str:
    """Bloque les schémas dangereux et les cibles privées avant toute requête."""
    candidate = str(url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL publique HTTP/HTTPS obligatoire.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in BLOCKED_HOSTNAMES:
        raise ValueError("Cette destination est bloquée pour des raisons de sécurité.")
    try:
        direct_ip = ipaddress.ip_address(hostname)
        addresses = [str(direct_ip)]
    except ValueError:
        try:
            addresses = list({info[4][0] for info in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)})
        except socket.gaierror as exc:
            raise ValueError("Impossible de résoudre le domaine demandé.") from exc
    if not addresses or not all(_public_ip(address) for address in addresses):
        raise ValueError("Les adresses privées ou internes ne sont pas accessibles par Hermes.")
    return candidate


def _plain_text_from_html(raw_html: str) -> Tuple[str, str]:
    parser = _WebTextParser()
    parser.feed(raw_html)
    parser.close()
    text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return re.sub(r"\s+", " ", parser.title).strip(), text[:WEB_MAX_TEXT_CHARS]


async def _call_web_search(args: Dict[str, Any]) -> Dict[str, Any]:
    query = re.sub(r"\s+", " ", str(args.get("query") or "").strip())[:240]
    if len(query) < 2:
        return {"error": "Une recherche d’au moins deux caractères est nécessaire."}
    max_results = min(max(int(args.get("max_results") or 8), 1), 10)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.post(
            settings.web_search_url,
            data={"q": query, "kl": "wt-wt"},
            headers={"User-Agent": WEB_USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )
    response.raise_for_status()
    parser = _SearchResultParser()
    parser.feed(response.text)
    parser.close()
    results = []
    for item in parser.results[:max_results]:
        results.append({
            "title": re.sub(r"\s+", " ", unescape(item.get("title", ""))).strip(),
            "url": item.get("url", "").strip(),
            "snippet": re.sub(r"\s+", " ", unescape(item.get("snippet", ""))).strip(),
        })
    return {"query": query, "source": "DuckDuckGo", "results": results}


async def _call_web_fetch(args: Dict[str, Any]) -> Dict[str, Any]:
    current_url = _validate_public_url(str(args.get("url") or ""))
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=False) as client:
        for _ in range(WEB_MAX_REDIRECTS + 1):
            async with client.stream("GET", current_url, headers={"User-Agent": WEB_USER_AGENT, "Accept": "text/html,text/plain,application/json"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirection sans destination.")
                    current_url = _validate_public_url(str(httpx.URL(current_url).join(location)))
                    continue
                response.raise_for_status()
                content_length = int(response.headers.get("content-length") or 0)
                if content_length and content_length > settings.web_fetch_max_bytes:
                    raise ValueError("La page est trop volumineuse pour une analyse sûre.")
                chunks: List[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > settings.web_fetch_max_bytes:
                        raise ValueError("La page dépasse la taille maximale autorisée.")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                content_type = response.headers.get("content-type", "").lower()
                if "html" in content_type:
                    title, text = _plain_text_from_html(raw.decode(response.encoding or "utf-8", errors="replace"))
                elif "text/" in content_type or "json" in content_type or "xml" in content_type:
                    title, text = "", raw.decode(response.encoding or "utf-8", errors="replace")[:WEB_MAX_TEXT_CHARS]
                else:
                    return {"url": current_url, "status_code": response.status_code, "content_type": content_type, "text": "Contenu non textuel non extrait par Hermes."}
                return {"url": current_url, "status_code": response.status_code, "content_type": content_type, "title": title, "text": text}
        raise ValueError("Trop de redirections.")


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "n8n_webhook": {
        "name": "n8n_webhook",
        "description": "Délègue une tâche à un workflow n8n via webhook",
        "parameters": {
            "type": "object",
            "properties": {
                "webhook_path": {"type": "string", "description": "Chemin du webhook n8n"},
                "method": {"type": "string", "enum": ["GET", "POST"], "default": "POST"},
                "payload": {"type": "object", "description": "Corps de la requête"},
                "confirmed": {"type": "boolean", "description": "Doit être true après confirmation explicite de l’utilisateur"},
            },
            "required": ["webhook_path"],
        },
    },
    "mcp_filesystem": {
        "name": "mcp_filesystem",
        "description": "Lit/écrit dans le système de fichiers via MCP",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["read", "write", "list", "delete"]},
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Requis pour write"},
                "confirmed": {"type": "boolean", "description": "Doit être true après confirmation explicite pour write/delete"},
            },
            "required": ["operation", "path"],
        },
    },
    "mcp_github": {
        "name": "mcp_github",
        "description": "Opérations GitHub via MCP",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["list_repos", "read_file", "create_pr", "search_code"]},
                "repo": {"type": "string"},
                "path": {"type": "string"},
                "branch": {"type": "string"},
                "confirmed": {"type": "boolean", "description": "Doit être true après confirmation explicite pour create_pr"},
            },
            "required": ["operation"],
        },
    },
    "server_diagnostics": {
        "name": "server_diagnostics",
        "description": "Analyse en lecture seule de l’état du daemon Hermes et de ses services autorisés",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["health", "system", "disk", "services"]},
            },
            "required": ["operation"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Recherche des informations récentes sur Internet et renvoie des sources avec liens",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Question ou sujet à rechercher sur Internet"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 8},
            },
            "required": ["query"],
        },
    },
    "web_fetch": {
        "name": "web_fetch",
        "description": "Lit une page web publique pour en extraire le contenu textuel et l’analyser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL publique HTTP ou HTTPS"},
            },
            "required": ["url"],
        },
    },
    "mcp_terminal": {
        "name": "mcp_terminal",
        "description": "Exécute une commande contrôlée dans le workspace Hermes pour diagnostiquer le projet et lancer des scripts autorisés",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": ["ls", "find", "cat", "head", "tail", "grep", "rg", "df", "du", "ps", "python3", "node", "npm", "git", "curl", "wget", "bash", "sh"]},
                "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments séparés, sans shell inline"},
                "cwd": {"type": "string", "default": ".", "description": "Sous-dossier relatif à /workspace"},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120, "default": 30},
                "confirmed": {"type": "boolean", "description": "Obligatoire pour scripts, réseau ou commandes potentiellement mutantes"},
            },
            "required": ["command"],
        },
    },
    "google_gmail": {
        "name": "google_gmail",
        "description": "Recherche et lecture d’emails Gmail avec le compte Google connecté",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["search", "read"]},
                "query": {"type": "string"},
                "message_id": {"type": "string"},
            },
            "required": ["operation"],
        },
    },
    "google_calendar": {
        "name": "google_calendar",
        "description": "Consulte l’agenda Google et prépare des événements",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["list", "create"]},
                "calendar_id": {"type": "string", "default": "primary"},
                "time_min": {"type": "string"},
                "time_max": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "confirmed": {"type": "boolean", "description": "Doit être true après confirmation explicite pour créer un événement"},
            },
            "required": ["operation"],
        },
    },
    "google_drive": {
        "name": "google_drive",
        "description": "Recherche et lecture de fichiers Google Drive accessibles au compte connecté",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["search", "read"]},
                "query": {"type": "string"},
                "file_id": {"type": "string"},
            },
            "required": ["operation"],
        },
    },
}


@app.get("/api/tools")
async def list_tools(_: bool = Depends(verify_token)):
    """Liste tous les tools disponibles."""
    return {"tools": list(TOOL_REGISTRY.values())}


@app.post("/api/tools/call")
async def call_tool(req: ToolCallRequest, _: bool = Depends(verify_token)):
    """Exécute un tool par son nom."""
    if req.tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool inconnu: {req.tool_name}")
    return await _execute_tool(req.tool_name, req.arguments)


async def _call_n8n_webhook(args: Dict[str, Any]):
    """Appelle un webhook n8n."""
    webhook_path = args.get("webhook_path", "").lstrip("/")
    method = args.get("method", "POST").upper()
    payload = args.get("payload", {})
    headers = args.get("headers", {})

    url = f"{settings.n8n_webhook_base_url.rstrip('/')}/{webhook_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                resp = await client.get(url, params=payload, headers=headers)
            else:
                resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return {"status": "success", "status_code": resp.status_code, "data": resp.json()}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur n8n: {e}")


async def _call_mcp(tool_name: str, args: Dict[str, Any]):
    """Appelle le serveur MCP via son API HTTP."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            headers = {"Authorization": f"Bearer {settings.mcp_auth_token}"}
            if tool_name == "mcp_github":
                github_token = _usable_value(_read_env_file().get("GITHUB_TOKEN"))
                if github_token:
                    headers["X-MCP-GitHub-Token"] = github_token
            resp = await client.post(
                f"{settings.mcp_server_url}/tools/{tool_name}/call",
                json={"arguments": args},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur MCP: {e}")


async def _call_server_diagnostics(args: Dict[str, Any]) -> Dict[str, Any]:
    """Diagnostics sans shell ni accès arbitraire au VPS hôte."""
    operation = str(args.get("operation") or "health")
    if operation == "system":
        load = Path("/proc/loadavg").read_text().split()[:3] if Path("/proc/loadavg").exists() else []
        memory: Dict[str, str] = {}
        if Path("/proc/meminfo").exists():
            for line in Path("/proc/meminfo").read_text().splitlines()[:20]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    memory[key] = value.strip()
        return {"scope": "conteneur Hermes", "load_average": load, "memory": memory}
    if operation == "disk":
        usage = shutil.disk_usage("/")
        return {"scope": "conteneur Hermes", "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}

    service_urls = {
        "hermes_daemon": "http://127.0.0.1:8001/health",
        "mcp_server": f"{settings.mcp_server_url.rstrip('/')}/health",
        "n8n": f"{settings.n8n_webhook_base_url.rstrip('/').removesuffix('/webhook')}/healthz",
    }
    results: Dict[str, Any] = {"scope": "services Hermes accessibles", "services": {}}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, url in service_urls.items():
            try:
                response = await client.get(url, headers={"Authorization": f"Bearer {settings.mcp_auth_token}"} if service == "mcp_server" else {})
                results["services"][service] = {"ok": response.is_success, "status_code": response.status_code}
            except httpx.HTTPError as exc:
                results["services"][service] = {"ok": False, "error": type(exc).__name__}
    if operation == "services":
        return results
    return {"scope": results["scope"], "services": results["services"], "timestamp": datetime.utcnow().isoformat()}


async def _execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Point d’entrée unique du Tool Broker, avec erreurs renvoyées au modèle."""
    try:
        destructive = (
            tool_name == "n8n_webhook"
            or (tool_name == "mcp_filesystem" and arguments.get("operation") in {"write", "delete"})
            or (tool_name == "mcp_github" and arguments.get("operation") == "create_pr")
            or (tool_name == "google_calendar" and arguments.get("operation") == "create")
        )
        if destructive and arguments.get("confirmed") is not True:
            return {"requires_confirmation": True, "tool": tool_name, "message": "Demande une confirmation explicite à l’utilisateur avant cette action."}
        if tool_name == "n8n_webhook":
            return await _call_n8n_webhook(arguments)
        if tool_name.startswith("mcp_"):
            return await _call_mcp(tool_name, arguments)
        if tool_name == "server_diagnostics":
            return await _call_server_diagnostics(arguments)
        if tool_name == "web_search":
            return await _call_web_search(arguments)
        if tool_name == "web_fetch":
            return await _call_web_fetch(arguments)
        if tool_name == "google_gmail":
            return await _call_google_gmail(arguments)
        if tool_name == "google_calendar":
            return await _call_google_calendar(arguments)
        if tool_name == "google_drive":
            return await _call_google_drive(arguments)
        return {"error": f"Outil inconnu : {tool_name}"}
    except HTTPException as exc:
        return {"error": str(exc.detail), "status_code": exc.status_code}
    except Exception as exc:
        LOGGER.exception("Outil %s en erreur", tool_name)
        return {"error": f"Erreur contrôlée de l’outil {tool_name}: {type(exc).__name__}"}


# ---------------------------------------------------------------------------
# Endpoints Agents
# ---------------------------------------------------------------------------
AGENTS_PATH = Path("/data/agents.json")


def _load_agents() -> Dict[str, AgentConfig]:
    if not AGENTS_PATH.exists():
        return {}
    try:
        raw = json.loads(AGENTS_PATH.read_text())
        return {name: AgentConfig.model_validate(agent) for name, agent in raw.items()}
    except (OSError, ValueError):
        return {}


def _save_agents() -> None:
    AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = AGENTS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({name: agent.model_dump() for name, agent in AGENTS.items()}, indent=2))
    temporary.replace(AGENTS_PATH)


AGENTS: Dict[str, AgentConfig] = _load_agents()


@app.get("/api/agents")
async def list_agents(_: bool = Depends(verify_token)):
    return {"agents": [a.model_dump() for a in AGENTS.values()]}


@app.post("/api/agents", response_model=AgentConfig)
async def create_agent(agent: AgentConfig, _: bool = Depends(verify_token)):
    if agent.name in AGENTS:
        raise HTTPException(status_code=409, detail="Un agent porte déjà ce nom.")
    unknown_tools = sorted(set(agent.tools) - set(TOOL_REGISTRY))
    if unknown_tools:
        raise HTTPException(status_code=400, detail=f"Outils inconnus: {', '.join(unknown_tools)}")
    AGENTS[agent.name] = agent
    _save_agents()
    return agent


@app.put("/api/agents/{current_name}", response_model=AgentConfig)
async def update_agent(current_name: str, agent: AgentConfig, _: bool = Depends(verify_token)):
    """Modifie un agent, y compris son nom, modèle, paramètres et outils."""
    if current_name not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    if agent.name != current_name and agent.name in AGENTS:
        raise HTTPException(status_code=409, detail="Un agent porte déjà ce nom.")
    unknown_tools = sorted(set(agent.tools) - set(TOOL_REGISTRY))
    if unknown_tools:
        raise HTTPException(status_code=400, detail=f"Outils inconnus: {', '.join(unknown_tools)}")
    if agent.name != current_name:
        del AGENTS[current_name]
    AGENTS[agent.name] = agent
    _save_agents()
    return agent


@app.delete("/api/agents/{name}")
async def delete_agent(name: str, _: bool = Depends(verify_token)):
    if name in AGENTS:
        del AGENTS[name]
        _save_agents()
        return {"status": "deleted", "name": name}
    raise HTTPException(status_code=404, detail="Agent introuvable")


# ---------------------------------------------------------------------------
# Conversations persistantes
# ---------------------------------------------------------------------------
CONVERSATIONS_PATH = Path("/data/conversations.json")


def _load_conversations() -> Dict[str, ConversationRecord]:
    if not CONVERSATIONS_PATH.exists():
        return {}
    try:
        raw = json.loads(CONVERSATIONS_PATH.read_text())
        return {conversation_id: ConversationRecord.model_validate(conversation) for conversation_id, conversation in raw.items()}
    except (OSError, ValueError):
        return {}


def _save_conversations() -> None:
    CONVERSATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONVERSATIONS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({conversation_id: conversation.model_dump() for conversation_id, conversation in CONVERSATIONS.items()}, indent=2, ensure_ascii=False))
    temporary.replace(CONVERSATIONS_PATH)


def _validate_conversation_options(agent_name: Optional[str], tool_names: List[str]) -> None:
    if agent_name and agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    unknown_tools = sorted(set(tool_names) - set(TOOL_REGISTRY))
    if unknown_tools:
        raise HTTPException(status_code=400, detail=f"Outils inconnus: {', '.join(unknown_tools)}")


CONVERSATIONS: Dict[str, ConversationRecord] = _load_conversations()


@app.post("/api/conversations/{conversation_id}/attachments", response_model=Attachment)
async def upload_attachment(conversation_id: str, file: UploadFile = File(...), _: bool = Depends(verify_token)):
    """Stocke une pièce jointe privée et contrôlée pour une conversation."""
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    original_name = Path(file.filename or "piece-jointe").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Type de fichier non pris en charge.")
    attachment_id = uuid4().hex
    directory = Path(settings.upload_dir) / conversation_id
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{attachment_id}{suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="La pièce jointe dépasse la limite de 20 Mo.")
                output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Impossible d’enregistrer la pièce jointe.") from exc
    finally:
        await file.close()
    extracted = bool(_extract_attachment_text(destination).strip())
    return Attachment(id=attachment_id, name=original_name[:180], mime_type=file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream", size=size, extracted=extracted)


@app.delete("/api/conversations/{conversation_id}/attachments/{attachment_id}")
async def delete_attachment(conversation_id: str, attachment_id: str, _: bool = Depends(verify_token)):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    path = _attachment_path(attachment_id)
    if not path or path.parent.name != conversation_id:
        raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
    path.unlink(missing_ok=True)
    return {"status": "deleted", "id": attachment_id}


@app.get("/api/conversations")
async def list_conversations(_: bool = Depends(verify_token)):
    conversations = sorted(CONVERSATIONS.values(), key=lambda item: item.updated_at, reverse=True)
    return {"conversations": [conversation.model_dump(exclude={"messages"}) for conversation in conversations]}


@app.post("/api/conversations", response_model=ConversationRecord)
async def create_conversation(payload: ConversationCreate, _: bool = Depends(verify_token)):
    _validate_conversation_options(payload.agent_name, payload.tool_names)
    now = datetime.utcnow().isoformat()
    conversation = ConversationRecord(
        id=uuid4().hex,
        title=payload.title.strip() or "Nouvelle conversation",
        agent_name=payload.agent_name,
        model=payload.model.strip() if payload.model else None,
        tool_names=payload.tool_names,
        context_tokens=payload.context_tokens,
        created_at=now,
        updated_at=now,
    )
    CONVERSATIONS[conversation.id] = conversation
    _save_conversations()
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=ConversationRecord)
async def get_conversation(conversation_id: str, _: bool = Depends(verify_token)):
    conversation = CONVERSATIONS.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation


@app.put("/api/conversations/{conversation_id}", response_model=ConversationRecord)
async def update_conversation(conversation_id: str, payload: ConversationUpdate, _: bool = Depends(verify_token)):
    conversation = CONVERSATIONS.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    fields_set = payload.model_fields_set
    next_agent = payload.agent_name if "agent_name" in fields_set else conversation.agent_name
    next_tools = payload.tool_names if "tool_names" in fields_set and payload.tool_names is not None else conversation.tool_names
    _validate_conversation_options(next_agent, next_tools)
    if payload.title is not None:
        conversation.title = payload.title.strip() or conversation.title
    if "agent_name" in fields_set:
        conversation.agent_name = payload.agent_name
    if "model" in fields_set:
        conversation.model = payload.model.strip() if payload.model else None
    if "tool_names" in fields_set and payload.tool_names is not None:
        conversation.tool_names = payload.tool_names
    if "context_tokens" in fields_set and payload.context_tokens is not None:
        conversation.context_tokens = payload.context_tokens
    if "messages" in fields_set and payload.messages is not None:
        conversation.messages = payload.messages
    conversation.updated_at = datetime.utcnow().isoformat()
    _save_conversations()
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, _: bool = Depends(verify_token)):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    del CONVERSATIONS[conversation_id]
    _save_conversations()
    return {"status": "deleted", "id": conversation_id}


# ---------------------------------------------------------------------------
# Endpoints Settings (clés API serveur)
# ---------------------------------------------------------------------------
ENV_PATH = Path("/data/hermes.env")  # Volume persistant du daemon


def _read_env_file() -> Dict[str, str]:
    """Lit le fichier .env persistant du daemon."""
    if not ENV_PATH.exists():
        return {}
    env: Dict[str, str] = {}
    with ENV_PATH.open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _write_env_file(env: Dict[str, str]) -> None:
    """Écrit le fichier .env persistant."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = ENV_PATH.with_suffix(".tmp")
    with temporary.open("w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    os.chmod(temporary, 0o600)
    temporary.replace(ENV_PATH)


def _usable_value(value: Optional[str]) -> str:
    value = (value or "").strip().strip('"').strip("'")
    return "" if not value or value.startswith("__") else value


def _get_minimax_config() -> Tuple[str, str, str]:
    """Retourne la configuration effective, avec priorité aux réglages sauvegardés."""
    persisted = _read_env_file()
    api_key = _usable_value(persisted.get("MINIMAX_API_KEY")) or _usable_value(settings.minimax_api_key)
    base_url = (_usable_value(persisted.get("MINIMAX_BASE_URL")) or _usable_value(settings.minimax_base_url) or DEFAULT_MINIMAX_BASE_URL).rstrip("/")
    model = _usable_value(persisted.get("MINIMAX_MODEL")) or _usable_value(settings.minimax_model) or DEFAULT_MINIMAX_MODEL
    if base_url == DEFAULT_MINIMAX_BASE_URL and model in LEGACY_MINIMAX_MODELS:
        model = DEFAULT_MINIMAX_MODEL
    return api_key, base_url, model


@app.get("/api/settings/status", response_model=SettingsStatus)
async def settings_status(_: bool = Depends(verify_token)):
    """Indique quelles clés sont configurées (jamais les valeurs)."""
    persisted = _read_env_file()
    api_key, base_url, model = _get_minimax_config()
    telegram_token, allowed_chat_id = _get_telegram_config()
    telegram_agent_name = _get_telegram_agent_name()

    mcp_ready = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{settings.mcp_server_url}/health",
                headers={"Authorization": f"Bearer {settings.mcp_auth_token}"},
            )
            mcp_ready = response.is_success
    except httpx.HTTPError:
        mcp_ready = False

    return SettingsStatus(
        minimax_configured=bool(api_key),
        telegram_configured=bool(telegram_token),
        telegram_chat_configured=bool(allowed_chat_id),
        telegram_running=bool(TELEGRAM_STATE["running"]),
        telegram_bot_username=TELEGRAM_STATE["bot_username"],
        telegram_last_error=TELEGRAM_STATE["last_error"],
        telegram_agent_name=telegram_agent_name or None,
        github_configured=bool(persisted.get("GITHUB_TOKEN")),
        model=model,
        minimax_base_url=base_url,
        mcp_ready=mcp_ready,
    )


@app.post("/api/settings/update")
async def update_settings(upd: SettingsUpdate, _: bool = Depends(verify_token)):
    """Met à jour les clés API côté serveur (fichier .env persistant)."""
    env = _read_env_file()

    if upd.minimax_api_key:
        env["MINIMAX_API_KEY"] = upd.minimax_api_key.strip()
    if upd.minimax_base_url:
        env["MINIMAX_BASE_URL"] = upd.minimax_base_url.strip().rstrip("/")
    if upd.minimax_model:
        env["MINIMAX_MODEL"] = upd.minimax_model.strip()
    if upd.telegram_bot_token:
        env["TELEGRAM_BOT_TOKEN"] = upd.telegram_bot_token
    if upd.allowed_chat_id:
        env["ALLOWED_CHAT_ID"] = upd.allowed_chat_id
    if upd.telegram_agent_name is not None:
        env["TELEGRAM_AGENT_NAME"] = upd.telegram_agent_name.strip()
    if upd.github_token:
        env["GITHUB_TOKEN"] = upd.github_token

    _write_env_file(env)

    return {
        "status": "ok",
        "updated": [
            k for k, v in [
                ("minimax", bool(upd.minimax_api_key)),
                ("minimax base URL", bool(upd.minimax_base_url)),
                ("minimax model", bool(upd.minimax_model)),
                ("telegram", bool(upd.telegram_bot_token)),
                ("chat Telegram autorisé", bool(upd.allowed_chat_id)),
                ("agent Telegram", bool(upd.telegram_agent_name)),
                ("github", bool(upd.github_token)),
            ] if v
        ],
        "message": "Les paramètres sont sauvegardés et pris en compte immédiatement.",
    }


# ---------------------------------------------------------------------------
# Connecteurs Google OAuth (tokens chiffrés côté serveur)
# ---------------------------------------------------------------------------
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.file",
]
CONNECTORS_PATH = Path("/data/connectors.json")
OAUTH_STATES_PATH = Path("/data/oauth-states.json")


def _google_fernet() -> Fernet:
    secret = _usable_value(settings.hermes_jwt_secret) or _usable_value(os.getenv("HERMES_SESSION_SECRET"))
    if not secret:
        raise HTTPException(status_code=503, detail="Le secret Hermes est nécessaire pour chiffrer les connexions Google.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _read_connector_store() -> Dict[str, str]:
    if not CONNECTORS_PATH.exists():
        return {}
    try:
        raw = json.loads(CONNECTORS_PATH.read_text())
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_connector_store(store: Dict[str, str]) -> None:
    CONNECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONNECTORS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(store, ensure_ascii=False))
    os.chmod(temporary, 0o600)
    temporary.replace(CONNECTORS_PATH)


def _read_google_connector() -> Dict[str, Any]:
    encrypted = _read_connector_store().get("google")
    if not encrypted:
        return {}
    try:
        return json.loads(_google_fernet().decrypt(encrypted.encode()).decode())
    except (InvalidToken, ValueError, TypeError):
        return {}


def _write_google_connector(data: Dict[str, Any]) -> None:
    store = _read_connector_store()
    encrypted = _google_fernet().encrypt(json.dumps(data, ensure_ascii=False).encode()).decode()
    store["google"] = encrypted
    _write_connector_store(store)


def _google_redirect_uri() -> str:
    return _usable_value(settings.google_redirect_uri) or "https://hermes.eaumalik.com/api/hermes/connectors/google/callback"


@app.get("/api/connectors")
async def list_connectors(_: bool = Depends(verify_token)):
    google = _read_google_connector()
    return {
        "connectors": [{
            "id": "google",
            "name": "Google Workspace",
            "configured": bool(_usable_value(settings.google_client_id) and _usable_value(settings.google_client_secret)),
            "connected": bool(google.get("refresh_token") or google.get("access_token")),
            "email": google.get("email"),
            "services": ["Gmail", "Agenda", "Drive"],
        }]
    }


@app.get("/api/connectors/google/start")
async def start_google_oauth(_: bool = Depends(verify_token)):
    google_client_id = _usable_value(settings.google_client_id)
    google_client_secret = _usable_value(settings.google_client_secret)
    if not google_client_id or not google_client_secret:
        raise HTTPException(status_code=503, detail="Configurez GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET sur le serveur.")
    state = secrets.token_urlsafe(32)
    states = {state: time.time() + 600}
    OAUTH_STATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OAUTH_STATES_PATH.write_text(json.dumps(states))
    query = {
        "client_id": google_client_id,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
    }
    from urllib.parse import urlencode
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(query)}


@app.get("/api/connectors/google/callback")
async def google_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        return RedirectResponse("/settings?connector=google&status=cancelled")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Réponse OAuth Google incomplète.")
    states = json.loads(OAUTH_STATES_PATH.read_text()) if OAUTH_STATES_PATH.exists() else {}
    expires_at = states.pop(state, 0)
    OAUTH_STATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OAUTH_STATES_PATH.write_text(json.dumps(states))
    if not expires_at or expires_at < time.time():
        raise HTTPException(status_code=400, detail="État OAuth expiré. Recommencez la connexion Google.")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": _usable_value(settings.google_client_id),
            "client_secret": _usable_value(settings.google_client_secret),
            "redirect_uri": _google_redirect_uri(),
            "grant_type": "authorization_code",
        })
        if not response.is_success:
            raise HTTPException(status_code=502, detail="Google a refusé la connexion OAuth.")
        token = response.json()
        user_response = await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {token.get('access_token', '')}"})
    previous = _read_google_connector()
    _write_google_connector({
        "access_token": token.get("access_token", ""),
        "refresh_token": token.get("refresh_token") or previous.get("refresh_token", ""),
        "expires_at": time.time() + int(token.get("expires_in", 3600)),
        "email": user_response.json().get("email") if user_response.is_success else previous.get("email"),
    })
    return RedirectResponse("/settings?connector=google&status=connected")


@app.delete("/api/connectors/google")
async def disconnect_google(_: bool = Depends(verify_token)):
    store = _read_connector_store()
    store.pop("google", None)
    _write_connector_store(store)
    return {"status": "disconnected"}


async def _google_access_token() -> str:
    connector = _read_google_connector()
    if not connector:
        raise HTTPException(status_code=409, detail="Connectez d’abord Google dans Configuration → Connecteurs.")
    if connector.get("access_token") and float(connector.get("expires_at", 0)) > time.time() + 60:
        return connector["access_token"]
    refresh_token = connector.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=409, detail="La connexion Google doit être renouvelée.")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": _usable_value(settings.google_client_id),
            "client_secret": _usable_value(settings.google_client_secret),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
    if not response.is_success:
        raise HTTPException(status_code=502, detail="Impossible de renouveler la connexion Google.")
    token = response.json()
    connector.update({"access_token": token.get("access_token", ""), "expires_at": time.time() + int(token.get("expires_in", 3600))})
    _write_google_connector(connector)
    return connector["access_token"]


async def _google_api(method: str, url: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = await _google_access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, params=params, json=json_body, headers={"Authorization": f"Bearer {token}"})
    if not response.is_success:
        raise HTTPException(status_code=502, detail=f"Google API a renvoyé HTTP {response.status_code}.")
    return response.json()


async def _call_google_gmail(args: Dict[str, Any]) -> Dict[str, Any]:
    operation = args.get("operation", "search")
    if operation == "search":
        data = await _google_api("GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages", params={"q": str(args.get("query") or "newer_than:30d")[:500], "maxResults": 20})
        return {"messages": data.get("messages", []), "result_size_estimate": data.get("resultSizeEstimate", 0)}
    message_id = str(args.get("message_id") or "")
    if not message_id:
        return {"error": "message_id est obligatoire pour lire un email."}
    data = await _google_api("GET", f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}", params={"format": "full"})
    return {"id": data.get("id"), "thread_id": data.get("threadId"), "snippet": data.get("snippet"), "payload": data.get("payload", {}).get("headers", [])}


async def _call_google_calendar(args: Dict[str, Any]) -> Dict[str, Any]:
    calendar_id = str(args.get("calendar_id") or "primary")
    if args.get("operation", "list") == "create":
        if not args.get("confirmed"):
            return {"requires_confirmation": True, "action": "create_calendar_event", "summary": args.get("summary"), "start": args.get("start"), "end": args.get("end")}
        return await _google_api("POST", f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events", json_body={"summary": args.get("summary", "Hermes"), "start": {"dateTime": args.get("start")}, "end": {"dateTime": args.get("end")}})
    params = {"singleEvents": "true", "orderBy": "startTime", "maxResults": 50}
    if args.get("time_min"): params["timeMin"] = args["time_min"]
    if args.get("time_max"): params["timeMax"] = args["time_max"]
    data = await _google_api("GET", f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events", params=params)
    return {"items": data.get("items", [])}


async def _call_google_drive(args: Dict[str, Any]) -> Dict[str, Any]:
    if args.get("operation", "search") == "search":
        query = str(args.get("query") or "")[:200].replace("'", "\\'")
        data = await _google_api("GET", "https://www.googleapis.com/drive/v3/files", params={"q": f"name contains '{query}' and trashed = false", "pageSize": 30, "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink)"})
        return {"files": data.get("files", [])}
    file_id = str(args.get("file_id") or "")
    if not file_id:
        return {"error": "file_id est obligatoire pour lire un fichier Drive."}
    return await _google_api("GET", f"https://www.googleapis.com/drive/v3/files/{file_id}", params={"alt": "json", "fields": "id,name,mimeType,modifiedTime,size,webViewLink,description"})


@app.post("/api/settings/test/minimax")
async def test_minimax(_: bool = Depends(verify_token)):
    """Teste réellement la clé et le modèle Minimax configurés."""
    api_key, base_url, model = _get_minimax_config()
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Minimax non configurée")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Réponds uniquement : OK"}],
                    "max_completion_tokens": 4,
                    "temperature": 0.1,
                    "reasoning_split": True,
                },
            )
            resp.raise_for_status()
            return {"status": "ok", "code": resp.status_code, "reachable": True, "model": model}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=422, detail="MiniMax a refusé la clé API configurée.") from e
            raise HTTPException(status_code=502, detail=f"MiniMax a renvoyé HTTP {e.response.status_code} pendant le test.") from e
        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail="MiniMax ne répond pas au test dans le délai imparti.") from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur Minimax: {e}")


@app.post("/api/settings/test/telegram")
async def test_telegram(_: bool = Depends(verify_token)):
    """Teste le token Telegram et signale si un webhook empêcherait le polling."""
    token, allowed_chat_id = _get_telegram_config()
    if not token:
        raise HTTPException(status_code=400, detail="Token Telegram non configuré")

    try:
        bot = await _telegram_api(token, "getMe", timeout=12.0)
        webhook = await _telegram_api(token, "getWebhookInfo", timeout=12.0)
    except TelegramAPIError as exc:
        status_code = 422 if exc.status_code in {401, 404} else 502
        raise HTTPException(status_code=status_code, detail=f"Telegram: {exc.detail}") from exc

    webhook_url = str((webhook or {}).get("url") or "")
    return {
        "status": "warning" if webhook_url else "ok",
        "bot_username": (bot or {}).get("username"),
        "webhook_configured": bool(webhook_url),
        "pending_updates": int((webhook or {}).get("pending_update_count") or 0),
        "allowed_chat_configured": bool(allowed_chat_id),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.hermes_port)
