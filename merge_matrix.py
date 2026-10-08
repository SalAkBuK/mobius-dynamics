import json

with open('upper_matrix_data.json') as f:
    upper = json.load(f)
with open('matrix_benchmark_data.json') as f:
    lower = json.load(f)

lower_filtered = [r for r in lower if r['particles'] in (75000, 40000)]
complete = upper + lower_filtered

with open('benchmark_matrix_complete.json', 'w') as f:
    json.dump(complete, f, indent=2)

print(f"Complete matrix has {len(complete)} entries:\n")
header = f"{'Particles':>9} | {'Steps':>5} | {'Avg FPS':>7} | {'1% Low':>7} | {'CPU ms':>7} | {'GPU ms':>7} | {'Sim ms':>7} | {'Splat ms':>8} | {'Post ms':>7} | {'Total ms':>8}"
print(header)
print("-" * len(header))
for r in complete:
    print(f"{r['particles']:>9} | {r['steps']:>5} | {r['avgFps']:>7.1f} | {r['fps1Low']:>7.1f} | {r['avgCpuMs']:>7.2f} | {r['avgGpuMs']:>7.2f} | {r['simGpuMs']:>7.2f} | {r['splatGpuMs']:>8.2f} | {r['postProcessingGpuMs']:>7.2f} | {r['totalFrameMs']:>8.2f}")
