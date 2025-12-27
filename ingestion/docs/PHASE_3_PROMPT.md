# Phase 3 Implementation Prompt

Use this prompt with a future agent to implement Phase 3:

---

**Task**: Implement download strategy (manifest downloading and parsing) following the comprehensive guide at `docs/PHASE_3_DOWNLOAD_STRATEGY.md`.

**Prerequisites**: 
- Phase 1 complete (core architecture)
- Phase 2 complete (Fab integration with metadata-only mode)

**Deliverables**:
1. Update `platforms/fab/source.py`:
   - Modify `get_asset_data()` to download manifests when `download=True`
   - Parse manifests with `manifest_result.load()`
   - Clean up temp directories

2. Update `platforms/fab/transformer.py`:
   - Add `_parse_manifest_files()` method
   - Add `_calculate_file_size()` method
   - Branch: if manifest present, parse files; else use placeholder

3. Ensure `pipeline.py` passes download flag based on strategy

4. Add tests for manifest parsing in `tests/test_fab_platform.py`

5. Update `examples/fab_ingestion.py` with manifests_only example

**Implementation Guide**: 
Read `docs/PHASE_3_DOWNLOAD_STRATEGY.md` (30+ pages) for:
- Complete updated implementations
- File size calculation from chunk parts
- Tag derivation from file paths
- Error handling and cleanup patterns
- Testing strategy with mock ParsedManifest

**Success Criteria**:
- `download_strategy='metadata_only'` still works (backward compat)
- `download_strategy='manifests_only'` downloads and parses manifests
- File sizes calculated correctly from chunks
- Local tags derived from file paths
- Temp directories cleaned up (no disk leaks)
- All tests pass

**Estimated Effort**: 2-4 days

---

The guide provides complete code for all modifications. Follow it step-by-step to add manifest downloading while maintaining Phase 2 compatibility.
