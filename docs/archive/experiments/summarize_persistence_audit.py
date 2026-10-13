import json

with open('persistence_audit/real_persistence_audit_report.json', 'r') as f:
    data = json.load(f)

workloads = ['brute_force', 'prod_150k_8', 'exp_155k_8', 'exp_160k_8', 'exp_165k_8']
checkpoints = ['1s', '3s', '5s', '10s', '20s', '30s']

print('=== PRESENTATION FPS ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['presentation_fps']:5.1f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== GPU FRAME TIME (MS) ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['gpu_frame_time_ms'] or 0.0:5.2f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== HARD EDGE COUNT (>15) ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['hard_edge_count_gt15']:6d}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== VISIBLE FEATURE PIXELS (>5) ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['visible_feature_pixels_gt5']:7d}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== MEAN FILAMENT LUMINANCE ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['mean_filament_luminance']:6.2f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== FAINT ENVELOPE LUMINANCE ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['faint_envelope_luminance']:6.2f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== CAUSTIC RIDGE LUMINANCE ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['caustic_ridge_luminance']:6.2f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== EFFECTIVE ACCUMULATED PHOTONS (EQUILIBRIUM FORMULA) ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['effective_accumulated_photons']//1000000:5d}M" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== STEADY STATE EQUILIBRIUM % ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['steady_state_equilibrium_pct']:5.1f}%" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))

print('\n=== SSIM VS BRUTE FORCE ===')
for w in workloads:
    row = [f"{data['workload_measurements'][w]['checkpoints'][cp]['ssim_vs_brute'] if data['workload_measurements'][w]['checkpoints'][cp]['ssim_vs_brute'] is not None else 1.0:6.4f}" for cp in checkpoints]
    print(f"{w:15s}: " + " ".join(row))
