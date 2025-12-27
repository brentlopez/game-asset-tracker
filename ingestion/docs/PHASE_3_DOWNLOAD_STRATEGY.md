# Phase 3: Download Strategy Implementation - Comprehensive Guide

**Status**: Documentation for future implementation  
**Estimated Effort**: 2-4 days  
**Prerequisites**: Phase 2 complete (Fab integration with metadata-only mode)

## Table of Contents

1. [Overview](#overview)
2. [Context & Rationale](#context--rationale)
3. [Architecture Changes](#architecture-changes)
4. [Implementation Steps](#implementation-steps)
5. [Complete Code Implementations](#complete-code-implementations)
6. [Testing Strategy](#testing-strategy)
7. [Integration & Validation](#integration--validation)
8. [Example Usage](#example-usage)
9. [Performance Considerations](#performance-considerations)
10. [Edge Cases & Gotchas](#edge-cases--gotchas)

---

## Overview

Phase 3 extends Phase 2's metadata-only transformation by adding the ability to download and parse Fab manifests. This provides detailed file listings with accurate sizes and metadata extracted from the manifest structure.

### Goals

- Download Fab manifests for entitled assets
- Parse manifest files (`.manifest` format used by Epic Games)
- Extract individual asset file information (paths, sizes, hashes)
- Support configurable download strategy (`metadata_only` vs `manifests_only`)
- Maintain backward compatibility with Phase 2 metadata-only mode

### Non-Goals

- Downloading actual game asset files (`.uasset`, `.umap`, etc.)
- Full asset installation or extraction
- Verifying file integrity (that's for a future phase)

---

## Context & Rationale

### Why Separate Manifest Downloading from File Downloading?

**Download strategies progress incrementally**:

1. **Phase 2: `metadata_only`** - Just marketplace metadata (fast, no disk I/O)
2. **Phase 3: `manifests_only`** - Download & parse manifests (moderate, ~1-5 MB per manifest)
3. **Future: `full_download`** - Download actual asset files (slow, GB per asset)

This progression allows users to:
- **Catalog quickly**: Get file lists without downloading gigabytes
- **Estimate space**: Know how much disk space needed before downloading
- **Filter wisely**: Only download manifests for assets they're interested in

### Manifest Structure

Fab manifests are compressed binary files containing:
- **Header**: Version, app_id, app_name, build_version
- **File list**: Each file with:
  - `filename`: Relative path within asset
  - `file_hash`: SHA hash for integrity verification
  - `file_chunk_parts`: Array of chunks with sizes

**Key insight**: We can calculate total file size by summing chunk sizes, without downloading the actual file.

### Design Decisions

#### Download Location

Manifests are temporary - they're parsed and discarded:

```python
temp_dir = Path(tempfile.mkdtemp(prefix='fab-manifests-'))
# Download manifest
manifest_result = client.download_manifest(asset, temp_dir)
# Parse immediately
parsed = manifest_result.load()
# Temp dir cleaned up automatically (or explicitly)
```

**Rationale**:
- Manifests are not needed after parsing
- Reduces disk usage
- User can specify custom temp location if needed

#### File Size Calculation

```python
def _calculate_file_size(manifest_file: ManifestFile) -> int:
    """Calculate total file size from chunk parts."""
    return sum(
        chunk.size 
        for chunk_part in manifest_file.file_chunk_parts
        for chunk in chunk_part.chunks
    )
```

**Rationale**:
- Accurate size without downloading files
- Useful for capacity planning
- Matches actual installed size

#### Tag Derivation

Reuse existing `derive_local_tags()` function from filesystem scanner:

```python
from ...scanner import derive_local_tags

local_tags = derive_local_tags(Path(manifest_file.filename))
# "Content/Models/Characters/Hero.uasset" → ["Content", "Models", "Characters"]
```

**Rationale**:
- Consistent tagging across filesystem and marketplace sources
- Enables cross-source search
- Leverages existing tested code

---

## Architecture Changes

### Modified Components

1. **FabSource.get_asset_data()** - Add manifest downloading logic
2. **FabTransformer.transform()** - Add manifest parsing branch
3. **FabTransformer._parse_manifest_files()** - New method (Phase 3)
4. **IngestionPipeline** - Pass download flag based on strategy
5. **AssetData** - Already supports `manifest` field (no changes needed)

### Data Flow

```
User specifies: download_strategy='manifests_only'
    ↓
IngestionPipeline.generate_manifests()
    ↓
Determines: should_download = (strategy == 'manifests_only')
    ↓
source.get_asset_data(asset, download=should_download)
    ↓
[IF download=True]
    client.download_manifest() → manifest_result
    manifest_result.load() → ParsedManifest
    Return AssetData with manifest field populated
    ↓
transformer.transform(asset_data)
    ↓
[IF asset_data.manifest present]
    _parse_manifest_files() → list of ManifestAsset
    ↓
Build Manifest with individual file entries
```

---

## Implementation Steps

### Step 1: Update FabSource to Download Manifests

**File**: `platforms/fab/source.py`

Modify `get_asset_data()` method:

```python
def get_asset_data(
    self,
    asset: SourceAsset,
    download: bool = False
) -> AssetData:
    """Get data for transformation.
    
    Phase 2: Returns metadata only (download=False)
    Phase 3: Downloads and parses manifest (download=True)
    
    Args:
        asset: SourceAsset to retrieve data for
        download: If True, download and parse manifest
        
    Returns:
        AssetData with optional manifest
    """
    if not isinstance(asset, FabAssetAdapter):
        raise ValueError(
            f"Expected FabAssetAdapter, got {type(asset).__name__}"
        )
    
    fab_asset = asset.raw_asset
    
    if download:
        # Phase 3: Download manifest
        print(f"Downloading manifest for {fab_asset.title}...", file=sys.stderr)
        
        # Create temp directory for manifest download
        temp_dir = Path(tempfile.mkdtemp(prefix='fab-manifests-'))
        
        try:
            # Download manifest (fab-api-client handles the download)
            manifest_result = self.client.download_manifest(
                fab_asset,
                download_path=temp_dir
            )
            
            # Parse manifest immediately
            parsed_manifest = manifest_result.load()
            
            print(f"  ✓ Parsed {len(parsed_manifest.files)} files", file=sys.stderr)
            
            return AssetData(
                source_asset=asset,
                metadata={'fab_asset': fab_asset},
                files=[],  # Not downloading actual files yet
                manifest=parsed_manifest,
            )
        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Phase 2: Return metadata only
    return AssetData(
        source_asset=asset,
        metadata={'fab_asset': fab_asset},
        files=[],
        manifest=None,
    )
```

**Key additions**:
- Import `tempfile` at top of file
- Create temporary directory for download
- Call `client.download_manifest()`
- Parse with `manifest_result.load()`
- Clean up temp dir in `finally` block

---

### Step 2: Update FabTransformer to Parse Manifests

**File**: `platforms/fab/transformer.py`

Add manifest parsing logic:

```python
def transform(
    self,
    asset_data: AssetData,
    pack_name: Optional[str] = None,
    global_tags: Optional[list[str]] = None,
    license_link: Optional[str] = None,
    **kwargs
) -> Manifest:
    """Transform Fab asset data into manifest.
    
    Phase 2: Creates placeholder asset if no manifest
    Phase 3: Parses individual files if manifest available
    """
    # Extract Fab asset
    fab_asset: FabAsset = asset_data.metadata.get('fab_asset')
    if not fab_asset:
        raise ValueError("AssetData missing 'fab_asset' in metadata")
    
    # Generate pack-level metadata (same as Phase 2)
    pack_id = str(uuid.uuid4())
    final_pack_name = pack_name or fab_asset.title
    
    if license_link is None and hasattr(fab_asset, 'listing'):
        if hasattr(fab_asset.listing, 'license_url'):
            license_link = fab_asset.listing.license_url or ""
    license_link = license_link or ""
    
    final_global_tags = global_tags or []
    
    # NEW: Check if manifest is available
    if asset_data.manifest:
        # Phase 3: Parse individual files from manifest
        assets = self._parse_manifest_files(
            asset_data.manifest,
            fab_asset
        )
    else:
        # Phase 2: Single placeholder asset
        assets = [self._create_placeholder_asset(fab_asset)]
    
    # Build manifest
    manifest: Manifest = {
        'pack_id': pack_id,
        'pack_name': final_pack_name,
        'root_path': '',
        'source': 'Fab - Epic Games',
        'license_link': license_link,
        'global_tags': final_global_tags,
        'assets': assets,
    }
    
    return manifest
```

---

### Step 3: Implement Manifest File Parsing

**File**: `platforms/fab/transformer.py`

Add new method:

```python
def _parse_manifest_files(
    self,
    parsed_manifest,
    fab_asset: FabAsset
) -> list[ManifestAsset]:
    """Parse individual files from Fab manifest.
    
    Phase 3: Converts ParsedManifest.files into ManifestAsset entries.
    
    Args:
        parsed_manifest: ParsedManifest from fab-api-client
        fab_asset: Original Fab asset for context
        
    Returns:
        List of ManifestAsset entries, one per file in manifest
    """
    from pathlib import Path
    from ...scanner import derive_local_tags
    
    assets: list[ManifestAsset] = []
    
    for manifest_file in parsed_manifest.files:
        # Extract file extension (lowercase, no dot)
        file_path = Path(manifest_file.filename)
        file_type = file_path.suffix.lstrip('.').lower()
        if not file_type:
            file_type = 'unknown'
        
        # Calculate total file size from chunk parts
        size_bytes = self._calculate_file_size(manifest_file)
        
        # Derive local tags from file path
        local_tags = derive_local_tags(file_path)
        
        # Build metadata for this file
        metadata: dict[str, str] = {
            'file_hash': manifest_file.file_hash,
            'build_version': parsed_manifest.build_version,
            'app_name': parsed_manifest.app_name,
        }
        
        # Create asset entry
        asset: ManifestAsset = {
            'relative_path': manifest_file.filename,
            'file_type': file_type,
            'size_bytes': size_bytes,
            'metadata': metadata,
            'local_tags': local_tags,
        }
        
        assets.append(asset)
    
    return assets

def _calculate_file_size(self, manifest_file) -> int:
    """Calculate total file size from chunk parts.
    
    Fab manifests split files into chunks for downloading.
    We sum all chunk sizes to get total file size.
    
    Args:
        manifest_file: ManifestFile from ParsedManifest
        
    Returns:
        Total file size in bytes
    """
    total_size = 0
    
    for chunk_part in manifest_file.file_chunk_parts:
        for chunk in chunk_part.chunks:
            total_size += chunk.size
    
    return total_size
```

**Import addition** (top of file):
```python
import tempfile
from pathlib import Path
```

---

### Step 4: Update IngestionPipeline to Pass Download Flag

**File**: `pipeline.py`

The pipeline already has `download_strategy` configuration. Ensure it's used:

```python
def generate_manifests(self, **kwargs) -> Iterator[Manifest]:
    """Generate manifests for all assets from source."""
    
    # Determine if we should download based on strategy
    should_download = (self.download_strategy == 'manifests_only')
    
    for asset in self.source.list_assets():
        # Pass download flag to source
        asset_data = self.source.get_asset_data(asset, download=should_download)
        
        # Transform to manifest
        manifest = self.transformer.transform(asset_data, **kwargs)
        
        yield manifest
```

**Validation**: This logic should already exist from Phase 1. Verify it passes the download flag correctly.

---

## Complete Code Implementations

### Updated platforms/fab/source.py (Key Changes)

```python
import tempfile
import shutil
import sys
from pathlib import Path
from typing import Iterator, Optional

# ... existing imports ...

class FabSource(Source):
    """Source implementation for Fab marketplace.
    
    Phase 2: Metadata-only mode (download=False)
    Phase 3: Manifest downloading and parsing (download=True)
    """
    
    # ... existing methods ...
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get data for transformation.
        
        Args:
            asset: SourceAsset to retrieve data for
            download: If True, download and parse manifest (Phase 3)
            
        Returns:
            AssetData with optional manifest
        """
        if not isinstance(asset, FabAssetAdapter):
            raise ValueError(
                f"Expected FabAssetAdapter, got {type(asset).__name__}"
            )
        
        fab_asset = asset.raw_asset
        
        if download:
            # Phase 3: Download and parse manifest
            print(f"Downloading manifest for {fab_asset.title}...", file=sys.stderr)
            
            temp_dir = Path(tempfile.mkdtemp(prefix='fab-manifests-'))
            
            try:
                manifest_result = self.client.download_manifest(
                    fab_asset,
                    download_path=temp_dir
                )
                
                parsed_manifest = manifest_result.load()
                print(f"  ✓ Parsed {len(parsed_manifest.files)} files", file=sys.stderr)
                
                return AssetData(
                    source_asset=asset,
                    metadata={'fab_asset': fab_asset},
                    files=[],
                    manifest=parsed_manifest,
                )
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Phase 2: Metadata only
        return AssetData(
            source_asset=asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            manifest=None,
        )
```

### Updated platforms/fab/transformer.py (Key Changes)

```python
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from fab_api_client import Asset as FabAsset

from ...core.types import Manifest, Asset as ManifestAsset
from ...transformers.base import Transformer
from ...sources.base import AssetData
from ...scanner import derive_local_tags


class FabTransformer(Transformer):
    """Transformer for Fab marketplace assets.
    
    Phase 2: Metadata-only transformation
    Phase 3: Manifest parsing with individual file entries
    """
    
    def transform(
        self,
        asset_data: AssetData,
        pack_name: Optional[str] = None,
        global_tags: Optional[list[str]] = None,
        license_link: Optional[str] = None,
        **kwargs
    ) -> Manifest:
        """Transform Fab asset data into manifest.
        
        Supports both Phase 2 (metadata-only) and Phase 3 (with manifest).
        """
        fab_asset: FabAsset = asset_data.metadata.get('fab_asset')
        if not fab_asset:
            raise ValueError("AssetData missing 'fab_asset' in metadata")
        
        # Pack-level metadata
        pack_id = str(uuid.uuid4())
        final_pack_name = pack_name or fab_asset.title
        
        if license_link is None and hasattr(fab_asset, 'listing'):
            if hasattr(fab_asset.listing, 'license_url'):
                license_link = fab_asset.listing.license_url or ""
        license_link = license_link or ""
        
        final_global_tags = global_tags or []
        
        # Asset-level: Parse manifest if available, else placeholder
        if asset_data.manifest:
            assets = self._parse_manifest_files(asset_data.manifest, fab_asset)
        else:
            assets = [self._create_placeholder_asset(fab_asset)]
        
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': '',
            'source': 'Fab - Epic Games',
            'license_link': license_link,
            'global_tags': final_global_tags,
            'assets': assets,
        }
        
        return manifest
    
    def _parse_manifest_files(
        self,
        parsed_manifest,
        fab_asset: FabAsset
    ) -> list[ManifestAsset]:
        """Parse individual files from manifest (Phase 3)."""
        assets: list[ManifestAsset] = []
        
        for manifest_file in parsed_manifest.files:
            file_path = Path(manifest_file.filename)
            file_type = file_path.suffix.lstrip('.').lower() or 'unknown'
            size_bytes = self._calculate_file_size(manifest_file)
            local_tags = derive_local_tags(file_path)
            
            metadata: dict[str, str] = {
                'file_hash': manifest_file.file_hash,
                'build_version': parsed_manifest.build_version,
                'app_name': parsed_manifest.app_name,
            }
            
            asset: ManifestAsset = {
                'relative_path': manifest_file.filename,
                'file_type': file_type,
                'size_bytes': size_bytes,
                'metadata': metadata,
                'local_tags': local_tags,
            }
            
            assets.append(asset)
        
        return assets
    
    def _calculate_file_size(self, manifest_file) -> int:
        """Calculate total file size from chunk parts."""
        total = 0
        for chunk_part in manifest_file.file_chunk_parts:
            for chunk in chunk_part.chunks:
                total += chunk.size
        return total
    
    # Keep existing _create_placeholder_asset() for Phase 2 compatibility
    # ... (unchanged from Phase 2)
```

---

## Testing Strategy

### Test Structure

Extend `tests/test_fab_platform.py` with new test classes:

1. **TestFabSourceWithManifests** - Test manifest downloading
2. **TestFabTransformerWithManifests** - Test manifest parsing
3. **TestDownloadStrategyIntegration** - End-to-end strategy tests

### Mock ParsedManifest Fixture

```python
@pytest.fixture
def mock_parsed_manifest():
    """Mock ParsedManifest for testing."""
    from unittest.mock import Mock
    
    manifest = Mock()
    manifest.version = "1.0"
    manifest.app_id = "fab-asset-123"
    manifest.app_name = "Fantasy Models Pack"
    manifest.build_version = "1.2.3"
    
    # Mock file entries
    file1 = Mock()
    file1.filename = "Content/Models/Character.uasset"
    file1.file_hash = "abc123def456"
    
    # Mock chunk parts for size calculation
    chunk1 = Mock()
    chunk1.size = 1024 * 1024  # 1 MB
    chunk_part1 = Mock()
    chunk_part1.chunks = [chunk1]
    file1.file_chunk_parts = [chunk_part1]
    
    file2 = Mock()
    file2.filename = "Content/Textures/Diffuse.uasset"
    file2.file_hash = "789xyz"
    chunk2 = Mock()
    chunk2.size = 512 * 1024  # 512 KB
    chunk_part2 = Mock()
    chunk_part2.chunks = [chunk2]
    file2.file_chunk_parts = [chunk_part2]
    
    manifest.files = [file1, file2]
    
    return manifest
```

### Test Cases

```python
class TestFabTransformerWithManifests:
    """Tests for manifest parsing (Phase 3)."""
    
    def test_parse_manifest_files(self, sample_fab_assets, mock_parsed_manifest):
        """Test parsing manifest into individual assets."""
        from game_asset_tracker_ingestion.platforms.fab import (
            FabTransformer,
            FabAssetAdapter
        )
        from game_asset_tracker_ingestion.sources.base import AssetData
        
        transformer = FabTransformer()
        fab_asset = sample_fab_assets[0]
        source_asset = FabAssetAdapter(fab_asset)
        
        asset_data = AssetData(
            source_asset=source_asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            manifest=mock_parsed_manifest,
        )
        
        manifest = transformer.transform(asset_data)
        
        # Should have 2 assets (from mock_parsed_manifest)
        assert len(manifest['assets']) == 2
        
        # Check first asset
        asset1 = manifest['assets'][0]
        assert asset1['relative_path'] == "Content/Models/Character.uasset"
        assert asset1['file_type'] == 'uasset'
        assert asset1['size_bytes'] == 1024 * 1024
        assert 'file_hash' in asset1['metadata']
        assert asset1['metadata']['file_hash'] == 'abc123def456'
        assert asset1['local_tags'] == ['Content', 'Models']
        
        # Check second asset
        asset2 = manifest['assets'][1]
        assert asset2['relative_path'] == "Content/Textures/Diffuse.uasset"
        assert asset2['size_bytes'] == 512 * 1024
    
    def test_calculate_file_size(self, mock_parsed_manifest):
        """Test file size calculation from chunks."""
        from game_asset_tracker_ingestion.platforms.fab import FabTransformer
        
        transformer = FabTransformer()
        
        # First file should be 1 MB
        size1 = transformer._calculate_file_size(mock_parsed_manifest.files[0])
        assert size1 == 1024 * 1024
        
        # Second file should be 512 KB
        size2 = transformer._calculate_file_size(mock_parsed_manifest.files[1])
        assert size2 == 512 * 1024
```

```python
class TestDownloadStrategyIntegration:
    """Integration tests for download strategies."""
    
    def test_metadata_only_strategy(self, mock_fab_client):
        """Test metadata_only strategy (Phase 2 behavior)."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client,
            download_strategy='metadata_only'
        )
        
        manifest = next(pipeline.generate_manifests())
        
        # Should have 1 placeholder asset
        assert len(manifest['assets']) == 1
        assert manifest['assets'][0]['file_type'] == 'marketplace'
        assert manifest['assets'][0]['size_bytes'] == 0
    
    def test_manifests_only_strategy(self, mock_fab_client, mock_parsed_manifest):
        """Test manifests_only strategy (Phase 3 behavior)."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        # Mock manifest downloading
        mock_fab_client.download_manifest.return_value.load.return_value = mock_parsed_manifest
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client,
            download_strategy='manifests_only'
        )
        
        manifest = next(pipeline.generate_manifests())
        
        # Should have 2 assets (from parsed manifest)
        assert len(manifest['assets']) == 2
        assert manifest['assets'][0]['file_type'] == 'uasset'
        assert manifest['assets'][0]['size_bytes'] > 0
```

---

## Integration & Validation

### Manual Testing

```python
from fab_egl_adapter import FabEGLAdapter
from fab_api_client import FabClient
from game_asset_tracker_ingestion import SourceRegistry

# Setup client via adapter
adapter = FabEGLAdapter()
auth_provider = adapter.get_auth_provider()
client = FabClient(auth=auth_provider)

# Test metadata-only (Phase 2)
pipeline_meta = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    download_strategy='metadata_only'
)
manifest_meta = next(pipeline_meta.generate_manifests())
print(f"Metadata-only: {len(manifest_meta['assets'])} assets")  # Should be 1

# Test manifests-only (Phase 3)
pipeline_manifest = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    download_strategy='manifests_only'
)
manifest_full = next(pipeline_manifest.generate_manifests())
print(f"With manifests: {len(manifest_full['assets'])} assets")  # Should be 100+

# Verify file details
for asset in manifest_full['assets'][:5]:
    print(f"  {asset['relative_path']}: {asset['size_bytes']} bytes")
```

### Validation Checklist

- [ ] `download_strategy='metadata_only'` still works (backward compatibility)
- [ ] `download_strategy='manifests_only'` downloads and parses manifests
- [ ] File sizes are accurate (sum of chunks)
- [ ] File types extracted correctly from extensions
- [ ] Local tags derived from file paths
- [ ] Metadata includes file_hash, build_version, app_name
- [ ] Temp directories cleaned up after download
- [ ] All tests pass

---

## Example Usage

```python
"""Example: Generate detailed manifests with file listings."""

import json
from pathlib import Path
from fab_egl_adapter import FabEGLAdapter
from fab_api_client import FabClient
from game_asset_tracker_ingestion import SourceRegistry

def main():
    # Setup authentication via adapter
    adapter = FabEGLAdapter()
    auth_provider = adapter.get_auth_provider()
    client = FabClient(auth=auth_provider)
    
    # Create pipeline with manifest downloading
    pipeline = SourceRegistry.create_pipeline(
        'fab',
        client=client,
        download_strategy='manifests_only'  # Phase 3!
    )
    
    output_dir = Path("manifests/fab-detailed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate manifests with file details
    for manifest in pipeline.generate_manifests():
        pack_name = manifest['pack_name']
        file_count = len(manifest['assets'])
        total_size = sum(a['size_bytes'] for a in manifest['assets'])
        
        print(f"\n{pack_name}")
        print(f"  Files: {file_count}")
        print(f"  Total size: {total_size / (1024**3):.2f} GB")
        
        # Save to file
        output_file = output_dir / f"{manifest['pack_id']}.json"
        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)

if __name__ == '__main__':
    main()
```

---

## Performance Considerations

### Download Time

- **Manifest size**: 1-5 MB typically
- **Download time**: 5-30 seconds per asset (depends on connection)
- **For 100 assets**: ~10-50 minutes total

**Mitigation**:
- Progress feedback (already implemented with stderr prints)
- Consider parallel downloads (future enhancement)
- Allow interruption and resume (future enhancement)

### Memory Usage

- **Parsed manifest**: ~10-50 MB in memory
- **Per-file overhead**: ~1 KB per file entry
- **Large packs**: 10,000 files = ~10 MB + manifest

**Mitigation**:
- Temp directories cleaned immediately after parsing
- No need to cache - parse once, generate manifest, discard

### Disk Usage

- **Temp storage**: 1-5 MB per manifest download
- **Cleanup**: Automatic via `finally` block
- **Failure cases**: Use `shutil.rmtree(ignore_errors=True)`

---

## Edge Cases & Gotchas

### Network Failures

```python
try:
    manifest_result = self.client.download_manifest(...)
except NetworkError as e:
    print(f"Warning: Failed to download manifest: {e}", file=sys.stderr)
    # Fall back to metadata-only mode
    return AssetData(source_asset=asset, metadata={...}, manifest=None)
```

### Malformed Manifests

```python
try:
    parsed_manifest = manifest_result.load()
except Exception as e:
    print(f"Warning: Failed to parse manifest: {e}", file=sys.stderr)
    return AssetData(source_asset=asset, metadata={...}, manifest=None)
```

### Empty File Lists

Some manifests may have zero files (rare, but possible):

```python
if not parsed_manifest.files:
    print(f"Warning: Manifest has no files", file=sys.stderr)
    # Fall back to placeholder
    assets = [self._create_placeholder_asset(fab_asset)]
```

### Chunk Size Edge Cases

Handle missing or zero-size chunks:

```python
def _calculate_file_size(self, manifest_file) -> int:
    total = 0
    for chunk_part in manifest_file.file_chunk_parts:
        if not hasattr(chunk_part, 'chunks'):
            continue
        for chunk in chunk_part.chunks:
            if hasattr(chunk, 'size'):
                total += chunk.size
    return max(0, total)  # Never return negative
```

---

## Summary

Phase 3 extends Phase 2 by adding manifest downloading and parsing:

**New capabilities**:
- Download Fab manifests (`download_strategy='manifests_only'`)
- Parse individual file entries from manifests
- Calculate accurate file sizes from chunk data
- Derive tags from file paths

**Backward compatibility**:
- Phase 2 mode still works (`download_strategy='metadata_only'`)
- Graceful fallback when downloads fail

**Next steps**:
- Phase 4: Documentation for extensions and filtering
- Phase 5: UAS integration following same pattern
- Future: Full file downloading and installation

This phase provides users with detailed file listings without downloading gigabytes of actual game assets.
