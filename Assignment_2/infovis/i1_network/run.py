"""I1 - Node-link diagram of the subreddit <-> external-domain network (A1 Reddit data).

Owner: Sidhanth Prabhu (BT2024027)

Graph: bipartite, undirected, weighted. Nodes = 43 subreddits + 628 external domains (>= 3 top posts).
Edge (s, d) weight = number of all-time top posts in subreddit s that link to domain d.

Outputs
  images/Fig_25_network_statistics.png        degree / strength distributions, community sizes
  images/Fig_26_network_layouts.png           5 layouts, same encoding (size = strength, colour = Louvain)
  images/Fig_27_network_layout_metrics.png    runtime, edge crossings, edge length, community separation
  images/Fig_28_network_filtering.png         before / after k-core + edge-weight filtering
  images/Fig_29_subreddit_projection.png      weighted one-mode projection on subreddits (labelled)
  images/Fig_30_network_interactive.png       screenshot of the PyVis HTML (Playwright)
  infovis/i1_network/interactive/network.html PyVis: hover tooltips, zoom/pan/drag, filter + physics controls
  infovis/i1_network/gexf/*.gexf              for Gephi (ForceAtlas2 / Fruchterman-Reingold / Yifan Hu)
  data/processed/i1_*.csv                     metrics tables

Run: python infovis/i1_network/run.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parents[2]
NET = ROOT / "data" / "processed" / "a1" / "network"
PROC = ROOT / "data" / "processed"
IMG = ROOT / "images"
HERE = Path(__file__).resolve().parent
SEED = 42
DPI = 300
plt.rcParams.update({"font.size": 9})


def save(fig, out):
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[fig]", out.name)


# ----------------------------------------------------------------------------------------------
def build_graph() -> nx.Graph:
    nodes = pd.read_csv(NET / "nodes.csv")
    edges = pd.read_csv(NET / "edges.csv")
    G = nx.Graph()
    for r in nodes.itertuples():
        G.add_node(r.id, type=r.type, bipartite=0 if r.type == "subreddit" else 1, posts=int(r.posts),
                   category=r.category if isinstance(r.category, str) else "",
                   domain_class=r.domain_class if isinstance(r.domain_class, str) else "")
    for r in edges.itertuples():
        G.add_edge(r.source, r.target, weight=int(r.weight), median_score=float(r.median_score))
    for n in G:
        G.nodes[n]["degree"] = G.degree(n)
        G.nodes[n]["strength"] = G.degree(n, weight="weight")
    return G


def communities(G, seed=SEED):
    comms = nx.community.louvain_communities(G, weight="weight", resolution=1.0, seed=seed)
    comms = sorted(comms, key=lambda c: -sum(G.nodes[n]["strength"] for n in c))
    for k, c in enumerate(comms):
        for n in c:
            G.nodes[n]["community"] = k
    return comms


def community_label(G, c):
    subs = sorted([n for n in c if G.nodes[n]["type"] == "subreddit"], key=lambda n: -G.nodes[n]["strength"])
    doms = sorted([n for n in c if G.nodes[n]["type"] == "domain"], key=lambda n: -G.nodes[n]["strength"])
    return subs, doms


def graph_stats(G, comms) -> dict:
    subs = [n for n, d in G.nodes(data=True) if d["type"] == "subreddit"]
    doms = [n for n, d in G.nodes(data=True) if d["type"] == "domain"]
    cc = list(nx.connected_components(G))
    P = nx.bipartite.weighted_projected_graph(G, subs)
    st = {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "subreddits": len(subs), "domains": len(doms),
        "density": nx.density(G),
        "bipartite_density": G.number_of_edges() / (len(subs) * len(doms)),
        "connected_components": len(cc), "largest_component_nodes": max(len(c) for c in cc),
        "mean_degree": np.mean([d for _, d in G.degree()]),
        "subreddit_mean_degree": np.mean([G.degree(n) for n in subs]),
        "domain_mean_degree": np.mean([G.degree(n) for n in doms]),
        "domain_degree_1_share": np.mean([G.degree(n) == 1 for n in doms]),
        "clustering_unipartite_avg": nx.average_clustering(G),
        "bipartite_clustering_avg": nx.bipartite.average_clustering(G),
        "projection_edges": P.number_of_edges(), "projection_density": nx.density(P),
        "projection_clustering_avg": nx.average_clustering(P),
        "louvain_communities": len(comms),
        "modularity": nx.community.modularity(G, comms, weight="weight"),
        "diameter_largest_cc": nx.diameter(G.subgraph(max(cc, key=len))),
        "degree_assortativity": nx.degree_assortativity_coefficient(G),
    }
    return st


# ----------------------------------------------------------------------------------------------
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf",
           "#bcbd22", "#7f7f7f", "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"]


def node_style(G):
    order = list(G.nodes())
    strength = np.array([G.nodes[n]["strength"] for n in order], float)
    size = 4 + 220 * np.sqrt(strength / strength.max())
    col = [PALETTE[G.nodes[n]["community"] % len(PALETTE)] for n in order]
    shape_sub = np.array([G.nodes[n]["type"] == "subreddit" for n in order])
    return order, size, col, shape_sub


def draw_graph(ax, G, pos, title, labels=6, edge_alpha=0.12, label_fs=6.5):
    order, size, col, is_sub = node_style(G)
    segs = np.array([[pos[u], pos[v]] for u, v in G.edges()])
    w = np.array([G.edges[e]["weight"] for e in G.edges()], float)
    ax.add_collection(LineCollection(segs, colors="0.35", linewidths=0.2 + 1.2 * np.sqrt(w / w.max()),
                                     alpha=edge_alpha, zorder=1))
    xy = np.array([pos[n] for n in order])
    col = np.array(col)
    ax.scatter(xy[~is_sub, 0], xy[~is_sub, 1], s=size[~is_sub], c=col[~is_sub], marker="o", edgecolors="white",
               linewidths=0.3, zorder=2, alpha=0.9)
    ax.scatter(xy[is_sub, 0], xy[is_sub, 1], s=size[is_sub], c=col[is_sub], marker="s", edgecolors="k",
               linewidths=0.6, zorder=3)
    if labels:
        top = sorted(G.nodes(), key=lambda n: -G.nodes[n]["strength"])[:labels]
        texts = [ax.text(pos[n][0], pos[n][1], n, fontsize=label_fs, zorder=5,
                         bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.4)) for n in top]
        adjust_text(texts, ax=ax, expand=(1.3, 1.5), arrowprops=dict(arrowstyle="-", color="0.3", lw=0.5))
    ax.set_title(title, fontsize=9.5)
    ax.set_aspect("equal"); ax.autoscale(); ax.margins(0.04)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("0.7")


def normalise_pos(pos):
    xy = np.array(list(pos.values()), float)
    xy = (xy - xy.mean(0))
    xy /= np.abs(xy).max()
    return {n: xy[k] for k, n in enumerate(pos)}


def edge_crossings(G, pos, max_edges=None):
    """Exact number of crossing edge pairs (shared endpoints excluded), vectorised in chunks."""
    E = list(G.edges())
    P = np.array([[pos[u], pos[v]] for u, v in E])
    idx = {n: k for k, n in enumerate(G.nodes())}
    ends = np.array([[idx[u], idx[v]] for u, v in E])
    m = len(E)
    total = 0
    for a in range(0, m, 300):
        A = P[a:a + 300]
        p1, p2 = A[:, None, 0], A[:, None, 1]
        q1, q2 = P[None, :, 0], P[None, :, 1]

        def orient(p, q, r):
            return np.sign((q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0]))
        o1, o2 = orient(p1, p2, q1), orient(p1, p2, q2)
        o3, o4 = orient(q1, q2, p1), orient(q1, q2, p2)
        cross = (o1 * o2 < 0) & (o3 * o4 < 0)
        ea = ends[a:a + 300]
        share = ((ea[:, None, 0] == ends[None, :, 0]) | (ea[:, None, 0] == ends[None, :, 1]) |
                 (ea[:, None, 1] == ends[None, :, 0]) | (ea[:, None, 1] == ends[None, :, 1]))
        rows = np.arange(a, a + len(A))[:, None]
        upper = np.arange(m)[None, :] > rows
        total += int((cross & ~share & upper).sum())
    return total


def layout_metrics(G, pos, runtime):
    xy = np.array([pos[n] for n in G.nodes()])
    lab = np.array([G.nodes[n]["community"] for n in G.nodes()])
    el = np.array([np.linalg.norm(pos[u] - pos[v]) for u, v in G.edges()])
    from scipy.spatial import cKDTree
    d, _ = cKDTree(xy).query(xy, k=2)
    near = d[:, 1]
    keep = np.isin(lab, [c for c in np.unique(lab) if (lab == c).sum() >= 2])
    return {"runtime_s": runtime, "edge_crossings": edge_crossings(G, pos),
            "mean_edge_length": el.mean(), "cv_edge_length": el.std() / el.mean(),
            "silhouette_by_community": silhouette_score(xy[keep], lab[keep]) if keep.sum() > 2 else np.nan,
            "node_pairs_closer_than_0.005": int((near < 0.005).sum())}


def compute_layouts(G):
    W = G.copy()
    # Kamada-Kawai treats weight as a distance -> give it 1/weight (strong links = short)
    for u, v, d in W.edges(data=True):
        d["dist"] = 1.0 / d["weight"]
    specs = {
        "Fruchterman-Reingold (spring)": lambda: nx.spring_layout(G, weight="weight", k=1.6 / math.sqrt(len(G)), iterations=200, seed=SEED),
        "Kamada-Kawai": lambda: nx.kamada_kawai_layout(W, weight="dist"),
        "ForceAtlas2 (distributed attraction)": lambda: nx.forceatlas2_layout(G, weight="weight", max_iter=600, gravity=1.0,
                                                                           scaling_ratio=2.0, distributed_action=True, seed=SEED),
        "Spectral (normalised Laplacian)": lambda: spectral_normalised(G),
        "Circular (grouped by community)": lambda: circular_by_community(G),
    }
    # Layouts are cached (Kamada-Kawai alone takes ~9 min on this graph); delete the cache or pass
    # --recompute to time them again. Runtimes in the cache are those of the run that computed them.
    cache = PROC / "i1_layout_cache.json"
    stored = json.loads(cache.read_text()) if cache.exists() and "--recompute" not in sys.argv else {}
    out = {}
    for name, fn in specs.items():
        if name in stored and set(stored[name]["pos"]) == set(G.nodes()):
            pos = {n: np.array(v) for n, v in stored[name]["pos"].items()}
            rt = stored[name]["runtime_s"]
        else:
            t0 = time.perf_counter()
            pos = normalise_pos(fn())
            rt = time.perf_counter() - t0
            stored[name] = {"runtime_s": rt, "pos": {n: list(map(float, v)) for n, v in pos.items()}}
            cache.write_text(json.dumps(stored))
        out[name] = (pos, rt)
        print(f"  layout {name}: {rt:.2f}s")
    return out


def spectral_normalised(G):
    """Spectral layout from eigenvectors 2-3 of the symmetric normalised Laplacian
    L = I - D^-1/2 W D^-1/2, mapped back with D^-1/2 (Shi-Malik / Ng-Jordan-Weiss embedding).

    nx.spectral_layout uses the unnormalised Laplacian L = D - W; on this hub-dominated bipartite graph its
    Fiedler vectors localise on a few weakly attached nodes, so the other 660+ nodes collapse into a point
    (kept in the metrics table as 'Spectral (unnormalised, nx)' for comparison).
    """
    import scipy.sparse as sp
    nodes = list(G)
    A = nx.to_scipy_sparse_array(G, nodelist=nodes, weight="weight", dtype=float)
    d = np.asarray(A.sum(1)).ravel()
    Dm = sp.diags(1 / np.sqrt(d))
    L = (sp.eye(len(d)) - Dm @ A @ Dm).toarray()
    _, vec = np.linalg.eigh(L)
    X = Dm @ vec[:, 1:3]
    return {n: X[i] for i, n in enumerate(nodes)}


def circular_by_community(G):
    order = sorted(G.nodes(), key=lambda n: (G.nodes[n]["community"], -G.nodes[n]["strength"]))
    ang = np.linspace(0, 2 * np.pi, len(order), endpoint=False)
    return {n: np.array([np.cos(a), np.sin(a)]) for n, a in zip(order, ang)}


# ----------------------------------------------------------------------------------------------
def fig_stats(G, comms, st, out):
    subs = [n for n, d in G.nodes(data=True) if d["type"] == "subreddit"]
    doms = [n for n, d in G.nodes(data=True) if d["type"] == "domain"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    ax = axes[0]
    for nodes_, lab, c, m in [(doms, "domains (n = %d)" % len(doms), "#ff7f0e", "o"), (subs, "subreddits (n = %d)" % len(subs), "#1f77b4", "s")]:
        deg = np.sort([G.degree(n) for n in nodes_])
        ccdf = 1 - np.arange(len(deg)) / len(deg)
        ax.loglog(deg, ccdf, m, ms=4, color=c, label=lab, alpha=0.8)
    ax.set_xlabel("Degree k (number of distinct partners)"); ax.set_ylabel("P(K ≥ k)  (CCDF)")
    ax.set_title("(a) Degree distribution (complementary CDF, log-log)"); ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="lower left")
    ax = axes[1]
    w = np.array([d["weight"] for *_, d in G.edges(data=True)])
    ax.hist(w, bins=np.logspace(0, np.log10(w.max() + 1), 30), color="0.5")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Edge weight (top posts linking subreddit → domain)"); ax.set_ylabel("Number of edges")
    ax.set_title(f"(b) Edge weights: median {np.median(w):.0f}, max {w.max()} posts"); ax.grid(alpha=0.3, which="both")
    ax = axes[2]
    sizes = [len(c) for c in comms]
    nsub = [sum(G.nodes[n]["type"] == "subreddit" for n in c) for c in comms]
    x = np.arange(len(comms))
    ax.bar(x, np.array(sizes) - np.array(nsub), color=[PALETTE[k % len(PALETTE)] for k in x], label="domains")
    ax.bar(x, nsub, bottom=np.array(sizes) - np.array(nsub), color="k", alpha=0.55, label="subreddits")
    for k, c in enumerate(comms):
        s, d = community_label(G, c)
        ax.text(k, sizes[k] + 3, f"{len(s)}", ha="center", fontsize=7)
    ax.set_xticks(x, [f"C{k}" for k in x])
    ax.set_xlabel("Louvain community (ordered by total strength)"); ax.set_ylabel("Nodes")
    ax.set_title(f"(c) {len(comms)} communities, modularity Q = {st['modularity']:.3f}"); ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.suptitle(f"Subreddit–domain network: {st['nodes']} nodes, {st['edges']} edges, density {st['density']:.4f}, "
                 f"{st['connected_components']} connected component(s)", fontsize=12)
    save(fig, out)


def community_legend(G, comms, max_items=8):
    hs = []
    for k, c in enumerate(comms[:max_items]):
        s, d = community_label(G, c)
        lab = f"C{k}: " + ", ".join(s[:2]) + (" …" if len(s) > 2 else "") + f" | {', '.join(d[:1])}"
        hs.append(Line2D([], [], marker="o", ls="", color=PALETTE[k % len(PALETTE)], ms=7, label=lab))
    hs += [Line2D([], [], marker="s", ls="", mfc="white", mec="k", ms=7, label="square = subreddit"),
           Line2D([], [], marker="o", ls="", mfc="0.6", mec="white", ms=7, label="circle = domain; size ∝ √strength")]
    return hs


def fig_layouts(G, comms, layouts, out):
    fig, axes = plt.subplots(2, 3, figsize=(17, 11.4), constrained_layout=True)
    for ax, (name, (pos, rt)) in zip(axes.flat, layouts.items()):
        draw_graph(ax, G, pos, f"{name}\nruntime {rt:.2f} s", labels=8)
    ax = axes.flat[-1]
    ax.axis("off")
    ax.legend(handles=community_legend(G, comms, 10), loc="center", fontsize=8.5, frameon=False,
              title="Louvain communities (top subreddits | top domain)", title_fontsize=9.5)
    fig.suptitle("Same graph, same encoding, five layouts (size = √ weighted degree, colour = Louvain community, "
                 "labels = 8 strongest nodes)", fontsize=12.5)
    save(fig, out)


def fig_layout_metrics(df, out):
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.8), constrained_layout=True)
    names = {"Fruchterman-Reingold (spring)": "Fruchterman-\nReingold", "Kamada-Kawai": "Kamada-\nKawai",
             "ForceAtlas2 (distributed attraction)": "ForceAtlas2", "Spectral (normalised Laplacian)": "Spectral\n(normalised)",
             "Circular (grouped by community)": "Circular", "Spectral (unnormalised, nx)": "Spectral\n(unnorm., nx)"}
    short = [names.get(n, n) for n in df.index]
    cols = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3", "#b0b0b0"]
    for ax, (col, lab, logy) in zip(axes, [("runtime_s", "Runtime (s)", True), ("edge_crossings", "Edge crossings (count)", False),
                                           ("cv_edge_length", "Edge-length coefficient of variation (–)", False),
                                           ("silhouette_by_community", "Silhouette of node positions by community (–)", False)]):
        ax.bar(short, df[col], color=cols[:len(df)])
        if logy:
            ax.set_yscale("log")
        ax.set_ylabel(lab); ax.tick_params(axis="x", labelsize=7.5)
        for k, v in enumerate(df[col]):
            ax.text(k, v, f"{v:,.2f}" if v < 100 else f"{v:,.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5)
        ax.grid(alpha=0.3, axis="y")
    for k, ax in enumerate(axes):
        ax.set_title(f"({'abcd'[k]}) " + ["Runtime", "Edge crossings (lower = cleaner)", "Edge-length uniformity (lower = more uniform)",
                                         "Community separation (higher = better)"][k], fontsize=10)
    fig.suptitle("Quantitative layout comparison on the same 671-node graph (grey = unnormalised spectral, not drawn in Fig. 26)",
                 fontsize=12)
    save(fig, out)


def filter_graph(G, k=2, wmin=2):
    H = nx.Graph()
    H.add_nodes_from(G.nodes(data=True))
    H.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if d["weight"] >= wmin)
    H.remove_nodes_from([n for n in list(H) if H.degree(n) == 0])
    core = set(nx.k_core(H, k))
    # rebuild in G's (CSV) node and edge order: k_core returns set order, which changes with Python's
    # string-hash seed and would make the force layouts non-reproducible between runs
    F = nx.Graph()
    F.add_nodes_from((n, d) for n, d in G.nodes(data=True) if n in core)
    F.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if u in core and v in core and d["weight"] >= wmin)
    return F


def fig_filter(G, H, out):
    t0 = time.perf_counter()
    posG = normalise_pos(nx.forceatlas2_layout(G, weight="weight", max_iter=600, scaling_ratio=2.0, distributed_action=True, seed=SEED))
    posH = normalise_pos(nx.forceatlas2_layout(H, weight="weight", max_iter=600, scaling_ratio=2.0, distributed_action=True, seed=SEED))
    for n in H:
        H.nodes[n]["strength"] = H.degree(n, weight="weight")
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.2), constrained_layout=True)
    draw_graph(axes[0], G, posG, f"(a) Before: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges", labels=8)
    draw_graph(axes[1], H, posH, f"(b) After: edge weight ≥ 2 posts, then 2-core → {H.number_of_nodes()} nodes, "
                                f"{H.number_of_edges()} edges", labels=16, edge_alpha=0.18)
    fig.legend(handles=community_legend(G, sorted(nx.community.louvain_communities(G, weight="weight", seed=SEED),
                                                 key=lambda c: -sum(G.nodes[n]["strength"] for n in c)), 6)[-2:],
               loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("Node filtering (ForceAtlas2 layout; colours = Louvain communities of the unfiltered graph)", fontsize=12.5)
    save(fig, out)
    print(f"  filter layouts {time.perf_counter() - t0:.1f}s")


def fig_projection(G, out):
    subs = [n for n, d in G.nodes(data=True) if d["type"] == "subreddit"]
    # cosine similarity of subreddit -> domain weight vectors (hub domains imgur / youtube down-weighted by IDF)
    doms = [n for n, d in G.nodes(data=True) if d["type"] == "domain"]
    M = np.zeros((len(subs), len(doms)))
    di = {d: k for k, d in enumerate(doms)}
    for k, s in enumerate(subs):
        for d_, a in G[s].items():
            M[k, di[d_]] = a["weight"]
    idf = np.log(len(subs) / (M > 0).sum(0))
    X = np.log1p(M) * idf
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    S = X @ X.T
    P = nx.Graph()
    for k, s in enumerate(subs):
        P.add_node(s, category=G.nodes[s]["category"], strength=G.nodes[s]["strength"])
    thr = 0.15
    for a in range(len(subs)):
        for b in range(a + 1, len(subs)):
            if S[a, b] >= thr:
                P.add_edge(subs[a], subs[b], weight=S[a, b])
    comms = nx.community.louvain_communities(P, weight="weight", seed=SEED)
    # Kamada-Kawai on the complete graph with distance = 1 - cosine similarity (an MDS-like layout:
    # Euclidean distance on the page approximates dissimilarity of the communities' link profiles)
    Q = nx.Graph()
    for a in range(len(subs)):
        for b in range(a + 1, len(subs)):
            Q.add_edge(subs[a], subs[b], dist=1.0 - S[a, b] + 0.05)
    pos = nx.kamada_kawai_layout(Q, weight="dist")
    cats = sorted({P.nodes[n]["category"] for n in P})
    cc = dict(zip(cats, plt.get_cmap("tab10").colors))
    fig, ax = plt.subplots(figsize=(14, 12), constrained_layout=True)
    w = np.array([P.edges[e]["weight"] for e in P.edges()])
    ax.add_collection(LineCollection([[pos[u], pos[v]] for u, v in P.edges()], colors="0.4",
                                     linewidths=0.4 + 4 * (w - thr) / (w.max() - thr), alpha=0.45, zorder=1))
    xy = np.array([pos[n] for n in P])
    ax.scatter(xy[:, 0], xy[:, 1], s=[60 + 500 * np.sqrt(P.nodes[n]["strength"] / max(1, max(nx.get_node_attributes(P, "strength").values()))) for n in P],
               c=[cc[P.nodes[n]["category"]] for n in P], edgecolors="k", linewidths=0.7, zorder=2)
    texts = [ax.text(pos[n][0], pos[n][1], n, fontsize=8.5, zorder=4,
                     bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=0.5)) for n in P]
    adjust_text(texts, x=xy[:, 0], y=xy[:, 1], ax=ax, expand=(1.25, 1.6), force_text=(0.6, 0.8),
                force_static=(0.4, 0.6), max_move=(40, 40), iter_lim=2000,
                arrowprops=dict(arrowstyle="-", color="0.4", lw=0.5))
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=cc[c], mec="k", ms=9, label=c) for c in cats],
              loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=9, title="A1 topic category", frameon=False)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal"); ax.margins(0.06)
    ax.set_title(f"One-mode projection on subreddits: edge if TF-IDF cosine similarity of linked domains ≥ {thr} "
                 f"({P.number_of_nodes()} nodes, {P.number_of_edges()} edges, {len(comms)} Louvain communities)\n"
                 "edge width ∝ similarity; node size ∝ √(top posts linking to external domains); Kamada-Kawai with distance = 1 - similarity", fontsize=11)
    save(fig, out)
    rows = sorted(((S[a, b], subs[a], subs[b]) for a in range(len(subs)) for b in range(a + 1, len(subs))), reverse=True)[:15]
    pd.DataFrame(rows, columns=["cosine", "sub_a", "sub_b"]).round(3).to_csv(PROC / "i1_top_similar_subreddits.csv", index=False)
    return P


# ----------------------------------------------------------------------------------------------
def export_gexf(G, H):
    gd = HERE / "gexf"
    gd.mkdir(exist_ok=True)
    for g, name in [(G, "reddit_domain_network.gexf"), (H, "reddit_domain_network_filtered.gexf")]:
        g2 = g.copy()
        for n in g2:
            g2.nodes[n]["label"] = n
            g2.nodes[n]["community"] = int(g2.nodes[n].get("community", -1))
        nx.write_gexf(g2, gd / name)
        print("[gexf]", name)


def build_pyvis(G, comms):
    from pyvis.network import Network
    out_dir = HERE / "interactive"
    out_dir.mkdir(exist_ok=True)
    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="#222", select_menu=True,
                  filter_menu=True, cdn_resources="remote")
    smax = max(G.nodes[n]["strength"] for n in G)
    for n, d in G.nodes(data=True):
        subs, doms = community_label(G, comms[d["community"]])
        tip = (f"{n}\ntype: {d['type']}\n" + (f"topic: {d['category']}\n" if d["type"] == "subreddit" else
                                              f"hosting class: {d['domain_class']}\n")
               + f"top posts in graph: {d['strength']}\ndistinct partners: {d['degree']}\n"
               f"community C{d['community']} (lead: {subs[0] if subs else '-'})")
        net.add_node(n, label=n if (d["type"] == "subreddit" or d["strength"] > 60) else " ", title=tip,
                     color=PALETTE[d["community"] % len(PALETTE)], shape="square" if d["type"] == "subreddit" else "dot",
                     size=6 + 40 * math.sqrt(d["strength"] / smax), type=d["type"], community=f"C{d['community']}",
                     category=d["category"] or d["domain_class"], strength=int(d["strength"]))
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, value=d["weight"], title=f"{u} — {v}: {d['weight']} top posts", color="rgba(120,120,120,0.35)")
    net.set_options(json.dumps({
        "physics": {"solver": "forceAtlas2Based", "forceAtlas2Based": {"gravitationalConstant": -60, "springLength": 80,
                                                                        "springConstant": 0.05, "avoidOverlap": 0.4},
                    "stabilization": {"iterations": 400}},
        "interaction": {"hover": True, "navigationButtons": True, "multiselect": True, "tooltipDelay": 80},
        "edges": {"smooth": False, "scaling": {"min": 1, "max": 8}},
        "nodes": {"font": {"size": 14, "strokeWidth": 3}},
    }))
    path = out_dir / "network.html"
    net.write_html(str(path), notebook=False)
    # add a header explaining the controls
    html = path.read_text(encoding="utf-8")
    header = ("<div style='font-family:sans-serif;padding:8px 12px;background:#f4f6f8;border-bottom:1px solid #ccc'>"
              "<b>DAS732 A2 - I1 (Sidhanth Prabhu, BT2024027): Subreddit ↔ external-domain network</b> - "
              f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges. Squares = subreddits, dots = domains; colour = "
              "Louvain community; size ∝ √(top posts). Hover for details, scroll to zoom, drag to pan/move nodes, "
              "use <i>Select a Node</i> to highlight a neighbourhood and <i>Select a network item</i> to filter by "
              "type / community / category.</div>")
    html = html.replace("<body>", "<body>\n" + header, 1)
    path.write_text(html, encoding="utf-8")
    print("[html]", path.relative_to(ROOT))
    return path


def screenshot_pyvis(path, out):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1050}, device_scale_factor=2)
        pg.goto(path.resolve().as_uri())
        pg.wait_for_timeout(12000)   # let the physics stabilise
        pg.screenshot(path=str(out), full_page=True)
        b.close()
    print("[fig]", out.name)


def main():
    G = build_graph()
    comms = communities(G)
    st = graph_stats(G, comms)
    pd.Series(st).to_csv(PROC / "i1_graph_metrics.csv", header=["value"])
    print(pd.Series(st).to_string())
    rows = []
    for k, c in enumerate(comms):
        s, d = community_label(G, c)
        rows.append({"community": f"C{k}", "nodes": len(c), "subreddits": len(s), "domains": len(d),
                     "strength": sum(G.nodes[n]["strength"] for n in c), "top_subreddits": "; ".join(s[:6]),
                     "top_domains": "; ".join(d[:8])})
    pd.DataFrame(rows).to_csv(PROC / "i1_communities.csv", index=False)
    print(pd.DataFrame(rows).to_string())
    fig_stats(G, comms, st, IMG / "Fig_25_network_statistics.png")
    layouts = compute_layouts(G)
    met = pd.DataFrame({name: layout_metrics(G, pos, rt) for name, (pos, rt) in layouts.items()}).T
    t0 = time.perf_counter()
    pos_un = normalise_pos(nx.spectral_layout(G, weight="weight"))
    met.loc["Spectral (unnormalised, nx)"] = layout_metrics(G, pos_un, time.perf_counter() - t0)
    met.round(4).to_csv(PROC / "i1_layout_metrics.csv")
    print(met.to_string())
    fig_layouts(G, comms, layouts, IMG / "Fig_26_network_layouts.png")
    fig_layout_metrics(met, IMG / "Fig_27_network_layout_metrics.png")
    H = filter_graph(G)
    print(f"filtered: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges")
    fig_filter(G, H, IMG / "Fig_28_network_filtering.png")
    fig_projection(G, IMG / "Fig_29_subreddit_projection.png")
    export_gexf(G, H)
    html = build_pyvis(G, comms)
    screenshot_pyvis(html, IMG / "Fig_30_network_interactive.png")


if __name__ == "__main__":
    main()
