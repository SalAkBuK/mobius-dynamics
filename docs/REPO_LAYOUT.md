# Repository layout map

The repository root used to hold about 200 files side by side. It now contains only the application and its
configuration; engineering material lives in folders. This page maps every file that moved from its old
root path to its new location, so older notes, commit messages and reports that quote the old names can be
followed. Nothing was rewritten: files were moved with `git mv`, so `git log --follow <new path>` shows the full history.

Root (unchanged): `index.html`, `app.js`, `renderer.js`, `math.js`, `adaptive.js`, `profiler.js`, `preset_validation.js`, `favicon.ico`, `preview.png`, `vercel.json`, `README.md`, `.gitignore`, `.vercelignore`.
`release_checks/` did not move.

How to run things after the move:

| What | Command |
|---|---|
| Full regression gate | `python tests/run_all.py` |
| One or more browser suites | `python tests/run_browser_regressions.py test_issue10_presets.html` |
| Benchmarks, probes, legacy tests, experiments | `python scripts/run_in_workbench.py <script name>` (see `--list`) |

Order below: most important first.

## Reports → `docs/`

| Old path | New path |
|---|---|
| `HARDENING_REPORT.md` | `docs/HARDENING_REPORT.md` |
| `RELEASE_CANDIDATE_REPORT.md` | `docs/RELEASE_CANDIDATE_REPORT.md` |

## UI/UX audit → `docs/ui/`

| Old path | New path |
|---|---|
| `UI_UX_AUDIT.md` | `docs/ui/UI_UX_AUDIT.md` |

## UI audit screenshots → `docs/ui/screenshots/`

| Old path | New path |
|---|---|
| `ui_audit_screenshots/a2_explore_drawer_1366.jpg` | `docs/ui/screenshots/a2_explore_drawer_1366.jpg` |
| `ui_audit_screenshots/m1_toast_overflow_390.jpg` | `docs/ui/screenshots/m1_toast_overflow_390.jpg` |
| `ui_audit_screenshots/m3_export_refmaster_390.jpg` | `docs/ui/screenshots/m3_export_refmaster_390.jpg` |
| `ui_audit_screenshots/p2_presets_long_dup_corrupt.jpg` | `docs/ui/screenshots/p2_presets_long_dup_corrupt.jpg` |
| `ui_audit_screenshots/v_1366x768_drawer_debug.jpg` | `docs/ui/screenshots/v_1366x768_drawer_debug.jpg` |
| `ui_audit_screenshots/v_1366x768_landing.jpg` | `docs/ui/screenshots/v_1366x768_landing.jpg` |
| `ui_audit_screenshots/v_1920x1080_landing.jpg` | `docs/ui/screenshots/v_1920x1080_landing.jpg` |
| `ui_audit_screenshots/v_390x844_landing.jpg` | `docs/ui/screenshots/v_390x844_landing.jpg` |

## Historical issue reports and audit notes → `docs/archive/`

| Old path | New path |
|---|---|
| `ISSUE2_WEBGL_RECOVERY.md` | `docs/archive/ISSUE2_WEBGL_RECOVERY.md` |
| `ISSUE3B_MEASUREMENTS.jpg` | `docs/archive/ISSUE3B_MEASUREMENTS.jpg` |
| `ISSUE3B_MEASUREMENTS.md` | `docs/archive/ISSUE3B_MEASUREMENTS.md` |
| `ISSUE3B_VALIDATION.md` | `docs/archive/ISSUE3B_VALIDATION.md` |
| `ISSUE3_VALIDATION.md` | `docs/archive/ISSUE3_VALIDATION.md` |
| `ISSUE4_VALIDATION.md` | `docs/archive/ISSUE4_VALIDATION.md` |
| `final_audit_message.md` | `docs/archive/final_audit_message.md` |
| `final_audit_report_full.md` | `docs/archive/final_audit_report_full.md` |

## Historical experiments and analysis → `docs/archive/experiments/`

