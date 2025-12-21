# Unreal Engine VaultCache Ingestion Script

This script ingests Unreal Engine assets directly from the local VaultCache directory where the Epic Games Launcher stores downloaded assets from the Fab marketplace.

## Overview

The script:
1. Scans the VaultCache directory at `/Users/Shared/UnrealEngine/Launcher/VaultCache` (macOS)
2. Parses JSON manifest files to extract asset pack metadata and file lists
3. Merges with web-scraped metadata from `fab_metadata.json` to add tags and descriptions
4. Gets actual file sizes from the `data/` folder (manifest sizes are in an encoded format)
5. Generates standardized JSON manifests conforming to the Game Asset Tracking System schema

## Requirements

- Python 3.7+
- Standard library only (no external dependencies)
- Access to the VaultCache directory
- Web metadata from the Fab scraper (optional but recommended)

## Usage

```bash
# Run the script
python3 ingest_vault.py

# Or make it executable and run directly
chmod +x ingest_vault.py
./ingest_vault.py
```

## Input

### VaultCache Structure
```
/Users/Shared/UnrealEngine/Launcher/VaultCache/
├── 10Creatu32251a2e4ae3V1/        # Asset folder (GUID-based name)
│   ├── manifest                    # JSON manifest with metadata
│   └── data/                       # Actual asset files
│       └── Content/
│           └── ...
├── ModularW0e8fc5138170V1/
│   ├── manifest
│   └── data/
└── FabLibrary/                     # Metadata folder (skipped)
    └── listings_v1.db
```

### Web Metadata
The script can optionally use `fab_metadata.json` which contains:
- Asset titles
- Tags
- Descriptions
- License info
- Original Fab URLs

## Output

### Location
`output/vault_assets.json`

### Format
Array of asset pack manifests conforming to the global schema:

```json
[
  {
    "pack_id": "46ceb905-8a60-4d94-b458-329c086b9b6b",
    "pack_name": "10 Creatures (Pack)",
    "root_path": "/Users/Shared/UnrealEngine/Launcher/VaultCache/10Creatu32251a2e4ae3V1/data",
    "source": "Fab Marketplace",
    "license_link": "https://www.fab.com/listings/0094617c-9eba-433a-8a5e-d3e0aba5735b",
    "global_tags": ["monster", "pbr", "lowpoly", "fantasy", "script"],
    "assets": [
      {
        "relative_path": "Content/Creatures_10_Pack/Demoscene_UE4/Animations/ThirdPerson_Jump.uasset",
        "file_type": "uasset",
        "size_bytes": 112960,
        "local_tags": ["content", "creatures-10-pack", "demoscene-ue4", "animations"]
      }
    ]
  }
]
```

## Manifest Parsing Details

### Title Extraction
1. **Primary**: `CustomFields["Vault.TitleText"]` - Human-readable asset name
2. **Fallback**: `AppNameString` - Machine identifier
3. **Last resort**: Folder name

### File Size Extraction
- Manifest chunk sizes are in an **encoded format** (not reliable)
- Script reads actual file sizes from the `data/` folder using `stat()`
- Files that don't exist yet are reported as 0 bytes

### Tag Derivation
- **Global tags**: From web metadata (if matched)
- **Local tags**: Derived from folder structure in file paths
  - Example: `Content/Creatures_10_Pack/Animations/file.uasset` → `["content", "creatures-10-pack", "animations"]`
  - Normalized: lowercase, underscores/spaces replaced with hyphens

## Matching Logic

The script matches VaultCache assets with web metadata by:
1. Extracting `Vault.TitleText` from the manifest
2. Performing case-insensitive lookup in `fab_metadata.json`
3. Merging tags and license URLs from matched entries

### Orphan Assets
Assets found in VaultCache but not in web metadata are still included, but without:
- Global tags
- Web-scraped license URLs (may have `Vault.ActionUrl` instead)

## Example Output

```
Loading web metadata...
Loaded 154 web metadata entries

Scanning VaultCache at /Users/Shared/UnrealEngine/Launcher/VaultCache...
Info: Skipping binary manifest in ModularW0e8fc5138170V1

✓ Success!
Found 1 cached assets. 1 matched with Web Metadata.

Output written to: /Users/brentlopez/Projects/game-asset-tracker/ingestion/unreal/vault-parser/output/vault_assets.json
```

## Limitations

### V1 Scope
- **Binary manifests**: Not supported (skipped with warning)
- **File validation**: No checksums or integrity verification
- **Incremental updates**: Full re-scan each time (no caching)

### Known Issues
- Assets downloading but not yet installed may have incomplete file lists
- Manifest format may change between Unreal Engine versions
- Some assets use non-JSON manifest formats (binary)

## Future Enhancements

- [ ] Support binary manifest parsing
- [ ] Incremental scanning (only changed assets)
- [ ] File integrity verification (checksums from manifest)
- [ ] Better error handling for corrupted manifests
- [ ] Progress bar for large asset collections
- [ ] Export to multiple formats (CSV, SQLite)

## Integration with Asset Tracking System

This script generates JSON that can be:
1. Imported into the Obsidian plugin
2. Used to create Markdown notes for asset packs
3. Indexed into SQLite for fast searching
4. Combined with other ingestion scripts (NAS, Unity, etc.)

See `../../ARCHITECTURE.md` for the complete system design.
