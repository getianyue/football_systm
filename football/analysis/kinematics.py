import numpy as np

def moving_average(traj, window=7):
    if len(traj) < window:
        return traj[-1]
    xs = [p[0] for p in traj[-window:]]
    ys = [p[1] for p in traj[-window:]]
    return np.mean(xs), np.mean(ys)


def compute_speed(p1, p2, dt):
    dist = np.linalg.norm(np.array(p1) - np.array(p2))
    v = dist / dt
    return min(v * 3.6, 40.0)  # km/h + 生理约束
