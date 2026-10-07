"""Download annual gridMET NetCDF files with a progress bar and HTTP-range resume.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083).

Source listing (verified 2026-10-07): https://www.northwestknowledge.net/metdata/data/
File pattern: <var>_<year>.nc

Usage:
    python scivis/common/download_gridmet.py                     # default variables, 2024
    python scivis/common/download_gridmet.py --vars vs th --raw-dir D:/tmp/gridmet
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://www.northwestknowledge.net/metdata/data"
DEFAULT_VARS = ["vs", "th", "tmmx", "pr", "vpd", "rmax", "srad"]
REPO_ROOT = Path(__file__).resolve().parents[2]
# Raw files can be redirected outside the (cloud-synced) repo via GRIDMET_RAW_DIR.
DEFAULT_RAW_DIR = Path(os.environ.get("GRIDMET_RAW_DIR", REPO_ROOT / "data" / "raw" / "gridmet"))


def download(var: str, year: int, raw_dir: Path, chunk: int = 1 << 20) -> Path:
    """Download <var>_<year>.nc into raw_dir, resuming a partial file if present."""
    url = f"{BASE_URL}/{var}_{year}.nc"
    out = raw_dir / f"{var}_{year}.nc"
    part = out.with_suffix(".nc.part")
    total = int(requests.head(url, timeout=60).headers["Content-Length"])

    if out.exists() and out.stat().st_size == total:
        print(f"[skip] {out.name} already complete ({total / 1e6:.1f} MB)")
        return out

    done = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={done}-"} if done else {}
    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        if done and r.status_code != 206:  # server ignored Range -> restart cleanly
            done = 0
        with open(part, "ab" if done else "wb") as fh, tqdm(
            total=total, initial=done, unit="B", unit_scale=True, desc=out.name
        ) as bar:
            for block in r.iter_content(chunk_size=chunk):
                fh.write(block)
                bar.update(len(block))

    if part.stat().st_size != total:
        raise IOError(f"{out.name}: size {part.stat().st_size} != expected {total}; rerun to resume")
    part.replace(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vars", nargs="+", default=DEFAULT_VARS)
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = ap.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    for v in args.vars:
        download(v, args.year, args.raw_dir)


if __name__ == "__main__":
    main()
