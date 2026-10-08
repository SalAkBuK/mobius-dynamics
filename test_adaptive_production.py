import http.server
import socketserver
import threading
import subprocess
import json
import time
import os

PORT = 8785
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
report_data = None
done_event = threading.Event()

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global report_data
        if self.path == '/test_report':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            report_data = json.loads(body.decode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
            done_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def main():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", PORT), TestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    url = f"http://localhost:{PORT}/test_adaptive.html"

    cmd = [
        chrome_path,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        url
    ]

    print(f"Launching Chrome to run adaptive validation suite: {url}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    success = done_event.wait(timeout=50)
    httpd.shutdown()

    if proc.poll() is None:
        proc.terminate()

    if not success or report_data is None:
        print("ERROR: Test suite timed out or failed to post report.")
        return False

    report_path = os.path.join(DIRECTORY, "adaptive_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print("\n" + "="*70)
    print("PRODUCTION ADAPTIVE RENDERER VALIDATION REPORT")
    print("="*70)
    print(json.dumps(report_data, indent=2))
    print("="*70)
    return True

if __name__ == '__main__':
    main()
