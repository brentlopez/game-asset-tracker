"""Core utilities for manifest generation.

This package contains schema validation, type definitions,
and metadata extraction utilities that are used across
all platform implementations.
"""

from .metadata import extract_metadata
from .types import Asset, AssetMetadata, Manifest
from .validator import validate_manifest, validate_manifest_with_error_details

__all__ = [
    "Asset",
    "AssetMetadata",
    "Manifest",
    "extract_metadata",
    "validate_manifest",
    "validate_manifest_with_error_details",
]
