"""Run the integrated adversarial sequence with a genuinely hidden Chrome tab."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from testserver import REPO_ROOT, SearchPathHandler   # serves repo root first, then tests/* (see testserver.py)
import time
from urllib.request import Request, urlopen
import websocket

root = REPO_ROOT
class Handler(SearchPathHandler):
    def log_message(self, *args):
        pass
with http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(root))) as server, tempfile.TemporaryDirectory(prefix='mobius-integrated-') as profile:
    threading.Thread(target=server.serve_forever, daemon=True).start()
    proc = subprocess.Popen([os.environ.get('CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'), '--headless=new', '--no-sandbox', '--use-gl=angle', '--use-angle=d3d11', '--remote-debugging-port=0', '--remote-allow-origins=*', '--user-data-dir='+profile, f'http://127.0.0.1:{server.server_port}/test_integrated_hardening.html'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        deadline = time.monotonic()+20
        while not Path(profile, 'DevToolsActivePort').exists():
            if time.monotonic() > deadline:
                raise RuntimeError('Chrome startup timeout')
            time.sleep(.1)
        port = Path(profile, 'DevToolsActivePort').read_text(encoding='utf-8').splitlines()[0]
        page = next(t for t in json.load(urlopen(f'http://127.0.0.1:{port}/json/list')) if t['type']=='page')
        ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=45)
        seq = 0
        def call(method, params=None):
            global seq
            seq += 1
            ws.send(json.dumps(dict(id=seq, method=method, params=params or {})))
            while True:
                reply = json.loads(ws.recv())
                if reply.get('id') == seq:
                    if 'error' in reply:
                        raise RuntimeError(reply)
                    return reply['result']
        def evaluate(expression):
            return call('Runtime.evaluate', dict(expression=expression, returnByValue=True))['result'].get('value')
        def wait(expression, timeout=120):
            deadline = time.monotonic()+timeout
            while not evaluate(expression):
                if time.monotonic() > deadline:
                    raise RuntimeError('Timeout: '+expression)
                time.sleep(.1)
        wait('window.__ready')
        evaluate('void window.__run()')
        wait('window.__hideRequested || window.__done')
        if not evaluate('window.__done'):
            other = json.load(urlopen(Request(f'http://127.0.0.1:{port}/json/new?about:blank', method='PUT')))
            wait('document.hidden')
            wait('window.__hiddenDone || window.__done')
            call('Page.bringToFront')
            urlopen(f'http://127.0.0.1:{port}/json/close/'+other['id']).read()
        wait('window.__done')
        results = evaluate('window.__results')
        ws.close()
    finally:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait()
        server.shutdown()
for result in results:
    print(f"[{'PASS' if result['passed'] else 'FAIL'}] {result['name']}: {result['details']}")
print(f"SUITE integrated hardening: {sum(r['passed'] for r in results)}/{len(results)} passed")
raise SystemExit(0 if results and all(r['passed'] for r in results) else 1)
