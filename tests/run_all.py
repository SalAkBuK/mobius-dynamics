"""Run the complete regression gate: every browser suite, then the integrated, Issue 7 and Issue 3 campaigns.

    python tests/run_all.py             # run everything and print the assertion total
    python tests/run_all.py --list      # check the manifest against the files on disk, run nothing

Needs Chrome (CHROME env var overrides the default Windows path), python `websocket-client` and Pillow.
The manifest below is the single list of active browser suites. --list fails if a suite is missing on disk, or if a
test_*.html page exists under tests/ that is neither listed here nor one of the three campaign pages / fixtures.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BROWSER_SUITES = [
    # hardening (one suite per hardening issue)
    'test_issue1_reference_invariant.html', 'test_issue2_context_loss.html', 'test_issue2_rebuild_retry.html',
    'test_issue3b_tier_budgets.html', 'test_issue4_particle_isolation.html', 'test_issue5_input_isolation.html',
    'test_issue6_cancellation.html', 'test_issue8_allocations.html', 'test_issue9_encoding.html',
    'test_issue10_presets.html', 'test_issue11_metadata.html', 'test_issue12_randomizer.html',
    'test_issue13_startup.html', 'test_issue14_transactions.html', 'test_issue15_lifecycle.html',
    # regression
    'test_math_reporting.html', 'test_modes_and_exports.html', 'test_reference_master.html',
    'test_export_display_hold.html', 'test_export_failure_and_edge_cases.html', 'test_export_download_delivery.html',
    'test_preset_copy_name.html', 'test_preset_name_limit.html', 'test_url_param_validation.html',
    'test_space_after_randomize.html',
    # browser / UI
    'test_phase_b_explore_stash.html', 'test_phase_b_panel.html', 'test_phase_b_clarity.html', 'test_phase_b_help.html',
    'test_phase_c_responsive.html', 'test_phase_c_a11y.html', 'test_phase_c_export_states.html', 'test_phase_c_copy.html',
]
CAMPAIGNS = ['run_integrated_hardening.py', 'run_issue7_background.py', 'run_issue3_regressions.py']
# pages that are driven by a campaign runner or are fixtures, not browser suites
NOT_SUITES = {'test_integrated_hardening.html', 'test_issue7_background.html', 'test_issue3_reference_settle.html', 'test_math_units.html'}


def check_manifest():
    found = {p.name for folder in ('hardening', 'regression', 'browser', 'fixtures') for p in (HERE / folder).glob('test_*.html')}
    missing = [s for s in BROWSER_SUITES + sorted(NOT_SUITES) if s not in found]
    unlisted = sorted(found - set(BROWSER_SUITES) - NOT_SUITES)
    print(f'{len(BROWSER_SUITES)} browser suites + {len(CAMPAIGNS)} campaigns listed; {len(found)} test pages on disk')
    for name in missing:
        print('MISSING on disk:', name)
    for name in unlisted:
        print('NOT in manifest:', name)
    return not missing and not unlisted


def run(command):
    process = subprocess.run([sys.executable, *command], cwd=HERE.parent, capture_output=True, text=True, encoding='utf-8', errors='replace')
    sys.stdout.write(process.stdout)
    suites = [(m.group(1), int(m.group(2)), int(m.group(3))) for m in re.finditer(r'^SUITE (.*): (\d+)/(\d+) passed', process.stdout, re.M)]
    return process.returncode, suites


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--list', action='store_true', help='only validate the manifest against the files on disk')
    args = parser.parse_args()
    ok = check_manifest()
    if args.list or not ok:
        raise SystemExit(0 if ok else 2)
    total = passed = 0
    all_ok = True
    for command in [[str(HERE / 'run_browser_regressions.py'), *BROWSER_SUITES, '--timeout', '900']] + [[str(HERE / name)] for name in CAMPAIGNS]:
        code, suites = run(command)
        all_ok &= code == 0 and all(a == b for _, a, b in suites)
        total += sum(b for _, _, b in suites)
        passed += sum(a for _, a, _ in suites)
    print(f'TOTAL {passed}/{total} assertions passed across the gate')
    raise SystemExit(0 if all_ok and passed == total else 1)
