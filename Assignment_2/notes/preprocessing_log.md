# Preprocessing log — DAS732 A2 (Team Silica)

Every data-handling decision is recorded here in order, with the reason for it. This file feeds the
"Data Handling" section of the report.

## Phase 0 — environment and inputs (2026-10-07)
- Python 3.14.6 in a virtual environment outside OneDrive (`~/.venvs/das732_a2`), so the cloud sync never
  touches thousands of package files. Dependencies are pinned in `requirements.txt`.
- A1 dataset copied unchanged into `data/a1/`: 50 per-subreddit CSVs plus `50_subreddits_list.csv`
  (Kaggle: sachinkanchan92/reddit-top-posts-50-subreddit-analysis-2011-2024) and the A1 cleaned file
  `reddit_top_posts_clean.csv` (49,266 posts). A2 re-derives its own cleaning in
  `infovis/common/a1_preprocess.py`. The A1 output is kept only for cross-checking.
- gridMET source verified by listing https://www.northwestknowledge.net/metdata/data/. The pattern
  `<var>_<year>.nc` was confirmed for vs, th, tmmx, pr, vpd, rmax, srad (2024). Sizes are 28–205 MB per
  file (~820 MB total), so a direct HTTP download is enough and server-side subsetting is not needed.

## Phase 1 — gridMET download, subsetting, cleaning (2026-10-07)

### P1.1 Download
- `scivis/common/download_gridmet.py` fetches `<var>_2024.nc` for vs, th, tmmx, pr, vpd, rmax, srad. It shows a
  tqdm progress bar and resumes from a `.part` file with an HTTP `Range` header. The rmax download was interrupted
  once and resumed correctly; each final size equals the server `Content-Length`.
- Raw files went to `GRIDMET_RAW_DIR` (`~/das732_gridmet_raw`, outside the OneDrive-synced repo). The default is
  `data/raw/gridmet/` (gitignored). After subsetting, the raw files can be deleted.

### P1.2 Raw schema (full dump in `notes/raw_schema_dump.txt`)
| file | data variable (CF name) | stored dtype | scale_factor | add_offset | _FillValue | units |
|---|---|---|---|---|---|---|
| tmmx | air_temperature | uint16 | 0.1 | 220.0 | 32767 | K |
| pr | precipitation_amount | uint16 | 0.1 | 0 | 32767 | mm |
| vs | wind_speed | uint16 | 0.1 | 0 | 32767 | m/s |
| th | wind_from_direction | uint16 | 1.0 | 0 | 32767 | degrees clockwise from north |
| vpd | mean_vapor_pressure_deficit | uint16 | 0.01 | 0 | 32767 | kPa |
| rmax | relative_humidity | uint16 | 0.1 | 0 | 32767 | % |
| srad | surface_downwelling_shortwave_flux_in_air | uint16 | 0.1 | 0 | 32767 | W m-2 |
- Dims are `(day, lat, lon)` = (366, 585, 1386), on a regular 1/24° (≈4 km) WGS84 grid covering 25.07–49.40 °N and
  124.77–67.06 °W. `day` is "days since 1900-01-01". **Latitude is stored descending** (49.40 → 25.07).
