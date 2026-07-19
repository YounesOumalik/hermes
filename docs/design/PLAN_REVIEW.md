# 🔍 Revue Critique du Plan d'Implémentation Frontend

> **Date** : 2026-07-19
> **Objet** : Analyse du plan proposé pour l'implémentation des écrans manquants
> **Plan source** : voir conversation du 2026-07-19
> **Verdict global** : ✅ **Plan solide, à adopter avec 6 ajustements mineurs**

---

## 1. Réponses aux questions ouvertes

### ❓ Q1 : Design System — Tailwind vs CSS vanilla ?

**Réponse recommandée** : 🟢 **Continuer en CSS vanilla, mais extraire une petite lib de composants UI réutilisables.**

**Justification** :

| Critère | Tailwind | CSS vanilla + composants |
|---|---|---|
| Cohérence avec l'existant | ❌ Migration massive (1649 lignes) | ✅ Aucun churn |
| Vitesse de développement des nouveaux écrans | ✅ Rapide | ⚠️ Moyenne |
| Taille du bundle | ⚠️ +30-50 Ko (avant purge) | ✅ 0 Ko |
| Courbe d'apprentissage | ❌ Nouvelle syntaxe | ✅ Aucune |
| Design system déjà défini | ⚠️ À reconcilier (`globals.css`) | ✅ Réutilisable tel quel |

**Recommandation** : Le projet a déjà un design system mature dans `globals.css` (variables CSS, glassmorphism, dark theme). Introduire Tailwind maintenant impliquerait :
- Soit dupliquer le design system (`tailwind.config.js` + `globals.css`)
- Soit migrer entièrement (risque de régression sur 1649 lignes existantes)

**Compromis gagnant** : Créer une **mini-lib interne** de composants stylés via className (`globals.css`), ce qui répond au besoin de réutilisabilité sans dépendance externe.

**À ajouter au plan (Phase 0)** :
```
src/components/ui/
├── Button.tsx          (variantes: primary, secondary, ghost, danger)
├── Input.tsx           (text, password, textarea)
├── Modal.tsx           (wrapper générique avec backdrop + escape)
├── Card.tsx            (glass-card réutilisable)
├── Badge.tsx           (variantes: active, pending, error, success)
├── Tabs.tsx            (pour Settings et autres pages à onglets)
├── EmptyState.tsx      (icône + titre + description)
├── ErrorState.tsx      (message + retry button)
└── Spinner.tsx         (loading indicator)
```

Ces composants peuvent être créés en ~200 lignes TSX + ~100 lignes CSS additionnel dans `globals.css`.

---

### ❓ Q2 : Icônes — continuer `lucide-react` ?

**Réponse recommandée** : ✅ **Oui, sans hésiter.**

**Justification** :
- `lucide-react` est **déjà installé** (`^0.454.0`)
- Bibliothèque **tree-shakeable** (seules les icônes utilisées sont bundlées)
- Compatible React 18 et 19
- Plus de 1500 icônes disponibles
- License ISC (permissive)

Aucune raison de changer. Pour les nouveaux composants :
```tsx
import { Plus, Trash2, Play, Pause, Settings, Bell, User } from "lucide-react";
```

---

## 2. Erreurs et imprécisions détectées dans le plan

### 🔴 Erreur #1 : `zustand` est DÉJÀ installé

Le plan dit :
> ⚠️ L'installation de `zustand` est requise pour la gestion de l'état global. La commande `npm install zustand` sera exécutée dans `hermes-nebula`.

**Réalité** (`package.json`) :
```json
"zustand": "^4.5.5"  ← déjà présent
```

**Action** : ❌ **Ne pas exécuter** `npm install zustand`. Aucune installation nécessaire. Aller directement à la création du store.

---

### 🟠 Erreur #2 : Sous-estimation de l'impact du helper `apiFetch`

Le plan mentionne l'utilité du helper mais ne chiffre pas l'ampleur du refactor.

