import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from db.mysql_helper import MysqlHelper
from mapping.homography import HomographyMapper
from visualize.pitch_vis import draw_pitch, draw_player, init_pitch
from visualize.video_vis import draw_on_frame, speed_to_color
from vision.detector import PlayerDetector
from vision.tracker import PlayerTracker


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_VIDEO = DATA_DIR / "match.mp4"
HOMOGRAPHY_FILE = DATA_DIR / "homography.json"
LATEST_RESULT_FILE = DATA_DIR / "latest_result.json"
RESULTS_DIR = DATA_DIR / "results"
ULTRALYTICS_CONFIG_DIR = PROJECT_ROOT / "Ultralytics"

ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))

WINDOW = 3
MIN_DIST = 0.005
MAX_SPEED = 12.0
MAX_ACC = 12.0
MAX_TRACK = 50
PITCH_OVERLAY_RATIO = 0.32


def _create_video_writer(output_path, fps, frame_size):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, frame_size)
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")
    return writer


def _overlay_pitch(frame, pitch_img):
    frame_h, frame_w = frame.shape[:2]
    overlay_w = max(240, int(frame_w * PITCH_OVERLAY_RATIO))
    overlay_h = int(pitch_img.shape[0] * overlay_w / pitch_img.shape[1])
    overlay_h = min(overlay_h, max(120, frame_h // 2))
    overlay = cv2.resize(pitch_img, (overlay_w, overlay_h), interpolation=cv2.INTER_AREA)

    pad = 16
    x1 = frame_w - overlay_w - pad
    y1 = pad
    x2 = x1 + overlay_w
    y2 = y1 + overlay_h

    cv2.rectangle(frame, (x1 - 4, y1 - 28), (x2 + 4, y2 + 4), (0, 0, 0), -1)
    cv2.rectangle(frame, (x1 - 4, y1 - 28), (x2 + 4, y2 + 4), (255, 255, 255), 2)
    cv2.putText(
        frame,
        "Pitch View",
        (x1, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )
    frame[y1:y2, x1:x2] = overlay
    return frame


def _json_safe_tracks(tracks):
    return {str(track_id): points for track_id, points in tracks.items()}


def _load_homography():
    if not HOMOGRAPHY_FILE.exists():
        raise FileNotFoundError(f"Homography file not found: {HOMOGRAPHY_FILE}")

    with HOMOGRAPHY_FILE.open("r", encoding="utf-8") as f:
        return np.array(json.load(f), dtype=float)


def _calc_average(values, counts):
    result = {}
    for track_id, count in counts.items():
        if count > 0:
            result[track_id] = values[track_id] / count
    return result


def analyze_video(video_path):
    video_path = Path(video_path).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25.0
    dt = 1.0 / fps
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if frame_w <= 0 or frame_h <= 0:
        raise RuntimeError(f"Cannot read video size: {video_path}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_video = RESULTS_DIR / f"result_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.mp4"

    pixel_tracks = defaultdict(list)
    world_tracks_raw = defaultdict(list)
    world_tracks_smooth = defaultdict(list)
    prev_speeds = {}
    prev_accs = {}
    speed_sum = defaultdict(float)
    acc_sum = defaultdict(float)
    frame_count = defaultdict(int)
    pitch_img = init_pitch()
    writer = None

    try:
        detector = PlayerDetector(model_path=str(PROJECT_ROOT / "yolov8n.pt"))
        tracker = PlayerTracker()
        mapper = HomographyMapper(_load_homography())
        writer = _create_video_writer(output_video, fps, (frame_w, frame_h))

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detections = detector.detect(frame)
            tracks = tracker.update(detections, frame)
            draw_pitch(pitch_img)

            for trk in tracks:
                if not trk.is_confirmed():
                    continue

                track_id = int(trk.track_id)
                left, top, right, bottom = map(int, trk.to_ltrb())
                cx = int((left + right) / 2)
                cy = int(bottom)

                pixel_tracks[track_id].append((cx, cy))
                x_m, y_m = mapper.pixel_to_world((cx, cy))
                world_tracks_raw[track_id].append((x_m, y_m))

                if len(world_tracks_raw[track_id]) > MAX_TRACK:
                    world_tracks_raw[track_id] = world_tracks_raw[track_id][-MAX_TRACK:]

                if world_tracks_smooth[track_id]:
                    px, py = world_tracks_smooth[track_id][-1]
                    smooth_x = 0.2 * x_m + 0.8 * px
                    smooth_y = 0.2 * y_m + 0.8 * py
                else:
                    smooth_x, smooth_y = x_m, y_m
                world_tracks_smooth[track_id].append((smooth_x, smooth_y))
                if len(world_tracks_smooth[track_id]) > MAX_TRACK:
                    world_tracks_smooth[track_id] = world_tracks_smooth[track_id][-MAX_TRACK:]

                if len(world_tracks_raw[track_id]) > WINDOW:
                    prev = world_tracks_raw[track_id][-WINDOW]
                    curr = world_tracks_raw[track_id][-1]
                    dx = curr[0] - prev[0]
                    dy = curr[1] - prev[1]
                    dist = float(np.sqrt(dx * dx + dy * dy))
                    speed = 0.0 if dist < MIN_DIST else dist / (dt * WINDOW)
                else:
                    speed = 0.0

                speed = min(float(speed), MAX_SPEED)

                if track_id in prev_speeds:
                    acc = (speed - prev_speeds[track_id]) / (dt * WINDOW)
                else:
                    acc = 0.0

                if track_id in prev_accs:
                    acc = 0.7 * prev_accs[track_id] + 0.3 * acc

                if abs(acc) > MAX_ACC:
                    acc = prev_accs.get(track_id, 0.0)

                prev_speeds[track_id] = speed
                prev_accs[track_id] = acc
                speed_sum[track_id] += speed
                acc_sum[track_id] += acc
                frame_count[track_id] += 1

                draw_on_frame(
                    frame,
                    (left, top, right, bottom),
                    track_id,
                    speed,
                    pixel_tracks[track_id],
                )
                draw_player(pitch_img, (smooth_x, smooth_y), speed_to_color(speed))

            _overlay_pitch(frame, pitch_img)
            writer.write(frame)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()

    avg_speeds = _calc_average(speed_sum, frame_count)
    avg_accs = _calc_average(acc_sum, frame_count)
    track_count = len(avg_speeds)
    overall_avg_speed = sum(avg_speeds.values()) / track_count if track_count else 0.0
    overall_avg_acc = sum(avg_accs.values()) / track_count if track_count else 0.0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "avg_speeds.json").open("w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in avg_speeds.items()}, f, ensure_ascii=False, indent=2)
    with (DATA_DIR / "avg_accs.json").open("w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in avg_accs.items()}, f, ensure_ascii=False, indent=2)
    with (DATA_DIR / "world_tracks.json").open("w", encoding="utf-8") as f:
        json.dump(_json_safe_tracks(world_tracks_raw), f, ensure_ascii=False, indent=2)

    result = {
        "video_name": video_path.name,
        "video_path": str(video_path),
        "avg_speed": float(overall_avg_speed),
        "avg_acc": float(overall_avg_acc),
        "track_count": int(track_count),
        "output_video": str(output_video),
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with LATEST_RESULT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    MysqlHelper.insert_analysis_result(result, avg_speeds, avg_accs)

    return result


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    video_path = argv[0] if argv else str(DEFAULT_VIDEO)
    result = analyze_video(video_path)

    print("Analysis finished")
    print(f"Video: {result['video_name']}")
    print(f"Average speed: {result['avg_speed']:.2f} m/s")
    print(f"Average acceleration: {result['avg_acc']:.2f} m/s^2")
    print(f"Track count: {result['track_count']}")
    print(f"Output video: {result['output_video']}")


if __name__ == "__main__":
    main()
