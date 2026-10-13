"""Run a benchmark / probe / legacy-test / experiment script exactly as it was written.

Those scripts date from when every file lived in one flat folder: they serve the current directory over HTTP,
write generated pages into it and open them by bare file name next to index.html. After the repository was
organized into folders they would no longer find anything. This helper rebuilds that flat layout in a scratch
directory (.workbench/, git-ignored), copying in the production files plus every tooling file, and runs the
script there unchanged.

    python scripts/run_in_workbench.py bench_xfb.py
    python scripts/run_in_workbench.py run_math_tests.py --some-arg
    python scripts/run_in_workbench.py --list          # every runnable script and where it lives
    python scripts/run_in_workbench.py --clean         # delete .workbench/

Generated pages, captures and reports end up in .workbench/ (path printed at the end), never in the repo.
The active regression suite does NOT use this helper; see tests/README.md.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKBENCH = ROOT / '.workbench'
PRODUCTION = ['index.html', 'app.js', 'renderer.js', 'math.js', 'adaptive.js', 'profiler.js', 'preset_validation.js', 'favicon.ico', 'preview.png']
TOOL_DIRS = ['tests/helpers', 'tests/fixtures', 'tests/hardening', 'tests/regression', 'tests/browser', 'tests/legacy',
             'benchmarks', 'scripts', 'docs/archive/experiments']


def tool_files():
    files = {}
    for folder in TOOL_DIRS:
        for path in sorted((ROOT / folder).glob('*')):
            if path.is_file() and path.name != Path(__file__).name:
                files.setdefault(path.name, path)
    return files


def build():
    if WORKBENCH.exists():
        shutil.rmtree(WORKBENCH)
    WORKBENCH.mkdir()
    for name in PRODUCTION:
        shutil.copy2(ROOT / name, WORKBENCH / name)
    for name, path in tool_files().items():
        shutil.copy2(path, WORKBENCH / name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('script', nargs='?', help='bare file name of a script, e.g. bench_xfb.py')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='arguments passed to the script')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--clean', action='store_true')
    options = parser.parse_args()
    if options.clean:
        shutil.rmtree(WORKBENCH, ignore_errors=True)
        raise SystemExit(0)
    if options.list:
        for name, path in sorted(tool_files().items()):
            if name.endswith('.py'):
                print(f'{name:48s} {path.parent.relative_to(ROOT).as_posix()}')
        raise SystemExit(0)
    if not options.script or options.script not in tool_files():
        parser.error('give the bare file name of a script (see --list)')
    build()
    code = subprocess.call([sys.executable, options.script, *options.args], cwd=WORKBENCH)
    print(f'\nscratch directory with any generated output: {WORKBENCH}')
    raise SystemExit(code)