| Old path | New path |
|---|---|
| `active_persistence_test.html` | `docs/archive/experiments/active_persistence_test.html` |
| `analyze_ghosting_images.py` | `docs/archive/experiments/analyze_ghosting_images.py` |
| `analyze_issue3b.py` | `docs/archive/experiments/analyze_issue3b.py` |
| `compute_image_metrics.py` | `docs/archive/experiments/compute_image_metrics.py` |
| `consolidate_experiment_report.py` | `docs/archive/experiments/consolidate_experiment_report.py` |
| `detail_audit_harness.html` | `docs/archive/experiments/detail_audit_harness.html` |
| `drift_aware_test.html` | `docs/archive/experiments/drift_aware_test.html` |
| `experiment.py` | `docs/archive/experiments/experiment.py` |
| `fallback_test.html` | `docs/archive/experiments/fallback_test.html` |
| `ghosting_and_ramp_test.html` | `docs/archive/experiments/ghosting_and_ramp_test.html` |
| `idle_persistence_test.html` | `docs/archive/experiments/idle_persistence_test.html` |
| `nobloom_void_test.html` | `docs/archive/experiments/nobloom_void_test.html` |
| `parity_test.html` | `docs/archive/experiments/parity_test.html` |
| `print_sustained_summary.py` | `docs/archive/experiments/print_sustained_summary.py` |
| `real_persistence_audit.html` | `docs/archive/experiments/real_persistence_audit.html` |
| `reproduce_issue2_context_loss.html` | `docs/archive/experiments/reproduce_issue2_context_loss.html` |
| `run_active_persistence_experiment.py` | `docs/archive/experiments/run_active_persistence_experiment.py` |
| `run_drift_aware_experiment.py` | `docs/archive/experiments/run_drift_aware_experiment.py` |
| `run_float_fallbacks.py` | `docs/archive/experiments/run_float_fallbacks.py` |
| `run_ghosting_and_ramp_experiment.py` | `docs/archive/experiments/run_ghosting_and_ramp_experiment.py` |
| `run_idle_persistence_accumulation.py` | `docs/archive/experiments/run_idle_persistence_accumulation.py` |
| `run_real_persistence_audit.py` | `docs/archive/experiments/run_real_persistence_audit.py` |
| `run_sustained_10min_test.py` | `docs/archive/experiments/run_sustained_10min_test.py` |
| `run_visual_detail_audit.py` | `docs/archive/experiments/run_visual_detail_audit.py` |
| `run_visual_parity.py` | `docs/archive/experiments/run_visual_parity.py` |
| `run_void_experiment.py` | `docs/archive/experiments/run_void_experiment.py` |
| `search_params.py` | `docs/archive/experiments/search_params.py` |
| `sim_test.py` | `docs/archive/experiments/sim_test.py` |
| `specimen_void_test.html` | `docs/archive/experiments/specimen_void_test.html` |
| `summarize_persistence_audit.py` | `docs/archive/experiments/summarize_persistence_audit.py` |
| `sustained_test.html` | `docs/archive/experiments/sustained_test.html` |
| `test_branch.py` | `docs/archive/experiments/test_branch.py` |
| `test_cap.html` | `docs/archive/experiments/test_cap.html` |
| `test_deep_accum.html` | `docs/archive/experiments/test_deep_accum.html` |
| `test_deep_zoom.py` | `docs/archive/experiments/test_deep_zoom.py` |
| `test_deep_zoom_scales.py` | `docs/archive/experiments/test_deep_zoom_scales.py` |
| `test_dyn.py` | `docs/archive/experiments/test_dyn.py` |
| `test_exact_mobius.py` | `docs/archive/experiments/test_exact_mobius.py` |
| `test_homoclinic.py` | `docs/archive/experiments/test_homoclinic.py` |
| `test_ifs_zoom.py` | `docs/archive/experiments/test_ifs_zoom.py` |
| `test_multiscale.py` | `docs/archive/experiments/test_multiscale.py` |
| `test_phase.py` | `docs/archive/experiments/test_phase.py` |
| `test_single_cap.py` | `docs/archive/experiments/test_single_cap.py` |
| `test_streamline.py` | `docs/archive/experiments/test_streamline.py` |
| `test_tonemapper.py` | `docs/archive/experiments/test_tonemapper.py` |
| `verify_theory.py` | `docs/archive/experiments/verify_theory.py` |
| `void_experiment.html` | `docs/archive/experiments/void_experiment.html` |
| `zoom_test.py` | `docs/archive/experiments/zoom_test.py` |

