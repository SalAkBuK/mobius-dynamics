import numpy as np
from PIL import Image

# Load base 16-fold accumulation data or generate high-quality IFS data
a = complex(-0.755, 0.33)
b = complex(-0.376, 0.026)
c = complex(6.401, 0.803)
d = complex(1.52, 0.84)
n = 16
omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)

W, H = 1000, 1000
accum = np.zeros((H, W), dtype=np.float32)

P = 30000
steps = 300
np.random.seed(42)
radii = np.random.uniform(0.2, 0.6, P)
thetas = np.random.uniform(0, 2 * np.pi, P)
z = (radii * np.exp(1j * thetas)).astype(np.complex128)

# Warmup
for _ in range(30):
    k = np.random.randint(0, n, size=P)
    om = omegas[k]
    num = a * z + b
    den = c * z + d
    den_mag_sq = den.real**2 + den.imag**2
    mask_bad = (den_mag_sq < 1e-7) | (np.abs(z) > 10.0) | np.isnan(z.real)
    inv_den = np.where(mask_bad, 0, den.conjugate() / np.maximum(den_mag_sq, 1e-7))
    z = np.where(mask_bad, 0.3 * np.exp(1j * np.random.uniform(0, 2*np.pi, P)), om * (num * inv_den))

zoom = 1.65
for _ in range(steps):
    k = np.random.randint(0, n, size=P)
    om = omegas[k]
    num = a * z + b
    den = c * z + d
    den_mag_sq = den.real**2 + den.imag**2
    mask_bad = (den_mag_sq < 1e-7) | (np.abs(z) > 10.0) | np.isnan(z.real)
    inv_den = np.where(mask_bad, 0, den.conjugate() / np.maximum(den_mag_sq, 1e-7))
    z = np.where(mask_bad, 0.3 * np.exp(1j * np.random.uniform(0, 2*np.pi, P)), om * (num * inv_den))
    
    px = (z.real * zoom + 1.0) * 0.5 * (W - 1)
    py = (-z.imag * zoom + 1.0) * 0.5 * (H - 1)
    valid = (px >= 0) & (px < W) & (py >= 0) & (py < H) & (~mask_bad)
    np.add.at(accum, (py[valid].astype(np.int32), px[valid].astype(np.int32)), 1.0)

print(f"Max accumulation: {np.max(accum)}, non-zero pixels: {np.count_nonzero(accum)}")

# Palette color definitions (linear sRGB)
col_bg = np.array([0.005, 0.008, 0.016])       # Near-black blue bias
col_midnight = np.array([0.025, 0.075, 0.220]) # Midnight cobalt
col_electric = np.array([0.080, 0.420, 0.950]) # Electric blue
col_icy = np.array([0.720, 0.910, 1.000])      # Delicate icy blue
col_white = np.array([1.000, 1.000, 1.000])    # Singular caustics

def apply_palette(norm_val):
    # 4-stage smoothstep color ramp preserving linework
    # 0.00 -> col_bg
    # 0.15 -> col_midnight
    # 0.50 -> col_electric
    # 0.85 -> col_icy
    # 1.00 -> col_white
    H, W = norm_val.shape
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    
    t1 = np.clip(norm_val / 0.15, 0, 1)[..., None]
    c1 = (1 - t1) * col_bg + t1 * col_midnight
    
    t2 = np.clip((norm_val - 0.15) / 0.35, 0, 1)[..., None]
    c2 = (1 - t2) * col_midnight + t2 * col_electric
    
    t3 = np.clip((norm_val - 0.50) / 0.35, 0, 1)[..., None]
    c3 = (1 - t3) * col_electric + t3 * col_icy
    
    t4 = np.clip((norm_val - 0.85) / 0.15, 0, 1)[..., None]
    # Use soft curve for the highlight so it doesn't clip
    t4 = t4 * t4 * (3 - 2 * t4)
    c4 = (1 - t4) * col_icy + t4 * col_white
    
    m1 = (norm_val < 0.15)[..., None]
    m2 = ((norm_val >= 0.15) & (norm_val < 0.50))[..., None]
    m3 = ((norm_val >= 0.50) & (norm_val < 0.85))[..., None]
    m4 = (norm_val >= 0.85)[..., None]
    
    rgb = np.where(m1, c1, np.where(m2, c2, np.where(m3, c3, c4)))
    return np.clip(rgb, 0, 1)

# Method 1: Previous curve (for comparison)
d_prev = accum * 0.02 * 9.0
norm_prev = d_prev / (1.0 + d_prev * 0.42)
norm_prev = np.log1p(norm_prev * 2.5) / np.log1p(2.5 * 2.2)
norm_prev = np.clip(norm_prev, 0, 1.5)
rgb_prev = apply_palette(np.clip(norm_prev, 0, 1))
Image.fromarray((rgb_prev * 255).astype(np.uint8)).save("tone_previous.png")

# Method 2: Extended Dynamic Range Logarithmic Photographic Curve
# log(1 + alpha * accum) with high-end preservation
alpha = 0.12
log_acc = np.log1p(accum * alpha)
# Use soft roll-off for the top 5%
max_log = np.log1p(np.max(accum) * alpha)
norm_new = log_acc / max_log
# Apply subtle contrast curve (toe and shoulder)
# toe raises faint outer filaments; shoulder keeps caustic lines distinct
norm_new = np.power(norm_new, 0.82)
rgb_new = apply_palette(norm_new)
Image.fromarray((rgb_new * 255).astype(np.uint8)).save("tone_refined.png")

print("Saved tone_previous.png and tone_refined.png")
