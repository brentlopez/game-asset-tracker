# Extending Game Asset Tracker Ingestion

This guide shows you how to add custom sources to the ingestion pipeline.

## Table of Contents

1. [Understanding the Architecture](#understanding-the-architecture)
2. [Implementing a Custom Source](#implementing-a-custom-source)
3. [Testing Your Implementation](#testing-your-implementation)
4. [Example: Steam Workshop Source](#example-steam-workshop-source)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)
7. [Resources](#resources)

---

## Understanding the Architecture

### Core Concepts

**Source**: Provides assets from a data source (filesystem, API, database, etc.)

**Transformer**: Converts source-specific data to standardized manifest format

**Pipeline**: Orchestrates source → transformation → output

**Registry**: Discovers and manages available sources

### Key Abstractions

#### SourceAsset Protocol

All assets must implement this protocol:

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
```

The protocol is minimal to support diverse source types. Only `uid` and `title` are required.

#### AssetData Dataclass

Container for raw data retrieved from a source:

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class AssetData:
    """Container for raw asset data before transformation."""
    
    asset: SourceAsset
    files: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    parsed_manifest: Any = None  # Platform-specific manifest type
```

#### Source ABC

All sources must implement this abstract base class:

```python
from abc import ABC, abstractmethod

class Source(ABC):
    """Base interface for all data sources."""
    
    @abstractmethod
    def list_assets(self) -> list[SourceAsset]:
        """List all available assets."""
        ...
    
    @abstractmethod
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve specific asset by UID."""
        ...
    
    @abstractmethod
    def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
        """Get raw data for transformation."""
        ...
    
    @abstractmethod
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source."""
        ...
```

#### Transformer ABC

Transformers convert source-specific data to manifests:

```python
from abc import ABC, abstractmethod

class Transformer(ABC):
    """Abstract base class for data transformers."""
    
    @abstractmethod
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: str | None = None,
        **kwargs
    ) -> Manifest:
        """Transform source data into a manifest."""
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
    def raw_asset(self):
        """Provide access to underlying asset for transformer."""
        return self._asset
```

### Step 2: Implement Source Interface

```python
# my_source/source.py

from game_asset_tracker_ingestion.sources.base import Source, SourceAsset, AssetData
from game_asset_tracker_ingestion.transformers.base import Transformer

class MySource(Source):
    """Source implementation for MySource."""
    
    def __init__(self, api_key: str, base_url: str):
        """Initialize with authentication."""
        self.api_key = api_key
        self.base_url = base_url
        self._client = self._create_client()
        
        # Create transformer for this source
        from .transformer import MySourceTransformer
        self._transformer = MySourceTransformer()
    
    def _create_client(self):
        """Create API client (your implementation)."""
        # Your client initialization
        pass
    
    def list_assets(self) -> list[SourceAsset]:
        """List all assets."""
        response = self._client.get_all_assets()
        
        return [MySourceAsset(raw_asset) for raw_asset in response]
    
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
            asset=asset,
            metadata=metadata,
            files=[],
            parsed_manifest=None,
        )
    
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source."""
        return self._transformer
```

### Step 3: Implement Transformer

```python
# my_source/transformer.py

import uuid
from game_asset_tracker_ingestion.transformers.base import Transformer
from game_asset_tracker_ingestion.sources.base import SourceAsset, AssetData
from game_asset_tracker_ingestion.core.types import Manifest, Asset as ManifestAsset

class MySourceTransformer(Transformer):
    """Transform MySource assets to manifests."""
    
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: str | None = None,
        **kwargs
    ) -> Manifest:
        """Transform asset data to manifest."""
        raw_asset = data.metadata['raw_asset']
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        pack_name = pack_name or asset.title
        
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
        # Your implementation - return list of Asset dicts
        return []
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
        Mock(id='1', name='Asset 1'),
        Mock(id='2', name='Asset 2'),
    ]
    return client

def test_list_assets(mock_client):
    """Test listing assets."""
    source = MySource(api_key='test', base_url='http://test')
    source._client = mock_client
    
    assets = source.list_assets()
    
    assert len(assets) == 2
    assert assets[0].uid == '1'
    assert assets[0].title == 'Asset 1'

def test_transformer():
    """Test transformation."""
    from game_asset_tracker_ingestion.sources.base import AssetData
    
    mock_asset = Mock(id='1', name='Test Asset')
    adapter = MySourceAsset(mock_asset)
    
    asset_data = AssetData(
        asset=adapter,
        metadata={'raw_asset': mock_asset},
        files=[],
        parsed_manifest=None,
    )
    
    transformer = MySourceTransformer()
    manifest = transformer.transform(adapter, asset_data)
    
    assert manifest['pack_name'] == 'Test Asset'
    assert manifest['source'] == 'MySource'
```

### Integration Tests

```python
def test_pipeline_integration():
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
from game_asset_tracker_ingestion.sources.base import Source, SourceAsset, AssetData
from game_asset_tracker_ingestion.transformers.base import Transformer

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
    def raw_data(self) -> dict:
        return self._data


class SteamWorkshopSource(Source):
    """Source for Steam Workshop items."""
    
    BASE_URL = 'https://api.steampowered.com/IPublishedFileService'
    
    def __init__(self, api_key: str, app_id: int):
        self.api_key = api_key
        self.app_id = app_id
        
        from .transformer import SteamWorkshopTransformer
        self._transformer = SteamWorkshopTransformer()
    
    def list_assets(self) -> list[SourceAsset]:
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
        return [
            SteamWorkshopAsset(item)
            for item in data['response']['publishedfiledetails']
        ]
    
    def get_asset(self, uid: str) -> SourceAsset:
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
    
    def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
        """Get asset data."""
        return AssetData(
            asset=asset,
            metadata={'raw_data': asset.raw_data},
            files=[],
            parsed_manifest=None,
        )
    
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source."""
        return self._transformer
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

**Solution**: Implement all required properties: `uid` and `title`.

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
   
   manifest = transformer.transform(asset, data)
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

### Code References
- **Base abstractions**: `src/game_asset_tracker_ingestion/sources/base.py`
- **Transformer base**: `src/game_asset_tracker_ingestion/transformers/base.py`
- **Pipeline**: `src/game_asset_tracker_ingestion/pipeline.py`
- **Registry**: `src/game_asset_tracker_ingestion/registry.py`
- **Filesystem reference**: `src/game_asset_tracker_ingestion/platforms/filesystem/`
- **Fab reference**: `src/game_asset_tracker_ingestion/platforms/fab/`

### Related Projects
- **[asset-marketplace-client-core](https://github.com/brentlopez/asset-marketplace-client-core)**: Architecture patterns for marketplace adapters
- **[fab-api-client](https://github.com/brentlopez/fab-api-client)**: Fab marketplace client library
- **[uas-api-client](https://github.com/brentlopez/uas-api-client)**: Unity Asset Store client library

### Schema & Documentation
- **JSON Schema**: `../schemas/manifest.schema.json`
- **TODO.md**: Planned future enhancements
- **README.md**: User documentation and CLI usage
