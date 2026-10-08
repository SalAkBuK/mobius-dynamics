import numpy as np
from PIL import Image
import os

# Explore parameter space around base coefficients:
# base: a = -0.755 + 0.33i, b = -0.376 + 0.026i, c = 6.401 + 0.803i, d = 1.52 + 0.84i

def simulate_and_render(a, b, c, d, n, W=600, H=600, steps=150, P=20000, filename="param_test.png", zoom=1.65, cx=0.0, cy=0.0):
    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    
    # Initialize particles
    radii = np.random.uniform(0.2, 0.6, P)
    thetas = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * thetas)).astype(np.complex128)
    
    accum = np.zeros((H, W), dtype=np.float32)
    
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
    
    # Simulation & accumulation
    for _ in range(steps):
        k = np.random.randint(0, n, size=P)
        om = omegas[k]
        num = a * z + b
        den = c * z + d
        den_mag_sq = den.real**2 + den.imag**2
        mask_bad = (den_mag_sq < 1e-7) | (np.abs(z) > 10.0) | np.isnan(z.real)
        inv_den = np.where(mask_bad, 0, den.conjugate() / np.maximum(den_mag_sq, 1e-7))
        z = np.where(mask_bad, 0.3 * np.exp(1j * np.random.uniform(0, 2*np.pi, P)), om * (num * inv_den))
        
        # Project
        px = ((z.real - cx) * zoom + 1.0) * 0.5 * (W - 1)
        py = ((-z.imag + cy) * zoom + 1.0) * 0.5 * (H - 1)
        
        valid = (px >= 0) & (px < W) & (py >= 0) & (py < H) & (~mask_bad)
        if np.any(valid):
            np.add.at(accum, (py[valid].astype(np.int32), px[valid].astype(np.int32)), 1.0)
            
    # Tonemap (high dynamic range)
    norm = np.log1p(accum * 0.8) / np.log1p(np.max(accum) * 0.8 + 1e-5)
    img_gray = (np.clip(norm, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img_gray).save(filename)
    return np.max(accum)

# Candidate parameter sets to explore:
candidates = [
    # Baseline
    ("base_16", complex(-0.755, 0.33), complex(-0.376, 0.026), complex(6.401, 0.803), complex(1.52, 0.84), 16),
    ("base_8", complex(-0.755, 0.33), complex(-0.376, 0.026), complex(6.401, 0.803), complex(1.52, 0.84), 8),
    ("base_24", complex(-0.755, 0.33), complex(-0.376, 0.026), complex(6.401, 0.803), complex(1.52, 0.84), 24),
    
    # Candidate 1: Delicate orbital lace (higher c magnitude, tighter loops)
    ("c1_lace", complex(-0.720, 0.380), complex(-0.390, 0.015), complex(7.150, 0.950), complex(1.68, 0.76), 16),
    
    # Candidate 2: Organic knot (asymmetric pinch, strong curl)
    ("c2_knot", complex(-0.840, 0.280), complex(-0.340, 0.065), complex(5.850, 1.150), complex(1.42, 0.98), 8),
    
    # Candidate 3: Caustic Crown (sharp inner boundary, outer interference)
    ("c3_crown", complex(-0.785, 0.315), complex(-0.410, 0.010), complex(6.650, 0.650), complex(1.58, 0.92), 16),
    
    # Candidate 4: Filament storm (braided, non-trivial high-n interference for n=24)
    ("c4_storm24", complex(-0.695, 0.415), complex(-0.385, -0.015), complex(7.450, 1.250), complex(1.72, 0.65), 24),
    
    # Candidate 5: High-n broken symmetry / secondary orbits
    ("c5_braid24", complex(-0.810, 0.250), complex(-0.355, 0.045), complex(6.120, 1.050), complex(1.45, 1.02), 24),
    
    # Candidate 6: Deep recursion specimen
    ("c6_deep", complex(-0.765, 0.345), complex(-0.372, 0.030), complex(6.520, 0.820), complex(1.54, 0.85), 12),
]

for name, a, b, c, d, n in candidates:
    fname = f"search_{name}.png"
    max_acc = simulate_and_render(a, b, c, d, n, filename=fname)
    print(f"Rendered {fname}: max_acc={max_acc:.1f}")
