"""Shared plotting helpers for the SciVis tasks: the 8 analysis dates, map axes, saving, GIFs.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# The 8 analysis dates shared by S1, S2 and S3 (selection rule in stats_and_dates.py / report Sec. II).
# Hybrid rule: 6 event anchors verified in the data (daily_evidence.csv) + 2 fillers that split the
# 37-day event-free gap 5 Aug -> 11 Sep into thirds, so consecutive dates are 12-16 days apart
# (except the deliberate Helene landfall / inland pair).
DATES: list[str] = ["2024-07-08", "2024-07-24", "2024-08-05", "2024-08-17",
                    "2024-08-29", "2024-09-11", "2024-09-26", "2024-09-27"]
EVENTS: list[str] = ["Beryl landfall (TX) + western heat", "Western heat-wave peak", "Debby landfall (FL)",
                     "Gap filler (quiet)", "Gap filler (quiet)", "Francine landfall (LA)",
                     "Helene landfall (FL Big Bend)", "Helene inland (GA/Carolinas)"]
DATE_LABELS: list[str] = [f"D{i + 1}" for i in range(len(DATES))]

DPI = 300


def save_fig(fig, out: Path, dpi: int = DPI) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[fig] {out.relative_to(out.parents[1]) if len(out.parents) > 1 else out}")
