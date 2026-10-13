# Benchmarks

Performance and render-quality measurement tooling used while tuning the adaptive quality tiers, transform-feedback
throughput and accumulation behavior. These are **not** part of the regression suite and do not run in CI.

| Group | Files |
|---|---|
| Transform-feedback / splat throughput | `bench_xfb.py`, `bench_full_xfb.py`, `bench_full_xfb_1m.py`, `bench_multi_splat.py` (+ `.html`), `test_full_xfb.html` |
| Tier / condition matrices | `benchmark_conditions.py`, `debug_conditions.py`, `run_matrix_benchmark.py`, `run_full_matrix.py`, `run_upper_matrix.py`, `merge_matrix.py` and their pages |
| Progressive accumulation | `benchmark_progressive.py` (+ `.html`) |
| GPU / frame timing | `measure_gpu_frame_times.py`, `gpu_bench_harness.html`, `test_bench_timing.*`, `test_raf_bench.*` |
| Reference settle measurement | `measure_issue3.py` (+ `.html`) |
| Benchmark self-validation | `validate_benchmarks.py` (+ `.html`) |

## Running

The scripts expect the flat layout they were written for (current directory = a folder holding `index.html`, the
production modules and their own pages). Use the helper, which assembles that layout in a git-ignored scratch folder:

```bash
python scripts/run_in_workbench.py bench_xfb.py
```

Results (captures, JSON, generated pages) land in `.workbench/`, not in the repository. Numbers depend on the GPU and
driver; compare runs on the same machine. Several scripts hard-code the default Windows Chrome path.
