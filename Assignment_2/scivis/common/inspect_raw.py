"""Print raw schema of each gridMET file: variable names, dims, coords, units, encoding.

Shared preprocessing (all members). Usage:
    python scivis/common/inspect_raw.py [--raw-dir DIR]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

from download_gridmet import DEFAULT_RAW_DIR, DEFAULT_VARS


def inspect(path: Path) -> None:
    # decode off first so we see the on-disk dtype, fill value and scale factor
    raw = xr.open_dataset(path, mask_and_scale=False, decode_times=False)
    print("=" * 100)
    print(path.name, f"({path.stat().st_size / 1e6:.1f} MB)")
    print(raw)
    for name, da in raw.data_vars.items():
        print(f"-- data var '{name}' attrs:")
        for k, v in da.attrs.items():
            print(f"     {k}: {v}")
        print(f"     encoding: { {k: da.encoding.get(k) for k in ('dtype', 'zlib', 'chunksizes', '_FillValue', 'scale_factor', 'add_offset')} }")
    for c in raw.coords:
        vals = raw[c].values
        print(f"-- coord {c}: n={vals.size}, first={vals[:3]}, last={vals[-3:]}, attrs={dict(raw[c].attrs)}")
    lat = raw["lat"].values
    print(f"   lat ordering: {'DESCENDING' if lat[0] > lat[-1] else 'ascending'}; "
          f"dlat={np.diff(lat).mean():.6f}, dlon={np.diff(raw['lon'].values).mean():.6f}")
    ds = xr.open_dataset(path)  # decoded
    print("-- decoded time range:", ds["day"].values[0], "->", ds["day"].values[-1], "n =", ds.sizes["day"])
    raw.close(); ds.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--vars", nargs="+", default=DEFAULT_VARS)
    ap.add_argument("--year", type=int, default=2024)
    a = ap.parse_args()
    for v in a.vars:
        p = a.raw_dir / f"{v}_{a.year}.nc"
        if p.exists():
            inspect(p)
        else:
            print("missing", p)
