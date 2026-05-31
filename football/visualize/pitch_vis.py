import cv2
import numpy as np

PITCH_W, PITCH_H = 105, 68
SCALE = 8

def init_pitch():
    img = np.ones((PITCH_H*SCALE, PITCH_W*SCALE, 3), dtype=np.uint8) * 40
    draw_pitch(img)
    return img


def draw_pitch(img):
    img[:] = 40
    cv2.rectangle(img, (0, 0), (PITCH_W*SCALE, PITCH_H*SCALE), (255, 255, 255), 2)
    cv2.line(img, (PITCH_W*SCALE//2, 0), (PITCH_W*SCALE//2, PITCH_H*SCALE), (255, 255, 255), 2)
    cv2.circle(img, (PITCH_W*SCALE//2, PITCH_H*SCALE//2),
               int(9.15*SCALE), (255, 255, 255), 2)


def draw_player(img, pos, color):
    x, y = pos
    px = int(x * SCALE)
    py = int((PITCH_H - y) * SCALE)
    cv2.circle(img, (px, py), 4, color, -1)
