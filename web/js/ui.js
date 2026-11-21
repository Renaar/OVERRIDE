// Small DOM helpers shared by every screen.
export const $ = (sel, root = document) => root.querySelector(sel);

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const win = (title, ...children) =>
  h("section", { class: "win" }, title ? h("h2", { class: "win-h" }, `[ ${title} ]`) : null, ...children);

export const prefs = {
  reducedMotion: () => matchMedia("(prefers-reduced-motion: reduce)").matches || document.body.classList.contains("reduced"),
};

// System message written character by character; a tap shows everything.
export function sysText(text) {
  const el = h("div", { class: "sys", role: "status" });
  if (!text) return el;
  if (prefs.reducedMotion()) { el.textContent = text; return el; }
  let i = 0, timer;
  const caret = h("span", { class: "caret" }, " ");
  const span = h("span");
  el.append(span, caret);
  const done = () => { clearInterval(timer); span.textContent = text; caret.remove(); };
  timer = setInterval(() => { i += 1; span.textContent = text.slice(0, i); if (i >= text.length) done(); }, 22);
  el.addEventListener("click", done);
  return el;
}

export function vibrate(pattern = 60) { try { navigator.vibrate && navigator.vibrate(pattern); } catch (_) {} }

export function toast(msg, ms = 2600) {
  const t = h("div", { class: "toast" }, msg);
  document.body.append(t);
  setTimeout(() => t.remove(), ms);
}

export function mmss(s) {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const kg = (v) => (v == null ? "" : `${Number(v).toLocaleString("fr-CH", { maximumFractionDigits: 2 })} kg`);

export function overlay(content, { onClose } = {}) {
  const o = h("div", { class: "overlay", onclick: (e) => { if (e.target === o && onClose) { o.remove(); onClose(); } } }, content);
  document.body.append(o);
  return o;
}

export function cinematic(big, small, hold = 1600) {
  const c = h("div", { class: "cine", style: `--hold:${hold}ms` }, h("div", { class: "t" }, h("b", {}, big), h("span", {}, small)));
  c.addEventListener("click", () => c.remove());
  document.body.append(c);
  setTimeout(() => c.remove(), hold + 500);
  return new Promise((r) => setTimeout(r, hold + 400));
}

export const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