**Audit réel** :
- **20 occurrences** de `localStorage.getItem("access_token")` dans le code actuel
  - `page.tsx` : 11 occurrences
  - `admin/page.tsx` : 9 occurrences
- Aucun gestionnaire d'erreur 401 global
- Aucune logique de refresh token automatique (alors que `/api/auth/refresh` existe !)

**Recommandation** : Étendre `apiFetch` pour gérer **aussi le refresh automatique** :
```ts
// src/lib/api.ts
let isRefreshing = false;

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  // 401 → tenter refresh puis retry
  if (res.status === 401 && !isRefreshing) {
    isRefreshing = true;
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      const refreshRes = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        localStorage.setItem("access_token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        isRefreshing = false;
        return apiFetch(path, init); // retry
      }
    }
    isRefreshing = false;
    localStorage.clear();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  return res;
}
```

Cela résout un bug latent : actuellement quand le JWT expire, l'utilisateur est silencieusement déconnecté sans message.

---

### 🟠 Erreur #3 : Refactor `page.tsx` incomplet

Le plan propose 4 composants extraits :
- `Sidebar.tsx` ✅
- `ChatPanel.tsx` ✅
- `WorkspaceModal.tsx` ✅
- `AgentModal.tsx` ✅

**Manque** : `MessagesList.tsx` (suggéré dans `MISSING_SCREENS.md`). Sans ça, `ChatPanel.tsx` reste massif car il contient :
- Render des messages
- Auto-scroll
- Markdown rendering (probable)
- Streaming SSE handler
- Input box
- Upload (à venir Phase 4)

**Recommandation** : Ajouter `MessagesList.tsx` et `ChatInput.tsx` dans la liste.

---

### 🟡 Erreur #4 : Schéma backend `jobs` non spécifié

Le plan dit créer `CreateJobModal.tsx` mais ne mentionne pas les **champs obligatoires** selon le backend :

```python
# D'après hermes-nebula-api/app/api/jobs/router.py
class JobCreate(BaseModel):
    agent_id: uuid.UUID         # ← obligatoire (sélecteur d'agent requis)
    name: str                   # ← obligatoire (max 300 chars)
    prompt: str                 # ← obligatoire
    cron_expression: str        # ← obligatoire (max 100 chars)
```

**Implications UI** :
- Le modal doit contenir un **sélecteur d'agent** (dropdown depuis la liste des agents du workspace)
- Le champ `cron_expression` nécessite soit :
  - Un input texte libre (avec aide sur la syntaxe cron)
  - Idéalement un **cron picker visuel** (ex : presets "Toutes les heures", "Chaque jour à 9h", "Chaque lundi")
- Le champ `prompt` doit être un **textarea multi-lignes**

**Recommandation** : Ajouter une note sur l'UX du cron (preset + custom).

---

### 🟡 Erreur #5 : Absence de Phase pour le layout global

Le plan oublie un point critique : le **layout mobile avec bottom navigation** suggéré par les mockups Nebula (4 mockups ont un bottom-nav : `#18`, `#27`, `#28`, `#37`).

**Actuellement** : `src/app/layout.tsx` fait 35 lignes et ne contient que le wrapper HTML + fonts.

**Recommandation** : Ajouter une **Phase 0.5** ou **Phase 5** pour créer un `AppShell` avec bottom-nav mobile :
```
src/components/layout/
├── AppShell.tsx              (wrapper avec sidebar desktop + bottom-nav mobile)
├── BottomNav.tsx             (navigation mobile : Home, Jobs, Settings, Profile)
└── TopBar.tsx                (header avec workspace switcher + user avatar)
```

C'est ce qui transformera l'app desktop actuelle en **vraie PWA mobile** comme le suggèrent les mockups.

---

### 🟡 Erreur #6 : Pas de gestion du multi-workspace dans `/jobs`

Le endpoint est `GET /api/workspaces/{wid}/jobs` — il dépend donc du workspace courant.

**Question** : Comment l'utilisateur sélectionne-t-il le workspace dans la page `/jobs` ?

