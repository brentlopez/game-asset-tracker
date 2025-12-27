"""Fab marketplace platform integration.

This module provides Fab marketplace support for the ingestion pipeline.
It automatically registers with SourceRegistry if fab-api-client is available.

Usage:
    >>> from game_asset_tracker_ingestion import SourceRegistry
    >>> 
    >>> # Check if Fab support is available
    >>> if 'fab' in SourceRegistry.list_sources():
    ...     # Create pipeline
    ...     from fab_api_client import FabClient
    ...     from fab_egl_adapter import FabEGLAdapter
    ...     
    ...     adapter = FabEGLAdapter()
    ...     auth_provider = adapter.get_auth_provider()
    ...     client = FabClient(auth=auth_provider)
    ...     
    ...     pipeline = SourceRegistry.create_pipeline('fab', client=client)
    ...     
    ...     # Generate manifests
    ...     for manifest in pipeline.generate_manifests():
    ...         print(f"Generated manifest for {manifest['pack_name']}")
"""

# Gated import: Only load if fab-api-client is installed
try:
    from fab_api_client import Asset as FabAsset
    from fab_api_client import FabClient
    from fab_api_client import Library
    
    # Import our implementations
    from .source import FabAssetAdapter, FabSource
    from .transformer import FabTransformer
    
    # Import registry for auto-registration
    from ...registry import SourceRegistry
    
    # Factory function for creating FabSource instances
    def _create_fab_source(client: FabClient, **kwargs) -> FabSource:  # type: ignore[valid-type]
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
    FabSource = None  # type: ignore[assignment,misc]
    FabAssetAdapter = None  # type: ignore[assignment,misc]
    FabTransformer = None  # type: ignore[assignment,misc]
    
    __all__ = ['FAB_AVAILABLE']
