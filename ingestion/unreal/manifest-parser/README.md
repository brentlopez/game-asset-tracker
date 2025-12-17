# Epic Games Manifest Parser

Python parser for Epic Games binary manifest files (`.manifest` format) used by the Epic Games Store and Unreal Engine.

## Overview

This parser extracts complete manifest data from Epic's binary format, including:
- Metadata (app name, build version, prerequisites)
- Chunk lookup tables (ChunkHashList, ChunkShaList, DataGroupList, ChunkFilesizeList)
- File manifests with chunk parts for reconstruction
- Custom fields

## Reference Implementation

Based on the C# implementation: https://github.com/NotOfficer/EpicManifestParser

## Binary Format

Epic manifests use a column-major layout for arrays:
- All values of field X, then all values of field Y (not row-by-row records)
- Each structure has a `dataSize` header for seeking past unknown versions
- Strings are length-prefixed (4-byte length + UTF-8 + null terminator)

## Files

- `parse_binary_manifest.py` - Main parser implementation
- `manifest` - JSON reference manifest (Creatures Pack, 315 chunks, 338 files)
- `suburbs_manifest_compressed` - Binary test manifest (23 chunks, 84 files)

## Usage

```bash
python3 parse_binary_manifest.py <input_manifest> [output.json]
```

## Output Format

Generates JSON matching Epic's JSON manifest format with:
- `ManifestFileVersion`, `bIsFileData`, `AppID`
- `AppNameString`, `BuildVersionString`, `LaunchExeString`, `LaunchCommand`
- `PrereqIds`, `PrereqName`, `PrereqPath`, `PrereqArgs`
- `FileManifestList` - Array of files with `Filename`, `FileHash`, `FileChunkParts`
- `ChunkHashList` - Dict mapping chunk GUIDs to rolling hashes
- `ChunkShaList` - Dict mapping chunk GUIDs to SHA1 hashes
- `DataGroupList` - Dict mapping chunk GUIDs to data groups
- `ChunkFilesizeList` - Dict mapping chunk GUIDs to file sizes
- `CustomFields` - Dict of custom key-value pairs

## Development Status

Currently implementing full binary parsing based on UE format specification.
