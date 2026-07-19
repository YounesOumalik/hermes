"""
hermes-core/tools/dispatcher.py — Outils dispatcher.

Routes les appels d'outils vers :
  - mcp_*    → MCP server (filesystem, github, terminal)
  - n8n_*    → n8n webhook
  - autres   → ProviderUnavailable

Détecte le pattern `requires_confirmation` (cf. mcp-server/server.js) :
  retourne ToolCallResult(requires_approval=True, ...) pour que
  l'orchestrator crée un Approval et yield SSE `tool_calls_detected`.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger("hermes.core.tools")


class ToolCallResult:
    """Résultat unifié d'un tool call."""

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        requires_approval: bool = False,
        tool_name: str = "",
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.requires_approval = requires_approval
        self.tool_name = tool_name

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "success": self.success,
            "tool_name": self.tool_name,
            "requires_approval": self.requires_approval,
        }
        if self.data:
            d["data"] = self.data
        if self.error:
            d["error"] = self.error
        return d


async def route_tool_call(
    tool_name: str,
    args: Dict[str, Any],
    http_client: httpx.AsyncClient,
    confirmed: bool = False,
) -> ToolCallResult:
    """
    Dispatch un tool call vers le bon service.

    Args:
        tool_name: nom du tool (mcp_*, n8n_*, ...)
        args: arguments du tool
        http_client: client httpx partagé (lifespan)
        confirmed: si True, ajoute confirmed=true aux args (bypass approval gate)

    Returns:
        ToolCallResult avec success/data ou requires_approval
    """
    logger.info(f"Dispatch tool: {tool_name} args_keys={list(args.keys())} confirmed={confirmed}")

    if tool_name.startswith("mcp_"):
        return await _call_mcp(tool_name, args, http_client, confirmed)
    elif tool_name == "n8n_webhook":
        return await _call_n8n(args, http_client)
    else:
        return ToolCallResult(
            success=False,
            error=f"Tool inconnu: {tool_name}",
            tool_name=tool_name,
        )


async def _call_mcp(
    tool_name: str,
    args: Dict[str, Any],
    http_client: httpx.AsyncClient,
    confirmed: bool,
) -> ToolCallResult:
    """Appelle le serveur MCP via son API HTTP."""
    # Inject `confirmed` pour bypass approval gate (mcp-server pattern)
    if confirmed:
        args = {**args, "confirmed": True}

    try:
        resp = await http_client.post(
            f"{settings.mcp_server_url}/tools/{tool_name}/call",
            json={"arguments": args},
            headers={"Authorization": f"Bearer {settings.mcp_auth_token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        body = resp.json()

        # MCP retourne {content: [{type: "text", text: "<JSON string>"}]}
        # Détecte requires_confirmation (HTTP 200 avec marker)
        if isinstance(body, dict) and body.get("content"):
            text_content = body["content"][0].get("text", "")
            try:
                inner = __import__("json").loads(text_content)
            except Exception:
                inner = {"raw": text_content}

            if isinstance(inner, dict) and inner.get("requires_confirmation"):
                return ToolCallResult(
                    success=False,
                    data=inner,
                    requires_approval=True,
                    tool_name=tool_name,
                )

            return ToolCallResult(
                success=True,
                data=inner,
                tool_name=tool_name,
            )

        return ToolCallResult(
            success=True,
            data=body,
            tool_name=tool_name,
        )
    except httpx.HTTPStatusError as e:
        return ToolCallResult(
            success=False,
            error=f"MCP HTTP {e.response.status_code}: {e.response.text[:200]}",
            tool_name=tool_name,
        )
    except Exception as e:
        return ToolCallResult(
            success=False,
            error=f"MCP error: {e}",
            tool_name=tool_name,
        )


async def _call_n8n(args: Dict[str, Any], http_client: httpx.AsyncClient) -> ToolCallResult:
    """Appelle un webhook n8n."""
    webhook_path = args.get("webhook_path", "").lstrip("/")
    method = (args.get("method", "POST") or "POST").upper()
    payload = args.get("payload", {})
    headers = args.get("headers", {})

    url = f"{settings.n8n_webhook_base_url.rstrip('/')}/{webhook_path}"

    try:
        if method == "GET":
            resp = await http_client.get(url, params=payload, headers=headers, timeout=30.0)
        else:
            resp = await http_client.post(url, json=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}

        return ToolCallResult(
            success=True,
            data={"status_code": resp.status_code, "data": data},
            tool_name="n8n_webhook",
        )
    except httpx.HTTPStatusError as e:
        return ToolCallResult(
            success=False,
            error=f"n8n HTTP {e.response.status_code}: {e.response.text[:200]}",
            tool_name="n8n_webhook",
        )
    except Exception as e:
        return ToolCallResult(
            success=False,
            error=f"n8n error: {e}",
            tool_name="n8n_webhook",
        )