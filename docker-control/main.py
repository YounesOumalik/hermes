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
#   POST /pull               → git pull + docker compose pull + up -d
#   POST /down               → docker compose down
#
# Per-user storage quotas & model filtering (NEW 2026-07-20) :
#   GET  /quotas                       → liste users + leurs quotas + storage used
#   POST /quotas/{user_id}             → définir quota_mb et/ou allowed_models
#   DELETE /quotas/{user_id}           → supprimer les quotas
#   POST /upload-check/{user_id}?mb=N  → vérifier qu'un upload de N MB est OK
#
# Lancé en arrière-plan sur le VPS via systemd :
#   /opt/agentai/docker-control/venv/bin/uvicorn main:app --host 127.0.0.1 --port 9100
#
# Exposé publiquement via Caddy :
#   agentai.smartefp.com/api/control/* → 127.0.0.1:9100/*
#
# Implémentation des quotas : on stocke dans user.info (colonne JSON d'Open WebUI)
# sous les clés quota_mb (int) et allowed_models (list). Les lectures/écritures
# utilisent `docker exec open-webui python3 ...` car webui.db et uploads/ sont
# root-owned dans le volume Docker. docker-control tourne en `younes` (pas root)
# mais a accès au socket Docker via le groupe `docker`.
# ============================================================================
from __future__ import annotations

import os
import subprocess
import csv
import tempfile
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
CONTAINER_NAME = "open-webui"  # Open WebUI container (must exist)
DB_PATH_IN_CONTAINER = "/app/backend/data/webui.db"
UPLOADS_DIR_IN_CONTAINER = "/app/backend/data/uploads"

if not API_TOKEN or "__" in API_TOKEN or "PLACEHOLDER" in API_TOKEN:
    print("⚠️  DOCKER_CONTROL_TOKEN non configuré ou placeholder → API désactivée")

