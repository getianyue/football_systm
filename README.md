# football_systm

Code for football player tracking and speed estimation.

## Project overview

This project uses YOLOv8 and DeepSORT to detect and track football players in
match video, maps image coordinates to pitch coordinates with a homography
matrix, and estimates player speed and acceleration.

## Ablation experiments

A compact quantitative ablation workflow is included in
`football/experiments/run_ablation.py`. It runs the existing demo video through
several model and post-processing variants, then writes CSV, JSON, Markdown, and
PNG outputs for reporting.

### Environment

Create a separate conda environment and install the project dependencies:

```powershell
conda create -n football_ablation python=3.10 -y
conda run -n football_ablation python -m pip install -r football\requirements.txt
```

### Run

Run the full ablation experiment:

```powershell
conda run -n football_ablation python football\experiments\run_ablation.py
```

For a quick smoke test, limit the processed frames:

```powershell
conda run -n football_ablation python football\experiments\run_ablation.py --max-frames 30
```

### Outputs

Generated files are written to `football/data/experiments/`:

- `ablation_results.csv`
- `ablation_results.json`
- `ablation_summary.md`
- `fig_tracking_quality.png`
- `fig_motion_stability.png`
- `fig_homography_sensitivity.png`
- `homography_sensitivity.csv`

The current full-video run produced these headline values:

| Experiment | Avg Det/Frame | Tracks | Mean Track Length | Avg Speed (m/s) | Speed Std (m/s) | Acc Std (m/s^2) |
|---|---:|---:|---:|---:|---:|---:|
| baseline_full | 8.15 | 23 | 82.91 | 2.23 | 2.75 | 1.90 |
| no_smoothing | 8.15 | 23 | 82.91 | 2.30 | 2.52 | 2.58 |
| no_acc_filter | 8.15 | 23 | 82.91 | 2.23 | 2.75 | 7.31 |
| no_speed_constraint | 8.15 | 23 | 82.91 | 2.67 | 5.11 | 2.49 |
| low_conf_0_25 | 14.37 | 30 | 90.87 | 2.20 | 2.87 | 1.87 |
| high_conf_0_60 | 3.63 | 9 | 96.33 | 1.80 | 2.40 | 1.47 |
| short_max_age_15 | 8.15 | 32 | 44.41 | 1.41 | 1.76 | 1.47 |

Homography calibration sensitivity:

| Pixel Shift (px) | Projection Error (m) |
|---:|---:|
| 2 | 0.035 |
| 5 | 0.087 |
| 10 | 0.175 |
