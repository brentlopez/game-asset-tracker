# Phase 5 Implementation Prompt

Use this prompt with a future agent to implement Phase 5:

---

**Task**: Implement UAS (Unreal Asset Store) marketplace integration following the template at `docs/PHASE_5_UAS_INTEGRATION.md`.

**Prerequisites**: 
- Phases 1-3 complete
- Phase 2 (Fab) serves as reference implementation
- uas-api-client library available (parallel to fab-api-client)

**Deliverables**:
1. Create `platforms/uas/` directory with:
   - `source.py` - UASSource implementing Source ABC
   - `transformer.py` - UASTransformer implementing Transformer ABC
   - `__init__.py` - Gated import with auto-registration

2. Add optional dependency to `pyproject.toml`:
   ```toml
   uas = ["uas-api-client>=2.1.0"]
   ```

3. Write tests in `tests/test_uas_platform.py`

4. Create example script at `examples/uas_ingestion.py`

**Implementation Guide**: 
Read `docs/PHASE_5_UAS_INTEGRATION.md` (30+ pages) for:
- Complete UAS implementations (adapted from Fab pattern)
- UAS vs Fab differences (field mappings, auth, API patterns)
- Testing strategy with mock UAS fixtures
- Integration checklist
- Lessons learned from Fab integration

**Key Differences from Fab**:
- Authentication: Token-based instead of cookie-based
- Asset structure: `Product` instead of `Asset`
- Field names: `display_name` vs `title`, `app_version` vs `build_version`
- Entitlement: `ownership.entitled` vs `entitlement` boolean

**Success Criteria**:
- `uv sync --extra uas` installs successfully
- `SourceRegistry.list_sources()` includes `'uas'`
- Can create pipeline: `SourceRegistry.create_pipeline('uas', client=client)`
- All tests pass: `uv run pytest tests/test_uas_platform.py`
- Architecture validated (multiple marketplaces work side-by-side)

**Estimated Effort**: 2-3 days

---

Follow the Fab pattern closely, adapting for UAS-specific differences. The guide provides complete implementations - this validates the multi-marketplace architecture.
