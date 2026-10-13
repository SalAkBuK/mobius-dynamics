import http.server, socketserver, threading, subprocess, time, os

PORT = 8799
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(('', PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--headless=new',
    '--no-sandbox',
    '--use-gl=angle',
    '--use-angle=d3d11',
    '--window-size=1200,800',
    '--dump-dom',
    f'http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace'
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if any(k in line for k in ['dbg-res', 'dbg-fps', 'capture-container', 'dbg-zoom']):
        print(line[:120])

httpd.shutdown()
