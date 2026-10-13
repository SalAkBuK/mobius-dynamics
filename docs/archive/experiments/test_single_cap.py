import http.server, socketserver, threading, subprocess, time, os, base64

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
import re
m = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', res.stdout)
if m:
    b64 = m.group(1)
    print('Found b64, len:', len(b64))
    raw = base64.b64decode(b64)
    with open('test_cap_full.png', 'wb') as f:
        f.write(raw)
    from PIL import Image
    import numpy as np
    img = Image.open('test_cap_full.png')
    arr = np.array(img)
    print('test_cap_full.png min:', arr.min(), 'max:', arr.max(), 'mean:', arr.mean())
else:
    print('No b64 found')

httpd.shutdown()
