// I2b - Zoomable treemap with switchable hierarchy remodels, size measures, tiling strategies and sort order.
// Owner: Parthsarati Samanta (BT2024083). D3.js v7, no build step.
// Zooming follows the d3 "zoomable treemap" pattern: every node's children are laid out in the full
// viewport rectangle and then scaled into the parent's box, so a zoomed-in level keeps the tiling's
// aspect-ratio behaviour at screen size.
"use strict";

const TILES = { squarify: d3.treemapSquarify, binary: d3.treemapBinary, slice: d3.treemapSlice,
                dice: d3.treemapDice, sliceDice: d3.treemapSliceDice };
const HEADER = 30;
const state = { hier: "h1_topic", measure: "posts", tiling: "squarify", sort: "value" };
const cache = {};
let W, H, svg, group, x, y, root, current;
const fmt = d3.format(",");

function init() {
  W = Math.max(1100, window.innerWidth - 36);
  H = 660;
  svg = d3.select("#chart").append("svg").attr("width", W).attr("height", H + HEADER)
    .attr("viewBox", [0, -HEADER, W, H + HEADER]).style("font", "12px sans-serif");
  x = d3.scaleLinear().rangeRound([0, W]);
  y = d3.scaleLinear().rangeRound([0, H]);
  for (const id of ["hier", "measure", "tiling", "sort"]) {
    d3.select("#" + id).on("change", e => { state[id] = e.target.value; rebuild(); });
  }
  load("h1_topic").then(h1 => {
    for (const t of h1.children) for (const sub of t.children) SUB2TOPIC[sub.name] = t.name;
    return rebuild();
  }).then(() => { window.tm = api; window.tmReady = true; });
}

async function load(key) {
  if (!cache[key]) cache[key] = await d3.json(`../data/treemap_${key}.json`);
  return cache[key];
}

function tile(node, x0, y0, x1, y1) {
  TILES[state.tiling](node, 0, 0, W, H);
  for (const c of node.children) {
    c.x0 = x0 + c.x0 / W * (x1 - x0);
    c.x1 = x0 + c.x1 / W * (x1 - x0);
    c.y0 = y0 + c.y0 / H * (y1 - y0);
    c.y1 = y0 + c.y1 / H * (y1 - y0);
  }
}

async function rebuild(path) {
  const data = await load(state.hier);
  const keepPath = path ?? (current ? current.ancestors().reverse().slice(1).map(d => d.data.name) : []);
  const h = d3.hierarchy(data).sum(d => d.children ? 0 : d[state.measure]);
  h.sort(state.sort === "value" ? (a, b) => b.value - a.value : (a, b) => d3.ascending(a.data.name, b.data.name));
  root = d3.treemap().tile(tile)(h);
  // try to stay at the same place in the new hierarchy (only if the path still exists)
  let node = root;
  for (const name of keepPath) {
    const nxt = (node.children || []).find(c => c.data.name === name);
    if (!nxt || !nxt.children) break;
    node = nxt;
  }
  current = node;
  x.domain([node.x0, node.x1]); y.domain([node.y0, node.y1]);
  svg.selectAll("g.view").remove();
  group = svg.append("g").attr("class", "view").call(render, node);
  updateChrome();
}

// Stable colours per level type, identical in all three remodels (a topic / post type keeps its colour).
const TOPICS = ["Creative and lifestyle", "Entertainment and media", "Knowledge and curiosity", "Memes and GIFs",
                "News, science and tech", "Photos and curiosities", "Q&A and advice", "Text humour and stories"];
const PAL = {
  topic: d3.scaleOrdinal(TOPICS, d3.schemeTableau10),
  "post type": d3.scaleOrdinal(["image", "link", "text", "video"], ["#0072B2", "#E69F00", "#009E73", "#D55E00"]),
  "hosting class": d3.scaleOrdinal(["external website", "imgur", "other video host", "reddit-hosted media", "self post", "youtube"],
                                   d3.schemeSet2),
  era: d3.scaleOrdinal(["2011-16", "2017-18", "2019-20", "2021-22", "2023-24"], d3.quantize(d3.interpolateViridis, 6).slice(0, 5)),
};
let SUB2TOPIC = {};

function nodeColor(d) {
  const lvl = levelNames()[d.depth - 1];
  const name = d.data.name;
  if (lvl === "year") return d3.color(d3.interpolateViridis(Math.min(1, (+name - 2011) / 14)));
  if (lvl === "subreddit") {
    const base = d3.color(PAL.topic(SUB2TOPIC[name] || TOPICS[0]));
    const sibs = d.parent.children, t = sibs.length > 1 ? sibs.indexOf(d) / (sibs.length - 1) : 0.5;
    return d3.color(d3.interpolateRgb(base.darker(0.7), base.brighter(0.9))(t));
  }
  return d3.color((PAL[lvl] || PAL.topic)(name));
}

