// Animated holographic stick figure. Poses give hip position, torso angle and hand/foot targets;
// knees and elbows are solved with two-bone inverse kinematics so limbs keep their length.
import { FIGURES } from "./figures.js";

const NS = "http://www.w3.org/2000/svg";
const L = { shin: 25, thigh: 25, torso: 32, neck: 5, head: 6, upper: 18, fore: 17 };
const rad = (d) => (d * Math.PI) / 180;

function ik(a, t, l1, l2, bend) {
  let dx = t[0] - a[0], dy = t[1] - a[1];
  let d = Math.hypot(dx, dy) || 0.001;
  const dmax = l1 + l2 - 0.01, dmin = Math.abs(l1 - l2) + 0.01;
  if (d > dmax) { dx *= dmax / d; dy *= dmax / d; d = dmax; }
  if (d < dmin) { dx *= dmin / d; dy *= dmin / d; d = dmin; }
  const base = Math.atan2(dy, dx);
  const cosA = Math.min(1, Math.max(-1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)));
  const al = Math.acos(cosA);
  const cands = [base + al, base - al].map((g) => [a[0] + l1 * Math.cos(g), a[1] + l1 * Math.sin(g)]);
  const cross = (j) => dx * (j[1] - a[1]) - dy * (j[0] - a[0]);
  const j = cands.find((c) => (bend > 0 ? cross(c) < 0 : cross(c) > 0)) || cands[0];
  const end = [a[0] + dx, a[1] + dy];
  return [a, j, end];
}

// Pose -> joint coordinates.
export function solve(p, view = "side") {
  const tr = rad(p.t || 0);
  const dir = [Math.sin(tr), -Math.cos(tr)];               // hip -> shoulder
  const perp = [-dir[1], dir[0]];                           // screen-right when upright
  const neck = [p.hip[0] + L.torso * dir[0], p.hip[1] + L.torso * dir[1]];
  const up = L.torso + (p.shrug || 0);                     // shrug: shoulders raised toward the ears
  const sh = [p.hip[0] + up * dir[0], p.hip[1] + up * dir[1]];
  const hr = rad((p.t || 0) + (p.hd || 0));
  const hdir = [Math.sin(hr), -Math.cos(hr)];
  const head = [neck[0] + (L.neck + L.head) * hdir[0], neck[1] + (L.neck + L.head) * hdir[1]];
  const hw = view === "front" ? (p.hw ?? 6) : 0, sw = view === "front" ? (p.sw ?? 10) : 0;
  const hips = [[p.hip[0] - perp[0] * hw, p.hip[1] - perp[1] * hw], [p.hip[0] + perp[0] * hw, p.hip[1] + perp[1] * hw]];
  const shs = [[sh[0] - perp[0] * sw, sh[1] - perp[1] * sw], [sh[0] + perp[0] * sw, sh[1] + perp[1] * sw]];
  // shin1/2, fore1/2 shorten a segment that points toward the viewer (foreshortening)
  const legs = [p.f1, p.f2 || p.f1].map((f, i) => ik(hips[i], f, L.thigh, L.shin * (p[`shin${i + 1}`] ?? 1),
    (i ? p.kb2 : p.kb1) ?? p.kb ?? 1));
  const arms = [p.h1, p.h2 || p.h1].map((h, i) => ik(shs[i], h, L.upper, L.fore * (p[`fore${i + 1}`] ?? 1),
    (i ? p.eb2 : p.eb1) ?? p.eb ?? -1));
  return { hip: p.hip, hips, sh, shs, head, legs, arms };
}

