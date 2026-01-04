# DESKTOP APP KNOWLEDGE

## OVERVIEW

Tauri 2.0 macOS app. React frontend invokes Python ingestion CLI via Rust subprocess.

## STRUCTURE

```
src/                 # React + TypeScript
src-tauri/           # Rust backend
  src/lib.rs         # Commands: run_ingestion, validate_ingestion_path
  capabilities/      # Plugin permissions (shell, dialog)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add Tauri command | src-tauri/src/lib.rs |
| UI components | src/components/*.tsx |
| Type definitions | src/types.ts |
| Plugin permissions | src-tauri/capabilities/default.json |
| App config | src-tauri/tauri.conf.json |

## DATA FLOW

```
IngestionForm → invoke("run_ingestion") → Rust spawns `uv run ingest`
                                        → Events stream to LogViewer
                                        → Result displayed in ResultView
```

## CONVENTIONS

- Rust commands return `Result<T, String>`
- Events for real-time data: `ingestion-log`, `ingestion-stdout`
- Settings in localStorage under `gat-settings`
- CSS: inline styles, macOS-native feel, 8px grid

## ANTI-PATTERNS

| NEVER | Why |
|-------|-----|
| Block on subprocess | Use async with event streaming |
| Hardcode paths | Use settings for ingestion_path |
| Skip validation | validate_ingestion_path before run |

## COMMANDS

```bash
npm run tauri dev      # Development
npm run tauri build    # Production build
```
