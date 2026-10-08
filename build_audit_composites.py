import os
import json
import numpy as np
from PIL import Image, ImageDraw

DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
OUT_DIR = os.path.join(DIRECTORY, "visual_detail_audit")

# Metadata collected from Chrome browser run
RUN_METRICS = {
  "brute_force": {
    "label": "OLD BRUTE FORCE (589,824 x 16)",
    "particles": 589824,
    "steps": 16,
    "depositsPerFrame": 9437184,
    "checkpoints": {
      "1s": {"elapsedMs": 1003.4, "frames": 9, "fps": 9.0, "photons": 84934656},
      "3s": {"elapsedMs": 3059.1, "frames": 26, "fps": 8.5, "photons": 245366784},
      "5s": {"elapsedMs": 5074.5, "frames": 45, "fps": 8.9, "photons": 424673280},
      "10s": {"elapsedMs": 10051.9, "frames": 93, "fps": 9.3, "photons": 877658112},
      "20s": {"elapsedMs": 20003.0, "frames": 187, "fps": 9.3, "photons": 1764753408}
    }
  },
  "adaptive_std": {
    "label": "CURRENT ADAPTIVE STD (150,000 x 8)",
    "particles": 150000,
    "steps": 8,
    "depositsPerFrame": 1200000,
    "checkpoints": {
      "1s": {"elapsedMs": 1015.5, "frames": 61, "fps": 60.1, "photons": 73200000},
      "3s": {"elapsedMs": 3013.6, "frames": 179, "fps": 59.4, "photons": 214800000},
      "5s": {"elapsedMs": 5011.8, "frames": 297, "fps": 59.3, "photons": 356400000},
      "10s": {"elapsedMs": 10007.1, "frames": 595, "fps": 59.5, "photons": 714000000},
      "20s": {"elapsedMs": 20015.6, "frames": 1193, "fps": 59.6, "photons": 1431600000}
    }
  },
  "exp_180k_8": {
    "label": "EXPERIMENTAL A (180,000 x 8)",
    "particles": 180000,
    "steps": 8,
    "depositsPerFrame": 1440000,
    "checkpoints": {
      "3s": {"elapsedMs": 3003.5, "frames": 161, "fps": 53.6, "photons": 231840000},
      "5s": {"elapsedMs": 5017.5, "frames": 263, "fps": 52.4, "photons": 378720000},
      "10s": {"elapsedMs": 10018.0, "frames": 513, "fps": 51.2, "photons": 738720000}
    }
  },
  "exp_150k_10": {
    "label": "EXPERIMENTAL B (150,000 x 10)",
    "particles": 150000,
    "steps": 10,
    "depositsPerFrame": 1500000,
    "checkpoints": {
      "3s": {"elapsedMs": 3015.8, "frames": 140, "fps": 46.4, "photons": 210000000},
      "5s": {"elapsedMs": 5003.0, "frames": 228, "fps": 45.6, "photons": 342000000},
      "10s": {"elapsedMs": 10002.7, "frames": 454, "fps": 45.4, "photons": 681000000}
    }
  }
}

