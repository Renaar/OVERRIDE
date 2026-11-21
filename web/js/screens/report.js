// Quest report: rolling XP, multiplier, level, System messages, level-up cinematic.
import { go } from "../app.js";
import { cinematic, h, prefs, sysText, vibrate, win } from "../ui.js";

export async function render(app, [id]) {
  let r;
  try { r = JSON.parse(sessionStorage.getItem(`override:report:${id}`)); } catch (_) { r = null; }
  if (!r) return go("status");

  const roll = h("div", { class: "xp-roll" }, "+0");
  const pct = Math.min(100, (100 * r.xp_in_level) / r.xp_next);
  const levelUp = r.xp.levels_gained > 0;

  app.replaceChildren(
    win("RAPPORT DE QUÊTE",
      h("div", { class: "num muted", style: "text-align:center;letter-spacing:.14em" }, r.label || "QUÊTE"),
      roll,
      h("div", { class: "spread" }, h("span", { class: "muted" }, "XP de base"), h("b", { class: "num" }, r.xp.base)),
      h("div", { class: "spread" }, h("span", { class: "muted" }, "Multiplicateur"), h("b", { class: "num gold" }, `×${r.xp.multiplier.toFixed(1)}`)),
      r.sets ? h("div", { class: "spread" }, h("span", { class: "muted" }, "Séries validées"), h("b", { class: "num" }, r.sets)) : null,
      r.minutes ? h("div", { class: "spread" }, h("span", { class: "muted" }, "Durée"), h("b", { class: "num" }, `${r.minutes} min`)) : null,
      h("div", { class: "spread" }, h("span", { class: "muted" }, "Série"), h("b", { class: "num" }, `${r.streak} j · prochain ×${r.multiplier_next.toFixed(1)}`)),
      ...(r.extra || []).map((e) => h("div", { class: "spread ok" }, h("span", {}, e.label), h("b", { class: "num" }, `+${e.xp}`))),
      h("div", { class: "spread", style: "margin-top:12px" }, h("span", { class: "num" }, `NIV. ${r.level}`), h("span", { class: "num muted", style: "font-size:13px" }, `${r.xp_in_level} / ${r.xp_next} XP`)),
      h("div", { class: "bar xp" }, h("i", { style: `width:${pct}%` }))),
    win("SYSTÈME", sysText(r.message || ""), ...(r.level_messages || []).map((m) => h("div", { style: "margin-top:8px" }, sysText(m)))),
    h("button", { class: "btn primary block", onclick: () => { sessionStorage.removeItem(`override:report:${id}`); go("status"); } }, "Retour au Statut"));

  // XP roll
  const target = r.xp.gain;
  if (prefs.reducedMotion()) roll.textContent = `+${target}`;
  else {
    const t0 = performance.now(), dur = 1200;
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      roll.textContent = `+${Math.round(target * (1 - (1 - k) ** 3))}`;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  vibrate(80);
  if (levelUp) {
    setTimeout(() => { vibrate([150, 80, 150, 80, 300]); cinematic(`NIVEAU ${r.level}`, "MONTÉE DE NIVEAU · +1 POINT DE FOCUS", 1600); }, 1300);
  }
}
