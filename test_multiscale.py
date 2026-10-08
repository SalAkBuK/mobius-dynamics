import numpy as np
from PIL import Image

def test_multiscale():
    n = 12
    a = complex(0.92, 0.42)
    b = complex(0.62, -0.28)
    c = complex(-0.42, 0.48)
    d = complex(0.96, -0.12)
    
    # Mobius matrix
    # M1 = [a, b; c, d]
    # M2 = M1^2
    M1_a, M1_b = a, b
    M1_c, M1_d = c, d
    
    M2_a = a*a + b*c
    M2_b = a*b + b*d
    M2_c = c*a + d*c
    M2_d = c*b + d*d
    
    # Normalize M2
    det2 = M2_a * M2_d - M2_b * M2_c
    s2 = np.sqrt(det2)
    M2_a /= s2; M2_b /= s2; M2_c /= s2; M2_d /= s2
    
    # M_inv = [d, -b; -c, a]
    Minv_a = d
    Minv_b = -b
    Minv_c = -c
    Minv_d = a
    det_inv = Minv_a * Minv_d - Minv_b * Minv_c
    s_inv = np.sqrt(det_inv)
    Minv_a /= s_inv; Minv_b /= s_inv; Minv_c /= s_inv; Minv_d /= s_inv

    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    # Sub-harmonics for recursive loops inside lobes (e.g. 2*n or 3*n)
    omegas_sub = np.array([np.exp(2j * np.pi * k / (2 * n)) for k in range(2 * n)], dtype=np.complex128)

    def eval_mobius(A, B, C, D, u):
        den = C * u + D
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.003)
        return (A * u + B) * inv_den

    def V_multi(z_arr):
        # Macro lobes from M1
        res1 = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m1 = eval_mobius(M1_a, M1_b, M1_c, M1_d, u)
            res1 += w * m1
        res1 /= n
        
        # Recursive sub-loops from M2 (iterated Mobius) and inverse
        res2 = np.zeros_like(z_arr)
        for w in omegas_sub:
            u = z_arr / w
            m2 = eval_mobius(M2_a, M2_b, M2_c, M2_d, u)
            res2 += w * m2
        res2 /= (2 * n)
        
        # Dual stream: macro lobes + recursive internal eddy filaments
        rot1 = np.exp(-1.35j)
        rot2 = np.exp(1.10j)
        
        # Balance macro flow and nested recursive flow
        v_macro = rot1 * (res1 - 0.70 * z_arr)
        v_micro = rot2 * (res2 - 0.70 * z_arr) * 0.38
        
        return v_macro + v_micro

    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    np.random.seed(42)
    P = 30000
    steps = 450
    dt = 0.0035
    
    radii = np.random.uniform(0.35, 2.6, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.36
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = V_multi(z)
        k2 = V_multi(z + 0.5 * dt * k1)
        k3 = V_multi(z + 0.5 * dt * k2)
        k4 = V_multi(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        r_next = np.abs(z_next)
        mask = (r_next > 0.04) & (r_next < 4.8) & (~np.isnan(z_next.real))
        
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
        
    norm = np.log1p(accum * 0.12)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_multiscale.png")
    print("Saved test_multiscale.png")

test_multiscale()
