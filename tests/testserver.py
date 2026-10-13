"""Static file handler shared by the browser test runners.

The suites were written when every page lived beside index.html, so they use URLs such as ./index.html,
./math.js and ./hardening_test_helpers.js. Those pages now live under tests/. Instead of editing every page,
the runners serve the repository root first and then fall back to the test folders, so each page still sees
the same flat URL namespace it always did (and production files are always served from the repository root).
"""
import http.server
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# legacy/ is deliberately not served: it is not part of the active suite.
SEARCH_DIRS = [REPO_ROOT / 'tests' / name for name in ('hardening', 'regression', 'browser', 'fixtures', 'helpers')]


class SearchPathHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        resolved = super().translate_path(path)
        if os.path.exists(resolved):
            return resolved
        relative = os.path.relpath(resolved, self.directory)
        if os.sep not in relative:                       # only top-level names (/test_x.html, /helpers.js) fall back
            for folder in SEARCH_DIRS:
                candidate = folder / relative
                if candidate.is_file():
                    return str(candidate)
        return resolved
