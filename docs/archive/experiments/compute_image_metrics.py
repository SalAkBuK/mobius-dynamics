import os, json
import numpy as np
from PIL import Image

DIRECTORY = r"c:\Users\saleh\Documents\antigravity\METH"
save_dir = os.path.join(DIRECTORY, "validation_captures")

def compute_ssim(img1, img2):
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    if img1.ndim == 3:
        im1_gray = 0.2989 * img1[:, :, 0] + 0.5870 * img1[:, :, 1] + 0.1140 * img1[:, :, 2]
        im2_gray = 0.2989 * img2[:, :, 0] + 0.5870 * img2[:, :, 1] + 0.1140 * img2[:, :, 2]
    else:
        im1_gray = img1
        im2_gray = img2

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

target_secs_str = ["0.5", "1", "3", "5", "10"]
modes = ["ULTRA", "HIGH", "MEDIUM", "LOW", "POTATO"]

ref_10s_path = os.path.join(save_dir, "valid_ultra_10s.png")
ref_10s_img = np.array(Image.open(ref_10s_path))

iq_results = {}
for tsec in target_secs_str:
    iq_results[tsec] = {}
    ultra_t_path = os.path.join(save_dir, f"valid_ultra_{tsec}s.png")
    ultra_t_img = np.array(Image.open(ultra_t_path))

    for mode in modes:
        m_path = os.path.join(save_dir, f"valid_{mode.lower()}_{tsec}s.png")
        m_img = np.array(Image.open(m_path))

        ssim_vs_ultra_t = compute_ssim(m_img, ultra_t_img)
        psnr_vs_ultra_t = compute_psnr(m_img, ultra_t_img)

        ssim_vs_ultra_10s = compute_ssim(m_img, ref_10s_img)
        psnr_vs_ultra_10s = compute_psnr(m_img, ref_10s_img)

        iq_results[tsec][mode] = {
            "ssim_vs_ultra_at_time": round(ssim_vs_ultra_t, 4),
            "psnr_vs_ultra_at_time": round(psnr_vs_ultra_t, 2),
            "ssim_vs_ultra_10s_ref": round(ssim_vs_ultra_10s, 4),
            "psnr_vs_ultra_10s_ref": round(psnr_vs_ultra_10s, 2)
        }

with open(os.path.join(DIRECTORY, "image_quality_metrics.json"), "w") as f:
    json.dump(iq_results, f, indent=2)

print("=== IMAGE QUALITY METRICS TABLE ===")
for tsec, modes_data in iq_results.items():
    print(f"\n--- Checkpoint {tsec}s (vs Ultra at {tsec}s) ---")
    for m, vals in modes_data.items():
        print(f"  {m:7s}: SSIM = {vals['ssim_vs_ultra_at_time']:.4f}, PSNR = {vals['psnr_vs_ultra_at_time']:.2f} dB | "
              f"vs Ultra 10s: SSIM = {vals['ssim_vs_ultra_10s_ref']:.4f}, PSNR = {vals['psnr_vs_ultra_10s_ref']:.2f} dB")

# Generate side-by-side comparison images
for tsec in target_secs_str:
    strip_modes = ["POTATO", "LOW", "MEDIUM", "ULTRA"]
    imgs = [Image.open(os.path.join(save_dir, f"valid_{m.lower()}_{tsec}s.png")) for m in strip_modes]
    thumb_w, thumb_h = 600, 400
    thumbs = [im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS) for im in imgs]
    strip = Image.new("RGB", (thumb_w * 4, thumb_h))
    for idx, th in enumerate(thumbs):
        strip.paste(th, (idx * thumb_w, 0))
    strip_path = os.path.join(save_dir, f"side_by_side_{tsec}s.png")
    strip.save(strip_path)
    print(f"Saved: {strip_path}")

# Complete 4x5 comparison grid
# Rows: Potato, Low, Medium, Ultra
# Cols: 0.5s, 1s, 3s, 5s, 10s
grid_w, grid_h = 360, 240
grid = Image.new("RGB", (grid_w * 5, grid_h * 4))
row_modes = ["POTATO", "LOW", "MEDIUM", "ULTRA"]
for r_idx, m in enumerate(row_modes):
    for c_idx, tsec in enumerate(target_secs_str):
        im = Image.open(os.path.join(save_dir, f"valid_{m.lower()}_{tsec}s.png"))
        th = im.resize((grid_w, grid_h), Image.Resampling.LANCZOS)
        grid.paste(th, (c_idx * grid_w, r_idx * grid_h))
grid_path = os.path.join(save_dir, "comparison_grid_4x5.png")
grid.save(grid_path)
print(f"Saved: {grid_path}")