## Test runners → `tests/`

| Old path | New path |
|---|---|
| `run_browser_regressions.py` | `tests/run_browser_regressions.py` |
| `run_integrated_hardening.py` | `tests/run_integrated_hardening.py` |
| `run_issue3_regressions.py` | `tests/run_issue3_regressions.py` |
| `run_issue7_background.py` | `tests/run_issue7_background.py` |

## Active hardening suites → `tests/hardening/`

| Old path | New path |
|---|---|
| `test_integrated_hardening.html` | `tests/hardening/test_integrated_hardening.html` |
| `test_issue10_presets.html` | `tests/hardening/test_issue10_presets.html` |
| `test_issue11_metadata.html` | `tests/hardening/test_issue11_metadata.html` |
| `test_issue12_randomizer.html` | `tests/hardening/test_issue12_randomizer.html` |
| `test_issue13_startup.html` | `tests/hardening/test_issue13_startup.html` |
| `test_issue14_transactions.html` | `tests/hardening/test_issue14_transactions.html` |
| `test_issue15_lifecycle.html` | `tests/hardening/test_issue15_lifecycle.html` |
| `test_issue1_reference_invariant.html` | `tests/hardening/test_issue1_reference_invariant.html` |
| `test_issue2_context_loss.html` | `tests/hardening/test_issue2_context_loss.html` |
| `test_issue2_rebuild_retry.html` | `tests/hardening/test_issue2_rebuild_retry.html` |
| `test_issue3_reference_settle.html` | `tests/hardening/test_issue3_reference_settle.html` |
| `test_issue3b_tier_budgets.html` | `tests/hardening/test_issue3b_tier_budgets.html` |
| `test_issue4_particle_isolation.html` | `tests/hardening/test_issue4_particle_isolation.html` |
| `test_issue5_input_isolation.html` | `tests/hardening/test_issue5_input_isolation.html` |
| `test_issue6_cancellation.html` | `tests/hardening/test_issue6_cancellation.html` |
| `test_issue7_background.html` | `tests/hardening/test_issue7_background.html` |
| `test_issue8_allocations.html` | `tests/hardening/test_issue8_allocations.html` |
| `test_issue9_encoding.html` | `tests/hardening/test_issue9_encoding.html` |

## Active regression suites → `tests/regression/`

| Old path | New path |
|---|---|
| `test_export_display_hold.html` | `tests/regression/test_export_display_hold.html` |
| `test_export_download_delivery.html` | `tests/regression/test_export_download_delivery.html` |
| `test_export_failure_and_edge_cases.html` | `tests/regression/test_export_failure_and_edge_cases.html` |
| `test_math_reporting.html` | `tests/regression/test_math_reporting.html` |
| `test_modes_and_exports.html` | `tests/regression/test_modes_and_exports.html` |
| `test_preset_copy_name.html` | `tests/regression/test_preset_copy_name.html` |
| `test_preset_name_limit.html` | `tests/regression/test_preset_name_limit.html` |
| `test_reference_master.html` | `tests/regression/test_reference_master.html` |
| `test_space_after_randomize.html` | `tests/regression/test_space_after_randomize.html` |
| `test_url_param_validation.html` | `tests/regression/test_url_param_validation.html` |

## Active UI / browser suites → `tests/browser/`

