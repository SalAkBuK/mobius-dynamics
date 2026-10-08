import numpy as np
from PIL import Image

def run_experiment_1():
    n = 12
    a = complex(0.85, 0.38)
    b = complex(0.50, -0.22)
    c = complex(-0.28, 0.35)
    d = complex(0.92, -0.08)
    
    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    
    def F_vec(z_arr):
        # z_arr shape: (P,)
        res = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            den = c * u + d
            den_mag = np.abs(den)
            # prevent division by zero
            safe_den = np.where(den_mag < 0.05, (den / np.maximum(den_mag, 1e-6)) * 0.05, den)
            m = (a * u + b) / safe_den
            res += w * (m - u)
        return res
    
    np.random.seed(42)
    P = 15000
    steps = 120
    dt = 0.008
    
    radii = np.random.uniform(0.3, 2.5, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.4
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = F_vec(z)
        k2 = F_vec(z + 0.5 * dt * k1)
        k3 = F_vec(z + 0.5 * dt * k2)
        k4 = F_vec(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        px0 = np.clip(((z.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        valid = np.abs(z_next - z) < 0.5
        np.add.at(accum, (py0[valid], px0[valid]), 1.0)
        np.add.at(accum, (py1[valid], px1[valid]), 1.0)
        z = z_next
        
    norm = np.log1p(accum * 0.5)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_exp1.png")
    print("Saved test_exp1.png successfully!")

run_experiment_1()
