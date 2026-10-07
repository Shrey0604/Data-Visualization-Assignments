"""Cartopy map helpers shared by S1, S2 and S3.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083).

All processed fields have ascending latitude, so images are drawn with origin="lower".
Maps use a Lambert Conformal Conic projection (standard parallels 33 N / 45 N), the usual
equal-shape projection for CONUS, with state borders and coastlines from Natural Earth (50m).
"""
from __future__ import annotations

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

PC = ccrs.PlateCarree()
PROJ = ccrs.LambertConformal(central_longitude=-96, central_latitude=39, standard_parallels=(33, 45))
# Projected (LCC metres) bounding box of the gridMET land cells + ~2 % margin, so maps have no empty corners.
CONUS_EXTENT_PROJ = [-2.46e6, 2.35e6, -1.53e6, 1.47e6]
NODATA_COLOR = "#dfe6ec"   # ocean / outside the gridMET land mask
STATES = cfeature.NaturalEarthFeature("cultural", "admin_1_states_provinces_lakes", "50m", facecolor="none")


def grid_extent(da) -> list[float]:
    """Cell-edge extent of a (lat, lon) DataArray for imshow."""
    lon, lat = da.lon.values, da.lat.values
    dlon, dlat = np.diff(lon).mean(), np.diff(lat).mean()
    return [lon[0] - dlon / 2, lon[-1] + dlon / 2, lat[0] - dlat / 2, lat[-1] + dlat / 2]


def map_axes(fig, *args, extent=None, **kw):
    """Map axis on the LCC projection. `extent` = [lon0, lon1, lat0, lat1] for regional zooms."""
    ax = fig.add_subplot(*args, projection=PROJ, **kw)
    if extent is None:
        ax.set_extent(CONUS_EXTENT_PROJ, crs=PROJ)
    else:
        ax.set_extent(extent, crs=PC)
    ax.set_facecolor(NODATA_COLOR)
    return ax


def add_features(ax, lw_states=0.25, lw_coast=0.5, gridlines=True, labels="lb", fontsize=6.5):
    ax.add_feature(STATES, edgecolor="0.25", linewidth=lw_states, zorder=3)
    ax.coastlines("50m", linewidth=lw_coast, color="0.15", zorder=3)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=lw_coast, edgecolor="0.15", zorder=3)
    if gridlines:
        gl = ax.gridlines(crs=PC, draw_labels=bool(labels), x_inline=False, y_inline=False,
                          linewidth=0.3, color="0.5", alpha=0.6, linestyle=":",
                          xlocs=range(-130, -60, 10), ylocs=range(20, 55, 5))
        gl.top_labels = "t" in labels
        gl.bottom_labels = "b" in labels
        gl.left_labels = "l" in labels
        gl.right_labels = "r" in labels
        gl.xlabel_style = gl.ylabel_style = {"size": fontsize, "color": "0.3"}
        gl.rotate_labels = False
    return ax


def draw_field(ax, da, cmap, norm=None, **kw):
    """Draw a 2-D (lat, lon) field as an image on a map axis; NaN -> background colour."""
    cm = plt.get_cmap(cmap).copy() if isinstance(cmap, str) else cmap.copy()
    cm.set_bad(alpha=0.0)
    im = ax.imshow(np.ma.masked_invalid(da.values), origin="lower", extent=grid_extent(da), transform=PC,
                   cmap=cm, norm=norm, interpolation="nearest", regrid_shape=900, zorder=1, **kw)
    return im


def nodata_patch(label="No data (ocean / outside CONUS)"):
    return Patch(facecolor=NODATA_COLOR, edgecolor="0.4", linewidth=0.5, label=label)


_PROJ_GRID_CACHE: dict = {}


def projected_grid(da):
    """2-D LCC x/y (metres) of every grid cell centre (cached per grid)."""
    key = (da.lon.values[0], da.lon.values[-1], da.lon.size, da.lat.values[0], da.lat.values[-1], da.lat.size)
    if key not in _PROJ_GRID_CACHE:
        lon2, lat2 = np.meshgrid(da.lon.values, da.lat.values)
        p = PROJ.transform_points(PC, lon2, lat2)
        _PROJ_GRID_CACHE[key] = (p[..., 0], p[..., 1])
    return _PROJ_GRID_CACHE[key]


def contourf_proj(ax, da, **kw):
    """contourf computed directly in map coordinates (transform=PROJ).

    Filled-contour polygons with many holes are sometimes inverted when cartopy re-projects them from
    PlateCarree (the whole axis gets filled). Contouring on the projected 2-D coordinates of the grid
    avoids any path re-projection and gives the same bands.
    """
    X, Y = projected_grid(da)
    return ax.contourf(X, Y, np.ma.masked_invalid(da.values), transform=PROJ, **kw)