| Old path | New path |
|---|---|
| `test_phase_b_clarity.html` | `tests/browser/test_phase_b_clarity.html` |
| `test_phase_b_explore_stash.html` | `tests/browser/test_phase_b_explore_stash.html` |
| `test_phase_b_help.html` | `tests/browser/test_phase_b_help.html` |
| `test_phase_b_panel.html` | `tests/browser/test_phase_b_panel.html` |
| `test_phase_c_a11y.html` | `tests/browser/test_phase_c_a11y.html` |
| `test_phase_c_copy.html` | `tests/browser/test_phase_c_copy.html` |
| `test_phase_c_export_states.html` | `tests/browser/test_phase_c_export_states.html` |
| `test_phase_c_responsive.html` | `tests/browser/test_phase_c_responsive.html` |

## Test fixtures → `tests/fixtures/`

| Old path | New path |
|---|---|
| `issue4_export_fixtures.js` | `tests/fixtures/issue4_export_fixtures.js` |
| `test_math_units.html` | `tests/fixtures/test_math_units.html` |

## Test helpers → `tests/helpers/`

| Old path | New path |
|---|---|
| `hardening_test_helpers.js` | `tests/helpers/hardening_test_helpers.js` |
| `issue2_test_instrumentation.js` | `tests/helpers/issue2_test_instrumentation.js` |

## Legacy standalone test runners (not in the active suite) → `tests/legacy/`

| Old path | New path |
|---|---|
| `flush_test.html` | `tests/legacy/flush_test.html` |
| `run_math_tests.py` | `tests/legacy/run_math_tests.py` |
| `systems_test.html` | `tests/legacy/systems_test.html` |
| `test_589k.html` | `tests/legacy/test_589k.html` |
| `test_589k.py` | `tests/legacy/test_589k.py` |
| `test_adaptive.html` | `tests/legacy/test_adaptive.html` |
| `test_adaptive_production.py` | `tests/legacy/test_adaptive_production.py` |
| `test_canvas_read.html` | `tests/legacy/test_canvas_read.html` |
| `test_canvas_read.py` | `tests/legacy/test_canvas_read.py` |
| `test_export_display_hold.py` | `tests/legacy/test_export_display_hold.py` |
| `test_export_failure_and_edge_cases.py` | `tests/legacy/test_export_failure_and_edge_cases.py` |
| `test_flush_comparison.py` | `tests/legacy/test_flush_comparison.py` |
| `test_full_inst.html` | `tests/legacy/test_full_inst.html` |
| `test_full_instrumentation.py` | `tests/legacy/test_full_instrumentation.py` |
| `test_issue1_reference_invariant.py` | `tests/legacy/test_issue1_reference_invariant.py` |
| `test_modes_and_exports.py` | `tests/legacy/test_modes_and_exports.py` |
| `test_profiler_proto.html` | `tests/legacy/test_profiler_proto.html` |
| `test_profiler_proto.py` | `tests/legacy/test_profiler_proto.py` |
| `test_query_pool.html` | `tests/legacy/test_query_pool.html` |
| `test_query_pool.py` | `tests/legacy/test_query_pool.py` |
| `test_query_raf.html` | `tests/legacy/test_query_raf.html` |
| `test_query_raf.py` | `tests/legacy/test_query_raf.py` |
| `test_query_safety.html` | `tests/legacy/test_query_safety.html` |
| `test_query_safety.py` | `tests/legacy/test_query_safety.py` |
| `test_reference_master.py` | `tests/legacy/test_reference_master.py` |
| `test_render_err.html` | `tests/legacy/test_render_err.html` |
| `test_render_err.py` | `tests/legacy/test_render_err.py` |
| `test_systems_features.py` | `tests/legacy/test_systems_features.py` |
| `test_timer_query.html` | `tests/legacy/test_timer_query.html` |
| `test_timer_query.py` | `tests/legacy/test_timer_query.py` |

## Benchmarks → `benchmarks/`

