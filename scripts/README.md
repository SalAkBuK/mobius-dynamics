# Scripts

Verification, capture and probing utilities that are useful beside the app but are not tests or benchmarks.

| Script | Purpose |
|---|---|
| `verify_live_index.py` (+ `test_live_index.html`) | drives a live-index flow (fresh load, 4K export overlay) |
| `verify_production_persistence_states.py` (+ `verify_persistence_states.html`), `capture_production_state.py` (+ `capture_production_live.html`) | production state / persistence capture |
| `verify_features.py`, `check_index.py`, `check_vbo.py`, `diag_passes.py`, `debug_draw.py` | small feature / buffer / pass diagnostics |
| `probe_gpu.py`, `probe_edge.py`, `probe_raf.py` (+ their pages) | GPU, edge-case and requestAnimationFrame probes |
| `generate_visual_qa.py`, `build_audit_composites.py` | build side-by-side visual QA sheets |
| `run_in_workbench.py` | **runs any script in `benchmarks/`, `scripts/`, `tests/legacy/` or `docs/archive/experiments/` as originally written** |

```bash
python scripts/run_in_workbench.py --list          # every runnable script and where it lives
python scripts/run_in_workbench.py probe_gpu.py
python scripts/run_in_workbench.py --clean         # remove the .workbench/ scratch folder
```

The older scripts serve their current directory and open pages by bare file name. `run_in_workbench.py` builds that
flat directory (`.workbench/`, git-ignored) from the production files plus all tooling, so they work unchanged.
