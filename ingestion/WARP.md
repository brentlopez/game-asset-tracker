# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This directory contains ingestion tools for the Game Asset Tracking System. There are two main systems:

1. **`ingest.py`** - Generic asset pack ingestion script that scans local directories
2. **`asset_scraping/`** - Modular marketplace scraping system with unified GUI

### Filesystem Ingestion (`ingest.py`)

Scans asset directories (e.g., on a NAS or local filesystem) and generates standardized JSON manifests that describe Asset Packs and their individual files.

**Role in the larger system:** This script is the first step in a one-way data flow:
```
Python Script (scans filesystem) 
    ↓ generates
JSON Manifest (strict schema)
    ↓ imported via
Obsidian Plugin (creates SQLite index + Markdown notes)
```

### Marketplace Scraping (`asset_scraping/`)

A modular, platform-agnostic system for scraping metadata from online game asset marketplaces. **See `asset_scraping/README.md` for complete documentation.**

**Architecture:**
- `asset_scraper.py` - Platform-agnostic GUI launcher
- `platforms.json` - Platform manifest (defines available platforms)
- `platforms/` - Platform-specific implementations:
  - `platforms/fab/` - Fab (Epic) marketplace scraper
  - `platforms/unity/` - Unity Asset Store scraper

**Each platform has:**
- `gui.py` - GUI module (Setup, Scraping, Post-Processing tabs)
- `setup/` - Authentication scripts
- `scraping/` - Scraping scripts
- `post_processing/` - Post-processing scripts
- `output/` - Generated files
- `docs/` - Platform-specific documentation

## Repository Structure

```
ingestion/
├── ingest.py              # Filesystem ingestion script
├── requirements.txt       # Dependencies for ingest.py
├── README.md              # Overview of ingestion systems
├── WARP.md                # This file
└── asset_scraping/        # Marketplace scraping system
    ├── asset_scraper.py   # Platform-agnostic GUI launcher
    ├── platforms.json     # Platform manifest
    ├── requirements.txt   # Scraping-specific dependencies
    ├── README.md          # Asset scraping documentation
    └── platforms/         # Platform-specific implementations
        ├── fab/           # Fab (Epic) marketplace
        │   ├── gui.py
        │   ├── setup/
        │   ├── scraping/
        │   ├── post_processing/
        │   ├── output/
        │   └── docs/
        └── unity/         # Unity Asset Store
            ├── gui.py
            ├── setup/
            ├── scraping/
            ├── post_processing/
            ├── output/
            └── docs/
```

**Important:** The asset scraping system was refactored (December 2024) to use a modular, platform-agnostic architecture with a manifest-based approach for extensibility.

## Development Commands

### For Generic Ingestion Script (`ingest.py`)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

Dependencies:
- `mutagen` - Audio metadata extraction (optional, script works without it)
- `jsonschema` - **REQUIRED** for validating output against `../schemas/manifest.schema.json`

### Running the Script

**Basic usage:**
```bash
python ingest.py \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store"
```

**With all options:**
```bash
python ingest.py \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store" \
  --tags 3d-models fantasy characters \
  --license "https://example.com/license"
```

**Save output to file:**
```bash
python ingest.py \
  --path /path/to/assets \
  --name "Asset Pack Name" \
  --source "Unity Asset Store" \
  > output.json
```

### Validation

**Validate generated JSON against formal schema:**
```bash
python -c "
import json
import jsonschema

with open('../schemas/manifest.schema.json') as f:
    schema = json.load(f)

with open('output.json') as f:
    manifest = json.load(f)

try:
    jsonschema.validate(instance=manifest, schema=schema)
    print('✓ Valid manifest')
except jsonschema.ValidationError as e:
    print(f'✗ Validation failed: {e.message}')
"
```

### Testing
Currently no automated tests exist. Manual testing approach:
1. Run script on a test directory
2. **Validate JSON output against `../schemas/manifest.schema.json`** (see Validation above)
3. Check that local_tags are correctly derived from folder structure
4. Verify audio metadata extraction (if mutagen installed)

## Architecture (Generic Ingestion Script)

### Core Concepts

**Formal Schema Validation is Mandatory**
All output MUST validate against the formal JSON Schema (Draft 7) at `../schemas/manifest.schema.json`. This schema is the contract between the ingestion script and the Obsidian plugin. The script MUST validate output using the `jsonschema` library before saving.

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

### Key Functions

- `generate_manifest()` - Main orchestrator that generates the complete JSON output
- `scan_directory()` - Recursively walks directory tree and builds asset list
- `derive_local_tags()` - Extracts folder names as tags from relative paths
- `extract_audio_metadata()` - Uses mutagen to get audio file properties

### Data Flow

1. User runs script with CLI arguments
2. Script validates path and arguments
3. `generate_manifest()` generates UUID and resolves absolute path
4. `scan_directory()` walks directory tree:
   - Skips hidden files (starting with `.`)
   - For each file: collects size, extension, relative path
   - Calls `derive_local_tags()` to build tag list from folders
   - For audio files: calls `extract_audio_metadata()` if mutagen available
5. JSON output sent to stdout (progress/errors to stderr)

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

## Design Constraints (Generic Ingestion Script)

1. **Output to stdout, logs to stderr** - JSON goes to stdout so it can be piped; all progress/errors go to stderr
2. **No reverse sync** - This is one-way: filesystem → JSON only
3. **Fail gracefully** - If a single file fails to process, log warning and continue
4. **Schema validation is mandatory** - MUST validate JSON against `../schemas/manifest.schema.json` before outputting
5. **Only save valid JSON** - If validation fails, log errors and exit with non-zero status
6. **Filesystem is source of truth** - JSON can be regenerated anytime

## Common Development Tasks (Generic Ingestion Script)

### Adding Support for New File Types

1. Add file extension to relevant category (e.g., `audio_extensions` set)
2. Implement metadata extraction function (similar to `extract_audio_metadata()`)
3. Call extraction function in `scan_directory()` loop
4. Update README.md with supported formats

### Modifying Tag Derivation Logic

Edit `derive_local_tags()` function. Current logic: splits path and takes all parts except filename.

Possible enhancements:
- Filter out common unhelpful folder names ("Assets", "Files", etc.)
- Normalize casing or formatting
- Apply stop-word filtering

### Adding New CLI Arguments

1. Add argument in `main()` using `argparse`
2. Pass to `generate_manifest()` function
3. Include in manifest dict structure
4. Update README.md examples

## Important Implementation Notes (Generic Ingestion Script)

### Current State (December 2024)
The script currently does NOT implement schema validation. This is a **critical missing feature** that must be added:

**TODO: Add schema validation**
```python
import jsonschema

# After generating manifest, before output:
try:
    with open('../schemas/manifest.schema.json') as f:
        schema = json.load(f)
    jsonschema.validate(instance=manifest, schema=schema)
except jsonschema.ValidationError as e:
    print(f"Schema validation failed: {e.message}", file=sys.stderr)
    sys.exit(1)
```

### Schema Reference Location
The formal schema is at: `../schemas/manifest.schema.json`
Validation examples at: `../schemas/README.md`

## Technology Stack (Generic Ingestion Script)

- **Python:** 3.7+
- **Required dependencies:** jsonschema (for validation)
- **Optional dependencies:** mutagen (audio metadata extraction)
- **Standard library:** argparse, json, pathlib, os, sys, uuid
