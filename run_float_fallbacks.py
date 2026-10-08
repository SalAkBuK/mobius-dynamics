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

PORT = 8795
DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
out_dir = os.path.join(DIRECTORY, "fallback_captures")
os.makedirs(out_dir, exist_ok=True)
done_event = threading.Event()
received_images = {}
final_meta = None

class FallbackHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        global received_images, final_meta
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/save_image':
            params = urllib.parse.parse_qs(parsed.query)
            img_name = params.get('name', ['unknown'])[0]
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            
            data_str = body.decode('utf-8')
            if ',' in data_str:
                data_str = data_str.split(',', 1)[1]
            img_bytes = base64.b64decode(data_str)
            
            file_path = os.path.join(out_dir, f"{img_name}.png")
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            received_images[img_name] = file_path
            print(f"Received fallback capture: {img_name}.png ({len(img_bytes)//1024} KB)")

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

html_page = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Float Format Fallback Validation Suite</title>
<style>
  body { margin: 0; background: #010307; color: #8da4c4; font-family: monospace; }
  canvas { width: 1200px; height: 800px; display: block; }
  #status { position: absolute; top: 10px; left: 10px; font-size: 14px; background: rgba(0,0,0,0.85); padding: 8px 12px; border: 1px solid #224477; border-radius: 4px; }
</style>
</head>
<body>
<div id="status">Initializing float fallback suite...</div>
<canvas id="c" width="1200" height="800"></canvas>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

function nextFrame() {
  return new Promise(r => requestAnimationFrame(r));
}

async function uploadCanvas(name) {
  const canvas = document.getElementById('c');
  const dataUrl = canvas.toDataURL('image/png');
  await fetch(`/save_image?name=${name}`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: dataUrl
  });
}

