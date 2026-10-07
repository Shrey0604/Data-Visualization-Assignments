"""I3 - Horizon plots and ridgeline plots of the A1 Reddit top-post data (Matplotlib, manual implementations).

Owner: Shrey Modi (BT2024125)

Horizon plot (implemented here, no library): x_t -> centre on a baseline b (deviation d_t = x_t - b), choose a band
height h = max|d| / N (shared by all rows of a figure so rows are comparable), split |d| into N bands
(band k holds clip(|d| - k*h, 0, h)), fold the negative part up onto the same axis and draw band k with the
k-th saturation of a diverging palette (blue = below baseline, red = above).

Ridgelines: Gaussian KDE per group with ONE fixed bandwidth (stated in each title), shared x-axis, groups ordered by
median (or time), overlap factor 1.8.

Figures (images/):
  Fig_35_horizon_construction.png     band splitting / folding, band-count comparison (N = 1..4)
  Fig_36_horizon_topics_monthly.png   8 topics, monthly top-post counts, 2016-01 .. 2024-08
  Fig_37_line_vs_horizon.png          same 8 series as overlapping lines, small-multiple lines, horizon (same height)
  Fig_38_horizon_topics_quarter_year.png  temporal granularity: quarterly vs yearly
  Fig_39_horizon_subreddits_monthly.png   50 subreddits, monthly median log10(score) anomaly
  Fig_40_ridgeline_subreddits_score.png   log10(score) by subreddit (50), ordered by median
  Fig_41_ridgeline_years_score.png        log10(score) by year (2015-2024), ordered by time
  Fig_42_ridgeline_topics_comments.png    log10(comments + 1) by topic, ordered by median

Run: python infovis/i3_horizon_ridgeline/run.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
A1 = ROOT / "data" / "processed" / "a1"
PROC = ROOT / "data" / "processed"
IMG = ROOT / "images"
DPI = 300
TOPICS = ["Creative and lifestyle", "Entertainment and media", "Knowledge and curiosity", "Memes and GIFs",
          "News, science and tech", "Photos and curiosities", "Q&A and advice", "Text humour and stories"]
TOPIC_COL = dict(zip(TOPICS, plt.get_cmap("tab10").colors))
plt.rcParams.update({"font.size": 9})


def save(fig, out):
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[fig]", out.name)


def band_colors(n):
    """n increasingly saturated reds (above baseline) and blues (below), from the RdBu diverging palette."""
    cm = plt.get_cmap("RdBu_r")
    pos = [cm(0.55 + 0.45 * (k + 1) / n) for k in range(n)]
    neg = [cm(0.45 - 0.45 * (k + 1) / n) for k in range(n)]
    return pos, neg


def horizon(ax, t, y, baseline, h, n_bands, step=False):
    """Draw one horizon row on ax (y-range [0, h]). Returns the folded band arrays (for testing)."""
    d = np.asarray(y, float) - baseline
    pos_c, neg_c = band_colors(n_bands)
    kw = dict(step="mid") if step else {}
    bands = []
    for k in range(n_bands):
        up = np.clip(d - k * h, 0, h)          # k-th slice of the positive part
        dn = np.clip(-d - k * h, 0, h)         # k-th slice of the negative part, mirrored upward
        ax.fill_between(t, 0, up, color=pos_c[k], lw=0, **kw)
        ax.fill_between(t, 0, dn, color=neg_c[k], lw=0, **kw)
        bands.append((up, dn))
    ax.set_ylim(0, h)
    ax.set_yticks([])
    return bands


def horizon_figure(series: pd.DataFrame, t, out, title, n_bands=3, row_h=0.42, label_w=2.3, unit="",
                   baseline="mean", step=False, label_colors=None, xfmt=None, events=None, extra_note="", h=None):
    rows = list(series.index)
    base = series.mean(axis=1) if baseline == "mean" else series.median(axis=1)
    dev = series.sub(base, axis=0)
    hmax = float(np.nanmax(np.abs(dev.values)))
    clipped = h is not None and hmax > n_bands * h   # fixed band height: larger deviations saturate the last band
    h = h if h is not None else hmax / n_bands
    fig_h = 1.2 + row_h * len(rows) + 0.9
    fig, axes = plt.subplots(len(rows), 1, figsize=(13, fig_h), sharex=True,
                             gridspec_kw={"hspace": 0.06, "left": label_w / 13, "right": 0.985,
                                          "top": 1 - 0.95 / fig_h, "bottom": 0.75 / fig_h})
    axes = np.atleast_1d(axes)
    for ax, r in zip(axes, rows):
        horizon(ax, t, series.loc[r].values, base[r], h, n_bands, step=step)
        ax.text(-0.006, 0.5, r, transform=ax.transAxes, ha="right", va="center", fontsize=8.5 if len(rows) < 20 else 7,
                color=(label_colors or {}).get(r, "k"))
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="x", length=0)
        if events:
            for ev in events:
                ax.axvline(ev, color="0.25", lw=0.6, ls=":")
    axes[-1].tick_params(axis="x", length=3)
    if xfmt:
        axes[-1].xaxis.set_major_locator(xfmt[0]); axes[-1].xaxis.set_major_formatter(xfmt[1])
    axes[-1].set_xlabel("Time (UTC)")
    pos_c, neg_c = band_colors(n_bands)
    def lab(k, sign):
        lo, hi = k * h, (k + 1) * h
        if clipped and k == n_bands - 1:
            return f"dev ≤ {-lo:+.2f}" if sign < 0 else f"dev > {lo:+.2f}"
        return f"{-hi:+.2f} ≤ dev < {-lo:+.2f}" if sign < 0 else f"{lo:+.2f} < dev ≤ {hi:+.2f}"
    handles = [Patch(color=neg_c[k], label=lab(k, -1)) for k in range(n_bands)][::-1] + \
              [Patch(color=pos_c[k], label=lab(k, 1)) for k in range(n_bands)]
    fig.legend(handles=handles, loc="upper center", ncol=2 * n_bands, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.5 + label_w / 26, 1 - 0.42 / fig_h), title=f"Deviation from each row's {baseline} ({unit}); "
               f"band height h = {h:.2f} {unit}, {n_bands} bands, darker = larger |deviation|", title_fontsize=8)
    fig.suptitle(title + (f"\n{extra_note}" if extra_note else ""), fontsize=11.5, y=1 - 0.05 / fig_h, va="top")
    save(fig, out)
    return h, dev


# ----------------------------------------------------------------------------------------------
def load():
    m = pd.read_csv(A1 / "ts_monthly_posts_by_category.csv", index_col=0)
    m.columns = pd.PeriodIndex(m.columns, freq="M").to_timestamp()
    q = pd.read_csv(A1 / "ts_quarterly_posts_by_category.csv", index_col=0)
    q.columns = pd.PeriodIndex(q.columns, freq="Q").to_timestamp()
    yr = pd.read_csv(A1 / "ts_yearly_posts_by_category.csv", index_col=0)
    ms = pd.read_csv(A1 / "ts_monthly_median_log10score_by_subreddit.csv", index_col=0)
    ms.columns = pd.PeriodIndex(ms.columns, freq="M").to_timestamp()
    posts = pd.read_csv(A1 / "posts_clean.csv", usecols=["subreddit", "category", "year", "score", "num_comments",
                                                         "log10_score", "post_type"])
    return m.loc[TOPICS], q.loc[TOPICS], yr.loc[TOPICS], ms, posts


def fig_construction(m, out):
    s = m.loc["Q&A and advice"]
    t = s.index
    b = s.mean()
    d = s - b
    fig, axes = plt.subplots(3, 3, figsize=(15, 7.6), constrained_layout=True,
                             gridspec_kw={"height_ratios": [1.6, 1, 1]})
    ax = axes[0, 0]
    ax.plot(t, s, color="k", lw=1)
    ax.axhline(b, color="0.4", ls="--", lw=1)
    ax.fill_between(t, b, s, where=s >= b, color="#d6604d", alpha=0.6, interpolate=True)
    ax.fill_between(t, b, s, where=s < b, color="#4393c3", alpha=0.6, interpolate=True)
    ax.set_title(f"(a) Raw series and baseline (mean = {b:.1f} posts/month)", fontsize=10)
    ax.set_ylabel("Top posts per month")
    n = 3
    h = np.abs(d).max() / n
    ax = axes[0, 1]
    pos_c, neg_c = band_colors(n)
    for k in range(n):
        ax.fill_between(t, k * h, np.clip(d, k * h, (k + 1) * h), where=d > k * h, color=pos_c[k], lw=0, interpolate=True)
        ax.fill_between(t, -k * h, np.clip(d, -(k + 1) * h, -k * h), where=d < -k * h, color=neg_c[k], lw=0, interpolate=True)
        ax.axhline(k * h, color="0.5", lw=0.5, ls=":"); ax.axhline(-k * h, color="0.5", lw=0.5, ls=":")
    ax.axhline(n * h, color="0.5", lw=0.5, ls=":"); ax.axhline(-n * h, color="0.5", lw=0.5, ls=":")
    ax.set_title(f"(b) Deviation split into {n} bands of h = {h:.1f} posts", fontsize=10)
    ax.set_ylabel("Deviation from baseline (posts/month)")
    ax = axes[0, 2]
    for k in range(n):
        ax.fill_between(t, 0, np.clip(d - k * h, 0, h), color=pos_c[k], lw=0)
        ax.fill_between(t, 0, np.clip(-d - k * h, 0, h), color=neg_c[k], lw=0)
    ax.set_ylim(0, h)
    ax.set_title("(c) Bands collapsed onto [0, h]; negatives mirrored up", fontsize=10)
    ax.set_ylabel("Folded height (posts/month)")
    for a in axes[0]:
        a.xaxis.set_major_locator(mdates.YearLocator(2)); a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        a.grid(alpha=0.25); a.set_xlabel("Month")
    # band count comparison (rows 2-3): same series, N = 1..4 + 6, height kept equal
    letters = "defghi"
    for k, nb in enumerate([1, 2, 3, 4, 6, None]):
        ax = axes[1 + k // 3, k % 3]
        if nb is None:
            ax.axis("off")
            ax.text(0.02, 0.95,
                    "Band-count choice\n"
                    "N = 1: a coloured area chart squeezed into one row; the\n"
                    "      2019-20 peak flattens and small dips are invisible.\n"
                    "N = 2-3: each band keeps ~1/3 of the range, so the peak\n"
                    "      reads as dark red and the 2023-24 deficit as dark blue.\n"
                    "N ≥ 4: more resolution but four or more shades per hue\n"
                    "      are hard to tell apart (Heer et al. 2009 found\n"
                    "      accuracy falls as bands increase).\n"
                    "We use N = 3 for all horizon figures.", transform=ax.transAxes, va="top", fontsize=9,
                    family="monospace")
            continue
        horizon(ax, t, s.values, b, np.abs(d).max() / nb, nb)
        ax.set_title(f"({letters[k]}) N = {nb} band{'s' if nb > 1 else ''}, h = {np.abs(d).max() / nb:.1f} posts", fontsize=10)
        ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlabel("Month")
    fig.suptitle("Horizon-plot construction for 'Q&A and advice' monthly top-post counts (2016-01 to 2024-08): "
                 "centre → split into bands → fold negatives → overlay", fontsize=12)
    save(fig, out)


def fig_line_vs_horizon(m, out, n_bands=3):
    t = m.columns
    fig = plt.figure(figsize=(16, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(len(TOPICS), 3, width_ratios=[1, 1, 1])
    ax = fig.add_subplot(gs[:, 0])
    for r in TOPICS:
        ax.plot(t, m.loc[r], color=TOPIC_COL[r], lw=1, label=r)
    ax.set_ylabel("Top posts per month"); ax.set_xlabel("Month")
    ax.set_title("(a) Overlapping line chart (8 series, one axis)", fontsize=10)
    ax.legend(fontsize=7, loc="upper left", ncol=1, framealpha=0.9)
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ymax = m.values.max()
    base = m.mean(axis=1)
    h = np.abs(m.sub(base, axis=0).values).max() / n_bands
    for i, r in enumerate(TOPICS):
        a = fig.add_subplot(gs[i, 1])
        a.fill_between(t, 0, m.loc[r], color=TOPIC_COL[r], alpha=0.5, lw=0)
        a.plot(t, m.loc[r], color=TOPIC_COL[r], lw=0.8)
        a.set_ylim(0, ymax); a.set_yticks([0, int(ymax)]); a.tick_params(labelsize=6)
        a.text(0.01, 0.92, r, transform=a.transAxes, fontsize=7, va="top")
        a.set_xticks([]) if i < len(TOPICS) - 1 else a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        if i == 0:
            a.set_title("(b) Small-multiple line charts (shared y, 0-%d)" % ymax, fontsize=10)
        b = fig.add_subplot(gs[i, 2])
        horizon(b, t, m.loc[r].values, base[r], h, n_bands)
        b.text(0.01, 0.92, r, transform=b.transAxes, fontsize=7, va="top",
               bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.5))
        if i < len(TOPICS) - 1:
            b.set_xticks([])
        else:
            b.xaxis.set_major_locator(mdates.YearLocator(2)); b.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        if i == 0:
            b.set_title(f"(c) Horizon rows (3 bands, h = {h:.1f} posts; red above, blue below own mean)", fontsize=10)
    fig.suptitle("Same 8 monthly series in the same vertical space: overlap vs small multiples vs horizon", fontsize=12)
    save(fig, out)
    # vertical space efficiency: effective resolution per row (pixels per post) at equal row height
    return {"row_height_share": 1 / len(TOPICS), "small_multiple_scale_posts": ymax, "horizon_band_posts": h,
            "virtual_resolution_gain": ymax / h}


def ridgeline(groups: list[tuple[str, np.ndarray]], out, title, xlabel, bw, xlim, colors=None, overlap=1.8,
              row_h=0.32, order_note="", label_fs=8, med_label=True):
    xs = np.linspace(*xlim, 600)
    n = len(groups)
    fig_h = 1.1 + row_h * n + 0.6
    fig, ax = plt.subplots(figsize=(11, fig_h))
    fig.subplots_adjust(left=0.2, right=0.97, top=1 - 0.85 / fig_h, bottom=0.6 / fig_h)
    dens = []
    for name, v in groups:
        v = v[np.isfinite(v)]
        z = (xs[:, None] - v[None, :]) / bw
        dens.append(np.exp(-0.5 * z ** 2).sum(1) / (v.size * bw * np.sqrt(2 * np.pi)))
    peak = max(d.max() for d in dens)
    for i, ((name, v), d) in enumerate(zip(groups, dens)):
        y0 = (n - 1 - i)
        yy = y0 + overlap * d / peak
        c = (colors or {}).get(name, "#4c72b0")
        ax.fill_between(xs, y0, yy, color=c, alpha=0.75, lw=0, zorder=2 * i)
        ax.plot(xs, yy, color="k", lw=0.6, zorder=2 * i + 1)
        ax.axhline(y0, color="0.6", lw=0.4, zorder=2 * i + 1)
        med = np.median(v)
        ax.plot([med, med], [y0, y0 + overlap * np.interp(med, xs, d) / peak], color="white", lw=1.2, zorder=2 * i + 1)
        ax.text(xlim[0] - 0.01 * (xlim[1] - xlim[0]), y0 + 0.12, f"{name} (n = {v.size:,})", ha="right", va="bottom",
                fontsize=label_fs, color="k")
    ax.set_yticks([])
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.3, n - 1 + overlap + 0.2)
    ax.set_xlabel(xlabel)
    for s in ["left", "right", "top"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    ax.set_title(f"{title}\nGaussian KDE, fixed bandwidth h = {bw:g} for every group; white tick = median; {order_note}",
                 fontsize=11)
    save(fig, out)


def main():
    m, q, yr, ms, posts = load()
    stats = {}
    fig_construction(m, IMG / "Fig_35_horizon_construction.png")

    h, dev = horizon_figure(m, m.columns, IMG / "Fig_36_horizon_topics_monthly.png",
                            "Horizon plot: monthly all-time-top posts per topic category (Jan 2016 - Aug 2024, 104 months)",
                            unit="posts/month", label_colors=TOPIC_COL,
                            xfmt=(mdates.YearLocator(), mdates.DateFormatter("%Y")),
                            events=[pd.Timestamp("2020-03-01"), pd.Timestamp("2023-06-01")],
                            extra_note="dotted lines: Mar 2020 (COVID-19 lockdowns), Jun 2023 (Reddit API protest / blackout)")
    stats["monthly_band_h"] = h
    peak = m.idxmax(axis=1).dt.strftime("%Y-%m")
    stats["monthly_peak_month"] = peak.to_dict()
    stats["monthly_peak_value"] = m.max(axis=1).to_dict()
    stats["monthly_mean"] = m.mean(axis=1).round(2).to_dict()

    stats["line_vs_horizon"] = fig_line_vs_horizon(m, IMG / "Fig_37_line_vs_horizon.png")

    # granularity: quarterly vs yearly, side by side as two horizon figures merged into one image
    from PIL import Image
    q_mid = q.columns + pd.Timedelta(days=45)   # plot each quarter at its centre (step="mid")
    hq, _ = horizon_figure(q, q_mid, IMG / "_tmp_q.png", "(a) Quarterly top-post counts per topic (2016 Q1 - 2024 Q3*)",
                           unit="posts/quarter", step=True, label_colors=TOPIC_COL,
                           xfmt=(mdates.YearLocator(), mdates.DateFormatter("%Y")),
                           extra_note="*2024 Q3 is partial (data end 11 Sep 2024)")
    yrs = yr.loc[:, [c for c in yr.columns if 2014 <= int(c) <= 2024]]
    yrs.columns = pd.to_datetime([f"{c}-07-01" for c in yrs.columns])
    hy, _ = horizon_figure(yrs, yrs.columns, IMG / "_tmp_y.png", "(b) Yearly top-post counts per topic (2014 - 2024*)",
                           unit="posts/year", step=True, label_colors=TOPIC_COL,
                           xfmt=(mdates.YearLocator(), mdates.DateFormatter("%Y")),
                           extra_note="*2024 is partial (Jan - 11 Sep)")
    ia, ib = Image.open(IMG / "_tmp_q.png"), Image.open(IMG / "_tmp_y.png")
    W = max(ia.width, ib.width)
    canvas = Image.new("RGB", (W, ia.height + ib.height + 60), "white")
    canvas.paste(ia, (0, 0)); canvas.paste(ib, (0, ia.height + 60))
    canvas.save(IMG / "Fig_38_horizon_topics_quarter_year.png", dpi=(DPI, DPI))
    (IMG / "_tmp_q.png").unlink(); (IMG / "_tmp_y.png").unlink()
    print("[fig] Fig_38_horizon_topics_quarter_year.png")
    stats["quarter_band_h"], stats["year_band_h"] = hq, hy

    # 50 subreddits, monthly median log10(score) anomaly (months without a top post = gap -> 0 deviation)
    sub_cat = posts.groupby("subreddit").category.first()
    order = sorted(ms.index, key=lambda s: (TOPICS.index(sub_cat[s]), s.lower()))
    msd = ms.loc[order]
    med = posts.groupby("subreddit").log10_score.median()
    filled = msd.T.fillna(med).T   # empty months = the subreddit's own median (zero deviation, drawn blank)
    hs, devs = horizon_figure(filled, filled.columns, IMG / "Fig_39_horizon_subreddits_monthly.png",
                              "Horizon plot: monthly median log10(score) of each subreddit's top posts relative to its overall median",
                              n_bands=3, row_h=0.2, label_w=2.6, unit="dex", baseline="median", h=0.15,
                              label_colors={s: TOPIC_COL[sub_cat[s]] for s in order},
                              xfmt=(mdates.YearLocator(), mdates.DateFormatter("%Y")),
                              extra_note="rows grouped by topic (label colour); months with no top post are blank; "
                                         "h = 0.15 dex (x1.41); |deviations| beyond 0.45 dex (x2.8) saturate the darkest band")
    stats["subreddit_band_h"] = hs
    yearly_dev = devs.T.groupby(devs.columns.year).mean().T
    stats["subreddits_peak_year"] = yearly_dev.idxmax(axis=1).value_counts().sort_index().to_dict()

    # ridgelines
    bw = 0.06
    g = posts.groupby("subreddit").log10_score
    order = g.median().sort_values(ascending=False).index
    ridgeline([(s, posts.loc[posts.subreddit == s, "log10_score"].values) for s in order],
              IMG / "Fig_40_ridgeline_subreddits_score.png",
              "Ridgeline: distribution of log10(score) of each subreddit's ~1,000 all-time top posts",
              "log10(score)   (3 = 1k, 4 = 10k, 5 = 100k upvotes)", bw, (3.0, 5.75),
              colors={s: TOPIC_COL[sub_cat[s]] for s in order}, row_h=0.2, overlap=2.2,
              order_note="ordered by median (highest at top); colour = topic", label_fs=7)
    years = list(range(2015, 2025))
    ridgeline([(str(y), posts.loc[posts.year == y, "log10_score"].values) for y in years],
              IMG / "Fig_41_ridgeline_years_score.png",
              "Ridgeline: distribution of log10(score) of all top posts by posting year (2015-2024; 2011-14 have 176 posts)",
              "log10(score)   (3 = 1k, 4 = 10k, 5 = 100k upvotes)", bw, (3.0, 5.75),
              colors={str(y): plt.get_cmap("viridis")((y - 2015) / 9) for y in years}, row_h=0.42, overlap=1.6,
              order_note="ordered by time (oldest at top)")
    posts["lc"] = np.log10(posts.num_comments + 1)
    gc = posts.groupby("category").lc.median().sort_values(ascending=False).index
    ridgeline([(c, posts.loc[posts.category == c, "lc"].values) for c in gc],
              IMG / "Fig_42_ridgeline_topics_comments.png",
              "Ridgeline: distribution of log10(comments + 1) per post, by topic category (all 49,266 posts)",
              "log10(comments + 1)   (2 = 100, 3 = 1k, 4 = 10k comments)", 0.08, (0, 5.0),
              colors=TOPIC_COL, row_h=0.55, overlap=1.5, order_note="ordered by median (highest at top)")
    summ = {"by_subreddit_median_log10": g.median().sort_values(ascending=False).round(3).to_dict(),
            "by_year_median_log10": posts.groupby("year").log10_score.median().round(3).to_dict(),
            "by_year_n": posts.year.value_counts().sort_index().to_dict(),
            "by_topic_median_comments": posts.groupby("category").num_comments.median().to_dict()}
    stats.update(summ)
    pd.Series({k: str(v) for k, v in stats.items()}).to_csv(PROC / "i3_stats.csv", header=["value"])
    for k, v in stats.items():
        print(k, ":", v)


if __name__ == "__main__":
    main()
