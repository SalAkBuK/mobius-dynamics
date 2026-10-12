"""Capture 60-second production Reference timelines for four sequential quality modes."""
import base64
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import argparse
from urllib.parse import urlencode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default='issue3_baseline')
parser.add_argument('--tiers', default='potato,low,standard,auto')
parser.add_argument('--times', default='2,5,10,20,30,60')
args = parser.parse_args()
output = Path(args.output).resolve()
output.mkdir(exist_ok=True)
done = threading.Event()


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/capture':
            png = payload.pop('png')
            (output / f"{payload['tier']}_{payload['second']:02d}.png").write_bytes(base64.b64decode(png))
            print(json.dumps(payload), flush=True)
        else:
            (output / 'measurements.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
            done.set()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, *args):
        pass


handler = functools.partial(Handler, directory=str(Path(__file__).resolve().parent))
with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='mobius-reference-') as profile:
        with (output / 'chrome.log').open('wb') as stderr:
            proc = subprocess.Popen([
                os.environ.get('CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
                '--headless=new', '--no-sandbox', '--use-gl=angle', '--use-angle=d3d11',
                '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
                '--window-size=1280,900', '--user-data-dir='+profile,
                f'http://127.0.0.1:{server.server_port}/measure_issue3.html?'+urlencode({'tiers':args.tiers,'times':args.times}),
            ], stdout=subprocess.DEVNULL, stderr=stderr)
            try:
                completed = done.wait(max(map(int,args.times.split(',')))*len(args.tiers.split(','))+90)
            finally:
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'], stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                proc.wait()
                server.shutdown()
            if not completed:
                raise RuntimeError('Measurement timed out')
            report = json.loads((output / 'measurements.json').read_text(encoding='utf-8'))
            if any('error' in entry for entry in report):
                raise RuntimeError('Browser measurement failed: '+str(report))
