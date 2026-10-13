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

# Test branch sampling for local lobe
# Suppose we focus on lobe 0 (around angle 0)
# What if we sample from all branches vs biased?
print("Testing branch sampling...")
