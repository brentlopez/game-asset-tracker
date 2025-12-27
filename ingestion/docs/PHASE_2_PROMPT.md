# Phase 2 Implementation Prompt

Use this prompt with a future agent to implement Phase 2:

---

**Task**: Implement Fab marketplace integration for the game-asset-tracker-ingestion library following the comprehensive guide at `docs/PHASE_2_FAB_INTEGRATION.md`.

**Context**: 
- Phase 1 (core architecture) is complete
- The modular architecture is in place with Source/Transformer abstractions
- SourceRegistry uses factory pattern for platform discovery

**Deliverables**:
1. Create `platforms/fab/` directory with:
   - `source.py` - FabSource implementing Source ABC
   - `transformer.py` - FabTransformer implementing Transformer ABC
   - `__init__.py` - Gated import with auto-registration

2. Add optional dependency to `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   fab = ["fab-api-client>=2.1.0"]
   ```

3. Write comprehensive tests in `tests/test_fab_platform.py`

4. Create example script at `examples/fab_ingestion.py`

**Implementation Guide**: 
Read `docs/PHASE_2_FAB_INTEGRATION.md` (50+ pages) for:
- Complete code implementations (copy-paste ready)
- Field mapping (Fab Asset → game-asset-tracker Manifest)
- Testing strategy with mock fixtures
- Edge cases and error handling

**Success Criteria**:
- `uv sync --extra fab` installs successfully
- `SourceRegistry.list_sources()` includes `'fab'`
- Can create pipeline: `SourceRegistry.create_pipeline('fab', client=client)`
- All tests pass: `uv run pytest tests/test_fab_platform.py`
- Generates valid manifests (metadata-only, Phase 2 behavior)

**Estimated Effort**: 2-3 days

---

Reference the comprehensive guide for all implementation details. The guide contains complete working code - you should be able to implement this by following it step-by-step.
