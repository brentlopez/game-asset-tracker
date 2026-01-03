# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-03
**Commit:** 25c7701
**Branch:** master

## OVERVIEW

Game asset tracker: Python ingestion CLI produces JSON manifests, Obsidian plugin consumes them into SQLite + Markdown notes. Pack-centric architecture (assets always belong to packs).

## STRUCTURE

```
./
├── ingestion/           # Python CLI - produces JSON manifests
├── obsidian-plugin/     # TypeScript/React - consumes manifests
└── schemas/             # JSON Schema (manifest.schema.json) - SACRED
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new asset source | `ingestion/src/.../platforms/` | Inherit BaseSource + BaseTransformer |
| Modify manifest format | `schemas/manifest.schema.json` | Update BOTH ingestion + plugin |
| Plugin UI changes | `obsidian-plugin/src/DashboardView.tsx` | React component |
| SQLite schema | `obsidian-plugin/src/database.ts` | sql.js WASM |
| Asset metadata types | `ingestion/.../core/types.py` + `obsidian-plugin/src/types.ts` | Keep in sync |

## DATA FLOW

```
Sources (filesystem/fab/uas)
    ↓
ingestion CLI (uv run ingest)
    ↓
JSON manifests (validated against schema)
    ↓
Obsidian plugin import
    ↓
SQLite (assets) + Markdown notes (packs)
```

## CONVENTIONS

- **Schema is sacred** - never bypass validation
- **One-way sync only** - manifests → plugin, never reverse
- **Pack-centric** - no standalone assets, always pack membership
- **Three-tier auth** - Sources auth-agnostic, API clients handle creds, Adapters extract from local apps

## ANTI-PATTERNS (THIS PROJECT)

| NEVER | Why |
|-------|-----|
| Standalone assets | Must belong to pack |
| Direct adapter access | Use API client only |
| Skip schema validation | Data integrity |
| Commit build artifacts | `.gitignore` handles |
| Two-way sync | Complexity, data loss risk |
| Hidden file ingestion | Security |
| `size_bytes < 0` | Invalid |

## COMMANDS

```bash
# Ingestion
cd ingestion && uv sync
uv run pytest              # tests with coverage
uv run ingest --help       # CLI

# Plugin
cd obsidian-plugin && npm install
npm run dev                # watch mode
npm run build              # production
```

## NOTES

- SQLite stores relative paths (not absolute)
- Plugin requires manual manifest import (no auto-sync)
- Extensions must be lowercase for matching
- `size_bytes=0` valid for metadata-only mode
- fab/uas sources require optional deps: `uv sync --extra fab` or `--extra uas`
