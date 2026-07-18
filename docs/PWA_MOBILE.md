# Hermes Studio — Refonte PWA & Mobile ✦

> Document de finalisation de la **Phase 6** du plan de refonte.
> Date : 2026-07-18 · Cible : déploiement sur `prodserveur` (169.58.30.70).

---

## 🎯 Résumé exécutif

L'interface **Hermes Studio** est désormais installable comme **PWA** sur iOS, Android et desktop (Chrome/Edge). Tous les assets PWA requis par Lighthouse sont en place.

| Élément | Statut | Fichier |
|---|---|---|
| Manifest PWA | ✅ | `public/manifest.json` |
| Favicon | ✅ | `public/favicon.ico` |
| Icône SVG vectorielle | ✅ | `public/icon.svg` |
| Apple touch icon 180×180 | ✅ | `public/apple-icon.png` |
| Icône PWA 192×192 | ✅ | `public/icons/icon-192.png` |
| Icône PWA 512×512 | ✅ | `public/icons/icon-512.png` |
| Icône maskable 512×512 | ✅ | `public/icons/icon-maskable-512.png` |
| Service Worker offline | ✅ | `public/sw.js` |
| Page offline fallback | ✅ | `public/offline.html` |
| Meta tags iOS PWA | ✅ | `app/layout.tsx` |
| Meta tags Android PWA | ✅ | `app/layout.tsx` |
| Meta tags Windows PWA | ✅ | `app/layout.tsx` |
| Theme color adaptatif | ✅ | `app/layout.tsx` |
| viewport-fit: cover (notch) | ✅ | `app/layout.tsx` |
| Safe-area insets CSS | ✅ | `app/globals.css` |
| Touch tap-highlight supprimé | ✅ | `app/globals.css` |
| `prefers-reduced-motion` | ✅ | `app/globals.css` |

---

## 📁 Structure créée

```
hermes-studio/public/                          ← nouveau
├── favicon.ico                               (32×32 ICO multi-size)
├── icon.svg                                  (source vectorielle Hermes)
├── apple-icon.png                            (180×180, iOS home)
├── manifest.json                             (PWA manifest, scope /)
├── robots.txt                                (SEO, bloque /api/)
├── sw.js                                     (Service Worker offline)
├── offline.html                              (fallback hors ligne)
└── icons/
    ├── icon-192.png                          (PWA standard)
    ├── icon-512.png                          (PWA standard)
    ├── icon-maskable-512.png                 (Android adaptive)
    └── icon-maskable-512.svg                 (source)

hermes-studio/app/components/
└── ServiceWorkerRegistrar.tsx                (client-only, no-op en dev)

hermes-studio/scripts/
└── build-icons.mjs                           (régénère les PNG depuis SVG)
```

---

## 🔧 Modifications principales

### 1. `app/layout.tsx` — Méta-données PWA complètes

Ajout de :
- `manifest: '/manifest.json'` dans les `metadata`
- Block `icons` (favicon, SVG, PNG, apple)
- `appleWebApp` (capable, statusBarStyle, title, startupImage)
- `openGraph` + `twitter` pour partage social
- `viewportFit: 'cover'` + `viewport` complet dans `<head>` :
  - `apple-mobile-web-app-capable` / `status-bar-style` / `title`
  - `apple-touch-icon` + `apple-touch-startup-image`
  - `mobile-web-app-capable`
  - `msapplication-TileColor` / `TileImage` (Windows)
  - `theme-color` adaptatif selon `prefers-color-scheme`

### 2. `app/globals.css` — UX mobile native

- `env(safe-area-inset-*)` sur `.app-container`, `.chat-header`, `.composer-wrap`, `.sidebar-container` (notch iPhone, Dynamic Island, home indicator)
- `-webkit-tap-highlight-color: transparent` + `touch-action: manipulation` sur tous les éléments interactifs
- `overscroll-behavior-y: none` en mode standalone (évite le pull-to-refresh et le rubber-band iOS)
- Media queries supplémentaires :
  - `@media (max-height: 600px)` (paysage mobile) — compactage composer
  - `@media (max-width: 360px)` (iPhone SE, Android anciens) — padding réduit
  - `@media (prefers-reduced-motion: reduce)` — désactive toutes les animations