- Global attribute note5: a gridMET "day" ends at midnight MST, i.e. 07 UTC of the next calendar day. This matters
  for hurricane timing (Helene's landfall at ~03 UTC 27 Sep falls inside gridMET day 26 Sep).
- Files are dated 03 Mar 2025 and carry no `last_permanent_slice` attribute, so the 2024 data are treated as final.

### P1.3 Processing (`scivis/common/load_gridmet.py`)
1. Lazy open with dask chunks equal to the on-disk chunking (61, 98, 231). Variables are processed one at a time
   to keep memory low.
2. Temporal subset 2024-07-01 … 2024-09-30 → 92 days. `day` renamed to `time`.
3. **Latitude sorted ascending** for all processed files, so every task uses one orientation
   (`origin="lower"`, `streamplot` needs increasing y, Marching Squares row 0 = south).
4. CF decoding applies scale/offset and turns the fill value 32767 into NaN. The land mask has 483,879 valid cells
   out of 810,810 (59.7 %). The mask is **identical across all 7 variables and constant across all 92 days**,
   checked cell by cell. NaN cells (ocean, Canada, Mexico) are left as NaN; nothing is interpolated.
5. Units: tmmx K → °C (−273.15). pr stays in mm/day, vs in m/s, vpd in kPa, rmax in %, srad in W m⁻². Stored as
   float32 NetCDF with zlib level 4 in `data/processed/gridmet_<var>_2024JAS.nc`.
6. **Wind decomposition.** th is the meteorological direction the wind comes FROM, clockwise from north. The
   components pointing where the wind blows TO are u = −vs·sin(th), v = −vs·cos(th). The sanity check gives
   th=270° (westerly) → u=+10, v=0; th=0° (northerly) → v=−10; th=90° → u=−10; th=180° → v=+10. Saved in
   `gridmet_wind_2024JAS.nc` (u, v). th has values 0 (63,867 cells) and 360 (42,580 cells), which are equivalent
   and decompose identically. Only 39 cell-days have vs < 0.5 m/s, so there is no calm-wind direction problem.
7. Extremes are physically plausible, so none were clipped:
   - tmmx max 53.85 °C on 6 Jul at 36.48 N, 116.89 W (Death Valley, during the record July heat wave).
   - tmmx min −6.35 °C on 23 Aug at 41.40 N, 122.18 W (summit of Mt Shasta, ~4300 m). This shows that the 4 km grid
     resolves high-elevation cold spots.
   - pr max 401.4 mm on 4 Aug at 27.40 N, 82.39 W (Sarasota–Manatee, Hurricane Debby's rain band).
   - vs max 16.1 m/s, reached on 18 Sep (Wyoming, 42.69 N, 106.06 W) and again on 26 Sep in the Debby/Helene box.
     These are daily means, so hurricane gusts are heavily smoothed.

### P1.4 Statistics
- `data/processed/stats_per_day.csv`: for each variable × day, n_valid, min, max, mean, std and p1/p5/p25/p50/p75/p95/p99.
- `data/processed/stats_global.csv`: the same over all 92 days. Global ranges:
  tmmx −6.35…53.85 °C (mean 29.17); pr 0…401.4 mm (mean 2.30); vs 0.3…16.1 m/s (mean 3.46);
  vpd 0…10.11 kPa (mean 1.47); rmax 6.4…100 % (mean 81.0); srad 36.8…451.9 W m⁻² (mean 254.9).

### P1.5 Date selection (`scivis/common/stats_and_dates.py`, `images/Fig_01_date_selection_timeline.png`)
- Daily indicators (`daily_evidence.csv`): CONUS max tmmx; share of western-US land (31–49.4 N, 124.8–104 W) with
  tmmx ≥ 40 °C; area-mean pr and max vs in four landfall boxes (TX coast 27–32 N 97.8–93.5 W; FL–GA–SC 26–34 N
  84–78.5 W; Louisiana 28.8–33 N 93.8–88.5 W; Southeast 29–37 N 86–80 W); CONUS max and p99 of vs.
- Rule (hybrid): **6 event anchors verified in the data** plus **2 fillers** that split the 37-day event-free gap
  (5 Aug → 11 Sep) into thirds. Consecutive dates are 12–16 days apart, apart from the deliberate Helene
  landfall/inland pair.
  | id | date | role | evidence |
  |---|---|---|---|
  | D1 | 08 Jul | Beryl landfall (TX) + western heat | TX box mean pr 40.0 mm (seasonal max), TX max vs 12.0 m/s; western area ≥40 °C 10.5 % |
  | D2 | 24 Jul | Western heat-wave peak | western area ≥40 °C 13.6 % (seasonal max) |
  | D3 | 05 Aug | Debby landfall (FL) | FL–GA–SC box mean pr 60.1 mm, max vs 12.0 m/s |
  | D4 | 17 Aug | gap filler | quiet day, regional pr ≤ 6 mm |
  | D5 | 29 Aug | gap filler | quiet day; some Gulf-coast convection (LA 14 mm) |
  | D6 | 11 Sep | Francine landfall (LA) | LA box mean pr 54.4 mm (seasonal max), max vs 9.8 m/s |
  | D7 | 26 Sep | Helene landfall (FL Big Bend) | SE box mean pr 93.5 mm (seasonal max), FL box max vs 16.1 m/s (= CONUS max) |
  | D8 | 27 Sep | Helene inland (GA/Carolinas) | SE box max vs 14.6 m/s (seasonal max), pr 11.7 mm |
- The same 8 dates are used in S1, S2 and S3 (`scivis/common/plot_utils.py: DATES`).
- The western heat wave was strongest 5–12 Jul (Death Valley peak on 6 Jul). D1 = 8 Jul captures it together with
  Beryl, so a separate 6 Jul date is not needed.

## Phase 2 — A1 dataset (Reddit top posts) cleaning and derivations (`infovis/common/a1_preprocess.py`)

Input: 50 per-subreddit Kaggle CSVs (`data/a1/*.csv`; ~1000 all-time top posts per subreddit, 19 columns).
The script's own log, regenerated on each run, is in `data/processed/a1/a1_preprocess_log.md`. Its key lines:

    - Raw merge: 49266 rows x 20 cols from 50 subreddit files.
    - Duplicate post ids: 0.
    - Timestamps: 48279 ISO + 987 M/D/YYYY H:MM parsed; range 2011-09-27 04:17:32 .. 2024-09-11 07:13:13 UTC.
    - Dropped columns: num_awards (all 49266 zero), crosspost_subreddits (99.35% missing), is_bot (8.53% missing), is_megathread (21 True), body (82.79% missing).
    - Rows kept: 49266 (no rows dropped; the corpus is the top tail by construction, so extremes are kept).
    - Posts per year: {2011: 1, 2012: 2, 2013: 5, 2014: 168, 2015: 602, 2016: 1747, 2017: 6266, 2018: 8096, 2019: 8465, 2020: 11493, 2021: 6279, 2022: 3930, 2023: 1589, 2024: 623}
    - Topic categories: {'Q&A and advice': 8, 'Text humour and stories': 4, 'News, science and tech': 8, 'Memes and GIFs': 4, 'Photos and curiosities': 7, 'Creative and lifestyle': 5, 'Entertainment and media': 10, 'Knowledge and curiosity': 4}
    - domain_class counts: {'reddit-hosted media': 14990, 'self post': 13135, 'external website': 13100, 'imgur': 4111, 'youtube': 3040, 'other video host': 890}
    - Network: posts linking to external domains = 21141 of 49266; distinct external domains = 3352; kept domains with >= 3 posts = 642.
      Nodes = 685 (43 subreddits + 642 domains); edges = 2389; total edge weight = 18002 posts.
      Subreddits with no qualifying external link (absent from graph): ['AskReddit', 'LifeProTips', 'NoStupidQuestions', 'Showerthoughts', 'explainlikeimfive', 'personalfinance', 'relationship_advice']
    - Treemap hierarchy h1_topic: category -> subreddit -> post_type; leaves = 135.
    - Treemap hierarchy h2_media: post_type -> domain_class -> category -> subreddit; leaves = 249.
    - Treemap hierarchy h3_time: era -> year -> category -> subreddit; leaves = 486.
    - Parallel coordinates: stratified sample 40/subreddit (seed 42) = 2000 posts; axes = ['dec_year', 'hour_utc', 'title_len', 'upvote_ratio', 'score', 'num_comments', 'num_crossposts']; log10 transform for score, log10(x+1) for comments and crossposts.
      k-means silhouette by k: {3: 0.241, 4: 0.248, 5: 0.229, 6: 0.221, 7: 0.226, 8: 0.194} -> k = 4.
      cluster sizes: [552, 675, 553, 220]
    - Time series window 2016-01..2024-08 (104 months, 48442 posts = 98.3% of corpus); months with zero posts in a category are true zeros.

Decisions and rationale:
- **Cleaning** (same rules as A1, re-implemented): two timestamp formats, no duplicate ids, five uninformative or
  near-empty columns dropped, **no rows dropped**. Outliers are kept because the corpus is the top tail by
  construction, so log scales are used instead.
- **Domain normalisation**: lower-case; strip `www.`/`m.`/`old.`/`mobile.` prefixes; merge aliases of one platform
  (youtu.be→youtube.com, i.imgur.com→imgur.com, i./v./preview.redd.it and reddit.com→redd.it, x.com→twitter.com).
  This avoids splitting one platform into several nodes.
- **Topic categories**: the 50 subreddits are grouped by hand into 8 topics by community purpose (table in the
  script: `CATEGORIES`). Used as the grouping/colour variable in I1, I2 and I3.
- **(1) Network = bipartite subreddit ↔ external domain.** An edge (s, d) exists if subreddit s has at least one
  top post linking to domain d. Edge weight = number of such posts. Self-posts and Reddit's own media host (redd.it)
  are excluded because they say nothing about what a community links out to. Domains with fewer than 3 top posts are
  dropped (3,352 → 642 domains) to remove one-off links. The result is 685 nodes / 2,389 edges. Seven text-only
  communities (AskReddit, LifeProTips, NoStupidQuestions, Showerthoughts, explainlikeimfive, personalfinance,
  relationship_advice) have no qualifying external link and so are not in the graph. That absence is itself a
  finding. The more obvious crosspost graph was rejected: `crosspost_subreddits` is 99.35 % missing (322 posts).
- **(2) Treemap hierarchies (three remodels of one table)**:
  H1 topic → subreddit → post type (135 leaves); H2 post type → hosting class → topic → subreddit (249 leaves);
  H3 era → year → topic → subreddit (486 leaves). Each leaf stores three measures (post count, total score,
  total comments), so the size encoding can also be switched.
- **(3) Parallel coordinates**: a stratified random sample of 40 posts per subreddit (seed 42) gives 2,000 posts,
  which is enough to show structure while keeping SVG brushing interactive. Axes: decimal year, posting hour (UTC),
  title length (chars), upvote ratio, score (log), comments (log, +1), crossposts (log, +1). Groups: topic (8),
  post type (4) and k-means cluster. k-means runs on min–max normalised (log-transformed where applicable) axes.
  k = 4 was chosen by the best silhouette over k = 3..8 (0.248; the low value means the clusters are soft, which is
  expected for this data). The clusters provide the bundling centroids in I2a.
- **(4) Time series**: monthly post counts and monthly median log10(score) per topic and per subreddit,
  Jan 2016 – Aug 2024 (104 months, 98.3 % of posts). Before 2016 there are under 50 posts per month in total, and
  Sep 2024 is a partial month (data end 11 Sep). Quarterly and yearly counts per topic are kept for the
  granularity comparison. The per-post log10(score) distributions for the ridgelines come from `posts_clean.csv`.

## Phases 3-8 — task-level data transformations (2026-10-07)
- **S1**: anomaly = daily Tmax minus each cell's Jul-Sep 2024 mean. Precipitation zeros (71.3 % of cell-days) are shown as
  a separate "dry" category instead of an epsilon, because LogNorm needs x > 0. Global normalisation uses the 92-day
  min/max (-6.35 / 53.85 degC; pr 0.1 / 401.4 mm). Maps use a Lambert Conformal projection (33/45 N) with a fixed
  projected extent derived from the land mask.
- **S2**: VPD was chosen over rmax (21.3 % of cells saturate at 100 %) and srad (narrow range); see
  s2_variable_choice.csv. Validation isovalues are offset by half the 0.01 kPa storage step so no data value equals the
  isovalue. Smoothing is mask-aware: G(f*m)/G(m). Filled contours are computed on projected coordinates, because
  re-projecting PlateCarree contourf polygons inverted some of them.
- **S3**: vectors are subsampled by k x k NaN-aware block means (blocks with < 50 % land dropped); plain striding is kept
  only as the aliasing comparison. Streamlines are integrated on a 360 x 224 regular grid in projected metres (u, v
  rotated by cartopy.vector_transform). Points outside the land mask are masked. The field is coarsened 3 x 3 for the
  CONUS view. Matplotlib streamline arrowheads were mis-oriented on GeoAxes, so they are redrawn as quiver heads in map
  coordinates (segment direction verified: 0/74 reversed).
- **I1**: domains reduced to registrable domain (eTLD+1); Reddit's own media hosts (redd.it, reddituploads.com,
  redditmedia.com) merged and excluded from the network. Kamada-Kawai uses distance 1/weight. Layout positions are
  cached in data/processed/i1_layout_cache.json (KK takes about 9 min); runtimes are those of the computing run. The
  spectral layout uses the normalised Laplacian, because the unnormalised one collapses (kept in the metrics table).
- **I2**: parcoords sample = 40 posts/subreddit (seed 42). Comments and crossposts use a symlog scale because of zeros.
  Treemap leaf measures are additive sums (posts, score, comments).
- **I3**: horizon band height is shared within a figure. The subreddit horizon uses a fixed h = 0.15 dex with
  saturation beyond 0.45 dex. Months without a top post are left blank for medians and counted as 0 for counts. Ridgeline
  KDE bandwidth is fixed (0.06 dex for score, 0.08 for log comments) for every group.
