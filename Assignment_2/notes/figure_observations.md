# Figure observations (written after viewing each PNG; feeds the report inferences)

## Fig 1 — date-selection timeline
- (a) The CONUS hottest cell exceeds 52 °C from 4 to 12 Jul (peak 53.85 °C on 6 Jul, Death Valley). It falls below 42 °C
  on 12–22 Sep, an early-autumn cool spell in the desert Southwest (CONUS max only 38.2 °C on 16 Sep).
- The western area with Tmax ≥ 40 °C has two peaks: ~12–13 % on 5–11 Jul and 13.6 % on 24 Jul (D2). It is near 0 %
  from 12 to 22 Sep.
- (b) Each landfall box has one dominant rain spike that matches the event: TX 40 mm (8 Jul, Beryl); FL–GA–SC 60 mm
  (5 Aug, Debby); LA 54 mm (11 Sep, Francine); SE 93.5 mm (26 Sep, Helene). These are the largest area-mean values of
  the season. Secondary LA spike of 35.6 mm on 5 Sep (Gulf disturbance, not a named landfall, % TODO verify).
- (c) Box-maximum daily-mean wind tracks the same events: TX 12 m/s (Beryl), FL 13 m/s (Debby, 4 Aug), LA 9.8 m/s
  (Francine), FL 16.1 m/s and SE 14.6 m/s (Helene, 26/27 Sep). Helene is the only event whose daily-mean wind
  exceeds 14 m/s.
- (d) The CONUS-max wind of 16.1 m/s on 18 Sep is a non-tropical (Wyoming) wind event. Daily means smooth hurricane
  winds, so mountain/plains wind events compete with hurricanes in the daily maximum. The 99th percentile only
  reaches ~10 m/s on Helene's 26/27 Sep.

## Fig 2 — continuous colormaps, D2 (24 Jul), linear 5.1–51.0 °C
- Same data in all panels. jet draws a sharp cyan→yellow "front" around 28–30 °C that cuts across the Midwest and a
  second sharp yellow→orange edge at ~38 °C in the Plains. Neither is a physical discontinuity; they are hue
  boundaries at the bright (high-L*) band of jet.
- In jet the hottest region (CA Central Valley, lower Colorado River / AZ, Death Valley ~45–51 °C) is dark red,
  darker than the ~40 °C Montana area. Lightness falls at the top of jet, so the hottest cells look less salient.
- viridis/cividis compress the 25–35 °C bulk of CONUS (most of the East) into a narrow teal band. This gives low
  contrast in the East but an honest, ordered ramp. inferno gives the best overall reading: the Montana–Dakota hot
  spot (~38–42 °C), cool Rockies ridges (~10–20 °C), cool Pacific NW coast (~15–20 °C) and cooler Great Lakes/New
  England (~22–27 °C) are all readable.
- cividis gives the same ordering with yellow–blue only (colour-vision-deficiency safe); mid values look grey.

## Fig 3 — lightness profiles
- viridis, inferno and cividis: monotone L*. inferno spans 0→98, the largest range (more distinguishable steps);
  viridis spans 15→91 and cividis 14→91.
- jet: L* rises 13→96 then falls to 25 (3 sign changes, with a kink at 0.11). turbo: rise then fall (1 change). So
  equal data steps are not equal perceived steps, and two different values can share a lightness (e.g. L* ≈ 60 at
  positions ~0.25 and ~0.8).
- RdBu_r / coolwarm: symmetric profiles (L* peaks at the centre: 97 / 88). This is the intended design for diverging
  data, where the light centre marks the reference value (0 anomaly). Their greyscale renderings lose the sign.

## Fig 4 — discrete classes, D2
- Equal-interval 5 °C classes: 10 bins from 5–55 °C. The land share per class is very uneven (0.0 % to 42.7 %; the
  30–35 °C class covers 42.7 % of land), so most of the East is one or two colours. Boundaries are interpretable
  ("35 °C" isotherm).
- Quantile (decile) classes: breaks 24.6/26.9/28.6/30.2/31.6/32.7/33.7/34.8/37.3 °C. Each class holds 8.9–10.8 % of
  land, which maximises contrast. But classes are 1–3 °C wide in the middle and 20 °C wide at the ends (5–24.6 and
  37.3–52 °C). As a result the cool NW/NE and Great Lakes look as "extreme" as the 50 °C desert, and the map
  exaggerates small differences in the Plains (e.g. the 32.7–33.7 °C class).
- The histogram is bimodal-ish (a peak at ~32–34 °C plus a shoulder at ~25 °C and a hot tail at ~40–42 °C = northern
  Plains/desert).

## Fig 5 — pr linear vs log, D3 (Debby) and D7 (Helene)
- D3 linear (0–331 mm): only the FL west coast to SC coastal plain stands out (>150 mm). Elsewhere looks dry.
  Clipped at 25 mm: the Debby swath (FL→GA→SC) saturates and a second, frontal band appears across the Dakotas–MN–WI–MI
  and New England. Log: light monsoon showers (0.3–5 mm) over CO/NM/UT/AZ and MT/ID become visible. Wet land share
  is 32.3 %, median wet-cell rain 3.5 mm, p99 142.5 mm.
