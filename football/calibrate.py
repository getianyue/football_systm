import cv2
import numpy as np
import json

VIDEO_PATH = "data/match.mp4"

# 世界坐标（单位：米）
world_points = np.array([
    [52.5, 0],      # 中线下边线
    [52.5, 34],     # 中圈中心
    [88.5, 0],      # 右禁区下角
    [88.5, 40.32],  # 右禁区上角
], dtype=np.float32)


clicked_points = []

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Clicked: {x}, {y}")
        clicked_points.append([x, y])

cap = cv2.VideoCapture(VIDEO_PATH)
ret, frame = cap.read()
cap.release()

cv2.imshow("Click Points in Order", frame)
cv2.setMouseCallback("Click Points in Order", mouse_callback)

print("请按顺序点击：")
print("1. 中线下边线交点")
print("2. 中圈中心")
print("3. 右禁区下角")
print("4. 右禁区上角")

while True:
    cv2.imshow("Click Points in Order", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break
    if len(clicked_points) == 4:
        break

cv2.destroyAllWindows()

image_points = np.array(clicked_points, dtype=np.float32)

H, _ = cv2.findHomography(image_points, world_points)

with open("data/homography.json", "w") as f:
    json.dump(H.tolist(), f)

print("Homography saved to data/homography.json")
