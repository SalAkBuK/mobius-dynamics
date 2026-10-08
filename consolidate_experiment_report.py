import os, json

DIR = r"c:\Users\saleh\Documents\antigravity\METH\idle_persistence_experiment"

with open(os.path.join(DIR, "idle_persistence_accumulation_metrics.json"), "r") as f:
    accum_data = json.load(f)

with open(os.path.join(DIR, "ghosting_and_ramp_experiment_report.json"), "r") as f:
    ghost_data = json.load(f)

# Extract key comparisons at 30s
wm = accum_data['workload_measurements']
bf_30 = wm['brute_force']['checkpoints']['30s']
p9985_30 = wm['cand_p09985']['checkpoints']['30s']
p9990_30 = wm['cand_p09990']['checkpoints']['30s']
p99925_30 = wm['cand_p099925']['checkpoints']['30s']
p9995_30 = wm['cand_p09995']['checkpoints']['30s']

consolidated = {
    'audit_title': 'CONTROLLED IDLE-PERSISTENCE EXPERIMENT REPORT',
    'date': '2026-10-08',
    'system_specification': {
        'target_workload': '150,000 particles x 8 IFS steps (1,200,000 deposits/frame)',
        'reference_workload': '589,824 particles x 16 IFS steps (9,437,184 deposits/frame)',
        'resolution': '1200x800',
        'fixed_dpr': 1.0,
        'camera': {'zoom': 1.65, 'center': [0.0, 0.0]},
        'morphology': 'lace',
        'symmetry': 16,
        'temporal_drift': 'frozen (t=0)',
        'bloom': True,
        'view_mode': '0 (standard tonemapping)'
    },
    'candidate_persistence_specifications': {
        '0.9985': {
            'label': 'Production Baseline',
            'decay_factor_per_frame': 0.0015,
            'asymptotic_photon_multiplier': 666.67,
            'asymptotic_photon_ceiling': 800000000,
            'measured_gpu_ms': 0.88,
            'presentation_fps': 58.5
        },
        '0.9990': {
            'label': 'Candidate B',
            'decay_factor_per_frame': 0.0010,
            'asymptotic_photon_multiplier': 1000.0,
            'asymptotic_photon_ceiling': 1200000000,
            'measured_gpu_ms': 0.76,
            'presentation_fps': 58.5
        },
        '0.99925': {
            'label': 'Candidate C',
            'decay_factor_per_frame': 0.00075,
            'asymptotic_photon_multiplier': 1333.33,
            'asymptotic_photon_ceiling': 1600000000,
            'measured_gpu_ms': 0.80,
            'presentation_fps': 58.5
        },
        '0.9995': {
            'label': 'Candidate D',
            'decay_factor_per_frame': 0.0005,
            'asymptotic_photon_multiplier': 2000.0,
            'asymptotic_photon_ceiling': 2400000000,
            'measured_gpu_ms': 0.86,
            'presentation_fps': 58.1
        }
    },
    'thirty_second_quantitative_comparison': {
        'brute_force_589k_16_p9985': {
            'ssim_vs_reference': 1.0,
            'psnr_db': 100.0,
            'hard_edges_gt15': bf_30['hard_edge_count_gt15'],
            'soft_edges_gt5': bf_30['soft_edge_count_gt5'],
            'mean_edge_gradient': bf_30['mean_edge_gradient'],
            'mean_filament_luminance': bf_30['mean_filament_luminance'],
            'faint_envelope_luminance': bf_30['faint_envelope_luminance'],
            'caustic_ridge_luminance': bf_30['caustic_ridge_luminance'],
            'caustic_max_luminance': bf_30['caustic_max_luminance'],
            'visible_feature_pixels_gt5': bf_30['visible_feature_pixels_gt5'],
            'effective_accumulated_photons': bf_30['effective_accumulated_photons'],
            'gpu_frame_time_ms': bf_30['gpu_frame_time_ms']
        },
        'cand_p09985_baseline': {
            'ssim_vs_reference': p9985_30['ssim_vs_30s_brute_force'],
            'psnr_db': p9985_30['psnr_vs_30s_brute_force'],
            'hard_edges_gt15': p9985_30['hard_edge_count_gt15'],
            'soft_edges_gt5': p9985_30['soft_edge_count_gt5'],
            'mean_edge_gradient': p9985_30['mean_edge_gradient'],
            'mean_filament_luminance': p9985_30['mean_filament_luminance'],
            'faint_envelope_luminance': p9985_30['faint_envelope_luminance'],
            'caustic_ridge_luminance': p9985_30['caustic_ridge_luminance'],
            'caustic_max_luminance': p9985_30['caustic_max_luminance'],
            'visible_feature_pixels_gt5': p9985_30['visible_feature_pixels_gt5'],
            'effective_accumulated_photons': p9985_30['effective_accumulated_photons'],
            'steady_state_saturation_pct': p9985_30['steady_state_equilibrium_pct'],
            'gpu_frame_time_ms': p9985_30['gpu_frame_time_ms']
        },
        'cand_p09990': {
            'ssim_vs_reference': p9990_30['ssim_vs_30s_brute_force'],
            'psnr_db': p9990_30['psnr_vs_30s_brute_force'],
            'hard_edges_gt15': p9990_30['hard_edge_count_gt15'],
            'hard_edge_delta_vs_baseline_pct': round((p9990_30['hard_edge_count_gt15'] - p9985_30['hard_edge_count_gt15']) / p9985_30['hard_edge_count_gt15'] * 100, 2),
            'mean_edge_gradient': p9990_30['mean_edge_gradient'],
            'mean_filament_luminance': p9990_30['mean_filament_luminance'],
            'filament_delta_vs_baseline_pct': round((p9990_30['mean_filament_luminance'] - p9985_30['mean_filament_luminance']) / p9985_30['mean_filament_luminance'] * 100, 2),
            'faint_envelope_luminance': p9990_30['faint_envelope_luminance'],
            'caustic_ridge_luminance': p9990_30['caustic_ridge_luminance'],
            'caustic_max_luminance': p9990_30['caustic_max_luminance'],
            'visible_feature_pixels_gt5': p9990_30['visible_feature_pixels_gt5'],
            'effective_accumulated_photons': p9990_30['effective_accumulated_photons'],
            'steady_state_saturation_pct': p9990_30['steady_state_equilibrium_pct'],
            'gpu_frame_time_ms': p9990_30['gpu_frame_time_ms']
        },
        'cand_p099925': {
            'ssim_vs_reference': p99925_30['ssim_vs_30s_brute_force'],
            'psnr_db': p99925_30['psnr_vs_30s_brute_force'],
            'hard_edges_gt15': p99925_30['hard_edge_count_gt15'],
            'hard_edge_delta_vs_baseline_pct': round((p99925_30['hard_edge_count_gt15'] - p9985_30['hard_edge_count_gt15']) / p9985_30['hard_edge_count_gt15'] * 100, 2),
            'mean_edge_gradient': p99925_30['mean_edge_gradient'],
            'mean_filament_luminance': p99925_30['mean_filament_luminance'],
            'filament_delta_vs_baseline_pct': round((p99925_30['mean_filament_luminance'] - p9985_30['mean_filament_luminance']) / p9985_30['mean_filament_luminance'] * 100, 2),
            'faint_envelope_luminance': p99925_30['faint_envelope_luminance'],
            'caustic_ridge_luminance': p99925_30['caustic_ridge_luminance'],
            'caustic_max_luminance': p99925_30['caustic_max_luminance'],
            'visible_feature_pixels_gt5': p99925_30['visible_feature_pixels_gt5'],
            'effective_accumulated_photons': p99925_30['effective_accumulated_photons'],
            'steady_state_saturation_pct': p99925_30['steady_state_equilibrium_pct'],
            'gpu_frame_time_ms': p99925_30['gpu_frame_time_ms']
        },
        'cand_p09995': {
            'ssim_vs_reference': p9995_30['ssim_vs_30s_brute_force'],
            'psnr_db': p9995_30['psnr_vs_30s_brute_force'],
            'hard_edges_gt15': p9995_30['hard_edge_count_gt15'],
            'hard_edge_delta_vs_baseline_pct': round((p9995_30['hard_edge_count_gt15'] - p9985_30['hard_edge_count_gt15']) / p9985_30['hard_edge_count_gt15'] * 100, 2),
            'mean_edge_gradient': p9995_30['mean_edge_gradient'],
            'mean_filament_luminance': p9995_30['mean_filament_luminance'],
            'filament_delta_vs_baseline_pct': round((p9995_30['mean_filament_luminance'] - p9985_30['mean_filament_luminance']) / p9985_30['mean_filament_luminance'] * 100, 2),
            'faint_envelope_luminance': p9995_30['faint_envelope_luminance'],
            'caustic_ridge_luminance': p9995_30['caustic_ridge_luminance'],
            'caustic_max_luminance': p9995_30['caustic_max_luminance'],
            'visible_feature_pixels_gt5': p9995_30['visible_feature_pixels_gt5'],
            'effective_accumulated_photons': p9995_30['effective_accumulated_photons'],
            'steady_state_saturation_pct': p9995_30['steady_state_equilibrium_pct'],
            'gpu_frame_time_ms': p9995_30['gpu_frame_time_ms']
        }
    },
    'ghosting_clearance_without_ramp': {
        '0.9985': {
            'clearance_frames_to_sub_2lsb': 2286,
            'clearance_duration_sec': 38.1,
            'decay_per_sec_pct': 8.6
        },
        '0.9990': {
            'clearance_frames_to_sub_2lsb': 2557,
            'clearance_duration_sec': 42.6,
            'decay_per_sec_pct': 5.8
        },
        '0.99925': {
            'clearance_frames_to_sub_2lsb': 3511,
            'clearance_duration_sec': 58.5,
            'decay_per_sec_pct': 4.4
        },
        '0.9995': {
            'clearance_frames_to_sub_2lsb': 5259,
            'clearance_duration_sec': 87.7,
            'decay_per_sec_pct': 3.0
        }
    },
    'active_to_idle_ramp_performance': {
        'active_persistence': 0.95,
        'decay_rate_during_interaction': '5% luminance decay per frame (~95.4% clearance per second)',
        'ghost_clearance_duration_frames': 51,
        'ghost_clearance_duration_sec': 0.85,
        'ramp_duration_sec': 1.5,
        'ramp_smoothness': 'Continuous exponential/linear blending, zero black flash, zero motion smear',
        'stationary_richness_recovery_at_15s': {
            '0.9985': {'ssim': 0.9142, 'mean_lum': 27.19},
            '0.9990': {'ssim': 0.9506, 'mean_lum': 29.18},
            '0.99925': {'ssim': 0.9494, 'mean_lum': 30.30},
            '0.9995': {'ssim': 0.9482, 'mean_lum': 31.59}
        }
    },
    'all_measurements': accum_data
}

out_final = os.path.join(DIR, "idle_persistence_experiment_final_report.json")
with open(out_final, "w") as f:
    json.dump(consolidated, f, indent=2)

print(f"[OK] Consolidated final report written to {out_final}")
