"""Base abstractions for source adapters.

This module defines the core interfaces and data structures that all
source adapters must implement to integrate with the ingestion pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceAsset(Protocol):
    """Protocol for assets from any source.
    
    Any object with a uid and title can act as a SourceAsset.
    This allows marketplace assets, filesystem directories, etc.
    to all be treated uniformly by the pipeline.
    
    Attributes:
        uid: Unique identifier for the asset
        title: Human-readable name/title
    """
    
    uid: str
    title: str


@dataclass
class AssetData:
    """Container for raw data retrieved from a source.
    
    This holds the raw information that will be transformed into
    a game-asset-tracker manifest. The structure is flexible to
    accommodate different source types.
    
    Attributes:
        asset: The source asset this data belongs to
        files: List of file metadata (for filesystem sources)
        metadata: Additional metadata dictionary
        parsed_manifest: Optional parsed manifest (for marketplace sources)
    """
    
    asset: SourceAsset
    files: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    parsed_manifest: Any = None  # Platform-specific manifest type


class Source(ABC):
    """Abstract base class for all data sources.
    
    Implementations provide platform-specific logic for retrieving
    assets and their data, while adhering to this common interface.
    
    This enables the pipeline to work with any source type without
    knowing the implementation details.
    """
    
    @abstractmethod
    def list_assets(self) -> list[SourceAsset]:
        """List all available assets from this source.
        
        Returns:
            List of assets available from this source
            
        Raises:
            Exception: If listing fails
        """
        pass
    
    @abstractmethod
    def get_asset(self, uid: str) -> SourceAsset:
        """Retrieve a specific asset by UID.
        
        Args:
            uid: Unique identifier for the asset
            
        Returns:
            The requested asset
            
        Raises:
            KeyError: If asset not found
            Exception: If retrieval fails
        """
        pass
    
    @abstractmethod
    def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
        """Get raw data for transformation.
        
        Args:
            asset: The asset to get data for
            download: Whether to download additional data (manifests, files, etc.)
            
        Returns:
            AssetData containing all information needed for transformation
            
        Raises:
            Exception: If data retrieval fails
        """
        pass
