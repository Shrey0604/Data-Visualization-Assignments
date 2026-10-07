"""Scripted high-resolution screenshots of the I2 D3 views (Playwright, Chromium, device scale factor 2).

Owner: Parthsarati Samanta (BT2024083)

Starts a local http.server on this folder, drives the pages through their window.pc / window.tm hooks
(the same functions the UI controls call) and writes images/Fig_31*.png .. Fig_34*.png plus
data/processed/i2_*.csv metric tables.

Run: python infovis/i2_web/screenshots.py
"""
from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMG = ROOT / "images"
PROC = ROOT / "data" / "processed"
PORT = 8766
VIEW = {"width": 1600, "height": 900}


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def shot(page, name):
    page.wait_for_timeout(900)
    page.screenshot(path=str(IMG / name), full_page=True)
    print("[fig]", name)


def parcoords(b):
    pg = b.new_page(viewport=VIEW, device_scale_factor=2)
    pg.goto(f"http://127.0.0.1:{PORT}/parcoords/index.html")
    pg.wait_for_function("window.pcReady === true")
    rows = []

    def rec(state, **kw):
        s = pg.evaluate("pc.stats()")
        rows.append({"state": state, "selected": s["n"], **{f"sel_{k}": v for k, v in s["by"].items()}, **kw})

    pg.evaluate("pc.setGroup('cluster'); pc.setBeta(0)")
    rec("unbundled, k-means colour"); shot(pg, "Fig_31a_parcoords_unbundled.png")
    pg.evaluate("pc.setBeta(0.85)")
    rec("bundled beta=0.85, k-means"); shot(pg, "Fig_31b_parcoords_bundled_kmeans.png")
    pg.evaluate("pc.setGroup('category'); pc.setBeta(0.85); pc.spine(true)")
    rec("bundled beta=0.85, topic + centroid lines"); shot(pg, "Fig_31c_parcoords_bundled_topic.png")

    pg.evaluate("pc.reset()")
    pg.evaluate("pc.setGroup('post_type')")
    pg.evaluate("pc.brush('score', 60000, 500000)")
    rec("brush score >= 60k (post type colour)");
    pg.evaluate("pc.brush('post_type', 'text', 'text')")
    rec("brush score >= 60k AND text"); shot(pg, "Fig_32a_parcoords_brush_score_text.png")
    pg.evaluate("pc.reset(); pc.setGroup('category')")
    pg.evaluate("pc.brush('num_comments', 3000, 80000)")
    rec("brush comments >= 3000")
    pg.evaluate("pc.brush('upvote_ratio', 0.55, 0.85)")
    rec("brush comments >= 3000 AND ratio <= 0.85"); shot(pg, "Fig_32b_parcoords_brush_controversial.png")
    pg.evaluate("pc.reset(); pc.setGroup('post_type'); pc.setBeta(0.5)")
    pg.evaluate("pc.reorder(['post_type','score','num_comments','upvote_ratio','num_crossposts','title_len','hour_utc','dec_year'])")
    pg.evaluate("pc.brush('dec_year', 2021, 2025)")
    rec("reordered + beta 0.5 + brush year >= 2021"); shot(pg, "Fig_32c_parcoords_reordered.png")
    pd.DataFrame(rows).to_csv(PROC / "i2_parcoords_states.csv", index=False)
    pg.close()


def treemap(b):
    pg = b.new_page(viewport=VIEW, device_scale_factor=2)
    pg.goto(f"http://127.0.0.1:{PORT}/treemap/index.html")
    pg.wait_for_function("window.tmReady === true")
    base = {"measure": "posts", "tiling": "squarify", "sort": "value"}
    # hierarchy remodels (root views)
    for k, (h, tag) in enumerate([("h1_topic", "h1_topic"), ("h2_media", "h2_media"), ("h3_time", "h3_time")]):
        pg.evaluate("opts => tm.set(opts, [])", {**base, "hier": h})
        shot(pg, f"Fig_33{'abc'[k]}_treemap_{tag}.png")
    # zoom states
    pg.evaluate("opts => tm.set(opts, [])", {**base, "hier": "h1_topic"})
    pg.evaluate("tm.zoomPath(['Entertainment and media'])")
    shot(pg, "Fig_33d_treemap_zoom_entertainment.png")
    pg.evaluate("opts => tm.set(opts, [])", {**base, "hier": "h3_time", "sort": "name", "measure": "comments"})
    pg.evaluate("tm.zoomPath(['2019-20'])"); pg.wait_for_timeout(900)
    pg.evaluate("tm.zoomPath(['2019-20','2020'])")
    shot(pg, "Fig_33e_treemap_zoom_2020_comments.png")
    pg.evaluate("opts => tm.set(opts, [])", {**base, "hier": "h2_media", "measure": "score"})
    pg.evaluate("tm.zoomPath(['link'])")
    shot(pg, "Fig_33f_treemap_zoom_link_score.png")

    # tiling strategies on the same view (H1 root, size = total score)
    tilings = ["squarify", "binary", "slice", "dice", "sliceDice"]
    for k, t in enumerate(tilings):
        pg.evaluate("opts => tm.set(opts, [])", {"hier": "h1_topic", "measure": "score", "tiling": t, "sort": "value"})
        shot(pg, f"Fig_34{'abcde'[k]}_treemap_tiling_{t}.png")

    # metrics table: every tiling x sort x view
    views = [("h1_topic", [], "H1 root (8 topics)"), ("h1_topic", ["Entertainment and media"], "H1 Entertainment (10 subreddits)"),
             ("h2_media", [], "H2 root (4 post types)"), ("h3_time", [], "H3 root (5 eras)"),
             ("h3_time", ["2017-18"], "H3 era 2017-18 (2 years)")]
    rows = []
    for t in tilings:
        for srt in ["value", "name"]:
            for h, path, label in views:
                m = pg.evaluate("([o, p]) => tm.set(o, p)", [{"hier": h, "measure": "posts", "tiling": t, "sort": srt}, path])
                rows.append({"tiling": t, "sort": srt, "view": label, **{k: m[k] for k in ["n", "mean", "median", "max", "tau"]}})
    df = pd.DataFrame(rows).round(3)
    df.to_csv(PROC / "i2_treemap_tiling_metrics.csv", index=False)
    print(df.groupby(["tiling", "sort"])[["mean", "max", "tau"]].mean().round(2).to_string())
    pg.close()


def main():
    httpd = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        parcoords(b)
        treemap(b)
        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
