# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This directory contains the **game-asset-tracker-ingestion** Python package - a modern, type-safe tool for scanning asset directories and generating validated JSON manifests.

### Filesystem Ingestion

Scans asset directories (e.g., on a NAS or local filesystem) and generates standardized JSON manifests that describe Asset Packs and their individual files.

**Role in the larger system:** This package is the first step in a one-way data flow:
```
Python Package (scans filesystem)
    ↓ generates
JSON Manifest (validated against schema)
    ↓ imported via
Obsidian Plugin (creates SQLite index + Markdown notes)
```


## Repository Structure

```
ingestion/
├── src/
│   └── game_asset_tracker_ingestion/
│       ├── __init__.py         # Package exports
│       ├── cli.py              # CLI entry point
│       ├── scanner.py          # Directory scanning & security
│       ├── metadata.py         # Format-specific metadata extraction
│       ├── validator.py        # JSON schema validation
│       └── types.py            # TypedDict definitions
├── tests/
│   ├── __init__.py
│   └── test_scanner.py         # Security & functionality tests
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

### Running the Script

**Basic usage:**
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
