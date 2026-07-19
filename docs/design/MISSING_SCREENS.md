# 📋 Écrans Manquants — Roadmap Frontend AgentAI

> **Date** : 2026-07-19
> **Source** : croisement entre routers backend existants et pages frontend actuelles
> **Cible** : atteindre la parité backend ↔ frontend

---

## 1. État actuel du frontend

### 1.1 Pages implémentées

| Route | Fichier | Lignes | Fonctionnalités |
|---|---|---|---|
| `/login` | `src/app/login/page.tsx` | 172 | Google OAuth + dev login |
| `/` | `src/app/page.tsx` | 761 | Dashboard : workspaces, agents, conversations, chat |
| `/admin` | `src/app/admin/page.tsx` | 586 | Stats, users, API keys, audit log |
| `/pending` | `src/app/pending/page.tsx` | 95 | Page d'attente (compte en validation) |
| `/` (root layout) | `src/app/layout.tsx` | 35 | HTML + fonts + globals |

**Total** : 1649 lignes — frontend minimal mais fonctionnel.

### 1.2 Endpoints backend consommés vs disponibles

D'après les 10 routers (`hermes-nebula-api/app/api/`), voici la **couverture actuelle** :

| Router | Endpoints totaux | Endpoints consommés par le frontend | Couverture |
|---|---|---|---|
| `auth` | 5 | 5 (google, callback, dev-login, refresh, me) | ✅ 100% |
| `workspaces` | 7 | 4 (list, create, get, members manquants) | ⚠️ 57% |
| `agents` | 5 | 4 (list, create, get, patch, delete partiels) | ⚠️ 80% |
| `chat` | 4 | 4 | ✅ 100% |
| `tools` | 3 | 1 (list) | ⚠️ 33% |
| `models_api` | 1 | 1 | ✅ 100% |
| `admin` | 11 | 4 (stats, users, api-keys, audit-log) | ⚠️ 36% |
| `jobs` | 7 | 0 | ❌ 0% |
| `settings` | 3 | 0 | ❌ 0% |
| `files` | 2 | 0 | ❌ 0% |

**Couverture globale** : **28/48 endpoints consommés = 58%**.

---

## 2. Écrans et composants à créer

### 2.1 🔴 Priorité haute (fonctionnalités cœur)

#### 2.1.1 Page Jobs / Schedules (`/jobs`)
**Endpoints disponibles** :
- `GET /api/workspaces/{wid}/jobs`
- `POST /api/workspaces/{wid}/jobs`
- `GET /api/jobs/{id}`
- `PATCH /api/jobs/{id}`
- `DELETE /api/jobs/{id}`
- `GET /api/jobs/{id}/runs`
- `POST /api/jobs/{id}/run-now`

**Écran proposé** : Liste des jobs planifiés + bouton "Create Job" + drawer détail.

```
┌─────────────────────────────────────┐
│  ⬅ Jobs                       ＋   │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐   │
│  │ Daily Standup Reporter       │   │
│  │ Cron: 0 9 * * * · Active     │   │
│  │ Next run: in 8h              │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Weekly Code Review Summary   │   │
│  │ Cron: 0 17 * * 5 · Paused   │   │
│  │ Last run: 2d ago · ✓ success │   │
│  └─────────────────────────────┘   │
│  ...                                │
└─────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/app/jobs/page.tsx`
- `src/components/jobs/JobCard.tsx`
- `src/components/jobs/CreateJobModal.tsx`

**Mockups Nebula probables** : `#15`, `#16`, `#25`, `#35` (list-or-content)

---

#### 2.1.2 Page Settings (`/settings`)
**Endpoints disponibles** :
- `PATCH /api/settings/profile`
- `GET /api/settings/notifications/channels`
- `PATCH /api/settings/notifications/channels/{id}`

**Écran proposé** : Tabs `Profile` | `Notifications` | `Security`.

```
┌─────────────────────────────────────┐
│  ⬅ Settings                         │
├─────────────────────────────────────┤
│  ┌─[Profile]─[Notifications]──┐     │
│  │                            │     │
│  │  Display name               │     │
│  │  ┌──────────────────────┐  │     │
│  │  │ Younes Oumalik       │  │     │
│  │  └──────────────────────┘  │     │
│  │                            │     │
│  │  Username                   │     │
│  │  ┌──────────────────────┐  │     │
│  │  │ younes               │  │     │
│  │  └──────────────────────┘  │     │
│  │                            │     │
│  │       [Save changes]        │     │
│  └────────────────────────────┘     │
└─────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/app/settings/page.tsx`
- `src/components/settings/ProfileTab.tsx`
- `src/components/settings/NotificationsTab.tsx`

**Mockups Nebula probables** : `#02`, `#08`, `#12`, `#22` (onboarding / minimal)

---

