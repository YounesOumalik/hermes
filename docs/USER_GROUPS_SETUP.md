# 👥 Restriction des modèles par utilisateur — Open WebUI

> Mis à jour : 2026-07-20 — pour Open WebUI v0.10.2 sur `agentai.smartefp.com`.

Open WebUI ne supporte pas la **restriction de modèles par utilisateur individuel**.
La seule mécanique native est la **restriction par groupe** (User Groups).

---

## 🚧 Limites de stockage / uploads (déjà appliquées globalement)

Variables `docker-compose.yml` → service `open-webui` :

| Variable | Valeur | Effet |
|---|---|---|
| `RAG_FILE_MAX_SIZE` | `100` | Max 100 MB par fichier uploadé |
| `RAG_FILE_MAX_COUNT` | `20` | Max 20 fichiers par envoi RAG |
| `FOLDER_MAX_FILE_COUNT` | `500` | Max 500 fichiers dans un dossier |
| `USER_PERMISSIONS_CHAT_WEB_UPLOAD` | `False` | Pas d'upload d'URL pour les non-admins |
| `USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS` | `False` | Accès Workspace Models désactivé pour non-admins |
| `USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS` | `False` | Accès Knowledge désactivé |
| `USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS` | `False` | Accès Prompts désactivé |
| `USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS` | `False` | Accès Tools désactivé |

> ⚠️ **Quotas per-user (Go/Disk) NON supportés** nativement par Open WebUI.
> Le stockage du volume `open_webui_data` est partagé (75 Go libres / 96 Go).
> Si tu veux des vrais quotas, il faut un script externe qui surveille `/var/lib/docker/volumes/agentai_open_webui_data/_data/uploads/<user_id>/`.

---

## 👨‍💼 Restreindre les modèles visibles par utilisateur (via User Groups)

### 1. Pré-requis : chaque modèle a un "Group Access"

Sans assignation de groupe, un modèle est **privé** (seul l'admin le voit).
Pour le rendre visible à un groupe, il faut lui attribuer des permissions de groupe.

#### En SQL direct (méthode rapide, recommandée)

```bash
ssh prodserveur
sudo sqlite3 /var/lib/docker/volumes/agentai_open_webui_data/_data/webui.db
```

##### (a) Créer les groupes

```sql
-- Groupe admin = tout voir
INSERT INTO group (id, name, description, permissions, created_at, updated_at, user_ids)
VALUES ('grp-admin', 'Admins', 'Groupe Younes (admin)', '{}', strftime('%s','now')*1000, strftime('%s','now')*1000, '["ff36523b-904a-4ac3-a07b-0802675052b8"]');

-- Groupe standard = modèles limités
INSERT INTO group (id, name, description, permissions, created_at, updated_at, user_ids)
VALUES ('grp-users', 'Standard Users', 'Soukaina + futurs users', '{}', strftime('%s','now')*1000, strftime('%s','now')*1000, '["61d9466c-c5a8-4797-9daf-4964477ad1c9"]');
```

##### (b) Lister les `model.id` disponibles

```sql
SELECT id, name, base_model_id, meta FROM model WHERE name IS NOT NULL ORDER BY name;
```

##### (c) Mettre le groupe en lecture sur un modèle

Pour chaque modèle qu'on veut rendre visible au groupe `Standard Users` :

```sql
UPDATE model
SET access_grants = json_insert(IFNULL(access_grants, '{}'),
  '$.group_read',  json_array('grp-users'),
  '$.group_write', json_array()
)
WHERE id = '<model_id>';
```

> Si `access_grants` n'est pas encore utilisé dans ta version Open WebUI,
> le mécanisme natif est l'**ancienne** colonne `group_ids` :
>
> ```sql
> ALTER TABLE model ADD COLUMN group_ids JSON;
> UPDATE model SET group_ids = json_array('grp-users') WHERE id = '<model_id>';
> ```

##### (d) Verrouiller les modèles côté métadonnées (fallback)

```sql
UPDATE model
SET meta = json_set(IFNULL(meta, '{}'), '$.groupIds', json_array('grp-users'))
WHERE id = '<model_id>';
```

---

### 2. Approche via l'admin UI (méthode officielle, plus safe)

1. Connecte-toi en tant qu'**admin** sur `https://agentai.smartefp.com`.
2. **Admin Panel → Users → Groups** :
   - Crée `Admins` → ajoute `younesoumalik@gmail.com` → permissions par défaut.
   - Crée `Standard Users` → ajoute `soukainaelalmri@gmail.com` → permissions par défaut
     (cocher **"Workspace Models"** + tout ce qui doit être visible).
3. **Admin Panel → Settings → Models** :
   - Pour chaque modèle, ouvre l'éditeur.
   - Section **"Access"** : coche uniquement les groupes autorisés.
4. Les non-admins verront uniquement les modèles cochés pour leur groupe dans le menu déroulant.

> ⚠️ Cette méthode UI n'est pas scriptable et il faut la refaire à chaque ajout de modèle.

---

## 📋 Exemple de matrice recommandée (3 users)

| Groupe | Users | Modèles autorisés |
|---|---|---|
| **Admins** | Younes | Tous (MiniMax + OpenCode Zen — tous les modèles) |
| **Standard Users** | Soukaina | Modèles "safe" seulement : <br>– `gpt-4o-mini` (rapide, pas cher) <br>– `claude-3-haiku` (Anthropic léger) <br>– autres modèles petits |
| **Premium Users** | (futurs users) | + modèles puissants (Claude Sonnet, GPT-4o, etc.) |

---

## 🛠️ Pour aller plus loin : quotas disk per-user (custom)

Si tu veux vraiment des quotas par user (~25 GB/user), il faut ajouter une couche externe :

1. **Quota via XFS/ext4 project quotas** sur le mount du volume.
2. **Script Python dans `docker-control`** qui vérifie `du -sh /var/lib/docker/volumes/agentai_open_webui_data/_data/uploads/<user>/` et bloque les nouveaux uploads si dépassé.
3. **Quota via quotas Docker** (`--storage-opt size=10G` sur la création de user uploads) — pas natif dans Open WebUI.

Pour ta config actuelle (3 users, 75 Go), c'est overkill. **Les limites globales actuelles suffisent largement**.

---

## ✅ À faire maintenant

1. **Redéployer** les variables ajoutées :
   ```bash
   scp docker-compose.yml prodserveur:/srv/agentai/
   ssh prodserveur "cd /srv/agentai && docker compose up -d open-webui"
   ```
2. **Créer les 2 groupes** (SQL ou UI).
3. **Restreindre 2-3 modèles** pour le groupe standard.
4. **Approuver le compte pending** dans Admin → Users (Soukaina El Amri).

Fichier lié : `docker-compose.yml`, `docs/OPENWEBUI_PROVIDERS.md`.
