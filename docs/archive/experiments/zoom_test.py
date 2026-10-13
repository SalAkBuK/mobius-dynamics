import numpy as np
from PIL import Image

def test_zoom():
    n = 12
    a = complex(0.88, 0.36)
    b = complex(0.54, -0.24)
    c = complex(-0.32, 0.38)
    d = complex(0.94, -0.10)
    
    det = a*d - b*c
    s = np.sqrt(det)
    a /= s; b /= s; c /= s; d /= s
    
    inv_a = d
    inv_b = -b
    inv_c = -c
    inv_d = a

    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    omegas_sub = np.array([np.exp(2j * np.pi * (k + 0.5) / n) for k in range(n)], dtype=np.complex128)

    def eval_mob(A, B, C, D, u):
        den = C * u + D
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.002)
        return (A * u + B) * inv_den

    def V_tangle(z_arr):
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
        
        M2_a = a*a + b*c
        M2_b = a*b + b*d
        M2_c = c*a + d*c
        M2_d = c*b + d*d
        s2 = np.sqrt(M2_a*M2_d - M2_b*M2_c)
        M2_a /= s2; M2_b /= s2; M2_c /= s2; M2_d /= s2
        
        Msub = np.zeros_like(z_arr)
        for w in omegas_sub:
            u = z_arr / w
            m = eval_mob(M2_a, M2_b, M2_c, M2_d, u)
            Msub += w * (m - u)
        Msub /= n

        rot_f = np.exp(1j * (-1.20))
        rot_i = np.exp(1j * (1.20))
        rot_sub = np.exp(1j * (-0.80))
        
        return rot_f * Mf + rot_i * Mi + rot_sub * Msub * 0.35

    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    # Zoom right into the caustic boundary of a lobe: center around (0.8, 0.6), zoom = 5.0
    zoom = 6.0
    cx, cy = 0.9, 0.7
    
    np.random.seed(42)
    P = 40000
    steps = 450
    dt = 0.001 / zoom
    
    # Seed particles right inside the zoomed region
    xs = np.random.uniform(cx - 1.2/zoom, cx + 1.2/zoom, P)
    ys = np.random.uniform(cy - 1.2/zoom, cy + 1.2/zoom, P)
    z = (xs + 1j * ys).astype(np.complex128)
    
    for s in range(steps):
        k1 = V_tangle(z)
        k2 = V_tangle(z + 0.5 * dt * k1)
        k3 = V_tangle(z + 0.5 * dt * k2)
        k4 = V_tangle(z + dt * k3)
        z_next = z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        px0 = np.clip(((z.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py0 = np.clip(((-z.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        px1 = np.clip(((z_next.real - cx) * zoom * (W / 2) + W / 2).astype(np.int32), 0, W - 1)
        py1 = np.clip(((-z_next.imag - cy) * zoom * (H / 2) + H / 2).astype(np.int32), 0, H - 1)
        
        np.add.at(accum, (py0, px0), 1.0)
        np.add.at(accum, (py1, px1), 1.0)
        z = z_next
        
    norm = np.log1p(accum * 0.15)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_zoom.png")
    print("Saved test_zoom.png")

test_zoom()
