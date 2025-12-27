# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a hybrid system for managing game development assets at scale. It combines:
- **Obsidian** for high-level Asset Pack organization (Markdown notes, linking, tagging)
- **SQLite** for granular file-level search across thousands of individual asset files
- **Python ingestion library** for automated manifest generation from multiple sources
- **TypeScript/Obsidian plugin** for bridging JSON manifests to the database and notes

**Current status**: 
- ✅ Ingestion library implemented (filesystem, Fab marketplace, extensible architecture)
- 🚧 Obsidian plugin scaffolded but not yet implemented

## Critical Architecture Concepts

### Data Flow (One-Way Sync)
```
Multiple Sources (filesystem, Fab, UAS, custom)
    ↓ ingestion pipeline
JSON Manifests (strict schema)
    ↓ imported via
Obsidian Plugin
    ↓ simultaneously creates
    ├─→ SQLite Index (for fast search)
    └─→ Markdown Notes (for human organization)
```

### Key Principle: Dual Storage Model
- **Asset Packs** = High-level collections → Markdown notes in Obsidian (linkable, human-readable)
- **Asset Files** = Individual files within packs → SQLite rows (searchable, scalable)

### JSON Schema is Sacred
All data MUST conform to the formal JSON Schema (Draft 7) at `schemas/manifest.schema.json`. This schema enforces:
- **Pack-level metadata**: pack_id (UUID), pack_name, root_path, source, license_link, global_tags
- **Asset-level metadata**: relative_path, file_type (lowercase), size_bytes, metadata object, local_tags
- **Validation rules**: Required fields, type constraints, UUID format, unique tags, no additional properties

Both ingestion scripts and the plugin MUST validate against this schema. See `schemas/README.md` for validation examples.

## Architecture Documentation

**READ THESE FIRST before making changes:**
- `ARCHITECTURE.md` - Complete system design, data model, workflow, and JSON schema
- `README.md` - Project overview and quick start

## Repository Structure

```
ingestion/           # Python: Scans asset directories → generates validated JSON
obsidian-plugin/     # TypeScript: Validates & imports JSON → updates SQLite + creates Markdown
schemas/             # THE CONTRACT: Formal JSON Schema + examples
  ├── manifest.schema.json   # JSON Schema (Draft 7) - strict validation rules
  ├── example-manifest.json  # Valid example demonstrating structure
  └── README.md              # Schema documentation and validation guide
```

## Development Guidelines

### For Python Ingestion Library
- **Status**: ✅ **Implemented** - See `ingestion/` directory
- Target: Python 3.11+ with modern tooling (uv, ruff, mypy)
- **Architecture**: Modular pipeline with pluggable sources
- Must generate JSON conforming to `schemas/manifest.schema.json`
- **Available sources**:
  - `filesystem`: Local directory scanning
  - `fab`: Fab marketplace integration (via fab-api-client)
  - Custom sources via extensible interface
- **Key features**:
  - Auto-discovery of source plugins
  - Schema validation built-in
  - Multiple download strategies (metadata-only, manifests-only)
  - Type-safe with full mypy strict mode
- **Documentation**: See `ingestion/README.md`, `ingestion/EXTENDING.md`, `ingestion/TODO.md`

### For Obsidian Plugin
- Target: TypeScript with React for UI components
- **CRITICAL**: Validate all incoming JSON using AJV library against `schemas/manifest.schema.json`
- Must implement:
  - JSON import UI with drag-and-drop support
  - Schema validation with user-friendly error messages
  - SQLite database operations (see schema in ARCHITECTURE.md)
  - Atomic transactions for database updates
  - Markdown note generation with frontmatter
  - Search interface for querying asset files
- Database schema (from ARCHITECTURE.md):
  ```sql
  CREATE TABLE packs (
      pack_id TEXT PRIMARY KEY,
      pack_name TEXT NOT NULL,
      root_path TEXT NOT NULL,
      source TEXT,
      license_link TEXT,
      global_tags TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE assets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pack_id TEXT NOT NULL,
      relative_path TEXT NOT NULL,
      file_type TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      metadata_json TEXT,
      local_tags TEXT,
      FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
  );

  CREATE INDEX idx_file_type ON assets(file_type);
  CREATE INDEX idx_pack_id ON assets(pack_id);
  CREATE INDEX idx_local_tags ON assets(local_tags);
  ```

## Development Commands

### Python Ingestion Library (✅ Implemented)

```bash
# Install dependencies
cd ingestion && uv sync

# Install with Fab support
cd ingestion && uv sync --extra fab

# CLI usage (legacy filesystem scanning)
uv run ingest --path /path/to/assets --name "Pack Name" --source "Source"

# Library usage (programmatic)
python -c "from game_asset_tracker_ingestion import SourceRegistry; ..."

# Run tests
uv run pytest

# Code quality
uv run ruff check src/
uv run mypy src/
```

See `ingestion/README.md` for complete documentation.

### When Obsidian Plugin Is Implemented
Expected commands will likely be:
```bash
# Install dependencies
cd obsidian-plugin && npm install

# Build plugin
npm run build

# Development mode with hot reload
npm run dev

# Run tests
npm test
```

## Design Constraints

1. **One-Way Sync Only**: No reverse sync from Obsidian/SQLite back to filesystem
2. **JSON as Source of Truth**: All data flows through the JSON schema
3. **Filesystem is Ultimate Source**: JSON can be regenerated and re-imported anytime
4. **No Direct File References**: Asset files are tracked by metadata, not opened/edited by the system
5. **Pack-Centric Organization**: Assets are always grouped into packs, never standalone

## Technology Stack

- **Ingestion**: Python 3.x
- **Plugin**: TypeScript, React (Obsidian API)
- **Database**: SQLite (embedded)
- **Notes**: Markdown with YAML frontmatter
- **Data Interchange**: JSON (strict schema)

## Schema Validation is Non-Negotiable

**Every manifest MUST be validated before use:**
- Python scripts: Use `jsonschema` library to validate before saving
- TypeScript plugin: Use `ajv` library to validate before processing
- Invalid manifests should be rejected with clear error messages

See `schemas/README.md` for validation code examples.

## Common Pitfalls to Avoid

1. **Don't skip schema validation** - Both scripts and plugin must validate rigorously
2. **Don't bypass the JSON schema** - All data must flow through `schemas/manifest.schema.json`
3. **Don't use uppercase file extensions** - Normalize to lowercase (schema enforces this)
4. **Don't implement two-way sync** - This is intentionally one-way for simplicity
5. **Don't store absolute paths in SQLite** - Use relative paths within pack root
6. **Don't generate Markdown without updating SQLite** - Both must be updated simultaneously
7. **Don't create orphaned asset records** - Every asset must reference a valid pack_id

## Development Priorities

**Completed**:
1. ✅ Python ingestion library with multi-source architecture
2. ✅ JSON Schema validation
3. ✅ Example manifests and documentation

**In Progress / Planned**:
1. Develop Obsidian plugin with SQLite integration
2. Implement Unity Asset Store source (see `ingestion/TODO.md`)
3. Add advanced filtering and parallel processing (see `ingestion/TODO.md`)

## Working with This Project

When implementing new features:
1. Review the strict JSON schema in ARCHITECTURE.md
2. Ensure all code adheres to the one-way data flow
3. Maintain the dual storage model (SQLite for search, Markdown for organization)
4. Test with realistic asset directory structures (thousands of files)
5. Consider scalability - this system is designed for large asset libraries
