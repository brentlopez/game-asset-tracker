"""Ingestion pipeline for manifest generation.

This module provides the main interface for generating manifests
from various sources. The pipeline is platform-agnostic and delegates
to source-specific implementations.
"""

from collections.abc import Iterator
from typing import Callable

from .core.types import Manifest
from .sources.base import Source, SourceAsset


class IngestionPipeline:
    """Main interface for manifest generation.
    
    This class is platform-agnostic. It works with any Source implementation
    and delegates transformation to the source's associated transformer.
    
    Sources register themselves via SourceRegistry and can be instantiated
    through factory functions.
    
    Example:
        >>> # Via registry (recommended)
        >>> from game_asset_tracker_ingestion import SourceRegistry
        >>> pipeline = SourceRegistry.create_pipeline('filesystem', path=Path('/assets'))
        >>> 
        >>> # Direct instantiation (advanced)
        >>> from game_asset_tracker_ingestion.platforms.filesystem import FilesystemSource
        >>> source = FilesystemSource(Path('/assets'))
        >>> pipeline = IngestionPipeline(source)
    """
    
    def __init__(self, source: Source, download_strategy: str = 'metadata_only'):
        """Initialize the pipeline.
        
        Args:
            source: Source instance to retrieve data from
            download_strategy: Strategy for downloading additional data.
                             Options: 'metadata_only', 'manifests_only'
        """
        self.source = source
        self.download_strategy = download_strategy
    
    def generate_manifests(
        self,
        filter_fn: Callable[[SourceAsset], bool] | None = None,
        limit: int | None = None,
    ) -> Iterator[Manifest]:
        """Generate manifests for assets from the source.
        
        By default (Option A), generates one manifest per asset.
        Users can filter assets (Option C) for more control.
        
        Args:
            filter_fn: Optional filter function to select specific assets
            limit: Optional limit on number of manifests to generate
            
        Yields:
            Manifest dictionaries conforming to the JSON schema
            
        Example:
            >>> # Generate all manifests
            >>> for manifest in pipeline.generate_manifests():
            ...     print(manifest['pack_name'])
            >>> 
            >>> # Filter specific assets (Option C)
            >>> for manifest in pipeline.generate_manifests(
            ...     filter_fn=lambda a: 'character' in a.title.lower()
            ... ):
            ...     print(manifest['pack_name'])
        """
        # Get all available assets
        assets = self.source.list_assets()
        
        # Apply filtering if provided (Option C behavior)
        if filter_fn:
            assets = [asset for asset in assets if filter_fn(asset)]
        
        # Apply limit if provided
        if limit:
            assets = assets[:limit]
        
        # Generate one manifest per asset (Option A behavior)
        for asset in assets:
            yield self.generate_manifest_for_asset(asset)
    
    def generate_manifest_for_asset(
        self,
        asset: SourceAsset,
        pack_name: str | None = None,
        **kwargs
    ) -> Manifest:
        """Generate manifest for a single asset.
        
        This provides granular control (Option C) for processing
        individual assets.
        
        Args:
            asset: The asset to generate a manifest for
            pack_name: Optional override for pack name (defaults to asset.title)
            **kwargs: Additional parameters passed to transformer
            
        Returns:
            Manifest dictionary conforming to the JSON schema
            
        Example:
            >>> asset = pipeline.source.get_asset('specific-uid')
            >>> manifest = pipeline.generate_manifest_for_asset(
            ...     asset,
            ...     pack_name="Custom Name"
            ... )
        """
        # Determine if we should download based on strategy
        should_download = self.download_strategy != 'metadata_only'
        
        # Get data from source
        data = self.source.get_asset_data(asset, download=should_download)
        
        # Get the source's transformer and use it to transform
        transformer = self.source.get_transformer()
        return transformer.transform(asset, data, pack_name=pack_name, **kwargs)
