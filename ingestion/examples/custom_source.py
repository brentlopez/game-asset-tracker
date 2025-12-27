"""Template for implementing a custom source.

This example demonstrates the complete pattern for creating a custom source:
- Asset adapter implementing SourceAsset protocol
- Source implementation
- Transformer implementation
- Registration with SourceRegistry

For detailed guidance, see EXTENDING.md in the project root.

Related projects:
- asset-marketplace-client-core: https://github.com/brentlopez/asset-marketplace-client-core
"""

import uuid
from typing import Any

from game_asset_tracker_ingestion import SourceRegistry
from game_asset_tracker_ingestion.sources.base import AssetData, Source, SourceAsset
from game_asset_tracker_ingestion.transformers.base import Transformer
from game_asset_tracker_ingestion.core.types import Manifest, Asset as ManifestAsset


# Step 1: Define asset adapter
class MySourceAsset:
    """Adapter that makes your asset compatible with SourceAsset protocol."""
    
    def __init__(self, data: dict[str, Any]):
        self._data = data
    
    @property
    def uid(self) -> str:
        """Unique identifier for this asset."""
        return self._data['id']
    
    @property
    def title(self) -> str:
        """Human-readable title."""
        return self._data['name']
    
    @property
    def raw_data(self) -> dict[str, Any]:
        """Access to underlying data for transformer."""
        return self._data


# Step 2: Implement Source interface
class MySource(Source):
    """Source implementation for MySource."""
    
    def __init__(self, api_url: str):
        """Initialize with configuration."""
        self.api_url = api_url
        self._transformer = MySourceTransformer()
    
    def list_assets(self) -> list[SourceAsset]:
        """List all available assets."""
        # In a real implementation, you would:
        # 1. Make API calls
        # 2. Parse responses
        # 3. Return wrapped assets
        
        # Placeholder example data
        example_assets = [
            {'id': '1', 'name': 'Asset 1', 'description': 'First asset'},
            {'id': '2', 'name': 'Asset 2', 'description': 'Second asset'},
        ]
        
        return [MySourceAsset(data) for data in example_assets]
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve specific asset by UID."""
        # In a real implementation: fetch from API
        data = {'id': uid, 'name': f'Asset {uid}'}
        return MySourceAsset(data)
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get asset data for transformation."""
        if not isinstance(asset, MySourceAsset):
            raise ValueError(f"Expected MySourceAsset, got {type(asset)}")
        
        return AssetData(
            asset=asset,
            metadata={'raw_data': asset.raw_data},
            files=[],
            parsed_manifest=None,
        )
    
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source."""
        return self._transformer


# Step 3: Implement Transformer
class MySourceTransformer(Transformer):
    """Transform MySource assets to manifests."""
    
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: str | None = None,
        **kwargs: Any
    ) -> Manifest:
        """Transform asset data to manifest."""
        raw_data = data.metadata['raw_data']
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        pack_name = pack_name or asset.title
        
        # Create asset entries
        # In a real implementation, you would extract file information
        assets: list[ManifestAsset] = [
            {
                'relative_path': 'example/file.txt',
                'file_type': 'txt',
                'size_bytes': 1024,
                'metadata': {},
                'local_tags': ['example'],
            }
        ]
        
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


# Step 4: Register with SourceRegistry
def create_my_source(api_url: str, **kwargs: Any) -> MySource:
    """Factory function for creating MySource."""
    return MySource(api_url)


# Register the source
SourceRegistry.register_factory('my_source', create_my_source)


# Step 5: Use your source
def main():
    """Example usage of custom source."""
    print("Custom Source Example")
    print("=" * 50)
    
    # Create pipeline using your source
    pipeline = SourceRegistry.create_pipeline(
        'my_source',
        api_url='https://api.example.com'
    )
    
    # Generate manifests
    print("\nGenerating manifests...")
    for manifest in pipeline.generate_manifests():
        print(f"\n✓ Generated: {manifest['pack_name']}")
        print(f"  Pack ID: {manifest['pack_id']}")
        print(f"  Files: {len(manifest['assets'])}")
        print(f"  Source: {manifest['source']}")


if __name__ == '__main__':
    main()
