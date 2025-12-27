"""UAS (Unity Asset Store) marketplace source implementation.

This module provides a Source adapter for the UAS marketplace
using the uas-api-client library.
"""

import sys
from typing import Optional

from uas_api_client import UnityAsset, UnityClient, UnityCollection

from ...sources.base import AssetData, Source, SourceAsset
from ...transformers.base import Transformer


class UASAssetAdapter:
    """Adapter that makes UnityAsset compatible with SourceAsset protocol.
    
    This wraps a uas_api_client.UnityAsset and provides the interface expected
    by the pipeline.
    """
    
    def __init__(self, unity_asset: UnityAsset):
        self._asset = unity_asset
    
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
        return "uas"
    
    @property
    def raw_asset(self) -> UnityAsset:
        """Access to underlying Unity asset for transformation."""
        return self._asset


class UASSource(Source):
    """Source implementation for UAS (Unity Asset Store) marketplace.
    
    This source adapter wraps a UnityClient and provides asset listing
    and retrieval functionality conforming to the Source interface.
    
    Phase 2: Metadata-only mode. Does not download packages or manifests.
    
    Example:
        >>> from uas_api_client import UnityClient, BearerTokenAuthProvider
        >>> from uas_adapter import UnityHubAuth
        >>> from uas_adapter.extractors import ElectronExtractor
        >>> 
        >>> # Extract tokens from Unity Hub
        >>> extractor = ElectronExtractor()
        >>> tokens = extractor.extract_tokens()
        >>> auth = UnityHubAuth(
        ...     access_token=tokens['accessToken'],
        ...     access_token_expiration=tokens['accessTokenExpiration'],
        ...     refresh_token=tokens['refreshToken']
        ... )
        >>> 
        >>> client = UnityClient(auth)
        >>> source = UASSource(client)
        >>> assets = source.list_assets()
    """
    
    def __init__(self, client: UnityClient):
        """Initialize UAS source with authenticated client.
        
        Args:
            client: Authenticated UnityClient instance. Users typically obtain
                   this via uas-adapter token extraction followed by
                   UnityClient(auth=auth_provider).
        """
        self.client = client
        self._collection: Optional[UnityCollection] = None
        
        # Create transformer instance for this source
        from .transformer import UASTransformer
        self._transformer = UASTransformer()
    
    def _get_collection(self) -> UnityCollection:
        """Lazy-load user's owned assets collection.
        
        Returns:
            User's UAS collection with all owned assets
            
        Raises:
            UnityAPIError: If API call fails
        """
        if self._collection is None:
            print("Fetching UAS owned assets...", file=sys.stderr)
            self._collection = self.client.get_collection()
            print(f"Found {len(self._collection.assets)} assets in collection", file=sys.stderr)
        return self._collection
    
    def list_assets(self) -> list[SourceAsset]:
        """List all assets in user's UAS collection.
        
        Returns:
            List of SourceAsset wrappers around Unity assets
            
        Raises:
            UnityAPIError: If API call fails
        """
        collection = self._get_collection()
        
        return [UASAssetAdapter(unity_asset) for unity_asset in collection.assets]
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve a specific asset by UID.
        
        Args:
            uid: Unity asset package ID
            
        Returns:
            SourceAsset wrapper around the Unity asset
            
        Raises:
            KeyError: If asset not found in collection
            UnityAPIError: If API call fails
        """
        collection = self._get_collection()
        
        # Search collection for matching asset
        for unity_asset in collection.assets:
            if unity_asset.uid == uid:
                return UASAssetAdapter(unity_asset)
        
        raise KeyError(f"Asset {uid} not found in UAS collection")
    
    def get_asset_data(
        self,
        asset: SourceAsset,
        download: bool = False
    ) -> AssetData:
        """Get data for transformation.
        
        Phase 2: Returns only metadata (download=False)
        Phase 3: Would download and parse package (download=True) - not yet implemented
        
        Args:
            asset: SourceAsset to retrieve data for
            download: If True, would download package (not yet implemented)
            
        Returns:
            AssetData with Unity asset metadata
            
        Raises:
            ValueError: If asset is not a UASAssetAdapter
            NotImplementedError: If download=True (Phase 3 not yet implemented)
        """
        if not isinstance(asset, UASAssetAdapter):
            raise ValueError(
                f"Expected UASAssetAdapter, got {type(asset).__name__}"
            )
        
        if download:
            # Phase 3: Would download and parse encrypted .unitypackage
            raise NotImplementedError(
                "Download mode not yet implemented for UAS. "
                "Phase 3 will require uas-adapter decryption integration."
            )
        
        unity_asset = asset.raw_asset
        
        # Phase 2: Return metadata only
        return AssetData(
            asset=asset,
            metadata={'unity_asset': unity_asset},
            files=[],
            parsed_manifest=None,
        )
    
    def get_transformer(self) -> Transformer:
        """Get the transformer for this source.
        
        Returns:
            UASTransformer instance
        """
        return self._transformer
