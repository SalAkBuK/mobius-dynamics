import os, glob
import numpy as np
from PIL import Image

DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH\idle_persistence_experiment"

candidates = [
    ('cand_p09985', 0.9985, 'Baseline (0.9985)'),
    ('cand_p09990', 0.9990, 'Candidate B (0.9990)'),
    ('cand_p099925', 0.99925, 'Candidate C (0.99925)'),
    ('cand_p09995', 0.9995, 'Candidate D (0.9995)')
]

def compute_ssim(img1, img2):
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu1 = np.mean(img1)
    mu2 = np.mean(img2)
    s1_sq = np.var(img1)
    s2_sq = np.var(img2)
    s12 = np.mean((img1 - mu1) * (img2 - mu2))
    num = (2 * mu1 * mu2 + c1) * (2 * s12 + c2)
    den = (mu1**2 + mu2**2 + c1) * (s1_sq + s2_sq + c2)
    return float(num / den)

print("==========================================================================")
print("ANALYZING SAVED GHOSTING RECOVERY IMAGES (WITHOUT RAMP)")
print("==========================================================================")

checkpoints = [
    ('01_perturbed_peak', 0.0, 0),
    ('rec_0.5s', 0.5, 30),
    ('rec_1s', 1.0, 60),
    ('rec_2s', 2.0, 120),
    ('rec_5s', 5.0, 300),
    ('rec_10s', 10.0, 600),
    ('rec_20s', 20.0, 1200),
    ('rec_30s', 30.0, 1800)
]

for c_id, p_val, c_lbl in candidates:
    base_file = os.path.join(DIRECTORY, f"ghost_no_ramp_{c_id}_00_baseline_15s.png")
    if not os.path.exists(base_file):
        print(f"Missing {base_file}")
        continue
    base_im = np.array(Image.open(base_file).convert('RGB'), dtype=float)
    base_gray = 0.2989 * base_im[:,:,0] + 0.5870 * base_im[:,:,1] + 0.1140 * base_im[:,:,2]

    # Peak perturbed
    peak_file = os.path.join(DIRECTORY, f"ghost_no_ramp_{c_id}_01_perturbed_peak.png")
    peak_im = np.array(Image.open(peak_file).convert('RGB'), dtype=float)
    peak_gray = 0.2989 * peak_im[:,:,0] + 0.5870 * peak_im[:,:,1] + 0.1140 * peak_im[:,:,2]

    # Ghost mask: pixels that are substantially brighter in perturbed state than baseline
    diff_peak = peak_gray - base_gray
    ghost_mask = (diff_peak > 15.0) & (base_gray < 10.0)
    ghost_count = np.sum(ghost_mask)
    initial_peak_ghost = np.max(diff_peak[ghost_mask]) if ghost_count > 0 else np.max(diff_peak)

    print(f"\n--- {c_lbl} (p={p_val:.5f}) ---")
    print(f"Ghost pixel count (diff > 15 & base < 10): {ghost_count}")
    print(f"Initial peak ghost luminance: {initial_peak_ghost:.2f} / 255")

    for cp_key, cp_sec, cp_frames in checkpoints:
        cp_file = os.path.join(DIRECTORY, f"ghost_no_ramp_{c_id}_{cp_key}.png")
        if not os.path.exists(cp_file):
            continue
        cur_im = np.array(Image.open(cp_file).convert('RGB'), dtype=float)
        cur_gray = 0.2989 * cur_im[:,:,0] + 0.5870 * cur_im[:,:,1] + 0.1140 * cur_im[:,:,2]

        cur_diff = np.abs(cur_gray - base_gray)
        max_diff_all = np.max(cur_diff)
        max_ghost = np.max(cur_diff[ghost_mask]) if ghost_count > 0 else np.max(cur_diff)
        mean_ghost = np.mean(cur_diff[ghost_mask]) if ghost_count > 0 else np.mean(cur_diff)
        ssim_val = compute_ssim(base_gray, cur_gray)

        # Theoretical decay: initial_peak_ghost * (p ** cp_frames)
        theor_ghost = initial_peak_ghost * (p_val ** cp_frames)

        print(f"  t={cp_sec:4.1f}s ({cp_frames:4d}f): max ghost = {max_ghost:5.2f} (theor: {theor_ghost:5.2f}) | mean ghost = {mean_ghost:5.2f} | SSIM vs base = {ssim_val:.4f} | max diff all = {max_diff_all:5.2f}")

print("\n==========================================================================")
print("ANALYZING ACTIVE-TO-IDLE RAMP IMAGES")
print("==========================================================================")

ramp_checkpoints = [
    ('01_interaction_active', 'Active (p=0.95)', 1.0, 60),
    ('post_1.5s', 'Ramp End (p->idle)', 1.5, 90),
    ('post_5.0s', 'Post 5s', 5.0, 300),
    ('post_10.0s', 'Post 10s', 10.0, 600),
    ('post_15.0s', 'Post 15s', 15.0, 900)
]

for c_id, p_val, c_lbl in candidates:
    base_file = os.path.join(DIRECTORY, f"ghost_no_ramp_{c_id}_00_baseline_15s.png")
    base_im = np.array(Image.open(base_file).convert('RGB'), dtype=float)
    base_gray = 0.2989 * base_im[:,:,0] + 0.5870 * base_im[:,:,1] + 0.1140 * base_im[:,:,2]

    print(f"\n--- {c_lbl} (Active Ramp 0.95 -> {p_val:.5f} over 1.5s) ---")
    for cp_key, cp_name, cp_sec, cp_frames in ramp_checkpoints:
        cp_file = os.path.join(DIRECTORY, f"ramp_{c_id}_{cp_key}.png")
        if not os.path.exists(cp_file):
            continue
        cur_im = np.array(Image.open(cp_file).convert('RGB'), dtype=float)
        cur_gray = 0.2989 * cur_im[:,:,0] + 0.5870 * cur_im[:,:,1] + 0.1140 * cur_im[:,:,2]

        cur_diff = np.abs(cur_gray - base_gray)
        mean_diff = np.mean(cur_diff)
        max_diff = np.max(cur_diff)
        ssim_val = compute_ssim(base_gray, cur_gray)
        org_pixels = cur_gray[cur_gray > 5.0]
        mean_lum = np.mean(org_pixels) if len(org_pixels) > 0 else 0.0

        print(f"  {cp_name:25s} (t={cp_sec:4.1f}s): SSIM = {ssim_val:.4f} | mean organism lum = {mean_lum:5.2f} | max diff = {max_diff:5.2f}")
