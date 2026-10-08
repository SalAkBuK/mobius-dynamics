import http.server, socketserver, threading, subprocess, time, json

html_test = """
<!DOCTYPE html>
<html>
<body>
<div id="results">Running tests...</div>
<script type="module">
import { MathSystem } from './math.js';
import { MobiusRenderer } from './renderer.js';

const math = new MathSystem();
const initialA = math.a.clone();
const initialC = math.c.clone();

const tests = [];

// Test 1: Pointer perturbation changes coefficients
math.setPointer(0.5, -0.5);
math.update(0.1);
const pertA = math.a.clone();
const aDiff = Math.hypot(pertA.r - initialA.r, pertA.i - initialA.i);
tests.push({
  name: "Pointer Perturbation",
  passed: aDiff > 0.001,
  details: `Delta a: ${aDiff.toFixed(5)}`
});

// Test 2: Shock injection changes coefficients significantly
const beforeShock = math.c.clone();
math.injectShock(1.0, 0.0);
math.update(0.016);
const afterShock = math.c.clone();
const shockDiff = Math.hypot(afterShock.r - beforeShock.r, afterShock.i - beforeShock.i);
tests.push({
  name: "Click Shock Injection",
  passed: shockDiff > 0.05,
  details: `Delta c on shock: ${shockDiff.toFixed(4)}`
});

// Test 3: Shock relaxation
for (let i = 0; i < 180; i++) {
  math.update(0.016);
}
tests.push({
  name: "Shock Relaxation",
  passed: math.shockMag < 0.02,
  details: `Remaining shockMag: ${math.shockMag.toFixed(5)}`
});

// Test 4: Symmetry change
math.setSymmetry(24);
tests.push({
  name: "Symmetry Order Change",
  passed: math.n === 24 && math.omegas.length === 24,
  details: `n = ${math.n}, roots count = ${math.omegas.length}`
});

// Test 5: Coefficient offset via sliders
math.setCoefficientOffset('a', 0.25, 0.15);
math.update(0.016);
tests.push({
  name: "User Coefficient Control",
  passed: Math.abs(math.userOffsetA.r - 0.25) < 1e-4,
  details: `User offset a: ${math.userOffsetA.format()}`
});

document.getElementById('results').innerText = JSON.stringify(tests, null, 2);
window._testsCompleted = true;
</script>
</body>
</html>
"""

with open("test_math_units.html", "w") as f:
    f.write(html_test)

PORT = 8796
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--window-size=800,600",
    "--dump-dom",
    f"http://localhost:{PORT}/test_math_units.html"
]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
for line in res.stdout.splitlines():
    if "Pointer" in line or "Shock" in line or "Symmetry" in line or "User" in line or "passed" in line:
        print(line.strip())

httpd.shutdown()