**Options** :
- A) URL : `/jobs?wid=xxx` (simple mais pas très REST)
- B) Route paramétrée : `/workspaces/[wid]/jobs` (REST mais plus verbeux)
- C) Store Zustand : workspace actif global (recommandé, cohérent avec le dashboard)

**Recommandation** : Créer un **`useWorkspaceStore`** en plus de `useAuth` :
```ts
// src/stores/workspaceStore.ts
interface WorkspaceState {
  activeWorkspace: Workspace | null;
  workspaces: Workspace[];
  setActiveWorkspace: (w: Workspace) => void;
  setWorkspaces: (ws: Workspace[]) => void;
}
```

Ainsi `/jobs` peut lire `useWorkspaceStore(s => s.activeWorkspace)` sans prop drilling.

---

## 3. Risques additionnels non couverts par le plan

### ⚠️ Risque #1 : Régression sur le dashboard existant

Le `page.tsx` actuel (761 lignes) gère **le streaming SSE du chat**. Si on découpe à la va-vite, on risque de casser :
- L'event source SSE
- L'auto-scroll des messages
- Le state partagé entre input et messages

**Mitigation** : Refactor incrémental
1. D'abord créer les composants **à côté** (sans modifier `page.tsx`)
2. Tester chaque composant en isolation
3. Puis substituer progressivement
4. Garder `page.tsx` en backup (`page.tsx.bak`) durant la transition

### ⚠️ Risque #2 : Performance et re-renders

Actuellement, le state du chat vit dans `page.tsx`. Si on le déplace dans Zustand, **tous les composants abonnés se re-render à chaque nouveau message**.

**Mitigation** : Utiliser des **sélecteurs fins** :
```tsx
// ❌ Mauvais : re-render à chaque changement du store
const store = useChatStore();

// ✅ Bon : re-render uniquement quand messages change
const messages = useChatStore(s => s.messages);
const isStreaming = useChatStore(s => s.isStreaming);
```

### ⚠️ Risque #3 : Tests manuels insuffisants

Le plan prévoit `npm run lint` et `npm run build`. C'est bien mais insuffisant.

**Recommandation** : Ajouter des tests unitaires minimaux avec **Vitest** + **React Testing Library** sur :
- `apiFetch` (401 → refresh → retry)
- `authStore` (login, logout)
- Modal d'onboarding (formulaire valide/invalide)

Effort : ~2h pour configurer Vitest + 3-4 tests de base.

---

## 4. Plan révisé et consolidé

### 🆕 Phase 0 (AJOUT) — Composants UI primitifs

Avant tout, créer la lib interne pour ne pas dupliquer du CSS :

| Fichier | Rôle | Effort |
|---|---|---|
| `src/components/ui/Button.tsx` | 4 variantes | 30 min |
| `src/components/ui/Input.tsx` | Text/password/textarea | 30 min |
| `src/components/ui/Modal.tsx` | Wrapper backdrop + escape | 45 min |
| `src/components/ui/Card.tsx` | Glass-card | 15 min |
| `src/components/ui/Badge.tsx` | 4 couleurs | 15 min |
| `src/components/ui/Tabs.tsx` | Onglets contrôlés | 30 min |
| `src/components/ui/EmptyState.tsx` | Empty states | 15 min |
| `src/components/ui/ErrorState.tsx` | Error states | 15 min |
| `src/components/ui/Spinner.tsx` | Loading | 10 min |
| `globals.css` (update) | Classes additionnelles | 30 min |

**Total Phase 0** : ~3.5h — **investissement qui rentabilise toutes les phases suivantes**.

---

### Phase 1 — Core Helpers & Stores