# ---------- App -------------------------------------------------------------
app = FastAPI(title="docker-control", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agentai.smartefp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def verify_token(authorization: Annotated[str | None, Header()] = None) -> None:
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
def run(cmd, cwd=APP_DIR, timeout=60):
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def docker_cp_exec_python(script_body: str, container: str = CONTAINER_NAME, timeout: int = 30):
    """Write a python script to a tmp file on the host, `docker cp` it into
    the container, then `docker exec python3 ...`. Returns (rc, stdout, stderr).
    Use the container's full root context to access webui.db / uploads/.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_body)
        tmp_path = f.name
    container_path = "/tmp/_agentai_exec.py"
    try:
        rc1, _, err1 = run(
            ["docker", "cp", tmp_path, f"{container}:{container_path}"], timeout=10
        )
        if rc1 != 0:
            return rc1, "", f"docker cp failed: {err1[:500]}"
        return run(
            ["docker", "exec", container, "python3", container_path], timeout=timeout
        )
    finally:
        run(
            ["docker", "exec", container, "rm", "-f", container_path], timeout=5
        )
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def read_via_docker(query: str) -> list[dict]:
    """Run a SELECT inside the open-webui container. Returns list of row dicts
    (header-row aware). CSV output parsed in Python.
    """
    import json as _json
    lines = [
        "import sqlite3, csv, sys",
        "con = sqlite3.connect('" + DB_PATH_IN_CONTAINER + "')",
        "con.row_factory = sqlite3.Row",
        "rows = con.execute(" + _json.dumps(query) + ").fetchall()",
        "header = list(rows[0].keys()) if rows else []",
        "w = csv.writer(sys.stdout)",
        "w.writerow(header)",
        "for r in rows: w.writerow(['' if v is None else str(v) for v in r])",
        "con.close()",
    ]
    script = "\n".join(lines)
    rc, out, err = docker_cp_exec_python(script)
    if rc != 0:
        raise HTTPException(500, f"sqlite read failed (rc={rc}): {err[:500]}")
    if not out.strip():
        return []
    rows = out.strip().splitlines()
    if len(rows) < 2:
        return []
    return list(csv.DictReader(rows))


import csv  # placed after the function to keep import local; also used below


def write_user_info_via_docker(user_id: str, info: dict) -> None:
    """UPDATE user.info via docker exec python (parameter binding).

    Generates a small Python script that runs inside the open-webui container
    with full root access to webui.db. Uses sqlite3 parameter binding;
    the JSON info dict and user_id string are embedded as Python string
    literals via json.dumps (which adds proper quoting + escaping).
    """
    _info_json = _json.dumps(info)          # '{"quota_mb":5000,...}'
    _user_id_str = _json.dumps(user_id)     # '"ff36523b-..."'
    # Each of the above is already a valid Python string literal
    # (wrapped in double quotes). We just concatenate them into the script.
    _sql = _json.dumps('UPDATE "user" SET info = ? WHERE id = ?')
    script_parts = [
        "import sqlite3",
        "con = sqlite3.connect('" + DB_PATH_IN_CONTAINER + "')",
        "con.execute(" + _sql + ", (" + _info_json + ", " + _user_id_str + "))",
        "con.commit()",
        "con.close()",
    ]
    script = "\n".join(script_parts)
    rc, out, err = docker_cp_exec_python(script)
    if rc != 0:
        raise HTTPException(500, f"sqlite UPDATE failed (rc={rc}): {err[:500]}")


def get_user_storage_mb(user_id: str) -> int:
    """Total MB used by user's uploads (delegated to container)."""
    import json as _json
    lines = [
        "import os",
        "p = " + _json.dumps(UPLOADS_DIR_IN_CONTAINER + "/" + user_id),
        "if not os.path.isdir(p):",
        "    print(0); exit()",
        "total = 0",
        "for r, _d, files in os.walk(p):",
        "    for f in files: total += os.path.getsize(os.path.join(r, f))",
        "print(total // (1024 * 1024))",
    ]
    script = "\n".join(lines)
    rc, out, err = docker_cp_exec_python(script)
    if rc != 0:
        return 0
    val = (out.strip() or "0").splitlines()[-1].strip()
    try:
        return int(val)
    except (ValueError, IndexError):
        return 0


def parse_info_json(info_raw: str | None) -> dict:
    """Parse the JSON blob from user.info column. Robust to NULL/'null'/None."""
    if not info_raw or info_raw.strip() in ("", "null", "None"):
        return {}
    try:
        v = json.loads(info_raw)
    except Exception:
        return {}
    return v if isinstance(v, dict) else {}


import json  # imported here to avoid shadowing; used by parse_info_json


# ---------- Original endpoints --------------------------------------------
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
            return JSONResponse(results, status_code=500)
    return JSONResponse(results)


@app.post("/down")
def down(_: Annotated[None, Depends(verify_token)]):
    rc, out, err = run(["docker", "compose", "down"], timeout=60)
    return JSONResponse(
        {"rc": rc, "stdout": out, "stderr": err},
        status_code=200 if rc == 0 else 500,
    )


# ---------- Quotas per-user (NEW) ------------------------------------------
@app.get("/quotas")
def list_quotas(_: Annotated[None, Depends(verify_token)]):
    """Liste tous les users Open WebUI + leurs quotas + stockage réel."""
    try:
        rows = read_via_docker(
            'SELECT id, name, email, role, info FROM "user" ORDER BY created_at;'
        )
    except HTTPException:
        raise
    out = []
    for r in rows:
        info = parse_info_json(r.get("info"))
        out.append({
            "id": (r.get("id") or "").strip(),
            "name": (r.get("name") or "").strip(),
            "email": (r.get("email") or "").strip(),
            "role": (r.get("role") or "").strip(),
            "quota_mb": info.get("quota_mb"),
            "allowed_models": info.get("allowed_models") or [],
            "storage_used_mb": get_user_storage_mb((r.get("id") or "").strip()),
        })
    return {
        "users": out,
        "defaults": {
            "global_quota_mb": int(os.environ.get("DEFAULT_USER_QUOTA_MB", "0")),
            "hint": "quota_mb=null means unlimited. 0 in defaults means 'no global cap applied'.",
        },
    }


class QuotaUpdate(BaseModel):
    quota_mb: int | None = None
    allowed_models: list[str] | None = None


@app.post("/quotas/{user_id}")
def set_quota(user_id: str, payload: QuotaUpdate, _: Annotated[None, Depends(verify_token)]):
    """Pose ou met à jour le quota d'un user."""
    if payload.quota_mb is not None and payload.quota_mb < 0:
        raise HTTPException(400, "quota_mb must be >= 0 (or null)")
    try:
        rows = read_via_docker(
            'SELECT info FROM "user" WHERE id = \'' + user_id.replace("'", "''") + '\';'
        )
    except HTTPException:
        raise
    info = parse_info_json(rows[0]["info"] if rows else None)
    if payload.quota_mb is not None:
        info["quota_mb"] = None if payload.quota_mb == 0 else payload.quota_mb
    if payload.allowed_models is not None:
        info["allowed_models"] = payload.allowed_models
    write_user_info_via_docker(user_id, info)
    return {
        "ok": True,
        "user_id": user_id,
        "quota_mb": info.get("quota_mb"),
        "allowed_models": info.get("allowed_models", []),
        "storage_used_mb": get_user_storage_mb(user_id),
    }


@app.delete("/quotas/{user_id}")
def clear_quota(user_id: str, _: Annotated[None, Depends(verify_token)]):
    """Supprime les quotas d'un user (revient à illimité)."""
    try:
        rows = read_via_docker(
            'SELECT info FROM "user" WHERE id = \'' + user_id.replace("'", "''") + '\';'
        )
    except HTTPException:
        raise
    info = parse_info_json(rows[0]["info"] if rows else None)
    info.pop("quota_mb", None)
    info.pop("allowed_models", None)
    write_user_info_via_docker(user_id, info)
    return {"ok": True, "user_id": user_id, "message": "quotas cleared"}


@app.post("/upload-check/{user_id}")
def upload_check(
    user_id: str,
    incoming_mb: int = 0,
    _: Annotated[None, Depends(verify_token)] = None,
):
    """Hook pré-upload. 200 + remaining_mb si OK, 413 si quota dépassé."""
    try:
        rows = read_via_docker(
            'SELECT info FROM "user" WHERE id = \'' + user_id.replace("'", "''") + '\';'
        )
    except HTTPException:
        raise
    if not rows:
        raise HTTPException(404, f"user {user_id} not found")
    info = parse_info_json(rows[0]["info"])
    quota_mb = info.get("quota_mb")
    used = get_user_storage_mb(user_id)
    if quota_mb is not None and used + incoming_mb > quota_mb:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "quota_exceeded",
                "user_id": user_id,
                "quota_mb": quota_mb,
                "used_mb": used,
                "incoming_mb": incoming_mb,
                "message": (
                    f"Quota storage dépassé : {used} MB utilisés sur {quota_mb} MB "
                    f"(upload demandé : {incoming_mb} MB)."
                ),
            },
        )
    return {
        "ok": True,
        "user_id": user_id,
        "quota_mb": quota_mb,
        "used_mb": used,
        "remaining_mb": (quota_mb - used) if quota_mb is not None else None,
    }
