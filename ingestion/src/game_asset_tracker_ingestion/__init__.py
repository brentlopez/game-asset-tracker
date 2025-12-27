"""Game Asset Tracker - Ingestion Module.

This package provides tools for scanning game asset directories and generating
standardized JSON manifests for import into the Asset Tracking System.
"""

from .cli import generate_manifest, main
from .metadata import extract_metadata
from .scanner import scan_directory, validate_path_safety, validate_url
from .types import Asset, AssetMetadata, Manifest
from .validator import validate_manifest, validate_manifest_with_error_details

__version__ = "0.1.0"

__all__ = [
    "generate_manifest",
    "main",
    "extract_metadata",
    "scan_directory",
    "validate_path_safety",
    "validate_url",
    "Asset",
    "AssetMetadata",
    "Manifest",
    "validate_manifest",
    "validate_manifest_with_error_details",
]
