"""UAS marketplace transformer implementation.

Converts Unity Asset Store assets to game-asset-tracker manifest format.
"""

import uuid
from typing import Optional

from uas_api_client import UnityAsset

from ...core.types import Asset as ManifestAsset
from ...core.types import Manifest
from ...sources.base import AssetData, SourceAsset
from ...transformers.base import Transformer


class UASTransformer(Transformer):
    """Transformer for UAS marketplace assets.
    
    Converts Unity Asset Store assets into game-asset-tracker manifests.
    
    Phase 2: Metadata-only transformation. Creates a single placeholder
    asset entry with marketplace metadata. No individual files.
    
    Phase 3: Would parse .unitypackage and create entries for individual files.
    """
    
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: Optional[str] = None,
        **kwargs
    ) -> Manifest:
        """Transform Unity asset data into manifest.
        
        Args:
            asset: The source asset being transformed
            data: AssetData from UASSource containing Unity asset
            pack_name: Optional override for pack name (default: asset title)
            **kwargs: Additional arguments (global_tags, license_link, etc.)
            
        Returns:
            Manifest conforming to schema
            
        Raises:
            ValueError: If data doesn't contain Unity asset
        """
        # Extract Unity asset from metadata
        unity_asset: UnityAsset = data.metadata.get('unity_asset')
        if not unity_asset:
            raise ValueError("AssetData missing 'unity_asset' in metadata")
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        
        # Use provided pack_name or fallback to asset title
        final_pack_name = pack_name or asset.title
        
        # License URL - UAS doesn't provide this directly
        license_link = kwargs.get('license_link', '')
        
        # Global tags (empty for now, TODO: extract from category)
        global_tags = kwargs.get('global_tags', [])
        
        # Phase 2: Create single placeholder asset entry
        # Phase 3 would parse .unitypackage for individual files
        assets = [self._create_placeholder_asset(unity_asset)]
        
        # Build manifest
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': 'N/A',  # Marketplace assets have no local path (schema requires non-empty)
            'source': 'UAS - Unity Asset Store',
            'license_link': license_link,
            'global_tags': global_tags,
            'assets': assets,
        }
        
        return manifest
    
    def _create_placeholder_asset(self, unity_asset: UnityAsset) -> ManifestAsset:
        """Create placeholder asset entry for metadata-only mode.
        
        Phase 2: Single entry representing the entire marketplace asset.
        Phase 3: Would be replaced with individual file entries from .unitypackage.
        
        Args:
            unity_asset: Unity asset to create placeholder for
            
        Returns:
            ManifestAsset with marketplace metadata
        """
        # Extract marketplace-specific metadata
        metadata: dict[str, str] = {}
        
        # Publisher information
        if unity_asset.publisher:
            metadata['publisher'] = str(unity_asset.publisher)
        
        if unity_asset.publisher_id:
            metadata['publisher_id'] = str(unity_asset.publisher_id)
        
        # Category
        if unity_asset.category:
            metadata['category'] = str(unity_asset.category)
        
        # Unity version compatibility
        if unity_asset.unity_version:
            metadata['unity_version'] = str(unity_asset.unity_version)
        
        # Pricing
        if unity_asset.price is not None:
            metadata['price'] = str(unity_asset.price)
        
        # Rating
        if unity_asset.rating is not None:
            metadata['rating'] = str(unity_asset.rating)
        
        # Package size
        if unity_asset.package_size is not None:
            metadata['package_size_bytes'] = str(unity_asset.package_size)
            # Also provide MB for convenience
            size_mb = unity_asset.get_download_size_mb()
            if size_mb is not None:
                metadata['package_size_mb'] = f"{size_mb:.2f}"
        
        # Dependencies
        if unity_asset.dependencies:
            metadata['dependencies'] = ', '.join(unity_asset.dependencies)
            metadata['dependency_count'] = str(len(unity_asset.dependencies))
        
        # Download information
        if unity_asset.download_url:
            metadata['download_available'] = 'true'
        else:
            metadata['download_available'] = 'false'
        
        if unity_asset.asset_count is not None:
            metadata['asset_count'] = str(unity_asset.asset_count)
        
        # Timestamps from BaseAsset
        if hasattr(unity_asset, 'created_at') and unity_asset.created_at:
            metadata['created_at'] = str(unity_asset.created_at)
        
        if hasattr(unity_asset, 'updated_at') and unity_asset.updated_at:
            metadata['updated_at'] = str(unity_asset.updated_at)
        
        # TODO: This metadata storage approach is temporary.
        # Future: Need more robust solution for marketplace-specific fields.
        # See docs/PHASE_4_DOCUMENTATION.md for alternatives:
        # - Schema extensions with marketplace-specific tables
        # - Sidecar JSON files for complex structured data
        # - Separate SQLite tables for queryable metadata
        
        asset: ManifestAsset = {
            'relative_path': unity_asset.title,  # Use title as pseudo-path
            'file_type': 'marketplace',  # Special type for marketplace assets
            'size_bytes': unity_asset.package_size or 0,  # Package size if available
            'metadata': metadata,
            'local_tags': [],  # No folder structure for marketplace assets
        }
        
        return asset
