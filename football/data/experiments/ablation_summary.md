# Ablation Experiment Summary

## Core Ablation Results

|Experiment|Avg Det/Frame|Tracks|Mean Track Length|Frag/100F|Avg Speed|Speed Std|Acc Std|Clip Ratio|Abnormal Acc Ratio|
|---|---|---|---|---|---|---|---|---|---|
|baseline_full|8.15|23|82.91|0.00|2.23|2.75|1.90|0.041|0.026|
|no_smoothing|8.15|23|82.91|0.00|2.30|2.52|2.58|0.029|0.144|
|no_acc_filter|8.15|23|82.91|0.00|2.23|2.75|7.31|0.041|0.026|
|no_speed_constraint|8.15|23|82.91|0.00|2.67|5.11|2.49|0.041|0.050|
|low_conf_0_25|14.37|30|90.87|0.00|2.20|2.87|1.87|0.054|0.034|
|high_conf_0_60|3.63|9|96.33|0.00|1.80|2.40|1.47|0.022|0.016|
|short_max_age_15|8.15|32|44.41|0.00|1.41|1.76|1.47|0.013|0.015|

## Homography Sensitivity

|Pixel Shift (px)|Projection Error (m)|
|---|---|
|2|0.035|
|5|0.087|
|10|0.175|

## Generated Figures

- fig_tracking_quality.png
- fig_motion_stability.png
- fig_homography_sensitivity.png
