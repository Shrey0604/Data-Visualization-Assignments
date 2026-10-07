"""S3 - Quiver plots and streamlines of gridMET 10 m wind, Jul-Sep 2024.

Owner: Parthsarati Samanta (BT2024083)

u, v come from load_gridmet.wind_components: u = -vs*sin(th), v = -vs*cos(th) (vectors point where the wind blows TO).
Vectors are given in geographic east/north components; cartopy rotates them into the Lambert Conformal map
(transform=PlateCarree), so arrow and streamline directions are correct on the projected map.

Figures (images/):
  Fig_18_quiver_stride.png             plain striding every 10th / 20th / 40th cell (proportional arrows)
  Fig_19_quiver_stride_vs_block.png    striding vs block averaging + aliasing statistics
  Fig_20_quiver_proportional_vs_uniform.png  magnitude-proportional vs same-length arrows coloured by speed
  Fig_21_hurricane_zooms.png           regional zooms of the four landfalls (speed background + arrows)
  Fig_22_streamlines_vs_quiver.png     quiver vs streamplot (width + colour by speed)
  Fig_23_streamline_seeding.png        uniform-grid, random and feature-based seeds (Helene zoom)
  Fig_24_wind_evolution.png/.gif       8 dates, speed background + block-averaged arrows
Tables (data/processed/): s3_aliasing.csv, s3_quiver_sampling.csv, s3_seeding.csv, s3_regional_wind.csv

Run: python scivis/s3_quiver_streamlines/run.py
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
import xarray as xr
from matplotlib import colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from scipy.ndimage import gaussian_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scivis" / "common"))
from load_gridmet import PROC_DIR, load_var  # noqa: E402
from maps import PC, PROJ, add_features, draw_field, map_axes, nodata_patch  # noqa: E402
from plot_utils import DATES, DATE_LABELS, EVENTS, save_fig  # noqa: E402

IMG = ROOT / "images"
SPEED_LABEL = "Daily-mean 10 m wind speed (m/s)"
SPEED_CMAP = "GnBu"
SPEED_NORM = mcolors.Normalize(0, 14)
REF = 10.0  # quiverkey reference speed (m/s)
SEED = 7
R_EARTH = 6.371e6
REGIONS = {  # lon0, lon1, lat0, lat1
    "Beryl (TX coast)": ([-100.5, -87.5, 25.8, 37.0], 0),
    "Debby (FL / GA / SC)": ([-89.0, -75.5, 24.5, 35.5], 2),
    "Francine (LA / MS)": ([-97.0, -83.5, 27.0, 36.0], 5),
    "Helene (FL Big Bend -> SE)": ([-90.0, -75.5, 25.0, 38.5], 6),
}
HELENE = REGIONS["Helene (FL Big Bend -> SE)"][0]
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5})


def date_title(i):
    return f"{DATE_LABELS[i]}  {pd.Timestamp(DATES[i]):%d %b %Y}  ({EVENTS[i]})"


def panel_letter(ax, k):
    ax.text(0.01, 0.99, f"({chr(97 + k)})", transform=ax.transAxes, ha="left", va="top", fontsize=10,
            fontweight="bold", zorder=9, bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5))


def inset_legend(ax, handles, fontsize=6.5, loc="lower left"):
    ax.legend(handles=handles, loc=loc, fontsize=fontsize, framealpha=0.92, borderpad=0.4,
              handlelength=1.4).set_zorder(10)


def load_dates() -> xr.Dataset:
    w = xr.open_dataset(PROC_DIR / "gridmet_wind_2024JAS.nc").sel(time=DATES).load()
    w["vs"] = load_var("vs").sel(time=DATES)
    return w


def stride(ds, k):
    """Plain sub-sampling: every k-th cell (offset k//2 so samples sit inside blocks)."""
    return ds.isel(lat=slice(k // 2, None, k), lon=slice(k // 2, None, k))


def block_mean(ds, k, min_valid=0.5):
    """k x k block average of u and v (NaN-aware); blocks with < min_valid land share are dropped."""
    c = ds.coarsen(lat=k, lon=k, boundary="trim")
    out = c.mean()  # float mean skips NaN by default
    frac = ds["u"].notnull().coarsen(lat=k, lon=k, boundary="trim").mean()
    return out.where(frac >= min_valid)


def quiver(ax, d, scale=None, color="k", C=None, cmap=None, norm=None, width=0.0022, normalise=False, key=True,
           key_xy=(0.86, 0.035), zorder=6):
    lon2, lat2 = np.meshgrid(d.lon.values, d.lat.values)
    u, v = d["u"].values, d["v"].values
    if normalise:
        sp = np.hypot(u, v)
        u, v = u / np.where(sp > 0, sp, 1), v / np.where(sp > 0, sp, 1)
    args = (lon2, lat2, u, v) if C is None else (lon2, lat2, u, v, C)
    q = ax.quiver(*args, transform=PC, color=color if C is None else None, cmap=cmap, norm=norm,
                  scale=scale, scale_units="inches" if scale else None, width=width, headwidth=3.6, headlength=4,
                  headaxislength=3.6, zorder=zorder, pivot="middle")
    if key and not normalise:
        ax.quiverkey(q, *key_xy, REF, f"{REF:g} m/s", labelpos="W", coordinates="axes", fontproperties={"size": 7},
                     color="k").set_zorder(11)
    return q


def speed_background(ax, ds_t, alpha=1.0):
    return draw_field(ax, ds_t["vs"], SPEED_CMAP, SPEED_NORM, alpha=alpha)


def vorticity(ds_t):
    """Relative vorticity zeta = dv/dx - du/dy (1/s) on the lat/lon grid (centred differences)."""
    lat = np.deg2rad(ds_t.lat.values)[:, None]
    dlam = np.deg2rad(np.diff(ds_t.lon.values).mean())
    dphi = np.deg2rad(np.diff(ds_t.lat.values).mean())
    u, v = ds_t["u"].values, ds_t["v"].values
    dvdx = np.gradient(v, axis=1) / (R_EARTH * np.cos(lat) * dlam)
    dudy = np.gradient(u * np.cos(lat), axis=0) / (R_EARTH * dphi) / np.cos(lat)
    return dvdx - dudy


# ----------------------------------------------------------------------------------------------
def fig_stride(w, out):
    i = 6
    d = w.isel(time=i)
    fig = plt.figure(figsize=(17, 4.9), constrained_layout=True)
    rows = []
    for k, (st, sc) in enumerate([(10, 40), (20, 30), (40, 22)]):
        s = stride(d, st)
        ax = map_axes(fig, 1, 3, k + 1)
        im = speed_background(ax, d, alpha=0.55)
        n = int(np.isfinite(s["u"].values).sum())
        quiver(ax, s, scale=sc, width=0.0016 if st == 10 else 0.0022)
        add_features(ax, labels="lb" if k == 0 else "b")
        ax.set_title(f"Every {st}th cell (≈ {4 * st} km spacing): {n:,} arrows; scale {sc} m/s per inch", fontsize=9.5)
        panel_letter(ax, k)
        if k == 0:
            inset_legend(ax, [nodata_patch("No data")])
        rows.append({"method": "stride", "k": st, "spacing_km": 4 * st, "arrows": n})
    fig.colorbar(im, ax=fig.axes, orientation="horizontal", shrink=0.35, pad=0.02, aspect=40, label=SPEED_LABEL,
                 extend="max")
    fig.suptitle(f"Grid sampling by plain striding (magnitude-proportional arrows over the speed field) - {date_title(i)}",
                 fontsize=12)
    save_fig(fig, out)
    return rows


def fig_stride_vs_block(w, out):
    i = 6
    d = w.isel(time=i)
    rows = []
    fig = plt.figure(figsize=(16, 9.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.8])
    for r, st in enumerate([20, 40]):
        s, b = stride(d, st), block_mean(d, st)
        for c, (dd, name) in enumerate([(s, "plain stride (point sample)"), (b, f"{st}×{st} block average")]):
            ax = map_axes(fig, gs[r, c], extent=HELENE)
            speed_background(ax, d, alpha=0.6)
            quiver(ax, dd, scale=25 if st == 20 else 18, width=0.003)
            add_features(ax, labels="lb" if c == 0 else "b", lw_states=0.4)
            ax.set_title(f"k = {st} (≈ {4 * st} km): {name}", fontsize=10)
            panel_letter(ax, 3 * r + c)
            if r == 0 and c == 0:
                inset_legend(ax, [nodata_patch("No data")])
        # aliasing statistics over CONUS for several k (all 8 dates)
    ks = [5, 10, 20, 40]
    for k_ in ks:
        dang, dsp, ratio = [], [], []
        for t in range(len(DATES)):
            dt_ = w.isel(time=t)
            b = block_mean(dt_, k_)
            # point sample at the block centre cell
            s = dt_.isel(lat=slice(k_ // 2, None, k_), lon=slice(k_ // 2, None, k_)).isel(
                lat=slice(0, b.sizes["lat"]), lon=slice(0, b.sizes["lon"]))
            us, vs_, ub, vb = s["u"].values, s["v"].values, b["u"].values, b["v"].values
            m = np.isfinite(us) & np.isfinite(ub)
            a = np.degrees(np.arctan2(us * vb - vs_ * ub, us * ub + vs_ * vb))[m]
            dang.append(np.abs(a)); dsp.append(np.abs(np.hypot(us, vs_) - np.hypot(ub, vb))[m])
            ms = dt_["vs"].coarsen(lat=k_, lon=k_, boundary="trim").mean().values
            mm = np.isfinite(ms) & np.isfinite(ub)
            ratio.append((np.hypot(ub, vb)[mm] / ms[mm]))
        dang, dsp, ratio = np.concatenate(dang), np.concatenate(dsp), np.concatenate(ratio)
        rows.append({"k": k_, "spacing_km": 4 * k_, "n_pairs": dang.size, "median_dir_diff_deg": np.median(dang),
                     "p90_dir_diff_deg": np.percentile(dang, 90), "share_dir_diff_gt_45": 100 * (dang > 45).mean(),
                     "median_speed_diff_ms": np.median(dsp), "p90_speed_diff_ms": np.percentile(dsp, 90),
                     "median_vector_mean_over_mean_speed": np.median(ratio)})
    df = pd.DataFrame(rows)
    df.round(3).to_csv(PROC_DIR / "s3_aliasing.csv", index=False)
    print(df.to_string())
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(df.spacing_km, df.median_dir_diff_deg, "o-", color="#b2182b", label="median |Δ direction|")
    ax.plot(df.spacing_km, df.p90_dir_diff_deg, "s--", color="#b2182b", alpha=0.6, label="90th pct |Δ direction|")
    ax.set_xscale("log"); ax.set_xticks(df.spacing_km, [f"{x:g}" for x in df.spacing_km])
    ax.set_xlabel("Sampling spacing (km) = 4 km × k"); ax.set_ylabel("Direction difference, stride vs block (degrees)")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
    ax.set_title("(c) Aliasing: point sample vs block mean,\nall 8 dates, CONUS", fontsize=10)
    ax = fig.add_subplot(gs[1, 2])
    ax.plot(df.spacing_km, df.median_speed_diff_ms, "o-", color="#2166ac", label="median |Δ speed| (m/s)")
    ax.plot(df.spacing_km, df.p90_speed_diff_ms, "s--", color="#2166ac", alpha=0.6, label="90th pct |Δ speed| (m/s)")
    ax2 = ax.twinx()
    ax2.plot(df.spacing_km, df.median_vector_mean_over_mean_speed, "^-", color="0.3",
             label="|block-mean vector| / block-mean speed")
    ax2.set_ylabel("|mean vector| / mean speed (–)"); ax2.set_ylim(0, 1.05)
    ax.set_xscale("log"); ax.set_xticks(df.spacing_km, [f"{x:g}" for x in df.spacing_km])
    ax.set_xlabel("Sampling spacing (km) = 4 km × k"); ax.set_ylabel("Speed difference (m/s)")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="center left")
    ax.grid(alpha=0.3)
    ax.set_title("(f) Speed difference and vector cancellation", fontsize=10)
    sm = plt.cm.ScalarMappable(cmap=SPEED_CMAP, norm=SPEED_NORM)
    fig.colorbar(sm, ax=fig.axes[:4], orientation="horizontal", shrink=0.6, pad=0.02, aspect=45, label=SPEED_LABEL,
                 extend="max")
    fig.suptitle(f"Plain striding vs block averaging - Helene zoom, {date_title(i)}", fontsize=12)
    save_fig(fig, out)
    return df


def fig_prop_vs_uniform(w, out):
    i = 6
    d = w.isel(time=i)
    b = block_mean(d, 20)
    bz = block_mean(d, 8)
    sp_b, sp_bz = np.hypot(b["u"], b["v"]).values, np.hypot(bz["u"], bz["v"]).values
    fig = plt.figure(figsize=(15, 9.4), constrained_layout=True)
    for r, (dd, sp, ext, sc) in enumerate([(b, sp_b, None, 30), (bz, sp_bz, HELENE, 22)]):
        ax = map_axes(fig, 2, 2, 2 * r + 1, extent=ext)
        quiver(ax, dd, scale=sc, width=0.0022 if ext is None else 0.0026)
        add_features(ax, labels="lb", lw_states=0.3 if ext is None else 0.45)
        ax.set_title(("CONUS, 20×20 blocks" if ext is None else "Helene zoom, 8×8 blocks") +
                     ": length ∝ speed (black)", fontsize=10)
        panel_letter(ax, 2 * r)
        if r == 0:
            inset_legend(ax, [nodata_patch("No data")])
        ax = map_axes(fig, 2, 2, 2 * r + 2, extent=ext)
        q = quiver(ax, dd, scale=4.5 if ext is None else 3.2, C=sp, cmap="plasma", norm=mcolors.Normalize(0, 12),
                   normalise=True, width=0.0022 if ext is None else 0.0026)
        add_features(ax, labels="b", lw_states=0.3 if ext is None else 0.45)
        ax.set_title(("CONUS, 20×20 blocks" if ext is None else "Helene zoom, 8×8 blocks") +
                     ": same length, colour = speed", fontsize=10)
        panel_letter(ax, 2 * r + 1)
        cb = fig.colorbar(q, ax=ax, orientation="vertical", shrink=0.85, pad=0.02, aspect=25, extend="max")
        cb.set_label("Speed of block-mean vector (m/s)")
    fig.suptitle(f"Magnitude-proportional vs uniform-length arrows - {date_title(i)}", fontsize=12)
    save_fig(fig, out)


def fig_hurricanes(w, out):
    rows = []
    fig = plt.figure(figsize=(15, 11.6), constrained_layout=True)
    for k, (name, (ext, i)) in enumerate(REGIONS.items()):
        d = w.isel(time=i)
        sub = d.sel(lon=slice(ext[0], ext[1]), lat=slice(ext[2], ext[3]))
        ax = map_axes(fig, 2, 2, k + 1, extent=ext)
        im = speed_background(ax, d)
        quiver(ax, block_mean(sub, 7), scale=18, width=0.0028)
        z = vorticity(sub)
        zs = gaussian_filter(np.nan_to_num(z), 3)
        jm = np.unravel_index(np.nanargmax(np.where(np.isfinite(z), zs, -np.inf)), zs.shape)
        lonc, latc = float(sub.lon[jm[1]]), float(sub.lat[jm[0]])
        ax.plot(lonc, latc, marker="x", ms=12, mew=2.5, color="#d7301f", transform=PC, zorder=8)
        sp = sub["vs"].values
        imx = np.unravel_index(np.nanargmax(sp), sp.shape)
        ax.plot(float(sub.lon[imx[1]]), float(sub.lat[imx[0]]), marker="*", ms=13, color="#fec44f", mec="k",
                transform=PC, zorder=8)
        add_features(ax, labels="lb", lw_states=0.45)
        ax.set_title(f"{name}: {date_title(i)}\nmax {np.nanmax(sp):.1f} m/s, regional mean {np.nanmean(sp):.1f} m/s",
                     fontsize=10)
        panel_letter(ax, k)
        if k == 0:
            inset_legend(ax, [Line2D([], [], marker="x", ls="", color="#d7301f", mew=2, ms=9,
                                     label="max cyclonic vorticity (smoothed)"),
                              Line2D([], [], marker="*", ls="", color="#fec44f", mec="k", ms=10,
                                     label="max daily-mean speed"), nodata_patch("No data")])
        rows.append({"event": name, "date": DATES[i], "max_speed": np.nanmax(sp), "mean_speed": np.nanmean(sp),
                     "max_speed_lon": float(sub.lon[imx[1]]), "max_speed_lat": float(sub.lat[imx[0]]),
                     "vort_max_lon": lonc, "vort_max_lat": latc, "vort_max_1e-5_s": float(zs[jm]) * 1e5})
    fig.colorbar(im, ax=fig.axes, orientation="horizontal", shrink=0.45, pad=0.02, aspect=45, label=SPEED_LABEL,
                 extend="max")
    fig.suptitle("Regional zooms of the four landfall days: speed (colour) + 7×7 block-averaged wind vectors", fontsize=12.5)
    save_fig(fig, out)
    df = pd.DataFrame(rows).round(3)
    df.to_csv(PROC_DIR / "s3_regional_wind.csv", index=False)
    print(df.to_string())


def streamplot(ax, d, density, lw_scale=True, color_by_speed=True, start_points=None, regrid=300, cmap="viridis",
               norm=None, arrowsize=0.9, lw_const=0.8, coarsen=1):
    """Streamlines on the map projection.

    cartopy's GeoAxes.streamplot regrids to only 30*density points per side (~70 km on CONUS), so the vector
    field (east/north components, rotated into the projection by cartopy.vector_transform) is regridded
    here onto a regrid x (aspect-matched) grid in projected metres and matplotlib's streamplot is called
    directly in map coordinates. Cells outside the land mask stay masked, so streamlines stop at the coast.
    start_points (if given) must be in projected coordinates.
    """
    from cartopy.vector_transform import vector_scalar_to_grid
    from matplotlib.axes import Axes
    if coarsen > 1:
        d = d.coarsen(lat=coarsen, lon=coarsen, boundary="trim").mean()
    lon2, lat2 = np.meshgrid(d.lon.values, d.lat.values)
    u, v = d["u"].values, d["v"].values
    ok = np.isfinite(u) & np.isfinite(v)
    sp = np.hypot(u, v)
    x0, x1, y0, y1 = ax.get_extent(PROJ)
    shape = (regrid, max(20, int(regrid * (y1 - y0) / (x1 - x0))))
    X, Y, U, V, S = vector_scalar_to_grid(PC, PROJ, shape, lon2[ok], lat2[ok], u[ok], v[ok], sp[ok],
                                          target_extent=(x0, x1, y0, y1))
    # mask grid points that fall on ocean / outside CONUS (nearest gridMET cell is NaN)
    lonlat = PC.transform_points(PROJ, X, Y)
    jj = np.clip(np.searchsorted(d.lon.values, lonlat[..., 0]), 0, d.sizes["lon"] - 1)
    ii = np.clip(np.searchsorted(d.lat.values, lonlat[..., 1]), 0, d.sizes["lat"] - 1)
    land = ok[ii, jj]
    U, V, S = (np.ma.masked_where(~land | ~np.isfinite(A), A) for A in (U, V, S))
    norm = norm or mcolors.Normalize(0, 12)
    kw = dict(density=density, arrowsize=arrowsize, zorder=6)
    if color_by_speed:
        kw.update(color=S, cmap=cmap, norm=norm)
    else:
        kw.update(color="k")
    kw["linewidth"] = 0.3 + 1.6 * np.clip(S.filled(0) / 12, 0, 1) if lw_scale else lw_const
    if start_points is not None:
        kw["start_points"] = start_points
        kw["broken_streamlines"] = False
    n_before = len(ax.patches)
    sset = Axes.streamplot(ax, X, Y, U, V, **kw)
    # Matplotlib's FancyArrowPatch heads are mis-oriented on a cartopy GeoAxes (their tail->head vector is
    # correct, but every head renders pointing east). Replace them by quiver arrowheads drawn in the map's own
    # projected coordinates, at the same positions and directions, coloured like the streamline underneath.
    heads = ax.patches[n_before:]
    if heads:
        P = np.array([[*h._posA_posB[0], *h._posA_posB[1]] for h in heads])
        for h in heads:
            h.remove()
        d = P[:, 2:] - P[:, :2]
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        L = 0.016 * (x1 - x0) * arrowsize                  # arrow length in map metres
        if color_by_speed:
            jj = np.clip(np.searchsorted(X[0], P[:, 0]), 0, X.shape[1] - 1)
            ii = np.clip(np.searchsorted(Y[:, 0], P[:, 1]), 0, Y.shape[0] - 1)
            cols = plt.get_cmap(cmap)(norm(S.filled(0)[ii, jj]))
        else:
            cols = "k"
        ax.quiver(P[:, 0], P[:, 1], d[:, 0] * L, d[:, 1] * L, color=cols, angles="xy", scale_units="xy", scale=1, transform=PROJ,
                  pivot="tip", width=0.0032, headwidth=4.5, headlength=5.5, headaxislength=5.0, zorder=7)
    return sset


def fig_stream_vs_quiver(w, out):
    i = 6
    d = w.isel(time=i)
    fig = plt.figure(figsize=(16, 6.0), constrained_layout=True)
    ax = map_axes(fig, 1, 2, 1)
    speed_background(ax, d, alpha=0.6)
    quiver(ax, block_mean(d, 20), scale=30)
    add_features(ax, labels="lb")
    ax.set_title("(a) Quiver: 20×20 block-mean arrows over the speed field", fontsize=10)
    inset_legend(ax, [nodata_patch("No data")])
    ax = map_axes(fig, 1, 2, 2)
    s = streamplot(ax, d, density=2.4, coarsen=3, regrid=360)
    add_features(ax, labels="b")
    ax.set_title("(b) Streamlines (matplotlib streamplot, density 2.4): width and colour ∝ speed", fontsize=10)
    fig.colorbar(s.lines, ax=fig.axes, orientation="horizontal", shrink=0.4, pad=0.02, aspect=45,
                 label=SPEED_LABEL + " (streamline colour; quiver background uses GnBu)", extend="max")
    fig.suptitle(f"Quiver vs streamlines - {date_title(i)}", fontsize=12, y=1.06)
    save_fig(fig, out)


def fig_seeding(w, out):
    i = 6
    d = w.isel(time=i)
    ext = HELENE
    sub = d.sel(lon=slice(ext[0] - 1, ext[1] + 1), lat=slice(ext[2] - 1, ext[3] + 1))
    land = sub["u"].notnull().values
    lon2, lat2 = np.meshgrid(sub.lon.values, sub.lat.values)
    n_seeds = 120
    rng = np.random.default_rng(SEED)
    # (a) uniform grid seeds on land
    gl = np.linspace(ext[0] + 0.4, ext[1] - 0.4, 15)
    gt = np.linspace(ext[2] + 0.4, ext[3] - 0.4, 13)
    G = np.array([(x, y) for y in gt for x in gl])
    Gi = np.clip(np.searchsorted(sub.lat.values, G[:, 1]), 0, len(sub.lat) - 1)
    Gj = np.clip(np.searchsorted(sub.lon.values, G[:, 0]), 0, len(sub.lon) - 1)
    uni = G[land[Gi, Gj]]
    # (b) random seeds on land (same count)
    inbox = land & (lon2 > ext[0] + 0.3) & (lon2 < ext[1] - 0.3) & (lat2 > ext[2] + 0.3) & (lat2 < ext[3] - 0.3)
    li, lj = np.nonzero(inbox)   # random / feature seeds are drawn inside the zoom window only
    pick = rng.choice(li.size, size=len(uni), replace=False)
    rnd = np.c_[lon2[li[pick], lj[pick]], lat2[li[pick], lj[pick]]]
    # (c) feature-based: speed-weighted sampling (probability ∝ speed^4) + a ring around the vorticity maximum
    sp = np.nan_to_num(sub["vs"].values)
    p = (sp ** 4)[li, lj]; p /= p.sum()
    pick2 = rng.choice(li.size, size=len(uni) - 24, replace=False, p=p)
    z = gaussian_filter(np.nan_to_num(vorticity(sub)), 3)
    jm = np.unravel_index(np.argmax(np.where(inbox, z, -np.inf)), z.shape)
    c_lon, c_lat = float(sub.lon[jm[1]]), float(sub.lat[jm[0]])
    ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    ring = np.c_[c_lon + 1.2 * np.cos(ang) / np.cos(np.deg2rad(c_lat)), c_lat + 1.2 * np.sin(ang)]
    feat = np.r_[np.c_[lon2[li[pick2], lj[pick2]], lat2[li[pick2], lj[pick2]]], ring]

    rows = []
    fig = plt.figure(figsize=(17, 6.6), constrained_layout=True)
    for k, (seeds, name) in enumerate([(uni, "uniform grid seeds"), (rnd, "random seeds (uniform on land)"),
                                       (feat, "feature-based seeds (∝ speed⁴ + ring around vorticity max)")]):
        ax = map_axes(fig, 1, 3, k + 1, extent=ext)
        draw_field(ax, sub["vs"], "Greys", mcolors.Normalize(0, 20), alpha=0.5)
        sp_pts = PROJ.transform_points(PC, seeds[:, 0], seeds[:, 1])[:, :2]
        x0, x1, y0, y1 = ax.get_extent(PROJ)
        inside = (sp_pts[:, 0] > x0 + 2e4) & (sp_pts[:, 0] < x1 - 2e4) & (sp_pts[:, 1] > y0 + 2e4) & (sp_pts[:, 1] < y1 - 2e4)
        seeds, sp_pts = seeds[inside], sp_pts[inside]   # keep seeds inside the projected map window
        s = streamplot(ax, sub, density=4, start_points=sp_pts, regrid=200, arrowsize=0.8)
        ax.plot(seeds[:, 0], seeds[:, 1], "o", ms=2.6, color="#e41a1c", transform=PC, zorder=8)
        if k == 2:
            ax.plot(c_lon, c_lat, "x", ms=11, mew=2.5, color="k", transform=PC, zorder=9)
        add_features(ax, labels="lb" if k == 0 else "b", lw_states=0.45)
        # coverage metric: share of land cells within ~25 km (6 cells) of any streamline vertex
        paths = s.lines.get_segments()
        pts = np.concatenate([np.asarray(pp) for pp in paths]) if paths else np.empty((0, 2))
        ll = PC.transform_points(PROJ, pts[:, 0], pts[:, 1])[:, :2] if len(pts) else pts
        cover = np.zeros_like(land)
        if len(ll):
            ci = np.clip(np.searchsorted(sub.lat.values, ll[:, 1]), 0, len(sub.lat) - 1)
            cj = np.clip(np.searchsorted(sub.lon.values, ll[:, 0]), 0, len(sub.lon) - 1)
            cover[ci, cj] = True
            cover = maximum_filter(cover, size=13)
        cov = 100 * (cover & inbox).sum() / inbox.sum()
        hs = sp >= np.percentile(sp[inbox], 90)
        cov_hs = 100 * (cover & hs & inbox).sum() / (hs & inbox).sum()
        ax.set_title(f"({'abc'[k]}) {name}\n{len(seeds)} seeds; coverage {cov:.0f} % of land, {cov_hs:.0f} % of top-10 % speed cells",
                     fontsize=9.5)
        rows.append({"strategy": name, "seeds": len(seeds), "land_coverage_pct": cov, "high_speed_coverage_pct": cov_hs,
                     "line_segments": len(pts)})
        if k == 0:
            inset_legend(ax, [Line2D([], [], marker="o", ls="", color="#e41a1c", ms=4, label="seed point"),
                              Line2D([], [], marker="x", ls="", color="k", mew=2, ms=8, label="vorticity max (panel c)"),
                              nodata_patch("No data")])
    fig.colorbar(s.lines, ax=fig.axes, orientation="horizontal", shrink=0.4, pad=0.02, aspect=45,
                 label="Streamline colour: " + SPEED_LABEL + "; grey background = speed", extend="max")
    fig.suptitle(f"Streamline seeding strategies (same number of seeds) - Helene zoom, {date_title(i)}", fontsize=12)
    save_fig(fig, out)
    df = pd.DataFrame(rows).round(2)
    df.to_csv(PROC_DIR / "s3_seeding.csv", index=False)
    print(df.to_string(), "\nvorticity max at", c_lon, c_lat)


def fig_evolution(w, out_png, out_gif):
    fig = plt.figure(figsize=(17, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 4)
    rows = []
    for i in range(8):
        d = w.isel(time=i)
        ax = map_axes(fig, gs[i // 4, i % 4])
        im = speed_background(ax, d)
        quiver(ax, block_mean(d, 24), scale=26, width=0.0028, key_xy=(0.84, 0.04))
        add_features(ax, labels=("l" if i % 4 == 0 else "") + ("b" if i >= 4 else ""), fontsize=6)
        ax.set_title(date_title(i).replace("  (", "\n("), fontsize=9)
        panel_letter(ax, i)
        if i == 0:
            inset_legend(ax, [nodata_patch("No data")])
        sp = d["vs"].values
        u, v = d["u"].values, d["v"].values
        rows.append({"id": DATE_LABELS[i], "date": DATES[i], "mean_speed": np.nanmean(sp), "p99_speed": np.nanpercentile(sp, 99),
                     "max_speed": np.nanmax(sp), "mean_u": np.nanmean(u), "mean_v": np.nanmean(v),
                     "share_westerly_pct": 100 * np.nanmean(u[np.isfinite(u)] > 0)})
    fig.colorbar(im, ax=fig.axes, orientation="horizontal", shrink=0.45, pad=0.02, aspect=45, label=SPEED_LABEL,
                 extend="max")
    fig.suptitle("Wind field on the 8 dates: speed (colour, fixed 0-14 m/s) + 24×24 block-mean vectors (≈ 96 km)",
                 fontsize=12.5)
    save_fig(fig, out_png)
    df = pd.DataFrame(rows).round(3)
    df.to_csv(PROC_DIR / "s3_quiver_sampling.csv", index=False)
    print(df.to_string())

    frames, tmp = [], out_gif.with_suffix(".frame.png")
    for i in range(8):
        d = w.isel(time=i)
        fig = plt.figure(figsize=(9, 6.4))
        ax = map_axes(fig, 1, 1, 1); ax.set_position([0.04, 0.17, 0.92, 0.72])
        im = speed_background(ax, d)
        quiver(ax, block_mean(d, 20), scale=28, width=0.0022)
        add_features(ax, labels="lb")
        ax.set_title(f"S3 - 10 m wind (speed + 20×20 block-mean vectors)\n{date_title(i)}", fontsize=11)
        cax = fig.add_axes([0.15, 0.08, 0.7, 0.03])
        fig.colorbar(im, cax=cax, orientation="horizontal", label=SPEED_LABEL, extend="max")
        fig.savefig(tmp, dpi=110, facecolor="white"); plt.close(fig)
        frames.append(imageio.imread(tmp))
    tmp.unlink()
    imageio.mimsave(out_gif, frames, duration=1000, loop=0)
    print(f"[gif] {out_gif.name}")


def main():
    w = load_dates()
    fig_stride(w, IMG / "Fig_18_quiver_stride.png")
    fig_stride_vs_block(w, IMG / "Fig_19_quiver_stride_vs_block.png")
    fig_prop_vs_uniform(w, IMG / "Fig_20_quiver_proportional_vs_uniform.png")
    fig_hurricanes(w, IMG / "Fig_21_hurricane_zooms.png")
    fig_stream_vs_quiver(w, IMG / "Fig_22_streamlines_vs_quiver.png")
    fig_seeding(w, IMG / "Fig_23_streamline_seeding.png")
    fig_evolution(w, IMG / "Fig_24_wind_evolution.png", IMG / "Fig_24_wind_evolution.gif")


if __name__ == "__main__":
    main()
