# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This directory contains the **game-asset-tracker-ingestion** Python package - a modern, type-safe, modular library for generating validated JSON manifests from multiple sources.

### Multi-Source Architecture

The library supports ingestion from:
- **Filesystem**: Local directory scanning (NAS, local drives)
- **Marketplaces**: Fab marketplace (via fab-api-client), Unity Asset Store (planned)
- **Custom sources**: Extensible architecture for third-party integrations

**Role in the larger system:** This package is the first step in a one-way data flow:
```
Multiple Sources (filesystem, Fab, UAS, custom)
    ↓ unified pipeline
JSON Manifests (validated against schema)
    ↓ imported via
Obsidian Plugin (creates SQLite index + Markdown notes)
```

**Key architectural components**:
- `Source` ABC: Interface for data retrieval
- `Transformer` ABC: Converts source data to standardized manifests
- `IngestionPipeline`: Orchestrates source → transformation → output
- `SourceRegistry`: Auto-discovers and manages available sources


## Repository Structure

```
ingestion/
├── src/
│   └── game_asset_tracker_ingestion/
│       ├── __init__.py         # Package exports & auto-discovery
│       ├── cli.py              # CLI entry point (legacy)
│       ├── scanner.py          # Filesystem utilities (legacy)
│       ├── pipeline.py         # Main ingestion pipeline
│       ├── registry.py         # Source factory registry
│       ├── core/               # Core types and utilities
│       │   ├── types.py        # TypedDict definitions
│       │   ├── validator.py    # JSON schema validation
│       │   └── metadata.py     # Format-specific metadata extraction
│       ├── sources/            # Base abstractions
│       │   └── base.py         # Source, SourceAsset, AssetData
│       ├── transformers/       # Base transformer
│       │   └── base.py         # Transformer ABC
│       └── platforms/          # Source implementations
│           ├── filesystem/     # Local directory scanning
│           │   ├── source.py
│           │   └── transformer.py
│           └── fab/            # Fab marketplace integration
│               ├── source.py
│               └── transformer.py
├── tests/                      # Test suite
│   ├── test_scanner.py         # Security & filesystem tests
│   └── test_fab_platform.py    # Fab platform tests
├── examples/                   # Example scripts
│   ├── filesystem_basic.py
│   ├── fab_metadata_only.py
│   ├── fab_with_manifests.py
│   └── custom_source.py
├── docs/                       # Phase documentation
│   ├── PHASE_2_FAB_INTEGRATION.md
│   ├── PHASE_3_DOWNLOAD_STRATEGY.md
│   └── PHASE_4_DOCUMENTATION.md
├── EXTENDING.md                # Developer guide for custom sources
├── TODO.md                     # Planned future enhancements
├── pyproject.toml              # Project configuration (uv format)
├── uv.lock                     # Locked dependencies
├── README.md                   # User documentation
└── WARP.md                     # This file
```

## Development Commands

### Setup
```bash
# Install all dependencies (creates .venv/ automatically)
uv sync

# Install with dev dependencies
uv sync --group dev
```

**Dependencies:**
- Runtime: `jsonschema` (required), `mutagen` (optional for audio metadata)
- Dev: `ruff`, `mypy`, `pytest`, `pytest-cov`, `types-jsonschema`

### Library Usage

**Filesystem scanning:**
```python
from pathlib import Path
from game_asset_tracker_ingestion import SourceRegistry

pipeline = SourceRegistry.create_pipeline('filesystem', path=Path('/path/to/assets'))
for manifest in pipeline.generate_manifests():
    print(f"Generated: {manifest['pack_name']}")
```

**Fab marketplace** (requires `uv sync --extra fab`):
```python
from fab_api_client import FabClient
from game_asset_tracker_ingestion import SourceRegistry

# Setup authentication (see fab-api-client docs)
client = FabClient(auth=auth_provider)

pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    download_strategy='metadata_only'  # or 'manifests_only'
)

for manifest in pipeline.generate_manifests():
    print(f"Generated: {manifest['pack_name']}")
```

