# INGESTION KNOWLEDGE BASE

**Scope:** Python CLI that scans asset sources → JSON manifests

## OVERVIEW

Sources→Transformers→Pipeline→Registry architecture. Python 3.11+, uv+hatchling, strict MyPy.

## STRUCTURE

```
src/game_asset_tracker_ingestion/
├── core/           # types.py, metadata.py, validator.py
├── platforms/      # filesystem/, fab/, uas/ - each has source.py + transformer.py
├── sources/        # base.py - BaseSource protocol
├── transformers/   # base.py - BaseTransformer protocol
├── cli.py          # Entry point
├── pipeline.py     # Orchestration
└── registry.py     # Source/transformer registration
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add new platform | `platforms/newname/` with `source.py`, `transformer.py`, `__init__.py` |
| Modify asset metadata | `core/types.py` (AssetInfo, PackInfo) |
| Change tag extraction | `core/metadata.py` (heuristic_tags_from_path) |
| Audio metadata | `core/metadata.py` (uses mutagen) |
| CLI commands | `cli.py` |
| Schema validation | `core/validator.py` |

## CONVENTIONS

- **Protocols over ABC** - BaseSource/BaseTransformer are Protocols
- **Heuristic tagging** - folder names become tags automatically
- **Schema strict** - jsonschema validates all output
- **Optional deps** - fab/uas behind extras, graceful degradation

## ADDING A NEW PLATFORM

1. Create `platforms/newname/__init__.py`, `source.py`, `transformer.py`
2. Source implements `scan() -> Iterator[RawAssetData]`
3. Transformer implements `transform(raw) -> AssetInfo`
4. Register in `registry.py`
5. Add tests in `tests/test_newname_platform.py`

## ANTI-PATTERNS

| NEVER | Instead |
|-------|---------|
| Import optional deps at top level | Lazy import inside functions |
| Skip schema validation | Always validate before write |
| Hardcode paths | Use pathlib, accept root arg |
| Ignore file extensions | Lowercase + validate against known types |

## COMMANDS

```bash
uv sync                    # install deps
uv sync --extra fab        # with Fab marketplace
uv sync --extra uas        # with UAS
uv sync --extra all        # everything

uv run ingest --help       # CLI usage
uv run pytest              # tests (90%+ coverage expected)
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy .              # type check (strict)
```

## TESTING

- pytest with `pytest-cov`
- Mock classes for protocols (avoid real API calls)
- `@pytest.mark.skipif` for optional dep tests
- Schema validation in test assertions