function render(g, node) {
  const kids = node.children;
  const items = g.selectAll("g.node").data(kids.concat(node)).join("g").attr("class", "node");
  items.filter(d => d === node ? d.parent : d.children)
    .attr("cursor", "pointer")
    .on("click", (e, d) => d === node ? zoomTo(d.parent) : zoomTo(d));
  items.append("rect")
    .attr("fill", d => d === node ? "#e9edf1" : nodeColor(d))
    .attr("stroke", "#fff").attr("stroke-width", d => d === node ? 0 : 1.5);
  // next-level structure as thin outlines inside each child
  items.filter(d => d !== node && d.children).each(function (d) {
    d3.select(this).selectAll("rect.inner").data(d.children).join("rect").attr("class", "inner")
      .attr("fill", "none").attr("stroke", "rgba(255,255,255,0.55)").attr("stroke-width", 0.8);
  });
  items.filter(d => d !== node).append("rect").attr("class", "labbg").attr("fill", d => nodeColor(d)).attr("rx", 2);
  const ink = d => d === node ? "#1f2328" : (d3.hsl(nodeColor(d)).l > 0.6 ? "#1f2328" : "#fff");
  const halo = d => d === node ? "#e9edf1" : nodeColor(d).formatHex();
  items.append("text").attr("class", "lab").attr("x", 5).attr("y", 15).attr("font-weight", 600)
    .attr("fill", ink).attr("stroke", halo).attr("stroke-width", 4).attr("paint-order", "stroke").attr("stroke-linejoin", "round");
  items.append("text").attr("class", "val").attr("x", 5).attr("y", 29).attr("font-size", 11)
    .attr("fill", ink).attr("stroke", halo).attr("stroke-width", 4).attr("paint-order", "stroke").attr("stroke-linejoin", "round");
  items.on("mouseover", (e, d) => showTip(e, d, node)).on("mousemove", moveTip).on("mouseout", hideTip);
  g.call(position, node);
}

function position(g, node) {
  g.selectAll("g.node")
    .attr("transform", d => d === node ? `translate(0,${-HEADER})` : `translate(${x(d.x0)},${y(d.y0)})`)
    .each(function (d) {
      const sel = d3.select(this);
      const w = d === node ? W : Math.max(0, x(d.x1) - x(d.x0));
      const h = d === node ? HEADER : Math.max(0, y(d.y1) - y(d.y0));
      sel.select("rect").attr("width", w).attr("height", h);
      sel.selectAll("rect.inner")
        .attr("x", c => x(c.x0) - x(d.x0)).attr("y", c => y(c.y0) - y(d.y0))
        .attr("width", c => Math.max(0, x(c.x1) - x(c.x0))).attr("height", c => Math.max(0, y(c.y1) - y(c.y0)));
      const name = d === node ? d.ancestors().reverse().map(a => a.data.name).join(" / ") : d.data.name;
      const l1 = fitText(sel.select("text.lab"), name, w - 8, h >= 18);
      const pct = d === node ? "" : ` (${(100 * d.value / node.value).toFixed(1)} %)`;
      const l2 = fitText(sel.select("text.val"), d === node ? `${fmtVal(d.value)} ${unit()} - click to zoom out` : `${fmtVal(d.value)}${pct}`,
        w - 8, h >= 34 && d !== node);
      // opaque label plate so next-level outlines never run through the text
      if (d !== node) {
        const bw = Math.min(w - 2, Math.max(l1.length * 7.2, l2.length * 6.4) + 8);
        sel.select("rect.labbg").attr("x", 1).attr("y", 1).attr("width", l1 ? Math.max(0, bw) : 0)
          .attr("height", l1 ? (l2 ? 34 : 20) : 0);
      }
      if (d === node) sel.select("text.val").attr("x", W - 6).attr("y", 19).attr("text-anchor", "end");
    });
}

function fitText(t, s, w, show) {
  if (!show || w < 24) { t.text(""); return ""; }
  const maxChars = Math.floor(w / 6.6);
  const out = s.length > maxChars ? s.slice(0, Math.max(1, maxChars - 1)) + "…" : s;
  t.text(out);
  return out;
}

function fmtVal(v) { return state.measure === "posts" ? fmt(v) : d3.format(".3~s")(v); }
function unit() { return { posts: "posts", score: "upvotes", comments: "comments" }[state.measure]; }

function zoomTo(target) {
  if (!target || target === current || !target.children) return;
  const goingIn = target.depth > current.depth;
  const g0 = group.attr("pointer-events", "none");
  const g1 = group = goingIn ? svg.append("g").attr("class", "view") : svg.insert("g", "g.view").attr("class", "view");
  g1.call(render, target);
  const from = current;
  x.domain([target.x0, target.x1]); y.domain([target.y0, target.y1]);
  if (goingIn) {
    g1.call(position0, from, target);
    svg.transition().duration(750)
      .call(t => g0.transition(t).remove().call(position, from))
      .call(t => g1.transition(t).attrTween("opacity", () => d3.interpolate(0, 1)).call(position, target));
  } else {
    svg.transition().duration(750)
      .call(t => g0.transition(t).remove().attrTween("opacity", () => d3.interpolate(1, 0)).call(position, from))
      .call(t => g1.transition(t).call(position, target));
  }
  current = target;
  updateChrome();
}

