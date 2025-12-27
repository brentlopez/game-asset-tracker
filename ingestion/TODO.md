# TODO: Future Enhancements

This document specifies planned features that are not yet implemented.
Each item includes design specifications to guide future implementation.

---

## High Priority

### 1. Advanced Filtering

**Current state**: Pipeline generates manifests for all assets

**Goal**: Allow users to filter which assets are processed

**Design**:

```python
# Example usage
def my_filter(asset: SourceAsset) -> bool:
    """Only process assets matching criteria."""
    return asset.title.startswith('Character')

pipeline = SourceRegistry.create_pipeline('fab', client=client)
manifests = pipeline.generate_manifests(
    filter_fn=my_filter,
    limit=10  # Optional: limit number of results
)
```

**Implementation notes**:

1. `filter_fn` and `limit` parameters already exist in `IngestionPipeline.generate_manifests()`
2. Current implementation filters results from `source.list_assets()`
3. Could be extended to support async filter functions
4. Could add more sophisticated filtering (e.g., query language)

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Status**: ✅ Partially implemented (basic filtering exists)

**Estimated effort**: 0.5 days (for async support and improvements)

---

### 2. Per-Source Download Strategy Override

**Current state**: Global `download_strategy` applies to all sources

**Goal**: Allow different strategies for different sources in mixed pipelines

**Design**:

```python
# Example: Download manifests for Fab, metadata-only for UAS
pipeline = MultiSourcePipeline([
    ('fab', {'client': fab_client}),
    ('uas', {'client': uas_client}),
])

manifests = pipeline.generate_manifests(
    download_overrides={
        'fab': 'manifests_only',
        'uas': 'metadata_only',
    }
)
```

**Implementation notes**:

1. Create `MultiSourcePipeline` class that wraps multiple sources
2. Accept `download_overrides` dict in `generate_manifests()`
3. Pass appropriate strategy to each source's `get_asset_data()`
4. Maintain unified iterator interface

**Code location**: New file `src/game_asset_tracker_ingestion/multi_pipeline.py`

**Estimated effort**: 2 days

---

### 3. Parallel Processing for Large Libraries

**Current state**: Sequential processing of assets

**Goal**: Speed up manifest generation with parallel processing

**Design**:

```python
pipeline = SourceRegistry.create_pipeline('fab', client=client)

# Enable parallel processing
manifests = pipeline.generate_manifests(
    parallel=True,
    max_workers=4
)
```

**Implementation notes**:

1. Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound operations
2. Add `parallel` and `max_workers` parameters
3. Maintain order of results (use `as_completed` with tracking)
4. Handle exceptions gracefully (don't fail entire batch)

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Estimated effort**: 3 days

**Considerations**:
- Thread safety of Source implementations
- Rate limiting for API sources
- Memory usage with large worker pools

---

## Medium Priority

### 4. Plugin System via Entry Points

**Current state**: Sources must be in `platforms/` directory

**Goal**: Allow third-party packages to register sources

**Design**:

**In third-party package**:

```toml
# pyproject.toml of my-steam-adapter package
[project.entry-points."game_asset_tracker_ingestion.sources"]
steam_workshop = "my_steam_adapter:create_source"
```

**In ingestion library**:

```python
# Automatic discovery
import importlib.metadata

for ep in importlib.metadata.entry_points(
    group='game_asset_tracker_ingestion.sources'
):
    source_factory = ep.load()
    SourceRegistry.register_factory(ep.name, source_factory)
```

**Implementation notes**:

1. Add entry point discovery to `SourceRegistry.discover_platforms()`
2. Support both built-in and plugin sources
3. Handle plugin loading errors gracefully
4. Add `--list-sources` CLI command to show available sources

**Code location**: `src/game_asset_tracker_ingestion/registry.py`

**Estimated effort**: 2 days

---

### 5. Configuration File Support

**Current state**: All configuration via code or CLI arguments

**Goal**: Support project-local and global configuration files

**Design**:

**Project-local config** (`.game-asset-tracker.yaml`):

```yaml
sources:
  fab:
    enabled: true
    download_strategy: manifests_only
  
  uas:
    enabled: false

output:
  directory: ./manifests
  format: json
  validate: true

filters:
  - source: fab
    condition: entitled == true
```

**Global config** (`~/.config/game-asset-tracker/config.yaml`):

Same format, project-local overrides global.

**Implementation notes**:

1. Use `PyYAML` or `tomli` for parsing
2. Load global config first, then project-local
3. Deep merge configurations
4. Add `--config` CLI flag to specify custom config file
5. Validate config against schema

**Code location**: New file `src/game_asset_tracker_ingestion/config.py`

**Estimated effort**: 3 days

---

### 6. Caching Layer

**Current state**: Re-fetch data on every run

**Goal**: Cache API responses to speed up repeated runs

**Design**:

```python
from game_asset_tracker_ingestion import SourceRegistry
from game_asset_tracker_ingestion.cache import FileCache

cache = FileCache(cache_dir='~/.cache/game-asset-tracker', ttl=3600)

pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    cache=cache
)
```

**Implementation notes**:

1. Create `Cache` ABC with `get()`, `set()`, `invalidate()` methods
2. Implement `FileCache` (pickle-based) and `MemoryCache`
3. Add cache key generation (hash of source + asset UID)
4. Add TTL (time-to-live) support
5. Add `--no-cache` CLI flag

**Code location**: New file `src/game_asset_tracker_ingestion/cache.py`

**Estimated effort**: 3 days

---

## Low Priority

### 7. Robust Marketplace Metadata Storage

**Current state**: Marketplace-specific metadata stored as strings in flexible `metadata` dict

**Problem**: Hard to query, no type safety, schema limitations

**Goal**: Structured storage for marketplace-specific fields

**Option A: Schema Extensions**

Extend JSON schema with marketplace-specific fields:

```json
{
  "pack_id": "...",
  "pack_name": "...",
  "marketplace_metadata": {
    "fab": {
      "listing_uid": "...",
      "seller": {...},
      "status": "ACTIVE"
    }
  }
}
```

**Option B: Sidecar Files**

Store complex metadata separately:

```
output/
├── abc123.json          # Standard manifest
└── abc123.meta.json     # Marketplace metadata
```

**Option C: Separate Tables (Obsidian plugin)**

Let the Obsidian plugin create marketplace-specific SQLite tables:

```sql
CREATE TABLE fab_metadata (
    pack_id TEXT PRIMARY KEY,
    listing_uid TEXT,
    seller_name TEXT,
    status TEXT,
    FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
);
```

**Recommendation**: Option C - Handle in Obsidian plugin, not ingestion library

**Estimated effort**: N/A (deferred to Obsidian plugin)

---

### 8. Resume Interrupted Downloads

**Current state**: Must restart if download interrupted

**Goal**: Resume from last successful download

**Design**:

```python
pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    resume=True,
    state_file='.ingestion-state.json'
)
```

State file stores:

```json
{
  "last_processed_uid": "asset-123",
  "timestamp": "2024-01-15T10:30:00Z",
  "completed": ["asset-1", "asset-2", ...],
  "failed": {"asset-99": "error message"}
}
```

**Implementation notes**:

1. Save state after each successful asset
2. Skip already-processed assets on resume
3. Retry failed assets with exponential backoff
4. Add `--resume` CLI flag

**Code location**: New file `src/game_asset_tracker_ingestion/state.py`

**Estimated effort**: 2 days

---

### 9. Progress Bar and Statistics

**Current state**: Minimal progress feedback

**Goal**: Rich progress display with statistics

**Design**:

```python
from game_asset_tracker_ingestion import SourceRegistry
from rich.progress import Progress

with Progress() as progress:
    pipeline = SourceRegistry.create_pipeline('fab', client=client)
    
    task = progress.add_task("Generating manifests", total=None)
    
    for manifest in pipeline.generate_manifests():
        progress.update(task, advance=1)
        # Process manifest

# Show statistics
print(f"Processed: {pipeline.stats.processed}")
print(f"Failed: {pipeline.stats.failed}")
print(f"Total size: {pipeline.stats.total_size_gb:.2f} GB")
```

**Implementation notes**:

1. Add optional `rich` dependency for progress bars
2. Add `Statistics` dataclass to track metrics
3. Emit progress events from pipeline
4. Make progress display optional (for scripting)

**Code location**: `src/game_asset_tracker_ingestion/pipeline.py`

**Estimated effort**: 2 days

---

### 10. Incremental Updates

**Current state**: Full re-scan every time

**Goal**: Only process new/changed assets

**Design**:

```python
pipeline = SourceRegistry.create_pipeline(
    'fab',
    client=client,
    incremental=True,
    state_file='.last-scan.json'
)

# Only processes assets added/modified since last scan
manifests = pipeline.generate_manifests()
```

**Implementation notes**:

1. Store asset UIDs and timestamps from last run
2. Query source for assets modified since last timestamp
3. Skip unchanged assets
4. Handle deleted assets (optional: generate deletion manifests)

**Code location**: Extend `state.py` from TODO item #8

**Estimated effort**: 3 days

---

## UAS Integration Specifics

### UAS Source Implementation

**Expected differences from Fab**:

1. **Authentication**: Uses different auth mechanism (see uas-api-client)
2. **Asset structure**: Different fields (e.g., `package_id` vs `listing_uid`)
3. **Manifest format**: May have different manifest structure
4. **License handling**: Different license URL format

**Template** (`platforms/uas/source.py`):

```python
from uas_api_client import UnityClient
from game_asset_tracker_ingestion.sources.base import Source

class UASSource(Source):
    def __init__(self, client: UnityClient):
        self.client = client
        
        from .transformer import UASTransformer
        self._transformer = UASTransformer()
    
    def list_assets(self):
        # UAS-specific implementation
        library = self.client.get_library()
        return [UASAssetAdapter(item) for item in library.results]
    
    # ... implement other methods
```

**Estimated effort**: 2 days (following Fab pattern)

**Resources**:
- [uas-api-client](https://github.com/brentlopez/uas-api-client): Unity Asset Store client library
- [asset-marketplace-client-core](https://github.com/brentlopez/asset-marketplace-client-core): Architecture patterns

---

## Implementation Priority

**Recommended order**:

1. **Advanced Filtering** (0.5 day) - High user value, partially done
2. **Plugin System** (2 days) - Enables ecosystem growth
3. **Configuration Files** (3 days) - Better UX
4. **UAS Integration** (2 days) - Validates multi-marketplace architecture
5. **Parallel Processing** (3 days) - Performance boost for large libraries
6. **Caching** (3 days) - Performance boost for repeated runs
7. **Progress/Statistics** (2 days) - Better UX
8. **Resume/Incremental** (5 days combined) - Nice to have for large operations

**Total estimated effort**: ~20.5 days for all items

---

## Contributing

When implementing these features:

1. Follow existing code patterns in `platforms/filesystem/` and `platforms/fab/`
2. Add comprehensive tests (unit + integration)
3. Update EXTENDING.md if adding new extension points
4. Update README.md with new features
5. Run `uv run ruff check` and `uv run mypy` before committing
6. Validate manifests against schema

See [EXTENDING.md](EXTENDING.md) for architecture details.
