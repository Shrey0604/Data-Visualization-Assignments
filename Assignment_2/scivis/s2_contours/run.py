"""S2 - Contour mapping of gridMET vapour pressure deficit (VPD), Jul-Sep 2024.

Owner: Shrey Modi (BT2024125)

Isolines come from our own Marching Squares (marching_squares.py); filled bands use Matplotlib contourf.

Figures (images/):
  Fig_10_s2_variable_candidates.png   why VPD (vs rmax, srad) is contoured
  Fig_11_marching_squares_cases.png   16-case lookup table incl. both saddle resolutions
  Fig_12_ms_validation.png            own MS vs skimage.find_contours (+ saddle decider zoom)
  Fig_13_isolines_vs_filled.png       isolines vs filled bands vs both
  Fig_14_contour_levels.png           uniform vs quantile vs domain-threshold levels
  Fig_15_contour_smoothing.png        Gaussian pre-smoothing sigma = 0, 1, 3, 6 cells
  Fig_16_contour_overlay.png          isolines over colour-mapped fields
  Fig_17_vpd_contour_evolution.png/.gif   8 dates, fixed levels
Tables (data/processed/): s2_validation.csv, s2_smoothing.csv, s2_levels.csv, s2_variable_choice.csv

Run: python scivis/s2_contours/run.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import contourpy
import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.spatial import cKDTree
from skimage.measure import find_contours

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scivis" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_gridmet import PROC_DIR, load_var  # noqa: E402
from maps import PC, add_features, contourf_proj, draw_field, map_axes, nodata_patch  # noqa: E402
from marching_squares import join_segments, marching_squares, segment_length  # noqa: E402
from plot_utils import DATES, DATE_LABELS, EVENTS, save_fig  # noqa: E402

IMG = ROOT / "images"
VPD_LABEL = "Vapour pressure deficit, VPD (kPa)"
VPD_CMAP = "YlOrBr"
UNIFORM_LEVELS = np.arange(0.5, 5.01, 0.5)
# Domain-informed VPD classes (plant-stress / fire-weather literature; % TODO verify exact thresholds in report)
DOMAIN_LEVELS = [0.5, 1.0, 2.0, 3.0, 4.0]
DOMAIN_NAMES = ["humid / low stress", "moderate", "high plant stress", "very high (fire weather)", "extreme"]
EVOL_LEVELS = [1.0, 2.0, 3.0, 4.0]
SMOOTH_REGION = [-114.0, -103.0, 35.5, 42.5]   # Utah / Colorado plateau + Rockies
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5})


def date_title(i: int) -> str:
    return f"{DATE_LABELS[i]}  {pd.Timestamp(DATES[i]):%d %b %Y}  ({EVENTS[i]})"


def panel_letter(ax, k):
    ax.text(0.01, 0.99, f"({chr(97 + k)})", transform=ax.transAxes, ha="left", va="top", fontsize=10,
            fontweight="bold", zorder=7, bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5))


def inset_legend(ax, handles, fontsize=7, loc="lower left"):
    ax.legend(handles=handles, loc=loc, fontsize=fontsize, framealpha=0.92, borderpad=0.4,
              handlelength=1.4).set_zorder(8)


def ms_lines(da, levels, decider="asymptotic"):
    """Run our Marching Squares for each level on a (lat, lon) field -> {level: segments in lon/lat}."""
    x, y, Z = da.lon.values, da.lat.values, da.values
    return {lv: marching_squares(Z, lv, x, y, decider=decider) for lv in levels}


def add_lines(ax, res: dict, colors, lw=0.8, zorder=4, ls="-", transform=PC):
    for (lv, r), c in zip(res.items(), colors):
        ax.add_collection(LineCollection(r.segments, colors=[c], linewidths=lw, linestyles=ls,
                                         transform=transform, zorder=zorder))


def level_colors(levels, cmap="viridis"):
    cm = plt.get_cmap(cmap)
    return [cm(v) for v in np.linspace(0.05, 0.95, len(levels))]


def nan_gaussian(da, sigma):
    """Normalised (mask-aware) Gaussian smoothing: G(f*m)/G(m); NaN cells stay NaN."""
    if sigma == 0:
        return da.copy()
    f = da.values
    m = np.isfinite(f)
    num = gaussian_filter(np.where(m, f, 0.0), sigma)
    den = gaussian_filter(m.astype(float), sigma)
    out = da.copy()
    out.values = np.where(m, num / np.maximum(den, 1e-9), np.nan)
    return out


def label_polylines(ax, res: dict, fmt="{:g}", per_level=2, min_len=3.0, fontsize=6.5, transform=PC):
    """Place a text label at the middle of the longest polylines of each level (our own clabel)."""
    for lv, r in res.items():
        lines = sorted(join_segments(r.segments), key=lambda l: -np.linalg.norm(np.diff(l, axis=0), axis=1).sum())
        for line in lines[:per_level]:
            if np.linalg.norm(np.diff(line, axis=0), axis=1).sum() < min_len:
                continue
            p = line[len(line) // 2]
            ax.text(p[0], p[1], fmt.format(lv), transform=transform, fontsize=fontsize, ha="center", va="center",
                    zorder=9, bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.6))


# ----------------------------------------------------------------------------------------------
def fig_candidates(out):
    i = 1
    rows = []
    fig = plt.figure(figsize=(16, 4.9), constrained_layout=True)
    specs = [("vpd", "YlOrBr", "VPD (kPa)"), ("rmax", "GnBu", "Maximum relative humidity, rmax (%)"),
             ("srad", "magma", "Shortwave radiation, srad (W m$^{-2}$)")]
    for k, (v, cm, lab) in enumerate(specs):
        all8 = load_var(v).sel(time=DATES)
        a = all8.values
        f = all8.sel(time=DATES[i])
        lv = np.unique(np.round(np.nanpercentile(f.values, [10, 30, 50, 70, 90]), 2))
        res = ms_lines(f, lv)
        rough = []
        for t in range(a.shape[0]):
            g = a[t]; m = np.isfinite(g); g0 = np.where(m, g, np.nanmean(g))
            rough.append(np.nanstd((g0 - uniform_filter(g0, 15))[m]) / np.nanstd(g0[m]))
        p5, p95 = np.nanpercentile(a, [5, 95])
        plateau = float(np.mean(a[np.isfinite(a)] >= np.nanmax(a) - 1e-6))
        nseg = sum(len(r.segments) for r in res.values())
        rows.append({"variable": v, "p5": p5, "p95": p95, "p95_over_p5": p95 / p5,
                     "roughness_8dates": np.mean(rough), "share_at_max_value": plateau, "segments_D2_5levels": nseg})
        ax = map_axes(fig, 1, 3, k + 1)
        im = draw_field(ax, f, cm, mcolors.Normalize(*np.nanpercentile(f.values, [1, 99])))
        add_lines(ax, res, ["k"] * len(lv), lw=0.5)
        add_features(ax, labels="lb" if k == 0 else "b")
        ax.set_title(f"{v}: p95/p5 = {p95 / p5:.1f}, roughness = {np.mean(rough):.2f}, "
                     f"cells at max = {100 * plateau:.1f} %\n{nseg:,} isoline segments for 5 decile levels", fontsize=9)
        panel_letter(ax, k)
        cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.9, pad=0.03, aspect=30, extend="both")
        cb.set_label(lab)
        for l in lv:
            cb.ax.axvline(l, color="k", lw=0.8)
        if k == 0:
            inset_legend(ax, [nodata_patch("No data"), Line2D([], [], color="k", lw=0.8, label="isolines (10/30/50/70/90th pct)")],
                         fontsize=6.5)
    fig.suptitle(f"Choosing the contour variable - {date_title(i)}; black lines = our Marching Squares at the 10/30/50/70/90th "
                 "percentile of the day", fontsize=11.5)
    save_fig(fig, out)
    pd.DataFrame(rows).round(4).to_csv(PROC_DIR / "s2_variable_choice.csv", index=False)


def fig_cases(out):
    """Illustrate the 16-case lookup table (corner states, edge crossings, both saddle resolutions)."""
    from marching_squares import LUT, SADDLE
    mid = {0: (0.5, 0), 1: (1, 0.5), 2: (0.5, 1), 3: (0, 0.5)}   # B, R, T, L midpoints
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]                    # bl, br, tr, tl
    fig, axes = plt.subplots(4, 4, figsize=(10, 10.6), constrained_layout=True)
    for c in range(16):
        ax = axes[c // 4, c % 4]
        ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=1.2, color="0.3"))
        bits = [(c >> b) & 1 for b in range(4)]
        for (px, py), bit in zip(corners, bits):
            ax.plot(px, py, "o", ms=13, mfc="#d95f02" if bit else "white", mec="k", mew=1.2, zorder=3)
        if c in SADDLE:
            joined, sep = SADDLE[c]
            for e0, e1 in joined:
                ax.plot(*zip(mid[e0], mid[e1]), color="#1b9e77", lw=3, zorder=2)
            for e0, e1 in sep:
                ax.plot(*zip(mid[e0], mid[e1]), color="#7570b3", lw=2.2, ls="--", zorder=2)
            ax.plot(0.5, 0.5, "s", ms=7, color="0.5")
            ax.set_title(f"case {c} (saddle, ambiguous)", fontsize=10, color="#b2182b")
        else:
            for e0, e1 in LUT[c]:
                ax.plot(*zip(mid[e0], mid[e1]), color="#1b9e77", lw=3, zorder=2)
            ax.set_title(f"case {c}", fontsize=10)
        ax.text(0.5, -0.32, "bits (tl tr br bl) = " + "".join(str(b) for b in bits[::-1]), ha="center", fontsize=8)
        ax.set_xlim(-0.25, 1.25); ax.set_ylim(-0.42, 1.2); ax.set_aspect("equal"); ax.axis("off")
    handles = [Line2D([], [], marker="o", ls="", mfc="#d95f02", mec="k", ms=10, label="corner value ≥ isovalue (inside)"),
               Line2D([], [], marker="o", ls="", mfc="white", mec="k", ms=10, label="corner value < isovalue"),
               Line2D([], [], color="#1b9e77", lw=3, label="isoline segment (decider value ≥ isovalue: inside corners joined)"),
               Line2D([], [], color="#7570b3", lw=2.2, ls="--", label="saddle alternative (decider < isovalue: inside corners separated)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.06), frameon=False)
    fig.suptitle("Marching Squares lookup table: case = 1·bl + 2·br + 4·tr + 8·tl; segments join edge crossings\n"
                 "(drawn at edge midpoints here; the implementation interpolates linearly along each edge)", fontsize=11.5)
    save_fig(fig, out)


def sk_segments(Z, level, fc="high"):
    out = []
    for c in find_contours(Z, level, fully_connected=fc):
        xy = c[:, ::-1]
        out.append(np.stack([xy[:-1], xy[1:]], 1))
    return np.concatenate(out) if out else np.empty((0, 2, 2))


def segset(segs, nd=7):
    s = set()
    for p, q in np.round(segs, nd):
        a, b = tuple(p), tuple(q)
        s.add((min(a, b), max(a, b)))
    return s


def fig_validation(vpd, out):
    i = 1
    f = vpd.sel(time=DATES[i])
    Z = f.values
    levels = [1.005, 2.005, 3.005]   # offset by half the 0.01 kPa storage step -> no ties with data values
    rows = []
    for lv in levels:
        t0 = time.perf_counter(); r_hi = marching_squares(Z, lv, decider="high"); t_ms = time.perf_counter() - t0
        r_as = marching_squares(Z, lv, decider="asymptotic")
        r_me = marching_squares(Z, lv, decider="mean")
        t0 = time.perf_counter(); sk = sk_segments(Z, lv, "high"); t_sk = time.perf_counter() - t0
        sk_lo = sk_segments(Z, lv, "low")
        A, S = segset(r_hi.segments), segset(sk)
        # vertex distance both ways (index units = grid cells)
        va, vs = r_as.segments.reshape(-1, 2), sk.reshape(-1, 2)
        d1 = cKDTree(vs).query(va)[0]; d2 = cKDTree(va).query(vs)[0]
        cg = contourpy.contour_generator(np.arange(Z.shape[1]), np.arange(Z.shape[0]), np.ma.masked_invalid(Z),
                                         name="serial", line_type="Separate")
        mpl_len = sum(np.linalg.norm(np.diff(l, axis=0), axis=1).sum() for l in cg.lines(lv))
        rows.append({"level_kPa": lv, "saddle_cells": r_hi.n_saddles,
                     "segments_own_high": len(r_hi.segments), "segments_skimage_high": len(sk),
                     "identical_segments_high_vs_high": len(A & S), "match_pct": 100 * len(A & S) / max(len(S), 1),
                     "own_high_vs_skimage_low_identical": len(A & segset(sk_lo)),
                     "segments_own_asymptotic": len(r_as.segments),
                     "asymptotic_joined_saddles": r_as.n_saddles_joined, "mean_joined_saddles": r_me.n_saddles_joined,
                     "segments_differing_asym_vs_skimage_high": len(segset(r_as.segments) ^ S),
                     "max_vertex_dist_cells": max(d1.max(), d2.max()),
                     "length_own_asym_cells": segment_length(r_as.segments),
                     "length_skimage_cells": segment_length(sk), "length_contourpy_cells": mpl_len,
                     "time_own_s": t_ms, "time_skimage_s": t_sk})
    df = pd.DataFrame(rows)
    df.round(6).to_csv(PROC_DIR / "s2_validation.csv", index=False)
    print(df.T.to_string())

    # ---- figure
    fig = plt.figure(figsize=(16, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.55, 1, 1])
    ax = map_axes(fig, gs[0, 0])
    draw_field(ax, f, VPD_CMAP, mcolors.Normalize(0, 5), alpha=0.6)
    cols = ["#1b9e77", "#d95f02", "#7570b3"]
    for lv, c in zip(levels, cols):
        r = marching_squares(Z, lv, f.lon.values, f.lat.values, decider="asymptotic")
        ax.add_collection(LineCollection(r.segments, colors=[c], linewidths=1.6, transform=PC, zorder=4))
        for cc in find_contours(Z, lv, fully_connected="high"):
            lon = np.interp(cc[:, 1], np.arange(Z.shape[1]), f.lon.values)
            lat = np.interp(cc[:, 0], np.arange(Z.shape[0]), f.lat.values)
            ax.plot(lon, lat, color="k", lw=0.35, ls="-", transform=PC, zorder=5)
    add_features(ax, labels="lb")
    ax.set_title(f"(a) Own Marching Squares (thick, coloured) vs skimage.find_contours (thin black)\n{date_title(i)}",
                 fontsize=9.5)
    inset_legend(ax, [Line2D([], [], color=c, lw=1.6, label=f"own MS, {lv:g} kPa") for lv, c in zip(levels, cols)]
                 + [Line2D([], [], color="k", lw=0.5, label="skimage (same levels)"), nodata_patch("No data")], fontsize=6.5)

    # (b) zoom on a saddle where the asymptotic decider disagrees with the fixed 'high' rule
    lv = 2.005
    r_as = marching_squares(Z, lv, decider="asymptotic")
    bl, br, tr, tl = Z[:-1, :-1], Z[:-1, 1:], Z[1:, 1:], Z[1:, :-1]
    case = ((bl >= lv) * 1 + (br >= lv) * 2 + (tr >= lv) * 4 + (tl >= lv) * 8)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (bl * tr - br * tl) / (bl + tr - br - tl)
    sad = np.isin(case, [5, 10]) & np.isfinite(bl + br + tr + tl)
    disagree = sad & (s < lv)
    ii, jj = np.nonzero(disagree)
    k = len(ii) // 2
    ci, cj = ii[k], jj[k]
    w = 4
    i0, i1, j0, j1 = ci - w, ci + w + 1, cj - w, cj + w + 1
    sub = Z[i0:i1 + 1, j0:j1 + 1]
    for kk, (dec, title) in enumerate([("high", "fixed rule ('high', = skimage)"), ("asymptotic", "asymptotic decider (ours)")]):
        axz = fig.add_subplot(gs[0, 1 + kk])
        rr = marching_squares(sub, lv, decider=dec)
        im = axz.imshow(sub, origin="lower", cmap=VPD_CMAP, norm=mcolors.Normalize(np.nanmin(sub), np.nanmax(sub)),
                        extent=[-0.5, sub.shape[1] - 0.5, -0.5, sub.shape[0] - 0.5], interpolation="nearest")
        yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
        inside = sub >= lv
        axz.scatter(xx[inside], yy[inside], s=16, c="#d95f02", edgecolors="k", linewidths=0.4, zorder=4,
                    label="cell centre ≥ 2.005 kPa")
        axz.scatter(xx[~inside], yy[~inside], s=16, c="white", edgecolors="k", linewidths=0.4, zorder=4,
                    label="cell centre < 2.005 kPa")
        axz.add_collection(LineCollection(rr.segments, colors="#1b9e77" if dec == "asymptotic" else "#7570b3",
                                          linewidths=2.2, zorder=5))
        si, sj = np.nonzero(np.isin(case[i0:i1, j0:j1], [5, 10]))
        for a_, b_ in zip(si, sj):
            axz.add_patch(Rectangle((b_, a_), 1, 1, fill=False, ec="#b2182b", lw=1.8, ls="--", zorder=6))
        axz.set_xlim(-0.5, sub.shape[1] - 0.5); axz.set_ylim(-0.5, sub.shape[0] - 0.5)
        lon0, lat0 = f.lon.values[j0], f.lat.values[i0]
        axz.set_xlabel(f"Grid column (≈ 4 km); col 0 = {abs(lon0):.2f}° W")
        axz.set_ylabel(f"Grid row (≈ 4 km); row 0 = {lat0:.2f}° N")
        axz.set_title(f"({'bc'[kk]}) Saddle cells (red dashed) at 2.005 kPa:\n{title}", fontsize=9.5)
        cb = fig.colorbar(im, ax=axz, orientation="horizontal", shrink=0.9, pad=0.02, aspect=25)
        cb.set_label(VPD_LABEL)
        if kk == 0:
            axz.legend(loc="lower left", fontsize=6.5, framealpha=0.92, markerscale=1.0)
    sm = df.iloc[1]
    fig.suptitle(f"Validation: with the same saddle rule our implementation reproduces skimage exactly "
                 f"({int(sm.identical_segments_high_vs_high):,}/{int(sm.segments_skimage_high):,} segments at 2.005 kPa); "
                 f"the asymptotic decider separates {int(sm.saddle_cells - sm.asymptotic_joined_saddles)} of the "
                 f"{int(sm.saddle_cells)} saddle cells that the fixed rule joins", fontsize=11)
    save_fig(fig, out)
    return df


def fig_iso_vs_filled(vpd, out):
    i = 0
    f = vpd.sel(time=DATES[i])
    lv = UNIFORM_LEVELS
    res = ms_lines(f, lv)
    cols = level_colors(lv, "viridis")
    cmap = plt.get_cmap(VPD_CMAP)
    bnorm = mcolors.BoundaryNorm(np.r_[0, lv, 11], cmap.N, extend="neither")
    fig = plt.figure(figsize=(16, 4.75), constrained_layout=True)
    for k in range(3):
        ax = map_axes(fig, 1, 3, k + 1)
        if k == 0:
            add_lines(ax, res, cols, lw=0.6)
            sm = plt.cm.ScalarMappable(cmap=mcolors.ListedColormap(cols), norm=mcolors.BoundaryNorm(
                np.r_[lv - 0.25, lv[-1] + 0.25], len(lv)))
            cb = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.9, pad=0.03, aspect=30, ticks=lv)
            cb.set_label("Isoline value, VPD (kPa)")
            ax.set_title("(a) Isolines only (own Marching Squares), 10 levels 0.5-5 kPa", fontsize=9.5)
        else:
            cs = contourf_proj(ax, f, levels=np.r_[0, lv, 11], cmap=cmap,
                             norm=bnorm, zorder=1)
            if k == 2:
                add_lines(ax, res, ["k"] * len(lv), lw=0.35)
                label_polylines(ax, {l: res[l] for l in [1.0, 2.0, 3.0, 4.0]}, per_level=1, min_len=4)
            cb = fig.colorbar(cs, ax=ax, orientation="horizontal", shrink=0.9, pad=0.03, aspect=30, ticks=np.r_[0, lv])
            cb.set_label(VPD_LABEL)
            cb.ax.tick_params(labelsize=7)
            ax.set_title("(b) Filled bands only (contourf, same levels)" if k == 1 else
                         "(c) Filled bands + isolines + labels (1-4 kPa)", fontsize=9.5)
        add_features(ax, labels="lb" if k == 0 else "b")
        panel_letter(ax, k)
        if k == 0:
            inset_legend(ax, [nodata_patch("No data")], fontsize=6.5)
    fig.suptitle(f"Isolines vs filled contours of VPD - {date_title(i)}", fontsize=12)
    save_fig(fig, out)


def fig_levels(vpd, out):
    i = 1
    f = vpd.sel(time=DATES[i])
    v = f.values[np.isfinite(f.values)]
    q_levels = np.round(np.percentile(v, np.arange(10, 100, 10)), 2)
    specs = [("Uniform: every 0.5 kPa (0.5-5.0)", UNIFORM_LEVELS),
             ("Quantile: deciles of the day's land cells", q_levels),
             ("Domain thresholds: 0.5 / 1 / 2 / 3 / 4 kPa", np.array(DOMAIN_LEVELS))]
    fig = plt.figure(figsize=(16, 7.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.45, 0.75])
    rows = []
    for k, (name, lv) in enumerate(specs):
        ax = map_axes(fig, gs[0, k])
        cmap = plt.get_cmap(VPD_CMAP)
        bounds = np.r_[min(0, v.min()), lv, max(v.max(), lv[-1]) + 0.01]
        cs = contourf_proj(ax, f, levels=bounds, cmap=cmap,
                         norm=mcolors.BoundaryNorm(bounds, cmap.N), zorder=1)
        res = ms_lines(f, lv)
        add_lines(ax, res, ["k"] * len(lv), lw=0.35)
        add_features(ax, labels="lb" if k == 0 else "b")
        ax.set_title(f"({'abc'[k]}) {name}", fontsize=9.5)
        panel_letter(ax, k)
        cb = fig.colorbar(cs, ax=ax, orientation="horizontal", shrink=0.9, pad=0.03, aspect=30, ticks=bounds)
        cb.set_label(VPD_LABEL); cb.ax.tick_params(labelsize=6.5, rotation=90)
        if k == 0:
            inset_legend(ax, [nodata_patch("No data")], fontsize=6.5)
        hx = fig.add_subplot(gs[1, k])
        hx.hist(v, bins=np.linspace(0, v.max(), 150), color="0.6", weights=np.full(v.size, 100 / v.size))
        for l in lv:
            hx.axvline(l, color="k", lw=0.7)
        counts = np.histogram(v, bins=bounds)[0]
        sh = 100 * counts / counts.sum()
        hx.set_title(f"({'def'[k]}) band area shares: min {sh.min():.1f} %, max {sh.max():.1f} %", fontsize=9)
        hx.set_xlabel(VPD_LABEL); hx.set_ylabel("Share of land cells (%)"); hx.grid(alpha=0.3)
        rows.append({"scheme": name, "levels": " ".join(f"{x:g}" for x in lv),
                     "segments": sum(len(r.segments) for r in res.values()),
                     "min_band_share_pct": sh.min(), "max_band_share_pct": sh.max()})
    pd.DataFrame(rows).round(2).to_csv(PROC_DIR / "s2_levels.csv", index=False)
    fig.suptitle(f"Number and placement of contour levels - {date_title(i)}", fontsize=12)
    save_fig(fig, out)


def fig_smoothing(vpd, out):
    i = 1
    f = vpd.sel(time=DATES[i])
    sigmas = [0, 1, 3, 6]
    lv = [2.0, 3.0]
    rows = []
    fig = plt.figure(figsize=(17, 7.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.05])
    for k, sg in enumerate(sigmas):
        g = nan_gaussian(f, sg)
        res = ms_lines(g, lv)
        sub = g.sel(lon=slice(SMOOTH_REGION[0], SMOOTH_REGION[1]), lat=slice(SMOOTH_REGION[2], SMOOTH_REGION[3]))
        res_sub = ms_lines(sub, lv)
        nlines = sum(len(join_segments(r.segments)) for r in res_sub.values())
        nseg = sum(len(r.segments) for r in res.values())
        length_km = sum(segment_length(r.segments) for r in res_sub.values()) / 0.0416667 * 4.0
        rows.append({"sigma_cells": sg, "sigma_km": 4 * sg, "segments_conus": nseg,
                     "polylines_zoom": nlines, "length_zoom_km_approx": length_km})
        for r_, (region, labels) in enumerate([(None, "lb" if k == 0 else "b"), (SMOOTH_REGION, "lb" if k == 0 else "b")]):
            ax = map_axes(fig, gs[r_, k], extent=region)
            draw_field(ax, g if region is None else sub, VPD_CMAP, mcolors.Normalize(0, 5))
            add_lines(ax, res if region is None else res_sub, ["#2166ac", "#b2182b"], lw=0.5 if region is None else 0.9)
            add_features(ax, labels=labels, lw_states=0.4)
            if region is None:
                ax.set_title(f"σ = {sg} cells (≈ {4 * sg} km): {nseg:,} segments (CONUS)", fontsize=9.5)
                ax.add_patch(Rectangle((SMOOTH_REGION[0], SMOOTH_REGION[2]), SMOOTH_REGION[1] - SMOOTH_REGION[0],
                                       SMOOTH_REGION[3] - SMOOTH_REGION[2], fill=False, ec="k", lw=1.2, transform=PC, zorder=6))
            else:
                ax.set_title(f"Zoom UT/CO: {nlines} separate polylines, ≈{length_km:,.0f} km of isoline", fontsize=9.5)
            panel_letter(ax, k + 4 * r_)
            if k == 0 and r_ == 0:
                inset_legend(ax, [Line2D([], [], color="#2166ac", lw=1, label="2 kPa"),
                                  Line2D([], [], color="#b2182b", lw=1, label="3 kPa"), nodata_patch("No data")], fontsize=6.5)
    sm = plt.cm.ScalarMappable(cmap=VPD_CMAP, norm=mcolors.Normalize(0, 5))
    fig.colorbar(sm, ax=fig.axes, orientation="horizontal", shrink=0.4, pad=0.02, aspect=50, label=VPD_LABEL, extend="max")
    pd.DataFrame(rows).round(1).to_csv(PROC_DIR / "s2_smoothing.csv", index=False)
    fig.suptitle(f"Effect of Gaussian pre-smoothing (mask-aware) on the 2 and 3 kPa isolines - {date_title(i)}; "
                 "box = zoom region", fontsize=12)
    save_fig(fig, out)
    print(pd.DataFrame(rows).to_string())


def fig_overlay(vpd, tmmx, out):
    i = 0
    f, t = vpd.sel(time=DATES[i]), tmmx.sel(time=DATES[i])
    lv = [1.0, 2.0, 3.0, 4.0]
    res = ms_lines(f, lv)
    cols = ["#2166ac", "#1a9850", "#fdae61", "#d73027"]
    fig = plt.figure(figsize=(15, 6.0), constrained_layout=True)
    ax = map_axes(fig, 1, 2, 1)
    im = draw_field(ax, f, VPD_CMAP, mcolors.Normalize(0, 6))
    add_lines(ax, res, ["k"] * 4, lw=0.5)
    label_polylines(ax, res, per_level=2, min_len=4)
    add_features(ax, labels="lb")
    fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.8, pad=0.03, aspect=35, label=VPD_LABEL, extend="max")
    ax.set_title("(a) VPD isolines (1-4 kPa, labelled) over the VPD colour map", fontsize=10)
    panel_letter(ax, 0)
    inset_legend(ax, [nodata_patch("No data")], fontsize=6.5)
    ax = map_axes(fig, 1, 2, 2)
    im = draw_field(ax, t, "inferno", mcolors.Normalize(10, 50))
    add_lines(ax, res, cols, lw=0.8)
    add_features(ax, labels="b")
    fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.8, pad=0.03, aspect=35,
                 label="Daily maximum temperature $T_{max}$ (°C)", extend="both")
    ax.set_title("(b) VPD isolines over the $T_{max}$ colour map (bivariate overlay)", fontsize=10)
    panel_letter(ax, 1)
    inset_legend(ax, [Line2D([], [], color=c, lw=1.5, label=f"VPD = {l:g} kPa") for l, c in zip(lv, cols)], fontsize=6.5)
    fig.suptitle(f"Contour lines overlaid on colour-mapped fields - {date_title(i)}", fontsize=12)
    save_fig(fig, out)


def fig_evolution(vpd, out_png, out_gif):
    lv = EVOL_LEVELS
    bounds = np.r_[0, lv, 12]
    cmap = plt.get_cmap(VPD_CMAP)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    rows = []

    def draw(ax, i, labels, lw=0.4, letter=True):
        f = vpd.sel(time=DATES[i])
        cs = contourf_proj(ax, f, levels=bounds, cmap=cmap, norm=norm, zorder=1)
        res = ms_lines(f, lv)
        add_lines(ax, res, ["k"] * len(lv), lw=lw)
        add_features(ax, labels=labels, fontsize=6)
        v = f.values[np.isfinite(f.values)]
        rows.append({"id": DATE_LABELS[i], "date": DATES[i], **{f"area_ge_{l:g}kPa_pct": 100 * (v >= l).mean() for l in lv},
                     "segments": sum(len(r.segments) for r in res.values())})
        return cs

    fig = plt.figure(figsize=(17, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 4)
    for i in range(8):
        ax = map_axes(fig, gs[i // 4, i % 4])
        cs = draw(ax, i, ("l" if i % 4 == 0 else "") + ("b" if i >= 4 else ""))
        ax.set_title(date_title(i).replace("  (", "\n("), fontsize=9)
        panel_letter(ax, i)
        if i == 0:
            inset_legend(ax, [nodata_patch("No data")], fontsize=6.5)
    cb = fig.colorbar(cs, ax=fig.axes, orientation="horizontal", shrink=0.45, pad=0.02, aspect=45, ticks=bounds[:-1])
    cb.set_label(VPD_LABEL + "; fixed levels 1/2/3/4 kPa on every date")
    fig.suptitle("Evolution of VPD contours over the 8 dates (fixed levels, own Marching Squares isolines + filled bands)",
                 fontsize=12.5)
    save_fig(fig, out_png)
    df = pd.DataFrame(rows).round(2)
    df.to_csv(PROC_DIR / "s2_evolution_area.csv", index=False)
    print(df.to_string())

    frames, tmp = [], out_gif.with_suffix(".frame.png")
    for i in range(8):
        fig = plt.figure(figsize=(9, 6.4))
        ax = map_axes(fig, 1, 1, 1); ax.set_position([0.04, 0.17, 0.92, 0.72])
        cs = draw(ax, i, "lb", lw=0.6)
        ax.set_title(f"S2 - VPD contours, fixed levels 1/2/3/4 kPa\n{date_title(i)}", fontsize=11)
        cax = fig.add_axes([0.15, 0.08, 0.7, 0.03])
        fig.colorbar(cs, cax=cax, orientation="horizontal", ticks=bounds[:-1], label=VPD_LABEL)
        fig.savefig(tmp, dpi=110, facecolor="white"); plt.close(fig)
        frames.append(imageio.imread(tmp))
    tmp.unlink()
    imageio.mimsave(out_gif, frames, duration=1000, loop=0)
    print(f"[gif] {out_gif.name}")


def main():
    vpd, tmmx = load_var("vpd"), load_var("tmmx")
    fig_candidates(IMG / "Fig_10_s2_variable_candidates.png")
    fig_cases(IMG / "Fig_11_marching_squares_cases.png")
    fig_validation(vpd, IMG / "Fig_12_ms_validation.png")
    fig_iso_vs_filled(vpd, IMG / "Fig_13_isolines_vs_filled.png")
    fig_levels(vpd, IMG / "Fig_14_contour_levels.png")
    fig_smoothing(vpd, IMG / "Fig_15_contour_smoothing.png")
    fig_overlay(vpd, tmmx, IMG / "Fig_16_contour_overlay.png")
    fig_evolution(vpd, IMG / "Fig_17_vpd_contour_evolution.png", IMG / "Fig_17_vpd_contour_evolution.gif")


if __name__ == "__main__":
    main()
