"""A1 (Reddit top posts, 50 subreddits, 2011-2024) cleaning + derivations for the InfoVis tasks.

Shared preprocessing (all members: Sidhanth Prabhu BT2024027, Shrey Modi BT2024125,
Parthsarati Samanta BT2024083).

Derived datasets
  (1) network      : bipartite subreddit <-> external domain graph (I1)
  (2) hierarchies  : three tabular->tree remodels for the zoomable treemap (I2b)
  (3) multivariate : stratified post sample with 7 axes + groups + k-means clusters (I2a)
  (4) time series  : monthly / quarterly / yearly series and per-post distributions (I3)

Run: python infovis/common/a1_preprocess.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parents[2]
A1 = ROOT / "data" / "a1"
OUT = ROOT / "data" / "processed" / "a1"
WEB = ROOT / "infovis" / "i2_web" / "data"
SEED = 42

# Topic grouping of the 50 communities (manual, by subreddit purpose; see preprocessing log).
CATEGORIES = {
    "Q&A and advice": ["AskReddit", "NoStupidQuestions", "explainlikeimfive", "askscience", "IAmA",
                       "relationship_advice", "personalfinance", "LifeProTips"],
    "Text humour and stories": ["tifu", "Jokes", "Showerthoughts", "WritingPrompts"],
    "News, science and tech": ["news", "worldnews", "nottheonion", "UpliftingNews", "technology",
                               "Futurology", "science", "space"],
    "Memes and GIFs": ["funny", "memes", "wholesomememes", "gifs"],
    "Photos and curiosities": ["pics", "aww", "EarthPorn", "OldSchoolCool", "mildlyinteresting",
                               "interestingasfuck", "creepy"],
    "Creative and lifestyle": ["Art", "food", "travel", "DIY", "GetMotivated"],
    "Entertainment and media": ["movies", "television", "Music", "listentothis", "gaming", "anime",
                                "books", "sports", "videos", "Documentaries"],
    "Knowledge and curiosity": ["todayilearned", "history", "dataisbeautiful", "InternetIsBeautiful"],
}
SUB2CAT = {s: c for c, subs in CATEGORIES.items() for s in subs}

# Domain normalisation: strip mobile/www prefixes, merge aliases of one platform.
DOMAIN_ALIASES = {"youtu.be": "youtube.com", "i.imgur.com": "imgur.com", "m.imgur.com": "imgur.com",
                  "v.redd.it": "redd.it", "i.redd.it": "redd.it", "preview.redd.it": "redd.it",
                  "reddit.com": "redd.it", "gfycat.com": "gfycat.com", "giant.gfycat.com": "gfycat.com",
                  "mobile.twitter.com": "twitter.com", "x.com": "twitter.com"}
VIDEO_HOSTS = ("gfycat", "streamable", "vimeo", "twitch")
MIN_DOMAIN_POSTS = 3       # network: keep domains with >= 3 top posts in the corpus
PC_PER_SUB = 40            # parallel coordinates: posts sampled per subreddit (2,000 rows)
LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg)


# ----------------------------------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------------------------------
REDDIT_HOSTS = {"redd.it", "reddit.com", "reddituploads.com", "redditmedia.com"}  # Reddit's own media hosting
SECOND_LEVEL = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp", "com.br",
                "co.in", "co.za", "com.mx", "com.ar", "com.sg", "com.tr", "co.kr", "com.cn"}


def registrable_domain(d: str) -> str:
    """Reduce a host name to its registrable domain (eTLD+1): cdna.artstation.com -> artstation.com,
    news.bbc.co.uk -> bbc.co.uk. Self-posts ('self.<sub>') and Reddit's media host are left unchanged."""
    if d.startswith("self.") or d == "redd.it":
        return d
    parts = d.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL:
        return ".".join(parts[-3:])
    reg = ".".join(parts[-2:])
    return "redd.it" if reg in REDDIT_HOSTS else reg


