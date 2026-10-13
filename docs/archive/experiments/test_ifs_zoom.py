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

# Generate high density points
print("Generating attractor trajectory...")
z = 0.3 + 0.1j
for _ in range(1000):
    k = np.random.randint(0, n)
    z = eval_m(z, k)

# Let's find a focal caustic point on a prominent lobe
# In the reference image, the caustic scallops are around r = 0.18 - 0.25
# Let's find points with high density
pts = []
for _ in range(5000000):
    k = np.random.randint(0, n)
    z = eval_m(z, k)
    pts.append(z)

pts = np.array(pts)
print(f"Total points generated: {len(pts)}")

# Zoom centers: Let's pick a point in an intricate caustic fold
# Let's see points around r ~ 0.22, theta ~ 0.3
mask = (np.abs(pts) > 0.18) & (np.abs(pts) < 0.28) & (np.angle(pts) > 0.2) & (np.angle(pts) < 0.4)
sub = pts[mask]
center = sub[len(sub)//2]
cx, cy = center.real, center.imag
print(f"Zoom center: ({cx:.5f}, {cy:.5f}), r={np.abs(center):.4f}")

zooms = [1.65, 6.0, 24.0, 96.0]
for idx, z_scale in enumerate(zooms):
    W, H = 800, 800
    accum = np.zeros((H, W), dtype=np.float32)
    
    # Coordinates in viewport
    c_x = 0.0 if z_scale == 1.65 else cx
    c_y = 0.0 if z_scale == 1.65 else cy
    
    # Scale to pixels
    # clip = (z - center) * z_scale
    # pixel = clip * (H/2) + (W/2, H/2)
    px = ((pts.real - c_x) * z_scale + 1.0) * 0.5 * (W - 1)
    py = ((-pts.imag + c_y) * z_scale + 1.0) * 0.5 * (H - 1)
    
    valid = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    px = px[valid].astype(np.int32)
    py = py[valid].astype(np.int32)
    
    np.add.at(accum, (py, px), 1.0)
    
    # Density tone mapping
    norm = np.log1p(accum * 0.5) / np.log1p(np.max(accum) * 0.5 + 1e-5)
    img_gray = (np.clip(norm, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img_gray).save(f"zoom_level_{idx+1}.png")
    print(f"Saved zoom_level_{idx+1}.png (valid hits in view: {len(px)})")
