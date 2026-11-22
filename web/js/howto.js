// "Comment faire ?" sheet: large animated figure, detailed steps, common mistakes, video search.
import { figure } from "./figure.js";
import { h, overlay, prefs, win } from "./ui.js";

export function videoUrl(info) {
  if (info.video_url) return info.video_url;
  const q = info.video_query || info.name;
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`;
}

/** Small looping figure for an exercise card, or null when the movement has no drawing. */
export function figureBox(info, { size = "small" } = {}) {
  if (!info || !info.figure) return null;
  const svg = figure(info.figure, { tempo: info.figure_tempo, still: prefs.reducedMotion() });
  if (!svg) return null;
  return h("div", { class: `fig-box ${size}` }, svg);
}

export function howToButton(info, label = "Comment faire ?") {
  if (!info || !(info.steps || info.figure)) return null;
  return h("button", { class: "btn ghost howto-btn", onclick: (e) => { e.stopPropagation(); openHowTo(info); } }, label);
}

export function openHowTo(info) {
  const close = () => o.remove();
  const body = win(info.name,
    figureBox(info, { size: "large" }),
    info.steps && info.steps.length ? h("div", {},
      h("div", { class: "howto-h" }, "EXÉCUTION"),
      h("ol", { class: "howto-steps" }, info.steps.map((s) => h("li", {}, s)))) : null,
    info.mistakes && info.mistakes.length ? h("div", {},
      h("div", { class: "howto-h warn" }, "ERREURS FRÉQUENTES"),
      h("ul", { class: "howto-mistakes" }, info.mistakes.map((s) => h("li", {}, s)))) : null,
    info.back_note ? h("div", { class: "backnote" }, `⚠ ${info.back_note}`) : null,
    h("div", { class: "row", style: "margin-top:14px" },
      h("a", { class: "btn grow", href: videoUrl(info), target: "_blank", rel: "noopener noreferrer" }, "Vidéos ↗"),
      h("button", { class: "btn primary grow", onclick: close }, "Compris")));
  const o = overlay(body, { onClose: () => {} });
  return o;
}