window.onload = async function() {
  const canvas = document.getElementById('c');
  const statusEl = document.getElementById('status');

  const math = new MathSystem();
  math.setMorphology('lace');
  math.setSymmetry(16);
  math.evolving = false;

  const renderer = new MobiusRenderer(canvas);
  const gl = renderer.gl;

  // Query and record all active extensions
  const activeExtensions = {
    EXT_color_buffer_float: !!gl.getExtension('EXT_color_buffer_float'),
    EXT_color_buffer_half_float: !!gl.getExtension('EXT_color_buffer_half_float'),
    EXT_float_blend: !!gl.getExtension('EXT_float_blend'),
    OES_texture_float_linear: !!gl.getExtension('OES_texture_float_linear'),
    EXT_disjoint_timer_query_webgl2: !!gl.getExtension('EXT_disjoint_timer_query_webgl2')
  };

  const formats = [
    {
      id: 'rgba32f',
      name: 'RGBA32F',
      setup: () => {
        renderer.floatCap = {
          internalFormat: gl.RGBA32F,
          format: gl.RGBA,
          type: gl.FLOAT,
          name: 'RGBA32F',
          label: 'Native RGBA32F Float Blending',
          photonScale: 1.0
        };
        renderer.floatFormat = 'RGBA32F';
        renderer.floatCapability = 'Native RGBA32F Float Blending';
        renderer.initTextures();
      }
    },
    {
      id: 'rgba16f',
      name: 'RGBA16F',
      setup: () => {
        renderer.floatCap = {
          internalFormat: gl.RGBA16F,
          format: gl.RGBA,
          type: gl.HALF_FLOAT,
          name: 'RGBA16F',
          label: 'RGBA16F Half-Float Blending Fallback',
          photonScale: 1.0
        };
        renderer.floatFormat = 'RGBA16F';
        renderer.floatCapability = 'RGBA16F Half-Float Blending Fallback';
        renderer.initTextures();
      }
    },
    {
      id: 'rgba8',
      name: 'RGBA8',
      setup: () => {
        renderer.floatCap = {
          internalFormat: gl.RGBA8,
          format: gl.RGBA,
          type: gl.UNSIGNED_BYTE,
          name: 'RGBA8',
          label: 'Reduced Precision RGBA8 Fallback',
          photonScale: 25.0
        };
        renderer.floatFormat = 'RGBA8';
        renderer.floatCapability = 'Reduced Precision RGBA8 Fallback';
        renderer.initTextures();
      }
    }
  ];

  // Target accumulation times: 1s (~60 frames), 3s (~180 frames), 10s (~600 frames)
  const checkpoints = [
    { label: '1s', targetFrames: 60 },
    { label: '3s', targetFrames: 180 },
    { label: '10s', targetFrames: 600 }
  ];

  const meta = { activeExtensions, formats: {} };

  for (const fmt of formats) {
    statusEl.innerText = `Configuring format path: ${fmt.name}...`;
    fmt.setup();
    renderer.adaptive.setMode('standard');
    renderer.clearAccumulation();

    meta.formats[fmt.id] = { name: fmt.name, checkpoints: {} };

    let currentFrame = 0;
    for (const cp of checkpoints) {
      statusEl.innerText = `Accumulating ${fmt.name} to ${cp.label} (${cp.targetFrames} frames)...`;
      while (currentFrame < cp.targetFrames - 1) {
        math.update(0.016, renderer.zoom);
        renderer.render(math, 0.016);
        currentFrame++;
        await nextFrame();
      }

      // Synchronous render & capture on boundary frame
      math.update(0.016, renderer.zoom);
      renderer.render(math, 0.016);
      currentFrame++;

      const capName = `fallback_${fmt.id}_${cp.label}`;
      statusEl.innerText = `Saving ${capName}...`;
      await uploadCanvas(capName);

      meta.formats[fmt.id].checkpoints[cp.label] = {
        accumFrames: renderer.accumulationFrames,
        particles: renderer.numParticles,
        steps: renderer.stepsPerFrame,
        deposits: renderer.numParticles * renderer.stepsPerFrame * renderer.accumulationFrames
      };
    }
  }

  statusEl.innerText = "Finishing fallback test suite...";
  await fetch('/finish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(meta)
  });
  statusEl.innerText = "Fallback validation complete!";
};
</script>
</body>
</html>
"""

def compute_ssim(img1, img2):
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    im1_gray = 0.2989 * img1[:, :, 0] + 0.5870 * img1[:, :, 1] + 0.1140 * img1[:, :, 2]
    im2_gray = 0.2989 * img2[:, :, 0] + 0.5870 * img2[:, :, 1] + 0.1140 * img2[:, :, 2]
    mu1 = np.mean(im1_gray)
    mu2 = np.mean(im2_gray)
    sigma1_sq = np.var(im1_gray)
    sigma2_sq = np.var(im2_gray)
    sigma12 = np.mean((im1_gray - mu1) * (im2_gray - mu2))
    num = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
    den = (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)
    return float(num / den)

def compute_psnr(img1, img2):
    mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
    if mse == 0:
        return 100.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))

def main():
    html_path = os.path.join(DIRECTORY, "fallback_test.html")
    with open(html_path, "w") as f:
        f.write(html_page)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), FallbackHandler)
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
        f"http://localhost:{PORT}/fallback_test.html"
    ]

    print("Launching Chrome for Float Fallback Validation Suite...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 3 formats x 600 frames = 1800 frames total (~30-40s at 60 FPS)
    success = done_event.wait(timeout=90)
    server.shutdown()
    if proc.poll() is None:
        proc.terminate()

    if not success or final_meta is None:
        print("ERROR: Float fallback test failed or timed out.")
        return False

    print("\nProcessing captured fallback frames & computing comparative quality...")
    analysis = {
        'activeExtensions': final_meta['activeExtensions'],
        'comparisons': {}
    }

    # Compare RGBA16F and RGBA8 against reference RGBA32F at each checkpoint (1s, 3s, 10s)
    checkpoints = ['1s', '3s', '10s']
    for cp in checkpoints:
        file_32f = os.path.join(out_dir, f"fallback_rgba32f_{cp}.png")
        file_16f = os.path.join(out_dir, f"fallback_rgba16f_{cp}.png")
        file_8 = os.path.join(out_dir, f"fallback_rgba8_{cp}.png")

        img_32f = Image.open(file_32f).convert('RGB')
        img_16f = Image.open(file_16f).convert('RGB')
        img_8 = Image.open(file_8).convert('RGB')

        arr_32f = np.array(img_32f)
        arr_16f = np.array(img_16f)
        arr_8 = np.array(img_8)

        # Metrics vs RGBA32F reference
        ssim_16f = compute_ssim(arr_32f, arr_16f)
        psnr_16f = compute_psnr(arr_32f, arr_16f)

        ssim_8 = compute_ssim(arr_32f, arr_8)
        psnr_8 = compute_psnr(arr_32f, arr_8)

        # Dynamic range & intensity statistics
        analysis['comparisons'][cp] = {
            'rgba16f_vs_rgba32f': {
                'ssim': round(ssim_16f, 4),
                'psnr_db': round(psnr_16f, 2),
                'mean_intensity_ratio': round(float(arr_16f.mean() / max(1e-5, arr_32f.mean())), 4),
                'max_pixel_16f': int(arr_16f.max()),
                'max_pixel_32f': int(arr_32f.max())
            },
            'rgba8_vs_rgba32f': {
                'ssim': round(ssim_8, 4),
                'psnr_db': round(psnr_8, 2),
                'mean_intensity_ratio': round(float(arr_8.mean() / max(1e-5, arr_32f.mean())), 4),
                'max_pixel_8': int(arr_8.max()),
                'max_pixel_32f': int(arr_32f.max()),
                'zero_pixel_ratio_8': round(float(np.mean(arr_8 == 0)), 4),
                'zero_pixel_ratio_32f': round(float(np.mean(arr_32f == 0)), 4)
            }
        }
        print(f"[{cp}] RGBA16F vs RGBA32F: SSIM={ssim_16f:.4f}, PSNR={psnr_16f:.2f} dB")
        print(f"[{cp}] RGBA8   vs RGBA32F: SSIM={ssim_8:.4f}, PSNR={psnr_8:.2f} dB")

        # Create 3-way side-by-side composite
        w, h = img_32f.size
        comp = Image.new('RGB', (w * 3, h))
        comp.paste(img_32f, (0, 0))
        comp.paste(img_16f, (w, 0))
        comp.paste(img_8, (w * 2, 0))
        comp_file = os.path.join(out_dir, f"triptych_{cp}_32F_vs_16F_vs_8.png")
        comp.save(comp_file)

    report_file = os.path.join(DIRECTORY, "float_fallbacks_report.json")
    with open(report_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nFallback analysis report saved to {report_file}")
    print(f"Triptych composites saved to {out_dir}")
    return True

if __name__ == '__main__':
    main()
