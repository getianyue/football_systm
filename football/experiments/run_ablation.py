import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_VIDEO = DATA_DIR / "match.mp4"
DEFAULT_HOMOGRAPHY = DATA_DIR / "homography.json"
DEFAULT_OUTPUT_DIR = DATA_DIR / "experiments"
MODEL_PATH = PROJECT_ROOT / "yolov8n.pt"
ULTRALYTICS_CONFIG_DIR = PROJECT_ROOT / "Ultralytics"
MPL_CONFIG_DIR = DEFAULT_OUTPUT_DIR / ".matplotlib_cache"

ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

WINDOW = 3
MIN_DIST = 0.005
MAX_SPEED = 12.0
MAX_ACC = 12.0
MAX_TRACK = 50


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    detector_conf: float = 0.4
    smoothing_enabled: bool = True
    acc_filter_enabled: bool = True
    speed_constraint_enabled: bool = True
    tracker_max_age: int = 50
    tracker_n_init: int = 3
    tracker_max_cosine_distance: float = 0.4


CORE_EXPERIMENTS = [
    ExperimentConfig("baseline_full"),
    ExperimentConfig("no_smoothing", smoothing_enabled=False),
    ExperimentConfig("no_acc_filter", acc_filter_enabled=False),
    ExperimentConfig("no_speed_constraint", speed_constraint_enabled=False),
    ExperimentConfig("low_conf_0_25", detector_conf=0.25),
    ExperimentConfig("high_conf_0_60", detector_conf=0.60),
    ExperimentConfig("short_max_age_15", tracker_max_age=15),
]


def _import_runtime_dependencies():
    try:
        import cv2
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from deep_sort_realtime.deepsort_tracker import DeepSort
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "Missing runtime dependency. Install project dependencies with "
            "`pip install -r football/requirements.txt` and rerun this script."
        ) from exc

    return cv2, plt, DeepSort, YOLO


def _load_homography(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return np.array(json.load(f), dtype=float)


def _pixel_to_world(homography, point):
    p = np.array([point[0], point[1], 1.0], dtype=float)
    w = homography @ p
    w /= w[2]
    return float(w[0]), float(w[1])


def _mean(values):
    return float(np.mean(values)) if values else 0.0


def _std(values):
    return float(np.std(values)) if values else 0.0


def _safe_ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else 0.0


def _detect_players(model, frame, conf):
    results = model(frame, conf=conf, classes=[0], verbose=False)
    detections = []

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            score = float(box.conf[0])
            detections.append(([x1, y1, x2 - x1, y2 - y1], score, "person"))

    return detections


def run_core_experiment(config, video_path, homography, max_frames=None):
    cv2, _, DeepSort, YOLO = _import_runtime_dependencies()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25.0
    dt = 1.0 / fps

    os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))
    model = YOLO(str(MODEL_PATH))
    tracker = DeepSort(
        max_age=config.tracker_max_age,
        n_init=config.tracker_n_init,
        max_cosine_distance=config.tracker_max_cosine_distance,
    )

    frame_index = 0
    detection_counts = []
    track_frames = defaultdict(list)
    track_lengths = defaultdict(int)
    raw_tracks = defaultdict(list)
    smooth_tracks = defaultdict(list)
    prev_speeds = {}
    prev_accs = {}
    speeds = []
    accs = []
    clipped_speed_count = 0
    abnormal_acc_count = 0
    speed_obs_count = 0
    acc_obs_count = 0

    try:
        while cap.isOpened():
            if max_frames is not None and frame_index >= max_frames:
                break

            ret, frame = cap.read()
            if not ret:
                break

            detections = _detect_players(model, frame, config.detector_conf)
            detection_counts.append(len(detections))
            tracks = tracker.update_tracks(detections, frame=frame)

            for trk in tracks:
                if not trk.is_confirmed():
                    continue

                track_id = int(trk.track_id)
                left, top, right, bottom = map(float, trk.to_ltrb())
                cx = (left + right) / 2.0
                cy = bottom
                world_point = _pixel_to_world(homography, (cx, cy))

                raw_tracks[track_id].append(world_point)
                if len(raw_tracks[track_id]) > MAX_TRACK:
                    raw_tracks[track_id] = raw_tracks[track_id][-MAX_TRACK:]

                if smooth_tracks[track_id] and config.smoothing_enabled:
                    px, py = smooth_tracks[track_id][-1]
                    point_for_motion = (
                        0.2 * world_point[0] + 0.8 * px,
                        0.2 * world_point[1] + 0.8 * py,
                    )
                else:
                    point_for_motion = world_point

                smooth_tracks[track_id].append(point_for_motion)
                if len(smooth_tracks[track_id]) > MAX_TRACK:
                    smooth_tracks[track_id] = smooth_tracks[track_id][-MAX_TRACK:]

                motion_track = smooth_tracks[track_id] if config.smoothing_enabled else raw_tracks[track_id]
                if len(motion_track) > WINDOW:
                    prev = motion_track[-WINDOW]
                    curr = motion_track[-1]
                    dx = curr[0] - prev[0]
                    dy = curr[1] - prev[1]
                    dist = float(math.sqrt(dx * dx + dy * dy))
                    min_dist = MIN_DIST if config.speed_constraint_enabled else 0.0
                    raw_speed = 0.0 if dist < min_dist else dist / (dt * WINDOW)
                else:
                    raw_speed = 0.0

                speed_obs_count += 1
                if raw_speed > MAX_SPEED:
                    clipped_speed_count += 1

                if config.speed_constraint_enabled:
                    speed = min(float(raw_speed), MAX_SPEED)
                else:
                    speed = float(raw_speed)

                if track_id in prev_speeds:
                    raw_acc = (speed - prev_speeds[track_id]) / (dt * WINDOW)
                else:
                    raw_acc = 0.0

                acc_obs_count += 1
                if abs(raw_acc) > MAX_ACC:
                    abnormal_acc_count += 1

                if config.acc_filter_enabled:
                    acc = raw_acc
                    if track_id in prev_accs:
                        acc = 0.7 * prev_accs[track_id] + 0.3 * raw_acc
                    if abs(acc) > MAX_ACC:
                        acc = prev_accs.get(track_id, 0.0)
                else:
                    acc = raw_acc

                prev_speeds[track_id] = speed
                prev_accs[track_id] = acc
                speeds.append(speed)
                accs.append(acc)
                track_frames[track_id].append(frame_index)
                track_lengths[track_id] += 1

            frame_index += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()

    fragmentation_count = 0
    for frames in track_frames.values():
        ordered = sorted(frames)
        fragmentation_count += sum(1 for idx in range(1, len(ordered)) if ordered[idx] - ordered[idx - 1] > 1)

    return {
        "experiment": config.name,
        "avg_detections_per_frame": _mean(detection_counts),
        "confirmed_track_count": int(len(track_lengths)),
        "mean_track_length": _mean(list(track_lengths.values())),
        "fragmentation_per_100_frames": 100.0 * _safe_ratio(fragmentation_count, frame_index),
        "avg_speed_mps": _mean(speeds),
        "speed_std_mps": _std(speeds),
        "acc_std_mps2": _std(accs),
        "clipped_speed_ratio": _safe_ratio(clipped_speed_count, speed_obs_count),
        "abnormal_acc_ratio": _safe_ratio(abnormal_acc_count, acc_obs_count),
    }


