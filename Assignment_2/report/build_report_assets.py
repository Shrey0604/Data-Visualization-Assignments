"""Generate LaTeX tables, the figure index, code excerpts and the preprocessing-log appendix for the report.

Shared (all members). Every number in the generated tables is read from data/processed/*.csv, so the report
cannot drift from the data. Run before latexmk:  python build_report_assets.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
P = ROOT / "data" / "processed"
GEN = HERE / "generated"
GEN.mkdir(exist_ok=True)

ASCII = {"°": " deg", "≥": ">=", "≤": "<=", "→": "->", "←": "<-", "↔": "<->", "×": "x", "∝": "~", "σ": "sigma",
         "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", "·": ".", "⁻": "^-", "¹": "1",
         "²": "2", "³": "3", "⁴": "^4", "√": "sqrt", "±": "+/-", "≈": "~", "β": "beta", "τ": "tau", "μ": "mu",
         "Δ": "Delta", "ζ": "zeta", "₀": "0", "∗": "*", "✓": "ok", "λ": "lambda", "φ": "phi"}


def ascii(s: str) -> str:
    for k, v in ASCII.items():
        s = s.replace(k, v)
    return s.encode("ascii", "replace").decode("ascii")


def tex(s) -> str:
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$")]:
        s = s.replace(a, b)
    return s


def write(name, body):
    (GEN / name).write_text(body, encoding="utf-8")
    print("[gen]", name)


def table(df: pd.DataFrame, cols, heads, fmt, caption, label, star=False, size=r"\footnotesize", align=None):
    env = "table*" if star else "table"
    align = align or "l" + "r" * (len(cols) - 1)
    lines = [rf"\begin{{{env}}}[!t]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}", size,
             r"\begin{adjustbox}{max width=\linewidth}", rf"\begin{{tabular}}{{{align}}}", r"\toprule",
             " & ".join(heads) + r" \\", r"\midrule"]
    for _, r in df.iterrows():
        cells = []
        for c, f in zip(cols, fmt):
            v = r[c]
            if f.endswith("d") and pd.notna(v):
                v = int(v)
            cells.append(tex(v) if f == "s" else str(v) if f == "r" else (f"{v:{f}}" if pd.notna(v) else "--"))
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}", rf"\end{{{env}}}"]
    return "\n".join(lines) + "\n"


def main():
    # ------------------------------------------------------------------ SciVis tables
    sel = pd.read_csv(P / "selected_dates.csv")
    write("tab_dates.tex", table(sel, ["id", "date", "role", "conus_tmmx_max_C", "west_area_ge40C_pct", "tx_pr_mean",
                                       "fl_pr_mean", "la_pr_mean", "se_pr_mean", "conus_vs_max"],
                                 ["ID", "Date", "Role", r"$T_{max}$ max (\si{\celsius})", r"W.\ area $\ge$40\,\si{\celsius} (\%)",
                                  "TX pr", "FL--GA--SC pr", "LA pr", "SE pr", r"$v_s$ max (m/s)"],
                                 ["s", "s", "s", ".1f", ".1f", ".1f", ".1f", ".1f", ".1f", ".1f"],
                                 "The eight analysis dates and the evidence that selected them (regional pr = area-mean daily "
                                 "precipitation in mm; boxes defined in Sec.~\\ref{sec:dates}).", "tab:dates", star=True,
                                 align="llp{4.2cm}rrrrrrr"))
    g = pd.read_csv(P / "stats_global.csv")
    g["units"] = g["units"].replace({"degrees clockwise from north (direction wind comes FROM)": "deg (from)",
                                     "degC": r"\si{\celsius}", "W/m^2": r"W\,m$^{-2}$", "%": r"\%"})
    g["variable"] = g["variable"].map(lambda v: v)
    body = table(g, ["variable", "units", "min", "p5", "p25", "p50", "p75", "p95", "max", "mean", "std"],
                 ["Var.", "Unit", "min", "p5", "p25", "p50", "p75", "p95", "max", "mean", "std"],
                 ["s", "r", ".2f", ".2f", ".2f", ".2f", ".2f", ".2f", ".2f", ".2f", ".2f"],
                 "Global statistics of every processed variable over all 92 days and 483,879 land cells "
                 "(44.5 million cell-days). 71.3\\,\\% of pr cell-days are exactly 0.", "tab:global", star=True)
    write("tab_global.tex", body)
    d = pd.read_csv(P / "stats_per_day.csv")
    dates = sel.date.tolist()
    rows = []
    for dt, idd in zip(dates, sel.id):
        r = {"id": idd, "date": dt}
        for v in ["tmmx", "pr", "vs", "vpd"]:
            x = d[(d.variable == v) & (d.date == dt)].iloc[0]
            r[f"{v}_min"], r[f"{v}_max"], r[f"{v}_mean"], r[f"{v}_p95"] = x["min"], x["max"], x["mean"], x["p95"]
        rows.append(r)
    rows = pd.DataFrame(rows)
    write("tab_perdate.tex", table(rows, ["id", "date"] + [f"{v}_{s}" for v in ["tmmx", "pr", "vs", "vpd"] for s in ["min", "max", "mean"]],
                                   ["ID", "Date", r"$T$ min", r"$T$ max", r"$T$ mean", "pr min", "pr max", "pr mean",
                                    r"$v_s$ min", r"$v_s$ max", r"$v_s$ mean", "VPD min", "VPD max", "VPD mean"],
                                   ["s", "s"] + [".2f"] * 12,
                                   r"Per-timestep statistics on the eight dates over land ($T_{max}$ in \si{\celsius}, pr in mm, "
                                   r"$v_s$ in m/s, VPD in kPa). The full 92-day table is \fpath{data/processed/stats_per_day.csv}.",
                                   "tab:perdate", star=True))
    r = pd.read_csv(P / "s1_global_vs_local_ranges.csv")
    write("tab_s1_ranges.tex", table(r, ["id", "date", "local_min", "local_max", "share_of_global_range_%"],
                                     ["ID", "Date", "local min", "local max", r"\% of global range"],
                                     ["s", "s", ".2f", ".2f", ".1f"],
                                     r"Local (per-date) $T_{max}$ range vs the global range $-6.35$ to $53.85$\,\si{\celsius}.",
                                     "tab:s1ranges"))
    L = pd.read_csv(P / "s1_colormap_lightness.csv")
    L["monotonic"] = L.monotonic.map({True: "yes", False: "no"})
    write("tab_s1_lightness.tex", table(L, ["colormap", "L_start", "L_end", "L_min", "L_max", "monotonic", "n_sign_changes"],
                                        ["Colormap", "$L^*_0$", "$L^*_1$", "$L^*_{min}$", "$L^*_{max}$", "Monotone", "Turns"],
                                        ["s", ".1f", ".1f", ".1f", ".1f", "s", "d"],
                                        "CIELAB lightness along each colour map (Fig.~\\ref{fig:03}). Turns = sign changes of "
                                        "$\\mathrm{d}L^*/\\mathrm{d}x$.", "tab:lightness"))
    v = pd.read_csv(P / "s2_variable_choice.csv")
    write("tab_s2_choice.tex", table(v, ["variable", "p5", "p95", "p95_over_p5", "roughness_8dates", "share_at_max_value", "segments_D2_5levels"],
                                     ["Var.", "p5", "p95", "p95/p5", "Rough.", "At max", "Segments"],
                                     ["s", ".2f", ".2f", ".2f", ".3f", ".3f", ",d"],
                                     "Contour-variable screening on the eight dates. Roughness = std of (field $-$ 15-cell box "
                                     "mean) / std of field; At max = share of cells equal to the maximum value; Segments = "
                                     "Marching-Squares segments for five decile levels on D2.", "tab:s2choice"))
    m = pd.read_csv(P / "s2_validation.csv")
    mm = m.T.reset_index()
    mm.columns = ["metric", "1.005 kPa", "2.005 kPa", "3.005 kPa"]
    names = {"saddle_cells": "Saddle cells (cases 5, 10)", "segments_own_high": "Segments, own MS ('high' rule)",
             "segments_skimage_high": "Segments, skimage ('high')", "identical_segments_high_vs_high": "Identical segments",
             "match_pct": "Match (\\%)", "own_high_vs_skimage_low_identical": "Identical vs skimage 'low'",
             "segments_own_asymptotic": "Segments, own MS (asymptotic)", "asymptotic_joined_saddles": "Saddles joined, asymptotic",
             "mean_joined_saddles": "Saddles joined, centre mean", "segments_differing_asym_vs_skimage_high": "Segments differing, asympt.\\ vs skimage",
             "max_vertex_dist_cells": "Max vertex distance (cells)", "length_own_asym_cells": "Isoline length, own (cells)",
             "length_skimage_cells": "Isoline length, skimage (cells)", "length_contourpy_cells": "Isoline length, contourpy (cells)",
             "time_own_s": "Runtime own (s)", "time_skimage_s": "Runtime skimage (s)"}
    mm = mm[mm.metric.isin(names)].copy()
    mm["metric"] = mm.metric.map(names)
    lines = [r"\begin{table}[!t]", r"\centering", r"\caption{Validation of our Marching Squares against "
             r"\texttt{skimage.measure.find\_contours} and \texttt{contourpy} on the D2 VPD field (810,810 cells).}",
             r"\label{tab:msval}", r"\footnotesize", r"\begin{adjustbox}{max width=\linewidth}", r"\begin{tabular}{lrrr}", r"\toprule",
             r"Metric & 1.005 kPa & 2.005 kPa & 3.005 kPa \\", r"\midrule"]
    for _, rr in mm.iterrows():
        f = (lambda x: f"{x:.3f}") if "Runtime" in rr.metric or "distance" in rr.metric else (
            (lambda x: f"{x:.1f}") if "Match" in rr.metric or "length" in rr.metric else (lambda x: f"{x:,.0f}"))
        lines.append(f"{rr.metric} & {f(rr['1.005 kPa'])} & {f(rr['2.005 kPa'])} & {f(rr['3.005 kPa'])} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    write("tab_msval.tex", "\n".join(lines) + "\n")
    lv = pd.read_csv(P / "s2_levels.csv")
    write("tab_s2_levels.tex", table(lv, ["scheme", "levels", "segments", "min_band_share_pct", "max_band_share_pct"],
                                     ["Scheme", "Levels (kPa)", "Segments", "Min band \\%", "Max band \\%"],
                                     ["s", "s", ",d", ".1f", ".1f"], "Contour-level placement on D2 (Fig.~\\ref{fig:14}).",
                                     "tab:levels", star=True, align="p{5cm}p{6cm}rrr"))
    sm = pd.read_csv(P / "s2_smoothing.csv")
    write("tab_s2_smooth.tex", table(sm, ["sigma_cells", "sigma_km", "segments_conus", "polylines_zoom", "length_zoom_km_approx"],
                                     [r"$\sigma$ (cells)", r"$\sigma$ (km)", "CONUS segs", "Zoom lines", "Zoom km"],
                                     ["d", "d", ",d", ",d", ",.0f"], "Effect of mask-aware Gaussian pre-smoothing on the 2 and "
                                     "3 kPa isolines (D2).", "tab:smooth"))
    ev = pd.read_csv(P / "s2_evolution_area.csv")
    write("tab_s2_evol.tex", table(ev, ["id", "date", "area_ge_1kPa_pct", "area_ge_2kPa_pct", "area_ge_3kPa_pct", "area_ge_4kPa_pct", "segments"],
                                   ["ID", "Date", r"$\ge$1", r"$\ge$2", r"$\ge$3", r"$\ge$4", "Segments"],
                                   ["s", "s", ".1f", ".1f", ".1f", ".1f", ",d"],
                                   "Share of CONUS land (\\%) above each fixed VPD level (kPa) on the eight dates.", "tab:evol"))
    al = pd.read_csv(P / "s3_aliasing.csv")
    write("tab_s3_alias.tex", table(al, ["k", "spacing_km", "n_pairs", "median_dir_diff_deg", "p90_dir_diff_deg", "share_dir_diff_gt_45",
                                         "median_speed_diff_ms", "p90_speed_diff_ms", "median_vector_mean_over_mean_speed"],
                                    ["$k$", "km", "Pairs", r"med.\ $|\Delta\theta|$", r"p90 $|\Delta\theta|$", r"\% $>$45\si{\degree}",
                                     r"med.\ $|\Delta v|$", r"p90 $|\Delta v|$", r"$|\bar{\mathbf{v}}|/\overline{|\mathbf{v}|}$"],
                                    ["d", "d", ",d", ".2f", ".2f", ".2f", ".3f", ".3f", ".3f"],
                                    "Aliasing of plain striding relative to $k\\times k$ block averaging, pooled over all eight "
                                    "dates (directions in degrees, speeds in m/s).", "tab:alias", star=True))
    rw = pd.read_csv(P / "s3_regional_wind.csv")
    write("tab_s3_regional.tex", table(rw, ["event", "date", "max_speed", "mean_speed", "max_speed_lat", "max_speed_lon", "vort_max_lat", "vort_max_lon", "vort_max_1e-5_s"],
                                       ["Event box", "Date", "max $v_s$", "mean $v_s$", "max lat", "max lon", r"$\zeta$ lat", r"$\zeta$ lon", r"$\zeta_{max}$"],
                                       ["s", "s", ".1f", ".2f", ".2f", ".2f", ".2f", ".2f", ".1f"],
                                       "Regional wind statistics of the four landfall zooms (speeds in m/s, smoothed relative "
                                       "vorticity $\\zeta$ in $10^{-5}$\\,s$^{-1}$).", "tab:regional", star=True))
    se = pd.read_csv(P / "s3_seeding.csv")
    write("tab_s3_seed.tex", table(se, ["strategy", "seeds", "land_coverage_pct", "high_speed_coverage_pct", "line_segments"],
                                   ["Strategy", "Seeds", "Land cov.\\ \\%", "Top-10\\% speed cov.\\ \\%", "Segments"],
                                   ["s", "d", ".1f", ".1f", ",d"], "Streamline seeding comparison on D7 (Helene zoom).",
                                   "tab:seed", align="p{3.3cm}rrrr"))
    qs = pd.read_csv(P / "s3_quiver_sampling.csv")
    write("tab_s3_dates.tex", table(qs, ["id", "date", "mean_speed", "p99_speed", "max_speed", "mean_u", "mean_v", "share_westerly_pct"],
                                    ["ID", "Date", "mean", "p99", "max", r"$\bar u$", r"$\bar v$", r"\% $u>0$"],
                                    ["s", "s", ".2f", ".1f", ".1f", ".2f", ".2f", ".1f"],
                                    "CONUS wind summary on the eight dates (m/s).", "tab:s3dates"))
    # ------------------------------------------------------------------ InfoVis tables
    gm = pd.read_csv(P / "i1_graph_metrics.csv", index_col=0)["value"]
    nice = {"nodes": "Nodes", "edges": "Edges", "subreddits": "Subreddit nodes", "domains": "Domain nodes",
            "density": "Density", "bipartite_density": "Bipartite density $|E|/(|S||D|)$",
            "connected_components": "Connected components", "mean_degree": "Mean degree",
            "subreddit_mean_degree": "Mean degree, subreddits", "domain_mean_degree": "Mean degree, domains",
            "domain_degree_1_share": "Share of domains with degree 1", "clustering_unipartite_avg": "Avg.\\ clustering (unipartite)",
            "bipartite_clustering_avg": "Avg.\\ bipartite clustering", "projection_edges": "Edges of subreddit projection",
            "projection_density": "Density of projection", "projection_clustering_avg": "Avg.\\ clustering of projection",
            "louvain_communities": "Louvain communities", "modularity": "Modularity $Q$",
            "diameter_largest_cc": "Diameter", "degree_assortativity": "Degree assortativity"}
    lines = [r"\begin{table}[!t]", r"\centering", r"\caption{Metrics of the subreddit--domain graph.}", r"\label{tab:graph}",
             r"\footnotesize", r"\begin{tabular}{lr}", r"\toprule", r"Metric & Value \\", r"\midrule"]
    for k, n in nice.items():
        x = gm[k]
        lines.append(f"{n} & {x:,.0f} \\\\" if float(x).is_integer() else f"{n} & {x:.4f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("tab_graph.tex", "\n".join(lines) + "\n")
    cm = pd.read_csv(P / "i1_communities.csv")
    cm["top_subreddits"] = cm.top_subreddits.str.replace("; ", ", ")
    cm["top_domains"] = cm.top_domains.str.split("; ").str[:5].str.join(", ")
    write("tab_communities.tex", table(cm, ["community", "nodes", "subreddits", "domains", "strength", "top_subreddits", "top_domains"],
                                       ["C", "Nodes", "Subs", "Doms", "Strength", "Leading subreddits", "Leading domains"],
                                       ["s", "d", "d", "d", ",d", "s", "s"],
                                       "Louvain communities (resolution 1, weighted, seed 42). Strength = total edge weight.",
                                       "tab:comm", star=True, align="lrrrrp{5.6cm}p{6.2cm}"))
    lm = pd.read_csv(P / "i1_layout_metrics.csv", index_col=0).reset_index().rename(columns={"index": "layout"})
    write("tab_layouts.tex", table(lm, ["layout", "runtime_s", "edge_crossings", "mean_edge_length", "cv_edge_length", "silhouette_by_community", "node_pairs_closer_than_0.005"],
                                   ["Layout", "Runtime (s)", "Crossings", "Mean edge len.", "CV edge len.", "Silhouette", "Near-overlaps"],
                                   ["s", ".2f", ",.0f", ".3f", ".3f", ".3f", ",.0f"],
                                   "Layout comparison on the same 671-node graph (positions normalised to $[-1,1]$; near-overlaps "
                                   "= nodes whose nearest neighbour is closer than 0.005).", "tab:layouts", star=True,
                                   align="p{4.6cm}rrrrrr"))
    ps = pd.read_csv(P / "i2_parcoords_states.csv")
    write("tab_pcstates.tex", table(ps, ["state", "selected"], ["Interaction state", "Selected posts"], ["s", ",d"],
                                    "Record counts after each scripted interaction (Figs.~\\ref{fig:31}--\\ref{fig:32}).",
                                    "tab:pcstates", align="p{5.8cm}r"))
    tm = pd.read_csv(P / "i2_treemap_tiling_metrics.csv")
    agg = tm.groupby(["tiling", "sort"]).agg(mean=("mean", "mean"), maxar=("max", "max"), tau=("tau", "mean")).reset_index()
    agg["sort"] = agg["sort"].map({"value": "size", "name": "name"})
    write("tab_tiling.tex", table(agg, ["tiling", "sort", "mean", "maxar", "tau"],
                                  ["Tiling", "Child order", "Mean AR", "Worst AR", r"Order $\tau$"],
                                  ["s", "s", ".2f", ".2f", ".2f"],
                                  "Tiling strategies, averaged over five views (H1 root, H1 Entertainment, H2 root, H3 root, H3 "
                                  "era 2017--18). AR = long/short side (1 = square); $\\tau$ = Kendall rank correlation "
                                  "between the sort order and the reading order of the rectangles.", "tab:tiling"))
    # ------------------------------------------------------------------ figure index + code + log
    imgs = sorted(p.name for p in (ROOT / "images").glob("Fig_*"))
    lines = [r"\begin{table*}[!t]", r"\centering", r"\caption{Figure index: report figure number $\rightarrow$ file in \fpath{images/}.}",
             r"\label{tab:figindex}", r"\scriptsize", r"\begin{tabular}{llll}", r"\toprule", r"Fig. & File & Fig. & File \\", r"\midrule"]
    pairs = []
    for f in imgs:
        mt = re.match(r"Fig_(\d+)([a-f]?)_", f)
        pairs.append((f"{int(mt.group(1))}{mt.group(2)}", f))
    half = (len(pairs) + 1) // 2
    for a, b in zip(pairs[:half], pairs[half:] + [("", "")] * (2 * half - len(pairs))):
        lines.append(f"{a[0]} & \\fpath{{{a[1]}}} & {b[0]} & " + (f"\\fpath{{{b[1]}}}" if b[1] else "") + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    write("tab_figindex.tex", "\n".join(lines) + "\n")

    excerpts = [("scivis/common/load_gridmet.py", "wind_components", "code_wind.py"),
                ("scivis/s2_contours/marching_squares.py", "marching_squares", "code_ms.py"),
                ("scivis/s2_contours/run.py", "nan_gaussian", "code_gauss.py"),
                ("scivis/s3_quiver_streamlines/run.py", "block_mean", "code_block.py"),
                ("infovis/i3_horizon_ridgeline/run.py", "horizon", "code_horizon.py"),
                ("infovis/common/a1_preprocess.py", "to_tree", "code_tree.py")]
    for path, fn, out in excerpts:
        src = (ROOT / path).read_text(encoding="utf-8")
        node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == fn)
        seg = "\n".join(src.splitlines()[node.lineno - 1 - len(node.decorator_list): node.end_lineno])
        (GEN / out).write_text(ascii(seg) + "\n", encoding="ascii")
        print("[gen]", out)
    js = (ROOT / "infovis/i2_web/parcoords/parcoords.js").read_text(encoding="utf-8")
    a = js.index("function pathPoints(r)"); b = js.index("const lineGen")
    (GEN / "code_bundle.js").write_text(ascii(js[a:b].rstrip()) + "\n", encoding="ascii")
    js2 = (ROOT / "infovis/i2_web/treemap/treemap.js").read_text(encoding="utf-8")
    a = js2.index("function tile(node"); b = js2.index("async function rebuild")
    (GEN / "code_tile.js").write_text(ascii(js2[a:b].rstrip()) + "\n", encoding="ascii")
    log = (ROOT / "notes/preprocessing_log.md").read_text(encoding="utf-8")
    (GEN / "preprocessing_log.txt").write_text(ascii(log), encoding="ascii")
    print("[gen] preprocessing_log.txt")


if __name__ == "__main__":
    main()
