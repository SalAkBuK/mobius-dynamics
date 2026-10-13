import numpy as np
from PIL import Image

def test_fixed_point_mobius():
    n = 12
    # Inner caustic fixed point
    zeta1 = complex(0.75, 0.15)
    # Outer lobe fixed point
    zeta2 = complex(2.30, 0.45)
    
    # Multiplier mu: slightly loxodromic / elliptic
    # angle controls swirl, radius controls expansion/contraction
    r_mu = 0.96
    theta_mu = 1.35
    mu = r_mu * np.exp(1j * theta_mu)
    
    # Form Mobius coefficients:
    a = zeta1 - mu * zeta2
    b = (mu - 1.0) * zeta1 * zeta2
    c = 1.0 - mu
    d = mu * zeta1 - zeta2
    
    # Normalize det = 1
    det = a * d - b * c
    s = np.sqrt(det)
    a /= s; b /= s; c /= s; d /= s
    
    print(f"Mobius coefficients:")
    print(f"a = {a.real:.4f} + {a.imag:.4f}i")
    print(f"b = {b.real:.4f} + {b.imag:.4f}i")
    print(f"c = {c.real:.4f} + {c.imag:.4f}i")
    print(f"d = {d.real:.4f} + {d.imag:.4f}i")
    
    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    
    # Symmetrized Mobius flow:
    def eval_mob(u):
        den = c * u + d
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.001)
        return (a * u + b) * inv_den

    def V(z_arr):
        # Primary Mobius flow
        res = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(u)
            # Generator: (m - u)
            res += w * (m - u)
        res /= n
        
        # Second harmonic Mobius flow (M^2) for recursive sub-loops inside lobes
        # M^2 has multiplier mu^2
        mu2 = mu * mu
        a2 = (zeta1 - mu2 * zeta2)
        b2 = (mu2 - 1.0) * zeta1 * zeta2
        c2 = (1.0 - mu2)
        d2 = (mu2 * zeta1 - zeta2)
        det2 = a2 * d2 - b2 * c2
        s2 = np.sqrt(det2)
        a2 /= s2; b2 /= s2; c2 /= s2; d2 /= s2
        
        res2 = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            den2 = c2 * u + d2
            inv_den2 = den2.conjugate() / np.maximum(den2.real**2 + den2.imag**2, 0.001)
            m2 = (a2 * u + b2) * inv_den2
            res2 += w * (m2 - u)
        res2 /= n
        
        # Combine primary loop flow and recursive sub-loop flow
        # Trajectories circulate along lobes and weave nested filaments
        return res + 0.45 * res2

    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    np.random.seed(42)
    P = 35000
    steps = 400
    dt = 0.004
    
    radii = np.random.uniform(0.4, 2.5, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.35
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = V(z)
        k2 = V(z + 0.5 * dt * k1)
        k3 = V(z + 0.5 * dt * k2)
        k4 = V(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        r_next = np.abs(z_next)
        mask = (r_next > 0.04) & (r_next < 4.5) & (~np.isnan(z_next.real))
        
        px0 = np.clip(((z.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        np.add.at(accum, (py0, px0), 1.0)
        np.add.at(accum, (py1, px1), 1.0)
        
        dead = ~mask
        if np.any(dead):
            r_respawn = np.random.uniform(0.5, 2.4, np.sum(dead))
            th_respawn = np.random.uniform(0, 2*np.pi, np.sum(dead))
            z_next[dead] = r_respawn * np.exp(1j * th_respawn)
            
        z = z_next
        
    norm = np.log1p(accum * 0.15)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_exact_mobius.png")
    print("Saved test_exact_mobius.png")

test_fixed_point_mobius()
