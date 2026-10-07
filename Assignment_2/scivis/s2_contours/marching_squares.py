"""Marching Squares implemented from scratch in NumPy (vectorised over all cells).

Owner: Shrey Modi (BT2024125)

Conventions
-----------
* Z has shape (ny, nx); row i = y[i] (ascending), column j = x[j] (ascending).
* Cell (i, j) has corners  bl = Z[i, j], br = Z[i, j+1], tr = Z[i+1, j+1], tl = Z[i+1, j].
* A corner is "inside" (bit = 1) when its value >= level.
  case index = 1*bl + 2*br + 4*tr + 8*tl  ->  16 cases (0..15).
* Edges: B (bl-br), R (br-tr), T (tl-tr), L (bl-tl). The crossing point on an edge from value a to b
  is placed by linear interpolation  t = (level - a) / (b - a).
* Ambiguous saddles (case 5: bl & tr inside; case 10: br & tl inside) are resolved by a decider:
    "asymptotic" (default): value of the bilinear interpolant at its saddle point
                            s = (bl*tr - br*tl) / (bl + tr - br - tl)  (Nielson & Hamann 1991)
    "mean":                 cell-centre average (bl + br + tr + tl) / 4
    "high" / "low":         fixed rule - inside (resp. outside) region always connected through the
                            centre (this is what skimage.measure.find_contours does with
                            fully_connected='high' / 'low').
  If the decider value is >= level the two inside corners are joined through the cell centre.
* Cells with any NaN corner are skipped (no contour crosses the land/ocean mask).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

B, R, T, L = 0, 1, 2, 3
EDGE_NAMES = "BRTL"

# Unambiguous cases: list of (edge, edge) segments.
LUT: dict[int, list[tuple[int, int]]] = {
    0: [], 15: [],
    1: [(L, B)], 14: [(L, B)],
    2: [(B, R)], 13: [(B, R)],
    3: [(L, R)], 12: [(L, R)],
    4: [(R, T)], 11: [(R, T)],
    6: [(B, T)], 9: [(B, T)],
    7: [(L, T)], 8: [(L, T)],
}
# Saddles: (segments if the inside corners are connected through the centre, segments if separated)
SADDLE = {
    5: ([(B, R), (L, T)], [(L, B), (R, T)]),    # bl & tr inside
    10: ([(L, B), (R, T)], [(B, R), (L, T)]),   # br & tl inside
}


@dataclass
class MSResult:
    segments: np.ndarray        # (N, 2, 2) array of [[x0, y0], [x1, y1]]
    case_counts: np.ndarray     # (16,) number of valid cells per case
    n_saddles: int
    n_saddles_joined: int       # saddles whose inside corners were joined through the centre
    n_nan_cells: int


def _edge_points(Z, x, y, level):
    """Interpolated crossing point on each of the 4 edges of every cell -> (4, ny-1, nx-1, 2)."""
    bl, br, tr, tl = Z[:-1, :-1], Z[:-1, 1:], Z[1:, 1:], Z[1:, :-1]
    X0, X1 = x[None, :-1], x[None, 1:]
    Y0, Y1 = y[:-1, None], y[1:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        tB = (level - bl) / (br - bl)
        tR = (level - br) / (tr - br)
        tT = (level - tl) / (tr - tl)
        tL = (level - bl) / (tl - bl)
    shape = bl.shape
    P = np.empty((4,) + shape + (2,))
    P[B, ..., 0] = X0 + tB * (X1 - X0); P[B, ..., 1] = np.broadcast_to(Y0, shape)
    P[R, ..., 0] = np.broadcast_to(X1, shape); P[R, ..., 1] = Y0 + tR * (Y1 - Y0)
    P[T, ..., 0] = X0 + tT * (X1 - X0); P[T, ..., 1] = np.broadcast_to(Y1, shape)
    P[L, ..., 0] = np.broadcast_to(X0, shape); P[L, ..., 1] = Y0 + tL * (Y1 - Y0)
    return P, (bl, br, tr, tl)


def marching_squares(Z, level, x=None, y=None, decider="asymptotic") -> MSResult:
    Z = np.asarray(Z, dtype=float)
    ny, nx = Z.shape
    x = np.arange(nx, dtype=float) if x is None else np.asarray(x, float)
    y = np.arange(ny, dtype=float) if y is None else np.asarray(y, float)
    P, (bl, br, tr, tl) = _edge_points(Z, x, y, level)

    valid = np.isfinite(bl) & np.isfinite(br) & np.isfinite(tr) & np.isfinite(tl)
    case = ((bl >= level).astype(np.uint8) | ((br >= level).astype(np.uint8) << 1)
            | ((tr >= level).astype(np.uint8) << 2) | ((tl >= level).astype(np.uint8) << 3))
    case[~valid] = 0  # NaN cells produce nothing (counted separately)
    counts = np.bincount(case[valid].ravel(), minlength=16)

    segs = []
    for c, pairs in LUT.items():
        if not pairs:
            continue
        ii, jj = np.nonzero((case == c) & valid)
        for e0, e1 in pairs:
            segs.append(np.stack([P[e0, ii, jj], P[e1, ii, jj]], axis=1))

    n_sad = n_join = 0
    for c, (joined, separated) in SADDLE.items():
        ii, jj = np.nonzero((case == c) & valid)
        if ii.size == 0:
            continue
        a, b_, t_, l_ = bl[ii, jj], br[ii, jj], tr[ii, jj], tl[ii, jj]
        if decider == "asymptotic":
            den = a + t_ - b_ - l_
            with np.errstate(divide="ignore", invalid="ignore"):
                s = np.where(den != 0, (a * t_ - b_ * l_) / den, (a + b_ + t_ + l_) / 4)
            join = s >= level
        elif decider == "mean":
            join = (a + b_ + t_ + l_) / 4 >= level
        elif decider == "high":
            join = np.ones(ii.size, bool)
        elif decider == "low":
            join = np.zeros(ii.size, bool)
        else:
            raise ValueError(decider)
        n_sad += ii.size
        n_join += int(join.sum())
        for mask, pairs in ((join, joined), (~join, separated)):
            for e0, e1 in pairs:
                segs.append(np.stack([P[e0, ii[mask], jj[mask]], P[e1, ii[mask], jj[mask]]], axis=1))

    segments = np.concatenate(segs) if segs else np.empty((0, 2, 2))
    return MSResult(segments, counts, n_sad, n_join, int((~valid).sum()))


def segment_length(segments: np.ndarray) -> float:
    return float(np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1).sum())


def join_segments(segments: np.ndarray, decimals: int = 9) -> list[np.ndarray]:
    """Chain unordered segments into polylines (for labelling / counting connected contours)."""
    from collections import defaultdict, deque
    rs = np.round(segments, decimals)
    key = lambda p: (p[0], p[1])  # noqa: E731
    adj = defaultdict(list)
    for k, (p, q) in enumerate(rs):
        adj[key(p)].append(k); adj[key(q)].append(k)
    used = np.zeros(len(segments), bool)
    lines = []
    for start in range(len(segments)):
        if used[start]:
            continue
        used[start] = True
        line = deque([segments[start][0], segments[start][1]])
        ends = deque([key(rs[start][0]), key(rs[start][1])])
        for direction in (1, 0):  # extend forward from the end, then backward from the start
            while True:
                end = ends[-1] if direction else ends[0]
                nxt = [k for k in adj[end] if not used[k]]
                if not nxt:
                    break
                k = nxt[0]; used[k] = True
                far = 1 if key(rs[k][0]) == end else 0
                if direction:
                    line.append(segments[k][far]); ends.append(key(rs[k][far]))
                else:
                    line.appendleft(segments[k][far]); ends.appendleft(key(rs[k][far]))
        lines.append(np.array(line))
    return lines
