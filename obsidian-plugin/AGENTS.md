# OBSIDIAN PLUGIN KNOWLEDGE BASE

**Scope:** TypeScript/React plugin consuming JSON manifests → SQLite + Markdown

## OVERVIEW

sql.js WASM for SQLite in-browser. React 18 UI. Dual storage: SQLite (queryable assets), Markdown notes (Obsidian-native packs).

## STRUCTURE

```
src/
├── main.ts           # Plugin lifecycle, ribbon, commands
├── database.ts       # sql.js init, schema, queries
├── DashboardView.tsx # React UI component
├── types.ts          # TypeScript interfaces (mirror ingestion types)
└── utils.ts          # Markdown generation for pack notes
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Plugin commands/ribbon | `main.ts` |
| SQLite schema/queries | `database.ts` |
| Dashboard UI | `DashboardView.tsx` |
| Type definitions | `types.ts` |
| Pack note generation | `utils.ts` |
| Manifest import flow | `database.ts` → `importManifest()` |

## SQLITE SCHEMA

```sql
packs (pack_id PK, pack_name, root_path, source, license_link, global_tags, created_at, updated_at)
assets (id, pack_id FK, relative_path, file_type, size_bytes, metadata_json, local_tags)
-- Indexes on pack_id, file_type, relative_path
```

## CONVENTIONS

- **sql.js WASM** - runs SQLite in browser, no native deps
- **Relative paths** - SQLite stores paths relative to pack root
- **AJV validation** - validates manifest JSON before import
- **Dual write** - import creates BOTH SQLite rows AND Markdown note

## IMPORT FLOW

1. User triggers import (ribbon/command)
2. Read JSON manifest file
3. Validate against schema (AJV)
4. Insert pack → `packs` table
5. Insert assets → `assets` table
6. Generate Markdown note via `utils.ts`
7. Save note to vault

## ANTI-PATTERNS

| NEVER | Instead |
|-------|---------|
| Skip AJV validation | Always validate before insert |
| Store absolute paths | Relative to pack root only |
| Direct SQLite without sql.js | Use database.ts abstractions |
| Modify Markdown from code after creation | One-way: generate once |

## COMMANDS

```bash
npm install           # deps
npm run dev           # esbuild watch mode
npm run build         # production build (tsc + esbuild)
```

## BUILD OUTPUT

- `main.js` - bundled plugin
- `manifest.json` - Obsidian plugin manifest
- Copy both to `.obsidian/plugins/game-asset-tracker/` in vault

## NOTES

- React 18.2, TypeScript 4.7.4
- esbuild bundles to ES2018 CommonJS (Obsidian requirement)
- sql.js requires WASM file loading (handled in database.ts)
- `strictNullChecks` enabled
