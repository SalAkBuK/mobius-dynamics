import numpy as np
from PIL import Image

def test_streamlines():
    n = 12
    # Let's choose a, b, c, d so that:
    # 1. |d/c| ~ 1.4 (poles around r = 1.4)
    # 2. det(M) / d^2 has positive real part or imaginary part for swirl
    
    # Let c = -0.6 * exp(i * 0.2), d = 0.9 * exp(-i * 0.1) -> |d/c| = 1.5
    # Let a = 1.1 * exp(i * 0.5), b = 0.7 * exp(-i * 0.3)
    
    a = complex(0.95, 0.45)
    b = complex(0.65, -0.35)
    c = complex(-0.45, 0.50)
    d = complex(0.95, -0.15)
    
    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    
    # Phase rotation
    phi = -1.25 # swirl
    rot = np.exp(1j * phi)
    
    def G(z_arr):
        # Symmetrized Mobius map:
        # G(z) = (1/n) * sum_k w_k * ( (a*u_k + b) / (c*u_k + d) )
        res = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            den = c * u + d
            # Soften singularity very slightly to prevent NaN
            den_mag_sq = den.real**2 + den.imag**2
            inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.002)
            m = (a * u + b) * inv_den
            res += w * m
        return res / n

    def V(z_arr):
        # Velocity field: rot * (G(z) - 0.7 * z)
        # We can also add higher-order Mobius or reciprocal terms
        return rot * (G(z_arr) - 0.65 * z_arr)

    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    # Trace 20000 particles for 400 steps
    np.random.seed(123)
    P = 25000
    steps = 400
    dt = 0.004
    
    radii = np.random.uniform(0.3, 2.5, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.38
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = V(z)
        k2 = V(z + 0.5 * dt * k1)
        k3 = V(z + 0.5 * dt * k2)
        k4 = V(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        # Discard runaway or dead particles
        r_next = np.abs(z_next)
        mask = (r_next > 0.05) & (r_next < 4.5) & (~np.isnan(z_next.real))
        
        px0 = np.clip(((z.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        np.add.at(accum, (py0, px0), 1.0)
        np.add.at(accum, (py1, px1), 1.0)
        
        # Respawn dead particles
        dead = ~mask
        if np.any(dead):
            r_respawn = np.random.uniform(0.4, 2.2, np.sum(dead))
            th_respawn = np.random.uniform(0, 2*np.pi, np.sum(dead))
            z_next[dead] = r_respawn * np.exp(1j * th_respawn)
            
        z = z_next
        
    norm = np.log1p(accum * 0.1)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_streamline1.png")
    print("Saved test_streamline1.png")

test_streamlines()