def domain_class(d: str) -> str:
    if d.startswith("self."):
        return "self post"
    if d == "redd.it":
        return "reddit-hosted media"
    if d == "imgur.com":
        return "imgur"
    if d == "youtube.com":
        return "youtube"
    if any(h in d for h in VIDEO_HOSTS):
        return "other video host"
    return "external website"


def load_clean() -> pd.DataFrame:
    files = sorted(f for f in A1.glob("*.csv") if f.name not in ("50_subreddits_list.csv", "reddit_top_posts_clean.csv"))
    df = pd.concat([pd.read_csv(f).assign(source_file=f.name) for f in files], ignore_index=True)
    log(f"- Raw merge: {len(df)} rows x {df.shape[1]} cols from {len(files)} subreddit files.")
    assert df["id"].is_unique
    log(f"- Duplicate post ids: {df['id'].duplicated().sum()}.")

    # Two timestamp formats exist (ISO, and M/D/YYYY H:MM in AskReddit) -> parse both.
    dt = pd.to_datetime(df["created_utc"], errors="coerce", format="ISO8601")
    bad = dt.isna()
    dt[bad] = pd.to_datetime(df.loc[bad, "created_utc"], format="%m/%d/%Y %H:%M")
    assert dt.notna().all()
    df["created_dt"] = dt
    log(f"- Timestamps: {int((~bad).sum())} ISO + {int(bad.sum())} M/D/YYYY H:MM parsed; "
        f"range {dt.min()} .. {dt.max()} UTC.")

    drop = ["num_awards", "crosspost_subreddits", "is_bot", "is_megathread", "body"]
    log(f"- Dropped columns: num_awards (all {int((df.num_awards == 0).sum())} zero), crosspost_subreddits "
        f"({100 * df.crosspost_subreddits.isna().mean():.2f}% missing), is_bot ({100 * df.is_bot.isna().mean():.2f}% missing), "
        f"is_megathread ({int(df.is_megathread.sum())} True), body ({100 * df.body.isna().mean():.2f}% missing).")
    df = df.drop(columns=drop)

    df["year"] = df.created_dt.dt.year
    df["month"] = df.created_dt.dt.to_period("M").astype(str)
    df["hour_utc"] = df.created_dt.dt.hour
    df["dec_year"] = df.year + (df.created_dt.dt.dayofyear - 1) / 365.25
    df["title_len"] = df.title.str.len()
    df["category"] = df.subreddit.map(SUB2CAT)
    assert df.category.notna().all(), df.loc[df.category.isna(), "subreddit"].unique()
    d = df.domain.str.lower().str.replace(r"^(www\.|m\.|old\.|mobile\.|en\.m\.)", "", regex=True)
    d = d.replace(DOMAIN_ALIASES)
    df["domain_norm"] = d.map(registrable_domain)
    log(f"- Domains: {df.domain.nunique()} raw -> {df.domain_norm.nunique()} after prefix stripping, alias merging "
        f"and reduction to the registrable domain (eTLD+1).")
    df["domain_class"] = df.domain_norm.map(domain_class)
    df["log10_score"] = np.log10(df.score)
    df["era"] = pd.cut(df.year, bins=[2010, 2016, 2018, 2020, 2022, 2024],
                       labels=["2011-16", "2017-18", "2019-20", "2021-22", "2023-24"]).astype(str)
    log(f"- Rows kept: {len(df)} (no rows dropped; the corpus is the top tail by construction, so extremes are kept).")
    log(f"- Posts per year: {df.year.value_counts().sort_index().to_dict()}")
    return df


