#!/usr/bin/env python3
"""Upload récursif de la stack AgentAI vers le VPS prodserveur via SFTP (Paramiko).

Usage:
    python3 scripts/upload_stack.py [--dry-run]

Skip automatique des dossiers:
    .git, .venv, venv, node_modules, .next, __pycache__, dist, build,
    .pytest_cache, .mypy_cache, .rename-backup, .vscode, .venv, .gemini

Configuration:
    La clé SSH est lue en priorité depuis :
      1. /home/oumalik-younes/Documents/ProdServeur/id_smartserveur (workspace)
      2. /home/oumalik-younes/.ssh/id_smartserveur (host)
"""
import os
import sys
import argparse
import paramiko
from pathlib import Path

HOST = "169.58.30.70"
USER = "younes"
REMOTE_ROOT = "/srv/agentai"

WORKSPACE_KEY = "/home/oumalik-younes/Documents/ProdServeur/id_smartserveur"
HOST_KEY = "/home/oumalik-younes/.ssh/id_smartserveur"
KEY_PATH = WORKSPACE_KEY if os.path.exists(WORKSPACE_KEY) else HOST_KEY

LOCAL_ROOT = "/home/oumalik-younes/Documents/ProdServeur"

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", ".next", "__pycache__",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".rename-backup",
    ".vscode", ".gemini", "Nebula", "hermes-core", "hermes-daemon",
    "hermes-studio", "infra", "mcp-server", "tools",
}

SKIP_FILES = {
    "id_smartserveur",  # Never upload SSH private keys
    "*.bak", "*.pyc",
}


def should_skip(path: Path) -> bool:
    parts = set(path.relative_to(LOCAL_ROOT).parts)
    if parts & SKIP_DIRS:
        return True
    name = path.name
    for pattern in SKIP_FILES:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
        if name == pattern:
            return True
    return False


def upload(local_path: str, remote_path: str, sftp: paramiko.SFTPClient, dry_run: bool) -> tuple[int, int]:
    """Recursively upload local_path to remote_path. Returns (files_uploaded, dirs_created)."""
    files_count = 0
    dirs_count = 0

    for root, dirs, files in os.walk(local_path):
        rel = Path(root).relative_to(LOCAL_ROOT)
        # Filter out SKIP_DIRS in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for d in dirs:
            local_sub = Path(root) / d
            if should_skip(local_sub):
                continue
            remote_sub = os.path.join(remote_path, rel.as_posix(), d) if rel != Path('.') else os.path.join(remote_path, d)
            if not dry_run:
                try:
                    sftp.mkdir(remote_sub)
                    dirs_count += 1
                except IOError:
                    pass  # already exists

        for f in files:
            local_file = Path(root) / f
            if should_skip(local_file):
                continue
            remote_file = os.path.join(remote_path, rel.as_posix(), f) if rel != Path('.') else os.path.join(remote_path, f)
            if dry_run:
                print(f"  [dry-run] ↑ {local_file.relative_to(LOCAL_ROOT)}")
            else:
                try:
                    sftp.put(str(local_file), remote_file)
                    files_count += 1
                except Exception as e:
                    print(f"  ❌ {local_file.relative_to(LOCAL_ROOT)}: {e}")

    return files_count, dirs_count


def main():
    parser = argparse.ArgumentParser(description="Upload AgentAI stack to VPS via SFTP")
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    parser.add_argument("--host", default=HOST, help=f"VPS hostname/IP (default: {HOST})")
    parser.add_argument("--user", default=USER, help=f"SSH user (default: {USER})")
    parser.add_argument("--remote-root", default=REMOTE_ROOT, help=f"Remote root (default: {REMOTE_ROOT})")
    args = parser.parse_args()

    print(f"🔑 Using SSH key: {KEY_PATH}")
    if not os.path.exists(KEY_PATH):
        print(f"❌ Clé SSH introuvable : {KEY_PATH}")
        print(f"   Copie-la avec : cp ~/.ssh/id_smartserveur {WORKSPACE_KEY}")
        sys.exit(1)

    print(f"📤 Local:  {LOCAL_ROOT}")
    print(f"📍 Remote: {args.user}@{args.host}:{args.remote_root}")

    if args.dry_run:
        print("\n=== DRY-RUN (no upload) ===")
        files, dirs = upload(LOCAL_ROOT, args.remote_root, None, dry_run=True)
        print(f"\n[DRY-RUN] {files} files, {dirs} dirs would be uploaded")
        return

    # Connect SSH
    print("\n🔌 Connexion SSH...")
    pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(args.host, username=args.user, pkey=pkey, timeout=15)
    except Exception as e:
        print(f"❌ Connexion SSH échouée : {e}")
        sys.exit(1)

    print(f"✅ Connecté à {args.host}")

    # Create remote root
    sftp = ssh.open_sftp()
    try:
        sftp.mkdir(args.remote_root)
        print(f"✅ Dossier créé: {args.remote_root}")
    except IOError:
        print(f"⏭️  Dossier existe déjà: {args.remote_root}")

    # Upload recursively
    print(f"\n📦 Upload en cours (skip: {', '.join(sorted(SKIP_DIRS))})...")
    files_count, dirs_count = upload(LOCAL_ROOT, args.remote_root, sftp, dry_run=False)

    sftp.close()
    ssh.close()

    print(f"\n✅ Upload terminé: {files_count} fichiers uploadés, {dirs_count} dossiers créés")


if __name__ == "__main__":
    main()