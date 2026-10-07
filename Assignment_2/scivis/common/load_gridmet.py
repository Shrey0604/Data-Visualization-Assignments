"""Shared gridMET loading, subsetting, masking, unit conversion and wind decomposition.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083). Used by S1, S2 and S3.

Run once to build the processed Jul-Sep 2024 subsets:
    python scivis/common/load_gridmet.py            # reads GRIDMET_RAW_DIR or data/raw/gridmet

Afterwards every task imports `load_var(...)` / `load_wind()` which read data/processed/ only.

Conventions in processed files (see notes/preprocessing_log.md):
  * time dimension renamed day -> time, restricted to 2024-07-01 .. 2024-09-30 (92 days)
  * latitude sorted ASCENDING (raw files are descending) so that origin='lower', streamplot and
    contour routines all see the same orientation
  * fill value 32767 decoded to NaN (non-land / outside CONUS mask)
  * tmmx in degC; pr in mm/day; vs in m/s; th in degrees (meteorological, FROM, clockwise from N);
    vpd in kPa; rmax in %; srad in W/m^2
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_gridmet import DEFAULT_RAW_DIR  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = REPO_ROOT / "data" / "processed"
YEAR = 2024
T0, T1 = "2024-07-01", "2024-09-30"

# file abbreviation -> (short output name, output units, long description)
VARS = {
    "tmmx": ("tmmx", "degC", "Daily maximum near-surface air temperature"),
    "pr":   ("pr",   "mm",   "Daily accumulated precipitation"),
    "vs":   ("vs",   "m/s",  "Daily mean wind speed at 10 m"),
    "th":   ("th",   "degrees clockwise from north (direction wind comes FROM)", "Daily mean wind direction at 10 m"),
    "vpd":  ("vpd",  "kPa",  "Daily mean vapour pressure deficit"),
    "rmax": ("rmax", "%",    "Daily maximum relative humidity"),
    "srad": ("srad", "W/m^2", "Daily mean downward shortwave radiation at surface"),
}



# ----------------------------------------------------------------------------------------------
# Raw -> processed
# ----------------------------------------------------------------------------------------------
def open_raw(abbr: str, raw_dir: Path = DEFAULT_RAW_DIR) -> xr.DataArray:
    """Lazily open one annual file and return its single data variable (CF-decoded)."""
    ds = xr.open_dataset(raw_dir / f"{abbr}_{YEAR}.nc", chunks={"day": 61, "lat": 98, "lon": 231})  # = on-disk chunking
    (name,) = list(ds.data_vars)  # the long CF name differs from the file abbreviation
    return ds[name]


def subset(da: xr.DataArray) -> xr.DataArray:
    """Jul-Sep 2024, ascending latitude, time dim renamed, crs scalar dropped."""
    da = da.sel(day=slice(T0, T1)).rename(day="time")
    da = da.sortby("lat")  # raw latitude is descending (49.4 -> 25.07)
    return da.drop_vars([c for c in da.coords if c not in ("time", "lat", "lon")])


def convert_units(abbr: str, da: xr.DataArray) -> xr.DataArray:
    """K -> degC for temperature; every other variable keeps its native unit."""
    attrs = dict(da.attrs)
    if abbr == "tmmx":
        assert attrs.get("units") == "K", attrs.get("units")
        da = da - 273.15
    out_units = VARS[abbr][1]
    da = da.astype("float32")
    da.attrs = {"units": out_units, "long_name": VARS[abbr][2], "source_units": attrs.get("units", ""),
                "source_variable": attrs.get("description", "")}
    return da


def wind_components(vs: xr.DataArray, th: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray]:
    """Meteorological (speed, FROM-direction clockwise from N) -> (u, v) pointing where wind blows TO.

    u = -vs * sin(th),  v = -vs * cos(th)   (th in radians)
    """
    rad = np.deg2rad(th)
    u = (-vs * np.sin(rad)).astype("float32")
    v = (-vs * np.cos(rad)).astype("float32")
    u.attrs = {"units": "m/s", "long_name": "Eastward wind component (toward), 10 m"}
    v.attrs = {"units": "m/s", "long_name": "Northward wind component (toward), 10 m"}
    return u, v


def wind_sanity_check() -> None:
    """Print the decomposition for the four cardinal FROM-directions."""
    print("Wind decomposition sanity check (vs = 10 m/s):")
    for th, name in [(0, "northerly (from N)"), (90, "easterly (from E)"),
                     (180, "southerly (from S)"), (270, "westerly (from W)")]:
        r = np.deg2rad(th)
        u, v = -10 * np.sin(r), -10 * np.cos(r)
        print(f"  th={th:3d} deg {name:20s} -> u={u:+6.2f}, v={v:+6.2f}")
    r = np.deg2rad(270)
    assert -10 * np.sin(r) > 0 and abs(-10 * np.cos(r)) < 1e-9, "westerly must give u>0, v~0"
    r = np.deg2rad(0)
    assert -10 * np.cos(r) < 0, "northerly must give v<0"


ENCODING = {"zlib": True, "complevel": 4, "dtype": "float32"}


def build_processed(raw_dir: Path = DEFAULT_RAW_DIR) -> None:
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    land_masks = {}
    for abbr in VARS:
        if not (raw_dir / f"{abbr}_{YEAR}.nc").exists():
            print(f"[warn] raw {abbr} missing, skipped")
            continue
        da = convert_units(abbr, subset(open_raw(abbr, raw_dir))).load()
        da.name = abbr
        land_masks[abbr] = da.notnull()
        out = PROC_DIR / f"gridmet_{abbr}_2024JAS.nc"
        da.to_dataset().to_netcdf(out, encoding={abbr: ENCODING})
        print(f"[ok] {out.name}: shape={da.shape}, NaN={int(da.isnull().sum())}, "
              f"range=[{float(da.min()):.2f}, {float(da.max()):.2f}] {da.attrs['units']}")

    # wind: combine vs + th into one file with u, v
    if {"vs", "th"} <= land_masks.keys():
        vs, th = load_var("vs"), load_var("th")
        u, v = wind_components(vs, th)
        ds = xr.Dataset({"u": u, "v": v})  # vs and th already stored in their own files
        ds.to_netcdf(PROC_DIR / "gridmet_wind_2024JAS.nc", encoding={k: ENCODING for k in ds.data_vars})
        print(f"[ok] gridmet_wind_2024JAS.nc: u range [{float(u.min()):.2f}, {float(u.max()):.2f}], "
              f"v range [{float(v.min()):.2f}, {float(v.max()):.2f}] m/s")

    # land-mask consistency across variables and days
    ref = land_masks["tmmx"].isel(time=0)
    print(f"tmmx land cells day0: {int(ref.sum())} of {ref.size} ({100 * float(ref.mean()):.1f}%)")
    for abbr, m in land_masks.items():
        const_in_time = bool((m == m.isel(time=0)).all())
        same_as_tmmx = int((m.isel(time=0) != ref).sum())
        print(f"  {abbr:5s}: mask constant in time={const_in_time}, cells differing from tmmx mask={same_as_tmmx}")


# ----------------------------------------------------------------------------------------------
# Readers used by the tasks
# ----------------------------------------------------------------------------------------------
def load_var(abbr: str) -> xr.DataArray:
    """Processed Jul-Sep 2024 field for one variable (time, lat[ascending], lon)."""
    return xr.open_dataset(PROC_DIR / f"gridmet_{abbr}_2024JAS.nc")[abbr].load()


def load_wind() -> xr.Dataset:
    """Processed wind dataset with vs, th, u, v."""
    ds = xr.open_dataset(PROC_DIR / "gridmet_wind_2024JAS.nc").load()
    ds["vs"], ds["th"] = load_var("vs"), load_var("th")
    return ds


def anomaly(da: xr.DataArray) -> xr.DataArray:
    """Daily value minus the Jul-Sep 2024 per-cell mean."""
    out = da - da.mean("time")
    out.attrs = dict(da.attrs, long_name=da.attrs.get("long_name", "") + " anomaly (vs Jul-Sep 2024 mean)")
    return out


if __name__ == "__main__":
    wind_sanity_check()
    build_processed()
