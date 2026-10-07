"""Summary statistics for every processed variable + evidence for choosing the 8 analysis dates.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083).

Outputs
  data/processed/stats_per_day.csv     per-timestep min/max/mean/std/percentiles for each variable
  data/processed/stats_global.csv      the same over the whole Jul-Sep 2024 period
  data/processed/daily_evidence.csv    daily regional indicators used to pick event dates
  data/processed/selected_dates.csv    the 8 chosen dates with the rule that selected them
  images/Fig_01_date_selection_timeline.png

Run: python scivis/common/stats_and_dates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_gridmet import PROC_DIR, REPO_ROOT, VARS, load_var  # noqa: E402
from plot_utils import DATES, DATE_LABELS, EVENTS, save_fig  # noqa: E402

PCTS = [1, 5, 25, 50, 75, 95, 99]

# Regional boxes (lat_min, lat_max, lon_min, lon_max) used as event indicators.
REGIONS = {
    "west_heat": (31.0, 49.4, -124.8, -104.0),     # US West, July heat wave
    "tx_coast_beryl": (27.0, 32.0, -97.8, -93.5),  # Texas Gulf coast + E Texas (Beryl)
    "fl_ga_sc_debby": (26.0, 34.0, -84.0, -78.5),  # W Florida -> Georgia / S Carolina (Debby)
    "louisiana_francine": (28.8, 33.0, -93.8, -88.5),  # Louisiana / Mississippi (Francine)
    "southeast_helene": (29.0, 37.0, -86.0, -80.0),    # FL Big Bend -> GA -> Carolinas (Helene)
}


def box(da, r):
    la0, la1, lo0, lo1 = REGIONS[r]
    return da.sel(lat=slice(la0, la1), lon=slice(lo0, lo1))


def stats_tables() -> None:
    rows_day, rows_glob = [], []
    for abbr in VARS:
        da = load_var(abbr)
        arr = da.values.reshape(da.sizes["time"], -1)
        units = da.attrs["units"]
        for i, t in enumerate(pd.to_datetime(da.time.values)):
            x = arr[i][~np.isnan(arr[i])]
            row = {"variable": abbr, "units": units, "date": t.date(), "n_valid": x.size,
                   "min": x.min(), "max": x.max(), "mean": x.mean(), "std": x.std()}
            row.update({f"p{p}": v for p, v in zip(PCTS, np.percentile(x, PCTS))})
            rows_day.append(row)
        x = arr[~np.isnan(arr)]
        row = {"variable": abbr, "units": units, "n_valid": x.size, "min": x.min(), "max": x.max(),
               "mean": x.mean(), "std": x.std()}
        row.update({f"p{p}": v for p, v in zip(PCTS, np.percentile(x, PCTS))})
        if abbr == "pr":
            row["frac_zero"] = float((x == 0).mean())
        rows_glob.append(row)
        print(f"[stats] {abbr}: global min={row['min']:.2f} max={row['max']:.2f} mean={row['mean']:.2f} {units}")
    pd.DataFrame(rows_day).round(3).to_csv(PROC_DIR / "stats_per_day.csv", index=False)
    pd.DataFrame(rows_glob).round(3).to_csv(PROC_DIR / "stats_global.csv", index=False)


def daily_evidence() -> pd.DataFrame:
    tmmx, pr, vs = load_var("tmmx"), load_var("pr"), load_var("vs")
    ev = pd.DataFrame(index=pd.to_datetime(tmmx.time.values))
    ev.index.name = "date"
    ev["conus_tmmx_mean"] = tmmx.mean(["lat", "lon"]).values
    ev["conus_tmmx_max"] = tmmx.max(["lat", "lon"]).values
    w = box(tmmx, "west_heat")
    ev["west_frac_tmmx_ge_40C"] = ((w >= 40).sum(["lat", "lon"]) / w.notnull().sum(["lat", "lon"])).values
    ev["conus_vs_max"] = vs.max(["lat", "lon"]).values
    ev["conus_vs_p99"] = vs.quantile(0.99, dim=["lat", "lon"]).values
    ev["conus_pr_mean"] = pr.mean(["lat", "lon"]).values
    for r in [k for k in REGIONS if k != "west_heat"]:
        p, s = box(pr, r), box(vs, r)
        ev[f"{r}_pr_mean"] = p.mean(["lat", "lon"]).values
        ev[f"{r}_pr_max"] = p.max(["lat", "lon"]).values
        ev[f"{r}_vs_max"] = s.max(["lat", "lon"]).values
        ev[f"{r}_vs_mean"] = s.mean(["lat", "lon"]).values
    ev.round(3).to_csv(PROC_DIR / "daily_evidence.csv")
    return ev


def plot_timeline(ev: pd.DataFrame, out: Path) -> None:
    """Fig 1: daily indicators with the 8 chosen dates marked."""
    sel = pd.to_datetime(DATES)
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True, constrained_layout=True)
    ax = axes[0]
    ax.plot(ev.index, ev["conus_tmmx_max"], color="#b2182b", label="CONUS maximum of $T_{max}$")
    ax.set_ylabel("$T_{max}$ (°C)")
    ax2 = ax.twinx()
    ax2.plot(ev.index, 100 * ev["west_frac_tmmx_ge_40C"], color="#ef8a62", ls="--",
             label="Western US land area with $T_{max}$ ≥ 40 °C")
    ax2.set_ylabel("Area ≥ 40 °C (%)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9, framealpha=0.9)
    ax.set_title("(a) Heat: CONUS hottest cell and western-US area above 40 °C", loc="left", fontsize=11, pad=22)

    ax = axes[1]
    cols = {"tx_coast_beryl": ("#1b9e77", "Texas coast (Beryl box)"),
            "fl_ga_sc_debby": ("#d95f02", "FL–GA–SC (Debby box)"),
            "louisiana_francine": ("#7570b3", "Louisiana (Francine box)"),
            "southeast_helene": ("#e7298a", "Southeast (Helene box)")}
    for r, (c, lab) in cols.items():
        ax.plot(ev.index, ev[f"{r}_pr_mean"], color=c, label=lab)
    ax.set_ylabel("Regional mean\nprecipitation (mm/day)")
    ax.legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
    ax.set_title("(b) Rain: area-mean daily precipitation in four hurricane landfall boxes", loc="left", fontsize=11)

    ax = axes[2]
    for r, (c, lab) in cols.items():
        ax.plot(ev.index, ev[f"{r}_vs_max"], color=c, label=lab)
    ax.set_ylabel("Regional maximum\ndaily-mean wind (m/s)")
    ax.legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
    ax.set_title("(c) Wind: highest daily-mean 10 m wind speed in the same boxes", loc="left", fontsize=11)

    ax = axes[3]
    ax.plot(ev.index, ev["conus_vs_max"], color="#4d4d4d", label="CONUS maximum")
    ax.plot(ev.index, ev["conus_vs_p99"], color="#878787", ls="--", label="CONUS 99th percentile")
    ax.set_ylabel("Daily-mean 10 m\nwind speed (m/s)")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.set_title("(d) Wind over the whole domain", loc="left", fontsize=11)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_xlabel("Date (2024; gridMET day ends 07 UTC next calendar day)")

    for a in axes:
        for d in sel:
            a.axvline(d, color="k", lw=0.8, alpha=0.35, zorder=0)
        a.grid(alpha=0.25)
    # date labels above the top panel only, so they never collide with curves
    for i, (d, lab) in enumerate(zip(sel, DATE_LABELS)):
        # adjacent dates (26/27 Sep) are pushed apart horizontally so the labels never overlap
        close_prev = i > 0 and (d - sel[i - 1]).days < 3
        close_next = i < len(sel) - 1 and (sel[i + 1] - d).days < 3
        ha = "right" if close_next else ("left" if close_prev else "center")
        axes[0].annotate(f"{lab} {d:%d %b}", xy=(d, 1.0), xycoords=("data", "axes fraction"),
                         xytext=(-2 if close_next else (2 if close_prev else 0), 4),
                         textcoords="offset points", ha=ha, va="bottom", fontsize=8.5, fontweight="bold")
    fig.suptitle(" Daily evidence used to select the 8 analysis dates (vertical lines), gridMET Jul–Sep 2024",
                 fontsize=13)
    save_fig(fig, out)


def write_selected(ev: pd.DataFrame) -> None:
    rows = []
    for d, lab, evn in zip(DATES, DATE_LABELS, EVENTS):
        e = ev.loc[d]
        rows.append({"id": lab, "date": d, "role": evn,
                     "conus_tmmx_max_C": e["conus_tmmx_max"],
                     "west_area_ge40C_pct": 100 * e["west_frac_tmmx_ge_40C"],
                     "tx_pr_mean": e["tx_coast_beryl_pr_mean"], "fl_pr_mean": e["fl_ga_sc_debby_pr_mean"],
                     "la_pr_mean": e["louisiana_francine_pr_mean"], "se_pr_mean": e["southeast_helene_pr_mean"],
                     "conus_vs_max": e["conus_vs_max"]})
    df = pd.DataFrame(rows).round(2)
    df.to_csv(PROC_DIR / "selected_dates.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    stats_tables()
    ev = daily_evidence()
    write_selected(ev)
    if DATES:
        plot_timeline(ev, REPO_ROOT / "images" / "Fig_01_date_selection_timeline.png")
