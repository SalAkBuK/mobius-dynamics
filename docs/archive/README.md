# Archive

Historical evidence kept for provenance. Nothing here is needed to build, run or test the application.

* **Issue reports** — `ISSUE2_WEBGL_RECOVERY.md`, `ISSUE3_VALIDATION.md`, `ISSUE3B_VALIDATION.md`,
  `ISSUE3B_MEASUREMENTS.md` (+ `.jpg`), `ISSUE4_VALIDATION.md`: the validation write-ups for the context-recovery,
  Reference-settle, adaptive tier-budget and particle-isolation fixes. `HARDENING_REPORT.md` (in `docs/`) is the
  consolidated record.
* **Audit notes** — `final_audit_message.md`, `final_audit_report_full.md`: an earlier engineering audit. They contain
  absolute `file:///` links to the author's original working folder, which no longer exist; they are left as written.
* **`experiments/`** — one-off research and measurement scripts and their pages (persistence, ghosting, void, drift,
  parity, float fallbacks, sustained runs, deep-zoom and math probes). Run any of them as originally written with
  `python scripts/run_in_workbench.py <name>.py`.

`renderer.js` has a header comment that says "See ISSUE3B_VALIDATION.md and ISSUE3B_MEASUREMENTS.md". Those two files
are in this folder now. The comment was intentionally not edited so that the production file stays byte-identical.
