# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a hybrid system for managing game development assets at scale. It combines:
- **Obsidian** for high-level Asset Pack organization (Markdown notes, linking, tagging)
- **SQLite** for granular file-level search across thousands of individual asset files
- **Python scripts** for automated ingestion from asset directories
- **TypeScript/Obsidian plugin** for bridging JSON manifests to the database and notes

The project is currently **scaffolded** with architecture defined but not yet implemented.

## Critical Architecture Concepts

### Data Flow (One-Way Sync)
```
Python Script (scans filesystem)
    ↓ generates
JSON Manifest (strict schema)
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

### For Python Ingestion Scripts
- Target: Python 3.x
- Must generate JSON conforming to `schemas/manifest.schema.json`
- **CRITICAL**: Always validate output using `jsonschema` library before saving
- Key tasks:
  - Recursively scan asset directories
  - Generate UUIDs (lowercase, hyphenated format)
  - Normalize file extensions to lowercase (`.PNG` → `png`)
  - Extract file metadata (size in bytes, format-specific data as strings)
  - Derive tags from folder structure
  - Validate and output JSON only if it passes schema validation

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

Since the project is scaffolded but not implemented, there are no build/test commands yet.

### When Python Scripts Are Implemented
Expected commands will likely be:
```bash
# Run ingestion script
python ingestion/ingest.py --path /path/to/assets --output output.json

# Install dependencies
pip install -r ingestion/requirements.txt
```

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

## Future Development Priorities (from README)

1. Implement Python ingestion script
2. Develop Obsidian plugin with SQLite integration
3. Create JSON Schema validation
4. Add example manifests and test data

## Working with This Project

When implementing new features:
1. Review the strict JSON schema in ARCHITECTURE.md
2. Ensure all code adheres to the one-way data flow
3. Maintain the dual storage model (SQLite for search, Markdown for organization)
4. Test with realistic asset directory structures (thousands of files)
5. Consider scalability - this system is designed for large asset libraries
