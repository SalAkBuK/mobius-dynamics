import numpy as np
from PIL import Image

def test_deep_zoom_nested():
    n = 12
    a = complex(0.86, 0.42)
    b = complex(0.52, -0.26)
    c = complex(-0.34, 0.40)
    d = complex(0.92, -0.12)
    
    det = a*d - b*c
    s = np.sqrt(det)
    a /= s; b /= s; c /= s; d /= s
    inv_a, inv_b, inv_c, inv_d = d, -b, -c, a
    
    # M^2
    a2 = a*a + b*c
    b2 = a*b + b*d
    c2 = c*a + d*c
    d2 = c*b + d*d
    s2 = np.sqrt(a2*d2 - b2*c2)
    a2 /= s2; b2 /= s2; c2 /= s2; d2 /= s2

    # M^4 (for deep microscopic detail)
    a4 = a2*a2 + b2*c2
    b4 = a2*b2 + b2*d2
    c4 = c2*a2 + d2*c2
    d4 = c2*b2 + d2*d2
    s4 = np.sqrt(a4*d4 - b4*c4)
    a4 /= s4; b4 /= s4; c4 /= s4; d4 /= s4

    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    omegas_sub = np.array([np.exp(2j * np.pi * (k + 0.5) / n) for k in range(n)], dtype=np.complex128)
    omegas_micro = np.array([np.exp(2j * np.pi * k / (2 * n)) for k in range(2 * n)], dtype=np.complex128)

    def eval_mob(A, B, C, D, u):
        den = C * u + D
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.001)
        return (A * u + B) * inv_den

    def V_zoom(z_arr, zoom_level):
        Mf = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(a, b, c, d, u)
            Mf += w * (m - u)
        Mf /= n
        
        Mi = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(inv_a, inv_b, inv_c, inv_d, u)
            Mi += w * (m - u)
        Mi /= n
        
        Msub = np.zeros_like(z_arr)
        for w in omegas_sub:
            u = z_arr / w
            m = eval_mob(a2, b2, c2, d2, u)
            Msub += w * (m - u)
        Msub /= n
        
        # Deep microscopic component
        Mmicro = np.zeros_like(z_arr)
        for w in omegas_micro:
            u = z_arr / w
            m = eval_mob(a4, b4, c4, d4, u)
            Mmicro += w * (m - u)
        Mmicro /= (2 * n)

        rot_f = np.exp(1j * (-1.25))
        rot_i = np.exp(1j * (1.15))
        rot_sub = np.exp(1j * (-0.75))
        rot_micro = np.exp(1j * (0.85))
        
        # Microscopic amplitude scales with zoom!
        micro_weight = min(0.65, 0.20 + 0.15 * np.log10(max(1.0, zoom_level)))
        
        return (rot_f * Mf + rot_i * Mi + 
                rot_sub * Msub * 0.42 + 
                rot_micro * Mmicro * micro_weight - 
                0.05 * z_arr)

    W, H = 1000, 1000
    accum = np.zeros((H, W), dtype=np.float32)
    
    # Zoom into a lobe caustic near (0.8, 0.45) with 12x zoom
    zoom = 12.0
    cx, cy = 0.82, 0.46
    
    np.random.seed(42)
    P = 40000
    steps = 400
    dt = 0.0035 / np.sqrt(zoom)
    
    # Seed 90% of particles directly in the viewport
    half_w = 1.1 / zoom
    half_h = 1.1 / zoom
    xs = np.random.uniform(cx - half_w, cx + half_w, P)
    ys = np.random.uniform(cy - half_h, cy + half_h, P)
    z = (xs + 1j * ys).astype(np.complex128)
    
    for s in range(steps):
        k1 = V_zoom(z, zoom)
        k2 = V_zoom(z + 0.5 * dt * k1, zoom)
        k3 = V_zoom(z + 0.5 * dt * k2, zoom)
        k4 = V_zoom(z + dt * k3, zoom)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        px0 = np.clip(((z.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        # Valid only if within or near viewport
        valid = (np.abs(z_next.real - cx) < half_w * 1.5) & (np.abs(z_next.imag - cy) < half_h * 1.5)
        np.add.at(accum, (py0[valid], px0[valid]), 1.0)
        np.add.at(accum, (py1[valid], px1[valid]), 1.0)
        
        # Respawn dead/escaped
        dead = ~valid
        if np.any(dead):
            rx = np.random.uniform(cx - half_w, cx + half_w, np.sum(dead))
            ry = np.random.uniform(cy - half_h, cy + half_h, np.sum(dead))
            z_next[dead] = rx + 1j * ry
            
        z = z_next
        
    norm = np.log1p(accum * 0.08)
    if norm.max() > 0:
        norm /= norm.max()
        
    # Palette
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
              
    Image.fromarray(final_c.astype(np.uint8)).save("c:/Users/saleh/Documents/antigravity/METH/verify_deep_zoom.png")
    print("Saved verify_deep_zoom.png!")

test_deep_zoom_nested()