- D7 linear (0–359 mm): the heaviest rain is a SW–NE stripe over GA/SC/NC Appalachians (Helene + pre-storm
  rain). Clipped: the whole Southeast (AL, GA, SC, NC, TN, KY) saturates. Log: the core (>100 mm) separates from a
  broad 10–30 mm shield, and rain in WA/Pacific NW and New England appears. Wet share is 23.4 %; median wet 12.6 mm.
- Linear hides light rain because 90 % of wet cells are < ~10 % of the maximum. Log compresses the extreme tail.
  Zeros are masked (shown as cream "dry") because log(0) is undefined. This is an explicit category, not an epsilon,
  so dry and drizzle stay separate.

## Fig 6 — diverging anomaly
- D2 (24 Jul): warm anomaly dominates (69.3 % of land > 0). Montana/N Wyoming/W Dakotas +10 to +15 °C; the West +3 to
  +8 °C. A cool band of −3 to −8 °C runs from S Texas → LA → MS/AL/TN (rain-cooled). The coolwarm version shows the
  same pattern with less saturated extremes.
- D7 (26 Sep): cool anomaly dominates (mean −2.48 °C; 20.0 % of land < −5 °C). The Pacific NW and New England are
  −8 to −12 °C. The strongest cold anomaly (−10 to −13 °C) is a narrow N–S band over AL/GA/TN = Helene's cloud and
  rain shield. The N Plains (Dakotas/Nebraska) are +5 to +8 °C.
- viridis with min–max has no visual zero. On D2, 0 °C falls in dark teal, so slightly negative and slightly
  positive anomalies look the same. Viewers read "yellow = high" but cannot tell warmer from colder than normal.

## Fig 7 — global normalisation (−6.35 to 53.85 °C)
- Dates are comparable: D1/D2 are visibly the hottest overall (desert SW yellow; Plains orange). D6–D8 (Sep) are
  darker overall, especially the Pacific NW and New England.
- D3: dark (cool) band over the N Plains/Upper Midwest = the frontal rain band of Fig 5/9.
- D7/D8: darker purple patch over AL/GA/TN = Helene's rain shield.
- Because the global range spans 60 °C, most of CONUS falls in 25–40 °C (orange-red), so within-day detail is low.

## Fig 8 — local normalisation
- Each date fills the whole palette, so the coolest region of each day turns near-black even when it is warm in
  absolute terms. D3's Upper Midwest (~15–20 °C) and D8's Tennessee Valley look as dark as D6's Rockies near −2.7 °C.
- The range spans 64–80 % of the global range (D5 narrowest, 9.1–47.8 °C; D6 widest, −2.7–45.2 °C). Colours mean
  different temperatures in each panel, so they cannot be compared without reading each colorbar.

## Fig 9 — precipitation, 8 dates, global log
- D1: Beryl swath from the upper TX coast NE through E Texas, Arkansas, Missouri and Illinois into Michigan (>30 mm
  core in E TX/AR).
- D2: monsoon in the SW (AZ/NM/CO/UT) plus Gulf Coast–Appalachian convection.
- D3: Debby on FL/GA/SC + Upper Midwest frontal band.
- D4/D5: scattered convection; D5 has a SW–NE band from TX/OK through KS/MO/IA to WI plus the Mid-Atlantic.
- D6: Francine's heavy core over LA/MS/AL (S Louisiana > 100 mm) plus rain over the Pacific NW and N Rockies.
- D7: Helene's SE core + New England. D8: the heaviest rain has moved inland over TN/KY/W NC/VA (Appalachian flood
  rain), with Florida mostly dry.

## Fig 10 — contour variable candidates (D2)
- VPD: p95/p5 = 11.0 (0.29–3.20 kPa over the 8 dates); 0 % of cells at the maximum; roughness 0.19. A strong
  west–east gradient: >4 kPa in the Mojave/Sonoran deserts, Central Valley and Great Basin; ~3 kPa on the N Plains
  (MT/WY) heat dome; <1 kPa east of ~97° W. The isolines trace real dry/humid boundaries.
- rmax: 21.3 % of cells sit exactly at 100 % (saturation plateau). The 90th-percentile level coincides with the
  plateau, so the isolines fragment into 118,998 segments, the most of the three. Range ratio only 2.6.
- srad: smoothest (roughness 0.12; 42,426 segments). Its pattern is transient cloud cover: low srad over the
  Gulf-coast → Appalachian band (rain-cooled, cf. Fig 6 D2) and New England. It is less physically graded.
- So VPD was chosen: largest dynamic range, no plateau, physically meaningful thresholds, and it links S1
  temperature with moisture.

## Fig 11 — lookup table
- Shows all 16 cases. Cases 5 and 10 are drawn with both resolutions (solid = joined through the centre, dashed =
  separated). Bits are (tl tr br bl).

