# DAS732 Data Visualization — Assignments (Team Silica, IIIT Bangalore, Term 1 2026-27)

Team: Sidhanth Prabhu (BT2024027) · Shrey Modi (BT2024125) · Parthsarati Samanta (BT2024083)

| Folder | Assignment | Contents |
|---|---|---|
| [`Assignment_1/`](Assignment_1/) | **A1** — Visual exploration of Reddit's top communities (2011–2024) | Python pipeline, 14 figures, Tableau workbook, report |
| [`Assignment_2/`](Assignment_2/) | **A2** — SciVis on gridMET (Jul–Sep 2024) + InfoVis on the A1 Reddit data | S1 colour mapping, S2 Marching Squares contours, S3 quiver/streamlines; I1 network layouts, I2 D3.js parallel coordinates + zoomable treemap, I3 horizon/ridgeline plots; IEEE LaTeX report |

Each folder has its own README with setup and run instructions.

Notes for A2:
- The processed gridMET NetCDF files (>100 MB) and the compiled report PDF are not in git. Regenerate them with
  `REBUILD_RAW=1 bash run_all.sh` inside `Assignment_2/` (see `Assignment_2/README.md`).
