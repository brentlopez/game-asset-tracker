"""Source registry for factory-based pipeline creation.

This module provides a central registry for source factories,
enabling platform-agnostic pipeline creation and automatic
platform discovery.
"""

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .pipeline import IngestionPipeline
    from .sources.base import Source


class SourceRegistry:
    """Central registry for source factories.
    
    This class manages factory functions that create source instances.
    Platforms register themselves when imported, and the registry
    can automatically discover all available platforms.
    
    This design keeps the core pipeline platform-agnostic while
    allowing dynamic platform loading.
    """
    
    _factories: dict[str, Callable[..., "Source"]] = {}
    
    @classmethod
    def register_factory(cls, name: str, factory: Callable[..., "Source"]) -> None:
        """Register a factory function for creating sources.
        
        Args:
            name: Name of the source (e.g., 'filesystem', 'fab')
            factory: Callable that creates a Source instance
            
        Example:
            >>> def create_fs_source(path: Path) -> FilesystemSource:
            ...     return FilesystemSource(path)
            >>> SourceRegistry.register_factory('filesystem', create_fs_source)
        """
        cls._factories[name] = factory
    
    @classmethod
    def create_pipeline(cls, source_name: str, **kwargs) -> "IngestionPipeline":
        """Create a pipeline from a registered source.
        
        Args:
            source_name: Name of the registered source
            **kwargs: Arguments passed to the source factory.
                     'download_strategy' is extracted and passed to pipeline.
            
        Returns:
            IngestionPipeline configured with the requested source
            
        Raises:
            ValueError: If source_name is not registered
            
        Example:
            >>> pipeline = SourceRegistry.create_pipeline(
            ...     'filesystem',
            ...     path=Path('/assets'),
            ...     download_strategy='metadata_only'
            ... )
        """
        # Import here to avoid circular dependency
        from .pipeline import IngestionPipeline
        
        if source_name not in cls._factories:
            available = ', '.join(cls._factories.keys()) or 'none'
            raise ValueError(
                f"Unknown source: '{source_name}'. Available sources: {available}"
            )
        
        # Extract download_strategy for pipeline
        download_strategy = kwargs.pop('download_strategy', 'metadata_only')
        
        # Create source via factory
        source = cls._factories[source_name](**kwargs)
        
        return IngestionPipeline(source, download_strategy)
    
    @classmethod
    def list_sources(cls) -> list[str]:
        """List all registered source names.
        
        Returns:
            List of registered source names
            
        Example:
            >>> SourceRegistry.list_sources()
            ['filesystem', 'fab']
        """
        return list(cls._factories.keys())
    
    @classmethod
    def discover_platforms(cls) -> None:
        """Auto-discover and import all platforms.
        
        This method iterates through the platforms/ directory and
        attempts to import each platform module. Platforms with
        missing dependencies are gracefully skipped.
        
        Platforms automatically register themselves when imported
        via their __init__.py files.
        """
        platforms_dir = Path(__file__).parent / 'platforms'
        
        if not platforms_dir.exists():
            return
        
        for platform_path in platforms_dir.iterdir():
            if not platform_path.is_dir():
                continue
            
            if not (platform_path / '__init__.py').exists():
                continue
            
            platform_name = platform_path.name
            
            try:
                # Import the platform module
                # This triggers auto-registration via the platform's __init__.py
                importlib.import_module(
                    f'.platforms.{platform_name}',
                    package='game_asset_tracker_ingestion'
                )
            except ImportError:
                # Platform dependencies not installed, skip silently
                pass