def run_homography_sensitivity():
    cv2, _, _, _ = _import_runtime_dependencies()

    world_points = np.array(
        [
            [52.5, 0.0],
            [52.5, 34.0],
            [88.5, 0.0],
            [88.5, 40.32],
        ],
        dtype=np.float32,
    )
    image_points = np.array(
        [
            [513.0, 795.0],
            [475.0, 497.0],
            [1610.0, 579.0],
            [1220.0, 384.0],
        ],
        dtype=np.float32,
    )
    test_point = np.array([1000.0, 600.0], dtype=np.float32)

    base_homography, _ = cv2.findHomography(image_points, world_points)
    base_projection = np.array(_pixel_to_world(base_homography, test_point), dtype=float)
    rows = []

    for shift in (2, 5, 10):
        shifted_points = image_points.copy()
        shifted_points[0][0] += shift
        shifted_homography, _ = cv2.findHomography(shifted_points, world_points)
        shifted_projection = np.array(_pixel_to_world(shifted_homography, test_point), dtype=float)
        error = float(np.linalg.norm(base_projection - shifted_projection))
        rows.append(
            {
                "experiment": f"homography_shift_{shift}px",
                "pixel_shift_px": shift,
                "projection_error_m": error,
            }
        )

    return rows


def _write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _autolabel_bars(ax, bars, fmt="{:.2f}"):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            fmt.format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def _plot_grouped_bars(plt, rows, metrics, title, output_path):
    labels = [row["experiment"] for row in rows]
    x = np.arange(len(labels))
    width = 0.8 / len(metrics)

    fig, ax = plt.subplots(figsize=(12, 6))
    for idx, (metric, label) in enumerate(metrics):
        values = [float(row[metric]) for row in rows]
        offset = (idx - (len(metrics) - 1) / 2) * width
        bars = ax.bar(x + offset, values, width, label=label)
        _autolabel_bars(ax, bars)

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def create_figures(core_rows, homography_rows, output_dir):
    _, plt, _, _ = _import_runtime_dependencies()

    _plot_grouped_bars(
        plt,
        core_rows,
        [
            ("avg_detections_per_frame", "Avg detections/frame"),
            ("confirmed_track_count", "Confirmed tracks"),
            ("mean_track_length", "Mean track length"),
            ("fragmentation_per_100_frames", "Fragmentation/100 frames"),
        ],
        "Tracking Quality Ablation",
        output_dir / "fig_tracking_quality.png",
    )

    _plot_grouped_bars(
        plt,
        core_rows,
        [
            ("speed_std_mps", "Speed std (m/s)"),
            ("acc_std_mps2", "Acceleration std (m/s^2)"),
            ("abnormal_acc_ratio", "Abnormal acceleration ratio"),
        ],
        "Motion Stability Ablation",
        output_dir / "fig_motion_stability.png",
    )

    shifts = [row["pixel_shift_px"] for row in homography_rows]
    errors = [row["projection_error_m"] for row in homography_rows]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(shifts, errors, marker="o", linewidth=2)
    for shift, error in zip(shifts, errors):
        ax.annotate(f"{error:.3f} m", (shift, error), textcoords="offset points", xytext=(0, 8), ha="center")
    ax.set_title("Homography Calibration Sensitivity")
    ax.set_xlabel("Calibration point shift (px)")
    ax.set_ylabel("Projection error (m)")
    ax.grid(True, linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "fig_homography_sensitivity.png", dpi=300)
    plt.close(fig)


