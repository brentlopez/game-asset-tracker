"""Transformers for converting source data to manifests.

This package contains base classes for transformers.
Platform-specific implementations live in the platforms/ directory.
"""

from .base import Transformer

__all__ = ["Transformer"]
