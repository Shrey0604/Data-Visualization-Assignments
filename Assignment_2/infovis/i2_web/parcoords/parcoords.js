// I2a - Parallel coordinates with edge bundling, brushing on every axis and drag-to-reorder axes.
// Owner: Parthsarati Samanta (BT2024083). D3.js v7, no build step.
"use strict";

const DIMS = [
  { key: "dec_year", label: "Post date (year)", type: "linear", fmt: d3.format("d") },
  { key: "hour_utc", label: "Hour posted (UTC)", type: "linear", fmt: d3.format("d") },
  { key: "post_type", label: "Post type", type: "ordinal" },
  { key: "title_len", label: "Title length (chars)", type: "linear", fmt: d3.format("d") },
  { key: "upvote_ratio", label: "Upvote ratio", type: "linear", fmt: d3.format(".2f") },
  { key: "score", label: "Score (upvotes, log)", type: "log", fmt: d3.format("~s") },
  { key: "num_comments", label: "Comments (symlog)", type: "symlog", fmt: d3.format("~s") },
  { key: "num_crossposts", label: "Crossposts (symlog)", type: "symlog", fmt: d3.format("~s") },
];
const GROUP_LABEL = { cluster: "k-means cluster", category: "Topic category", post_type: "Post type" };
const GREY = "#d5d9de";

const state = { beta: 0, group: "cluster", order: DIMS.map(d => d.key), brushes: new Map(), spine: false };
let data, x, y = {}, centroids, color, lines, spines, axesG, dimByKey, innerW, innerH, svg, root;
const dragging = {};

const margin = { top: 78, right: 250, bottom: 18, left: 46 };

d3.json("../data/parcoords_posts.json").then(raw => {
  data = raw;
  data.forEach(d => { d.cluster = "C" + d.cluster; });
  dimByKey = Object.fromEntries(DIMS.map(d => [d.key, d]));
  d3.select("#total").text(data.length);
  build();
  window.pc = api;            // hooks for the scripted Playwright screenshots
  window.pcReady = true;
});

function build() {
  const W = Math.max(1100, window.innerWidth - 30), H = 640;
  innerW = W - margin.left - margin.right;
  innerH = H - margin.top - margin.bottom;
  svg = d3.select("#chart").append("svg").attr("width", W).attr("height", H);
  root = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  for (const d of DIMS) {
    const vals = data.map(r => r[d.key]);
    if (d.type === "ordinal") {
      y[d.key] = d3.scalePoint().domain(["image", "link", "text", "video"]).range([innerH, 0]).padding(0.3);
    } else if (d.type === "log") {
      y[d.key] = d3.scaleLog().domain(d3.extent(vals)).range([innerH, 0]).nice();
    } else if (d.type === "symlog") {
      y[d.key] = d3.scaleSymlog().constant(1).domain([0, d3.max(vals)]).range([innerH, 0]);
    } else {
      y[d.key] = d3.scaleLinear().domain(d3.extent(vals)).range([innerH, 0]).nice();
    }
  }
  x = d3.scalePoint().domain(state.order).range([0, innerW]);

  lines = root.append("g").attr("class", "lines").attr("fill", "none");
  spines = root.append("g").attr("class", "spines").attr("fill", "none");
  axesG = root.append("g").attr("class", "axes");
  root.append("g").attr("class", "legend");
  setGroup(state.group);
  drawAxes();

  d3.select("#group").on("change", e => setGroup(e.target.value));
  d3.select("#beta").on("input", e => setBeta(+e.target.value));
  d3.select("#showSpine").on("change", e => { state.spine = e.target.checked; drawSpines(); });
  d3.select("#reset").on("click", reset);
}

// ---------------------------------------------------------------- groups, colours, centroids
function setGroup(g) {
  state.group = g;
  d3.select("#group").property("value", g);
  const keys = Array.from(new Set(data.map(d => d[g]))).sort();
  const scheme = g === "category" ? d3.schemeTableau10 : g === "post_type"
    ? ["#0072B2", "#E69F00", "#009E73", "#D55E00"] : ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"];
  color = d3.scaleOrdinal().domain(keys).range(scheme);
  computeCentroids();
  drawLines();
  drawLegend(keys);
}

function computeCentroids() {
  // centroid of each group on each axis, in pixel space (so log / ordinal axes are handled uniformly)
  centroids = d3.rollup(data, v => Object.fromEntries(DIMS.map(d => [d.key, d3.mean(v, r => y[d.key](r[d.key]))])),
    r => r[state.group]);
}

function px(k) { return dragging[k] ?? x(k); }

