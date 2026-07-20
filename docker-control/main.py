#!/usr/bin/env python3
# ============================================================================
# docker-control — Mini-API HTTP pour piloter la stack depuis Open WebUI
#
# Endpoints (tous requièrent Authorization: Bearer $DOCKER_CONTROL_TOKEN) :
#   GET  /health             → {"status": "ok"}
#   GET  /ps                 → Liste des containers + status
#   GET  /logs/<service>     → 50 dernières lignes de logs d'un service
#   POST /restart/<service>  → docker compose restart <service>
#   POST /up                 → docker compose up -d (toute la stack)
#   POST /down               → docker compose down
#   POST /pull               → git pull + docker compose pull + up -d
#
# Lancé en arrière-plan sur le VPS via systemd :
#   /opt/agentai/docker-control/venv/bin/uvicorn main:app --host 127.0.0.1 --port 9100
#
# Exposé publiquement via Caddy :
#   agentai.smartefp.com/api/control/* → 127.0.0.1:9100/*
# ============================================================================
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

# ---------- Config ----------------------------------------------------------
APP_DIR = Path("/srv/agentai")
API_TOKEN = os.environ.get("DOCKER_CONTROL_TOKEN", "")
ALLOWED_SERVICES = {"open-webui", "llm-proxy", "agentai-postgres", "agentai-redis"}

if not API_TOKEN or "__" in API_TOKEN or "PLACEHOLDER" in API_TOKEN:
    print("⚠️  DOCKER_CONTROL_TOKEN non configuré ou placeholder → API désactivée")

# ---------- App -------------------------------------------------------------
app = FastAPI(title="docker-control", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agentai.smartefp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def verify_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Vérifie le Bearer token."""
    if not API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DOCKER_CONTROL_TOKEN not set on server",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token",
        )


# ---------- Helpers --------------------------------------------------------
def run(cmd: list[str], cwd: Path | None = APP_DIR, timeout: int = 60) -> tuple[int, str, str]:
    """Run a subprocess and return (rc, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


# ---------- Endpoints ------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "token_configured": bool(API_TOKEN)}


@app.get("/ps")
def ps(_: Annotated[None, Depends(verify_token)]):
    rc, out, err = run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"]
    )
    if rc != 0:
        raise HTTPException(500, f"docker ps failed: {err}")
    lines = out.strip().split("\n") if out.strip() else []
    return {
        "services": [
            {
                "name": parts[0],
                "status": parts[1] if len(parts) > 1 else "",
                "ports": parts[2] if len(parts) > 2 else "",
            }
            for parts in (line.split("\t") for line in lines)
        ]
    }


@app.get("/logs/{service}", response_class=PlainTextResponse)
def logs(service: str, _: Annotated[None, Depends(verify_token)], tail: int = 50):
    if service not in ALLOWED_SERVICES and service != "all":
        raise HTTPException(400, f"Unknown service: {service}")
    rc, out, err = run(["docker", "compose", "logs", "--tail", str(tail), service], timeout=30)
    if rc != 0:
        raise HTTPException(500, f"docker compose logs failed: {err}")
    return out


class RestartResponse(BaseModel):
    service: str
    rc: int
    stdout: str
    stderr: str


@app.post("/restart/{service}")
def restart(service: str, _: Annotated[None, Depends(verify_token)]):
    if service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service: {service}")
    rc, out, err = run(["docker", "compose", "restart", service], timeout=60)
    return RestartResponse(service=service, rc=rc, stdout=out, stderr=err)


@app.post("/up")
def up(_: Annotated[None, Depends(verify_token)]):
    rc, out, err = run(["docker", "compose", "up", "-d"], timeout=180)
    return JSONResponse(
        {"rc": rc, "stdout": out, "stderr": err},
        status_code=200 if rc == 0 else 500,
    )


@app.post("/pull")
def pull(_: Annotated[None, Depends(verify_token)]):
    """git pull + docker compose pull + up -d. Plus long (peut prendre 1-3 min)."""
    results = {}
    for label, cmd in [
        ("git_pull", ["git", "pull", "--ff-only"]),
        ("compose_pull", ["docker", "compose", "pull"]),
        ("compose_up", ["docker", "compose", "up", "-d"]),
    ]:
        rc, out, err = run(cmd, timeout=300 if "pull" in label else 180)
        results[label] = {"rc": rc, "stdout": out[-2000:], "stderr": err[-1000:]}
        if rc != 0 and label == "git_pull":
            # Si git pull échoue, on ne continue pas
            return JSONResponse(results, status_code=500)
    return JSONResponse(results)


@app.post("/down")
def down(_: Annotated[None, Depends(verify_token)]):
    rc, out, err = run(["docker", "compose", "down"], timeout=60)
    return JSONResponse(
        {"rc": rc, "stdout": out, "stderr": err},
        status_code=200 if rc == 0 else 500,
    )