# Open WebUI — Connexion aux providers LLM

> **Statut** : ✅ Documenté le 2026-07-20, après migration de la stack agentai vers
> Open WebUI officiel (`ghcr.io/open-webui/open-webui:main`).
>
> **Pré-requis** :
> - Open WebUI déployé et accessible sur `https://agentai.smartefp.com`
> - Compte Google autorisé en admin (via `scripts/promote-openwebui-admin.sh`)
> - Clé(s) API valide(s) pour le(s) provider(s) souhaité(s)

## 📑 Providers supportés

| Provider | Endpoint | Modèles | Auth | Doc |
|---|---|---|---|---|
| **MiniMax** | `https://api.minimax.io/v1` | M3, M2.7, M2.7-highspeed, M2.5, M2.1, M2 | Bearer | https://api.minimax.io |
| **OpenCode Zen** | `https://opencode.ai/zen/v1` | GPT 5.x, Claude 4.x, Gemini 3.x, MiniMax M3/M2.7/M2.5, GLM 5.x, Kimi K2.x, DeepSeek V4, Grok 4.x, etc. | Bearer | https://opencode.ai/docs/zen/ |

> 💡 **Pourquoi Zen plutôt qu'OpenAI direct ?** Zen négocie les prix,
> sélectionne les meilleures versions de chaque modèle, et reverse les
> baisses de prix au consommateur. Pour un usage coding/agent, c'est
> souvent le meilleur rapport qualité/prix.

---

## 🎯 Pourquoi cette procédure

Le `hermes-llm-proxy` historique attendait un format propriétaire
(`model_config_id: UUID`) incompatible avec l'API OpenAI standard.
Open WebUI parle nativement le **format OpenAI**, donc on configure
directement les endpoints publics (MiniMax, Zen) dans l'UI Admin.

Open WebUI permet d'ajouter **plusieurs connexions OpenAI-compat en parallèle**.
On peut donc avoir MiniMax + Zen + d'autres simultanément, et choisir
modèle par modèle dans le sélecteur.

---

## 📋 Procédure générique (valable pour tout provider OpenAI-compat)

### Étape 1 — Connexion en admin