**Custom sources**: See [EXTENDING.md](EXTENDING.md) for implementation guide.

### CLI Usage (Legacy)

**Basic CLI usage:**
```bash
uv run ingest \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store"
```

**With all options:**
```bash
uv run ingest \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store" \
  --tags 3d-models fantasy characters \
  --license "https://example.com/license"
```

**Save output to file:**
```bash
uv run ingest \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store" \
  > output.json
```

### Code Quality

**Run linting:**
```bash
# Check for issues
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/
```

**Run type checking:**
```bash
uv run mypy src/
```

### Testing

**Run all tests:**
```bash
uv run pytest
```

**Run with coverage:**
```bash
uv run pytest --cov=game_asset_tracker_ingestion --cov-report=term-missing
```

**Run specific test file:**
```bash
uv run pytest tests/test_scanner.py -v
```

**Note:** Schema validation is **automatically performed** by the CLI before outputting JSON. Invalid manifests will fail with detailed error messages.

## Architecture

### Multi-Source Design

The library uses an extensible, plugin-based architecture:

**Core abstractions** (`sources/base.py`, `transformers/base.py`):
- `SourceAsset` Protocol: Minimal interface (`uid`, `title`) that all assets must implement
- `Source` ABC: Interface for retrieving assets from any data source
- `Transformer` ABC: Converts source-specific data to standardized manifests
- `AssetData`: Container for raw data before transformation

**Pipeline** (`pipeline.py`):
- `IngestionPipeline`: Platform-agnostic orchestrator
- Calls `source.list_assets()` → `source.get_asset_data()` → `transformer.transform()`
- Supports filtering and download strategies

**Registry** (`registry.py`):
- `SourceRegistry`: Manages factory functions for creating sources
- Auto-discovers platforms in `platforms/` directory via `discover_platforms()`
- Platforms self-register when imported (see `platforms/*/` __init__.py files)

**Current implementations**:
- `platforms/filesystem/`: Scans local directories
- `platforms/fab/`: Integrates with Fab marketplace via fab-api-client

**Extending**: See [EXTENDING.md](EXTENDING.md) for guide on implementing custom sources.

### Core Concepts

**Formal Schema Validation is Mandatory**
All output is validated against the formal JSON Schema (Draft 7) at `../schemas/manifest.schema.json`. This schema is the contract between the ingestion package and the Obsidian plugin. The `validator.py` module handles validation using the `jsonschema` library.

