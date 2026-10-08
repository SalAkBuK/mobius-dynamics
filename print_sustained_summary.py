import json

with open('sustained_10min_report.json') as f:
    d = json.load(f)

print(f"{'Time':>6} | {'Tier':<8} | {'GPU EMA':>8} | {'FPS':>4} | {'Particles':>9} | {'Steps':>5} | {'Deposits':>9} | {'DPR':>4} | {'Heap':>7}")
print("-" * 75)
for s in d['samples30s']:
    print(f"{s['elapsedSec']:>5}s | {s['tier']:<8} | {s['gpuEma']:>6.2f}ms | {s['fps']:>4} | {s['particles']:>9} | {s['steps']:>5} | {s['deposits']:>9} | {s['dpr']:>4.1f} | {s['jsHeapUsedMb']:>5.1f}MB")
