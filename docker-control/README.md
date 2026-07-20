# docker-control — Pilotage Docker depuis Open WebUI

> **Date** : 2026-07-20
> **But** : Permettre à un admin Open WebUI de piloter la stack agentai
> (containers, logs, restart, pull/deploy) directement depuis le chat.

---

## 🏗️ Architecture

```
[Chat Open WebUI]
       │
       │ (tool call HTTP)
       ▼
[Caddy] https://agentai.smartefp.com/api/control/*
       │
       │ (handle_path /api/control/*)
       ▼
[docker-control :9100]  FastAPI + Bearer token
       │
       │ (subprocess docker compose ...)
       ▼
[Docker daemon] sur le VPS
```

## 🔐 Authentification

- Bearer token stocké dans `/opt/agentai/docker-control/.env` (chmod 600, root).
- Token généré par `install.sh` (48 chars base64).
- Le token est aussi à configurer dans le tool Open WebUI (Admin Panel → Tools → Docker Control → champ "api_token").

## 📡 Endpoints

| Méthode | Path | Description |
|---|---|---|
| GET | `/health` | Healthcheck (pas d'auth) |
| GET | `/ps` | Liste des containers + status + ports |
| GET | `/logs/{service}?tail=50` | 50 dernières lignes de logs |
| POST | `/restart/{service}` | Restart d'un service |
| POST | `/up` | `docker compose up -d` (toute la stack) |
| POST | `/pull` | `git pull` + `docker compose pull` + `up -d` (1-3 min) |
| POST | `/down` | `docker compose down` ⚠️ destructif |

Services autorisés : `open-webui`, `llm-proxy`, `agentai-postgres`, `agentai-redis`, `all` (logs seulement).

## 🚀 Installation

```bash
# Sur le VPS (ou via SSH depuis le local)
sudo ./docker-control/install.sh
```

Le script :
1. Crée `/opt/agentai/docker-control/`
2. Crée le venv Python + installe `fastapi`/`uvicorn`
3. Génère un Bearer token dans `.env`
4. Crée le service systemd `docker-control`
5. Patche Caddy pour exposer `/api/control/*`

## 🛠️ Tool Open WebUI

Le fichier [`openwebui-tool.json`](openwebui-tool.json) contient le code du tool
à importer via Admin Panel → Tools → "Import tool from JSON" ou en collant
le code Python dans le textarea.

Le tool expose 7 actions utilisables depuis le chat :
- `list_services()` — voir ce qui tourne
- `get_logs(service, tail)` — récupérer les logs
- `restart_service(service)` — restart un service
- `pull_and_deploy()` — git pull + docker pull + up
- `bring_up()` — `docker compose up -d`
- `bring_down()` — `docker compose down` (destructif)
- `list_allowed_actions()` — lister les actions

### Exemples de prompts

> *"Liste les services qui tournent"*
> *"Montre-moi les 100 dernières lignes de logs d'open-webui"*
> *"Restart open-webui"*
> *"Fais un pull et déploie"*

## 🧪 Test manuel

```bash
# Token
TOKEN=$(ssh prodserveur 'sudo cat /opt/agentai/docker-control/.env' | cut -d= -f2)

# Tests
curl -sS https://agentai.smartefp.com/api/control/health
curl -sS -H "Authorization: Bearer $TOKEN" https://agentai.smartefp.com/api/control/ps
curl -sS -H "Authorization: Bearer $TOKEN" "https://agentai.smartefp.com/api/control/logs/open-webui?tail=10"
```

## 🛡️ Sécurité

- CORS limité à `https://agentai.smartefp.com` uniquement
- Token stocké dans `chmod 600` file, owned par root
- Liste blanche de services (`ALLOWED_SERVICES`)
- Pas d'accès aux commandes arbitraires : uniquement `docker ps/logs/restart/up/down` + `git pull`
- Le tool expose 7 actions atomiques et explicites (pas de "exec arbitrary command")

## 📝 Limitations

- L'endpoint `/pull` fait un `git pull --ff-only` sur la branche locale. Si la
  branche a divergé (rebase, force push), ça échoue. Workaround : faire un
  `git reset --hard origin/<branch>` manuellement.
- Le tool ne montre pas le **diff** du code déployé. Pour voir ce qui a changé,
  il faut aller sur GitHub.
- Le tool ne permet pas de modifier le `.env` ou le `docker-compose.yml`. Pour
  ça, il faut toujours passer par SSH (les secrets ne doivent pas transiter
  par un LLM).

## 🔮 Évolutions

- [ ] Ajouter une UI web simple pour `/pull` (formulaire + log streaming)
- [ ] Intégrer un webhook GitHub → appel direct à `/pull` (sans passer par Open WebUI)
- [ ] Supporter plusieurs stacks (multi-tenant)
- [ ] Logger toutes les actions dans une DB pour audit