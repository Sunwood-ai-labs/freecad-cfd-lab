# 実験ガイド / Experiment guide

各実験は別の形状・計算です。公式エルボ管の画面を平屋の計算結果として扱わないでください。
The four experiments use different geometries and cases; the tool screenshots
from the Elbow demonstration are not evidence of the house simulation.

## 1. Elbow: OSS integration demonstration

`experiments/elbow/` contains the official CfdOF Elbow-derived model, macro,
compatibility patch, screenshots and result checks. Recorded final data:
10,823 cells, iteration 242; point-interpolated speed range 0–4.367 m/s.
Pressure images convert OpenFOAM kinematic pressure to Pa using density 1.2 kg/m³.
This verifies integration, not physical accuracy. See `result-summary.json`,
`verification.json` and [third-party notices](../THIRD_PARTY_NOTICES.md).

## 2. Window layout comparison / 窓配置2案

`experiments/window-comparison/` is a simplified 8×6 m house seen from above.
Both cases use 2 m/s left-to-right external wind and steady RANS kEpsilon.
The constant 1 m extrusion makes volume weighting equivalent to area weighting.

| Layout | Cells | Final iteration | Mean indoor speed | Fraction below 0.1 m/s |
| --- | --- | --- | --- | --- |
| A: opposite windows / 向かい合う窓 | 13,712 | 1,429 | 0.566 m/s | 5.71% |
| B: adjacent walls / 隣り合う壁 | 13,711 | 2,026 | 0.517 m/s | 2.22% |

A has higher mean speed; B has a smaller low-speed fraction under these conditions.
This does not establish a generally superior window layout. Values are from
`animation-summary.json`. The 12-second animation follows the calculated steady
flow at a common physical integration-time scale, not equalized path durations.

## 3. Family-house design / 4人家族の平屋

`experiments/family-house/` contains an editable FreeCAD BIM model and JSON design
for a fictional single-storey 3LDK, with furniture, circulation, storage and
window/door schedules. Reference wall-centre area: 105.91 m² (about 32 tsubo).
The design PDF has seven pages. Site, structure, energy performance and statutory
compliance were not established.

`はじめに.txt` is a historical note written before the subsequent CFD experiment;
its statement that this house had not yet undergone CFD refers to that earlier
point in time. The following experiment is the later analysis of this design.

## 4. Family-house 3D airflow / 平屋の3D風通し

`experiments/family-house-airflow/` uses the derived CFD model, not the original
BIM as a solver-ready fluid volume. South-to-north wind is 2 m/s. Seven sliding
windows are half-open; two high windows have idealized plates tilted outward
45°. Interior door leaves are omitted as a fully-open doorway approximation;
the entrance stays closed. Walls, ceiling, floor and major furniture remain
part of the calculation geometry.

| Check | Saved final value / evidence |
| --- | --- |
| Final mesh | 538,479 cells; Mesh OK; connected fluid domain |
| Solver | Steady RANS kEpsilon; iteration 697; residual threshold 1e-5 |
| Geometry probes | 69/69 pass (`mesh-geometry-audit.json`) |
| Maximum room-volume discrepancy | 0.3477%; geometric check, not mesh independence |
| Relative external flux imbalance | 3.7731e-10 (`independent-flux-audit.json`) |
| Maximum room flux imbalance | 1.5084e-6 (same file) |
| Main-room mean-speed change, 585→697 | Maximum 0.1841% (`stability-585-697.json`) |
| Final velocity-field SHA256 | `ffef09c52a6992f0e2d767942e14c99c1aa60471b26575b3dc8d23337beedc25` |

Room values are in `room-metrics.json`. The final velocity hash matches the actual
`case/697/U` and the animation's recorded input. Earlier 400/500/585 fields and
parallel processor copies are excluded from the downloadable final-data archive;
the historical stability comparison JSON remains available.

The 20-second video contains a top view, an oblique 3D view, then a top view.
Roof/ceiling clipping is visual only. Particles follow 3D streamlines through the
final steady field, at twice the physical integration time. Particle counts are
not air volumes, and these are not transient opening-window dynamics.

## What remains unverified / 未検証

- Mesh independence, domain-size dependence and agreement with measurements.
- Different wind directions, window/door configurations and surrounding buildings.
- Buoyancy, mechanical ventilation, plants, terrain, screens and curtains.
- Fresh-air replacement, age of air, air changes per hour and comfort compliance.
- Fresh execution of the public adapted scripts and clean container build.
- Regenerating and solving the final case entirely through the CfdOF GUI.

Original JSON retains historical paths as provenance. These paths are not
instructions to access the original computer. Packaged sources use the public
layout; see [reproduction](reproduction.md) for the supported entry points and
their verification status.