# ----------------------------------------------------------------------------------------------
# (1) Network
# ----------------------------------------------------------------------------------------------
def build_network(df: pd.DataFrame) -> None:
    ext = df[df.domain_class.isin(["imgur", "youtube", "other video host", "external website"])]
    counts = ext.domain_norm.value_counts()
    keep = counts[counts >= MIN_DOMAIN_POSTS].index
    e = (ext[ext.domain_norm.isin(keep)].groupby(["subreddit", "domain_norm"])
         .agg(weight=("id", "size"), median_score=("score", "median")).reset_index())
    nodes_s = (df.groupby("subreddit").agg(posts=("id", "size"), subscribers=("subscribers", "first"))
               .reset_index().rename(columns={"subreddit": "id"}))
    nodes_s = nodes_s[nodes_s.id.isin(e.subreddit)]
    nodes_s["type"] = "subreddit"
    nodes_s["category"] = nodes_s.id.map(SUB2CAT)
    nodes_d = (ext[ext.domain_norm.isin(keep)].groupby("domain_norm")
               .agg(posts=("id", "size"), domain_class=("domain_class", "first")).reset_index()
               .rename(columns={"domain_norm": "id"}))
    nodes_d["type"] = "domain"
    nodes = pd.concat([nodes_s, nodes_d], ignore_index=True)
    out = OUT / "network"
    out.mkdir(parents=True, exist_ok=True)
    nodes.to_csv(out / "nodes.csv", index=False)
    e.rename(columns={"subreddit": "source", "domain_norm": "target"}).to_csv(out / "edges.csv", index=False)
    log(f"- Network: posts linking to external domains = {len(ext)} of {len(df)}; distinct external domains "
        f"= {ext.domain_norm.nunique()}; kept domains with >= {MIN_DOMAIN_POSTS} posts = {len(keep)}.")
    log(f"  Nodes = {len(nodes)} ({len(nodes_s)} subreddits + {len(nodes_d)} domains); edges = {len(e)}; "
        f"total edge weight = {int(e.weight.sum())} posts.")
    no_ext = sorted(set(df.subreddit) - set(nodes_s.id))
    log(f"  Subreddits with no qualifying external link (absent from graph): {no_ext}")


# ----------------------------------------------------------------------------------------------
# (2) Hierarchies for the treemap
# ----------------------------------------------------------------------------------------------
def to_tree(df: pd.DataFrame, levels: list[str], name: str) -> dict:
    """Nest a flat table into {name, children[...]}; leaves carry posts / score / comments sums."""
    def rec(sub: pd.DataFrame, depth: int, label: str) -> dict:
        if depth == len(levels):
            return {"name": label, "posts": int(len(sub)), "score": int(sub.score.sum()),
                    "comments": int(sub.num_comments.sum())}
        kids = [rec(g, depth + 1, str(k)) for k, g in sub.groupby(levels[depth], sort=True, observed=True)]
        return {"name": label, "children": kids}
    return rec(df, 0, name)


def build_hierarchies(df: pd.DataFrame) -> None:
    specs = {
        "h1_topic": (["category", "subreddit", "post_type"], "All posts by topic"),
        "h2_media": (["post_type", "domain_class", "category", "subreddit"], "All posts by media"),
        "h3_time": (["era", "year", "category", "subreddit"], "All posts by time"),
    }
    WEB.mkdir(parents=True, exist_ok=True)
    meta = []
    for key, (levels, title) in specs.items():
        tree = to_tree(df, levels, title)
        (WEB / f"treemap_{key}.json").write_text(json.dumps(tree))
        n_leaves = len(df.groupby(levels, observed=True))
        meta.append({"key": key, "levels": levels, "title": title, "leaves": n_leaves})
        log(f"- Treemap hierarchy {key}: {' -> '.join(levels)}; leaves = {n_leaves}.")
    (WEB / "treemap_meta.json").write_text(json.dumps(meta, indent=1))


# ----------------------------------------------------------------------------------------------
# (3) Multivariate table for parallel coordinates
# ----------------------------------------------------------------------------------------------
PC_DIMS = ["dec_year", "hour_utc", "title_len", "upvote_ratio", "score", "num_comments", "num_crossposts"]


