"""S1 - Colour mapping of gridMET Jul-Sep 2024 (tmmx, pr).

Owner: Sidhanth Prabhu (BT2024027)

Figures (images/):
  Fig_02_tmmx_continuous_colormaps.png   jet vs viridis / inferno / cividis on the same field
  Fig_03_colormap_lightness_profiles.png CIELAB L* along each colormap (perceptual uniformity)
  Fig_04_tmmx_discrete_equal_vs_quantile.png  BoundaryNorm with 5 degC classes vs decile classes
  Fig_05_pr_linear_vs_log.png            linear, clipped-linear and LogNorm precipitation
  Fig_06_tmmx_anomaly_diverging.png      diverging (TwoSlopeNorm, centred at 0) vs sequential
  Fig_07_tmmx_global_norm.png/.gif       8 dates, one global colour range
  Fig_08_tmmx_local_norm.png/.gif        8 dates, per-date colour range
  Fig_09_pr_global_log.png/.gif          8 dates of precipitation, global LogNorm

Run: python scivis/s1_colormapping/run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.patches import Patch
from skimage.color import rgb2lab

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scivis" / "common"))
from load_gridmet import PROC_DIR, anomaly, load_var  # noqa: E402
from maps import PC, add_features, draw_field, map_axes, nodata_patch  # noqa: E402
from plot_utils import DATES, DATE_LABELS, EVENTS, save_fig  # noqa: E402

IMG = ROOT / "images"
TMAX_LABEL = "Daily maximum temperature $T_{max}$ (°C)"
PR_LABEL = "Daily precipitation (mm/day)"
DRY_COLOR = "#f3efe0"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5})


def date_title(i: int) -> str:
    d = pd.Timestamp(DATES[i])
    return f"{DATE_LABELS[i]}  {d:%d %b %Y}  ({EVENTS[i]})"


def inset_legend(ax, handles, fontsize=7):
    """Legend inside a map panel (lower-left = Pacific / Mexico, never data or other text)."""
    ax.legend(handles=handles, loc="lower left", fontsize=fontsize, framealpha=0.92, borderpad=0.4,
              handlelength=1.2).set_zorder(6)


def panel_letter(ax, k):
    ax.text(0.01, 0.99, f"({chr(97 + k)})", transform=ax.transAxes, ha="left", va="top", fontsize=10,
            fontweight="bold", zorder=5, bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5))


# ----------------------------------------------------------------------------------------------
def fig_continuous(tmmx, out):
    """Same field, four continuous colormaps, identical linear norm."""
    i = 1  # D2 = western heat-wave peak
    f = tmmx.sel(time=DATES[i])
    norm = mcolors.Normalize(vmin=float(f.min()), vmax=float(f.max()))
    cmaps = [("jet", "jet (rainbow baseline)"), ("viridis", "viridis (perceptually uniform)"),
             ("inferno", "inferno (perceptually uniform)"), ("cividis", "cividis (CVD-friendly)")]
    fig = plt.figure(figsize=(13, 9.2), constrained_layout=True)
    for k, (cm, name) in enumerate(cmaps):
        ax = map_axes(fig, 2, 2, k + 1)
        im = draw_field(ax, f, cm, norm)
        add_features(ax, labels="lb" if k in (2, 3) else "l")
        ax.set_title(name, fontsize=11)
        panel_letter(ax, k)
        fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.75, pad=0.03, aspect=35, label=TMAX_LABEL)
        if k == 0:
            inset_legend(ax, [nodata_patch()])
    fig.suptitle(f"Continuous colour maps of the same field - {date_title(i)}\n"
                 f"identical linear normalisation {norm.vmin:.1f}-{norm.vmax:.1f} °C; only the palette changes",
                 fontsize=12)
    save_fig(fig, out)


def fig_lightness(out):
    """CIELAB lightness L* along each colormap - a monotone, linear L* ramp is perceptually ordered."""
    cmaps = ["jet", "turbo", "viridis", "inferno", "cividis", "RdBu_r", "coolwarm"]
    x = np.linspace(0, 1, 256)
    fig, (ax, axs) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.5, 1]},
                                  constrained_layout=True)
    styles = {"jet": ("#d62728", "-"), "turbo": ("#ff7f0e", "--"), "viridis": ("#2ca02c", "-"),
              "inferno": ("#000000", "-"), "cividis": ("#1f77b4", "-"), "RdBu_r": ("#9467bd", ":"),
              "coolwarm": ("#8c564b", "-.")}
    rows = []
    for cm in cmaps:
        rgb = plt.get_cmap(cm)(x)[:, :3]
        L = rgb2lab(rgb[None, :, :])[0, :, 0]
        c, ls = styles[cm]
        ax.plot(x, L, color=c, ls=ls, lw=2, label=cm)
        dL = np.diff(L)
        rows.append({"colormap": cm, "L_start": L[0], "L_end": L[-1], "L_min": L.min(), "L_max": L.max(),
                     "monotonic": bool((dL >= -0.05).all() or (dL <= 0.05).all()),
                     "n_sign_changes": int((np.diff(np.sign(dL[np.abs(dL) > 0.05])) != 0).sum())})
    ax.set_xlabel("Position along colour map (normalised data value, 0-1)")
    ax.set_ylabel("CIELAB lightness L* (0 = black, 100 = white)")
    ax.set_title("(a) Lightness profile of each colour map", loc="left")
    ax.grid(alpha=0.3)
    ax.legend(ncol=2, fontsize=9, loc="lower right", framealpha=0.95)
    # (b) colour strips + their greyscale (L*) rendering
    axs.set_title("(b) Colour strip and its greyscale (L*) rendering", loc="left")
    axs.set_xlim(0, 1); axs.set_ylim(-0.5, len(cmaps) - 0.5); axs.invert_yaxis()
    for r, cm in enumerate(cmaps):
        rgb = plt.get_cmap(cm)(x)[:, :3]
        L = rgb2lab(rgb[None, :, :])[0, :, 0] / 100
        axs.imshow(rgb[None], extent=[0, 1, r - 0.05, r - 0.42], aspect="auto")
        axs.imshow(np.repeat(L[None, :, None], 3, axis=2), extent=[0, 1, r + 0.38, r + 0.02], aspect="auto")
    axs.set_yticks(range(len(cmaps)), cmaps)
    axs.set_xlabel("Position along colour map (0-1); upper strip = colour, lower strip = L* only")
    axs.set_ylim(len(cmaps) - 0.5, -0.5)
    fig.suptitle("Perceptual uniformity: CIELAB lightness along the colour maps used in S1", fontsize=12)
    save_fig(fig, out)
    pd.DataFrame(rows).round(2).to_csv(PROC_DIR / "s1_colormap_lightness.csv", index=False)


def fig_discrete(tmmx, out):
    """Equal-interval (5 degC) vs quantile (decile) classes, with histograms showing the breaks."""
    i = 1
    f = tmmx.sel(time=DATES[i])
    v = f.values[~np.isnan(f.values)]
    eq_bounds = np.arange(5 * np.floor(v.min() / 5), 5 * np.ceil(v.max() / 5) + 0.1, 5)
    q_bounds = np.unique(np.round(np.percentile(v, np.linspace(0, 100, 11)), 1))
    q_bounds[0], q_bounds[-1] = np.floor(v.min()), np.ceil(v.max())
    cm = "inferno"
    eq_norm = mcolors.BoundaryNorm(eq_bounds, plt.get_cmap(cm).N)
    q_norm = mcolors.BoundaryNorm(q_bounds, plt.get_cmap(cm).N)
    cont_norm = mcolors.Normalize(v.min(), v.max())

    fig = plt.figure(figsize=(16, 7.5), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.3, 1])
    specs = [(cont_norm, "Continuous (linear Normalize)", None),
             (eq_norm, f"Equal-interval classes: {len(eq_bounds) - 1} bins of 5 °C (BoundaryNorm)", eq_bounds),
             (q_norm, f"Quantile classes: {len(q_bounds) - 1} deciles of land cells (BoundaryNorm)", q_bounds)]
    for k, (norm, name, b) in enumerate(specs):
        ax = map_axes(fig, gs[0, k])
        im = draw_field(ax, f, cm, norm)
        add_features(ax, labels="lb" if k == 0 else "b")
        ax.set_title(name, fontsize=10)
        panel_letter(ax, k)
        if k == 0:
            inset_legend(ax, [nodata_patch()])
        cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.92, pad=0.03, aspect=30,
                          label=TMAX_LABEL, ticks=b if b is not None else None, spacing="proportional")
        if b is not None:
            cb.ax.tick_params(labelsize=7, rotation=90 if k == 2 else 0)
        # class histogram: share of land cells per class
        hx = fig.add_subplot(gs[1, k])
        bins = np.linspace(v.min(), v.max(), 120)
        hx.hist(v, bins=bins, color="0.6", weights=np.full(v.size, 100 / v.size))
        if b is not None:
            counts, _ = np.histogram(v, bins=b)
            for lo, hi, c in zip(b[:-1], b[1:], counts):
                hx.axvspan(lo, hi, color=plt.get_cmap(cm)(norm((lo + hi) / 2)), alpha=0.35, lw=0)
                hx.axvline(lo, color="k", lw=0.6)
            hx.axvline(b[-1], color="k", lw=0.6)
            shares = 100 * counts / counts.sum()
            hx.set_title(f"Land share per class: min {shares.min():.1f} %, max {shares.max():.1f} %", fontsize=9)
        else:
            hx.set_title("Histogram of land-cell values (no classes)", fontsize=9)
        hx.set_xlabel(TMAX_LABEL)
        hx.set_ylabel("Share of land cells (%)")
        hx.grid(alpha=0.3)
        hx.text(0.01, 0.97, f"({chr(100 + k)})", transform=hx.transAxes, va="top", fontweight="bold")
    fig.suptitle(f"Discrete vs continuous colour mapping of $T_{{max}}$ - {date_title(i)}", fontsize=12)
    save_fig(fig, out)
    return eq_bounds, q_bounds


def _pr_panel(fig, pos, f, norm, cmap, title, letter, labels, extend):
    ax = map_axes(fig, pos)
    land = f.notnull()
    dry = land & (f == 0)
    # cream layer = land with 0 mm (dry); precipitation drawn on top with zeros masked
    draw_field(ax, dry.where(land).astype(float).where(dry), mcolors.ListedColormap([DRY_COLOR]),
               mcolors.Normalize(0, 1))
    im = draw_field(ax, f.where(f > 0), cmap, norm)
    add_features(ax, labels=labels)
    ax.set_title(title, fontsize=9.5)
    panel_letter(ax, letter)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.92, pad=0.03, aspect=30, label=PR_LABEL,
                      extend=extend)
    if letter % 3 == 0:
        inset_legend(ax, [nodata_patch(), Patch(facecolor=DRY_COLOR, edgecolor="0.4", lw=0.5,
                                                 label="Land with 0 mm (dry)")])
    return ax, cb


def fig_pr_log(pr, out):
    cm = "YlGnBu"
    gmax = float(pr.max())
    fig = plt.figure(figsize=(16, 9.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    for r, i in enumerate([2, 6]):  # D3 Debby, D7 Helene
        f = pr.sel(time=DATES[i])
        fmax = float(f.max())
        wet = f.values[(f.values > 0)]
        dt = date_title(i)
        _pr_panel(fig, gs[r, 0], f, mcolors.Normalize(0, fmax), cm, f"{dt}\nLinear 0-{fmax:.0f} mm (day maximum)",
                  3 * r, "lb", "neither")
        _pr_panel(fig, gs[r, 1], f, mcolors.Normalize(0, 25), cm, f"{dt}\nLinear, clipped at 25 mm", 3 * r + 1,
                  "b", "max")
        _, cb = _pr_panel(fig, gs[r, 2], f, mcolors.LogNorm(0.1, gmax), cm,
                          f"{dt}\nLogarithmic (LogNorm 0.1-{gmax:.0f} mm), zeros masked", 3 * r + 2, "b", "neither")
        cb.set_ticks([0.1, 0.3, 1, 3, 10, 30, 100, 300])
        cb.set_ticklabels(["0.1", "0.3", "1", "3", "10", "30", "100", "300"])
        print(f"  {DATES[i]}: wet land share {100 * wet.size / np.isfinite(f.values).sum():.1f}%, "
              f"median wet {np.median(wet):.1f} mm, p99 {np.percentile(wet, 99):.1f} mm, max {fmax:.1f}")
    fig.suptitle("Precipitation: linear vs logarithmic colour mapping (two hurricane landfall days)", fontsize=12)
    save_fig(fig, out)


def fig_diverging(tmmx, out):
    an = anomaly(tmmx)
    fig = plt.figure(figsize=(16, 9.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 3)
    lim = 15.0
    for r, i in enumerate([1, 6]):  # D2 heat peak, D7 Helene / western cool spell
        a = an.sel(time=DATES[i])
        specs = [("RdBu_r", mcolors.TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim), "Diverging RdBu_r, TwoSlopeNorm centred at 0"),
                 ("coolwarm", mcolors.TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim), "Diverging coolwarm, centred at 0"),
                 ("viridis", mcolors.Normalize(float(a.min()), float(a.max())), "Sequential viridis, min-max (no centre)")]
        for k, (cm, norm, name) in enumerate(specs):
            ax = map_axes(fig, gs[r, k])
            im = draw_field(ax, a, cm, norm)
            add_features(ax, labels="lb" if k == 0 else "b")
            ax.set_title(f"{date_title(i)}\n{name}", fontsize=9.5)
            panel_letter(ax, 3 * r + k)
            if k == 0:
                inset_legend(ax, [nodata_patch()])
            cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.92, pad=0.03, aspect=30,
                              label="$T_{max}$ anomaly vs Jul-Sep 2024 cell mean (°C)",
                              extend="both" if k < 2 else "neither")
            if k == 2:
                cb.ax.axvline(0, color="k", lw=1.2)
        v = a.values[np.isfinite(a.values)]
        print(f"  anomaly {DATES[i]}: mean {v.mean():+.2f}, warm share {100 * (v > 0).mean():.1f}%, "
              f">+5: {100 * (v > 5).mean():.1f}%, <-5: {100 * (v < -5).mean():.1f}%")
    fig.suptitle("Diverging vs sequential colour maps for the $T_{max}$ anomaly (daily value minus Jul-Sep 2024 mean of each cell)",
                 fontsize=12)
    save_fig(fig, out)


# ----------------------------------------------------------------------------------------------
# Global vs local normalisation (multi-panel + GIFs)
# ----------------------------------------------------------------------------------------------
def multipanel(da, out, cmap, norm_fn, cb_label, suptitle, per_panel_cb, extend="neither", log_ticks=None,
               dry_layer=False):
    fig = plt.figure(figsize=(17, 8.3 if per_panel_cb else 7.3), constrained_layout=True)
    gs = fig.add_gridspec(2, 4)
    ims = []
    for i in range(len(DATES)):
        f = da.sel(time=DATES[i])
        ax = map_axes(fig, gs[i // 4, i % 4])
        if dry_layer:
            land = f.notnull(); dry = land & (f == 0)
            draw_field(ax, dry.astype(float).where(dry), mcolors.ListedColormap([DRY_COLOR]), mcolors.Normalize(0, 1))
            f = f.where(f > 0)
        norm = norm_fn(f)
        im = draw_field(ax, f, cmap, norm)
        add_features(ax, labels=("l" if i % 4 == 0 else "") + ("b" if i >= 4 else ""), fontsize=6)
        ax.set_title(date_title(i).replace("  (", "\n("), fontsize=9)
        panel_letter(ax, i)
        ims.append(im)
        if i == 0:
            handles = [nodata_patch("No data")]
            if dry_layer:
                handles.append(Patch(facecolor=DRY_COLOR, edgecolor="0.4", lw=0.5, label="0 mm (dry)"))
            inset_legend(ax, handles, fontsize=6.5)
        if per_panel_cb:
            cb = fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.9, pad=0.02, aspect=25, extend=extend)
            cb.ax.tick_params(labelsize=7)
            cb.set_label(f"{cb_label}\nrange {norm.vmin:.1f}-{norm.vmax:.1f}", fontsize=7.5)
    if not per_panel_cb:
        cb = fig.colorbar(ims[0], ax=fig.axes, orientation="horizontal", shrink=0.5, pad=0.02, aspect=50,
                          label=cb_label, extend=extend)
        if log_ticks:
            cb.set_ticks(log_ticks); cb.set_ticklabels([f"{t:g}" for t in log_ticks])
    fig.suptitle(suptitle, fontsize=12.5)
    save_fig(fig, out)


def gif(da, out, cmap, norm_fn, cb_label, title, extend="neither", log_ticks=None, dry_layer=False, dpi=110):
    """1 frame per date at 1 fps; colourbar axis fixed in place, date in the title."""
    frames = []
    tmp = out.with_suffix(".frame.png")
    for i in range(len(DATES)):
        f = da.sel(time=DATES[i])
        fig = plt.figure(figsize=(9, 6.4))
        ax = map_axes(fig, 1, 1, 1)
        ax.set_position([0.04, 0.17, 0.92, 0.72])
        if dry_layer:
            land = f.notnull(); dry = land & (f == 0)
            draw_field(ax, dry.astype(float).where(dry), mcolors.ListedColormap([DRY_COLOR]), mcolors.Normalize(0, 1))
            f = f.where(f > 0)
        norm = norm_fn(f)
        im = draw_field(ax, f, cmap, norm)
        add_features(ax, labels="lb")
        ax.set_title(f"{title}\n{date_title(i)}", fontsize=11)
        cax = fig.add_axes([0.15, 0.08, 0.7, 0.03])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend=extend)
        cb.set_label(f"{cb_label}   (range {norm.vmin:.1f}-{norm.vmax:.1f})")
        if log_ticks:
            cb.set_ticks(log_ticks); cb.set_ticklabels([f"{t:g}" for t in log_ticks])
        fig.savefig(tmp, dpi=dpi, facecolor="white")
        plt.close(fig)
        frames.append(imageio.imread(tmp))
    tmp.unlink()
    imageio.mimsave(out, frames, duration=1000, loop=0)  # 1000 ms per frame = 1 fps
    print(f"[gif] {out.name} ({len(frames)} frames)")


def main():
    tmmx, pr = load_var("tmmx"), load_var("pr")
    gmin, gmax = float(tmmx.min()), float(tmmx.max())
    print(f"tmmx global (92-day) range {gmin:.2f}..{gmax:.2f} degC")

    fig_continuous(tmmx, IMG / "Fig_02_tmmx_continuous_colormaps.png")
    fig_lightness(IMG / "Fig_03_colormap_lightness_profiles.png")
    eq, q = fig_discrete(tmmx, IMG / "Fig_04_tmmx_discrete_equal_vs_quantile.png")
    print("  equal-interval bounds", eq, "\n  quantile bounds", q)
    fig_pr_log(pr, IMG / "Fig_05_pr_linear_vs_log.png")
    fig_diverging(tmmx, IMG / "Fig_06_tmmx_anomaly_diverging.png")

    glob = lambda f: mcolors.Normalize(gmin, gmax)                       # noqa: E731
    loc = lambda f: mcolors.Normalize(float(f.min()), float(f.max()))     # noqa: E731
    sub = tmmx.sel(time=DATES)
    multipanel(sub, IMG / "Fig_07_tmmx_global_norm.png", "inferno", glob, TMAX_LABEL,
               f"Global normalisation: one colour range for all dates (Jul-Sep 2024 min {gmin:.1f} °C to max {gmax:.1f} °C)",
               per_panel_cb=False)
    multipanel(sub, IMG / "Fig_08_tmmx_local_norm.png", "inferno", loc, "$T_{max}$ (°C)",
               "Local normalisation: each date stretched to its own min-max range (note the different colour bars)",
               per_panel_cb=True)
    prmax = float(pr.max())
    plog = lambda f: mcolors.LogNorm(0.1, prmax)                          # noqa: E731
    ticks = [0.1, 0.3, 1, 3, 10, 30, 100, 300]
    multipanel(pr.sel(time=DATES), IMG / "Fig_09_pr_global_log.png", "YlGnBu", plog, PR_LABEL + ", log scale",
               f"Precipitation on the 8 dates with one global logarithmic range (0.1-{prmax:.0f} mm/day; dry land in cream)",
               per_panel_cb=False, log_ticks=ticks, dry_layer=True)

    gif(sub, IMG / "Fig_07_tmmx_global_norm.gif", "inferno", glob, TMAX_LABEL, "S1 - $T_{max}$, GLOBAL normalisation")
    gif(sub, IMG / "Fig_08_tmmx_local_norm.gif", "inferno", loc, TMAX_LABEL, "S1 - $T_{max}$, LOCAL (per-date) normalisation")
    gif(pr.sel(time=DATES), IMG / "Fig_09_pr_global_log.gif", "YlGnBu", plog, PR_LABEL,
        "S1 - precipitation, global log normalisation", log_ticks=ticks, dry_layer=True)

    # per-date local ranges for the report table
    rows = [{"id": DATE_LABELS[i], "date": d, "local_min": float(tmmx.sel(time=d).min()),
             "local_max": float(tmmx.sel(time=d).max()), "global_min": gmin, "global_max": gmax,
             "share_of_global_range_%": 100 * float(tmmx.sel(time=d).max() - tmmx.sel(time=d).min()) / (gmax - gmin)}
            for i, d in enumerate(DATES)]
    pd.DataFrame(rows).round(2).to_csv(PROC_DIR / "s1_global_vs_local_ranges.csv", index=False)


if __name__ == "__main__":
    main()
