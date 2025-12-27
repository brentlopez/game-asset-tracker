"""Fab marketplace transformer implementation.

Converts Fab assets to game-asset-tracker manifest format.
"""

import uuid
from typing import Optional

from fab_api_client import Asset as FabAsset

from ...core.types import Asset as ManifestAsset
from ...core.types import Manifest
from ...sources.base import AssetData, SourceAsset
from ...transformers.base import Transformer


class FabTransformer(Transformer):
    """Transformer for Fab marketplace assets.
    
    Converts Fab Asset objects into game-asset-tracker manifests.
    
    Phase 2: Metadata-only transformation. Creates a single placeholder
    asset entry with marketplace metadata. No individual files.
    
    Phase 3: Will parse manifests and create entries for individual files.
    """
    
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: Optional[str] = None,
        **kwargs
    ) -> Manifest:
        """Transform Fab asset data into manifest.
        
        Args:
            asset: The source asset being transformed
            data: AssetData from FabSource containing Fab asset
            pack_name: Optional override for pack name (default: asset title)
            **kwargs: Additional arguments (global_tags, license_link, etc.)
            
        Returns:
            Manifest conforming to schema
            
        Raises:
            ValueError: If data doesn't contain Fab asset
        """
        # Extract Fab asset from metadata
        fab_asset: FabAsset = data.metadata.get('fab_asset')
        if not fab_asset:
            raise ValueError("AssetData missing 'fab_asset' in metadata")
        
        # Generate pack-level metadata
        pack_id = str(uuid.uuid4())
        
        # Use provided pack_name or fallback to asset title
        final_pack_name = pack_name or asset.title
        
        # Extract license from listing if not provided
        license_link = kwargs.get('license_link')
        if license_link is None and hasattr(fab_asset, 'listing'):
            if hasattr(fab_asset.listing, 'license_url'):
                license_link = fab_asset.listing.license_url or ""
        
        # Default to empty string if still None
        license_link = license_link or ""
        
        # Global tags (empty for now, TODO: extract from listing categories)
        global_tags = kwargs.get('global_tags', [])
        
        # Phase 2: Create single placeholder asset entry
        # This represents the marketplace asset as a whole
        placeholder_asset = self._create_placeholder_asset(fab_asset)
        
        # Build manifest
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': 'N/A',  # Marketplace assets have no local path (schema requires non-empty)
            'source': 'Fab - Epic Games',
            'license_link': license_link,
            'global_tags': global_tags,
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
            try:
                metadata['granted_licenses'] = str(len(fab_asset.granted_licenses))
            except TypeError:
                # Handle cases where granted_licenses is not a list/sequence
                metadata['granted_licenses'] = str(fab_asset.granted_licenses)
        
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
