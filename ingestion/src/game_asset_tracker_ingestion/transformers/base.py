"""Base transformer class for converting source data to manifests.

This module defines the base interface for transformers that convert
source-specific data into game-asset-tracker JSON manifests.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import Manifest
    from ..sources.base import AssetData, SourceAsset


class Transformer(ABC):
    """Abstract base class for data transformers.
    
    Transformers convert source-specific data (AssetData) into
    standardized game-asset-tracker manifests that conform to
    the JSON schema.
    """
    
    @abstractmethod
    def transform(
        self,
        asset: "SourceAsset",
        data: "AssetData",
        pack_name: str | None = None,
        **kwargs
    ) -> "Manifest":
        """Transform source data into a manifest.
        
        Args:
            asset: The source asset being transformed
            data: Raw data from the source
            pack_name: Optional override for pack name (defaults to asset.title)
            **kwargs: Additional transformation parameters
            
        Returns:
            Manifest dictionary conforming to the JSON schema
            
        Raises:
            Exception: If transformation fails
        """
        pass
