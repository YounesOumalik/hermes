# Open WebUI — Connexion au provider MiniMax

> **Statut** : ✅ Documenté le 2026-07-20, après migration de la stack agentai vers
> Open WebUI officiel (`ghcr.io/open-webui/open-webui:main`).
>
> **Pré-requis** :
> - Open WebUI déployé et accessible sur `https://agentai.smartefp.com`
> - Compte Google autorisé en admin (via `scripts/promote-openwebui-admin.sh`)
> - Clé API MiniMax valide (`sk-...` ou similaire) — voir [https://api.minimax.io](https://api.minimax.io)

---

## 🎯 Pourquoi cette procédure

Le `hermes-llm-proxy` historique attendait un format propriétaire
(`model_config_id: UUID`) incompatible avec l'API OpenAI standard.
Open WebUI parle nativement le **format OpenAI**, donc on configure
directement l'endpoint public MiniMax dans l'UI Admin.

---

## 📋 Procédure

### Étape 1 — Connexion en admin

1. Va sur [https://agentai.smartefp.com](https://agentai.smartefp.com)
2. Connecte-toi avec Google (`younesoumalik@gmail.com`)
3. Clique sur **ton avatar** en haut à droite → **Admin Panel**

> ⚠️ Si tu ne vois pas "Admin Panel" : ton user est encore en `pending`.
> Connecte-toi d'abord une fois (statut pending), puis :
> ```bash
> ./scripts/promote-openwebui-admin.sh younesoumalik@gmail.com
> ```
> Reconnecte-toi ensuite (vide les cookies si besoin).

### Étape 2 — Section Connections

Dans le panneau admin :

```
Admin Panel
└── Settings
    └── Connections   ← ici
```

Tu verras plusieurs sections :
- **OpenAI API** (le provider natif, accepte toutes les API compatibles)
- **Ollama API** (si tu utilises Ollama en local)
- **Direct Connections** (connections custom)

### Étape 3 — Configurer MiniMax

Dans la section **OpenAI API**, remplis :

| Champ | Valeur |
|---|---|
| **URL** | `https://api.minimax.io/v1` |
| **API Key** | *ta vraie clé MiniMax — ne pas commit, ne pas logger* |

Puis clique sur **+ Add** (ou l'icône de sauvegarde).

> 💡 Astuce : tu peux nommer cette connexion `MiniMax` pour la retrouver
> facilement dans la liste. Open WebUI supporte plusieurs connexions
> OpenAI-compat en parallèle.

### Étape 4 — Vérifier / ajouter les modèles

Une fois la connexion créée, Open WebUI peut :
- **Pull models** : clique sur le bouton de rafraîchissement à côté de la
  connexion → il va lister les modèles disponibles côté MiniMax. Tu devrais
  voir quelque chose comme :
  ```
  MiniMax-M3
  MiniMax-M2.7
  MiniMax-M2.7-highspeed
  MiniMax-M2.5
  MiniMax-M2.1
  MiniMax-M2
  ```
- **Add manually** : si le pull ne marche pas, tu peux ajouter un modèle
  custom avec l'ID exact (par ex. `MiniMax-M2.7`).

### Étape 5 — Tester

1. Retourne sur la page principale d'Open WebUI
2. En haut, sélecteur de modèle → choisis `MiniMax-M2.7` (ou autre)
3. Tape : `Bonjour, qui es-tu ?`
4. Tu devrais recevoir une réponse de MiniMax

---

## 🛠️ Troubleshooting

### Le modèle n'apparaît pas après "Pull models"

- Vérifie que ta clé API est valide (teste-la avec `curl` directement) :
  ```bash
  curl -sS https://api.minimax.io/v1/models \
    -H "Authorization: Bearer $MINIMAX_API_KEY"
  ```
- Vérifie que l'URL est bien `https://api.minimax.io/v1` (avec `/v1`)
- Le réseau `agentai-net` doit sortir vers Internet (vérifie
  `docker network inspect agentai-net`)

### Erreur 401 Unauthorized au 1er chat

- Ta clé API est invalide ou révoquée
- Récupère-en une nouvelle sur le dashboard MiniMax

### Erreur "Connection refused" sur l'URL du llm-proxy

C'est **normal** et **attendu** : on n'utilise PAS `hermes-llm-proxy` dans
cette config. L'`OPENAI_API_BASE_URL=http://llm-proxy:8001/v1` du compose
est conservé pour référence mais inopérant (le proxy attend un format
propriétaire). Tu peux le retirer du compose si tu veux.

### Erreur "Model not found" avec un ID custom

Vérifie que l'ID du modèle **EXACT** correspond à celui listé par MiniMax.
Les noms sont sensibles à la casse : `MiniMax-M2.7` ≠ `minimax-m2.7`.

---

## 📚 Modèles MiniMax recommandés

| Modèle | Usage | Coût approx. |
|---|---|---|
| `MiniMax-M3` | Dernier flagship, multimodal, raisonnement avancé | $$$ |
| `MiniMax-M2.7` | Bon ratio qualité/prix, polyvalent | $$ |
| `MiniMax-M2.7-highspeed` | Variante rapide de M2.7 (latence réduite) | $$ |
| `MiniMax-M2.5` | Stable, bien testé | $ |
| `MiniMax-M2.1` | Plus ancien, peu cher | $ |
| `MiniMax-M2` | Legacy | $ |

> Le défaut dans `.env.template` est `MiniMax-M2.7` (sweet spot qualité/coût).

---

## 🔮 Évolutions futures

### Recoder `hermes-llm-proxy` en format OpenAI-compat

Aujourd'hui, Open WebUI appelle directement `api.minimax.io`. Si tu veux
faire passer **toutes** les requêtes par `hermes-llm-proxy` (pour la
facturation, le rate limiting, le logging centralisé, etc.), il faut
recoder le proxy pour qu'il accepte le format OpenAI standard :

```python
# Format OpenAI standard (ce qu'Open WebUI envoie)
{
  "model": "MiniMax-M2.7",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.7,
  "stream": true
}

# Format actuel d'hermes-llm-proxy (incompatible)
{
  "model_config_id": "uuid-here",
  "messages": [...],
  ...
}
```

Effort estimé : ~30 min de dev (réécrire `router.py` + ajouter un
endpoint `/v1/models` qui liste les modèles depuis la DB).

### Stocker les clés API en DB (chiffrées)

Actuellement les clés sont en `.env` ou en dur. Pour une vraie gestion
multi-provider, il faudrait une table `api_keys` (déjà présente dans
`hermes-nebula-api/app/models/api_key.py`) avec chiffrement AES-GCM.

---

## ✅ Validation post-setup

Une fois MiniMax configuré, vérifie que :

- [ ] Le sélecteur de modèle en haut à gauche montre au moins 1 modèle MiniMax
- [ ] Tu peux envoyer un message et recevoir une réponse
- [ ] L'indicateur "model loaded" s'affiche correctement
- [ ] Le streaming fonctionne (réponse apparaît progressivement)

Si tous ces points sont OK, ta stack est **complètement opérationnelle**.