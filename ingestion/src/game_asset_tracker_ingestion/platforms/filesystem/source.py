"""Filesystem source adapter.

This module provides a Source implementation for scanning
local filesystem directories and generating manifests.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from ...core.metadata import extract_metadata
from ...core.types import Asset
from ...sources.base import AssetData, Source, SourceAsset

# Maximum length for metadata strings to prevent DoS
MAX_METADATA_STRING_LENGTH = 2048

# Dangerous characters to remove from filenames
DANGEROUS_FILENAME_CHARS = r'[<>:\"|?*\x00-\x1f]'


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for storage
    """
    # Remove dangerous characters
    sanitized = re.sub(DANGEROUS_FILENAME_CHARS, "", filename)
    # Remove path separators
    sanitized = sanitized.replace("/", "").replace("\\", "")
    return sanitized


def validate_path_safety(path: Path, base_dir: Path) -> None:
    """Validate that a path stays within the base directory.

    This prevents path traversal attacks.

    Args:
        path: Path to validate
        base_dir: Base directory that path must be within

    Raises:
        ValueError: If path escapes the base directory
    """
    resolved_path = path.resolve()
    resolved_base = base_dir.resolve()

    if not resolved_path.is_relative_to(resolved_base):
        raise ValueError(f"Path {path} escapes base directory {base_dir}")


def validate_url(url: str) -> None:
    """Validate URL format and scheme.

    Only allows http:// and https:// schemes.

    Args:
        url: URL to validate

    Raises:
        ValueError: If URL has invalid format or dangerous scheme
    """
    if not url:  # Empty string is allowed
        return

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https", ""):
        raise ValueError(
            f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed."
        )


def derive_local_tags(relative_path: Path) -> list[str]:
    """Derive tags from the folder structure.

    Example:
        "Audio/Explosions/SciFi/boom.wav" -> ["Audio", "Explosions", "SciFi"]

    Args:
        relative_path: Path relative to pack root

    Returns:
        List of tags derived from folder names (excludes filename)
    """
    path_parts = relative_path.parts
    # Exclude the filename itself, only use directory names
    return list(path_parts[:-1]) if len(path_parts) > 1 else []


@dataclass
class FilesystemAsset:
    """Simple asset representation for filesystem directories.
    
    This acts as a SourceAsset for the filesystem platform.
    """
    
    uid: str
    title: str
    path: Path


class FilesystemSource(Source):
    """Source adapter for filesystem directories.
    
    This implementation scans local directories and provides
    file metadata for manifest generation.
    
    Example:
        >>> source = FilesystemSource(Path('/path/to/assets'))
        >>> assets = source.list_assets()
        >>> data = source.get_asset_data(assets[0])
    """
    
    def __init__(self, path: Path):
        """Initialize filesystem source.
        
        Args:
            path: Root directory to scan
            
        Raises:
            ValueError: If path doesn't exist or isn't a directory
        """
        self.path = path.resolve()
        
        if not self.path.exists():
            raise ValueError(f"Path does not exist: {self.path}")
        
        if not self.path.is_dir():
            raise ValueError(f"Path is not a directory: {self.path}")
    
    def list_assets(self) -> list[SourceAsset]:
        """List available assets.
        
        For filesystem sources, there's only one "asset" - the directory itself.
        
        Returns:
            List containing a single FilesystemAsset representing the directory
        """
        return [
            FilesystemAsset(
                uid=str(self.path),
                title=self.path.name,
                path=self.path,
            )
        ]
    
    def get_asset(self, uid: str) -> SourceAsset:
        """Get a specific asset by UID.
        
        For filesystem sources, the UID is the path string.
        
        Args:
            uid: The path string
            
        Returns:
            FilesystemAsset for the directory
            
        Raises:
            KeyError: If UID doesn't match the directory path
        """
        if uid == str(self.path):
            return FilesystemAsset(
                uid=uid,
                title=self.path.name,
                path=self.path,
            )
        raise KeyError(f"No asset found with UID: {uid}")
    
    def get_asset_data(self, asset: SourceAsset, download: bool = False) -> AssetData:
        """Get asset data by scanning the directory.
        
        Args:
            asset: The filesystem asset to scan
            download: Ignored for filesystem sources (no downloads needed)
            
        Returns:
            AssetData containing scanned files
        """
        # Scan the directory
        files = self._scan_directory(self.path)
        
        return AssetData(
            asset=asset,
            files=[
                {
                    "relative_path": f["relative_path"],
                    "file_type": f["file_type"],
                    "size_bytes": f["size_bytes"],
                    "metadata": f["metadata"],
                    "local_tags": f["local_tags"],
                }
                for f in files
            ],
        )
    
    def _scan_directory(self, root_path: Path) -> list[Asset]:
        """Recursively scan a directory and collect asset metadata.

        Args:
            root_path: Absolute path to the pack root directory

        Returns:
            List of asset dictionaries conforming to the schema
        """
        assets: list[Asset] = []
        root_path_resolved = root_path.resolve()

        # Walk the directory tree
        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                # Skip hidden files and system files
                if filename.startswith("."):
                    continue

                file_path = Path(dirpath) / filename

                try:
                    # Validate path safety
                    validate_path_safety(file_path, root_path_resolved)

                    # Get file stats
                    stat_info = file_path.stat()
                    size_bytes = stat_info.st_size

                    # Calculate relative path
                    relative_path = file_path.relative_to(root_path_resolved)

                    # Extract file extension (lowercase)
                    file_type = file_path.suffix.lstrip(".").lower()
                    if not file_type:
                        file_type = "unknown"

                    # Derive local tags from folder structure
                    local_tags = derive_local_tags(relative_path)

                    # Extract format-specific metadata
                    metadata = extract_metadata(file_path, file_type)

                    # Truncate metadata strings if too long
                    for key in list(metadata.keys()):
                        value = metadata[key]  # type: ignore[literal-required]
                        if len(value) > MAX_METADATA_STRING_LENGTH:
                            metadata[key] = value[  # type: ignore[literal-required]
                                :MAX_METADATA_STRING_LENGTH
                            ]

                    # Build asset dictionary
                    asset = Asset(
                        relative_path=str(relative_path),
                        file_type=file_type,
                        size_bytes=size_bytes,
                        metadata=metadata,
                        local_tags=local_tags,
                    )

                    assets.append(asset)

                except Exception as e:
                    # Log error to stderr but continue processing
                    print(f"Warning: Failed to process {file_path}: {e}", file=sys.stderr)
                    continue

        return assets