1. Va sur [https://agentai.smartefp.com](https://agentai.smartefp.com)
2. Connecte-toi avec Google
3. Clique sur **ton avatar** en haut à droite → **Admin Panel**

> ⚠️ Si tu ne vois pas "Admin Panel" : ton user est encore en `pending`.
> ```bash
> ./scripts/promote-openwebui-admin.sh younesoumalik@gmail.com
> ```

### Étape 2 — Section Connections

```
Admin Panel
└── Settings
    └── Connections
```

### Étape 3 — Ajouter une connexion OpenAI-compat

Dans la section **OpenAI API** (ou **Direct Connections** pour un nom custom),
remplis :

| Champ | MiniMax | OpenCode Zen |
|---|---|---|
| **URL** | `https://api.minimax.io/v1` | `https://opencode.ai/zen/v1` |
| **API Key** | `sk-...` (depuis dashboard MiniMax) | `sk-...` (depuis https://opencode.ai/auth) |

Clique sur **+ Add**. Tu peux nommer la connexion (`MiniMax`, `Zen`, etc.)
pour la retrouver dans le sélecteur de modèle.

### Étape 4 — Pull models

Une fois la connexion créée, clique sur l'icône **refresh** à côté.
Open WebUI va appeler `<url>/models` et lister tous les modèles disponibles.

- Pour **MiniMax** : `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`, etc.
- Pour **Zen** : `gpt-5.6-sol`, `claude-opus-4-8`, `gemini-3.1-pro`,
  `minimax-m3`, `kimi-k2.7-code`, `deepseek-v4-pro`, etc. (40+ modèles)

Tu peux activer uniquement ceux que tu veux voir dans le sélecteur global.

### Étape 5 — Tester

1. Retourne sur la page principale d'Open WebUI
2. Sélecteur de modèle en haut → choisis un modèle
3. Tape un message → tu reçois une réponse

---

## 🛠️ Troubleshooting

### "Aucun modèle disponible" après Pull

- Vérifie ta clé API :
  ```bash
  # MiniMax
  curl -sS https://api.minimax.io/v1/models -H "Authorization: Bearer $MINIMAX_API_KEY" | jq '.data[].id'

  # Zen
  curl -sS https://opencode.ai/zen/v1/models -H "Authorization: Bearer $ZEN_API_KEY" | jq '.data[].id'
  ```
- Vérifie l'URL (avec `/v1` à la fin)
- Teste depuis le container :
  ```bash
  ssh prodserveur "docker exec open-webui curl -sS https://opencode.ai/zen/v1/models -H 'Authorization: Bearer xxx'"
  ```

### 401 Unauthorized au 1er chat

Clé invalide ou révoquée. Récupère-en une nouvelle sur le dashboard du provider.

### 404 sur un modèle spécifique

Zen peut renvoyer 404 si le modèle est obsolète (cf. leur liste de
modèles dépréciés). Retire-le de la liste active.

### Rate limit / quota dépassé

- Zen : recharge auto de $20 quand le solde passe sous $5 (configurable).
  Tu peux le désactiver depuis le dashboard Zen.
- MiniMax : pas de rate limit public, juste facturation à l'usage.

---

## 📚 Modèles recommandés (sélection)

### Pour le coding
- **Zen — Claude Sonnet 4.5 / 4.6** : référence pour le code, $3/$15 par M tokens
- **Zen — Kimi K2.7 Code** : excellent en code, $0.95/$4 par M tokens
- **Zen — GPT 5.4** : bon polyvalent code
- **MiniMax — MiniMax-M2.7** : bon pour les tâches plus larges

### Pour le chat général
- **Zen — Claude Haiku 4.5** : rapide et pas cher ($1/$5)
- **Zen — Gemini 3 Flash** : $0.50/$3
- **Zen — MiniMax M3 / M2.7** : via Zen, mêmes prix que direct

### Pour le raisonnement avancé
- **Zen — Claude Opus 4.8** : $5/$25 — top du top
- **Zen — GPT 5.5 Pro** : $30/$180 — cher mais très fort
- **Zen — Qwen3.7 Max** : $2.50/$7.50 — bon compromis

### Gratuits (pour tester sans frais)
- **Zen — DeepSeek V4 Flash Free**, **Big Pickle**, **MiMo-V2.5 Free**,
  **North Mini Code Free**, **Nemotron 3 Ultra Free** — tous gratuits,
  attention à la confidentialité (données potentiellement utilisées
  pour améliorer les modèles).

---

## 🔮 Évolutions futures

### Recoder `hermes-llm-proxy` en format OpenAI-compat

Aujourd'hui, Open WebUI appelle directement les providers. Si tu veux
faire passer **toutes** les requêtes par `hermes-llm-proxy` (pour la
facturation centralisée, le rate limiting, le logging), il faut recoder
le proxy pour qu'il accepte le format OpenAI standard. Effort ~30 min.

### Multi-comptes Zen / MiniMax

Open WebUI permet à chaque user d'avoir **ses propres clés API**
(préférences user). Tu peux activer ça pour que chacun puisse utiliser
son compte Zen/MiniMax avec ses propres crédits.

---

## ✅ Validation post-setup

Pour chaque provider configuré, vérifie que :

- [ ] La connexion est listée dans Admin → Connections
- [ ] Au moins 1 modèle apparaît dans le sélecteur
- [ ] Un chat test renvoie une réponse cohérente
- [ ] Le streaming fonctionne (réponse progressive)
- [ ] Pas de warning CORS dans la console dev

Si tous ces points sont OK, ta stack est **complètement opérationnelle**.