function position0(g, from, target) {
  // start the zoom-in transition from the old scale so the clicked box grows smoothly
  const xs = x.domain(), ys = y.domain();
  x.domain([from.x0, from.x1]); y.domain([from.y0, from.y1]);
  g.call(position, target);
  x.domain(xs); y.domain(ys);
}

function updateChrome() {
  const anc = current.ancestors().reverse();
  const c = d3.select("#crumbs").html("");
  anc.forEach((a, i) => {
    if (i) c.append("span").text("  ›  ");
    c.append("span").attr("class", i === anc.length - 1 ? "here" : "crumb").text(a.data.name)
      .on("click", () => { if (a !== current) zoomTo(a); });
  });
  const m = viewMetrics();
  d3.select("#metrics").html(
    `Level: <b>${["root", ...levelNames()][current.depth] ?? "-"}</b> → children: <b>${levelNames()[current.depth] ?? "-"}</b> · ` +
    `${m.n} rectangles · aspect ratio (long/short side) mean <b>${m.mean.toFixed(2)}</b>, median ${m.median.toFixed(2)}, ` +
    `max <b>${m.max.toFixed(1)}</b> · order preservation (Kendall τ between sort order and reading order) <b>${m.tau.toFixed(2)}</b> · ` +
    `tiling <b>${state.tiling}</b>, size = ${unit()}`);
  window.tmMetrics = m;
}

function levelNames() {
  return { h1_topic: ["topic", "subreddit", "post type"], h2_media: ["post type", "hosting class", "topic", "subreddit"],
           h3_time: ["era", "year", "topic", "subreddit"] }[state.hier];
}

function viewMetrics() {
  const kids = current.children;
  const ar = kids.map(d => {
    const w = (d.x1 - d.x0) / (current.x1 - current.x0) * W, h = (d.y1 - d.y0) / (current.y1 - current.y0) * H;
    return Math.max(w / h, h / w);
  }).filter(Number.isFinite);
  // reading order: top-to-bottom, then left-to-right (rows of ~equal y0)
  const read = kids.map((d, i) => ({ i, y0: Math.round(d.y0 * 1e6), x0: d.x0 }))
    .sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0).map(d => d.i);
  const readX = kids.map((d, i) => ({ i, x0: Math.round(d.x0 * 1e6), y0: d.y0 }))
    .sort((a, b) => a.x0 - b.x0 || a.y0 - b.y0).map(d => d.i);
  const tau = Math.max(kendall(read), kendall(readX));
  return { n: kids.length, mean: d3.mean(ar), median: d3.median(ar), max: d3.max(ar), tau };
}

function kendall(perm) {
  let c = 0, d = 0;
  for (let i = 0; i < perm.length; i++) for (let j = i + 1; j < perm.length; j++) (perm[i] < perm[j] ? c++ : d++);
  return (c + d) ? (c - d) / (c + d) : 1;
}

// ---------------------------------------------------------------- tooltip
const tip = d3.select("#tip");
function showTip(e, d, node) {
  if (d === node) {
    tip.style("opacity", 1).html(`<b>${d.ancestors().reverse().map(a => a.data.name).join(" / ")}</b><br>click to zoom out`);
  } else {
    const leaves = d.leaves().length;
    tip.style("opacity", 1).html(
      `<b>${d.ancestors().reverse().slice(1).map(a => a.data.name).join(" / ")}</b><br>` +
      `${fmt(d.value)} ${unit()}<br>${(100 * d.value / d.parent.value).toFixed(1)} % of ${d.parent.data.name}<br>` +
      `${(100 * d.value / root.value).toFixed(2)} % of all posts' ${unit()}<br>${leaves} leaf rectangle(s)` +
      (d.children ? "<br><i>click to zoom in</i>" : ""));
  }
  moveTip(e);
}
function moveTip(e) { tip.style("left", (e.clientX + 14) + "px").style("top", (e.clientY + 12) + "px"); }
function hideTip() { tip.style("opacity", 0); }

// ---------------------------------------------------------------- API for scripted screenshots
const api = {
  async set(opts, path = []) {
    Object.assign(state, opts);
    for (const k of Object.keys(opts)) d3.select("#" + k).property("value", opts[k]);
    await rebuild(path);
    return window.tmMetrics;
  },
  zoomPath(path) {
    let n = root;
    for (const name of path) { n = n.children.find(c => c.data.name === name); }
    zoomTo(n);
    return window.tmMetrics;
  },
  metrics() { return window.tmMetrics; },
};

init();
