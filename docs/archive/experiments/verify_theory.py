import numpy as np
from PIL import Image

def verify_theory():
    n = 12
    # Base coefficients
    # Choose values that give a gorgeous, rich structure
    a = complex(0.86, 0.42)
    b = complex(0.52, -0.26)
    c = complex(-0.34, 0.40)
    d = complex(0.92, -0.12)
    
    # Det normalize
    det = a*d - b*c
    s = np.sqrt(det)
    a /= s; b /= s; c /= s; d /= s
    
    # Inverse: [d, -b; -c, a]
    inv_a, inv_b, inv_c, inv_d = d, -b, -c, a
    
    # M^2
    a2 = a*a + b*c
    b2 = a*b + b*d
    c2 = c*a + d*c
    d2 = c*b + d*d
    s2 = np.sqrt(a2*d2 - b2*c2)
    a2 /= s2; b2 /= s2; c2 /= s2; d2 /= s2

    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    # Interleaved sub-roots (k + 0.5)
    omegas_sub = np.array([np.exp(2j * np.pi * (k + 0.5) / n) for k in range(n)], dtype=np.complex128)
    # Higher harmonic (2n)
    omegas_lace = np.array([np.exp(2j * np.pi * k / (2 * n)) for k in range(2 * n)], dtype=np.complex128)

    def eval_mob(A, B, C, D, u):
        den = C * u + D
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.0015)
        return (A * u + B) * inv_den

    def V_organism(z_arr):
        # 1. Forward Mobius field
        Mf = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(a, b, c, d, u)
            Mf += w * (m - u)
        Mf /= n
        
        # 2. Inverse Mobius field (recirculation)
        Mi = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(inv_a, inv_b, inv_c, inv_d, u)
            Mi += w * (m - u)
        Mi /= n
        
        # 3. Recursive sub-loops inside lobes (M^2 on interleaved roots)
        Msub = np.zeros_like(z_arr)
        for w in omegas_sub:
            u = z_arr / w
            m = eval_mob(a2, b2, c2, d2, u)
            Msub += w * (m - u)
        Msub /= n
        
        # 4. Filament lace (2n harmonic)
        Mlace = np.zeros_like(z_arr)
        for w in omegas_lace:
            u = z_arr / w
            m = eval_mob(a, b, c, d, u)
            Mlace += w * (m - u)
        Mlace /= (2 * n)

        # Holomorphic phases
        rot_f = np.exp(1j * (-1.25))
        rot_i = np.exp(1j * (1.15))
        rot_sub = np.exp(1j * (-0.75))
        rot_lace = np.exp(1j * (0.95))
        
        vf = rot_f * Mf
        vi = rot_i * Mi
        vsub = rot_sub * Msub * 0.42
        vlace = rot_lace * Mlace * 0.22
        
        # Outer containment haze (-0.08 * z)
        vcontain = -0.06 * z_arr
        
        return vf + vi + vsub + vlace + vcontain

    W, H = 1200, 1200
    accum = np.zeros((H, W), dtype=np.float32)
    
    np.random.seed(999)
    P = 45000
    steps = 500
    dt = 0.003
    
    radii = np.random.uniform(0.35, 2.6, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.35
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = V_organism(z)
        k2 = V_organism(z + 0.5 * dt * k1)
        k3 = V_organism(z + 0.5 * dt * k2)
        k4 = V_organism(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        r_next = np.abs(z_next)
        mask = (r_next > 0.04) & (r_next < 5.0) & (~np.isnan(z_next.real))
        
        px0 = np.clip(((z.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real[mask] - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag[mask] - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        np.add.at(accum, (py0, px0), 1.0)
        np.add.at(accum, (py1, px1), 1.0)
        
        dead = ~mask
        if np.any(dead):
            r_respawn = np.random.uniform(0.4, 2.4, np.sum(dead))
            th_respawn = np.random.uniform(0, 2*np.pi, np.sum(dead))
            z_next[dead] = r_respawn * np.exp(1j * th_respawn)
            
        z = z_next
        
    # Color tonemapping matching palette
    # Deep cobalt blue -> Electric blue -> Icy white
    norm = np.log1p(accum * 0.12)
    if norm.max() > 0:
        norm /= norm.max()
        
    rgb = np.zeros((H, W, 3), dtype=np.uint8)
    
    # col_bg = [2, 4, 8]
    # col_cobalt = [14, 42, 120]
    # col_electric = [30, 130, 255]
    # col_icy = [216, 244, 255]
    # col_white = [255, 255, 255]
    
    t1 = np.clip(norm / 0.25, 0, 1)[:, :, None]
    c1 = (1 - t1) * [2, 4, 8] + t1 * [14, 42, 120]
    
    t2 = np.clip((norm - 0.25) / 0.40, 0, 1)[:, :, None]
    c2 = (1 - t2) * [14, 42, 120] + t2 * [30, 130, 255]
    
    t3 = np.clip((norm - 0.65) / 0.30, 0, 1)[:, :, None]
    c3 = (1 - t3) * [30, 130, 255] + t3 * [216, 244, 255]
    
    t4 = np.clip((norm - 0.95) / 0.05, 0, 1)[:, :, None]
    c4 = (1 - t4) * [216, 244, 255] + t4 * [255, 255, 255]
    
    final_c = np.where(norm[:, :, None] < 0.25, c1,
              np.where(norm[:, :, None] < 0.65, c2,
              np.where(norm[:, :, None] < 0.95, c3, c4)))
              
    Image.fromarray(final_c.astype(np.uint8)).save("c:/Users/saleh/Documents/antigravity/METH/verify_theory.png")
    print("Saved verify_theory.png successfully!")

verify_theory()
