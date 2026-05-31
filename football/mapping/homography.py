import numpy as np

class HomographyMapper:
    def __init__(self, H):
        self.H = H

    def pixel_to_world(self, pt):
        p = np.array([pt[0], pt[1], 1.0])
        w = self.H @ p
        w /= w[2]
        return float(w[0]), float(w[1])