def build_parcoords(df: pd.DataFrame) -> None:
    rng = np.random.default_rng(SEED)
    idx = []
    for _, g in df.groupby("subreddit"):
        idx.extend(rng.choice(g.index.values, size=min(PC_PER_SUB, len(g)), replace=False))
    s = df.loc[sorted(idx)].copy()
    # k-means on min-max normalised axes; skewed counts are log-transformed first (same as axis scales)
    X = s[PC_DIMS].astype(float).copy()
    X["score"] = np.log10(X.score)
    X["num_comments"] = np.log10(X.num_comments + 1)
    X["num_crossposts"] = np.log10(X.num_crossposts + 1)
    Xn = ((X - X.min()) / (X.max() - X.min())).values
    sil = {}
    for k in range(3, 9):
        lab = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(Xn)
        sil[k] = silhouette_score(Xn, lab, random_state=SEED)
    k_best = max(sil, key=sil.get)
    km = KMeans(n_clusters=k_best, n_init=10, random_state=SEED).fit(Xn)
    s["cluster"] = km.labels_
    log(f"- Parallel coordinates: stratified sample {PC_PER_SUB}/subreddit (seed {SEED}) = {len(s)} posts; "
        f"axes = {PC_DIMS}; log10 transform for score, log10(x+1) for comments and crossposts.")
    log(f"  k-means silhouette by k: { {k: round(v, 3) for k, v in sil.items()} } -> k = {k_best}.")
    cols = ["id", "subreddit", "category", "post_type", "domain_class", "title", "cluster"] + PC_DIMS
    rec = s[cols].copy()
    rec["dec_year"] = rec.dec_year.round(3)
    rec["title"] = rec.title.str.slice(0, 120)
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "parcoords_posts.json").write_text(rec.to_json(orient="records"))
    rec.to_csv(OUT / "parcoords_posts.csv", index=False)
    cent = pd.DataFrame(km.cluster_centers_, columns=PC_DIMS)
    cent["size"] = np.bincount(km.labels_)
    cent.round(3).to_csv(OUT / "parcoords_kmeans_centroids.csv", index_label="cluster")
    log(f"  cluster sizes: {np.bincount(km.labels_).tolist()}")


# ----------------------------------------------------------------------------------------------
# (4) Time series / distributions
# ----------------------------------------------------------------------------------------------
def build_timeseries(df: pd.DataFrame) -> None:
    t0, t1 = "2016-01", "2024-08"   # before 2016 fewer than 50 posts/month in total; Sep 2024 is partial
    d = df[(df.month >= t0) & (df.month <= t1)]
    months = pd.period_range(t0, t1, freq="M").astype(str)
    for by in ["category", "subreddit"]:
        m = d.groupby([by, "month"]).size().unstack(fill_value=0).reindex(columns=months, fill_value=0)
        m.to_csv(OUT / f"ts_monthly_posts_by_{by}.csv")
        med = d.groupby([by, "month"]).log10_score.median().unstack().reindex(columns=months)
        med.to_csv(OUT / f"ts_monthly_median_log10score_by_{by}.csv")
    q = d.assign(quarter=d.created_dt.dt.to_period("Q").astype(str)).groupby(["category", "quarter"]).size().unstack(fill_value=0)
    q.to_csv(OUT / "ts_quarterly_posts_by_category.csv")
    y = df.groupby(["category", "year"]).size().unstack(fill_value=0)
    y.to_csv(OUT / "ts_yearly_posts_by_category.csv")
    log(f"- Time series window {t0}..{t1} ({len(months)} months, {len(d)} posts = "
        f"{100 * len(d) / len(df):.1f}% of corpus); months with zero posts in a category are true zeros.")
    df.to_csv(OUT / "posts_clean.csv", index=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_clean()
    log(f"- Topic categories: { {c: len(s) for c, s in CATEGORIES.items()} }")
    log(f"- domain_class counts: {df.domain_class.value_counts().to_dict()}")
    build_network(df)
    build_hierarchies(df)
    build_parcoords(df)
    build_timeseries(df)
    (OUT / "a1_preprocess_log.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