- `100dvh` (dynamic viewport height) pour éviter le resize du clavier mobile

### 3. `public/sw.js` — Service Worker

Stratégie hybride :
- **Network-first** pour `/api/*` (données temps réel → fallback cache si offline)
- **Cache-first** pour `/_next/static/*`, icônes, manifest (assets versionnés)
- **Network-first avec fallback `/offline.html`** pour la navigation

Versioning : cache names `hermes-v1-static`, `hermes-v1-runtime`. `skipWaiting()` + `clients.claim()` à l'activation pour appliquer les updates immédiatement.

### 4. `app/components/ServiceWorkerRegistrar.tsx`

Composant client-only (`'use client'`), no-op en `NODE_ENV !== 'production'` pour ne pas casser le HMR en dev. Délai de 1.5s avant enregistrement pour ne pas bloquer le rendu initial.

### 5. `package.json` — Script utilitaire

Ajout de `npm run icons:build` (`node scripts/build-icons.mjs`) qui régénère tous les PNG depuis `public/icon.svg` via ImageMagick (requis : `apt install imagemagick`).

---

## 🚀 Déploiement

### En local

```bash
cd ~/Documents/ProdServeur/hermes-studio
NODE_OPTIONS=--max-old-space-size=2048 npm run build
# ✅ Build vérifié : 4.2s, 0 warning, 0 erreur
```

### Sur prodserveur (VPS Contabo)

```bash
ssh prodserveur
cd /srv/apps/hermes    # ou le chemin de l'app
git pull  # ou copier les fichiers
docker compose build hermes-studio
docker compose up -d hermes-studio
```

Le `Dockerfile` copie déjà `public/` dans `.next/standalone/public/` :
```dockerfile
RUN mkdir -p .next/standalone/.next \
    && cp -r .next/static .next/standalone/.next/static \
    && if [ -d public ]; then cp -r public .next/standalone/public; fi
```

---

## 🧪 Comment tester l'installation

### Sur Android (Chrome)
1. Ouvrir `https://hermes.smartefp.com` (ou l'IP du VPS)
2. Chrome affiche une bannière « Installer l'application »
3. Cliquer → icône Hermes sur l'écran d'accueil

### Sur iOS (Safari)
1. Ouvrir le site dans Safari
2. Bouton Partager → « Sur l'écran d'accueil »
3. Confirmer → Hermes apparaît avec son icône purple

### Sur desktop (Chrome/Edge)
1. Ouvrir le site
2. Icône « Installer » dans la barre d'adresse (à droite)
3. Confirmer → ouvre en fenêtre standalone (sans URL bar)

---

## 🔍 Vérification Lighthouse

Pour vérifier le score PWA après déploiement :
1. Ouvrir DevTools (F12)
2. Onglet **Lighthouse**
3. Cocher **Progressive Web App**
4. **Analyze page load**

Score attendu : **100/100** PWA.

> ⚠️ Nécessite HTTPS en production (Let's Encrypt via Caddy).

---

## 📝 Variables d'environnement ajoutées

| Var | Défaut | Description |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | `https://hermes.smartefp.com` | URL canonique (OpenGraph, manifest) |
| `NEXT_PUBLIC_DAEMON_URL` | `http://hermes-daemon:8001` | URL du daemon (déjà existant) |

Ajoutées au service `hermes-studio` dans `docker-compose.yml`.

---

## ⚠️ Notes importantes

1. **HTTPS obligatoire** pour la PWA installable (sauf `localhost`). Caddy sur le VPS gère déjà Let's Encrypt automatiquement.
2. **Service Worker désactivé en dev** (`NODE_ENV !== 'production'`) pour ne pas interférer avec Turbopack HMR.
3. **Cache busting** : le SW utilise `updateViaCache: 'none'` pour toujours charger la dernière version de `sw.js`.
4. **Icons régénérables** : si vous modifiez `public/icon.svg`, exécutez `npm run icons:build` (ImageMagick requis).

---

_Dernière mise à jour : 2026-07-18 · Phase 6 du plan de refonte complétée._