✅ **Conforme au plan**, avec les ajustements :
- ❌ **NE PAS** faire `npm install zustand` (déjà installé)
- ✅ Étendre `apiFetch` avec refresh automatique (cf. erreur #2)
- ✅ Ajouter `workspaceStore.ts` en plus de `authStore.ts`

| Fichier | Effort |
|---|---|
| `src/lib/api.ts` (avec refresh) | 1h |
| `src/stores/authStore.ts` | 30 min |
| `src/stores/workspaceStore.ts` | 30 min |
| Update `login/page.tsx` | 30 min |
| **Total** | **2.5h** |

---

### Phase 2 — Refactor `page.tsx`

✅ **Conforme au plan**, avec les ajouts :
- Composant `MessagesList.tsx` (manquant dans le plan)
- Composant `ChatInput.tsx` (pour séparer input de MessagesList)
- Utilisation des primitives UI de la Phase 0

| Fichier | Effort |
|---|---|
| `src/components/dashboard/Sidebar.tsx` | 1.5h |
| `src/components/dashboard/ChatPanel.tsx` | 1h (orchestrateur) |
| `src/components/dashboard/MessagesList.tsx` | 1h |
| `src/components/dashboard/ChatInput.tsx` | 45 min |
| `src/components/dashboard/WorkspaceModal.tsx` | 30 min |
| `src/components/dashboard/AgentModal.tsx` | 1h |
| `src/app/page.tsx` (orchestrateur) | 1h |
| **Total** | **6.25h** |

⚠️ **Migration progressive** : garder `page.tsx.bak` en backup tant que la nouvelle version n'est pas testée en intégrité.

---

### 🆕 Phase 2.5 (AJOUT) — Layout & Navigation

| Fichier | Rôle | Effort |
|---|---|---|
| `src/components/layout/AppShell.tsx` | Wrapper global (desktop sidebar + mobile bottom-nav) | 1.5h |
| `src/components/layout/BottomNav.tsx` | Nav mobile | 1h |
| `src/components/layout/TopBar.tsx` | Header avec workspace switcher | 1h |
| Update `src/app/layout.tsx` | Intégrer AppShell | 30 min |
| **Total** | **4h** |

C'est ce qui transformera l'app desktop actuelle en PWA mobile-first (cohérent avec les 37 mockups Nebula).

---

### Phase 3 — Nouvelles Pages

✅ **Conforme au plan**, avec précisions :

#### Page Jobs
- **Endpoints** : `GET /api/workspaces/{wid}/jobs`, `POST /api/workspaces/{wid}/jobs`, `POST /api/jobs/{id}/run-now`, `PATCH /api/jobs/{id}` (pause/resume), `DELETE /api/jobs/{id}`, `GET /api/jobs/{id}/runs`
- **Workspace** : lire depuis `useWorkspaceStore` (pas depuis l'URL)
- **CreateJobModal** : champs requis = `agent_id` (select), `name`, `prompt` (textarea), `cron_expression` (preset + custom)

| Fichier | Effort |
|---|---|
| `src/app/jobs/page.tsx` | 2.5h |
| `src/components/jobs/JobCard.tsx` | 1h |
| `src/components/jobs/CreateJobModal.tsx` | 2h |
| `src/components/jobs/CronPresets.tsx` | 1h (helper) |
| `src/components/jobs/JobRunHistory.tsx` (drawer) | 1.5h |
| **Total** | **8h** |

#### Page Settings
- **Endpoints** : `PATCH /api/settings/profile`, `GET /api/settings/notifications/channels`, `PATCH /api/settings/notifications/channels/{id}`
- **Onglets** : Profile, Notifications, Security (changement de mot de passe à venir)

| Fichier | Effort |
|---|---|
| `src/app/settings/page.tsx` | 1.5h |
| `src/components/settings/ProfileTab.tsx` | 1h |
| `src/components/settings/NotificationsTab.tsx` | 1.5h |
| `src/components/settings/SecurityTab.tsx` | 45 min (placeholder) |
| **Total** | **4.75h** |

---

### Phase 4 — Composants additionnels

✅ **Conforme au plan**.

| Fichier | Effort |
|---|---|
| `src/components/chat/FileUploader.tsx` | 2h |
| Intégration dans `ChatInput.tsx` | 1h |
| **Total** | **3h** |

---

## 5. Synthèse comparative : Plan initial vs Plan révisé

| Phase | Plan initial | Plan révisé | Δ |
|---|---|---|---|
| **0. UI primitives** | — | 3.5h | 🆕 +3.5h |
| **1. Helpers & Stores** | 2h | 2.5h | +0.5h |
| **2. Refactor page.tsx** | 5h | 6.25h | +1.25h |
| **2.5. Layout & Nav** | — | 4h | 🆕 +4h |
| **3. Pages Jobs + Settings** | 7h | 12.75h | +5.75h |
| **4. FileUploader** | 2h | 3h | +1h |
| **TOTAL** | **~18h** | **~32h (4 jours)** | **+14h** |

**Conclusion** : le plan initial sous-estime l'effort de **~75%**. Le plan révisé est plus réaliste.

---

## 6. Recommandations stratégiques

### 🥇 Reco #1 : Phase 0 d'abord

Ne pas sauter la Phase 0 (UI primitives). C'est l'investissement le plus rentable : tous les composants suivants les utiliseront. Sans ça, on dupliquerait du CSS partout.

### 🥈 Reco #2 : Livrer par incréments testables

Ne pas faire tout d'un coup. Séquence recommandée :

1. **Sprint 1** (jour 1) : Phase 0 + Phase 1 → PR reviewable
2. **Sprint 2** (jour 2) : Phase 2 (refactor page.tsx) → testable en dev
3. **Sprint 3** (jour 3) : Phase 2.5 (layout mobile) → vraie PWA
4. **Sprint 4** (jour 4-5) : Phase 3 (Jobs + Settings) + Phase 4 (FileUploader)

### 🥉 Reco #3 : Backup git avant refactor

```bash
git checkout -b backup/dashboard-v1
git push origin backup/dashboard-v1
git checkout main
# Maintenant on peut refactorer sereinement
```

### 🏅 Reco #4 : Tests E2E minimum

Ajouter **Playwright** avec 3 scénarios :
1. Login OAuth → dashboard
2. Création workspace + agent → conversation
3. Job creation → run-now

Effort : 4h pour mettre en place + 3 scénarios.

---

## 7. Verdict final

| Aspect | Note | Commentaire |
|---|---|---|
| Architecture globale | ✅ 8/10 | Saine, mais Phase 0 + Phase 2.5 manquantes |
| Réponses aux questions ouvertes | ✅ Très claires | Voir §1 |
| Découpage en composants | ⚠️ 6/10 | Manque MessagesList et ChatInput |
| Estimation d'effort | ❌ 4/10 | Sous-estimée de ~75% |
| Couverture backend | ✅ 9/10 | Tous les endpoints importants couverts |
| Risques identifiés | ⚠️ 5/10 | Manque SSE streaming + re-renders |

**Recommandation** : **Adopter le plan avec les 6 ajustements ci-dessus**. En particulier :
- ✅ Ajouter Phase 0 (UI primitives)
- ✅ Ajouter Phase 2.5 (Layout & Nav mobile)
- ✅ Étendre apiFetch avec refresh
- ✅ Ajouter `workspaceStore`
- ✅ Corriger l'erreur sur `npm install zustand` (déjà installé)
- ✅ Réviser l'estimation à ~32h au lieu de 18h

---

## 8. Prochaines actions recommandées

1. **Confirmer les réponses aux 2 questions ouvertes** (cf. §1)
2. **Décider si on intègre Phase 0 et Phase 2.5** (recommandé)
3. **Créer une branche backup git** avant tout refactor
4. **Lancer Sprint 1** (Phase 0 + Phase 1) — incrément testable

Une fois ces décisions prises, je peux commencer l'implémentation concrète en suivant le plan révisé.

---

**Voir aussi** :
- [`MISSING_SCREENS.md`](./MISSING_SCREENS.md) — Roadmap initiale (à compléter par cette revue)
- [`SPEC.md`](./SPEC.md) — Spécification design
- [`../AUDIT_2026-07-19.md`](../AUDIT_2026-07-19.md) — Audit complet du projet