| Old path | New path |
|---|---|
| `bench_full_xfb.py` | `benchmarks/bench_full_xfb.py` |
| `bench_full_xfb_1m.py` | `benchmarks/bench_full_xfb_1m.py` |
| `bench_multi_splat.html` | `benchmarks/bench_multi_splat.html` |
| `bench_multi_splat.py` | `benchmarks/bench_multi_splat.py` |
| `bench_xfb.py` | `benchmarks/bench_xfb.py` |
| `benchmark_conditions.html` | `benchmarks/benchmark_conditions.html` |
| `benchmark_conditions.py` | `benchmarks/benchmark_conditions.py` |
| `benchmark_matrix.html` | `benchmarks/benchmark_matrix.html` |
| `benchmark_progressive.html` | `benchmarks/benchmark_progressive.html` |
| `benchmark_progressive.py` | `benchmarks/benchmark_progressive.py` |
| `debug_conditions.html` | `benchmarks/debug_conditions.html` |
| `debug_conditions.py` | `benchmarks/debug_conditions.py` |
| `gpu_bench_harness.html` | `benchmarks/gpu_bench_harness.html` |
| `matrix_benchmark_page.html` | `benchmarks/matrix_benchmark_page.html` |
| `measure_gpu_frame_times.py` | `benchmarks/measure_gpu_frame_times.py` |
| `measure_issue3.html` | `benchmarks/measure_issue3.html` |
| `measure_issue3.py` | `benchmarks/measure_issue3.py` |
| `merge_matrix.py` | `benchmarks/merge_matrix.py` |
| `run_full_matrix.py` | `benchmarks/run_full_matrix.py` |
| `run_matrix_benchmark.py` | `benchmarks/run_matrix_benchmark.py` |
| `run_upper_matrix.py` | `benchmarks/run_upper_matrix.py` |
| `test_bench_timing.html` | `benchmarks/test_bench_timing.html` |
| `test_bench_timing.py` | `benchmarks/test_bench_timing.py` |
| `test_full_xfb.html` | `benchmarks/test_full_xfb.html` |
| `test_raf_bench.html` | `benchmarks/test_raf_bench.html` |
| `test_raf_bench.py` | `benchmarks/test_raf_bench.py` |
| `upper_matrix_page.html` | `benchmarks/upper_matrix_page.html` |
| `validate_benchmarks.html` | `benchmarks/validate_benchmarks.html` |
| `validate_benchmarks.py` | `benchmarks/validate_benchmarks.py` |

## Verification and utility scripts → `scripts/`

| Old path | New path |
|---|---|
| `build_audit_composites.py` | `scripts/build_audit_composites.py` |
| `capture_production_live.html` | `scripts/capture_production_live.html` |
| `capture_production_state.py` | `scripts/capture_production_state.py` |
| `check_index.py` | `scripts/check_index.py` |
| `check_vbo.py` | `scripts/check_vbo.py` |
| `debug_draw.py` | `scripts/debug_draw.py` |
| `diag_passes.py` | `scripts/diag_passes.py` |
| `edge_probe_page.html` | `scripts/edge_probe_page.html` |
| `generate_visual_qa.html` | `scripts/generate_visual_qa.html` |
| `generate_visual_qa.py` | `scripts/generate_visual_qa.py` |
| `probe_edge.py` | `scripts/probe_edge.py` |
| `probe_gpu.py` | `scripts/probe_gpu.py` |
| `probe_page.html` | `scripts/probe_page.html` |
| `probe_raf.py` | `scripts/probe_raf.py` |
| `test_debug_draw.html` | `scripts/test_debug_draw.html` |
| `test_live_index.html` | `scripts/test_live_index.html` |
| `test_raf.html` | `scripts/test_raf.html` |
| `test_read_vbo.html` | `scripts/test_read_vbo.html` |
| `verify_features.py` | `scripts/verify_features.py` |
| `verify_live_index.py` | `scripts/verify_live_index.py` |
| `verify_persistence_states.html` | `scripts/verify_persistence_states.html` |
| `verify_production_persistence_states.py` | `scripts/verify_production_persistence_states.py` |
