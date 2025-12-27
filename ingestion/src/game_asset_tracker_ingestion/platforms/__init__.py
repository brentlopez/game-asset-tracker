"""Platform implementations for the ingestion pipeline.

This package contains self-contained platform modules that
provide source and transformer implementations for different
data sources (filesystem, marketplaces, etc.).

Each platform module auto-registers itself with the SourceRegistry
when imported.
"""

# Platform modules are imported dynamically by SourceRegistry.discover_platforms()
# to handle missing dependencies gracefully
