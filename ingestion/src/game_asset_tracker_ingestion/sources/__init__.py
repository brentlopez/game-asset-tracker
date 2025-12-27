"""Source adapters for the ingestion pipeline.

This package contains base classes and interfaces for source adapters.
Platform-specific implementations live in the platforms/ directory.
"""

from .base import AssetData, Source, SourceAsset

__all__ = ["Source", "SourceAsset", "AssetData"]
