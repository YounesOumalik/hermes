#!/usr/bin/env python3
import sys
import os
import argparse
import paramiko

HOST = "169.58.30.70"
USER = "younes"
# Tester d'abord si la clé a été copiée dans le workspace (pour bypasser le sandbox snap)
WORKSPACE_KEY_PATH = "/home/oumalik-younes/Documents/ProdServeur/id_smartserveur"
HOST_KEY_PATH = "/home/oumalik-younes/.ssh/id_smartserveur"
KEY_PATH = WORKSPACE_KEY_PATH if os.path.exists(WORKSPACE_KEY_PATH) else HOST_KEY_PATH


def get_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Charger la clé privée Ed25519
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    except Exception as e:
        print(f"Error loading private key {KEY_PATH}: {e}")
        sys.exit(1)
        
    try:
        client.connect(hostname=HOST, username=USER, pkey=pkey, timeout=15)
        return client
    except Exception as e:
        print(f"Failed to connect to {USER}@{HOST} via SSH: {e}")
        sys.exit(1)


def execute_command(cmd, verbose=True):
    client = get_ssh_client()
    if verbose:
        print(f"Executing remote command: {cmd}")
    
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # Lire la sortie en continu pour les longs processus
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line, end="")
        
    err_output = stderr.read().decode("utf-8")
    if err_output:
        print(f"STDERR:\n{err_output}", file=sys.stderr)
        
    exit_status = stdout.channel.recv_exit_status()
    client.close()
    return exit_status


def sftp_upload_dir(sftp, local_dir, remote_dir):
    """Upload récursif de dossier via SFTP."""
    os.makedirs(local_dir, exist_ok=True)
    
    # S'assurer que le dossier distant existe
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass  # Déjà existant
        
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = os.path.join(remote_dir, item)
        
        # Ignorer node_modules, .next, __pycache__, .git, etc.
        if any(ignored in local_path for ignored in ["node_modules", ".next", "__pycache__", ".git", "venv"]):
            continue
            
        if os.path.isdir(local_path):
            sftp_upload_dir(sftp, local_path, remote_path)
        else:
            print(f"Uploading: {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)


def upload_path(local_path, remote_path):
    client = get_ssh_client()
    sftp = client.open_sftp()
    
    try:
        if os.path.isdir(local_path):
            sftp_upload_dir(sftp, local_path, remote_path)
        else:
            # S'assurer que le dossier parent distant existe
            remote_parent = os.path.dirname(remote_path)
            try:
                sftp.mkdir(remote_parent)
            except IOError:
                pass
            print(f"Uploading file: {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
        print("Upload completed successfully!")
    finally:
        sftp.close()
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSH Remote helper via Paramiko")
    parser.add_argument("--cmd", type=str, help="Command to execute remotely")
    parser.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"), help="Upload local file or directory to remote")
    
    args = parser.parse_args()
    
    if args.cmd:
        status_code = execute_command(args.cmd)
        sys.exit(status_code)
    elif args.upload:
        upload_path(args.upload[0], args.upload[1])
        sys.exit(0)
    else:
        # Test connection par défaut
        print("Testing SSH connection to prodserveur...")
        client = get_ssh_client()
        print("Connection successful! Remote system information:")
        stdin, stdout, stderr = client.exec_command("uname -a; uptime")
        print(stdout.read().decode("utf-8"))
        client.close()
        sys.exit(0)
