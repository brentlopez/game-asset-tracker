# Phase 5: UAS Integration - Comprehensive Template Guide

**Status**: Documentation for future implementation  
**Estimated Effort**: 2-3 days  
**Prerequisites**: Phases 1-3 complete, Phase 2 (Fab) serves as reference template

## Table of Contents

1. [Overview](#overview)
2. [Context & Rationale](#context--rationale)
3. [UAS vs Fab Differences](#uas-vs-fab-differences)
4. [Implementation Template](#implementation-template)
5. [Complete Code Implementations](#complete-code-implementations)
6. [Testing Strategy](#testing-strategy)
7. [Integration Checklist](#integration-checklist)
8. [Validation & Examples](#validation--examples)
9. [Lessons from Fab Integration](#lessons-from-fab-integration)

---

## Overview

Phase 5 documents UAS (Unreal Asset Store) marketplace integration following the same pattern established by Fab in Phase 2. This phase serves as:

1. **Validation** of the multi-marketplace architecture
2. **Template** for future marketplace integrations
3. **Reference** showing platform-specific adaptations

### Goals

- Document complete UAS source implementation
- Identify UAS-specific differences from Fab
- Validate that the architecture supports multiple marketplaces
- Provide template for adding other marketplaces (Steam, Sketchfab, etc.)

### Non-Goals

- Implementing UAS integration (documentation only)
- Creating uas-api-client (assumed to exist, parallel to fab-api-client)
- Full testing suite (test templates provided)

---

## Context & Rationale

### Why UAS as Phase 5?

1. **Parallel structure to Fab**: Both are marketplace sources from Epic Games ecosystem
2. **Different enough**: UAS has distinct API, auth, and data structures
3. **Multi-marketplace validation**: Proves architecture works for > 1 marketplace
4. **Template value**: Other Epic assets (Quixel, MetaHumans) may follow similar patterns

### Architectural Validation

Phase 5 validates these architectural decisions:

**✅ Platform modularity**: Each marketplace in self-contained `platforms/` directory

**✅ Registry pattern**: Auto-registration without modifying core code

**✅ Graceful degradation**: System works even when uas-api-client not installed

**✅ Transformer flexibility**: Each marketplace can have unique transformation logic

**✅ Download strategy**: Configurable per-pipeline

---

## UAS vs Fab Differences

### Key Differences

| Aspect | Fab | UAS | Impact |
|--------|-----|-----|--------|
| **Authentication** | Cookie-based | Token/OAuth | Different auth provider |
| **Asset structure** | `Asset` with `listing` | `Product` with `catalog_item` | Different field names |
| **Version field** | `build_version` | `app_version` | Transformation mapping |
| **Manifest format** | Custom binary | May be JSON or binary | Parser logic |
| **License info** | `listing.license_url` | `terms_of_service_url` | Field mapping |
| **Entitlement** | `entitlement` boolean | `ownership.granted` object | Entitlement check |

### Expected API Differences

**Fab client pattern (with adapter)**:
```python
# Tier 3: Extract authentication
from fab_egl_adapter import FabEGLAdapter
adapter = FabEGLAdapter()
auth_provider = adapter.get_auth_provider()  # CookieAuthProvider

# Tier 2: Use authenticated client
client = FabClient(auth=auth_provider)
library = client.get_library()
for asset in library.assets:
    manifest = client.download_manifest(asset, temp_dir)
```

**Expected UAS client pattern (with adapter)**:
```python
# Tier 3: Extract authentication
from uas_adapter import UASAdapter
adapter = UASAdapter()
auth_provider = adapter.get_auth_provider()  # TokenAuthProvider

# Tier 2: Use authenticated client
client = UASClient(auth=auth_provider)
collection = client.get_owned_products()
for product in collection.products:
    manifest = client.download_product_manifest(product, temp_dir)
```

**Key Difference**: Both use adapters but extract different auth types:
- **Fab**: `fab-egl-adapter` → `CookieAuthProvider` (cookies from Epic Games Launcher)
- **UAS**: `uas-adapter` → `TokenAuthProvider` (tokens from Unity Editor installation)

### Metadata Field Mapping

**Fab** → **UAS** equivalent:

- `asset.title` → `product.display_name`
- `asset.description` → `product.long_description`
- `asset.uid` → `product.id`
- `asset.listing.seller.name` → `product.seller.display_name`
- `asset.status` → `product.release_info.status`
- `asset.entitlement` → `product.ownership.entitled`

---

## Implementation Template

### Directory Structure

```
platforms/uas/
├── __init__.py          # Auto-registration (gated import)
├── source.py            # UASSource implementing Source ABC
└── transformer.py       # UASTransformer implementing Transformer ABC
```

### Implementation Checklist

- [ ] Create `platforms/uas/` directory
- [ ] Implement `UASAssetAdapter` (SourceAsset protocol)
- [ ] Implement `UASSource` (Source ABC)
- [ ] Implement `UASTransformer` (Transformer ABC)
- [ ] Create gated import in `__init__.py`
- [ ] Add optional dependency to `pyproject.toml`
- [ ] Write tests with mocked UAS client
- [ ] Create example script
- [ ] Update documentation

---

## Complete Code Implementations

### platforms/uas/source.py

```python
"""UAS (Unreal Asset Store) marketplace source implementation.

This module provides a Source adapter for the UAS marketplace
using the uas-api-client library.
"""

from pathlib import Path
from typing import Iterator, Optional
import sys
import tempfile
import shutil

from uas_api_client import UASClient, Product as UASProduct, Collection

from ...sources.base import Source, SourceAsset, AssetData


class UASAssetAdapter:
    """Adapter that makes UASProduct compatible with SourceAsset protocol.
    
    This wraps a uas_api_client.Product and provides the interface expected
    by the pipeline.
    """
    
    def __init__(self, uas_product: UASProduct):
        self._product = uas_product
    
    @property
    def uid(self) -> str:
        """Unique identifier for this asset."""
        return self._product.id
    
    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._product.display_name
    
    @property
    def description(self) -> str:
        """Asset description."""
        return self._product.long_description or ""
    
    @property
    def source_type(self) -> str:
        """Source type identifier."""
        return "uas"
    
    @property
    def raw_product(self) -> UASProduct:
        """Access to underlying UAS product for transformation."""
        return self._product


class UASSource(Source):
    """Source implementation for UAS (Unreal Asset Store) marketplace.
    
    This source adapter wraps a UASClient and provides asset listing
    and retrieval functionality conforming to the Source interface.
    
    Phase 2: Metadata-only mode. Does not download manifests or files.
    Phase 3: Downloads and parses manifests (download=True).
    
    Example:
        >>> from uas_api_client import UASClient, TokenAuthProvider
        >>> auth = TokenAuthProvider(token='your-token')
        >>> client = UASClient(auth=auth)
        >>> source = UASSource(client)
        >>> assets = list(source.list_assets())
    """
    
    def __init__(self, client: UASClient):
        """Initialize UAS source with authenticated client.
        
        Args:
            client: Authenticated UASClient instance. User is responsible
                   for authentication (via TokenAuthProvider, etc.)
        """
        self.client = client
        self._collection: Optional[Collection] = None
    
    def _get_collection(self) -> Collection:
        """Lazy-load user's owned products collection.
        
        Returns:
            User's UAS collection with all owned products
            
        Raises:
            UASAPIError: If API call fails
        """
        if self._collection is None:
            print("Fetching UAS owned products...", file=sys.stderr)
            self._collection = self.client.get_owned_products()
            print(f"Found {len(self._collection.products)} products in collection", file=sys.stderr)
        return self._collection
    
    def list_assets(self) -> Iterator[SourceAsset]:
        """List all assets in user's UAS collection.
        
        Yields:
            SourceAsset wrappers around UAS products
            
        Raises:
            UASAPIError: If API call fails
        """
        collection = self._get_collection()
        
        for uas_product in collection.products:
            yield UASAssetAdapter(uas_product)
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve a specific asset by UID.
        
        Args:
            uid: UAS product ID
            
        Returns:
            SourceAsset wrapper around the UAS product
            
        Raises:
            ValueError: If product not found in collection
            UASAPIError: If API call fails
        """
        collection = self._get_collection()
        
        # Search collection for matching product
        for uas_product in collection.products:
            if uas_product.id == uid:
                return UASAssetAdapter(uas_product)
        
        raise ValueError(f"Product {uid} not found in UAS collection")
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get data for transformation.
        
        Phase 2: Returns only metadata. Does not download manifests.
        Phase 3: Downloads and parses manifests when download=True.
        
        Args:
            asset: SourceAsset to retrieve data for
            download: If True, download and parse manifest
            
        Returns:
            AssetData containing raw UAS product metadata
            
        Raises:
            ValueError: If asset is not a UASAssetAdapter
        """
        if not isinstance(asset, UASAssetAdapter):
            raise ValueError(
                f"Expected UASAssetAdapter, got {type(asset).__name__}"
            )
        
        uas_product = asset.raw_product
        
        if download:
            # Phase 3: Download and parse manifest
            print(f"Downloading manifest for {uas_product.display_name}...", file=sys.stderr)
            
            temp_dir = Path(tempfile.mkdtemp(prefix='uas-manifests-'))
            
            try:
                manifest_result = self.client.download_product_manifest(
                    uas_product,
                    download_path=temp_dir
                )
                
                parsed_manifest = manifest_result.load()
                print(f"  ✓ Parsed {len(parsed_manifest.files)} files", file=sys.stderr)
                
                return AssetData(
                    source_asset=asset,
                    metadata={'uas_product': uas_product},
                    files=[],
                    manifest=parsed_manifest,
                )
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Phase 2: Return metadata only
        return AssetData(
            source_asset=asset,
            metadata={'uas_product': uas_product},
            files=[],
            manifest=None,
        )
```

### platforms/uas/transformer.py

```python
"""UAS marketplace transformer implementation.

Converts UAS products to game-asset-tracker manifest format.
"""

import uuid
from pathlib import Path
from typing import Optional

from uas_api_client import Product as UASProduct

from ...core.types import Manifest, Asset as ManifestAsset
from ...transformers.base import Transformer
from ...sources.base import AssetData
from ...scanner import derive_local_tags


class UASTransformer(Transformer):
    """Transformer for UAS marketplace products.
    
    Converts UAS Product objects into game-asset-tracker manifests.
    
    Phase 2: Metadata-only transformation. Creates a single placeholder
    asset entry with marketplace metadata. No individual files.
    
    Phase 3: Parses manifests and creates entries for individual files.
    """
    
    def transform(
        self,
        asset_data: AssetData,
        pack_name: Optional[str] = None,
        global_tags: Optional[list[str]] = None,
        license_link: Optional[str] = None,
        **kwargs
    ) -> Manifest:
        """Transform UAS product data into manifest.
        
        Args:
            asset_data: AssetData from UASSource containing UAS product
            pack_name: Optional override for pack name (default: product display_name)
            global_tags: Optional global tags for the pack
            license_link: Optional override for license URL
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Manifest conforming to schema
            
        Raises:
            ValueError: If asset_data doesn't contain UAS product
        """
        # Extract UAS product from metadata
        uas_product: UASProduct = asset_data.metadata.get('uas_product')
        if not uas_product:
            raise ValueError("AssetData missing 'uas_product' in metadata")
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        
        # Use provided pack_name or fallback to product display_name
        final_pack_name = pack_name or uas_product.display_name
        
        # Extract license from product if not provided
        if license_link is None and hasattr(uas_product, 'terms_of_service_url'):
            license_link = uas_product.terms_of_service_url or ""
        
        # Default to empty string if still None
        license_link = license_link or ""
        
        # Global tags (empty for now, TODO: extract from product categories)
        final_global_tags = global_tags or []
        
        # Asset-level: Parse manifest if available, else placeholder
        if asset_data.manifest:
            # Phase 3: Parse individual files from manifest
            assets = self._parse_manifest_files(asset_data.manifest, uas_product)
        else:
            # Phase 2: Single placeholder asset
            assets = [self._create_placeholder_asset(uas_product)]
        
        # Build manifest
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': '',  # Marketplace assets have no local path
            'source': 'UAS - Unreal Asset Store',
            'license_link': license_link,
            'global_tags': final_global_tags,
            'assets': assets,
        }
        
        return manifest
    
    def _create_placeholder_asset(self, uas_product: UASProduct) -> ManifestAsset:
        """Create placeholder asset entry for metadata-only mode.
        
        Phase 2: Single entry representing the entire marketplace product.
        Phase 3: Replaced with individual file entries from manifest.
        
        Args:
            uas_product: UAS product to create placeholder for
            
        Returns:
            ManifestAsset with marketplace metadata
        """
        # Extract marketplace-specific metadata
        metadata: dict[str, str] = {}
        
        # Product status (ACTIVE, DEPRECATED, etc.)
        if hasattr(uas_product, 'release_info') and hasattr(uas_product.release_info, 'status'):
            metadata['status'] = str(uas_product.release_info.status)
        
        # Ownership/entitlement status
        if hasattr(uas_product, 'ownership'):
            metadata['entitled'] = 'true' if uas_product.ownership.entitled else 'false'
        
        # Catalog information
        if hasattr(uas_product, 'catalog_item'):
            catalog = uas_product.catalog_item
            
            if hasattr(catalog, 'id'):
                metadata['catalog_item_id'] = str(catalog.id)
            
            if hasattr(catalog, 'namespace'):
                metadata['namespace'] = str(catalog.namespace)
        
        # Seller information
        if hasattr(uas_product, 'seller') and hasattr(uas_product.seller, 'display_name'):
            metadata['seller_name'] = str(uas_product.seller.display_name)
        
        # Version information
        if hasattr(uas_product, 'app_version'):
            metadata['app_version'] = str(uas_product.app_version)
        
        # Timestamps
        if hasattr(uas_product, 'created_at'):
            metadata['created_at'] = str(uas_product.created_at)
        
        if hasattr(uas_product, 'updated_at'):
            metadata['updated_at'] = str(uas_product.updated_at)
        
        # TODO: This metadata storage approach is temporary.
        # See docs/PHASE_4_DOCUMENTATION.md for robust solutions.
        
        asset: ManifestAsset = {
            'relative_path': uas_product.display_name,
            'file_type': 'marketplace',
            'size_bytes': 0,
            'metadata': metadata,
            'local_tags': [],
        }
        
        return asset
    
    def _parse_manifest_files(
        self,
        parsed_manifest,
        uas_product: UASProduct
    ) -> list[ManifestAsset]:
        """Parse individual files from UAS manifest (Phase 3).
        
        Args:
            parsed_manifest: ParsedManifest from uas-api-client
            uas_product: Original UAS product for context
            
        Returns:
            List of ManifestAsset entries, one per file in manifest
        """
        assets: list[ManifestAsset] = []
        
        for manifest_file in parsed_manifest.files:
            # Extract file extension
            file_path = Path(manifest_file.filename)
            file_type = file_path.suffix.lstrip('.').lower() or 'unknown'
            
            # Calculate file size
            size_bytes = self._calculate_file_size(manifest_file)
            
            # Derive local tags from file path
            local_tags = derive_local_tags(file_path)
            
            # Build metadata
            metadata: dict[str, str] = {
                'file_hash': manifest_file.file_hash,
                'app_version': parsed_manifest.app_version,
                'product_id': uas_product.id,
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
        """Calculate total file size from chunk parts.
        
        UAS manifests may use same chunking system as Fab,
        or have different structure. Adapt as needed.
        """
        total = 0
        
        # Adapt this based on actual UAS manifest structure
        if hasattr(manifest_file, 'file_chunk_parts'):
            for chunk_part in manifest_file.file_chunk_parts:
                if hasattr(chunk_part, 'chunks'):
                    for chunk in chunk_part.chunks:
                        if hasattr(chunk, 'size'):
                            total += chunk.size
        elif hasattr(manifest_file, 'size'):
            # Direct size field
            total = manifest_file.size
        
        return max(0, total)
```

### platforms/uas/__init__.py

```python
"""UAS (Unreal Asset Store) marketplace platform integration.

This module provides UAS marketplace support for the ingestion pipeline.
It automatically registers with SourceRegistry if uas-api-client is available.

Usage:
    >>> from game_asset_tracker_ingestion import SourceRegistry
    >>> 
    >>> # Check if UAS support is available
    >>> if 'uas' in SourceRegistry.list_sources():
    ...     # Create pipeline
    ...     from uas_api_client import UASClient, TokenAuthProvider
    ...     auth = TokenAuthProvider(token='your-token')
    ...     client = UASClient(auth=auth)
    ...     
    ...     pipeline = SourceRegistry.create_pipeline('uas', client=client)
    ...     
    ...     # Generate manifests
    ...     for manifest in pipeline.generate_manifests():
    ...         print(f"Generated manifest for {manifest['pack_name']}")
"""

# Gated import: Only load if uas-api-client is installed
try:
    from uas_api_client import UASClient, Product as UASProduct, Collection
    
    # Import our implementations
    from .source import UASSource, UASAssetAdapter
    from .transformer import UASTransformer
    
    # Import registry for auto-registration
    from ...registry import SourceRegistry
    
    # Factory function for creating UASSource instances
    def _create_uas_source(client: UASClient, **kwargs) -> UASSource:
        """Factory function for creating UASSource.
        
        Args:
            client: Authenticated UASClient instance
            **kwargs: Additional arguments (currently unused)
            
        Returns:
            Configured UASSource instance
        """
        return UASSource(client)
    
    # Auto-register with registry when module is imported
    SourceRegistry.register_factory('uas', _create_uas_source)
    
    # Availability flag
    UAS_AVAILABLE = True
    
    __all__ = [
        'UASSource',
        'UASAssetAdapter',
        'UASTransformer',
        'UAS_AVAILABLE',
    ]

except ImportError:
    # uas-api-client not installed, provide graceful degradation
    UAS_AVAILABLE = False
    UASSource = None
    UASAssetAdapter = None
    UASTransformer = None
    
    __all__ = ['UAS_AVAILABLE']
```

---

## Testing Strategy

### Test File: tests/test_uas_platform.py

Follow the same pattern as `test_fab_platform.py`:

```python
"""Tests for UAS platform integration."""

import pytest
from unittest.mock import Mock

# Mock UAS types
class MockUASProduct:
    """Mock UAS product for testing."""
    
    def __init__(
        self,
        id: str,
        display_name: str,
        long_description: str = "",
        status: str = "ACTIVE",
        entitled: bool = True
    ):
        self.id = id
        self.display_name = display_name
        self.long_description = long_description
        
        # Mock release info
        self.release_info = Mock()
        self.release_info.status = status
        
        # Mock ownership
        self.ownership = Mock()
        self.ownership.entitled = entitled
        
        # Mock seller
        self.seller = Mock()
        self.seller.display_name = "Epic Games"
        
        # Mock catalog
        self.catalog_item = Mock()
        self.catalog_item.id = f"{id}-catalog"
        self.catalog_item.namespace = "ue"
        
        # Version and timestamps
        self.app_version = "1.0.0"
        self.created_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-02T00:00:00Z"
        self.terms_of_service_url = "https://example.com/tos"


class MockCollection:
    """Mock UAS collection for testing."""
    
    def __init__(self, products: list):
        self.products = products


@pytest.fixture
def sample_uas_products():
    """Sample UAS products for testing."""
    return [
        MockUASProduct(
            id="prod-1",
            display_name="Fantasy Character Pack",
            long_description="A collection of fantasy characters",
            status="ACTIVE",
            entitled=True
        ),
        MockUASProduct(
            id="prod-2",
            display_name="SciFi Environment Pack",
            long_description="Sci-fi environment assets",
            status="ACTIVE",
            entitled=True
        ),
    ]


@pytest.fixture
def mock_uas_client(sample_uas_products):
    """Mock UASClient for testing."""
    client = Mock()
    collection = MockCollection(sample_uas_products)
    client.get_owned_products.return_value = collection
    return client


class TestUASSourceMocked:
    """Tests for UASSource with mocked client."""
    
    def test_list_assets_returns_all_products(self, mock_uas_client):
        """Test that list_assets returns all products from collection."""
        from game_asset_tracker_ingestion.platforms.uas import UASSource
        
        source = UASSource(mock_uas_client)
        assets = list(source.list_assets())
        
        assert len(assets) == 2
        assert assets[0].uid == "prod-1"
        assert assets[0].title == "Fantasy Character Pack"
        assert assets[0].source_type == "uas"
    
    def test_get_asset_returns_specific_product(self, mock_uas_client):
        """Test retrieving a specific product by ID."""
        from game_asset_tracker_ingestion.platforms.uas import UASSource
        
        source = UASSource(mock_uas_client)
        asset = source.get_asset("prod-2")
        
        assert asset.uid == "prod-2"
        assert asset.title == "SciFi Environment Pack"


class TestUASTransformer:
    """Tests for UASTransformer."""
    
    def test_transform_creates_valid_manifest(self, sample_uas_products):
        """Test basic transformation to manifest."""
        from game_asset_tracker_ingestion.platforms.uas import (
            UASTransformer,
            UASAssetAdapter
        )
        from game_asset_tracker_ingestion.sources.base import AssetData
        from game_asset_tracker_ingestion.core.validator import validate_manifest
        
        transformer = UASTransformer()
        uas_product = sample_uas_products[0]
        source_asset = UASAssetAdapter(uas_product)
        
        asset_data = AssetData(
            source_asset=source_asset,
            metadata={'uas_product': uas_product},
            files=[],
            manifest=None,
        )
        
        manifest = transformer.transform(asset_data)
        
        # Validate against schema
        validate_manifest(manifest)
        
        # Check pack-level fields
        assert manifest['pack_name'] == "Fantasy Character Pack"
        assert manifest['source'] == "UAS - Unreal Asset Store"
        assert manifest['root_path'] == ""
```

---

## Integration Checklist

### Prerequisites
- [ ] uas-api-client library available (parallel to fab-api-client)
- [ ] Phase 1 core architecture complete
- [ ] Phase 2 Fab integration complete (serves as reference)

### Implementation Steps
- [ ] Create `platforms/uas/` directory
- [ ] Implement `UASAssetAdapter` class
- [ ] Implement `UASSource` class
- [ ] Implement `UASTransformer` class
- [ ] Create gated import in `__init__.py`
- [ ] Add to `pyproject.toml` optional dependencies
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Create example script (`examples/uas_ingestion.py`)
- [ ] Test with real UAS client (if available)

### Validation
- [ ] `uv sync --extra uas` installs successfully
- [ ] `SourceRegistry.list_sources()` includes `'uas'`
- [ ] Can create pipeline via registry
- [ ] Pipeline generates valid manifests
- [ ] Graceful degradation without uas-api-client
- [ ] All tests pass

---

## Validation & Examples

### Example Usage

```python
"""Example: Generate manifests for UAS products."""

import json
from pathlib import Path
from uas_api_client import UASClient, TokenAuthProvider
from game_asset_tracker_ingestion import SourceRegistry

def main():
    # Setup authentication
    auth = TokenAuthProvider(token='your-uas-token')
    client = UASClient(auth=auth)
    
    # Create pipeline
    pipeline = SourceRegistry.create_pipeline(
        'uas',
        client=client,
        download_strategy='metadata_only'
    )
    
    # Generate manifests
    output_dir = Path("manifests/uas")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for manifest in pipeline.generate_manifests():
        pack_name = manifest['pack_name']
        output_file = output_dir / f"{manifest['pack_id']}.json"
        
        with open(output_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ {pack_name}")

if __name__ == '__main__':
    main()
```

---

## Lessons from Fab Integration

### What Worked Well

1. **Gated imports**: Clean handling of optional dependencies
2. **Auto-registration**: No core code modifications needed
3. **Adapter pattern**: Clean separation of client types from Source protocol
4. **Placeholder assets**: Simple Phase 2 implementation
5. **Graceful degradation**: Module loads even without client library

### Adaptations for UAS

1. **Field name mapping**: Adjusted for UAS-specific naming (display_name vs title)
2. **Auth provider**: Changed from cookies to token-based
3. **Entitlement check**: Adapted from boolean to object property
4. **Manifest structure**: Prepared for potential differences in chunk structure

### Reusable Patterns

These patterns from Fab should apply to **any** marketplace:

1. Asset adapter implementing `SourceAsset` protocol
2. Source class with lazy-loaded collection
3. Transformer with placeholder (Phase 2) and manifest parsing (Phase 3)
4. Gated import with auto-registration
5. Factory function accepting client + kwargs
6. Progress feedback to stderr

---

## Summary

Phase 5 provides a complete template for UAS integration that:

**Validates the architecture**:
- ✅ Multiple marketplaces work side-by-side
- ✅ Platform modularity proven
- ✅ Registry pattern scales

**Serves as a template**:
- ✅ Shows platform-specific adaptations
- ✅ Maintains consistency with Fab
- ✅ Documents key differences

**Enables future integrations**:
- ✅ Other marketplaces can follow same pattern
- ✅ Steam Workshop, Sketchfab, ArtStation, etc.
- ✅ Clear guide for adding new platforms

**Estimated effort**: 2-3 days (following Fab pattern closely)

**Key deliverables**:
- ✅ Complete UAS source implementation
- ✅ Complete UAS transformer implementation
- ✅ Testing strategy and templates
- ✅ Example usage scripts
- ✅ Validation checklist

This completes the comprehensive documentation for all planned phases!
