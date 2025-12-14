# Ingestion Scripts

Python scripts for scanning asset directories and generating JSON manifests conforming to the strict schema defined in `ARCHITECTURE.md`.

## Overview

The ingestion script (`ingest.py`) recursively scans a directory tree and generates a standardized JSON manifest containing:
- Pack-level metadata (name, source, tags, license)
- Asset-level metadata for every file (path, type, size, tags)
- Heuristic tagging derived from folder structure
- Optional audio metadata extraction (duration, sample rate, etc.)

## Installation

### Requirements
- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   The only dependency is `mutagen` for audio metadata extraction. If you don't need audio metadata, the script will work without it.

2. **Make the script executable (optional):**
   ```bash
   chmod +x ingest.py
   ```

## Usage

### Basic Syntax

```bash
python ingest.py --path <directory> --name "<pack_name>" --source "<source>" [--tags <tag1> <tag2> ...] [--license <url>]
```

### Required Arguments

- `--path`: Root directory to scan (absolute or relative path)
- `--name`: Human-readable name of the asset pack
- `--source`: Origin of the pack (e.g., "Unity Asset Store", "Epic Marketplace", "NAS")

### Optional Arguments

- `--tags`: Space-separated list of global tags for the entire pack
- `--license`: URL or file path to license documentation

### Examples

**1. Basic usage with minimal arguments:**
```bash
python ingest.py \
  --path /Volumes/NAS/Assets/Unity/DragonPack \
  --name "Dragon Character Pack" \
  --source "Unity Asset Store"
```

**2. With global tags:**
```bash
python ingest.py \
  --path /Volumes/NAS/Assets/Unity/DragonPack \
  --name "Dragon Character Pack" \
  --source "Unity Asset Store" \
  --tags 3d-models characters fantasy dragons
```

**3. With license link:**
```bash
python ingest.py \
  --path /Volumes/NAS/Assets/Unity/DragonPack \
  --name "Dragon Character Pack" \
  --source "Unity Asset Store" \
  --tags 3d-models characters fantasy dragons \
  --license "https://assetstore.unity.com/license"
```

**4. Pipe output to a file:**
```bash
python ingest.py \
  --path /Volumes/NAS/Assets/Unity/DragonPack \
  --name "Dragon Character Pack" \
  --source "Unity Asset Store" \
  --tags 3d-models characters fantasy \
  > dragon_pack_manifest.json
```

**5. Scan a relative path:**
```bash
python ingest.py \
  --path ../my-assets/sound-effects \
  --name "Sound Effects Pack" \
  --source "NAS" \
  --tags audio sfx
```

## Output

The script outputs JSON to `stdout` (standard output), which can be:
- Displayed in the terminal (default)
- Piped to a file using `> output.json`
- Piped to another command for processing

Progress messages and warnings are sent to `stderr` (standard error), so they won't interfere with the JSON output when piping.

### Example Output

```json
{
  "pack_id": "550e8400-e29b-41d4-a716-446655440000",
  "pack_name": "Dragon Character Pack",
  "root_path": "/Volumes/NAS/Assets/Unity/DragonPack",
  "source": "Unity Asset Store",
  "license_link": "https://assetstore.unity.com/license",
  "global_tags": ["3d-models", "characters", "fantasy", "dragons"],
  "assets": [
    {
      "relative_path": "Models/Dragon_Red.fbx",
      "file_type": "fbx",
      "size_bytes": 4567890,
      "metadata": {},
      "local_tags": ["Models"]
    },
    {
      "relative_path": "Audio/DragonRoar.wav",
      "file_type": "wav",
      "size_bytes": 1234567,
      "metadata": {
        "duration": "3.50s",
        "sample_rate": "44100",
        "bitrate": "705600",
        "channels": "1"
      },
      "local_tags": ["Audio"]
    }
  ]
}
```

## Features

### Heuristic Tagging

The script automatically derives tags from the folder structure. For example:

```
Assets/
├── Audio/
│   ├── Explosions/
│   │   └── SciFi/
│   │       └── boom.wav  → local_tags: ["Audio", "Explosions", "SciFi"]
│   └── Music/
│       └── theme.mp3     → local_tags: ["Audio", "Music"]
└── Textures/
    └── Diffuse/
        └── rock.png      → local_tags: ["Textures", "Diffuse"]
```

This creates a rich, searchable taxonomy without manual tagging.

### Audio Metadata Extraction

When `mutagen` is installed, the script automatically extracts:
- Duration (in seconds)
- Sample rate
- Bitrate
- Number of channels

Supported audio formats: WAV, MP3, OGG, FLAC, M4A, AAC, WMA

If `mutagen` is not installed or extraction fails, the script continues without audio metadata.

### UUID Generation

Each manifest gets a unique UUID (`pack_id`) for database referencing. The UUID is generated automatically using Python's `uuid.uuid4()`.

### Error Handling

- **Missing path**: Script exits with error message
- **Invalid directory**: Script exits with error message
- **File processing errors**: Warnings logged to stderr, but processing continues
- **Audio metadata failures**: Silent failure, continues without metadata

## Next Steps

After generating a JSON manifest:

1. **Import into Obsidian**: Use the Obsidian plugin (to be developed) to import the JSON
2. **Database Population**: The plugin will automatically populate the SQLite database
3. **Note Creation**: The plugin will create a Markdown note for the Asset Pack

## Schema Reference

The output JSON strictly conforms to the schema defined in `../ARCHITECTURE.md`. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string (UUID) | Unique identifier |
| `pack_name` | string | Human-readable name |
| `root_path` | string | Absolute path to pack root |
| `source` | string | Origin of the pack |
| `license_link` | string | License URL or path |
| `global_tags` | array[string] | Tags for entire pack |
| `assets` | array[object] | List of individual files |
| `assets[].relative_path` | string | Path relative to root |
| `assets[].file_type` | string | File extension |
| `assets[].size_bytes` | integer | File size in bytes |
| `assets[].metadata` | object | Format-specific metadata |
| `assets[].local_tags` | array[string] | Tags from folder structure |

## Troubleshooting

### "mutagen not found" warning
This is normal if you haven't installed mutagen. Audio files will still be processed, just without duration/sample rate metadata.

**Solution**: Install mutagen with `pip install mutagen`

### Script skips hidden files
This is intentional. Files starting with `.` (like `.DS_Store`) are ignored.

### Relative path issues
If relative paths appear incorrect, ensure you're running the script from the correct directory or use absolute paths.

### Permission errors
Ensure you have read access to all files in the target directory.

## Contributing

When modifying the ingestion script:
1. Ensure output conforms to the strict schema in `ARCHITECTURE.md`
2. Maintain backward compatibility with existing JSON manifests
3. Add error handling for new features
4. Update this README with new functionality

## License

See the main project README for license information.
