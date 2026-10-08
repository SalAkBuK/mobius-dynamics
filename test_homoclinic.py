import numpy as np
from PIL import Image

def test_homoclinic():
    n = 12
    # Base coefficients
    a = complex(0.88, 0.36)
    b = complex(0.54, -0.24)
    c = complex(-0.32, 0.38)
    d = complex(0.94, -0.10)
    
    # Det normalize
    det = a*d - b*c
    s = np.sqrt(det)
    a /= s; b /= s; c /= s; d /= s
    
    # Inverse Mobius: M^-1 = [d, -b; -c, a]
    inv_a = d
    inv_b = -b
    inv_c = -c
    inv_d = a

    omegas = np.array([np.exp(2j * np.pi * k / n) for k in range(n)], dtype=np.complex128)
    # Sub-roots for recursive micro-filaments (2n order)
    omegas_sub = np.array([np.exp(2j * np.pi * (k + 0.5) / n) for k in range(n)], dtype=np.complex128)

    def eval_mob(A, B, C, D, u):
        den = C * u + D
        den_mag_sq = den.real**2 + den.imag**2
        inv_den = den.conjugate() / np.maximum(den_mag_sq, 0.002)
        return (A * u + B) * inv_den

    def V_tangle(z_arr):
        # Forward Mobius field (outward radial lobe launcher)
        Mf = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(a, b, c, d, u)
            Mf += w * (m - u)
        Mf /= n
        
        # Inverse Mobius field (recirculating inward catcher)
        Mi = np.zeros_like(z_arr)
        for w in omegas:
            u = z_arr / w
            m = eval_mob(inv_a, inv_b, inv_c, inv_d, u)
            Mi += w * (m - u)
        Mi /= n
        
        # Nested recursive filaments from alternating root offsets (M^2)
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

        # Homoclinic tangle:
        # Forward field is phase-rotated to push outward into lobes
        # Inverse field is phase-rotated to loop them back
        # Inner orbital circulation forms the bright caustic ring
        rot_f = np.exp(1j * (-1.20))
        rot_i = np.exp(1j * (1.20))
        rot_sub = np.exp(1j * (-0.80))
        
        v_forward = rot_f * Mf
        v_inverse = rot_i * Mi
        v_sub = rot_sub * Msub * 0.35
        
        return v_forward + v_inverse + v_sub

    W, H = 1024, 1024
    accum = np.zeros((H, W), dtype=np.float32)
    
    np.random.seed(42)
    P = 35000
    steps = 450
    dt = 0.003
    
    radii = np.random.uniform(0.35, 2.6, P)
    angles = np.random.uniform(0, 2 * np.pi, P)
    z = (radii * np.exp(1j * angles)).astype(np.complex128)
    
    zoom = 0.34
    cx, cy = 0.0, 0.0
    
    for s in range(steps):
        k1 = V_tangle(z)
        k2 = V_tangle(z + 0.5 * dt * k1)
        k3 = V_tangle(z + 0.5 * dt * k2)
        k4 = V_tangle(z + dt * k3)
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
        
    norm = np.log1p(accum * 0.12)
    if norm.max() > 0:
        norm /= norm.max()
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img).save("c:/Users/saleh/Documents/antigravity/METH/test_homoclinic.png")
    print("Saved test_homoclinic.png")

test_homoclinic()
