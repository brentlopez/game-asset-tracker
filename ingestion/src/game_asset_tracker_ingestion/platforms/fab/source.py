"""Fab marketplace source implementation.

This module provides a Source adapter for the Fab marketplace (Epic Games)
using the fab-api-client library.
"""

import sys
from typing import Optional

from fab_api_client import Asset as FabAsset
from fab_api_client import FabClient
from fab_api_client import Library

from ...sources.base import AssetData, Source, SourceAsset
from ...transformers.base import Transformer


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
        >>> assets = source.list_assets()
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
        
        # Create transformer instance for this source
        from .transformer import FabTransformer
        self._transformer = FabTransformer()
    
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
    
    def list_assets(self) -> list[SourceAsset]:
        """List all assets in user's Fab library.
        
        Returns:
            List of SourceAsset wrappers around Fab assets
            
        Raises:
            FabAPIError: If API call fails
        """
        library = self._get_library()
        
        return [FabAssetAdapter(fab_asset) for fab_asset in library.assets]
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve a specific asset by UID.
        
        Args:
            uid: Fab asset UID
            
        Returns:
            SourceAsset wrapper around the Fab asset
            
        Raises:
            KeyError: If asset not found in library
            FabAPIError: If API call fails
        """
        library = self._get_library()
        
        # Search library for matching asset
        for fab_asset in library.assets:
            if fab_asset.uid == uid:
                return FabAssetAdapter(fab_asset)
        
        raise KeyError(f"Asset {uid} not found in Fab library")
    
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
            asset=asset,  # Actual field name (not source_asset)
            metadata={
                'fab_asset': asset.raw_asset,  # Store raw asset for transformer
            },
            files=[],  # No files in metadata-only mode
            parsed_manifest=None,  # Actual field name (not manifest)
        )
    
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source.
        
        Returns:
            FabTransformer instance
        """
        return self._transformer