#### 2.1.3 Composant File Upload (intégré au chat)
**Endpoints disponibles** :
- `POST /api/files/upload`
- `GET /api/files/{id}`

**Composant proposé** : Drag & drop zone + progress bar dans la chat box.

```
┌─────────────────────────────────────────────┐
│  Message input...                            │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │  📎 Drop files here or click           │  │
│  │     (max 10 MB)                       │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│  ▓▓▓▓▓▓▓▓▓░░░░░░░░░  62% · report.pdf     │
└─────────────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/components/chat/FileUploader.tsx`
- (modifier `src/app/page.tsx` pour intégrer)

**Mockups Nebula probables** : `#14`, `#31` (cta-or-detail-screen)

---

### 2.2 🟠 Priorité moyenne (collaboration / partage)

#### 2.2.1 Modal Workspace Members
**Endpoints disponibles** :
- `GET /api/workspaces/{id}/members`
- `POST /api/workspaces/{id}/members`

**Composant proposé** : Bottom-sheet modal depuis le workspace actif.

```
┌─────────────────────────────────────┐
│  Workspace Members           ✕      │
├─────────────────────────────────────┤
│  Invite member by email             │
│  ┌──────────────────────────┐ [➤]  │
│  │ email@example.com        │      │
│  └──────────────────────────┘      │
│                                     │
│  Members                             │
│  • younes@eaumalik.com (owner)      │
│  • alice@example.com (member)       │
│  • bob@example.com (admin)          │
└─────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/components/workspace/MembersModal.tsx`
- (intégrer dans `src/app/page.tsx`)

---

#### 2.2.2 Modal Tools (sur agent detail)
**Endpoints disponibles** :
- `GET /api/agents/{id}/tools`
- `PATCH /api/agents/{id}/tools/{tid}`

**Composant proposé** : Liste de toggles pour activer/désactiver les tools sur un agent.

```
┌─────────────────────────────────────┐
│  Agent Tools                 ✕      │
├─────────────────────────────────────┤
│  ☐ Web Search            slug:web   │
│  ☐ Code Interpreter      slug:code  │
│  ☐ File Reader           slug:file  │
│  ☑ Email Sender          slug:email │
│  ☐ Calendar              slug:cal   │
└─────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/components/agents/ToolsModal.tsx`
- (intégrer dans `src/app/page.tsx` ou agent detail)

---

### 2.3 🟡 Priorité basse (admin / config avancée)

#### 2.3.1 Modal Quota (admin user detail)
**Endpoints disponibles** :
- `GET /api/admin/users/{id}/quota`
- `PATCH /api/admin/users/{id}/quota`

**Composant proposé** : Sliders pour disk/tokens + liste des modèles/tools autorisés.

```
┌─────────────────────────────────────┐
│  Quota · alice@example.com    ✕    │
├─────────────────────────────────────┤
│  Max disk: ▓▓▓▓▓░░░░░  5 GB         │
│  Used: 1.2 GB                       │
│                                     │
│  Max monthly tokens: 1,000,000      │
│  Used this month: 142,580           │
│                                     │
│  Allowed models                     │
│  ☑ GPT-4o   ☑ Claude-3.5  ☐ o1     │
│                                     │
│       [Save changes]                │
└─────────────────────────────────────┘
```

**Fichiers à créer** :
- `src/components/admin/QuotaModal.tsx`
- (intégrer dans `src/app/admin/page.tsx`)

---

#### 2.3.2 Modal Test API Key (admin)
**Endpoint disponible** : `POST /api/admin/api-keys/test`

**Composant proposé** : Modal de test d'une API key avec provider + message.

```
┌─────────────────────────────────────┐
│  Test API Key                 ✕     │
├─────────────────────────────────────┤
│  Provider: [Minimax ▾]              │
│  Test message:                       │
│  ┌──────────────────────────────┐   │
│  │ "Hello, can you help me?"    │   │
│  └──────────────────────────────┘   │
│       [Send test]                    │
│  ┌──────────────────────────────┐   │
│  │ ✓ Response received in 1.2s  │   │
│  │ "Hello! How can I assist?"   │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

### 2.4 ⚪ Composants transverses

#### 2.4.1 Helper `apiFetch()` centralisé
**Problème actuel** : Chaque page refait `localStorage.getItem("access_token")` + `if !res.ok redirect to /login`.

**Solution** :
```ts
// src/lib/api.ts
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem("access_token");
  const headers = {
    ...init?.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 401) {
    localStorage.clear();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  return res;
}
```

**Fichier à créer** : `src/lib/api.ts`
**Fichiers à modifier** : `src/app/page.tsx`, `src/app/admin/page.tsx`, `src/app/login/page.tsx`

---

#### 2.4.2 Store Zustand pour l'auth
**Fichiers à créer** :
- `src/stores/authStore.ts`

```ts
// src/stores/authStore.ts
import { create } from "zustand";

