# Phase 4: Documentation & Extension Points - Comprehensive Guide

**Status**: Documentation for future implementation  
**Estimated Effort**: 3-5 days  
**Prerequisites**: Phases 1-3 complete (core architecture, Fab integration, download strategy)

## Table of Contents

1. [Overview](#overview)
2. [Goals & Scope](#goals--scope)
3. [EXTENDING.md - Developer Guide](#extendingmd---developer-guide)
4. [TODO.md - Future Enhancements](#todomd---future-enhancements)
5. [README.md Updates](#readmemd-updates)
6. [Example Scripts](#example-scripts)
7. [Plugin System Design](#plugin-system-design)
8. [Configuration System Design](#configuration-system-design)
9. [Advanced Filtering Design](#advanced-filtering-design)
10. [Metadata Storage Solutions](#metadata-storage-solutions)

---

## Overview

Phase 4 focuses on **documentation and extensibility** rather than implementation. The goal is to create comprehensive guides that enable:

1. **Third-party developers** to extend the system with custom sources
2. **Future implementers** to add planned features with clear specifications
3. **Users** to understand the library architecture and capabilities
4. **Plugin authors** to integrate via entry points (future enhancement)

This phase creates the **developer experience** foundation for a thriving ecosystem.

---

## Goals & Scope

### Primary Goals

1. Document how to implement custom sources
2. Specify all planned future enhancements
3. Update main README with library usage examples
4. Create runnable example scripts
5. Design (but not implement) plugin system
6. Design (but not implement) configuration system

### Non-Goals

- Implementing any of the future enhancements
- Building the actual plugin system
- Creating production-ready examples (demos only)

---

## EXTENDING.md - Developer Guide

**File**: `EXTENDING.md` (project root)

This guide teaches developers how to extend the ingestion library with custom sources.

### Content Structure

```markdown
# Extending Game Asset Tracker Ingestion

This guide shows you how to add custom sources to the ingestion pipeline.

## Table of Contents

1. Understanding the Architecture
2. Implementing a Custom Source
3. Implementing a Custom Transformer
4. Registering Your Source
5. Testing Your Implementation
6. Example: Steam Workshop Source
7. Example: Sketchfab Source
8. Troubleshooting

---

## Understanding the Architecture

### Core Concepts

**Source**: Provides assets from a data source (filesystem, API, database, etc.)

**Transformer**: Converts source-specific data to standardized manifest format

**Pipeline**: Orchestrates source → transformation → output

**Registry**: Discovers and manages available sources

### Key Abstractions

#### SourceAsset Protocol

```python
from typing import Protocol

class SourceAsset(Protocol):
    """Protocol that all source assets must implement."""
    
    @property
    def uid(self) -> str:
        """Unique identifier for this asset."""
        ...
    
    @property
    def title(self) -> str:
        """Human-readable title."""
        ...
    
    @property
    def description(self) -> str:
        """Asset description."""
        ...
    
    @property
    def source_type(self) -> str:
        """Source type identifier (e.g., 'filesystem', 'fab')."""
        ...
```

#### AssetData Dataclass

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AssetData:
    """Container for raw asset data before transformation."""
    
    source_asset: SourceAsset
    metadata: dict[str, Any]
    files: list[dict[str, Any]]
    manifest: Optional[Any] = None
```

#### Source ABC

```python
from abc import ABC, abstractmethod
from typing import Iterator

class Source(ABC):
    """Base interface for all data sources."""
    
    @abstractmethod
    def list_assets(self) -> Iterator[SourceAsset]:
        """List all available assets."""
        ...
    
    @abstractmethod
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve specific asset by UID."""
        ...
    
    @abstractmethod
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get raw data for transformation."""
        ...
```

---

## Implementing a Custom Source

### Step 1: Define Your Asset Adapter

Create an adapter that implements the `SourceAsset` protocol:

```python
# my_source/asset_adapter.py

class MySourceAsset:
    """Adapter for MySource assets."""
    
    def __init__(self, raw_asset):
        self._asset = raw_asset
    
    @property
    def uid(self) -> str:
        return self._asset.id
    
    @property
    def title(self) -> str:
        return self._asset.name
    
    @property
    def description(self) -> str:
        return self._asset.desc or ""
    
    @property
    def source_type(self) -> str:
        return "my_source"
    
    @property
    def raw_asset(self):
        """Provide access to underlying asset for transformer."""
        return self._asset
```

### Step 2: Implement Source Interface

```python
# my_source/source.py

from typing import Iterator
from game_asset_tracker_ingestion.sources.base import Source, SourceAsset, AssetData

class MySource(Source):
    """Source implementation for MySource."""
    
    def __init__(self, api_key: str, base_url: str):
        """Initialize with authentication."""
        self.api_key = api_key
        self.base_url = base_url
        self._client = self._create_client()
    
    def _create_client(self):
        """Create API client (your implementation)."""
        # Your client initialization
        pass
    
    def list_assets(self) -> Iterator[SourceAsset]:
        """List all assets."""
        response = self._client.get_all_assets()
        
        for raw_asset in response:
            yield MySourceAsset(raw_asset)
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Get specific asset."""
        raw_asset = self._client.get_asset(uid)
        return MySourceAsset(raw_asset)
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get asset data for transformation."""
        if not isinstance(asset, MySourceAsset):
            raise ValueError(f"Expected MySourceAsset, got {type(asset)}")
        
        # Fetch additional data if needed
        metadata = {
            'raw_asset': asset.raw_asset,
            # Add any source-specific data
        }
        
        return AssetData(
            source_asset=asset,
            metadata=metadata,
            files=[],
            manifest=None,
        )
```

### Step 3: Implement Transformer

```python
# my_source/transformer.py

import uuid
from game_asset_tracker_ingestion.transformers.base import Transformer
from game_asset_tracker_ingestion.core.types import Manifest, Asset as ManifestAsset

class MySourceTransformer(Transformer):
    """Transform MySource assets to manifests."""
    
    def transform(
        self,
        asset_data: AssetData,
        **kwargs
    ) -> Manifest:
        """Transform asset data to manifest."""
        raw_asset = asset_data.metadata['raw_asset']
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        pack_name = kwargs.get('pack_name', raw_asset.name)
        
        # Create asset entries
        assets = self._create_assets(raw_asset)
        
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': pack_name,
            'root_path': '',
            'source': 'MySource',
            'license_link': kwargs.get('license_link', ''),
            'global_tags': kwargs.get('global_tags', []),
            'assets': assets,
        }
        
        return manifest
    
    def _create_assets(self, raw_asset) -> list[ManifestAsset]:
        """Create asset entries from raw asset."""
        # Your implementation
        pass
```

### Step 4: Register Your Source

```python
# my_source/__init__.py

from game_asset_tracker_ingestion.registry import SourceRegistry
from .source import MySource

def _create_my_source(api_key: str, base_url: str, **kwargs) -> MySource:
    """Factory function for creating MySource."""
    return MySource(api_key, base_url)

# Register with registry
SourceRegistry.register_factory('my_source', _create_my_source)

__all__ = ['MySource', 'MySourceTransformer']
```

### Step 5: Use Your Source

```python
from game_asset_tracker_ingestion import SourceRegistry

# Create pipeline using your source
pipeline = SourceRegistry.create_pipeline(
    'my_source',
    api_key='your-api-key',
    base_url='https://api.mysource.com'
)

# Generate manifests
for manifest in pipeline.generate_manifests():
    print(f"Generated: {manifest['pack_name']}")
```

---

## Testing Your Implementation

### Unit Tests

```python
# tests/test_my_source.py

import pytest
from unittest.mock import Mock
from my_source import MySource, MySourceTransformer, MySourceAsset

@pytest.fixture
def mock_client():
    """Mock API client."""
    client = Mock()
    client.get_all_assets.return_value = [
        Mock(id='1', name='Asset 1', desc='Description 1'),
        Mock(id='2', name='Asset 2', desc='Description 2'),
    ]
    return client

def test_list_assets(mock_client):
    """Test listing assets."""
    source = MySource(api_key='test', base_url='http://test')
    source._client = mock_client
    
    assets = list(source.list_assets())
    
    assert len(assets) == 2
    assert assets[0].uid == '1'
    assert assets[0].title == 'Asset 1'

def test_transformer():
    """Test transformation."""
    from game_asset_tracker_ingestion.sources.base import AssetData
    
    mock_asset = Mock(id='1', name='Test Asset')
    adapter = MySourceAsset(mock_asset)
    
    asset_data = AssetData(
        source_asset=adapter,
        metadata={'raw_asset': mock_asset},
        files=[],
        manifest=None,
    )
    
    transformer = MySourceTransformer()
    manifest = transformer.transform(asset_data)
    
    assert manifest['pack_name'] == 'Test Asset'
    assert manifest['source'] == 'MySource'
```

### Integration Tests

```python
def test_pipeline_integration(mock_client):
    """Test full pipeline."""
    from game_asset_tracker_ingestion import SourceRegistry
    
    # Register your source
    SourceRegistry.register_factory(
        'my_source',
        lambda **kw: MySource(api_key='test', base_url='http://test')
    )
    
    # Create pipeline
    pipeline = SourceRegistry.create_pipeline('my_source')
    
    # Generate manifests
    manifests = list(pipeline.generate_manifests())
    
    assert len(manifests) > 0
    assert all('pack_id' in m for m in manifests)
```

---

## Example: Steam Workshop Source

Complete implementation of a Steam Workshop source:

```python
# steam_workshop/source.py

import requests
from typing import Iterator
from game_asset_tracker_ingestion.sources.base import Source, AssetData

class SteamWorkshopAsset:
    """Adapter for Steam Workshop items."""
    
    def __init__(self, item_data: dict):
        self._data = item_data
    
    @property
    def uid(self) -> str:
        return str(self._data['publishedfileid'])
    
    @property
    def title(self) -> str:
        return self._data['title']
    
    @property
    def description(self) -> str:
        return self._data.get('description', '')
    
    @property
    def source_type(self) -> str:
        return 'steam_workshop'
    
    @property
    def raw_data(self) -> dict:
        return self._data


class SteamWorkshopSource(Source):
    """Source for Steam Workshop items."""
    
    BASE_URL = 'https://api.steampowered.com/IPublishedFileService'
    
    def __init__(self, api_key: str, app_id: int):
        self.api_key = api_key
        self.app_id = app_id
    
    def list_assets(self) -> Iterator[SteamWorkshopAsset]:
        """List subscribed items."""
        url = f"{self.BASE_URL}/GetUserFiles/v1/"
        params = {
            'key': self.api_key,
            'appid': self.app_id,
            'return_details': True,
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        for item in data['response']['publishedfiledetails']:
            yield SteamWorkshopAsset(item)
    
    def get_asset(self, uid: str) -> SteamWorkshopAsset:
        """Get specific workshop item."""
        url = f"{self.BASE_URL}/GetDetails/v1/"
        params = {
            'key': self.api_key,
            'publishedfileids[0]': uid,
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        item = data['response']['publishedfiledetails'][0]
        return SteamWorkshopAsset(item)
    
    def get_asset_data(self, asset, download=False) -> AssetData:
        """Get asset data."""
        return AssetData(
            source_asset=asset,
            metadata={'raw_data': asset.raw_data},
            files=[],
            manifest=None,
        )
```

**Usage:**

```python
from steam_workshop import SteamWorkshopSource
from game_asset_tracker_ingestion import SourceRegistry

# Register
SourceRegistry.register_factory(
    'steam_workshop',
    lambda api_key, app_id, **kw: SteamWorkshopSource(api_key, app_id)
)

# Use
pipeline = SourceRegistry.create_pipeline(
    'steam_workshop',
    api_key='your-steam-api-key',
    app_id=431960  # Wallpaper Engine example
)
```

---

## Troubleshooting

### Common Issues

**1. Source not registered**

```
ValueError: Unknown source: 'my_source'. Available sources: filesystem, fab
```

**Solution**: Ensure your `__init__.py` calls `SourceRegistry.register_factory()` and is imported.

**2. Protocol not satisfied**

```
TypeError: 'MyAsset' object does not implement SourceAsset protocol
```

**Solution**: Implement all required properties: `uid`, `title`, `description`, `source_type`.

**3. Import errors**

```
ImportError: cannot import name 'Source' from 'game_asset_tracker_ingestion.sources.base'
```

**Solution**: Check your import paths. Use absolute imports from the package.

### Debugging Tips

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Test components in isolation**:
   - Test adapter with mock data
   - Test source with mock client
   - Test transformer with sample AssetData
   - Then test full pipeline

3. **Validate manifests**:
   ```python
   from game_asset_tracker_ingestion.core.validator import validate_manifest
   
   manifest = transformer.transform(asset_data)
   validate_manifest(manifest)  # Will raise if invalid
   ```

---

## Best Practices

1. **Follow existing patterns**: Look at `platforms/filesystem/` and `platforms/fab/` for reference
2. **Handle errors gracefully**: Don't let one failed asset break the entire pipeline
3. **Add progress feedback**: Use `sys.stderr` for progress messages
4. **Document your code**: Include docstrings and type hints
5. **Write tests**: Unit tests for each component, integration test for pipeline
6. **Validate output**: Always validate manifests against the schema

---

## Resources

- **Base abstractions**: `src/game_asset_tracker_ingestion/sources/base.py`
- **Filesystem reference**: `src/game_asset_tracker_ingestion/platforms/filesystem/`
- **Fab reference**: `src/game_asset_tracker_ingestion/platforms/fab/` (Phase 2)
- **JSON Schema**: `../schemas/manifest.schema.json`
- **TODO.md**: Planned future enhancements
```

---

## TODO.md - Future Enhancements

**File**: `TODO.md` (project root)

This document specifies all planned future enhancements with enough detail for future implementation.

### Content Structure

```markdown
# TODO: Future Enhancements

This document specifies planned features that are not yet implemented.
Each item includes design specifications to guide future implementation.

---

## High Priority

### 1. Advanced Filtering (Option C)

**Current state**: Pipeline generates manifests for all assets

**Goal**: Allow users to filter which assets are processed

**Design**:

```python
# Example usage
def my_filter(asset: SourceAsset) -> bool:
    """Only process assets matching criteria."""
    return asset.source_type == 'fab' and 'entitled' in asset.metadata

pipeline = SourceRegistry.create_pipeline('fab', client=client)
manifests = pipeline.generate_manifests(
    filter_fn=my_filter,
    limit=10  # Optional: limit number of results
)
```

**Implementation notes**:

1. Add `filter_fn` parameter to `IngestionPipeline.generate_manifests()`
2. Apply filter to `source.list_assets()` results
3. Support both synchronous and async filter functions
4. Add `limit` parameter for pagination

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Estimated effort**: 1 day

---

### 2. Per-Source Download Strategy Override

**Current state**: Global `download_strategy` applies to all sources

**Goal**: Allow different strategies for different sources in mixed pipelines

**Design**:

```python
# Example: Download manifests for Fab, metadata-only for UAS
pipeline = MultiSourcePipeline([
    ('fab', {'client': fab_client}),
    ('uas', {'client': uas_client}),
])

manifests = pipeline.generate_manifests(
    download_overrides={
        'fab': 'manifests_only',
        'uas': 'metadata_only',
    }
)
```

**Implementation notes**:

1. Create `MultiSourcePipeline` class that wraps multiple sources
2. Accept `download_overrides` dict in `generate_manifests()`
3. Pass appropriate strategy to each source's `get_asset_data()`

**Code location**: New file `src/game_asset_tracker_ingestion/multi_pipeline.py`

**Estimated effort**: 2 days

---

### 3. Parallel Processing for Large Libraries

**Current state**: Sequential processing of assets

**Goal**: Speed up manifest generation with parallel processing

**Design**:

```python
pipeline = SourceRegistry.create_pipeline('fab', client=client)

# Enable parallel processing
manifests = pipeline.generate_manifests(
    parallel=True,
    max_workers=4
)
```

**Implementation notes**:

1. Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound operations
2. Add `parallel` and `max_workers` parameters
3. Maintain order of results (use `as_completed` with tracking)
4. Handle exceptions gracefully (don't fail entire batch)

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Estimated effort**: 3 days

**Considerations**:
- Thread safety of Source implementations
- Rate limiting for API sources
- Memory usage with large worker pools

---

## Medium Priority

### 4. Plugin System via Entry Points

**Current state**: Sources must be in `platforms/` directory

**Goal**: Allow third-party packages to register sources

**Design**:

**In third-party package**:

```toml
# pyproject.toml of my-steam-adapter package
[project.entry-points."game_asset_tracker_ingestion.sources"]
steam_workshop = "my_steam_adapter:SteamWorkshopSource"
```

**In ingestion library**:

```python
# Automatic discovery
import importlib.metadata

for ep in importlib.metadata.entry_points(
    group='game_asset_tracker_ingestion.sources'
):
    source_factory = ep.load()
    SourceRegistry.register_factory(ep.name, source_factory)
```

**Implementation notes**:

1. Add entry point discovery to `SourceRegistry.discover_platforms()`
2. Support both built-in and plugin sources
3. Handle plugin loading errors gracefully
4. Add `--list-sources` CLI command to show available sources

**Code location**: `src/game_asset_tracker_ingestion/registry.py`

**Estimated effort**: 2 days

---

### 5. Configuration File Support

**Current state**: All configuration via code or CLI arguments

**Goal**: Support project-local and global configuration files

**Design**:

**Project-local config** (`.game-asset-tracker.yaml`):

```yaml
sources:
  fab:
    enabled: true
    download_strategy: manifests_only
    auth:
      type: cookies
      cookies_file: ~/.fab/cookies.json
  
  uas:
    enabled: false

output:
  directory: ./manifests
  format: json
  validate: true

filters:
  - source: fab
    condition: entitled == true
```

**Global config** (`~/.config/game-asset-tracker/config.yaml`):

Same format, project-local overrides global.

**Implementation notes**:

1. Use `PyYAML` or `tomli` for parsing
2. Load global config first, then project-local
3. Deep merge configurations
4. Add `--config` CLI flag to specify custom config file
5. Validate config against schema

**Code location**: New file `src/game_asset_tracker_ingestion/config.py`

**Estimated effort**: 3 days

---

### 6. Caching Layer

**Current state**: Re-fetch data on every run

**Goal**: Cache API responses to speed up repeated runs

**Design**:

```python
from game_asset_tracker_ingestion import SourceRegistry
from game_asset_tracker_ingestion.cache import FileCache

cache = FileCache(cache_dir='~/.cache/game-asset-tracker', ttl=3600)

pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    cache=cache
)
```

**Implementation notes**:

1. Create `Cache` ABC with `get()`, `set()`, `invalidate()` methods
2. Implement `FileCache` (pickle-based) and `MemoryCache`
3. Add cache key generation (hash of source + asset UID)
4. Add TTL (time-to-live) support
5. Add `--no-cache` CLI flag

**Code location**: New file `src/game_asset_tracker_ingestion/cache.py`

**Estimated effort**: 3 days

---

## Low Priority

### 7. Robust Marketplace Metadata Storage

**Current state**: Marketplace-specific metadata stored as strings in flexible `metadata` dict

**Problem**: Hard to query, no type safety, schema limitations

**Goal**: Structured storage for marketplace-specific fields

**Option A: Schema Extensions**

Extend JSON schema with marketplace-specific fields:

```json
{
  "pack_id": "...",
  "pack_name": "...",
  "marketplace_metadata": {
    "fab": {
      "listing_uid": "...",
      "seller": {...},
      "status": "ACTIVE"
    }
  }
}
```

**Option B: Sidecar Files**

Store complex metadata separately:

```
output/
├── abc123.json          # Standard manifest
└── abc123.meta.json     # Marketplace metadata
```

**Option C: Separate Tables (Obsidian plugin)**

Let the Obsidian plugin create marketplace-specific SQLite tables:

```sql
CREATE TABLE fab_metadata (
    pack_id TEXT PRIMARY KEY,
    listing_uid TEXT,
    seller_name TEXT,
    status TEXT,
    FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
);
```

**Recommendation**: Option C - Handle in Obsidian plugin, not ingestion library

**Estimated effort**: N/A (deferred to Obsidian plugin)

---

### 8. Resume Interrupted Downloads

**Current state**: Must restart if download interrupted

**Goal**: Resume from last successful download

**Design**:

```python
pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    resume=True,
    state_file='.ingestion-state.json'
)
```

State file stores:

```json
{
  "last_processed_uid": "asset-123",
  "timestamp": "2024-01-15T10:30:00Z",
  "completed": ["asset-1", "asset-2", ...],
  "failed": ["asset-99": "error message"]
}
```

**Implementation notes**:

1. Save state after each successful asset
2. Skip already-processed assets on resume
3. Retry failed assets with exponential backoff
4. Add `--resume` CLI flag

**Code location**: New file `src/game_asset_tracker_ingestion/state.py`

**Estimated effort**: 2 days

---

### 9. Progress Bar and Statistics

**Current state**: Minimal progress feedback

**Goal**: Rich progress display with statistics

**Design**:

```python
from game_asset_tracker_ingestion import SourceRegistry
from rich.progress import Progress

with Progress() as progress:
    pipeline = SourceRegistry.create_pipeline('fab', client=client)
    
    task = progress.add_task("Generating manifests", total=None)
    
    for manifest in pipeline.generate_manifests():
        progress.update(task, advance=1)
        # Process manifest

# Show statistics
print(f"Processed: {pipeline.stats.processed}")
print(f"Failed: {pipeline.stats.failed}")
print(f"Total size: {pipeline.stats.total_size_gb:.2f} GB")
```

**Implementation notes**:

1. Add optional `rich` dependency for progress bars
2. Add `Statistics` dataclass to track metrics
3. Emit progress events from pipeline
4. Make progress display optional (for scripting)

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Estimated effort**: 2 days

---

### 10. Incremental Updates

**Current state**: Full re-scan every time

**Goal**: Only process new/changed assets

**Design**:

```python
pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    incremental=True,
    state_file='.last-scan.json'
)

# Only processes assets added/modified since last scan
manifests = pipeline.generate_manifests()
```

**Implementation notes**:

1. Store asset UIDs and timestamps from last run
2. Query source for assets modified since last timestamp
3. Skip unchanged assets
4. Handle deleted assets (optional: generate deletion manifests)

**Code location**: Extend `state.py` from TODO item #8

**Estimated effort**: 3 days

---

## UAS Integration Specifics

### UAS Source Implementation

**Expected differences from Fab**:

1. **Authentication**: UAS may use different auth mechanism
2. **Asset structure**: Different fields (e.g., `asset_version` vs `build_version`)
3. **Manifest format**: UAS may have different manifest structure
4. **License handling**: Different license URL format

**Template** (`platforms/uas/source.py`):

```python
from uas_api_client import UASClient
from game_asset_tracker_ingestion.sources.base import Source

class UASSource(Source):
    def __init__(self, client: UASClient):
        self.client = client
    
    def list_assets(self):
        # UAS-specific implementation
        pass
    
    # ... implement other methods
```

**Estimated effort**: 2 days (following Fab pattern)

---

## Implementation Priority

**Recommended order**:

1. Advanced Filtering (1 day) - High user value
2. Plugin System (2 days) - Enables ecosystem
3. Configuration Files (3 days) - Better UX
4. UAS Integration (2 days) - Validates multi-marketplace
5. Parallel Processing (3 days) - Performance boost
6. Caching (3 days) - Performance boost
7. Progress/Statistics (2 days) - Better UX
8. Resume/Incremental (5 days combined) - Nice to have

**Total estimated effort**: ~23 days for all items
```

---

## README.md Updates

Update the main README with library usage examples and architecture overview.

### New Sections to Add

#### Library Usage

```markdown
## Library Usage

The ingestion library can be used programmatically or via CLI.

### Basic Filesystem Scan

```python
from pathlib import Path
from game_asset_tracker_ingestion import SourceRegistry

# Create pipeline
pipeline = SourceRegistry.create_pipeline(
    'filesystem',
    path=Path('/path/to/assets')
)

# Generate manifests
for manifest in pipeline.generate_manifests():
    print(f"Pack: {manifest['pack_name']}")
    print(f"Files: {len(manifest['assets'])}")
```

### Fab Marketplace (requires `uv sync --extra fab`)

```python
from fab_api_client import FabClient, CookieAuthProvider
from game_asset_tracker_ingestion import SourceRegistry

# Setup Fab client
auth = CookieAuthProvider(cookies={...}, endpoints=...)
client = FabClient(auth=auth)

# Create pipeline
pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    download_strategy='metadata_only'  # or 'manifests_only'
)

# Generate manifests
for manifest in pipeline.generate_manifests():
    # Process manifest
    pass
```

### Custom Source

See [EXTENDING.md](EXTENDING.md) for details on implementing custom sources.

---

## Installation

```bash
# Filesystem only
uv sync

# With Fab marketplace support
uv sync --extra fab

# With all marketplace support
uv sync --extra all
```

---

## Architecture

The library follows a modular architecture:

- **Sources**: Abstract data retrieval from various origins
- **Transformers**: Convert source data to standardized manifests
- **Pipeline**: Orchestrates data flow
- **Registry**: Manages available sources

See [EXTENDING.md](EXTENDING.md) for detailed architecture documentation.
```

---

## Example Scripts

Create runnable example scripts in `examples/` directory.

### examples/filesystem_basic.py

```python
"""Basic filesystem scanning example."""

import json
from pathlib import Path
from game_asset_tracker_ingestion import SourceRegistry

def main():
    # Scan a directory
    asset_dir = Path.home() / "Documents" / "GameAssets"
    
    if not asset_dir.exists():
        print(f"Directory not found: {asset_dir}")
        return
    
    # Create pipeline
    pipeline = SourceRegistry.create_pipeline('filesystem', path=asset_dir)
    
    # Generate manifest
    manifest = next(pipeline.generate_manifests())
    
    # Display summary
    print(f"Pack: {manifest['pack_name']}")
    print(f"Files: {len(manifest['assets'])}")
    print(f"Total size: {sum(a['size_bytes'] for a in manifest['assets']) / 1024**2:.1f} MB")
    
    # Save to file
    output_file = Path("manifest.json")
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to {output_file}")

if __name__ == '__main__':
    main()
```

### examples/fab_metadata_only.py

```python
"""Fab marketplace - metadata only (no downloads)."""

import json
from pathlib import Path
from fab_api_client import FabClient, CookieAuthProvider
from game_asset_tracker_ingestion import SourceRegistry

def main():
    # Setup authentication (replace with your cookies)
    cookies = {
        'EPIC_SSO': 'your-sso-cookie',
        'EPIC_BEARER_TOKEN': 'your-bearer-token',
    }
    
    endpoints = {
        'library': 'https://fab.com/api/v1/library',
    }
    
    auth = CookieAuthProvider(cookies=cookies, endpoints=endpoints)
    client = FabClient(auth=auth)
    
    # Create pipeline
    pipeline = SourceRegistry.create_pipeline(
        'fab',
        client=client,
        download_strategy='metadata_only'
    )
    
    # Generate manifests
    output_dir = Path("manifests/fab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for manifest in pipeline.generate_manifests():
        # Save each manifest
        output_file = output_dir / f"{manifest['pack_id']}.json"
        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ {manifest['pack_name']}")
        count += 1
    
    print(f"\nGenerated {count} manifests in {output_dir}")

if __name__ == '__main__':
    main()
```

### examples/custom_source.py

```python
"""Template for implementing a custom source."""

from typing import Iterator
from game_asset_tracker_ingestion.sources.base import Source, SourceAsset, AssetData
from game_asset_tracker_ingestion.transformers.base import Transformer
from game_asset_tracker_ingestion import SourceRegistry

# Step 1: Define asset adapter
class MyAsset:
    def __init__(self, data: dict):
        self._data = data
    
    @property
    def uid(self) -> str:
        return self._data['id']
    
    @property
    def title(self) -> str:
        return self._data['name']
    
    @property
    def description(self) -> str:
        return self._data.get('description', '')
    
    @property
    def source_type(self) -> str:
        return 'my_source'

# Step 2: Implement source
class MySource(Source):
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    def list_assets(self) -> Iterator[SourceAsset]:
        # Fetch assets from your source
        assets = [
            {'id': '1', 'name': 'Asset 1', 'description': 'First asset'},
            {'id': '2', 'name': 'Asset 2', 'description': 'Second asset'},
        ]
        for data in assets:
            yield MyAsset(data)
    
    def get_asset(self, uid: str) -> SourceAsset:
        # Fetch specific asset
        data = {'id': uid, 'name': f'Asset {uid}'}
        return MyAsset(data)
    
    def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
        return AssetData(
            source_asset=asset,
            metadata={},
            files=[],
            manifest=None,
        )

# Step 3: Register
def create_my_source(api_url: str, **kwargs):
    return MySource(api_url)

SourceRegistry.register_factory('my_source', create_my_source)

# Step 4: Use
def main():
    pipeline = SourceRegistry.create_pipeline('my_source', api_url='https://api.example.com')
    
    for manifest in pipeline.generate_manifests():
        print(f"Generated: {manifest['pack_name']}")

if __name__ == '__main__':
    main()
```

---

## Summary

Phase 4 creates comprehensive documentation for:

1. **EXTENDING.md** - How to implement custom sources
2. **TODO.md** - Detailed specs for future features
3. **README updates** - Library usage examples
4. **Example scripts** - Runnable code demonstrating usage

This documentation enables the ecosystem to grow beyond the core team.

**Estimated effort for Phase 4**: 3-5 days

**Key deliverables**:
- ✅ Developer extension guide
- ✅ Future enhancement specifications
- ✅ Updated README
- ✅ Example scripts

**Next**: Phase 5 will document UAS integration as a template for other marketplaces.
