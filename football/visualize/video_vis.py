import cv2

def speed_to_color(speed):
    if speed < 3:
        return (255, 0, 0)
    elif speed < 7:
        return (0, 255, 255)
    else:
        return (0, 0, 255)


def draw_on_frame(frame, bbox, track_id, speed, track):
    l, t, r, b = bbox
    color = speed_to_color(speed)

    cv2.rectangle(frame, (l, t), (r, b), color, 2)
    label = f"ID {track_id} | {speed:.1f} m/s"
    label_pos = (max(l, 0), max(t - 10, 22))
    text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    bg_l = label_pos[0] - 4
    bg_t = label_pos[1] - text_size[1] - 6
    bg_r = label_pos[0] + text_size[0] + 4
    bg_b = label_pos[1] + 5
    cv2.rectangle(frame, (bg_l, bg_t), (bg_r, bg_b), (0, 0, 0), -1)
    cv2.putText(
        frame,
        label,
        label_pos,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2
    )

    visible_track = track[-40:]
    for i in range(1, len(visible_track)):
        cv2.line(frame, visible_track[i - 1], visible_track[i], color, 2)
