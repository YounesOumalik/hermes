# Webhook Deploy — Hermes Orchestration

Pattern de déploiement inspiré de `eaumalik.com`.

## Principe

```
git push origin main
       │
       ▼
GitHub → POST /webhook (HMAC SHA-256)
       │
       ▼
Caddy → reverse_proxy 127.0.0.1:9000
       │
       ▼
server.js (systemd: hermes-webhook.service)
   ├─ Vérifie signature HMAC
   ├─ Vérifie ref = refs/heads/main
   └─ Lance deploy-on-push.sh
       │
       ▼
   docker compose build + up -d
   ├─ Healthchecks (4 services)
   ├─ Smoke tests HTTP
   └─ Cleanup vieilles images
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `server.js` | Receiver HTTP (Node.js, port 9000), vérifie HMAC SHA-256 |
| `deploy-on-push.sh` | Build docker compose + healthcheck + smoke test |
| `hermes-webhook.service` | Service systemd pour garder le receiver actif |
| `install-webhook.sh` | Installation one-shot sur le VPS |
| `package.json` | Dépendances Node (aucune, tout est natif) |

## Installation

```bash
# Depuis le poste local
./infra/webhook/install-webhook.sh --remote --repo https://github.com/<user>/ProdServeur.git
```

Le script va :
1. Créer `/opt/hermes-orchestration/{repo,webhook}/`
2. Cloner le repo GitHub
3. Générer un secret HMAC (32 bytes hex)
4. Installer et démarrer le service systemd
5. Afficher le secret à copier dans GitHub

## Configuration GitHub

1. Repo → Settings → Webhooks → Add webhook
2. **Payload URL** : `https://ton-domaine.com/webhook`
3. **Content type** : `application/json`
4. **Secret** : copier la valeur affichée par `install-webhook.sh`
5. **Events** : Just the `push` event

## Configuration Caddy

Ajouter dans `/etc/caddy/Caddyfile` :

```caddy
@hermesWebhook path /webhook /health
handle @hermesWebhook {
    reverse_proxy 127.0.0.1:9000
}
```

Puis `sudo systemctl reload caddy`.

## Vérification

```bash
# Service actif ?
sudo systemctl status hermes-webhook

# Webhook répond ?
curl http://localhost:9000/health

# Logs
sudo journalctl -u hermes-webhook -f

# Déclencher un déploiement manuel (test)
cd /opt/hermes-orchestration/repo
sudo bash deploy-on-push.sh $(git rev-parse HEAD)
```

## Rollback

```bash
# Docker tag les images avec <sha>-<timestamp>
# Lister les images disponibles :
docker images | grep hermes

# Relancer avec une image précédente :
docker compose -f /opt/hermes-orchestration/repo/docker-compose.yml up -d
```
