import numpy as np
import cv2
import math

# ==============================
# 1️⃣ 世界坐标（和你标定时一致）
# ==============================
world_points = np.array([
    [52.5, 0],
    [52.5, 34],
    [88.5, 0],
    [88.5, 40.32],
], dtype=np.float32)

# ==============================
# 2️⃣ 你的真实点击点
# ==============================
image_points_original = np.array([
    [513, 795],
    [475, 497],
    [1610, 579],
    [1220, 384],
], dtype=np.float32)

# ==============================
# 3️⃣ 计算基准 H₀
# ==============================
H0, _ = cv2.findHomography(image_points_original, world_points)

# ==============================
# 4️⃣ 选一个测试点
# ==============================
test_point = np.array([1000, 600], dtype=np.float32)

def project_point(H, point):
    point_h = np.array([point[0], point[1], 1.0])
    projected = H @ point_h
    projected /= projected[2]
    return projected[:2]

base_projection = project_point(H0, test_point)


print("基准投影坐标（米）:", base_projection)

# ==============================
# 5️⃣ 误差实验
# ==============================
pixel_shifts = [2, 5, 10]

print("\n误差分析结果：")
print("像素偏移  →  顶视图误差（米）")

for shift in pixel_shifts:

    image_points_shifted = image_points_original.copy()

    # 对第一个点人为加偏移
    image_points_shifted[0][0] += shift

    H1, _ = cv2.findHomography(image_points_shifted, world_points)

    new_projection = project_point(H1, test_point)

    error = math.sqrt(
        (base_projection[0] - new_projection[0])**2 +
        (base_projection[1] - new_projection[1])**2
    )

    print(f"{shift:>6} px  →  {error:.3f} m")
