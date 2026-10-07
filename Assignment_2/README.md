# DAS732 Data Visualization — Assignment 2 (Team Silica)

IIIT Bangalore, Term 1 2026-27. SciVis on **gridMET, 1 Jul – 30 Sep 2024** and InfoVis on the **A1 dataset
(Reddit all-time top posts of 50 subreddits, 2011–2024)**.

| Member | Roll no. | SciVis task | InfoVis task |
|---|---|---|---|
| Sidhanth Prabhu | BT2024027 | **S1** Colour mapping (+ GIFs) | **I1** Node-link diagram, 5 layouts (NetworkX + Gephi export) |
| Shrey Modi | BT2024125 | **S2** Contour mapping: own Marching Squares + filled contours (+ GIF) | **I3** Horizon and ridgeline plots (Python) |
| Parthsarati Samanta | BT2024083 | **S3** Quiver plots and streamlines (+ GIF) | **I2** Parallel coordinates with edge bundling + zoomable treemap (D3.js) |
| All (shared) | — | gridMET download, subsetting, cleaning, statistics, date selection | A1 cleaning and derived datasets |

The owner's name is in the header of every task script. The report is at `report/DAS732_A2_Report.pdf` (IEEE
two-column). Every figure in it is in `images/` at 300 dpi (screenshots at 2× device scale), named by figure number.

---

## 1. Setup

