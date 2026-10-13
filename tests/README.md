# Tests

The regression and hardening suite for the application (7,618 assertions at the time of the last release check).
Everything runs in headless Chrome against the real `index.html` and production modules in the repository root.

## Run

```bash
python tests/run_all.py          # the whole gate: all browser suites + integrated, Issue 7 and Issue 3 campaigns
python tests/run_all.py --list   # check the suite manifest against the files on disk, run nothing

# a single suite (name only, no folder):
python tests/run_browser_regressions.py test_issue10_presets.html
python tests/run_issue7_background.py          # real hidden-tab campaign
python tests/run_integrated_hardening.py       # integrated adversarial campaign
python tests/run_issue3_regressions.py         # five-minute Reference idle campaign
```

Requirements: Windows Chrome (set `CHROME` to override the default path), Python 3 with `websocket-client` and `Pillow`.
Two suites (`test_modes_and_exports`, `test_reference_master`) perform real exports, so a few PNG files appear in your
browser's default Downloads folder during a run; they are test output and safe to delete.

## Layout

| Folder | Contents |
|---|---|
| `hardening/` | one suite per hardening issue (context loss, cancellation, input isolation, presets, startup, lifecycle …) and the integrated campaign page |
| `regression/` | feature regressions: modes and exports, Reference Master, export download delivery, preset naming/limits, URL parameter validation, Space-after-Randomize |
| `browser/` | UI / UX suites (explore stash, panel, help, clarity, responsive, accessibility, export dialog states, copy) |
| `fixtures/`, `helpers/` | shared fixtures and the instrumentation/helper modules the suites import |
| `legacy/` | older standalone runners and probe pages that are **not** part of the active suite; kept for provenance (see below) |
| `testserver.py`, `run_*.py` | the runners and the small web server they share |

## How paths work

The suites were written when every page sat next to `index.html`, so pages use URLs like `./index.html`, `./math.js` and
`./hardening_test_helpers.js`. The runners serve the **repository root first** and then fall back to the folders above
(`testserver.py`), so each page sees the same flat URL space it always did and no page needed editing. A page only has to
exist in one of those folders; production files always come from the root.

## Adding a suite

Put the page in the folder that matches its role, add its file name to `BROWSER_SUITES` in `run_all.py`, and run
`python tests/run_all.py --list`; it fails if a page on disk is missing from the manifest.

## Legacy folder

`legacy/` holds the original standalone runners (each generated its own page and served the current directory) and probe
pages that were never part of the 7,618-assertion gate. To run one exactly as written use
`python scripts/run_in_workbench.py <name>.py`.

Real-browser checks against the deployed site live in [`../release_checks/`](../release_checks/README.md).