## Fig 12 — validation
- With the same saddle rule ('high' = skimage fully_connected='high'), our MS reproduces skimage **exactly**:
  17,993/17,993 (1.005 kPa), 21,715/21,715 (2.005), 11,877/11,877 (3.005) identical segments; max vertex distance
  0.000 cells. Against skimage 'low' only 17,091 / 20,943 / 11,519 are identical (the rest differ only at saddles).
- Saddle cells: 451 / 386 / 179. The asymptotic decider joins 195 / 177 / 84 of them (45–47 %); the mean decider joins
  186 / 181 / 81. So asymptotic and mean disagree on only a few percent of saddles.
- Isoline length (cells): own (asymptotic) 12,952 / 15,903 / 8,844; skimage 13,144 / 16,086 / 8,933; contourpy
  13,037 / 15,918 / 8,854. The differences (≤1.5 %) come only from the saddle connections.
- Runtime: own vectorised NumPy 0.08–0.13 s vs skimage (Cython) 0.02–0.05 s per level on 810,810 cells.
- Zoom (Nebraska, row 0 = 41.98° N, col 0 = 100.68° W): in a checkerboard-like patch around 2.0 kPa, the fixed rule
  creates diamond-shaped closed loops around single cells. The asymptotic decider instead connects the bands into
  longer continuous lines. Both are valid; the asymptotic choice is consistent with the bilinear interpolant.

## Fig 13 — isolines vs filled (D1, 8 Jul)
- Isolines alone: the 10 levels pack tightly where the gradient is steep (Sierra Nevada / Central Valley edge,
  Mogollon Rim, Wasatch), so line density is a gradient cue. But values must be read from line colour, which is hard
  for 10 levels, and the low-VPD East is a tangle of the 0.5/1.0 kPa lines.
- Filled bands: give immediate magnitude (desert SW >5 kPa dark brown; East <1 kPa pale). The level is
  read from the colour bar, but gradient steepness is less visible.
- Bands + lines + labels give the best of both.

## Fig 14 — level placement (D2)
- Uniform 0.5 kPa: band shares 0.7–26.4 %. Most of the East falls in 0.5–1.0 kPa.
- Quantile (deciles): every band has 9.6–10.2 % of land. But the breaks bunch between 0.53 and 1.37 kPa (5 of 9 lines),
  so the East breaks into many tiny contours. In the West, everything above 3.16 kPa is one class.
- Domain thresholds (0.5/1/2/3/4 kPa): band shares 3.5–31.2 %. Interpretable categories: the 2 kPa line separates
  the semi-arid West + N Plains heat dome from the humid East; ≥4 kPa marks the hot deserts.
- The histogram is bimodal (peaks ~0.9 and ~2.2 kPa = humid East vs dry West), which is why uniform levels
  under-sample the first mode.

## Fig 15 — smoothing
- CONUS segments at 2 & 3 kPa: σ=0 → 33,599; σ=1 (4 km) → 20,652; σ=3 (12 km) → 11,794; σ=6 (24 km) → 8,443.
- Zoom UT/CO: 311 separate polylines (≈17,700 km of isoline) → 58 → 13 → 9 (≈5,200 km). Unsmoothed lines follow
  every ridge and valley (terrain-driven VPD). At σ=3, the major structure (dry Colorado Plateau / Uinta Basin vs
  moist Colorado Rockies) survives with 13 lines. σ=6 starts to merge separate dry basins and shift lines into
  the mountains, which over-smooths.

## Fig 16 — overlay (D1, 8 Jul)
- (a) Labelled 1–4 kPa lines over the VPD field: the 4 kPa line encloses the Mojave/Sonoran deserts and the
  Central Valley. The 1 kPa line meanders along ~100° W and through the East.
- (b) Over Tmax: the ≥3–4 kPa contours coincide with the hottest Tmax (≥40 °C: CA, NV, AZ). The VPD lines follow
  temperature, but the Rockies show low VPD where temperature is low. East of 100° W, Tmax is 30–35 °C but VPD stays
  <1–2 kPa (humid Gulf air, Beryl's moisture over TX/AR). So hot does not always mean dry, which the bivariate
  overlay makes explicit.

## Fig 17 — VPD evolution (fixed 1/2/3/4 kPa)
- Land share ≥2 kPa: D1 23.7 %, D2 34.2 % (seasonal high, heat-wave peak), D3 32.4 %, D4 24.4 %, D5 18.4 %, D6 21.1 %,
  D7 16.3 %, D8 20.5 %. ≥4 kPa: 4.6 % (D1) → 3.5 % (D2) → 1.1–2.0 % in Aug–Sep.
- The ≥1 kPa share stays at 64–73 % on every date (the dry West is persistent). The East moves below 1 kPa during
  tropical rain (D3 Debby: SE coast <1 kPa; D7 Helene: SE). The N Plains ≥3 kPa heat dome on D2 disappears by D4.
