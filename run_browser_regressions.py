"""Run repository HTML regression suites in isolated headless Chrome sessions."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading


def run(page, timeout):
    result = []
    done = threading.Event()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            path = Path(self.translate_path(self.path))
            if path.is_file() and path.suffix == '.html':
                # Older suites embed their original runner's fixed localhost port.
                html = re.sub(r'http://localhost:\d+/', '/', path.read_text(encoding='utf-8'))
                body = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

        def do_POST(self):
            result.extend(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            done.set()

        def log_message(self, *args):
            pass

    handler = functools.partial(Handler, directory=str(Path(__file__).resolve().parent))
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        chrome = os.environ.get('CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
        with tempfile.TemporaryDirectory(prefix='mobius-webgl-') as profile:
            with tempfile.TemporaryFile() as stderr:
                proc = subprocess.Popen([
                    chrome, '--headless=new', '--no-sandbox', '--use-gl=angle',
                    '--use-angle=d3d11', '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding', '--window-size=900,700',
                    '--user-data-dir=' + profile,
                    f'http://127.0.0.1:{server.server_port}/{page}',
                ], stdout=subprocess.DEVNULL, stderr=stderr)
                try:
                    completed = done.wait(timeout)
                finally:
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    proc.wait()
                    server.shutdown()
                if not completed:
                    stderr.seek(0)
                    print(stderr.read().decode(errors='replace')[-4000:])
                    raise RuntimeError(f'{page}: timed out after {timeout}s')
    for test in result:
        print(f"[{'PASS' if test.get('passed') else 'FAIL'}] {test['name']}: {test.get('details', '')}")
    print(f"SUITE {page}: {sum(bool(test.get('passed')) for test in result)}/{len(result)} passed")
    return bool(result) and all(test.get('passed') for test in result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pages', nargs='+')
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    passed = True
    for page in args.pages:
        passed = run(page, args.timeout) and passed
    raise SystemExit(0 if passed else 1)
