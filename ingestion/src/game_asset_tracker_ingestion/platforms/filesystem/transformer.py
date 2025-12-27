"""Filesystem transformer for manifest generation.

This module converts scanned filesystem data into
game-asset-tracker JSON manifests.
"""

import uuid

from ...core.types import Manifest
from ...sources.base import AssetData, SourceAsset
from ...transformers.base import Transformer


class FilesystemTransformer(Transformer):
    """Transformer for filesystem sources.
    
    Converts scanned file data into manifests conforming to
    the game-asset-tracker JSON schema.
    """
    
    def transform(
        self,
        asset: SourceAsset,
        data: AssetData,
        pack_name: str | None = None,
        **kwargs
    ) -> Manifest:
        """Transform filesystem data into a manifest.
        
        Args:
            asset: The source asset (filesystem directory)
            data: Scanned file data
            pack_name: Optional override for pack name
            **kwargs: Additional parameters from CLI (source, tags, license_link)
            
        Returns:
            Manifest dictionary conforming to the JSON schema
        """
        # Extract CLI parameters from kwargs
        source = kwargs.get('source', 'Filesystem')
        global_tags = kwargs.get('global_tags', [])
        license_link = kwargs.get('license_link', '')
        root_path = kwargs.get('root_path', '')
        
        # Generate manifest
        manifest: Manifest = {
            'pack_id': str(uuid.uuid4()),
            'pack_name': pack_name or asset.title,
            'root_path': root_path,
            'source': source,
            'license_link': license_link,
            'global_tags': global_tags,
            'assets': data.files,  # type: ignore[typeddict-item]
        }
        
        return manifest
