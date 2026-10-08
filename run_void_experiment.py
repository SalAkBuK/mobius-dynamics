import http.server
import socketserver
import threading
import subprocess
import json
import time
import os
import base64
import urllib.parse
import numpy as np
from PIL import Image

PORT = 8798
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "center_void_captures")
os.makedirs(OUT_DIR, exist_ok=True)
done_event = threading.Event()
received_checkpoints = {}
final_meta = None

class VoidHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_checkpoints, final_meta
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save_image':
            params = urllib.parse.parse_qs(parsed.query)
            img_name = params.get('name', ['unknown'])[0]
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode('utf-8'))
            
            data_url = payload.get('dataUrl', '')
            if ',' in data_url:
                data_url = data_url.split(',', 1)[1]
            img_bytes = base64.b64decode(data_url)
            
            file_path = os.path.join(OUT_DIR, f"{img_name}.png")
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            
            received_checkpoints[img_name] = {
                'path': file_path,
                'meta': payload.get('meta', {})
            }
            print(f"[OK] Saved {img_name}.png ({len(img_bytes)//1024} KB)")

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        elif parsed.path == '/finish':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            final_meta = json.loads(body.decode('utf-8'))
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

def analyze_and_crop():
    report = {}
    cx, cy = 600, 400 # Center of 1200x800 canvas
    
    # Grid coordinates
    y, x = np.ogrid[:800, :1200]
    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
    
    # Zones:
    # 1. Deep origin: r < 20 px (r_math < 0.030)
    # 2. Previous Discarded Disk: r < 66 px (r_math < 0.100, where r^2 < 0.010 was active)
    # 3. Transition Zone: 66 <= r < 100 px (0.100 <= r_math < 0.151)
    # 4. Caustic Ring: 100 <= r < 150 px (0.151 <= r_math < 0.227)
    mask_deep = dist < 20
    mask_discard_disk = dist < 66
    mask_transition = (dist >= 66) & (dist < 100)
    mask_caustic = (dist >= 100) & (dist < 150)
    
    for name, data in received_checkpoints.items():
        img_path = data['path']
        img = Image.open(img_path).convert('RGB')
        arr = np.array(img)
        
        # 1. Generate 400x400 close crop of central region [cx-200:cx+200, cy-200:cy+200]
        crop_400 = img.crop((cx - 200, cy - 200, cx + 200, cy + 200))
        crop_path = os.path.join(OUT_DIR, f"crop_{name}.png")
        crop_400.save(crop_path)
        
        # 2. Generate 200x200 super-close crop of the exact former discard disk
        crop_200 = img.crop((cx - 100, cy - 100, cx + 100, cy + 100))
        crop_200_zoom = crop_200.resize((400, 400), Image.Resampling.NEAREST)
        super_crop_path = os.path.join(OUT_DIR, f"super_crop_{name}.png")
        crop_200_zoom.save(super_crop_path)
        
        # 3. Channel statistics per zone
        def zone_stats(mask):
            pixels = arr[mask]
            # Luminance = 0.2126 R + 0.7152 G + 0.0722 B
            lum = 0.2126 * pixels[:, 0] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 2]
            return {
                'min_lum': round(float(np.min(lum)), 2),
                'max_lum': round(float(np.max(lum)), 2),
                'mean_lum': round(float(np.mean(lum)), 2),
                'std_lum': round(float(np.std(lum)), 2),
                'max_r': int(np.max(pixels[:, 0])),
                'max_g': int(np.max(pixels[:, 1])),
                'max_b': int(np.max(pixels[:, 2])),
                'non_bg_pixel_count': int(np.sum(pixels[:, 2] > 10)) # Background blue is ~6-7
            }
        
        stats = {
            'meta': data['meta'],
            'deep_origin_r_lt_20px': zone_stats(mask_deep),
            'former_discard_disk_r_lt_66px': zone_stats(mask_discard_disk),
            'transition_zone_66_to_100px': zone_stats(mask_transition),
            'caustic_ring_100_to_150px': zone_stats(mask_caustic),
            'full_crop_path': crop_path,
            'super_crop_path': super_crop_path
        }
        report[name] = stats
        print(f"\n--- Statistics for {name} ---")
        print(f"  Former Discard Disk (r < 66px): Max Blue={stats['former_discard_disk_r_lt_66px']['max_b']}, Mean Lum={stats['former_discard_disk_r_lt_66px']['mean_lum']}, Non-BG Pixels={stats['former_discard_disk_r_lt_66px']['non_bg_pixel_count']} / {np.sum(mask_discard_disk)}")
        print(f"  Transition Zone (66-100px):     Max Blue={stats['transition_zone_66_to_100px']['max_b']}, Mean Lum={stats['transition_zone_66_to_100px']['mean_lum']}, Non-BG Pixels={stats['transition_zone_66_to_100px']['non_bg_pixel_count']}")
        print(f"  Caustic Ring (100-150px):       Max Blue={stats['caustic_ring_100_to_150px']['max_b']}, Mean Lum={stats['caustic_ring_100_to_150px']['mean_lum']}")

    # Save comprehensive report
    report_file = os.path.join(DIRECTORY, "void_experiment_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Analysis report saved to {report_file}")

def main():
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), VoidHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(1.0)

    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=d3d11",
        "--window-size=1200,800",
        f"http://localhost:{PORT}/void_experiment.html"
    ]

    print(f"Launching Chrome headless to run 20-second progressive accumulation experiment...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for completion (20 seconds of accumulation ~ 1200 frames takes ~25-40s real time)
    success = done_event.wait(timeout=75)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success:
        print("ERROR: Void experiment timed out or failed.")
        return False

    print("\nProcessing captured checkpoints and analyzing central dynamics...")
    analyze_and_crop()
    return True

if __name__ == '__main__':
    main()
