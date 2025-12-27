"""UAS (Unity Asset Store) marketplace platform integration.

This module provides UAS marketplace support for the ingestion pipeline.
It automatically registers with SourceRegistry if uas-api-client is available.

Usage:
    >>> from game_asset_tracker_ingestion import SourceRegistry
    >>> 
    >>> # Check if UAS support is available
    >>> if 'uas' in SourceRegistry.list_sources():
    ...     # Create pipeline
    ...     from uas_api_client import UnityClient
    ...     from uas_adapter import UnityHubAuth
    ...     from uas_adapter.extractors import ElectronExtractor
    ...     
    ...     extractor = ElectronExtractor()
    ...     tokens = extractor.extract_tokens()
    ...     auth = UnityHubAuth(
    ...         access_token=tokens['accessToken'],
    ...         access_token_expiration=tokens['accessTokenExpiration'],
    ...         refresh_token=tokens['refreshToken']
    ...     )
    ...     client = UnityClient(auth)
    ...     
    ...     pipeline = SourceRegistry.create_pipeline('uas', client=client)
    ...     
    ...     # Generate manifests
    ...     for manifest in pipeline.generate_manifests():
    ...         print(f"Generated manifest for {manifest['pack_name']}")
"""

# Gated import: Only load if uas-api-client is installed
try:
    from uas_api_client import UnityAsset, UnityClient, UnityCollection
    
    # Import our implementations
    from .source import UASAssetAdapter, UASSource
    from .transformer import UASTransformer
    
    # Import registry for auto-registration
    from ...registry import SourceRegistry
    
    # Factory function for creating UASSource instances
    def _create_uas_source(client: UnityClient, **kwargs) -> UASSource:  # type: ignore[valid-type]
        """Factory function for creating UASSource.
        
        Args:
            client: Authenticated UnityClient instance
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
    UASSource = None  # type: ignore[assignment,misc]
    UASAssetAdapter = None  # type: ignore[assignment,misc]
    UASTransformer = None  # type: ignore[assignment,misc]
    
    __all__ = ['UAS_AVAILABLE']