def write_summary(output_path, core_rows, homography_rows):
    headers = [
        "Experiment",
        "Avg Det/Frame",
        "Tracks",
        "Mean Track Length",
        "Frag/100F",
        "Avg Speed",
        "Speed Std",
        "Acc Std",
        "Clip Ratio",
        "Abnormal Acc Ratio",
    ]
    align = "|".join(["---"] * len(headers))
    lines = [
        "# Ablation Experiment Summary",
        "",
        "## Core Ablation Results",
        "",
        "|" + "|".join(headers) + "|",
        "|" + align + "|",
    ]
    for row in core_rows:
        lines.append(
            "|"
            + "|".join(
                [
                    row["experiment"],
                    f"{row['avg_detections_per_frame']:.2f}",
                    str(row["confirmed_track_count"]),
                    f"{row['mean_track_length']:.2f}",
                    f"{row['fragmentation_per_100_frames']:.2f}",
                    f"{row['avg_speed_mps']:.2f}",
                    f"{row['speed_std_mps']:.2f}",
                    f"{row['acc_std_mps2']:.2f}",
                    f"{row['clipped_speed_ratio']:.3f}",
                    f"{row['abnormal_acc_ratio']:.3f}",
                ]
            )
            + "|"
        )

    lines.extend(
        [
            "",
            "## Homography Sensitivity",
            "",
            "|Pixel Shift (px)|Projection Error (m)|",
            "|---|---|",
        ]
    )
    for row in homography_rows:
        lines.append(f"|{row['pixel_shift_px']}|{row['projection_error_m']:.3f}|")

    lines.extend(
        [
            "",
            "## Generated Figures",
            "",
            "- fig_tracking_quality.png",
            "- fig_motion_stability.png",
            "- fig_homography_sensitivity.png",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run compact quantitative ablation experiments.")
    parser.add_argument("--video", default=str(DEFAULT_VIDEO), help="Input football match video.")
    parser.add_argument("--homography", default=str(DEFAULT_HOMOGRAPHY), help="Homography JSON file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for CSV/JSON/figures.")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional frame limit for quick validation.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    video_path = Path(args.video).expanduser().resolve()
    homography_path = Path(args.homography).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not homography_path.exists():
        raise FileNotFoundError(f"Homography file not found: {homography_path}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"YOLO model file not found: {MODEL_PATH}")

    output_dir.mkdir(parents=True, exist_ok=True)
    homography = _load_homography(homography_path)

    core_rows = []
    for config in CORE_EXPERIMENTS:
        print(f"Running {config.name}...")
        row = run_core_experiment(config, video_path, homography, max_frames=args.max_frames)
        row["config"] = json.dumps(asdict(config), ensure_ascii=False)
        core_rows.append(row)

    homography_rows = run_homography_sensitivity()

    core_fields = [
        "experiment",
        "avg_detections_per_frame",
        "confirmed_track_count",
        "mean_track_length",
        "fragmentation_per_100_frames",
        "avg_speed_mps",
        "speed_std_mps",
        "acc_std_mps2",
        "clipped_speed_ratio",
        "abnormal_acc_ratio",
        "config",
    ]
    homography_fields = ["experiment", "pixel_shift_px", "projection_error_m"]

    _write_csv(output_dir / "ablation_results.csv", core_rows, core_fields)
    _write_csv(output_dir / "homography_sensitivity.csv", homography_rows, homography_fields)

    with (output_dir / "ablation_results.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "core_ablation": core_rows,
                "homography_sensitivity": homography_rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    create_figures(core_rows, homography_rows, output_dir)
    write_summary(output_dir / "ablation_summary.md", core_rows, homography_rows)

    print(f"Done. Results saved to: {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