function pathPoints(r) {
  const c = centroids.get(r[state.group]);
  const pts = [];
  const ord = state.order;
  for (let i = 0; i < ord.length; i++) {
    const k = ord[i], x0 = px(k), y0 = y[k](r[k]);
    pts.push([x0, y0]);
    if (i < ord.length - 1) {
      const k1 = ord[i + 1], x1 = px(k1), y1 = y[k1](r[k1]);
      for (const t of [0.25, 0.75]) {
        const straight = y0 + t * (y1 - y0);
        const bundled = c[k] + t * (c[k1] - c[k]);
        pts.push([x0 + t * (x1 - x0), (1 - state.beta) * straight + state.beta * bundled]);
      }
    }
  }
  return pts;
}

const lineGen = d3.line().curve(d3.curveMonotoneX);

function drawLines() {
  lines.selectAll("path").data(data, d => d.id).join("path")
    .attr("d", d => lineGen(pathPoints(d)))
    .on("mouseover", (e, d) => showTip(e, d))
    .on("mousemove", e => moveTip(e))
    .on("mouseout", (e) => hideTip(e));
  applyBrushStyle();
  drawSpines();
}

function drawSpines() {
  const data_ = state.spine ? Array.from(centroids, ([k, c]) => ({ k, c })) : [];
  spines.selectAll("path").data(data_, d => d.k).join("path")
    .attr("stroke", d => d3.color(color(d.k)).darker(0.8))
    .attr("stroke-width", 3.2).attr("stroke-dasharray", "7,4")
    .attr("d", d => d3.line()(state.order.map(k => [px(k), d.c[k]])));
}

function selected(r) {
  for (const [k, [a, b]] of state.brushes) {
    const v = y[k](r[k]);
    if (v < a || v > b) return false;
  }
  return true;
}

function applyBrushStyle() {
  let n = 0;
  lines.selectAll("path").each(function (d) {
    const s = selected(d);
    d.__sel = s;
    if (s) n++;
  });
  const anyBrush = state.brushes.size > 0;
  lines.selectAll("path")
    .attr("stroke", d => d.__sel ? color(d[state.group]) : GREY)
    .attr("stroke-opacity", d => d.__sel ? (anyBrush ? 0.75 : 0.32) : 0.12)
    .attr("stroke-width", d => d.__sel && anyBrush ? 1.1 : 0.8);
  lines.selectAll("path").filter(d => d.__sel).raise();
  d3.select("#count").text(n);
  const desc = Array.from(state.brushes, ([k, [a, b]]) => {
    const d = dimByKey[k];
    if (d.type === "ordinal") {
      const cats = y[k].domain().filter(c => y[k](c) >= a && y[k](c) <= b);
      return `${d.label}: ${cats.join("/")}`;
    }
    return `${d.label}: ${d.fmt(y[k].invert(b))}–${d.fmt(y[k].invert(a))}`;
  });
  d3.select("#brushInfo").text(desc.length ? "Brushes → " + desc.join(" · ") : "");
  updateLegendCounts();
}

// ---------------------------------------------------------------- axes, brushing, drag-reorder
function drawAxes() {
  const g = axesG.selectAll("g.dim").data(state.order.map(k => dimByKey[k]), d => d.key).join(enter => {
    const a = enter.append("g").attr("class", "dim");
    a.append("g").attr("class", "axis");
    a.append("text").attr("class", "axis-title").attr("text-anchor", "middle").attr("y", -50);
    a.append("text").attr("class", "axis-sub").attr("text-anchor", "middle").attr("y", -36)
      .attr("font-size", 10).attr("fill", "#5b6470");
    a.append("g").attr("class", "brush");
    return a;
  });
  g.attr("transform", d => `translate(${px(d.key)},0)`);
  g.select(".axis").each(function (d) {
    const ax = d3.axisLeft(y[d.key]);
    if (d.type === "log") ax.ticks(6, "~s");
    else if (d.type === "symlog") {
      const cand = d.key === "num_comments" ? [0, 10, 100, 1000, 3000, 10000, 30000] : [0, 1, 3, 10, 30, 100, 300];
      ax.tickValues(cand.filter(v => v <= y[d.key].domain()[1])).tickFormat(d3.format("~s"));
    }
    else if (d.fmt) ax.ticks(8).tickFormat(d.fmt);
    d3.select(this).call(ax);
  });
  g.select(".axis-title").text(d => d.label)
    .call(d3.drag()
      .on("start", (e, d) => { dragging[d.key] = x(d.key); })
      .on("drag", (e, d) => {
        dragging[d.key] = Math.max(-30, Math.min(innerW + 30, e.x));
        state.order.sort((a, b) => px(a) - px(b));
        x.domain(state.order);
        axesG.selectAll("g.dim").attr("transform", dd => `translate(${px(dd.key)},0)`);
        lines.selectAll("path").attr("d", r => lineGen(pathPoints(r)));
        drawSpines();
      })
      .on("end", (e, d) => {
        delete dragging[d.key];
        x.domain(state.order);
        axesG.selectAll("g.dim").transition().duration(300).attr("transform", dd => `translate(${x(dd.key)},0)`);
        lines.selectAll("path").transition().duration(300).attr("d", r => lineGen(pathPoints(r)));
        drawSpines();
      }));
  g.select(".axis-sub").text(d => ({ linear: "linear", log: "log scale", symlog: "symlog scale", ordinal: "ordinal" })[d.type]);
  g.select(".brush").each(function (d) {
    const b = d3.brushY().extent([[-11, 0], [11, innerH]])
      .on("brush end", (e) => {
        if (e.selection) state.brushes.set(d.key, e.selection);
        else state.brushes.delete(d.key);
        applyBrushStyle();
      });
    d.__brush = b;
    d3.select(this).call(b);
  });
}

