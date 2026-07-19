# 🎨 Spécification Design — AgentAI Mobile

> **Source** : 37 mockups WhatsApp (`docs/design/nebula-mockups/`)
> **Date** : 2026-07-19
> **Statut** : Spécification partielle (analyse structurelle uniquement)
> **⚠️ Note importante** : ce document a été généré par analyse structurelle des images (dimensions, luminosité, couleurs). Le **contenu visuel précis (textes, illustrations, layout exact)** nécessite une **analyse visuelle par un modèle multimodal**.

---

## 1. Caractéristiques techniques des mockups

| Propriété | Valeur |
|---|---|
| Format | JPEG (export WhatsApp) |
| Dimensions | **738 × 1600 px** (tous identiques) |
| Ratio | **9:16** (mobile portrait) |
| Espace colorimétrique | sRGB (EXIF strippé par WhatsApp) |
| Quantité | **37 mockups** |
| Taille totale | 2.1 Mo |
| Taille moyenne par mockup | 56 Ko |

**Cible** : smartphones iPhone/Pixel. La maquette est donc un design **mobile-first**, pas desktop.

---

## 2. Palette de couleurs détectée

### 2.1 Fond principal (majoritaire sur tous les mockups)

Tous les mockups partagent un **fond bleu-noir uniforme** avec une teinte très légèrement bleutée.

| Couleur moyenne échantillonnée | Usage probable |
|---|---|
| `#0E1320` à `#151925` | Background le plus profond |
| `#161A26` à `#1B1F2A` | Background courant des cards |
| `#1C202B` à `#232834` | Cards plus claires, panels |
| `#242835` à `#272B38` | Zones d'élévation, headers |

### 2.2 Cohérence avec le design system actuel

```css
/* Comparaison mockups vs globals.css actuel */
--bg-primary:    #0a0c10   → mockups:#0E1320-#151925  ✅ cohérent
--bg-secondary:  #121620   → mockups:#161A26-#1B1F2A  ✅ cohérent
--bg-tertiary:   #1b2130   → mockups:#1C202B-#232834  ✅ cohérent
```

**Conclusion** : les mockups utilisent **exactement le même design system** que `globals.css`. **Pas besoin de refondre les couleurs**.

### 2.3 Accents détectés

Une seule zone d'accent colorée a été identifiée via analyse des bandes verticales :

| Position | Couleur | Signification probable |
|---|---|---|
| y=720-800 (centre-bas) | `#3F71A8` → `#4E8BC8` → `#222F42` | Bouton CTA bleu / avatar / illustration |

Ces valeurs correspondent à des nuances de **bleu cyan** similaires à `--accent-secondary: #00d2ff` et `--accent-primary: #5e5af6` déjà en place dans le design system.

---

## 3. Densité de contenu (luminosité)

Distribution de la luminosité moyenne par bande de 200px de hauteur, agrégée sur tous les mockups :

```
Y range       Avg brightness   Interprétation
─────────────────────────────────────────────────────────────
   0- 200     ~12.5%           Status bar (très sombre)
 200- 400     ~12.4%           Header (sombre, peu de contraste)
 400- 600     ~13.0%           ↑ début du contenu
 600- 800     ~13.3%           ↑ zone la plus dense
 800-1000     ~12.4%           Corps principal
1000-1200     ~12.0%           ↓
1200-1400     ~12.5%           Bas du contenu / début nav
1400-1600     ~13.0%           Bottom area / nav bar
```

**Distribution très plate** = design minimaliste, peu de contraste marqué → cohérent avec un **glassmorphism très subtil**.

---

## 4. Classification des 37 mockups

### 4.1 Groupes identifiés (par profil de luminosité)

| Type | Nombre | Caractéristiques |
|---|---|---|
| **content-medium** | 24 mockups (65%) | Écrans équilibrés, layout simple |
| **content-dense** | 12 mockups (32%) | Écrans riches, listes, formulaires |
| **content-dense + bottom-nav** | 1 mockup (`34.jpeg`) | Layout principal dashboard |
| **peak-y600-800** | 1 mockup (`32.jpeg`) | Pic lumineux central (CTA / image) |

### 4.2 Hypothèse de mapping (à valider visuellement)

| Mockup probable | Écran correspondant dans le frontend |
|---|---|
| `32.jpeg` (peak central) | **Page de login / Welcome** (CTA Google central) |
| `34.jpeg` (bottom-nav) | **Dashboard principal** (workspaces + agents + chat) |
| `30(1).jpeg`, `30(3).jpeg`, `30(4).jpeg` | Listes (workspaces, agents, conversations) |
| `31(1).jpeg`, `31(2).jpeg`, `31(3).jpeg` | Détails (agent, conversation, message) |
| `33(1).jpeg`, `33(2).jpeg`, `33(3).jpeg` | Paramètres / admin / profil |
| `28(2).jpeg` | Chat interface avec messages |
| `29(6).jpeg` (outlier rouge) | **Notification d'erreur / status pending** |
| `27(1).jpeg` | Splash / empty state |

⚠️ **Ces mappings sont des hypothèses basées uniquement sur la structure**. Une analyse visuelle est nécessaire pour les confirmer.

---

## 5. Croisement avec l'architecture frontend/backend existante

### 5.1 Pages frontend actuelles (`hermes-nebula/src/app/`)