def compute_gradient_mag(gray):
    gx = (
        -1.0 * gray[:-2, :-2] + 1.0 * gray[:-2, 2:] +
        -2.0 * gray[1:-1, :-2] + 2.0 * gray[1:-1, 2:] +
        -1.0 * gray[2:, :-2] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    gy = (
        -1.0 * gray[:-2, :-2] - 2.0 * gray[:-2, 1:-1] - 1.0 * gray[:-2, 2:] +
         1.0 * gray[2:, :-2] + 2.0 * gray[2:, 1:-1] + 1.0 * gray[2:, 2:]
    ) * (1.0 / 8.0)
    return np.hypot(gx, gy)

def compute_local_contrast(gray, patch_size=16):
    h, w = gray.shape
    stds = []
    for r in range(0, h - patch_size + 1, patch_size):
        for c in range(0, w - patch_size + 1, patch_size):
            patch = gray[r:r+patch_size, c:c+patch_size]
            if np.mean(patch) > 5.0:
                stds.append(np.std(patch))
    return float(np.mean(stds)) if stds else 0.0

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

def compute_psnr(img1, img2):
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100.0
    return float(20 * np.log10(255.0 / np.sqrt(mse)))

def main():
    print("Loading audit images from", OUT_DIR)
    
    # Checkpoints: 1s, 3s, 5s, 10s, 20s
    checkpoints = ["1s", "3s", "5s", "10s", "20s"]
    
    # Load all images into memory
    full_images = {}
    medium_crops = {}
    detail_crops = {}

    all_keys = [
        "brute_force_1s", "brute_force_3s", "brute_force_5s", "brute_force_10s", "brute_force_20s",
        "adaptive_std_1s", "adaptive_std_3s", "adaptive_std_5s", "adaptive_std_10s", "adaptive_std_20s",
        "exp_180k_8_3s", "exp_180k_8_5s", "exp_180k_8_10s",
        "exp_150k_10_3s", "exp_150k_10_5s", "exp_150k_10_10s"
    ]

    for k in all_keys:
        p_full = os.path.join(OUT_DIR, f"{k}_full.png")
        p_med = os.path.join(OUT_DIR, f"{k}_crop_medium.png")
        p_det = os.path.join(OUT_DIR, f"{k}_crop_detail.png")

        if os.path.exists(p_full): full_images[k] = Image.open(p_full).convert('RGB')
        if os.path.exists(p_med): medium_crops[k] = Image.open(p_med).convert('RGB')
        if os.path.exists(p_det): detail_crops[k] = Image.open(p_det).convert('RGB')

    print(f"Loaded {len(full_images)} full, {len(medium_crops)} medium, {len(detail_crops)} detail images.")

    # 1. BUILD SIDE-BY-SIDE COMPOSITES FOR 1s, 3s, 5s, 10s, 20s
    for t_str in checkpoints:
        b_key = f"brute_force_{t_str}"
        a_key = f"adaptive_std_{t_str}"

        # A. Full View Side-by-Side (2400 x 800)
        sbs_full = Image.new('RGB', (2400, 800))
        sbs_full.paste(full_images[b_key], (0, 0))
        sbs_full.paste(full_images[a_key], (1200, 0))
        d_full = ImageDraw.Draw(sbs_full)
        d_full.rectangle([10, 10, 480, 50], fill=(0, 0, 0))
        d_full.text((20, 20), f"OLD BRUTE FORCE (589k x 16) | {t_str} wall-clock", fill=(240, 240, 240))
        d_full.rectangle([1210, 10, 1720, 50], fill=(0, 0, 0))
        d_full.text((1220, 20), f"CURRENT ADAPTIVE (150k x 8) | {t_str} wall-clock", fill=(240, 240, 240))
        sbs_full_path = os.path.join(OUT_DIR, f"comparison_{t_str}_full_side_by_side.png")
        sbs_full.save(sbs_full_path)

        # B. Medium Crop Side-by-Side (800 x 400)
        sbs_med = Image.new('RGB', (800, 400))
        sbs_med.paste(medium_crops[b_key], (0, 0))
        sbs_med.paste(medium_crops[a_key], (400, 0))
        d_med = ImageDraw.Draw(sbs_med)
        d_med.rectangle([5, 5, 280, 30], fill=(0, 0, 0))
        d_med.text((10, 10), f"BRUTE MEDIUM ({t_str})", fill=(240, 240, 240))
        d_med.rectangle([405, 5, 680, 30], fill=(0, 0, 0))
        d_med.text((410, 10), f"ADAPTIVE MEDIUM ({t_str})", fill=(240, 240, 240))
        sbs_med_path = os.path.join(OUT_DIR, f"comparison_{t_str}_medium_crop_side_by_side.png")
        sbs_med.save(sbs_med_path)

        # C. Fine Detail Crop Side-by-Side (600 x 300)
        sbs_det = Image.new('RGB', (600, 300))
        sbs_det.paste(detail_crops[b_key], (0, 0))
        sbs_det.paste(detail_crops[a_key], (300, 0))
        d_det = ImageDraw.Draw(sbs_det)
        d_det.rectangle([5, 5, 230, 30], fill=(0, 0, 0))
        d_det.text((10, 10), f"BRUTE DETAIL ({t_str})", fill=(240, 240, 240))
        d_det.rectangle([305, 5, 530, 30], fill=(0, 0, 0))
        d_det.text((310, 10), f"ADAPTIVE DETAIL ({t_str})", fill=(240, 240, 240))
        sbs_det_path = os.path.join(OUT_DIR, f"comparison_{t_str}_detail_crop_side_by_side.png")
        sbs_det.save(sbs_det_path)

        print(f"[OK] Generated {t_str} side-by-side files (full, medium, detail)")

    # 2. BUILD LARGE COMPARISON GRID SHEET (Section 5 requirement)
    # Rows: 1s, 3s, 5s, 10s, 20s
    # Columns: Brute Full | Adaptive Full | Brute Detail | Adaptive Detail
    grid_w = 2000
    grid_h = 2060
    grid_img = Image.new('RGB', (grid_w, grid_h), color=(1, 3, 7))
    d_grid = ImageDraw.Draw(grid_img)

    col_x = [0, 600, 1200, 1600]
    col_titles = [
        "OLD BRUTE FORCE (589k x 16) - FULL VIEW",
        "CURRENT ADAPTIVE (150k x 8) - FULL VIEW",
        "BRUTE FORCE - DETAIL CROP",
        "ADAPTIVE - DETAIL CROP"
    ]
    for i, title in enumerate(col_titles):
        d_grid.text((col_x[i] + 15, 20), title, fill=(180, 210, 245))

    for r_idx, t_str in enumerate(checkpoints):
        y_pos = 60 + r_idx * 400
        b_key = f"brute_force_{t_str}"
        a_key = f"adaptive_std_{t_str}"

        b_full = full_images[b_key].resize((600, 400), Image.Resampling.LANCZOS)
        a_full = full_images[a_key].resize((600, 400), Image.Resampling.LANCZOS)
        b_det = detail_crops[b_key].resize((400, 400), Image.Resampling.NEAREST)
        a_det = detail_crops[a_key].resize((400, 400), Image.Resampling.NEAREST)

        grid_img.paste(b_full, (0, y_pos))
        grid_img.paste(a_full, (600, y_pos))
        grid_img.paste(b_det, (1200, y_pos))
        grid_img.paste(a_det, (1600, y_pos))

        d_grid.rectangle([5, y_pos + 5, 110, y_pos + 30], fill=(0, 0, 0))
        d_grid.text((10, y_pos + 10), f"TIME: {t_str}", fill=(255, 220, 100))

    grid_path = os.path.join(OUT_DIR, "large_comparison_grid_5x4.png")
    grid_img.save(grid_path)
    print(f"[OK] Saved large comparison grid sheet to {grid_path}")

    # 3. EXPERIMENTAL WORKLOADS 3-WAY COMPARISONS (at 3s, 5s, 10s)
    exp_times = ["3s", "5s", "10s"]
    for t_str in exp_times:
        std_key = f"adaptive_std_{t_str}"
        e180_key = f"exp_180k_8_{t_str}"
        e150_key = f"exp_150k_10_{t_str}"

        # 3-way Full View (1800 x 450)
        exp_full_strip = Image.new('RGB', (1800, 450), color=(1, 3, 7))
        exp_full_strip.paste(full_images[std_key].resize((600, 400), Image.Resampling.LANCZOS), (0, 50))
        exp_full_strip.paste(full_images[e180_key].resize((600, 400), Image.Resampling.LANCZOS), (600, 50))
        exp_full_strip.paste(full_images[e150_key].resize((600, 400), Image.Resampling.LANCZOS), (1200, 50))
        d_ef = ImageDraw.Draw(exp_full_strip)
        d_ef.text((20, 15), f"STANDARD (150k x 8) @ {t_str} (59.4 FPS)", fill=(180, 210, 245))
        d_ef.text((620, 15), f"EXPERIMENTAL A (180k x 8) @ {t_str} (53.6 FPS)", fill=(180, 210, 245))
        d_ef.text((1220, 15), f"EXPERIMENTAL B (150k x 10) @ {t_str} (46.4 FPS)", fill=(180, 210, 245))
        exp_full_path = os.path.join(OUT_DIR, f"experimental_comparison_{t_str}_full.png")
        exp_full_strip.save(exp_full_path)

        # 3-way Detail Crops (900 x 340)
        exp_det_strip = Image.new('RGB', (900, 340), color=(1, 3, 7))
        exp_det_strip.paste(detail_crops[std_key], (0, 40))
        exp_det_strip.paste(detail_crops[e180_key], (300, 40))
        exp_det_strip.paste(detail_crops[e150_key], (600, 40))
        d_ed = ImageDraw.Draw(exp_det_strip)
        d_ed.text((10, 10), f"150k x 8 ({t_str})", fill=(180, 210, 245))
        d_ed.text((310, 10), f"180k x 8 ({t_str})", fill=(180, 210, 245))
        d_ed.text((610, 10), f"150k x 10 ({t_str})", fill=(180, 210, 245))
        exp_det_path = os.path.join(OUT_DIR, f"experimental_comparison_{t_str}_detail.png")
        exp_det_strip.save(exp_det_path)

        print(f"[OK] Generated Experimental 3-way comparison for {t_str}")

    # 4. COMPUTE QUANTITATIVE METRICS
    quantitative_results = {}
    all_dict = {
        'full': full_images,
        'medium': medium_crops,
        'detail': detail_crops
    }

    for v_name, v_dict in all_dict.items():
        quantitative_results[v_name] = {}
        for img_key, img in v_dict.items():
            arr = np.array(img, dtype=float)
            gray = 0.2989 * arr[:,:,0] + 0.5870 * arr[:,:,1] + 0.1140 * arr[:,:,2]

            feat_pixels = int(np.sum(gray > 5.0))
            feat_pct = float(feat_pixels / gray.size * 100.0)
            max_val = float(np.max(gray))
            mean_val = float(np.mean(gray))

            gmag = compute_gradient_mag(gray)
            edge_soft = int(np.sum(gmag > 5.0))
            edge_hard = int(np.sum(gmag > 15.0))
            edge_soft_pct = float(edge_soft / gmag.size * 100.0)
            edge_hard_pct = float(edge_hard / gmag.size * 100.0)
            mean_edge = float(np.mean(gmag))
            loc_contrast = compute_local_contrast(gray, patch_size=16)

            quantitative_results[v_name][img_key] = {
                'dimensions': list(img.size),
                'mean_intensity': round(mean_val, 2),
                'max_intensity': round(max_val, 2),
                'feature_pixels': feat_pixels,
                'feature_pixel_pct': round(feat_pct, 2),
                'edges_soft_gt5': edge_soft,
                'edges_soft_pct': round(edge_soft_pct, 2),
                'edges_hard_gt15': edge_hard,
                'edges_hard_pct': round(edge_hard_pct, 2),
                'mean_edge_gradient': round(mean_edge, 3),
                'local_contrast_std': round(loc_contrast, 2)
            }

    # Cross-comparison correlations
    correlations = {}
    for t_str in checkpoints:
        b_key = f"brute_force_{t_str}"
        a_key = f"adaptive_std_{t_str}"
        correlations[t_str] = {}

        for v_name, v_dict in all_dict.items():
            b_arr = np.array(v_dict[b_key], dtype=float)
            a_arr = np.array(v_dict[a_key], dtype=float)

            b_gray = 0.2989 * b_arr[:,:,0] + 0.5870 * b_arr[:,:,1] + 0.1140 * b_arr[:,:,2]
            a_gray = 0.2989 * a_arr[:,:,0] + 0.5870 * a_arr[:,:,1] + 0.1140 * a_arr[:,:,2]

            r_int = float(np.corrcoef(b_gray.ravel(), a_gray.ravel())[0, 1])

            b_gmag = compute_gradient_mag(b_gray)
            a_gmag = compute_gradient_mag(a_gray)
            r_edge = float(np.corrcoef(b_gmag.ravel(), a_gmag.ravel())[0, 1])

            ssim_val = compute_ssim(b_gray, a_gray)
            psnr_val = compute_psnr(b_gray, a_gray)

            correlations[t_str][v_name] = {
                'intensity_correlation': round(r_int, 4),
                'sobel_edge_correlation': round(r_edge, 4),
                'ssim': round(ssim_val, 4),
                'psnr_db': round(psnr_val, 2)
            }

    # Cross-comparison for experimental workloads against adaptive standard (150k x 8)
    exp_correlations = {}
    for t_str in exp_times:
        std_key = f"adaptive_std_{t_str}"
        e180_key = f"exp_180k_8_{t_str}"
        e150_key = f"exp_150k_10_{t_str}"
        exp_correlations[t_str] = {}

        for test_name, test_key in [("180k_8_vs_150k_8", e180_key), ("150k_10_vs_150k_8", e150_key)]:
            std_det = np.array(detail_crops[std_key], dtype=float)
            test_det = np.array(detail_crops[test_key], dtype=float)

            std_gray = 0.2989 * std_det[:,:,0] + 0.5870 * std_det[:,:,1] + 0.1140 * std_det[:,:,2]
            test_gray = 0.2989 * test_det[:,:,0] + 0.5870 * test_det[:,:,1] + 0.1140 * test_det[:,:,2]

            r_int = float(np.corrcoef(std_gray.ravel(), test_gray.ravel())[0, 1])
            std_gmag = compute_gradient_mag(std_gray)
            test_gmag = compute_gradient_mag(test_gray)
            r_edge = float(np.corrcoef(std_gmag.ravel(), test_gmag.ravel())[0, 1])

            ssim_val = compute_ssim(std_gray, test_gray)
            psnr_val = compute_psnr(std_gray, test_gray)

            exp_correlations[t_str][test_name] = {
                'intensity_correlation': round(r_int, 4),
                'sobel_edge_correlation': round(r_edge, 4),
                'ssim': round(ssim_val, 4),
                'psnr_db': round(psnr_val, 2)
            }

    final_report = {
        'workload_metrics': RUN_METRICS,
        'cross_correlations_brute_vs_adaptive': correlations,
        'experimental_correlations_vs_adaptive': exp_correlations,
        'quantitative_metrics': quantitative_results
    }

    rep_path = os.path.join(OUT_DIR, "visual_detail_audit_report.json")
    with open(rep_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n[OK] Full audit report saved to {rep_path}")
    print("\n================ AUDIT SUMMARY ================")
    for t_str in checkpoints:
        print(f"\n--- CHECKPOINT {t_str} ---")
        corr = correlations[t_str]
        print(f"Full:   SSIM = {corr['full']['ssim']}, PSNR = {corr['full']['psnr_db']} dB, Intensity Corr = {corr['full']['intensity_correlation']}, Edge Corr = {corr['full']['sobel_edge_correlation']}")
        print(f"Medium: SSIM = {corr['medium']['ssim']}, PSNR = {corr['medium']['psnr_db']} dB, Intensity Corr = {corr['medium']['intensity_correlation']}, Edge Corr = {corr['medium']['sobel_edge_correlation']}")
        print(f"Detail: SSIM = {corr['detail']['ssim']}, PSNR = {corr['detail']['psnr_db']} dB, Intensity Corr = {corr['detail']['intensity_correlation']}, Edge Corr = {corr['detail']['sobel_edge_correlation']}")

if __name__ == '__main__':
    main()
