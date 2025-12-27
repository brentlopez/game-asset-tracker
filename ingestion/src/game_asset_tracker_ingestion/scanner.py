"""Directory scanning and asset collection.

This module handles filesystem traversal and asset metadata collection
with security features like path validation.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from .metadata import extract_metadata
from .types import Asset

# Maximum length for metadata strings to prevent DoS
MAX_METADATA_STRING_LENGTH = 2048

# Dangerous characters to remove from filenames
DANGEROUS_FILENAME_CHARS = r'[<>:"|?*\x00-\x1f]'


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
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed.")


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


def scan_directory(root_path: Path) -> list[Asset]:
    """Recursively scan a directory and collect asset metadata.

    Args:
        root_path: Absolute path to the pack root directory

    Returns:
        List of asset dictionaries conforming to the schema

    Raises:
        ValueError: If path validation fails
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
                        metadata[key] = value[:MAX_METADATA_STRING_LENGTH]  # type: ignore[literal-required]

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
