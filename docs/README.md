# Documentation

| Document | What it is |
|---|---|
| [`RELEASE_CANDIDATE_REPORT.md`](RELEASE_CANDIDATE_REPORT.md) | the public-release audit: real-browser results, regression totals, findings, owner decisions, final verdict |
| [`HARDENING_REPORT.md`](HARDENING_REPORT.md) | the engine / export / runtime hardening campaign and its tests |
| [`ui/UI_UX_AUDIT.md`](ui/UI_UX_AUDIT.md) | the UI/UX audit, redesign decisions and implementation record (representative images in [`ui/screenshots/`](ui/screenshots/)) |
| [`archive/`](archive/README.md) | earlier issue validations, measurements and audit notes, plus historical experiments |
| [`REPO_LAYOUT.md`](REPO_LAYOUT.md) | where every file went when the repository was organized, and how to run the tests/benchmarks now |

Other places to look: [`../tests/`](../tests/README.md) (regression suite), [`../benchmarks/`](../benchmarks/README.md),
[`../scripts/`](../scripts/README.md), [`../release_checks/`](../release_checks/README.md) (real-browser checks against the deployed site).

File names quoted inside the reports (for example `run_browser_regressions.py`, `test_issue10_presets.html`) refer to the
flat layout that existed when each report was written; `REPO_LAYOUT.md` gives the current location.
