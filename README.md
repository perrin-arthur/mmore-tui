# mmore-tui

Une vraie interface terminale (TUI) plein écran pour [mmore](https://github.com/swiss-ai/mmore) — le pipeline multimodal de RAG. Pour les utilisateurs qui ne veulent pas écrire de YAML à la main ni mémoriser les sous-commandes.

## Ce que ça fait

- **Liste toutes les commandes mmore** (`process`, `postprocess`, `index`, `rag`, `ragcli`, `retrieve`, …) avec une description visible.
- **Choix de config par étape** : sélectionner un YAML existant via un explorateur de fichiers, ou en générer un à travers un formulaire guidé construit automatiquement à partir des dataclasses de config de mmore.
- **Pipeline canonique** : enchaîne `process → postprocess → index → chat` avec un fil d'Ariane visible.
- **Logs en direct** pendant l'exécution (panneau `RichLog`).
- **Chat RAG intégré** : pose des questions à une collection indexée sans quitter la TUI.

```
┌─ mmore-tui ───────────────────────────────────────────────────┐
│                                                               │
│              ▶  Lancer une commande                           │
│              ⚙  Pipeline complète                             │
│              💬  Chat avec mes documents indexés              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Installation

Avec [uv](https://docs.astral.sh/uv/) (recommandé) :

```bash
uv sync
uv run mmore-tui
```

## Lancer

```bash
uv run mmore-tui
```

Raccourcis : flèches pour naviguer, `Entrée` pour valider, `Échap` pour revenir, `q` pour quitter.

## Tests

```bash
uv run pytest
```

## Architecture

- `src/mmore_tui/commands.py` — registre des commandes mmore (label, description, dataclass de config). Mirroir 1:1 de `mmore.cli`.
- `src/mmore_tui/config_builder.py` — introspection des dataclasses / modèles Pydantic vers des specs de widgets (pure Python, testable hors UI).
- `src/mmore_tui/screens/` — un écran Textual par étape (accueil, liste de commandes, choix de config, formulaire, exécution, pipeline, chat).
- `src/mmore_tui/runner.py` — exécute une commande mmore en thread worker, redirige les logs stdlib + stdout/stderr vers le `RichLog` de l'écran.

mmore lui-même n'est jamais forké : tout passe par des imports dynamiques (`mmore.run_*.run_*`, `mmore.utils.load_config`).
