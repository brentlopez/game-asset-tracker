# Phase 2: Fab Marketplace Integration - Comprehensive Implementation Guide

**Status**: Documentation for future implementation  
**Estimated Effort**: 2-3 days  
**Prerequisites**: Phase 1 complete (modular architecture in place)

## Table of Contents

1. [Overview](#overview)
2. [Context & Rationale](#context--rationale)
3. [Prerequisites & Dependencies](#prerequisites--dependencies)
4. [Architecture Overview](#architecture-overview)
5. [Implementation Steps](#implementation-steps)
6. [Complete Code Implementations](#complete-code-implementations)
7. [Testing Strategy](#testing-strategy)
8. [Integration & Validation](#integration--validation)
9. [Example Usage](#example-usage)
10. [Edge Cases & Gotchas](#edge-cases--gotchas)
11. [Future Enhancements](#future-enhancements)

---

## Overview

Phase 2 adds support for ingesting asset data from the Fab marketplace (Epic Games) using the `fab-api-client` library. This phase focuses on **metadata-only transformation** - we extract asset information without downloading actual game files or manifests.

### Goals

- Enable ingestion from Fab marketplace alongside existing filesystem source
- Demonstrate the extensibility of the modular architecture
- Create a template for future marketplace integrations (UAS, Steam Workshop, etc.)
- Maintain the same manifest output format for both filesystem and marketplace sources

### Non-Goals (Deferred to Phase 3)

- Downloading and parsing Fab manifests
- Processing individual asset files from manifests
- Calculating accurate file sizes

---

## Context & Rationale

### Why Metadata-Only First?

We split marketplace integration into two phases (metadata-only, then download strategy) for several reasons:

1. **Incremental complexity**: Marketplace metadata transformation is complex enough without also handling downloads
2. **Authentication scope**: Users may want to catalog their library without downloading gigabytes of data
3. **Testing simplicity**: Metadata-only mode is easier to test without mock file systems
4. **Use case validation**: Many users just want to know *what* they own, not download everything

### Design Decisions

#### One Manifest Per Asset (Option A)

Each Fab `Asset` (entitled item in user's library) becomes one `Manifest` (Asset Pack):

**Rationale**:
- Fab assets are already conceptual "packs" (a 3D model collection, a material library, etc.)
- Users browse and purchase at the asset level, not individual files
- Obsidian notes naturally map to asset-level organization
- Simplifies filtering and batch operations

**Trade-off**: Large assets with thousands of files will have large manifests. This is acceptable because:
- Manifests are JSON (compressible)
- SQLite handles large row counts efficiently
- Users can still filter at import time

#### Flexible Metadata Storage

Fab has marketplace-specific fields that don't map cleanly to the core schema:
- `status` (ACTIVE, EXPIRED, etc.)
- `capabilities` (permissions, features)
- `granted_licenses` (license agreements)
- Listing details (seller, price, ratings)

**Phase 2 approach**: Store as string key-value pairs in the `metadata` object.

**TODO for future**: This is a stopgap. See Phase 4 documentation for robust solutions:
- Schema extensions with marketplace-specific fields
- Sidecar JSON files for complex structured data
- Separate SQLite tables for queryable marketplace metadata

#### Platform Discovery via Registry

Platforms self-register when imported. This keeps the core pipeline platform-agnostic:

```python
# platforms/fab/__init__.py auto-registers on import
SourceRegistry.register_factory('fab', _create_fab_source)
```

**Rationale**:
- No central "list of all platforms" to maintain
- New platforms can be added without modifying core code
- Graceful degradation when optional dependencies missing
- Supports future plugin system

---

## Prerequisites & Dependencies

### Before Starting

Ensure Phase 1 is complete:
- ✅ Base abstractions exist (`sources/base.py`, `transformers/base.py`)
- ✅ `IngestionPipeline` is platform-agnostic
- ✅ `SourceRegistry` with factory pattern implemented
- ✅ `platforms/filesystem/` working as reference implementation
- ✅ All Phase 1 tests passing

### External Dependencies

#### fab-api-client

**Version**: >= 2.1.0  
**Location**: `../../fab-api-client/`  
**Documentation**: See `../../fab-api-client/README.md`

Key types and classes used:

```python
from fab_api_client import (
    FabClient,           # Main client class
    CookieAuthProvider,  # Authentication via browser cookies (provided by fab-egl-adapter)
    Asset,               # Fab asset with entitlements
    Library,             # User's library collection
)
```

**Note**: In practice, users will obtain `CookieAuthProvider` from `fab-egl-adapter` rather than constructing it manually. See [Authentication Architecture](#authentication-architecture) section below.

#### asset-marketplace-core

**Version**: >= 1.0.0 (pulled in by fab-api-client)  
**Location**: `../../asset-marketplace-client-core/`

Base types extended by `fab-api-client`:

```python
from asset_marketplace_core import (
    MarketplaceClient,  # ABC that FabClient implements
    BaseAsset,          # Minimal asset interface
    BaseCollection,     # Collection with filtering
)
```

### Installation

Update `pyproject.toml` to add optional dependencies:

```toml
[project.optional-dependencies]
fab = ["fab-api-client>=2.1.0"]
uas = ["uas-api-client>=2.1.0"]
all = ["fab-api-client>=2.1.0", "uas-api-client>=2.1.0"]
```

Install with:
```bash
uv sync --extra fab
```

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     IngestionPipeline                        │
│                  (platform-agnostic)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ uses
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Source ABC                               │
│              list_assets() / get_asset_data()                │
└─────────────┬──────────────────────┬────────────────────────┘
              │                      │
              │                      │
    ┌─────────▼────────┐   ┌────────▼─────────┐
    │ FilesystemSource │   │    FabSource     │
    │  (Phase 1)       │   │   (Phase 2)      │
    └──────────────────┘   └──────┬───────────┘
                                   │
                                   │ delegates to
                                   ▼
                         ┌──────────────────────┐
                         │     FabClient        │
                         │  (fab-api-client)    │
                         └──────────┬───────────┘
                                    │
                                    │ uses
                                    ▼
                         ┌──────────────────────┐
                         │   AuthProvider       │
                         │ (CookieAuthProvider) │
                         └──────────┬───────────┘
                                    │
                                    │ provided by
                                    ▼
                         ┌──────────────────────┐
                         │  FabEGLAdapter       │
                         │ (fab-egl-adapter)    │
                         │ Extracts cookies     │
                         │ from EGL install     │
                         └──────────────────────┘
```

### Authentication Architecture

The system uses a **three-tier authentication model** to separate concerns:

**Tier 3: Adapter Libraries** (Extract authentication from installed software)
- `fab-egl-adapter`: Extracts cookies/tokens from Epic Games Launcher installation
- `uas-adapter`: Extracts tokens from Unity Editor installation
- Handles platform-specific credential extraction (Windows Registry, macOS plist files, etc.)
- **Output**: Pre-configured `AuthProvider` instance

**Tier 2: API Client Libraries** (Use authentication to make API calls)
- `fab-api-client`: Uses `CookieAuthProvider` to authenticate Fab marketplace requests
- `uas-api-client`: Uses `TokenAuthProvider` to authenticate Unity Asset Store requests
- Handle request signing, token refresh, rate limiting, error handling
- **Output**: Authenticated `FabClient` or `UASClient` instance

**Tier 1: Ingestion Library** (Consumes pre-authenticated clients)
- `game-asset-tracker-ingestion`: Accepts pre-configured clients from Tier 2
- Platform-agnostic - doesn't know about authentication mechanisms
- Focuses solely on data transformation and manifest generation
- **Input**: Already-authenticated client instances

**Why this separation matters:**

1. **Separation of Concerns**: Ingestion library doesn't need to understand platform-specific auth
2. **Testability**: Each tier can be mocked/tested independently
3. **Reusability**: Adapter libraries can be used by other tools (not just ingestion)
4. **Security**: Credential extraction logic is isolated in adapters
5. **Flexibility**: Users can provide clients authenticated by any method

**Example authentication flow:**

```python
# Tier 3: Adapter extracts credentials from EGL
from fab_egl_adapter import FabEGLAdapter

adapter = FabEGLAdapter()
auth_provider = adapter.get_auth_provider()  # CookieAuthProvider with cookies

# Tier 2: Client uses auth to make API calls
from fab_api_client import FabClient

client = FabClient(auth=auth_provider)
library = client.get_library()  # Authenticated request

# Tier 1: Ingestion uses client to generate manifests
from game_asset_tracker_ingestion import SourceRegistry

pipeline = SourceRegistry.create_pipeline('fab', client=client)
for manifest in pipeline.generate_manifests():
    # Process manifest...
    pass
```

**Note**: The ingestion library **only sees the client** - it never touches adapters or auth providers directly. This keeps the ingestion code clean and platform-agnostic.

### Data Flow

1. **User creates pipeline**: `SourceRegistry.create_pipeline('fab', client=fab_client)`
2. **Registry creates source**: Factory function wraps `FabClient` in `FabSource`
3. **Pipeline queries source**: `source.list_assets()` → calls `client.get_library()`
4. **Source returns assets**: List of `FabAsset` objects wrapped as `SourceAsset`
5. **Pipeline transforms**: `FabTransformer.transform_asset()` converts to `Manifest`
6. **Output**: Standard JSON manifest conforming to schema

### File Structure

New files to create:

```
platforms/fab/
├── __init__.py          # Auto-registration and gated imports
├── source.py            # FabSource implementation
└── transformer.py       # FabTransformer implementation
```

---

## Implementation Steps

### Step 1: Update Dependencies

**File**: `pyproject.toml`

Add optional dependencies section:

```toml
[project.optional-dependencies]
fab = ["fab-api-client>=2.1.0"]
uas = ["uas-api-client>=2.1.0"]
all = [
    "fab-api-client>=2.1.0",
    "uas-api-client>=2.1.0",
]
```

**Validation**: Run `uv sync --extra fab` and verify installation succeeds.

---

### Step 2: Create Platform Directory

```bash
mkdir -p src/game_asset_tracker_ingestion/platforms/fab
```

---

### Step 3: Implement FabSource

**File**: `platforms/fab/source.py`

See [Complete Code Implementations](#complete-code-implementations) section for full implementation.

**Key design points**:

1. **Constructor**: Takes `FabClient` instance (user handles authentication)
2. **list_assets()**: Wraps Fab library iteration
3. **Asset wrapping**: Creates adapter objects implementing `SourceAsset` protocol
4. **Error handling**: Propagates client errors with context

---

### Step 4: Implement FabTransformer

**File**: `platforms/fab/transformer.py`

See [Complete Code Implementations](#complete-code-implementations) section for full implementation.

**Key design points**:

1. **Metadata extraction**: Maps Fab fields to manifest fields
2. **Placeholder asset**: Single dummy asset entry (no files in Phase 2)
3. **Marketplace metadata**: Stores Fab-specific data as strings in `metadata` object
4. **UUID generation**: Creates new pack_id for each manifest
5. **TODO markers**: Comments indicating Phase 3 enhancements

---

### Step 5: Create Auto-Registration Module

**File**: `platforms/fab/__init__.py`

See [Complete Code Implementations](#complete-code-implementations) section for full implementation.

**Key design points**:

1. **Gated import**: Try to import `fab-api-client`, set flag if unavailable
2. **Factory function**: Accepts `FabClient` and kwargs, returns `FabSource`
3. **Auto-registration**: Calls `SourceRegistry.register_factory()` on import
4. **Graceful degradation**: Module loads even if fab-api-client missing

---

### Step 6: Verify Registry Discovery

The registry's `discover_platforms()` method (from Phase 1) should automatically find and import the new `platforms/fab/` module.

**Verification**:

```python
from game_asset_tracker_ingestion import SourceRegistry

# Should include 'fab' if fab-api-client installed
print(SourceRegistry.list_sources())
# Expected: ['filesystem', 'fab']
```

---

## Complete Code Implementations

### platforms/fab/source.py

```python
"""Fab marketplace source implementation.

This module provides a Source adapter for the Fab marketplace (Epic Games)
using the fab-api-client library.
"""

from pathlib import Path
from typing import Iterator, Optional
import sys

from fab_api_client import FabClient, Asset as FabAsset, Library
from asset_marketplace_core import BaseAsset

from ...sources.base import Source, SourceAsset, AssetData


class FabAssetAdapter:
    """Adapter that makes FabAsset compatible with SourceAsset protocol.
    
    This wraps a fab_api_client.Asset and provides the interface expected
    by the pipeline.
    """
    
    def __init__(self, fab_asset: FabAsset):
        self._asset = fab_asset
    
    @property
    def uid(self) -> str:
        """Unique identifier for this asset."""
        return self._asset.uid
    
    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._asset.title
    
    @property
    def description(self) -> str:
        """Asset description."""
        return self._asset.description or ""
    
    @property
    def source_type(self) -> str:
        """Source type identifier."""
        return "fab"
    
    @property
    def raw_asset(self) -> FabAsset:
        """Access to underlying Fab asset for transformation."""
        return self._asset


class FabSource(Source):
    """Source implementation for Fab marketplace.
    
    This source adapter wraps a FabClient and provides asset listing
    and retrieval functionality conforming to the Source interface.
    
    Phase 2: Metadata-only mode. Does not download manifests or files.
    
    Example:
        >>> from fab_egl_adapter import FabEGLAdapter
        >>> from fab_api_client import FabClient
        >>> adapter = FabEGLAdapter()
        >>> auth_provider = adapter.get_auth_provider()
        >>> client = FabClient(auth=auth_provider)
        >>> source = FabSource(client)
        >>> assets = list(source.list_assets())
    """
    
    def __init__(self, client: FabClient):
        """Initialize Fab source with authenticated client.
        
        Args:
            client: Authenticated FabClient instance. Users typically obtain
                   this via fab-egl-adapter.get_auth_provider() followed by
                   FabClient(auth=auth_provider).
        """
        self.client = client
        self._library: Optional[Library] = None
    
    def _get_library(self) -> Library:
        """Lazy-load user's library.
        
        Returns:
            User's Fab library with all entitled assets
            
        Raises:
            FabAPIError: If API call fails
        """
        if self._library is None:
            print("Fetching Fab library...", file=sys.stderr)
            self._library = self.client.get_library()
            print(f"Found {len(self._library.assets)} assets in library", file=sys.stderr)
        return self._library
    
    def list_assets(self) -> Iterator[SourceAsset]:
        """List all assets in user's Fab library.
        
        Yields:
            SourceAsset wrappers around Fab assets
            
        Raises:
            FabAPIError: If API call fails
        """
        library = self._get_library()
        
        for fab_asset in library.assets:
            yield FabAssetAdapter(fab_asset)
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve a specific asset by UID.
        
        Args:
            uid: Fab asset UID
            
        Returns:
            SourceAsset wrapper around the Fab asset
            
        Raises:
            ValueError: If asset not found in library
            FabAPIError: If API call fails
        """
        library = self._get_library()
        
        # Search library for matching asset
        for fab_asset in library.assets:
            if fab_asset.uid == uid:
                return FabAssetAdapter(fab_asset)
        
        raise ValueError(f"Asset {uid} not found in Fab library")
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get data for transformation.
        
        Phase 2: Returns only metadata. Does not download manifests.
        
        Args:
            asset: SourceAsset to retrieve data for
            download: If True, download manifests (Phase 3 feature)
            
        Returns:
            AssetData containing raw Fab asset metadata
            
        Raises:
            ValueError: If asset is not a FabAssetAdapter
            NotImplementedError: If download=True (Phase 3 feature)
        """
        if not isinstance(asset, FabAssetAdapter):
            raise ValueError(
                f"Expected FabAssetAdapter, got {type(asset).__name__}"
            )
        
        if download:
            # Phase 3: Download and parse manifest
            raise NotImplementedError(
                "Manifest downloading not yet implemented. "
                "This is a Phase 3 feature. Use download_strategy='metadata_only'."
            )
        
        # Phase 2: Return metadata only
        return AssetData(
            source_asset=asset,
            metadata={
                'fab_asset': asset.raw_asset,  # Store raw asset for transformer
            },
            files=[],  # No files in metadata-only mode
            manifest=None,
        )
```

### platforms/fab/transformer.py

```python
"""Fab marketplace transformer implementation.

Converts Fab assets to game-asset-tracker manifest format.
"""

import uuid
from typing import Optional

from fab_api_client import Asset as FabAsset

from ...core.types import Manifest, Asset as ManifestAsset
from ...transformers.base import Transformer
from ...sources.base import AssetData


class FabTransformer(Transformer):
    """Transformer for Fab marketplace assets.
    
    Converts Fab Asset objects into game-asset-tracker manifests.
    
    Phase 2: Metadata-only transformation. Creates a single placeholder
    asset entry with marketplace metadata. No individual files.
    
    Phase 3: Will parse manifests and create entries for individual files.
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
        
        Args:
            asset_data: AssetData from FabSource containing Fab asset
            pack_name: Optional override for pack name (default: asset title)
            global_tags: Optional global tags for the pack
            license_link: Optional override for license URL
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Manifest conforming to schema
            
        Raises:
            ValueError: If asset_data doesn't contain Fab asset
        """
        # Extract Fab asset from metadata
        fab_asset: FabAsset = asset_data.metadata.get('fab_asset')
        if not fab_asset:
            raise ValueError("AssetData missing 'fab_asset' in metadata")
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        
        # Use provided pack_name or fallback to asset title
        final_pack_name = pack_name or fab_asset.title
        
        # Extract license from listing if not provided
        if license_link is None and hasattr(fab_asset, 'listing'):
            if hasattr(fab_asset.listing, 'license_url'):
                license_link = fab_asset.listing.license_url or ""
        
        # Default to empty string if still None
        license_link = license_link or ""
        
        # Global tags (empty for now, TODO: extract from listing categories)
        final_global_tags = global_tags or []
        
        # Phase 2: Create single placeholder asset entry
        # This represents the marketplace asset as a whole
        placeholder_asset = self._create_placeholder_asset(fab_asset)
        
        # Build manifest
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': '',  # Marketplace assets have no local path
            'source': 'Fab - Epic Games',
            'license_link': license_link,
            'global_tags': final_global_tags,
            'assets': [placeholder_asset],
        }
        
        return manifest
    
    def _create_placeholder_asset(self, fab_asset: FabAsset) -> ManifestAsset:
        """Create placeholder asset entry for metadata-only mode.
        
        Phase 2: Single entry representing the entire marketplace asset.
        Phase 3: This will be replaced with individual file entries from manifest.
        
        Args:
            fab_asset: Fab asset to create placeholder for
            
        Returns:
            ManifestAsset with marketplace metadata
        """
        # Extract marketplace-specific metadata
        metadata: dict[str, str] = {}
        
        # Asset status (ACTIVE, EXPIRED, etc.)
        if hasattr(fab_asset, 'status'):
            metadata['status'] = str(fab_asset.status)
        
        # Entitlement status
        if hasattr(fab_asset, 'entitlement'):
            metadata['entitled'] = 'true' if fab_asset.entitlement else 'false'
        
        # Listing information
        if hasattr(fab_asset, 'listing'):
            listing = fab_asset.listing
            
            if hasattr(listing, 'uid'):
                metadata['listing_uid'] = str(listing.uid)
            
            if hasattr(listing, 'seller') and hasattr(listing.seller, 'name'):
                metadata['seller_name'] = str(listing.seller.name)
            
            # Price information (if available)
            if hasattr(listing, 'current_price'):
                metadata['current_price'] = str(listing.current_price)
        
        # Grant information
        if hasattr(fab_asset, 'granted_licenses'):
            metadata['granted_licenses'] = str(len(fab_asset.granted_licenses))
        
        # Timestamps
        if hasattr(fab_asset, 'created_at'):
            metadata['created_at'] = str(fab_asset.created_at)
        
        if hasattr(fab_asset, 'updated_at'):
            metadata['updated_at'] = str(fab_asset.updated_at)
        
        # TODO: This metadata storage approach is temporary.
        # Future: Need more robust solution for marketplace-specific fields.
        # See docs/PHASE_4_DOCUMENTATION.md for alternatives:
        # - Schema extensions with marketplace-specific tables
        # - Sidecar JSON files for complex structured data
        # - Separate SQLite tables for queryable metadata
        
        asset: ManifestAsset = {
            'relative_path': fab_asset.title,  # Use title as pseudo-path
            'file_type': 'marketplace',  # Special type for marketplace assets
            'size_bytes': 0,  # Unknown in metadata-only mode
            'metadata': metadata,
            'local_tags': [],  # No folder structure for marketplace assets
        }
        
        return asset
```

### platforms/fab/__init__.py

```python
"""Fab marketplace platform integration.

This module provides Fab marketplace support for the ingestion pipeline.
It automatically registers with SourceRegistry if fab-api-client is available.

Usage:
    >>> from game_asset_tracker_ingestion import SourceRegistry
    >>> 
    >>> # Check if Fab support is available
    >>> if 'fab' in SourceRegistry.list_sources():
    ...     # Create pipeline
    ...     from fab_api_client import FabClient, CookieAuthProvider
    ...     auth = CookieAuthProvider(cookies={...}, endpoints=...)
    ...     client = FabClient(auth=auth)
    ...     
    ...     pipeline = SourceRegistry.create_pipeline('fab', client=client)
    ...     
    ...     # Generate manifests
    ...     for manifest in pipeline.generate_manifests():
    ...         print(f"Generated manifest for {manifest['pack_name']}")
"""

# Gated import: Only load if fab-api-client is installed
try:
    from fab_api_client import FabClient, Asset as FabAsset, Library
    
    # Import our implementations
    from .source import FabSource, FabAssetAdapter
    from .transformer import FabTransformer
    
    # Import registry for auto-registration
    from ...registry import SourceRegistry
    
    # Factory function for creating FabSource instances
    def _create_fab_source(client: FabClient, **kwargs) -> FabSource:
        """Factory function for creating FabSource.
        
        Args:
            client: Authenticated FabClient instance
            **kwargs: Additional arguments (currently unused)
            
        Returns:
            Configured FabSource instance
        """
        return FabSource(client)
    
    # Auto-register with registry when module is imported
    SourceRegistry.register_factory('fab', _create_fab_source)
    
    # Availability flag
    FAB_AVAILABLE = True
    
    __all__ = [
        'FabSource',
        'FabAssetAdapter',
        'FabTransformer',
        'FAB_AVAILABLE',
    ]

except ImportError:
    # fab-api-client not installed, provide graceful degradation
    FAB_AVAILABLE = False
    FabSource = None
    FabAssetAdapter = None
    FabTransformer = None
    
    __all__ = ['FAB_AVAILABLE']
```

---

## Testing Strategy

### Test File Structure

Create `tests/test_fab_platform.py` with the following test classes:

1. **TestFabSourceMocked** - Tests with mocked FabClient
2. **TestFabTransformer** - Tests transformer logic with sample data
3. **TestFabIntegration** - End-to-end tests with pipeline
4. **TestFabGracefulDegradation** - Tests when fab-api-client not installed

### Mock Data Fixtures

```python
# tests/test_fab_platform.py

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

# Mock Fab types
class MockFabAsset:
    """Mock Fab asset for testing."""
    
    def __init__(
        self,
        uid: str,
        title: str,
        description: str = "",
        status: str = "ACTIVE",
        entitlement: bool = True
    ):
        self.uid = uid
        self.title = title
        self.description = description
        self.status = status
        self.entitlement = entitlement
        self.created_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-02T00:00:00Z"
        
        # Mock listing
        self.listing = Mock()
        self.listing.uid = f"{uid}-listing"
        self.listing.seller = Mock()
        self.listing.seller.name = "Epic Games"
        self.listing.license_url = "https://example.com/license"
        self.listing.current_price = 0
        
        # Mock licenses
        self.granted_licenses = ["license1", "license2"]


class MockLibrary:
    """Mock Fab library for testing."""
    
    def __init__(self, assets: List[MockFabAsset]):
        self.assets = assets


@pytest.fixture
def sample_fab_assets():
    """Sample Fab assets for testing."""
    return [
        MockFabAsset(
            uid="asset-1",
            title="Fantasy 3D Models",
            description="A collection of fantasy characters",
            status="ACTIVE",
            entitlement=True
        ),
        MockFabAsset(
            uid="asset-2",
            title="SciFi Materials",
            description="PBR materials for sci-fi environments",
            status="ACTIVE",
            entitlement=True
        ),
        MockFabAsset(
            uid="asset-3",
            title="Sound Effects Pack",
            description="High-quality sound effects",
            status="EXPIRED",
            entitlement=False
        ),
    ]


@pytest.fixture
def mock_fab_client(sample_fab_assets):
    """Mock FabClient for testing."""
    client = Mock()
    library = MockLibrary(sample_fab_assets)
    client.get_library.return_value = library
    client.get_asset = Mock(side_effect=lambda uid: next(
        (a for a in sample_fab_assets if a.uid == uid),
        None
    ))
    return client
```

### Test Cases

#### TestFabSourceMocked

```python
class TestFabSourceMocked:
    """Tests for FabSource with mocked client."""
    
    def test_list_assets_returns_all_library_assets(self, mock_fab_client):
        """Test that list_assets returns all assets from library."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        assets = list(source.list_assets())
        
        assert len(assets) == 3
        assert assets[0].uid == "asset-1"
        assert assets[0].title == "Fantasy 3D Models"
        assert assets[0].source_type == "fab"
    
    def test_get_asset_returns_specific_asset(self, mock_fab_client):
        """Test retrieving a specific asset by UID."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-2")
        
        assert asset.uid == "asset-2"
        assert asset.title == "SciFi Materials"
    
    def test_get_asset_raises_for_unknown_uid(self, mock_fab_client):
        """Test that get_asset raises ValueError for unknown UID."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        
        with pytest.raises(ValueError, match="not found"):
            source.get_asset("nonexistent-uid")
    
    def test_get_asset_data_metadata_only(self, mock_fab_client):
        """Test get_asset_data in metadata-only mode."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-1")
        asset_data = source.get_asset_data(asset, download=False)
        
        assert asset_data.source_asset == asset
        assert 'fab_asset' in asset_data.metadata
        assert asset_data.files == []
        assert asset_data.manifest is None
    
    def test_get_asset_data_download_not_implemented(self, mock_fab_client):
        """Test that download=True raises NotImplementedError in Phase 2."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        asset = source.get_asset("asset-1")
        
        with pytest.raises(NotImplementedError, match="Phase 3"):
            source.get_asset_data(asset, download=True)
    
    def test_library_lazy_loaded(self, mock_fab_client):
        """Test that library is only fetched once."""
        from game_asset_tracker_ingestion.platforms.fab import FabSource
        
        source = FabSource(mock_fab_client)
        
        # First call
        list(source.list_assets())
        assert mock_fab_client.get_library.call_count == 1
        
        # Second call should use cached library
        list(source.list_assets())
        assert mock_fab_client.get_library.call_count == 1
```

#### TestFabTransformer

```python
class TestFabTransformer:
    """Tests for FabTransformer."""
    
    def test_transform_creates_valid_manifest(self, sample_fab_assets):
        """Test basic transformation to manifest."""
        from game_asset_tracker_ingestion.platforms.fab import (
            FabTransformer,
            FabAssetAdapter
        )
        from game_asset_tracker_ingestion.sources.base import AssetData
        from game_asset_tracker_ingestion.core.validator import validate_manifest
        
        transformer = FabTransformer()
        fab_asset = sample_fab_assets[0]
        source_asset = FabAssetAdapter(fab_asset)
        
        asset_data = AssetData(
            source_asset=source_asset,
            metadata={'fab_asset': fab_asset},
            files=[],
            manifest=None,
        )
        
        manifest = transformer.transform(asset_data)
        
        # Validate against schema
        validate_manifest(manifest)
        
        # Check pack-level fields
        assert manifest['pack_name'] == "Fantasy 3D Models"
        assert manifest['source'] == "Fab - Epic Games"
        assert manifest['root_path'] == ""
        assert manifest['license_link'] == "https://example.com/license"
    
    def test_transform_uses_custom_pack_name(self, sample_fab_assets):
        """Test that pack_name override works."""
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
            manifest=None,
        )
        
        manifest = transformer.transform(
            asset_data,
            pack_name="Custom Pack Name"
        )
        
        assert manifest['pack_name'] == "Custom Pack Name"
    
    def test_transform_creates_placeholder_asset(self, sample_fab_assets):
        """Test that placeholder asset is created in Phase 2."""
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
            manifest=None,
        )
        
        manifest = transformer.transform(asset_data)
        
        # Should have exactly one placeholder asset
        assert len(manifest['assets']) == 1
        
        asset = manifest['assets'][0]
        assert asset['file_type'] == 'marketplace'
        assert asset['size_bytes'] == 0
        assert asset['relative_path'] == "Fantasy 3D Models"
        assert asset['local_tags'] == []
        
        # Check metadata contains Fab-specific fields
        assert 'status' in asset['metadata']
        assert asset['metadata']['status'] == 'ACTIVE'
        assert 'entitled' in asset['metadata']
        assert asset['metadata']['entitled'] == 'true'
        assert 'listing_uid' in asset['metadata']
        assert 'seller_name' in asset['metadata']
    
    def test_transform_handles_missing_metadata(self):
        """Test transformer handles assets with minimal metadata."""
        from game_asset_tracker_ingestion.platforms.fab import (
            FabTransformer,
            FabAssetAdapter
        )
        from game_asset_tracker_ingestion.sources.base import AssetData
        
        # Minimal mock asset
        minimal_asset = Mock()
        minimal_asset.uid = "minimal"
        minimal_asset.title = "Minimal Asset"
        minimal_asset.description = ""
        
        transformer = FabTransformer()
        source_asset = FabAssetAdapter(minimal_asset)
        
        asset_data = AssetData(
            source_asset=source_asset,
            metadata={'fab_asset': minimal_asset},
            files=[],
            manifest=None,
        )
        
        # Should not raise even with missing optional fields
        manifest = transformer.transform(asset_data)
        
        assert manifest['pack_name'] == "Minimal Asset"
        assert manifest['license_link'] == ""
```

#### TestFabIntegration

```python
class TestFabIntegration:
    """Integration tests with IngestionPipeline."""
    
    def test_pipeline_creation_via_registry(self, mock_fab_client):
        """Test creating Fab pipeline via SourceRegistry."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        # Check Fab is registered
        assert 'fab' in SourceRegistry.list_sources()
        
        # Create pipeline
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        assert pipeline is not None
        assert pipeline.download_strategy == 'metadata_only'
    
    def test_generate_manifests_yields_all_assets(self, mock_fab_client):
        """Test that generate_manifests yields one manifest per asset."""
        from game_asset_tracker_ingestion import SourceRegistry
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        manifests = list(pipeline.generate_manifests())
        
        assert len(manifests) == 3
        assert manifests[0]['pack_name'] == "Fantasy 3D Models"
        assert manifests[1]['pack_name'] == "SciFi Materials"
        assert manifests[2]['pack_name'] == "Sound Effects Pack"
    
    def test_generate_manifests_validates_schema(self, mock_fab_client):
        """Test that all generated manifests are valid."""
        from game_asset_tracker_ingestion import SourceRegistry
        from game_asset_tracker_ingestion.core.validator import validate_manifest
        
        pipeline = SourceRegistry.create_pipeline(
            'fab',
            client=mock_fab_client
        )
        
        for manifest in pipeline.generate_manifests():
            # Should not raise ValidationError
            validate_manifest(manifest)
```

#### TestFabGracefulDegradation

```python
class TestFabGracefulDegradation:
    """Tests for graceful handling when fab-api-client not installed."""
    
    def test_module_loads_without_fab_api_client(self):
        """Test that module can be imported even without fab-api-client."""
        # This test would need to mock the ImportError
        # In practice, run with: `uv sync` (without --extra fab)
        
        try:
            from game_asset_tracker_ingestion.platforms import fab
            assert fab.FAB_AVAILABLE is False
        except ImportError:
            pytest.fail("Platform module should load even without dependencies")
    
    def test_fab_not_in_registry_without_client(self):
        """Test that 'fab' is not registered if fab-api-client missing."""
        # This test would need to be run in environment without fab-api-client
        # In CI, create separate test environment without optional dependencies
        
        from game_asset_tracker_ingestion import SourceRegistry
        
        if 'fab' in SourceRegistry.list_sources():
            pytest.skip("fab-api-client is installed, cannot test degradation")
        
        # Attempting to create fab pipeline should fail gracefully
        with pytest.raises(ValueError, match="Unknown source"):
            SourceRegistry.create_pipeline('fab', client=None)
```

### Running Tests

```bash
# Run all Fab tests
uv run pytest tests/test_fab_platform.py -v

# Run with coverage
uv run pytest tests/test_fab_platform.py --cov=game_asset_tracker_ingestion.platforms.fab

# Run specific test class
uv run pytest tests/test_fab_platform.py::TestFabSourceMocked -v

# Test graceful degradation (without fab-api-client)
uv sync  # No --extra fab
uv run pytest tests/test_fab_platform.py::TestFabGracefulDegradation -v
```

---

## Integration & Validation

### Manual Testing Checklist

1. **Installation**
   - [ ] `uv sync --extra fab` succeeds
   - [ ] `uv sync` (without fab) still works

2. **Registry Discovery**
   ```python
   from game_asset_tracker_ingestion import SourceRegistry
   print(SourceRegistry.list_sources())
   # Should include 'fab' if installed correctly
   ```

3. **Pipeline Creation**
   ```python
   from fab_egl_adapter import FabEGLAdapter
   from fab_api_client import FabClient
   from game_asset_tracker_ingestion import SourceRegistry
   
   # Setup authentication via adapter
   adapter = FabEGLAdapter()
   auth_provider = adapter.get_auth_provider()
   client = FabClient(auth=auth_provider)
   
   # Create pipeline
   pipeline = SourceRegistry.create_pipeline('fab', client=client)
   ```

4. **Manifest Generation**
   ```python
   # Generate all manifests
   for manifest in pipeline.generate_manifests():
       print(f"Generated: {manifest['pack_name']}")
   
   # Generate first 5 only
   from itertools import islice
   for manifest in islice(pipeline.generate_manifests(), 5):
       print(f"Pack: {manifest['pack_name']}, Assets: {len(manifest['assets'])}")
   ```

5. **Manifest Validation**
   ```python
   from game_asset_tracker_ingestion.core.validator import validate_manifest
   
   pipeline = SourceRegistry.create_pipeline('fab', client=client)
   manifest = next(pipeline.generate_manifests())
   
   # Should not raise
   validate_manifest(manifest)
   print("✓ Manifest is valid")
   ```

6. **Output to File**
   ```python
   import json
   from pathlib import Path
   
   output_dir = Path("output")
   output_dir.mkdir(exist_ok=True)
   
   for manifest in pipeline.generate_manifests():
       output_file = output_dir / f"{manifest['pack_id']}.json"
       with open(output_file, 'w') as f:
           json.dump(manifest, f, indent=2)
       print(f"Wrote {output_file}")
   ```

### Validation Criteria

**Phase 2 is complete when**:

- ✅ `uv sync --extra fab` installs successfully
- ✅ `SourceRegistry.list_sources()` includes `'fab'`
- ✅ Can create pipeline: `SourceRegistry.create_pipeline('fab', client=client)`
- ✅ Pipeline generates manifests that pass schema validation
- ✅ Each manifest has exactly 1 placeholder asset (Phase 2 behavior)
- ✅ Manifest contains Fab-specific metadata (status, listing_uid, etc.)
- ✅ All tests pass: `uv run pytest tests/test_fab_platform.py`
- ✅ Graceful degradation works (module loads without fab-api-client)

---

## Example Usage

### Complete Working Example

```python
"""Example: Generate manifests for all Fab assets in user's library.

Prerequisites:
- fab-api-client installed: uv sync --extra fab
- fab-egl-adapter installed (for authentication)
- Epic Games Launcher installed with active session
"""

import json
from pathlib import Path
from fab_egl_adapter import FabEGLAdapter
from fab_api_client import FabClient
from game_asset_tracker_ingestion import SourceRegistry

def main():
    # 1. Setup authentication via adapter
    # FabEGLAdapter extracts cookies from Epic Games Launcher installation
    try:
        adapter = FabEGLAdapter()
        auth_provider = adapter.get_auth_provider()
    except Exception as e:
        print(f"Error: Could not extract authentication from EGL: {e}")
        print("Ensure Epic Games Launcher is installed and you're logged in.")
        return
    
    # 2. Create authenticated client
    client = FabClient(auth=auth_provider)
    
    # 3. Create pipeline
    print("Creating Fab pipeline...")
    pipeline = SourceRegistry.create_pipeline(
        'fab',
        client=client,
        download_strategy='metadata_only'  # Phase 2: metadata only
    )
    
    # 4. Setup output directory
    output_dir = Path("manifests/fab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Generate manifests
    print("Generating manifests...")
    count = 0
    
    for manifest in pipeline.generate_manifests():
        pack_id = manifest['pack_id']
        pack_name = manifest['pack_name']
        
        # Write to file
        output_file = output_dir / f"{pack_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ {pack_name} → {output_file.name}")
        count += 1
    
    print(f"\nGenerated {count} manifests in {output_dir}")

if __name__ == '__main__':
    main()
```

### Filtering Example (Preview for Phase 4)

```python
"""Example: Generate manifests for only entitled assets."""

from game_asset_tracker_ingestion import SourceRegistry

# Create pipeline
pipeline = SourceRegistry.create_pipeline('fab', client=client)

# Define filter function
def only_entitled(asset):
    """Only process assets user is entitled to."""
    return hasattr(asset, 'entitlement') and asset.entitlement

# Generate filtered manifests
# NOTE: This filtering API is not yet implemented (Phase 4 feature)
# for manifest in pipeline.generate_manifests(filter_fn=only_entitled):
#     print(f"Processing: {manifest['pack_name']}")

# Phase 2 workaround: Filter manually
for manifest in pipeline.generate_manifests():
    # Check if placeholder asset metadata indicates entitlement
    asset = manifest['assets'][0]
    if asset['metadata'].get('entitled') == 'true':
        print(f"Processing: {manifest['pack_name']}")
```

---

## Edge Cases & Gotchas

### Authentication Issues

**Problem**: FabClient requires valid authentication cookies that expire.

**Solution**:
- Use `fab-egl-adapter` to automatically extract fresh cookies from EGL
- Adapter handles cookie refresh and expiration detection
- Provide clear error messages when auth fails:

```python
from fab_egl_adapter import FabEGLAdapter
from fab_api_client import FabClient
from game_asset_tracker_ingestion import SourceRegistry

try:
    # Adapter extracts authentication from EGL
    adapter = FabEGLAdapter()
    auth_provider = adapter.get_auth_provider()
    client = FabClient(auth=auth_provider)
    
    # Create pipeline and generate manifests
    pipeline = SourceRegistry.create_pipeline('fab', client=client)
    list(pipeline.generate_manifests())
except Exception as e:
    if 'authentication' in str(e).lower() or '401' in str(e):
        print("Error: Authentication failed.")
        print("Ensure Epic Games Launcher is installed and you're logged in.")
        print("Try restarting EGL and logging in again.")
    else:
        raise
```

**Alternative**: For testing or non-EGL environments, you can still manually provide auth:

```python
from fab_api_client import FabClient, CookieAuthProvider

# Manual authentication (not recommended for production)
cookies = {'EPIC_SSO': '...', 'EPIC_BEARER_TOKEN': '...'}
endpoints = {'library': 'https://fab.com/api/v1/library'}
auth_provider = CookieAuthProvider(cookies=cookies, endpoints=endpoints)
client = FabClient(auth=auth_provider)
```

### Large Libraries

**Problem**: Users with 100+ assets may experience slow initial load.

**Considerations**:
- Library fetching is lazy-loaded (only happens on first `list_assets()`)
- Consider adding progress feedback:

```python
# In FabSource.list_assets()
print(f"Fetching Fab library...", file=sys.stderr)
library = self._get_library()
print(f"Found {len(library.assets)} assets", file=sys.stderr)

for i, fab_asset in enumerate(library.assets, 1):
    if i % 10 == 0:
        print(f"Processing asset {i}/{len(library.assets)}...", file=sys.stderr)
    yield FabAssetAdapter(fab_asset)
```

### Missing Optional Fields

**Problem**: Not all Fab assets have complete metadata (seller, license, etc.).

**Solution**: Defensive programming with `hasattr()` checks:

```python
# Always check before accessing
if hasattr(fab_asset, 'listing'):
    if hasattr(fab_asset.listing, 'license_url'):
        license_url = fab_asset.listing.license_url or ""
```

**Best practice**: Provide sensible defaults:

```python
license_link = license_link or ""  # Empty string, not None
global_tags = global_tags or []    # Empty list, not None
```

### Schema Validation Failures

**Problem**: Manifest doesn't conform to schema.

**Common causes**:
1. Pack name contains invalid characters
2. Metadata values are not strings
3. UUID format incorrect

**Debugging**:

```python
from game_asset_tracker_ingestion.core.validator import (
    validate_manifest_with_error_details
)

is_valid, error_msg = validate_manifest_with_error_details(manifest)
if not is_valid:
    print(f"Validation failed: {error_msg}")
    print(f"Manifest: {json.dumps(manifest, indent=2)}")
```

### Phase 2 Limitations

**What Phase 2 CANNOT do**:

1. **No file lists**: Manifests contain only 1 placeholder asset
2. **No accurate sizes**: `size_bytes` is always 0
3. **No manifest parsing**: Cannot process `.uasset` or `.umap` files
4. **No downloads**: Setting `download=True` raises `NotImplementedError`

**Users should be warned**:

```python
# In documentation/error messages
print("Note: Phase 2 provides metadata-only transformation.")
print("Individual asset files will be available in Phase 3.")
print("Use download_strategy='metadata_only' for now.")
```

---

## Future Enhancements

### Phase 3 Integration Points

When implementing Phase 3 (download strategy), modify these areas:

1. **FabSource.get_asset_data()**:
   ```python
   def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
       if download:
           # Phase 3: Download manifest
           manifest_result = self.client.download_manifest(
               asset.raw_asset,
               temp_dir=Path('/tmp/fab-manifests')
           )
           parsed_manifest = manifest_result.load()
           
           return AssetData(
               source_asset=asset,
               metadata={'fab_asset': asset.raw_asset},
               files=[],
               manifest=parsed_manifest,  # Phase 3: Include parsed manifest
           )
       # ... Phase 2 code
   ```

2. **FabTransformer.transform()**:
   ```python
   def transform(self, asset_data: AssetData, **kwargs) -> Manifest:
       # Check if manifest is available
       if asset_data.manifest:
           # Phase 3: Parse manifest files
           assets = self._parse_manifest_files(asset_data.manifest)
       else:
           # Phase 2: Single placeholder
           assets = [self._create_placeholder_asset(fab_asset)]
       
       # ... rest of transformation
   ```

3. **Add `_parse_manifest_files()` method**:
   ```python
   def _parse_manifest_files(self, parsed_manifest) -> list[ManifestAsset]:
       """Phase 3: Parse individual files from manifest."""
       assets = []
       
       for manifest_file in parsed_manifest.files:
           asset = {
               'relative_path': manifest_file.filename,
               'file_type': Path(manifest_file.filename).suffix.lstrip('.').lower(),
               'size_bytes': self._calculate_file_size(manifest_file),
               'metadata': {
                   'file_hash': manifest_file.file_hash,
                   'build_version': parsed_manifest.build_version,
               },
               'local_tags': derive_local_tags(Path(manifest_file.filename)),
           }
           assets.append(asset)
       
       return assets
   ```

### Filtering Implementation (Phase 4)

Add filter support to pipeline:

```python
# In pipeline.py
def generate_manifests(
    self,
    filter_fn: Optional[Callable[[SourceAsset], bool]] = None,
    limit: Optional[int] = None
) -> Iterator[Manifest]:
    """Generate manifests with optional filtering."""
    
    assets = self.source.list_assets()
    
    # Apply filter
    if filter_fn:
        assets = filter(filter_fn, assets)
    
    # Apply limit
    if limit:
        from itertools import islice
        assets = islice(assets, limit)
    
    # Transform each asset
    for asset in assets:
        asset_data = self.source.get_asset_data(asset, download=should_download)
        manifest = self.transformer.transform(asset_data)
        yield manifest
```

### Robust Metadata Storage

See Phase 4 documentation for alternatives to flexible `metadata` dict:

1. **Schema Extensions**: Add marketplace-specific tables
2. **Sidecar Files**: Store complex data separately
3. **Typed Metadata**: Use Pydantic models for validation

---

## References

### External Documentation

- **fab-api-client**: `../../fab-api-client/README.md`
- **asset-marketplace-core**: `../../asset-marketplace-client-system/architecture/`
- **JSON Schema**: `../schemas/manifest.schema.json`
- **Phase 1 Implementation**: Review `platforms/filesystem/` for reference

### Related Phases

- **Phase 1**: Core architecture (prerequisite)
- **Phase 3**: Download strategy (builds on this phase)
- **Phase 4**: Documentation and extension points
- **Phase 5**: UAS integration (parallel marketplace)

---

## Summary

Phase 2 adds Fab marketplace support through:

1. **FabSource**: Adapter wrapping `FabClient` to implement `Source` interface
2. **FabTransformer**: Converts Fab assets to game-asset-tracker manifests
3. **Auto-registration**: Platform registers itself when imported
4. **Graceful degradation**: Works even when fab-api-client not installed

**Key achievements**:
- One manifest per Fab asset (marketplace asset = asset pack)
- Metadata-only transformation (no downloads in Phase 2)
- Schema-compliant output
- Extensible foundation for Phase 3 (download strategy)

**Next steps**:
- Implement Phase 3 to add manifest downloading and parsing
- See Phase 4 documentation for filtering and extension points
- Consider Phase 5 (UAS) to validate multi-marketplace architecture

This guide provides everything needed for a future implementer to add Fab support to the ingestion library.
