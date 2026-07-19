# 📐 Documentation Design AgentAI

Ce dossier contient toute la documentation relative au design de l'application AgentAI.

## 📁 Contenu

| Fichier | Description |
|---|---|
| [**`SPEC.md`**](./SPEC.md) | Spécification design : palette de couleurs, classification des mockups, hypothèses de mapping écran ↔ mockup |
| [**`MISSING_SCREENS.md`**](./MISSING_SCREENS.md) | Roadmap frontend : écrans et composants manquants pour atteindre la parité backend |
| [`nebula-mockups/`](./nebula-mockups/) | 37 mockups de design mobile (738×1600, ratio 9:16) |

## 🎨 Mockups

37 mockups au format mobile (738×1600) représentant les écrans cibles de l'application mobile AgentAI.

### Nommage

Les fichiers ont été renommés selon le pattern suivant :

```
[NN]-[type-d'écran].jpeg
```

Exemples :
- `01-splash-or-empty.jpeg`
- `18-dashboard-with-nav.jpeg`
- `29-login-or-welcome.jpeg`
- `07-error-state.jpeg`

> ⚠️ Les noms sont des **hypothèses basées sur une analyse structurelle** (dimensions, luminosité, palette). Une analyse visuelle par un modèle multimodal est nécessaire pour confirmer l'écran exact de chaque mockup.

### Classification

Voir [`SPEC.md`](./SPEC.md) §4 pour le détail de la classification.

## ⚠️ Analyse visuelle nécessaire

Ce modèle (GLM-5.2) ne supporte **pas la vision**. Pour transformer les mockups en code :

1. **VS Code Copilot** : sélectionne un modèle vision-compatible (Claude 3.5 Sonnet, GPT-4o)
2. **Google AI Studio** : gratuit, upload direct
3. **ChatGPT / Claude.ai** : drag & drop

Demande à l'IA : *"Analyse ce mockup et donne-moi : nom de l'écran, layout, composants visibles, couleurs exactes, textes, hiérarchie visuelle"*

## 📊 État d'avancement

| Phase | Statut |
|---|---|
| Audit + nettoyage | ✅ Terminé (2026-07-19) |
| Spécification design | ✅ Terminé |
| Renommage mockups | ✅ Terminé |
| Roadmap écrans manquants | ✅ Terminé |
| Analyse visuelle des mockups | ⏳ À faire (par modèle vision) |
| Implémentation des écrans manquants | ⏳ À faire (~20h estimées) |
