import numpy as np
from PIL import Image

a = complex(-0.755, 0.33)
b = complex(-0.376, 0.026)
c = complex(6.401, 0.803)
d = complex(1.52, 0.84)
n = 16
omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)

def eval_m(z, k):
    num = a * z + b
    den = c * z + d
    return omegas[k] * (num / den)

# Find high-density caustic point
z = 0.3 + 0.1j
for _ in range(1000):
    k = np.random.randint(0, n)
    z = eval_m(z, k)

# Trace trajectory and find a rich caustic coordinate
print("Locating deep zoom target point...")
pts = []
for _ in range(2000000):
    k = np.random.randint(0, n)
    z = eval_m(z, k)
    pts.append(z)
pts = np.array(pts)

# Filter near inner caustic ring: r in [0.18, 0.22]
mask = (np.abs(pts) > 0.18) & (np.abs(pts) < 0.22) & (pts.real > 0.15) & (pts.imag > 0.05)
target = pts[mask][100]
cx, cy = target.real, target.imag
print(f"Target center: cx={cx:.6f}, cy={cy:.6f}, r={np.abs(target):.6f}")

# Generate high-resolution progressive images at 5 distinct zoom levels
zoom_levels = [
    ("level_0_full", 1.65, 0.0, 0.0, 3000000),
    ("level_1_ring", 6.5, cx, cy, 5000000),
    ("level_2_lobe", 25.0, cx, cy, 10000000),
    ("level_3_filament", 90.0, cx, cy, 15000000),
    ("level_4_deepest", 360.0, cx, cy, 25000000),
]

W, H = 800, 800

# Color palette
col_bg = np.array([0.005, 0.008, 0.016])
col_midnight = np.array([0.025, 0.075, 0.220])
col_electric = np.array([0.080, 0.420, 0.950])
col_icy = np.array([0.720, 0.910, 1.000])
col_white = np.array([1.000, 1.000, 1.000])

def colorize(norm):
    t1 = np.clip(norm / 0.15, 0, 1)[..., None]
    c1 = (1 - t1) * col_bg + t1 * col_midnight
    t2 = np.clip((norm - 0.15) / 0.35, 0, 1)[..., None]
    c2 = (1 - t2) * col_midnight + t2 * col_electric
    t3 = np.clip((norm - 0.50) / 0.35, 0, 1)[..., None]
    c3 = (1 - t3) * col_electric + t3 * col_icy
    t4 = np.clip((norm - 0.85) / 0.15, 0, 1)[..., None]
    t4 = t4 * t4 * (3 - 2 * t4)
    c4 = (1 - t4) * col_icy + t4 * col_white
    
    m1 = (norm < 0.15)[..., None]
    m2 = ((norm >= 0.15) & (norm < 0.50))[..., None]
    m3 = ((norm >= 0.50) & (norm < 0.85))[..., None]
    return np.where(m1, c1, np.where(m2, c2, np.where(m3, c3, c4)))

for name, zoom, x_c, y_c, total_pts in zoom_levels:
    print(f"Generating {name} (zoom={zoom}x, pts={total_pts})...")
    accum = np.zeros((H, W), dtype=np.float32)
    
    # We can chunk iterations for speed
    chunk_size = 1000000
    num_chunks = total_pts // chunk_size
    curr_z = target
    
    for ch in range(num_chunks):
        # iterate
        batch_z = []
        for _ in range(chunk_size):
            k = np.random.randint(0, n)
            curr_z = eval_m(curr_z, k)
            batch_z.append(curr_z)
        bz = np.array(batch_z)
        
        px = ((bz.real - x_c) * zoom + 1.0) * 0.5 * (W - 1)
        py = ((-bz.imag + y_c) * zoom + 1.0) * 0.5 * (H - 1)
        valid = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        if np.any(valid):
            np.add.at(accum, (py[valid].astype(np.int32), px[valid].astype(np.int32)), 1.0)
            
    # Tonemap
    alpha = 0.15
    log_acc = np.log1p(accum * alpha)
    max_log = np.log1p(np.max(accum) * alpha + 1e-5)
    norm = np.power(log_acc / max_log, 0.82)
    rgb = colorize(norm)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(f"{name}.png")
    print(f"Saved {name}.png: max hits={np.max(accum):.1f}")
