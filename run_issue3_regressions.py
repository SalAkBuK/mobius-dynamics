"""Issue 3 browser suite with compositor screenshots (pip install websocket-client pillow)."""
import base64
import functools
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from urllib.request import urlopen

import websocket
from PIL import Image, ImageChops

root = Path(__file__).resolve().parent
artifacts = root / 'issue3_results'
artifacts.mkdir(exist_ok=True)
done = threading.Event()
ready = threading.Event()
results = []
cdp = None
sequence = 0


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        global sequence
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/screen':
            if not ready.wait(10):
                raise RuntimeError('DevTools did not connect')
            sequence += 1
            cdp.send(json.dumps({'id':sequence, 'method':'Page.captureScreenshot',
                                'params':{'format':'png', 'clip':payload['clip']}}))
            while True:
                reply = json.loads(cdp.recv())
                if reply.get('id') == sequence:
                    break
            if 'error' in reply:
                raise RuntimeError(reply['error'])
            data = base64.b64decode(reply['result']['data'])
            target = artifacts / (payload['name'] + '.png')
            target.write_bytes(data)
            im = Image.open(io.BytesIO(data)).convert('RGB')
            response = {'extrema':im.getextrema()}
            if payload.get('compare'):
                before = Image.open(artifacts / (payload['compare'] + '.png')).convert('RGB')
                response['identical'] = before.size == im.size and ImageChops.difference(before,im).getbbox() is None
            print('SCREEN', payload['name'], response, flush=True)
        else:
            results.extend(payload)
            (artifacts / 'results.json').write_text(json.dumps(results,indent=2), encoding='utf-8')
            response = {'ok':True}
            done.set()
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


handler = functools.partial(Handler,directory=str(root))
with http.server.ThreadingHTTPServer(('127.0.0.1',0),handler) as server:
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='mobius-settle-') as profile:
        with (artifacts / 'chrome.log').open('wb') as stderr:
            proc = subprocess.Popen([
                os.environ.get('CHROME',r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
                '--headless=new','--no-sandbox','--use-gl=angle','--use-angle=d3d11',
                '--disable-background-timer-throttling','--disable-renderer-backgrounding',
                '--window-size=1100,850','--remote-debugging-port=0','--remote-allow-origins=*',
                '--user-data-dir='+profile,
                f'http://127.0.0.1:{server.server_port}/test_issue3_reference_settle.html',
            ],stdout=subprocess.DEVNULL,stderr=stderr)
            try:
                portfile = Path(profile) / 'DevToolsActivePort'
                deadline = time.monotonic()+20
                while not portfile.exists():
                    if time.monotonic()>deadline:
                        raise RuntimeError('Chrome did not start')
                    time.sleep(.1)
                port = portfile.read_text().splitlines()[0]
                targets = json.load(urlopen(f'http://127.0.0.1:{port}/json/list'))
                page = next(t for t in targets if t['type']=='page')
                cdp = websocket.create_connection(page['webSocketDebuggerUrl'],timeout=30)
                ready.set()
                completed = done.wait(1500)
            finally:
                if cdp:
                    cdp.close()
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                proc.wait()
                server.shutdown()
            if not completed:
                raise RuntimeError('Issue 3 suite timed out')
for test in results:
    print(f"[{'PASS' if test.get('passed') else 'FAIL'}] {test['name']}: {test.get('details','')}")
print(f"SUITE Issue 3: {sum(bool(t.get('passed')) for t in results)}/{len(results)} passed")
raise SystemExit(0 if results and all(t.get('passed') for t in results) else 1)
