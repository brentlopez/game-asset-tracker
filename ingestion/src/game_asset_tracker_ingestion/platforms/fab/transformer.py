"""Fab marketplace transformer implementation.

Converts Fab assets to game-asset-tracker manifest format.
"""

import uuid
from pathlib import Path
from typing import Optional

from fab_api_client import Asset as FabAsset

from ...core.types import Asset as ManifestAsset
from ...core.types import Manifest
from ...scanner import derive_local_tags
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
        
        # Phase 3: Check if manifest is available
        if data.parsed_manifest:
            # Parse individual files from manifest
            assets = self._parse_manifest_files(data.parsed_manifest, fab_asset)
        else:
            # Phase 2: Create single placeholder asset entry
            assets = [self._create_placeholder_asset(fab_asset)]
        
        # Build manifest
        manifest: Manifest = {
            'pack_id': pack_id,
            'pack_name': final_pack_name,
            'root_path': 'N/A',  # Marketplace assets have no local path (schema requires non-empty)
            'source': 'Fab - Epic Games',
            'license_link': license_link,
            'global_tags': global_tags,
            'assets': assets,
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
