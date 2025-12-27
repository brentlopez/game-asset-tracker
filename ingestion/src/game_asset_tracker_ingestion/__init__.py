"""Game Asset Tracker - Ingestion Module.

This package provides a unified transformation library that can ingest data
from multiple sources (filesystem, marketplaces) and output standardized
JSON manifests for import into the Asset Tracking System.
"""

# Core library interface
from .pipeline import IngestionPipeline
from .registry import SourceRegistry
from .sources.base import AssetData, Source, SourceAsset

# Core utilities
from .core import Asset, AssetMetadata, Manifest, extract_metadata
from .core import validate_manifest, validate_manifest_with_error_details

# Legacy CLI interface (backward compatibility)
from .cli import generate_manifest, main

# Filesystem platform utilities
from .platforms.filesystem import sanitize_filename, validate_path_safety, validate_url

__version__ = "0.1.0"

# Auto-discover and register all platforms
SourceRegistry.discover_platforms()

__all__ = [
    # Primary library interface
    "IngestionPipeline",
    "SourceRegistry",
    "Source",
    "SourceAsset",
    "AssetData",
    # Core utilities
    "Asset",
    "AssetMetadata",
    "Manifest",
    "extract_metadata",
    "validate_manifest",
    "validate_manifest_with_error_details",
    # Backward compatibility (CLI and old functions)
    "generate_manifest",
    "main",
    "sanitize_filename",
    "validate_path_safety",
    "validate_url",
]
