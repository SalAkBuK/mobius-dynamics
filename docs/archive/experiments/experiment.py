import numpy as np
from PIL import Image
import math

def test_discrete_ifs():
    # Test discrete iterated Mobius transformations
    n = 12
    # Mobius parameters
    a = complex(0.85, 0.38)
    b = complex(0.50, -0.22)
    c = complex(-0.28, 0.35)
    d = complex(0.92, -0.08)
    
    omegas = [np.exp(2j * np.pi * k / n) for k in range(n)]
    
    W, H = 800, 800
    accum = np.zeros((H, W), dtype=np.float32)
    
    # Run multiple particle trajectories
    n_trajectories = 1000
    n_steps = 500
    
    # We want to see what happens
    print("Testing IFS...")

if __name__ == "__main__":
    test_discrete_ifs()
