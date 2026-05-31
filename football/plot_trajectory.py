import json
import numpy as np
import matplotlib.pyplot as plt

# ---------- 读取数据 ----------
with open("data/world_tracks.json", "r") as f:
    tracks = json.load(f)

# ---------- 创建球场 ----------
def draw_pitch():
    fig, ax = plt.subplots(figsize=(12, 8))

    # 标准足球场（单位：米）
    length = 105
    width = 68

    # 边界
    ax.plot([0, length, length, 0, 0],
            [0, 0, width, width, 0], linewidth=2)

    # 中线
    ax.plot([length/2, length/2], [0, width], linewidth=2)

    # 中圈
    center_circle = plt.Circle((length/2, width/2), 9.15, fill=False)
    ax.add_patch(center_circle)

    # 禁区
    ax.plot([0, 16.5, 16.5, 0],
            [width/2-20.15, width/2-20.15, width/2+20.15, width/2+20.15])

    ax.plot([length, length-16.5, length-16.5, length],
            [width/2-20.15, width/2-20.15, width/2+20.15, width/2+20.15])

    ax.set_xlim(0, length)
    ax.set_ylim(0, width)
    ax.set_aspect('equal')
    ax.set_title("Player Trajectories (Top View)", fontsize=16)

    return fig, ax

# ---------- 平滑轨迹 ----------
def smooth_track(track, window=5):
    if len(track) < window:
        return track

    smoothed = []
    for i in range(len(track)):
        start = max(0, i - window)
        pts = track[start:i+1]
        x = np.mean([p[0] for p in pts])
        y = np.mean([p[1] for p in pts])
        smoothed.append((x, y))
    return smoothed

# ---------- 绘制 ----------
fig, ax = draw_pitch()

colors = plt.cm.tab10.colors  # 10种颜色

for i, (tid, pts) in enumerate(tracks.items()):
    pts = smooth_track(pts, window=5)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    color = colors[i % len(colors)]

    # 轨迹线
    ax.plot(xs, ys, linewidth=2, color=color, label=f"ID {tid}")

    # 起点
    ax.scatter(xs[0], ys[0], color=color, marker='o', s=40)

    # 终点
    ax.scatter(xs[-1], ys[-1], color=color, marker='X', s=60)

# 图例
ax.legend(loc='upper right', fontsize=8)

# 坐标轴
ax.set_xlabel("X (meters)")
ax.set_ylabel("Y (meters)")

# 保存
plt.savefig("trajectory.png", dpi=300, bbox_inches='tight')
plt.show()