Key validation rules enforced by the schema:
- `pack_id` must be a valid UUID (lowercase, hyphenated format: `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
- `file_type` must be lowercase alphanumeric only (pattern: `^[a-z0-9]+$`)
- `assets` array must contain at least 1 item
- `size_bytes` must be non-negative integer
- Tags must be unique within their arrays
- No additional properties allowed beyond those defined in schema

**Heuristic Tagging**
The script automatically derives `local_tags` from folder structure:
```
Assets/Audio/Explosions/SciFi/boom.wav → local_tags: ["Audio", "Explosions", "SciFi"]
```
This creates a searchable taxonomy without manual tagging.

**Metadata Extraction**
- Audio files: Uses `mutagen` to extract duration, sample rate, bitrate, channels
- All files: Extracts size_bytes and file_type (extension)

### Key Modules

**`cli.py`** - Command-line interface
- `main()` - Entry point for the `ingest` command
- `generate_manifest()` - Orchestrates manifest generation
- Handles argument parsing and validation
- Calls schema validator before output

**`scanner.py`** - Directory scanning with security
- `scan_directory()` - Recursively walks directory tree
- `validate_path_safety()` - Prevents path traversal attacks
- `validate_url()` - Validates license URLs (http/https only)
- `sanitize_filename()` - Removes dangerous characters
- `derive_local_tags()` - Extracts folder names as tags

**`metadata.py`** - Format-specific metadata extraction
- `extract_metadata()` - Dispatcher for different file types
- `extract_audio_metadata()` - Uses mutagen for audio files
- Returns TypedDict for type safety

**`validator.py`** - JSON schema validation
- `validate_manifest()` - Validates against schema, raises on error
- `validate_manifest_with_error_details()` - Returns user-friendly errors
- `load_schema()` - Loads schema from `../schemas/manifest.schema.json`

**`types.py`** - Type definitions
- `Manifest` - TypedDict for complete manifest structure
- `Asset` - TypedDict for individual asset files
- `AssetMetadata` - Flexible TypedDict for format-specific metadata

### Data Flow

1. User runs `uv run ingest` with CLI arguments
2. `cli.main()` validates path exists and is a directory
3. `cli.generate_manifest()` generates UUID and resolves absolute path
4. `scanner.validate_url()` validates license URL if provided
5. `scanner.scan_directory()` walks directory tree:
   - Skips hidden files (starting with `.`)
   - For each file: validates path safety
   - Collects size, extension, relative path
   - Calls `metadata.extract_metadata()` for format-specific data
   - Calls `scanner.derive_local_tags()` from folder structure
   - Truncates metadata strings if too long (DoS prevention)
6. `validator.validate_manifest_with_error_details()` validates against schema
7. If valid: JSON output to stdout (progress/errors to stderr)
8. If invalid: Error message to stderr, exit code 1

## JSON Schema Reference (Generic Ingestion Script)

The script MUST generate JSON conforming to this schema:

```json
{
  "pack_id": "UUID (auto-generated)",
  "pack_name": "string (from --name)",
  "root_path": "absolute path (resolved from --path)",
  "source": "string (from --source)",
  "license_link": "string (from --license, optional)",
  "global_tags": ["array", "from", "--tags"],
  "assets": [
    {
      "relative_path": "path/to/file.ext",
      "file_type": "ext",
      "size_bytes": 12345,
      "metadata": {"duration": "3.50s"},  // optional, audio only
      "local_tags": ["path", "to"]         // derived from folders
    }
  ]
}
```

**Critical Rules (enforced by `../schemas/manifest.schema.json`):**
- `pack_id`: Generated via `uuid.uuid4()`, lowercase hyphenated UUID format
- `pack_name`: Required, 1-255 characters
- `root_path`: Required, absolute path (use `Path.resolve()`)
- `source`: Optional, max 255 characters
- `license_link`: Optional, max 2048 characters
- `global_tags`: Optional array, unique items, each tag 1-100 chars
- `assets`: Required array, minimum 1 item
- `assets[].relative_path`: Required, relative to root_path
- `assets[].file_type`: Required, lowercase alphanumeric only (no dots), 1-20 chars
- `assets[].size_bytes`: Required, non-negative integer
- `assets[].metadata`: Optional object, all values must be strings
- `assets[].local_tags`: Optional array, unique items, each tag 1-100 chars

## Design Constraints

1. **Output to stdout, logs to stderr** - JSON goes to stdout so it can be piped; all progress/errors go to stderr
2. **No reverse sync** - This is one-way: filesystem → JSON only
3. **Fail gracefully** - If a single file fails to process, log warning and continue
4. **Schema validation is mandatory** - Validates JSON against `../schemas/manifest.schema.json` before outputting
5. **Only output valid JSON** - If validation fails, log errors and exit with non-zero status
6. **Filesystem is source of truth** - JSON can be regenerated anytime
7. **Security first** - Path traversal prevention, URL validation, metadata size limits
8. **Type safety** - Full type hints, passes mypy strict mode

## Common Development Tasks

### Adding Support for New File Types

1. Add file extension to relevant set in `metadata.py` (e.g., `AUDIO_EXTENSIONS`)
2. Implement extraction function (similar to `extract_audio_metadata()`)
3. Add conditional in `extract_metadata()` dispatcher
4. Add type ignore comments for TypedDict keys if needed
5. Add tests in `tests/test_metadata.py`
6. Update README.md with supported formats

### Modifying Tag Derivation Logic

Edit `derive_local_tags()` in `scanner.py`. Current logic: splits path and takes all parts except filename.

Possible enhancements:
- Filter out common unhelpful folder names ("Assets", "Files", etc.)
- Normalize casing or formatting
- Apply stop-word filtering
- Add tests in `tests/test_scanner.py`

### Implementing a Custom Source

For detailed guidance, see [EXTENDING.md](EXTENDING.md).

**Quick overview**:

1. **Create asset adapter** implementing `SourceAsset` protocol (requires `uid` and `title` properties)
2. **Implement `Source` ABC** with `list_assets()`, `get_asset()`, `get_asset_data()`, `get_transformer()`
3. **Implement `Transformer` ABC** with `transform()` method
4. **Register source** via `SourceRegistry.register_factory(name, factory_fn)`
5. **Auto-discovery**: Place in `platforms/{name}/` directory with `__init__.py` that registers the source

**Reference implementations**:
- Simple: `platforms/filesystem/` - Direct directory scanning
- API-based: `platforms/fab/` - Marketplace integration with authentication
- Template: `examples/custom_source.py` - Minimal working example

**Related projects**:
- [asset-marketplace-client-core](https://github.com/brentlopez/asset-marketplace-client-core): Architecture patterns for marketplace adapters
- [fab-api-client](https://github.com/brentlopez/fab-api-client): Fab marketplace client
- [uas-api-client](https://github.com/brentlopez/uas-api-client): Unity Asset Store client

### Adding New CLI Arguments

1. Add argument in `cli.main()` using `argparse`
2. Pass to `cli.generate_manifest()` function
3. Update `types.Manifest` TypedDict if needed
4. Update schema at `../schemas/manifest.schema.json` if needed
5. Add validation in `cli.generate_manifest()` if needed
6. Update README.md examples

## Important Implementation Notes

### Security Features (December 2024)

**Path Traversal Prevention**
```python
from scanner import validate_path_safety

# Ensures paths stay within base directory
validate_path_safety(file_path, base_dir)
# Raises ValueError if path escapes base directory
```

**URL Validation**
```python
from scanner import validate_url

# Only allows http/https schemes
validate_url(license_link)
# Raises ValueError for javascript:, file://, data:, etc.
```

**Metadata Size Limits**
```python
# In scanner.py
MAX_METADATA_STRING_LENGTH = 2048
# Truncates metadata strings to prevent DoS attacks
```

### Schema Validation

Schema validation is **automatically performed** in `cli.main()` before outputting JSON:
```python
from validator import validate_manifest_with_error_details

is_valid, error_msg = validate_manifest_with_error_details(manifest)
if not is_valid:
    print(f"Error: Manifest validation failed:", file=sys.stderr)
    print(error_msg, file=sys.stderr)
    sys.exit(1)
```

The formal schema is at: `../schemas/manifest.schema.json`

## Technology Stack

- **Python:** 3.11+ (uses modern type hints like PEP 604 union types)
- **Package Manager:** uv (fast, modern alternative to pip)
- **Build Backend:** Hatchling (PEP 517 compliant)
- **Required dependencies:** jsonschema (validation), mutagen (audio metadata)
- **Dev dependencies:** ruff (linting/formatting), mypy (type checking), pytest (testing)
- **Standard library:** argparse, json, pathlib, os, sys, uuid, re, urllib

## Testing

**Test Coverage:** 42% (focused on security features)

Key test areas:
- Path traversal prevention (`test_scanner.py`)
- Filename sanitization (`test_scanner.py`)
- URL validation (`test_scanner.py`)
- Symlink handling within base directory

**Running Tests:**
```bash
# All tests
uv run pytest

# With coverage report
uv run pytest --cov

# Specific test class
uv run pytest tests/test_scanner.py::TestValidatePathSafety -v
```
