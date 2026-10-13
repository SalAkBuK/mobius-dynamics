"""Exercise real foreground/background Chrome tabs through CDP (websocket-client)."""
import argparse
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

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',action='store_true')
args=parser.parse_args()
root=REPO_ROOT
results=[]
def check(name,passed,details=''):
    results.append(dict(name=name,passed=bool(passed),details=details))
class Handler(SearchPathHandler):
    def log_message(self,*args):pass
with http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root))) as server, tempfile.TemporaryDirectory(prefix='mobius-background-') as profile:
    threading.Thread(target=server.serve_forever,daemon=True).start()
    proc=subprocess.Popen([os.environ.get('CHROME',r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
        '--headless=new','--no-sandbox','--use-gl=angle','--use-angle=d3d11','--remote-debugging-port=0',
        '--remote-allow-origins=*','--user-data-dir='+profile,f'http://127.0.0.1:{server.server_port}/test_issue7_background.html'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+20
        while not Path(profile,'DevToolsActivePort').exists():
            if time.monotonic()>deadline:raise RuntimeError('Chrome startup timeout')
            time.sleep(.1)
        port=Path(profile,'DevToolsActivePort').read_text(encoding='utf-8').splitlines()[0]
        page=next(t for t in json.load(urlopen(f'http://127.0.0.1:{port}/json/list')) if t['type']=='page')
        ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=45);seq=0
        def call(method,params=None):
            global seq
            seq+=1;ws.send(json.dumps(dict(id=seq,method=method,params=params or {})))
            while True:
                reply=json.loads(ws.recv())
                if reply.get('id')==seq:
                    if 'error' in reply:raise RuntimeError(reply)
                    return reply['result']
        def evaluate(expression):return call('Runtime.evaluate',dict(expression=expression,returnByValue=True))['result'].get('value')
        def wait(expression,timeout=90):
            end=time.monotonic()+timeout
            while not evaluate(expression):
                if time.monotonic()>end:raise RuntimeError('Timeout: '+expression)
                time.sleep(.1)
        wait('window.__ready')
        for kind in ['standard','master']:
            call('Page.bringToFront');evaluate(f"void window.__run('{kind}')");wait('window.__done')
            control=evaluate('window.__result')
            evaluate(f"void window.__run('{kind}')")
            other=json.load(urlopen(Request(f'http://127.0.0.1:{port}/json/new?about:blank',method='PUT')))
            wait("document.visibilityState==='hidden'")
            check(kind+': browser genuinely reports hidden',evaluate('document.hidden'))
            time.sleep(1);first=evaluate('window.__progress');time.sleep(3);second=evaluate('window.__progress');done=evaluate('window.__done')
            check(kind+(': pre-fix RAF stall reproduced' if args.baseline else ': export progresses/completes while hidden'),
                  first==second and not done if args.baseline else second>first or done,
                  dict(progressAfter1s=first,progressAfter4s=second,completedHidden=done))
            call('Page.bringToFront');wait('window.__done')
            output=evaluate('window.__result');error=evaluate('window.__error')
            check(kind+': visible again, output identical to foreground control',not error and output==control,dict(output=output,error=error))
            urlopen(f'http://127.0.0.1:{port}/json/close/'+other['id']).read()
            if not args.baseline:
                for action,expected in [('abort','AbortError'),('loss','WebGLContextLostError')]:
                    evaluate(f"void window.__run('{kind}','{action}')")
                    other=json.load(urlopen(Request(f'http://127.0.0.1:{port}/json/new?about:blank',method='PUT')))
                    wait("document.visibilityState==='hidden'");wait('window.__done')
                    check(kind+': '+action+' interrupts while genuinely hidden',evaluate('window.__error')==expected)
                    check(kind+': '+action+' clears renderer flag/waiter',evaluate('!window.__testApp.renderer.isExporting && !window.__testApp.renderer._interruptExport'))
                    if action=='loss':
                        wait('window.__testApp.contextLost');time.sleep(.2);evaluate('window.__extension.restoreContext()')
                        wait('!window.__testApp.contextLost')
                        check(kind+': context recovery completes while hidden',evaluate('!window.__testApp.renderer.contextLost'))
                    call('Page.bringToFront');urlopen(f'http://127.0.0.1:{port}/json/close/'+other['id']).read()
        ws.close()
    finally:
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);proc.wait();server.shutdown()
for result in results:print(f"[{'PASS' if result['passed'] else 'FAIL'}] {result['name']}: {result['details']}")
print(f"SUITE Issue 7 real background: {sum(r['passed'] for r in results)}/{len(results)} passed")
raise SystemExit(0 if results and all(r['passed'] for r in results) else 1)