Requires Python ≥ 3.10 (developed on 3.14.6, Windows 11).

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows   (source .venv/bin/activate on Linux / macOS)
python -m pip install -r requirements.txt
python -m playwright install chromium   # only for the I1/I2 screenshots
python env_check.py                     # prints versions of all required packages
```

To compile the report you need a TeX distribution with `latexmk` and `IEEEtran` (MiKTeX or TeX Live).
On Windows set `PYTHONUTF8=1` if the console is not UTF-8.

## 2. Data

### 2.1 gridMET (SciVis)
Source: https://www.climatologylab.org/gridmet.html → *Download* → *Direct download of NetCDF files*. The files are
in https://www.northwestknowledge.net/metdata/data/ and named `<var>_<year>.nc`.

```bash
# downloads vs, th, tmmx, pr, vpd, rmax, srad for 2024 (~820 MB) with a progress bar and resume support
python scivis/common/download_gridmet.py            # -> data/raw/gridmet/  (override with GRIDMET_RAW_DIR=...)
python scivis/common/inspect_raw.py                 # prints names, dims, units, fill values, scale factors
python scivis/common/load_gridmet.py                # subset Jul-Sep 2024, mask, convert units, u/v -> data/processed/
python scivis/common/stats_and_dates.py             # stats CSVs, daily event evidence, 8 dates, Fig. 1
```
After `load_gridmet.py` the raw annual files can be deleted. Every later script reads only `data/processed/`.

### 2.2 A1 dataset (InfoVis)
`data/a1/` holds the 50 per-subreddit CSVs and `50_subreddits_list.csv` from Kaggle
(`sachinkanchan92/reddit-top-posts-50-subreddit-analysis-2011-2024`), unchanged from A1. It also holds the A1
cleaned file, which is kept only for cross-checking.

```bash
python infovis/common/a1_preprocess.py   # cleaning + network / hierarchies / multivariate / time-series derivations
```
Every preprocessing decision is logged in `notes/preprocessing_log.md`.

## 3. Running each task (one command each; outputs go to `images/` and `data/processed/`)

| Task | Command | Approx. runtime |
|---|---|---|
| S1 colour mapping | `python scivis/s1_colormapping/run.py` | 4 min |
| S2 contours | `python scivis/s2_contours/run.py` | 6 min |
| S3 quiver / streamlines | `python scivis/s3_quiver_streamlines/run.py` | 6 min |
| I1 network | `python infovis/i1_network/run.py` (`--recompute` re-times all layouts; Kamada–Kawai alone ≈ 9 min) | 1 min (cached layouts) |
| I2 screenshots | `python infovis/i2_web/screenshots.py` (starts its own local server) | 1 min |
| I3 horizon / ridgeline | `python infovis/i3_horizon_ridgeline/run.py` | 30 s |
| Report | `cd report && python build_report_assets.py && latexmk -pdf main.tex` | 1 min |
| **Everything** | `bash run_all.sh` (`REBUILD_RAW=1` also re-downloads and re-subsets gridMET) | ≈ 20 min |

## 4. Serving the JavaScript visualizations (I2)

```bash
cd infovis/i2_web
python -m http.server 8000
# open http://localhost:8000/   -> links to parcoords/ and treemap/
```
D3 v7.9.0 is vendored in `infovis/i2_web/lib/`, so no internet connection or build step is needed.
- **Parallel coordinates** (`parcoords/`):
  - Brush any axis; brushes on several axes combine (AND).
  - Drag an axis title to reorder the axes.
  - The *bundling strength β* slider controls edge bundling (0 = plain polylines, 1 = fully bundled).
  - Colour and bundle by k-means cluster, topic or post type.
  - Optional group-centroid lines, hover tooltips, a Reset button and a live selected-record count.
- **Zoomable treemap** (`treemap/`):
  - Click to zoom in; use the breadcrumb or the header bar to zoom out.
  - Dropdowns switch the hierarchy (3 remodels), size measure (posts / score / comments), tiling (squarify, binary,
    slice, dice, slice-dice) and sort order.
  - Tooltips show value and share. A live line reports aspect ratio and order preservation for the current view.

The I1 interactive network is `infovis/i1_network/interactive/network.html`. Open it directly in a browser; it loads
vis-network from a CDN.

## 5. Gephi reproduction (I1)

The graph is exported to `infovis/i1_network/gexf/reddit_domain_network.gexf` (671 nodes, 2,350 edges) and
`..._filtered.gexf` (269 nodes, 1,003 edges). Node attributes: `type`, `category`, `domain_class`, `posts`,
`degree`, `strength`, `community` (Louvain). Edge attribute: `weight`.

1. Gephi 0.10+ → *File → Open* → the `.gexf` → *Graph type: Undirected* → *Append to new workspace*.
2. *Appearance → Nodes → Color → Partition → community* (or `type`) → Apply.
   *Size → Ranking → strength* (min 5, max 60) → Apply.
3. *Statistics*: run *Average Degree*, *Modularity* (resolution 1.0, use weights) and *Graph Density*. Compare
   modularity with ours (Q = 0.611, 6 communities).
4. **ForceAtlas2** (*Layout* panel): Scaling 2.0, Gravity 1.0, *Dissuade Hubs* on, *LinLog mode* off,
   *Prevent Overlap* on in a second pass. Run until stable (~1–2 min), then stop.
5. **Fruchterman Reingold**: Area 10000, Gravity 10, Speed 1. Run ~2 min.
6. **Yifan Hu**: Optimal distance 100, Relative strength 0.2, Initial step 20. Run until it converges.
7. For each layout: *Preview* → preset *Default Curved* off → *Show Labels* on, font 10, *proportional size*, edge
   opacity 30 → *Refresh* → *Export → PNG*, width 4000 px.
8. Save the three exports as `images/Fig_43_gephi_forceatlas2.png`, `images/Fig_44_gephi_fruchterman_reingold.png`
   and `images/Fig_45_gephi_yifanhu.png`, then recompile the report. Figures 43–45 in the appendix pick them up
   automatically; until then they show a placeholder box.

## 6. Folder map

```
DAS732_A2_Silica/
├── README.md, requirements.txt, env_check.py
├── data/
│   ├── raw/gridmet/            raw annual NetCDF (gitignored, deletable)
│   ├── processed/              gridmet_<var>_2024JAS.nc, wind u/v, stats_*.csv, daily_evidence.csv,
│   │                           selected_dates.csv, s1_*/s2_*/s3_*/i1_*/i2_*/i3_* metric tables
│   │   └── a1/                 posts_clean.csv, network/{nodes,edges}.csv, ts_*.csv, parcoords_*.csv
│   └── a1/                     A1 Kaggle CSVs (input)
├── scivis/
│   ├── common/                 download_gridmet.py, inspect_raw.py, load_gridmet.py, stats_and_dates.py,
│   │                           plot_utils.py (8 dates), maps.py (Cartopy helpers)
│   ├── s1_colormapping/run.py
│   ├── s2_contours/marching_squares.py, run.py
│   └── s3_quiver_streamlines/run.py
├── infovis/
│   ├── common/a1_preprocess.py
│   ├── i1_network/run.py, gexf/, interactive/network.html
│   ├── i2_web/index.html, style.css, lib/d3.v7.min.js, parcoords/, treemap/, data/*.json, screenshots.py
│   └── i3_horizon_ridgeline/run.py
├── images/                     Fig_01 … Fig_42 (+ GIFs for Fig_07, 08, 09, 17, 24)
├── notes/                      preprocessing_log.md, raw_schema_dump.txt, figure_observations.md
└── report/                     main.tex, sections/*.tex, references.bib, build_report_assets.py, DAS732_A2_Report.pdf
```

## 7. Figure index

| Fig. | File | Task | Content |
|---|---|---|---|
| 1 | Fig_01_date_selection_timeline.png | shared | daily evidence for the 8 dates |
| 2 | Fig_02_tmmx_continuous_colormaps.png | S1 | jet vs viridis / inferno / cividis |
| 3 | Fig_03_colormap_lightness_profiles.png | S1 | CIELAB L* of each colormap |
| 4 | Fig_04_tmmx_discrete_equal_vs_quantile.png | S1 | continuous vs 5 °C classes vs deciles |
| 5 | Fig_05_pr_linear_vs_log.png | S1 | precipitation, linear vs clipped vs LogNorm |
| 6 | Fig_06_tmmx_anomaly_diverging.png | S1 | diverging vs sequential anomaly maps |
| 7 | Fig_07_tmmx_global_norm.png / .gif | S1 | 8 dates, global normalisation |
| 8 | Fig_08_tmmx_local_norm.png / .gif | S1 | 8 dates, local normalisation |
| 9 | Fig_09_pr_global_log.png / .gif | S1 | 8 dates of precipitation, global log scale |
| 10 | Fig_10_s2_variable_candidates.png | S2 | VPD vs rmax vs srad for contouring |
| 11 | Fig_11_marching_squares_cases.png | S2 | 16-case lookup table |
| 12 | Fig_12_ms_validation.png | S2 | own MS vs skimage; saddle deciders |
| 13 | Fig_13_isolines_vs_filled.png | S2 | isolines vs filled bands |
| 14 | Fig_14_contour_levels.png | S2 | uniform vs quantile vs domain levels |
| 15 | Fig_15_contour_smoothing.png | S2 | Gaussian pre-smoothing |
| 16 | Fig_16_contour_overlay.png | S2 | isolines over colour maps |
| 17 | Fig_17_vpd_contour_evolution.png / .gif | S2 | 8 dates, fixed levels |
| 18 | Fig_18_quiver_stride.png | S3 | striding k = 10 / 20 / 40 |
| 19 | Fig_19_quiver_stride_vs_block.png | S3 | striding vs block averaging, aliasing |
| 20 | Fig_20_quiver_proportional_vs_uniform.png | S3 | proportional vs uniform arrows |
| 21 | Fig_21_hurricane_zooms.png | S3 | Beryl, Debby, Francine, Helene zooms |
| 22 | Fig_22_streamlines_vs_quiver.png | S3 | quiver vs streamlines |
| 23 | Fig_23_streamline_seeding.png | S3 | uniform / random / feature seeding |
| 24 | Fig_24_wind_evolution.png / .gif | S3 | 8 dates, speed + vectors |
| 25 | Fig_25_network_statistics.png | I1 | degree, weights, communities |
| 26 | Fig_26_network_layouts.png | I1 | 5 layouts, same encoding |
| 27 | Fig_27_network_layout_metrics.png | I1 | runtime, crossings, edge length, separation |
| 28 | Fig_28_network_filtering.png | I1 | before / after filtering |
| 29 | Fig_29_subreddit_projection.png | I1 | subreddit similarity projection |
| 30 | Fig_30_network_interactive.png | I1 | PyVis interactive page |
| 31a–c | Fig_31*_parcoords_*.png | I2a | unbundled vs bundled |
| 32a–c | Fig_32*_parcoords_*.png | I2a | brushing and axis reordering |
| 33a–f | Fig_33*_treemap_*.png | I2b | 3 hierarchies, 3 zoom states |
| 34a–e | Fig_34*_treemap_tiling_*.png | I2b | 5 tiling strategies |
| 35 | Fig_35_horizon_construction.png | I3 | horizon construction, band count |
| 36 | Fig_36_horizon_topics_monthly.png | I3 | monthly horizon, 8 topics |
| 37 | Fig_37_line_vs_horizon.png | I3 | line chart vs small multiples vs horizon |
| 38 | Fig_38_horizon_topics_quarter_year.png | I3 | quarterly vs yearly granularity |
| 39 | Fig_39_horizon_subreddits_monthly.png | I3 | 50 subreddits, score anomaly |
| 40 | Fig_40_ridgeline_subreddits_score.png | I3 | log score by subreddit |
| 41 | Fig_41_ridgeline_years_score.png | I3 | log score by year |
| 42 | Fig_42_ridgeline_topics_comments.png | I3 | log comments by topic |
| 43–45 | Fig_43–45_gephi_*.png | I1 | **to be added** (Gephi screenshots, Sec. 5) |