interface AuthState {
  user: User | null;
  setUser: (u: User | null) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.clear();
    set({ user: null });
    window.location.href = "/login";
  },
}));
```

---

## 3. Découpage du `page.tsx` (761 lignes)

Le dashboard actuel fait **761 lignes dans un seul composant**. Découpage recommandé :

```
src/app/page.tsx                    (orchestrateur, ~100 lignes)
src/components/dashboard/
├── Sidebar.tsx                    (workspaces + agents list, ~120 lignes)
├── ChatPanel.tsx                  (messages + input, ~180 lignes)
├── WorkspaceModal.tsx             (create workspace, ~50 lignes)
├── AgentModal.tsx                 (create agent, ~80 lignes)
└── MessagesList.tsx               (renders Message bubbles, ~80 lignes)
```

**Bénéfices** :
- Lisibilité : chaque composant < 200 lignes
- Réutilisabilité (modals ouvrables depuis d'autres pages)
- Tests unitaires possibles
- Pas de re-render global quand un message arrive

---

## 4. Mockups Nebula ↔ écrans à créer

| Mockup | Écran probable | Statut |
|---|---|---|
| `01-splash-or-empty` | Splash screen au démarrage | À créer |
| `02-onboarding` | Welcome / onboarding (3 swipes) | À créer (sous `/welcome`) |
| `04-form-step-1` à `09-form-step-3` | Onboarding multi-étapes | À créer |
| `07-error-state`, `10-error-state`, `11-error-state`, `13-error-or-status`, `30-alert-or-status`, `34-error-state` | Error states (à utiliser dans tous les écrans via composant `<ErrorState />`) | À créer composant |
| `14-detail-screen`, `31-cta-or-action` | Modal detail avec CTA | À créer (utilisé pour agents, jobs, etc.) |
| `15-list-or-content`, `16-list-or-content`, `21-list-or-content`, `25-list-or-content`, `35-list-or-content` | Listes (workspaces, agents, jobs, etc.) | Composant `<List />` à créer |
| `17-minimal-screen`, `22-minimal-screen`, `23-minimal-screen`, `32-minimal-screen` | Écrans de paramétrage simples | Utilisé pour Settings |
| `18-dashboard-with-nav`, `27-dashboard-with-nav`, `28-dashboard-with-nav`, `37-dashboard-with-nav` | Layout dashboard avec bottom-nav | Dashboard actuel (mais layout à améliorer) |
| `19-list-item`, `20-list-item` | Cartes d'item de liste (workspaces, agents) | Composant `<ListItem />` |
| `24-empty-state`, `26-empty-state`, `33-empty-state`, `36-empty-state` | Empty states (no workspaces, no messages, etc.) | Composant `<EmptyState />` |
| `29-login-or-welcome` | Page de login | ✅ Déjà implémentée |
| `18-dashboard-with-nav` (rouge outlier) | Dashboard avec notification d'erreur | À utiliser dans dashboard |

---

## 5. Effort estimé

| Phase | Composants | Effort | Priorité |
|---|---|---|---|
| **Helper `apiFetch()` + store Zustand** | 2 fichiers | 2h | 🔴 Bloquant |
| **Découpage `page.tsx` en composants** | 5 composants | 3h | 🔴 Bloquant |
| **Page Jobs** | 3 fichiers | 4h | 🔴 Haute |
| **Page Settings** | 3 fichiers | 3h | 🟠 Haute |
| **Composant File Upload** | 1 fichier | 2h | 🟠 Haute |
| **Modal Members** | 1 fichier | 1h | 🟡 Moyenne |
| **Modal Tools** | 1 fichier | 1h | 🟡 Moyenne |
| **Modal Quota + Test API Key** | 2 fichiers | 2h | 🟢 Basse |
| **Composants transverses (EmptyState, ErrorState, List, ListItem)** | 4 fichiers | 2h | 🟠 Haute |
| **TOTAL** | **~22 fichiers** | **~20h (2.5 jours)** | — |

---

## 6. Recommandations finales

1. **Commencer par l'analyse visuelle** des 37 mockups avec un modèle vision
2. **Prioriser les helpers transverses** (`apiFetch`, Zustand) avant tout nouveau composant
3. **Implémenter page par page** en respectant le découpage par composant
4. **Tester responsive** à chaque étape (mobile-first comme les mockups le suggèrent)
5. **Créer une storybook** (`/storybook`) pour valider les composants en isolation

---

**Voir aussi** :
- [`SPEC.md`](./SPEC.md) — Spécification design (couleurs, layout, classification mockups)
- [`AUDIT_2026-07-19.md`](../AUDIT_2026-07-19.md) — Audit complet du projet
