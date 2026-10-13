import numpy as np
from PIL import Image

def experiment_A():
    # Test discrete map with smooth spline / segment interpolation
    # z_{m+1} = w_k * (a*z_m + b)/(c*z_m + d)
    # How does k change? 
    # Suppose k is chosen by a deterministic or chaotic sequence, or cycling:
    # e.g., k = (m % n) or k chosen by angle sector: k = floor(angle * n / (2*pi))
    pass

print("Testing concepts...")
