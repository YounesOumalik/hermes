#!/usr/bin/env python3
"""Gestion DNS via l'API Contabo OAuth2.

Usage:
    python3 scripts/contabo_dns.py add-a smartefp.com agentai 169.58.30.70
    python3 scripts/contabo_dns.py list-records smartefp.com
    python3 scripts/contabo_dns.py delete-record <record_id>

Configuration (env vars ou prompt au premier lancement) :
    CONTABO_CLIENT_ID, CONTABO_CLIENT_SECRET, CONTABO_USER (email), CONTABO_PASS

Docs API:
    https://api.contabo.com/#tag/DNS
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.parse


def get_token():
    """Authentification OAuth2 client_credentials + password.

    Doc Contabo : POST https://auth.contabo.com/oauth2/token
    """
    url = "https://auth.contabo.com/oauth2/token"
    data = urllib.parse.urlencode({
        "client_id": os.environ["CONTABO_CLIENT_ID"],
        "client_secret": os.environ["CONTABO_CLIENT_SECRET"],
        "grant_type": "client_credentials",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
        return body["access_token"]


def api(method, path, body=None):
    """Appel générique à l'API Contabo."""
    token = get_token()
    url = f"https://dns-service.contabo.net{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def list_zones():
    """Liste toutes les zones DNS gérées par le compte."""
    return api("GET", "/v1/zones")


def find_zone(domain):
    """Trouve la zone correspondant à un domaine."""
    zones = list_zones()
    for z in zones.get("data", []):
        if domain in z.get("domainName", ""):
            return z
    raise ValueError(f"Zone {domain} introuvable. Zones dispo: {[z.get('domainName') for z in zones.get('data', [])]}")


def list_records(domain):
    """Liste les enregistrements d'une zone."""
    zone = find_zone(domain)
    zone_id = zone["zoneId"]
    return api("GET", f"/v1/zones/{zone_id}/records")


def add_a_record(domain, subdomain, ip, ttl=300):
    """Ajoute un A record: <subdomain>.<domain> → <ip>."""
    zone = find_zone(domain)
    zone_id = zone["zoneId"]
    body = {
        "type": "A",
        "name": subdomain,
        "value": ip,
        "ttl": ttl,
    }
    result = api("POST", f"/v1/zones/{zone_id}/records", body)
    print(f"✅ A record créé: {subdomain}.{domain} → {ip}")
    print(f"   ID: {result.get('recordId', '?')}")
    return result


def delete_record(record_id):
    """Supprime un record par son ID."""
    result = api("DELETE", f"/v1/records/{record_id}")
    print(f"✅ Record {record_id} supprimé")
    return result


def check_env():
    """Vérifie que les 4 variables d'env sont définies."""
    missing = [k for k in ("CONTABO_CLIENT_ID", "CONTABO_CLIENT_SECRET", "CONTABO_USER", "CONTABO_PASS")
               if not os.environ.get(k)]
    if missing:
        print(f"❌ Variables d'environnement manquantes : {', '.join(missing)}")
        print("   Définis-les avec :")
        print("     export CONTABO_CLIENT_ID=...")
        print("     export CONTABO_CLIENT_SECRET=...")
        print("     export CONTABO_USER=ton_email@contabo.com")
        print("     export CONTABO_PASS=ton_password")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gestion DNS via API Contabo")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add-a", help="Ajouter un A record")
    p_add.add_argument("domain", help="Domaine (ex: smartefp.com)")
    p_add.add_argument("subdomain", help="Sous-domaine (ex: agentai)")
    p_add.add_argument("ip", help="Adresse IP")
    p_add.add_argument("--ttl", type=int, default=300)

    p_list = sub.add_parser("list-records", help="Lister les records d'une zone")
    p_list.add_argument("domain", help="Domaine (ex: smartefp.com)")

    p_zones = sub.add_parser("list-zones", help="Lister toutes les zones DNS")
    p_del = sub.add_parser("delete-record", help="Supprimer un record par ID")
    p_del.add_argument("record_id", help="ID du record à supprimer")

    args = parser.parse_args()
    check_env()

    if args.cmd == "add-a":
        add_a_record(args.domain, args.subdomain, args.ip, args.ttl)
    elif args.cmd == "list-records":
        records = list_records(args.domain)
        print(f"Records pour {args.domain}:")
        for r in records.get("data", []):
            print(f"  {r.get('type'):4s} {r.get('name'):30s} → {r.get('value'):20s} TTL={r.get('ttl')} ID={r.get('recordId')}")
    elif args.cmd == "list-zones":
        zones = list_zones()
        print("Zones gérées par ce compte:")
        for z in zones.get("data", []):
            print(f"  - {z.get('domainName')} (zoneId={z.get('zoneId')})")
    elif args.cmd == "delete-record":
        delete_record(args.record_id)


if __name__ == "__main__":
    main()