"""Type definitions for game asset tracking manifests.

This module defines TypedDict classes that mirror the JSON schema structure
defined in schemas/manifest.schema.json.
"""

from typing import TypedDict


class AssetMetadata(TypedDict, total=False):
    """Flexible key-value pairs for file-specific metadata.

    Examples: duration, sample_rate, bitrate, channels, dimensions, poly_count
    All values must be strings as per schema.
    """


class Asset(TypedDict):
    """Individual asset file within a pack."""

    relative_path: str  # Path relative to pack root
    file_type: str  # File extension (lowercase, e.g., 'png', 'wav', 'fbx')
    size_bytes: int  # File size in bytes
    metadata: AssetMetadata  # Format-specific metadata
    local_tags: list[str]  # Tags derived from folder structure


class Manifest(TypedDict):
    """Complete manifest for an asset pack."""

    pack_id: str  # UUID in lowercase hyphenated format
    pack_name: str  # Human-readable name
    root_path: str  # Absolute path to pack root
    source: str  # Origin (e.g., "Unity Asset Store", "Epic Marketplace")
    license_link: str  # URL or path to license documentation
    global_tags: list[str]  # Tags for entire pack
    assets: list[Asset]  # Individual asset files
