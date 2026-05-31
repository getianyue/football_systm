import json
import matplotlib.pyplot as plt

# ---------- 读取数据 ----------
with open("data/avg_speeds.json", "r") as f:
    avg_speeds = json.load(f)

with open("data/avg_accs.json", "r") as f:
    avg_accs = json.load(f)

# ---------- 排序（按速度从高到低） ----------
sorted_ids = sorted(avg_speeds, key=lambda x: avg_speeds[x], reverse=True)

ids = sorted_ids
speeds = [avg_speeds[i] for i in ids]
accs = [avg_accs[i] for i in ids]

# ==============================
# 1️⃣ 平均速度图
# ==============================
plt.figure()

avg_reference = 3.0  # m/s（正常比赛平均水平）

plt.bar(ids, speeds)
plt.axhline(y=avg_reference, linestyle='--')

plt.xlabel("Player ID")
plt.ylabel("Average Speed (m/s)")
plt.title("Average Speed Comparison")

plt.grid(True)
plt.savefig("avg_speed.png")
plt.close()

# ==============================
# 2️⃣ 平均加速度图
# ==============================
plt.figure()

acc_reference = 1.5  # m/s²（正常范围）

plt.bar(ids, accs)
plt.axhline(y=acc_reference, linestyle='--')

plt.xlabel("Player ID")
plt.ylabel("Average Acceleration (m/s²)")
plt.title("Average Acceleration Comparison")

plt.grid(True)
plt.savefig("avg_acc.png")
plt.close()

print("图已生成：avg_speed.png 和 avg_acc.png")