function lerp(a, b, k) {
  if (Array.isArray(a)) return a.map((v, i) => lerp(v, b[i], k));
  if (typeof a === "number" && typeof b === "number") return a + (b - a) * k;
  return k < 0.5 ? a : b;
}
function mix(p, q, k) {
  const out = {};
  for (const key of new Set([...Object.keys(p), ...Object.keys(q)])) {
    out[key] = p[key] === undefined ? q[key] : q[key] === undefined ? p[key] : lerp(p[key], q[key], k);
  }
  return out;
}
const ease = (k) => k * k * (3 - 2 * k);

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.append(e);
  return e;
}
const pts = (arr) => arr.map((q) => `${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(" ");

function drawProps(g, props = []) {
  for (const pr of props) {
    if (pr.r) el("rect", { x: pr.r[0], y: pr.r[1], width: pr.r[2], height: pr.r[3], class: "fp" }, g);
    if (pr.l) el("line", { x1: pr.l[0], y1: pr.l[1], x2: pr.l[2], y2: pr.l[3], class: "fp" }, g);
    if (pr.c) el("circle", { cx: pr.c[0], cy: pr.c[1], r: pr.c[2], class: "fp" }, g);
    if (pr.p) el("polyline", { points: pts(pr.p), class: "fp" }, g);
  }
}

// Tight viewBox around every key pose and prop, so the movement fills its frame.
function fit(def, view) {
  const xs = [], ys = [];
  const add = (q, r = 0) => { xs.push(q[0] - r, q[0] + r); ys.push(q[1] - r, q[1] + r); };
  for (const k of def.k) {
    const j = solve(k, view);
    [j.hip, j.sh, ...j.hips, ...j.shs, ...j.legs.flat(), ...j.arms.flat()].forEach((q) => add(q, 2));
    add(j.head, L.head + 1);
    (def.db || []).forEach((w) => { const q = { h1: j.arms[0][2], h2: j.arms[1][2] }[w]; if (q) add(q, 7); });
  }
  for (const pr of def.props || []) {
    if (pr.r) { add([pr.r[0], pr.r[1]]); add([pr.r[0] + pr.r[2], pr.r[1] + pr.r[3]]); }
    if (pr.l) { add([pr.l[0], pr.l[1]]); add([pr.l[2], pr.l[3]]); }
    if (pr.c) add([pr.c[0], pr.c[1]], pr.c[2]);
  }
  if (def.band) add(def.band[0]);
  if (def.ground !== false) ys.push(def.gy ?? 110);
  const pad = 6;
  let x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  const minW = 70, minH = 44;                       // keep small movements from looking oversized
  if (x1 - x0 < minW) { const c = (x0 + x1) / 2; x0 = c - minW / 2; x1 = c + minW / 2; }
  if (y1 - y0 < minH) { y0 = y1 - minH; }
  return [x0, y0, x1 - x0, y1 - y0].map((v) => Math.round(v * 10) / 10);
}

/** Build an animated SVG for figure `id`. Returns null when the figure is unknown. */
export function figure(id, { tempo, still = false, className = "fig" } = {}) {
  const def = FIGURES[id];
  if (!def) return null;
  const view = def.view || "side";
  const box = fit(def, view);
  const svg = el("svg", { viewBox: box.join(" "), class: className, role: "img", "aria-label": def.label || "" });
  const gy = def.gy ?? 110;
  if (def.ground !== false) el("line", { x1: box[0] + 2, y1: gy, x2: box[0] + box[2] - 2, y2: gy, class: "fg" }, svg);
  drawProps(el("g", {}, svg), def.props);
  const far = el("g", { class: view === "side" ? "ff" : "fn" }, svg);
  const near = el("g", { class: "fn" }, svg);
  const mk = (g) => el("polyline", { points: "" }, g);
  const parts = {
    leg2: mk(far), arm2: mk(far), leg1: mk(near), torso: el("path", { d: "" }, near), arm1: mk(near),
    head: el("circle", { r: L.head, class: "fh" }, near),
  };
  const dbs = (def.db || []).map(() => el("g", { class: "fd" }, svg));
  dbs.forEach((g) => { el("rect", { x: -5, y: -1.2, width: 10, height: 2.4 }, g); el("rect", { x: -6.5, y: -3.2, width: 3, height: 6.4 }, g); el("rect", { x: 3.5, y: -3.2, width: 3, height: 6.4 }, g); });
  const band = def.band ? el("polyline", { class: "fb" }, svg) : null;
  const toes = def.toes ? [mk(near), mk(far)] : null;

  const render = (p) => {
    const j = solve(p, view);
    parts.leg1.setAttribute("points", pts(j.legs[0]));
    parts.leg2.setAttribute("points", pts(j.legs[1]));
    parts.arm1.setAttribute("points", pts(j.arms[0]));
    parts.arm2.setAttribute("points", pts(j.arms[1]));
    if (view === "front") {
      const seg = (a, b) => `M${pts([a])} L${pts([b])}`;
      parts.torso.setAttribute("d", `${seg(j.hips[0], j.hips[1])} ${seg(j.hip, j.sh)} ${seg(j.shs[0], j.shs[1])}`);
    } else {
      const a = p.arch || 0, tr = rad(p.t || 0);
      const c = [(j.hip[0] + j.sh[0]) / 2 + Math.cos(tr) * a, (j.hip[1] + j.sh[1]) / 2 + Math.sin(tr) * a];
      parts.torso.setAttribute("d", `M${pts([j.hip])} Q${pts([c])} ${pts([j.sh])}`);
    }
    if (toes) toes.forEach((tl, i) => {
      const an = j.legs[i][2];
      tl.setAttribute("points", pts([an, [an[0] + 6 * (p.toeDir ?? 1), Math.max(an[1], def.toes === true ? gy : def.toes)]]));
    });
    parts.head.setAttribute("cx", j.head[0].toFixed(1));
    parts.head.setAttribute("cy", j.head[1].toFixed(1));
    const at = { h1: j.arms[0][2], h2: j.arms[1][2], f1: j.legs[0][2], f2: j.legs[1][2],
      hip: j.hip, chest: [(j.hip[0] + 2 * j.sh[0]) / 3, (j.hip[1] + 2 * j.sh[1]) / 3] };
    (def.db || []).forEach((where, i) => {
      const q = at[where];
      const ang = def.dbAngle ?? 0;
      dbs[i].setAttribute("transform", `translate(${q[0].toFixed(1)},${q[1].toFixed(1)}) rotate(${ang})`);
    });
    if (band) band.setAttribute("points", pts([def.band[0], at[def.band[1]]]));
  };

  const keys = def.k;
  if (keys.length === 1 || still) { render(keys[def.still ?? keys.length - 1] || keys[0]); return svg; }

  // timeline: move to each key then hold. Two keys play A -> B -> A.
  const seq = keys.length === 2 ? [0, 1] : keys.map((_, i) => i);
  const [down, holdB, up, holdA] = tempo || def.tempo || [1.1, 0.35, 1.1, 0.45];
  const moves = keys.length === 2 ? [down, up] : seq.map(() => def.step || 0.8);
  const holds = keys.length === 2 ? [holdB, holdA] : seq.map(() => def.hold || 0.15);
  const total = moves.reduce((a, b) => a + b, 0) + holds.reduce((a, b) => a + b, 0);
  const t0 = performance.now();
  const frame = (now) => {
    if (!svg.isConnected && now - t0 > 1000) return;     // stop once removed from the page
    let t = ((now - t0) / 1000) % total;
    for (let i = 0; i < seq.length; i++) {
      const from = keys[seq[i]], to = keys[seq[(i + 1) % seq.length]];
      if (t < moves[i]) { render(mix(from, to, ease(t / moves[i]))); break; }
      t -= moves[i];
      if (t < holds[i]) { render(to); break; }
      t -= holds[i];
    }
    requestAnimationFrame(frame);
  };
  render(keys[0]);
  requestAnimationFrame(frame);
  return svg;
}

export const hasFigure = (id) => !!FIGURES[id];