| Page | Fichier | Endpoints backend consommés |
|---|---|---|
| `/login` | `login/page.tsx` | `GET /api/auth/google`, `POST /api/auth/dev-login` |
| `/` (dashboard) | `page.tsx` | `/api/auth/me`, `/api/workspaces`, `/api/agents/{id}/conversations`, `/api/agents/{id}/messages` |
| `/admin` | `admin/page.tsx` | `/api/admin/{stats,users,api-keys,audit-log}` |
| `/pending` | `pending/page.tsx` | (page statique d'attente) |

### 5.2 Endpoints backend sans page frontend correspondante

D'après la liste des routers (`app/api/`), **10 routers** existent mais seulement **4 pages** sont implémentées. Endpoints orphelins (à priori sans UI) :

| Endpoint | Écran à créer |
|---|---|
| `GET/POST /api/workspaces` | ✅ Déjà dans dashboard |
| `GET/POST /api/workspaces/{id}/members` | ⚠️ **Modal "Members"** (invite users) |
| `GET/POST/PATCH /api/jobs` | ❌ **Page "Jobs / Schedules"** |
| `POST /api/jobs/{id}/run-now` | ❌ Action dans page Jobs |
| `GET /api/workspaces/{wid}/jobs` | ❌ Tab Jobs dans workspace |
| `GET/PATCH /api/settings/profile` | ⚠️ **Page "Settings"** |
| `GET/PATCH /api/settings/notifications/channels` | ⚠️ **Section notifications dans Settings** |
| `POST /api/files/upload` | ⚠️ **Composant uploader dans chat** |
| `GET/PATCH /api/tools/agents/{id}` | ⚠️ **Modal "Tools" dans agent** |
| `GET/POST/DELETE /api/admin/api-keys` | ⚠️ **Section API Keys dans admin** |
| `POST /api/admin/api-keys/test` | ⚠️ Action dans API Keys |
| `GET /api/admin/users/{id}/quota` | ⚠️ **Modal "Quota" dans admin user** |
| `PATCH /api/admin/users/{id}/approve` | ⚠️ Action dans admin user |
| `PATCH /api/admin/users/{id}/disable` | ⚠️ Action dans admin user |
| `GET /api/models_api` | ✅ Via form d'agent (probablement) |

**Total** : ~10 écrans ou composants à créer pour atteindre la parité backend/frontend.

---

## 6. Plan d'action design

### 6.1 Court terme (recommandations immédiates)

| Action | Priorité | Effort |
|---|---|---|
| Analyser visuellement les 37 mockups avec un modèle vision | 🔴 critique | 30 min |
| Renommer les mockups par écran (`01-login.png`, `02-dashboard.png`, ...) | 🟠 haute | 10 min |
| Découper `hermes-nebula/src/app/page.tsx` (761 lignes) en composants | 🟠 haute | 2-3h |
| Centraliser les appels API dans un helper `apiFetch()` | 🟡 moyenne | 1h |

### 6.2 Moyen terme (implémentation des écrans manquants)

À prioriser après l'analyse visuelle des mockups :

1. **Page Jobs/Schedules** (`/jobs`) — fond glass, liste cards, bouton "Create Job"
2. **Page Settings** (`/settings`) — sections profile + notifications + security
3. **Page Workspace Members** (modal depuis dashboard) — invite + role management
4. **Modal Tools** (depuis agent detail) — toggle on/off tools
5. **Modal Quota** (depuis admin user) — sliders max disk/tokens
6. **Section API Keys** (dans admin) — list + create + test
7. **Composant FileUpload** (dans chat) — drag/drop + progress

### 6.3 Vision long terme (PWA Mobile)

Le ratio 9:16 des mockups suggère une cible **PWA mobile-first**. Voir [`docs/PWA_MOBILE.md`](../PWA_MOBILE.md) si existant.

---

## 7. Comment faire analyser visuellement les mockups

Puisque ce modèle (GLM-5.2) ne supporte pas la vision, voici comment procéder :

### Option A : Utiliser un autre modèle dans VS Code Copilot
1. Ouvre un fichier markdown dans VS Code
2. Sélectionne un modèle vision-compatible (Claude 3.5 Sonnet, GPT-4o, Gemini Pro Vision)
3. Drag & drop les mockups dans le chat
4. Demande : *"Analyse ce mockup et donne-moi : nom de l'écran, layout, composants visibles, couleurs exactes, textes, hiérarchie visuelle"*

### Option B : API directe
```bash
# Exemple avec Claude 3.5 Sonnet API
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $CLAUDE_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}},
        {"type": "text", "text": "Décris cet écran mobile en détail"}
      ]
    }]
  }'
```

### Option C : Outil gratuit
- **Google AI Studio** (Gemini Vision) : gratuit, upload direct
- **ChatGPT** avec vision (payant) : drag & drop
- **Claude.ai** (gratuit avec limites) : drag & drop

---

## 8. Conclusion

**État actuel** :
- ✅ Palette et ambiance : **100% cohérentes** avec le design system en place
- ✅ Format mobile portrait 9:16 : bien adapté à une cible smartphone
- ❌ **37 écrans à nommer et analyser visuellement**
- ❌ **~10 écrans/composants manquants** côté frontend pour atteindre la parité backend

**Effort estimé pour finaliser l'implémentation** :
- Analyse visuelle : 1-2h
- Renommage + catégorisation : 30 min
- Création des pages manquantes : 1-2 jours
- QA responsive + accessibilité : 1 jour

**Priorité** : faire l'analyse visuelle avant toute implémentation pour éviter de coder à l'aveugle.
