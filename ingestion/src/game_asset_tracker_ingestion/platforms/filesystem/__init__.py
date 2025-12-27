"""Filesystem platform for the ingestion pipeline.

This platform provides filesystem scanning functionality,
allowing the ingestion pipeline to generate manifests from
local directories.
"""

from pathlib import Path

from .source import FilesystemSource, sanitize_filename, validate_path_safety, validate_url
from .transformer import FilesystemTransformer

# Auto-register with the registry
from ...registry import SourceRegistry


def _create_filesystem_source(path: Path, **kwargs) -> FilesystemSource:
    """Factory function for creating filesystem sources.
    
    Args:
        path: Root directory to scan
        **kwargs: Additional parameters (unused for filesystem)
        
    Returns:
        FilesystemSource instance
    """
    return FilesystemSource(path)


# Auto-register at module import
SourceRegistry.register_factory('filesystem', _create_filesystem_source)

__all__ = [
    "FilesystemSource",
    "FilesystemTransformer",
    "sanitize_filename",
    "validate_path_safety",
    "validate_url",
]
