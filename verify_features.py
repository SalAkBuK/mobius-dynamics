import http.server
import socketserver
import threading
import subprocess
import time
import base64
import re
import os

PORT = 8771
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    def log_message(self, format, *args):
        pass

def run_tests():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", PORT), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(1.5)

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    tests = [
        ("full", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace"),
        ("n8", f"http://localhost:{PORT}/index.html?capture=1&n=8&morph=knot"),
        ("n24", f"http://localhost:{PORT}/index.html?capture=1&n=24&morph=storm"),
        ("crown", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=crown"),
        ("nobloom", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&nobloom=1"),
        ("raw", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&raw=1"),
        ("zoom_l1", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&zoom=4.5&cx=0.18&cy=0.08"),
        ("zoom_l2", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&zoom=14&cx=0.16&cy=0.085"),
        ("zoom_l3", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&zoom=45&cx=0.148&cy=0.088"),
        ("zoom_deep", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&zoom=130&cx=0.1422&cy=0.0894"),
        ("debug", f"http://localhost:{PORT}/index.html?capture=1&n=16&morph=lace&debug=1")
    ]

    for name, url in tests:
        print(f"Testing {name}...")
        cmd = [
            chrome_path,
            "--headless=new",
            "--no-sandbox",
            "--use-gl=angle",
            "--use-angle=d3d11",
            "--window-size=1200,800",
            "--dump-dom",
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        m = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', res.stdout)
        if not m or len(m.group(1)) < 50000:
            time.sleep(1.0)
            res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
            m = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', res.stdout)

        if m:
            b64 = m.group(1)
            out_file = os.path.join(DIRECTORY, f"verify_{name}.png")
            with open(out_file, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"Saved verify_{name}.png ({len(b64)} b64 chars)")
        else:
            print(f"Failed to capture {name} via dump-dom")
            
        # Also take full browser screenshot for full and debug
        if name in ("full", "debug"):
            ss_name = "full_ui_screenshot.png" if name == "full" else "debug_ui_screenshot.png"
            ss_file = os.path.join(DIRECTORY, ss_name)
            cmd_ss = [
                chrome_path,
                "--headless=new",
                "--no-sandbox",
                "--use-gl=angle",
                "--use-angle=d3d11",
                "--window-size=1200,800",
                f"--screenshot={ss_file}",
                url
            ]
            subprocess.run(cmd_ss, capture_output=True, text=True, errors='ignore')
            print(f"Saved {ss_name}")

    httpd.shutdown()

if __name__ == "__main__":
    run_tests()