// ---------------------------------------------------------------- legend
function drawLegend(keys) {
  const L = root.select("g.legend").attr("transform", `translate(${innerW + 40},0)`);
  L.selectAll("*").remove();
  L.append("text").attr("font-weight", 600).attr("font-size", 12).text(GROUP_LABEL[state.group]);
  const it = L.selectAll("g.item").data(keys).join("g").attr("class", "item")
    .attr("transform", (d, i) => `translate(0,${18 + i * 19})`);
  it.append("rect").attr("width", 14).attr("height", 14).attr("y", -1).attr("fill", d => color(d));
  it.append("text").attr("class", "lab").attr("x", 20).attr("y", 11).attr("font-size", 11.5);
  if (state.group === "cluster") {
    L.append("text").attr("y", 18 + keys.length * 19 + 14).attr("font-size", 10.5).attr("fill", "#5b6470")
      .text("k-means on min–max normalised axes");
  }
  updateLegendCounts();
}

function updateLegendCounts() {
  const cnt = d3.rollup(data.filter(d => d.__sel !== false), v => v.length, d => d[state.group]);
  const tot = d3.rollup(data, v => v.length, d => d[state.group]);
  root.select("g.legend").selectAll("g.item text.lab").text(d => `${d} (${cnt.get(d) || 0}/${tot.get(d)})`);
}

// ---------------------------------------------------------------- tooltip
const tip = d3.select("#tip");
function showTip(e, d) {
  d3.select(e.currentTarget).raise().attr("stroke-width", 2.6).attr("stroke-opacity", 1).attr("stroke", color(d[state.group]));
  tip.style("opacity", 1).html(
    `<b>${d.title}</b><br>r/${d.subreddit} · ${d.category} · ${d.post_type} · ${d.domain_class}<br>` +
    `score ${d3.format(",")(d.score)} · comments ${d3.format(",")(d.num_comments)} · ratio ${d.upvote_ratio}<br>` +
    `crossposts ${d.num_crossposts} · title ${d.title_len} chars · ${d.dec_year.toFixed(2)} · ${d.hour_utc}:00 UTC<br>` +
    `k-means cluster ${d.cluster}`);
  moveTip(e);
}
function moveTip(e) { tip.style("left", (e.clientX + 14) + "px").style("top", (e.clientY + 12) + "px"); }
function hideTip(e) { tip.style("opacity", 0); applyBrushStyle(); }

// ---------------------------------------------------------------- controls / API
function setBeta(b) {
  state.beta = b;
  d3.select("#beta").property("value", b);
  d3.select("#betaVal").text(b.toFixed(2));
  lines.selectAll("path").attr("d", r => lineGen(pathPoints(r)));
  drawSpines();
}

function reset() {
  state.order = DIMS.map(d => d.key);
  x.domain(state.order);
  axesG.selectAll("g.dim").each(function (d) { d3.select(this).select(".brush").call(d.__brush.move, null); });
  state.brushes.clear();
  setBeta(0);
  state.spine = false; d3.select("#showSpine").property("checked", false);
  setGroup("cluster");
  axesG.selectAll("g.dim").attr("transform", d => `translate(${x(d.key)},0)`);
  drawLines();
}

const api = {
  setBeta, setGroup, reset,
  spine(on) { state.spine = on; d3.select("#showSpine").property("checked", on); drawSpines(); },
  brush(key, lo, hi) {           // brush in data units
    const s = y[key];
    const clamp = v => Math.max(0, Math.min(innerH, v));
    const a = dimByKey[key].type === "ordinal" ? [s(hi) - 8, s(lo) + 8] : [clamp(s(hi)), clamp(s(lo))];
    axesG.selectAll("g.dim").filter(d => d.key === key).each(function (d) { d3.select(this).select(".brush").call(d.__brush.move, a); });
  },
  reorder(order) {
    state.order = order.slice();
    x.domain(state.order);
    axesG.selectAll("g.dim").attr("transform", d => `translate(${x(d.key)},0)`);
    drawLines();
  },
  stats() {
    const sel = data.filter(d => d.__sel !== false);
    return { n: sel.length, by: Object.fromEntries(d3.rollup(sel, v => v.length, d => d[state.group])) };
  },
};
