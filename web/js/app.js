// Hash router. Each screen module exports render(app, params) and may return a cleanup function.
import { api, flushQueue } from "./api.js";
import { $, h, win } from "./ui.js";

const routes = {
  awakening: () => import("./screens/awakening.js"),
  status: () => import("./screens/status.js"),
  quest: () => import("./screens/quest.js"),
  report: () => import("./screens/report.js"),
  skills: () => import("./screens/lists.js").then((m) => ({ render: m.skills })),
  inventory: () => import("./screens/lists.js").then((m) => ({ render: m.inventory })),
  journal: () => import("./screens/lists.js").then((m) => ({ render: m.journal })),
  settings: () => import("./screens/settings.js"),
};
const FULL = new Set(["awakening", "quest", "report"]);
let cleanup = null;

export function go(path) { location.hash = `#/${path}`; }

async function route() {
  const [name = "status", ...params] = location.hash.replace(/^#\/?/, "").split("/");
  const app = $("#app");
  if (cleanup) { try { cleanup(); } catch (_) {} cleanup = null; }
  const key = routes[name] ? name : "status";
  const st = await api.get("/api/state").catch(() => null);
  if (st && !st.awakened && key !== "awakening") return go("awakening");
  if (st && st.awakened && key === "awakening") return go("status");
  applyPrefs(st);
  document.body.classList.toggle("full", FULL.has(key));
  app.classList.toggle("full", FULL.has(key));
  $("#nav").classList.toggle("hidden", FULL.has(key));
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("on", a.dataset.r === key));
  app.replaceChildren();
  window.scrollTo(0, 0);
  try {
    const mod = await routes[key]();
    cleanup = (await mod.render(app, params)) || null;
  } catch (e) {
    console.error(e);
    app.replaceChildren(win("ERREUR", h("p", {}, e.message || String(e)),
      h("button", { class: "btn", onclick: () => route() }, "Réessayer")));
  }
}

function applyPrefs(st) {
  const s = st && st.settings;
  if (!s) return;
  document.body.classList.toggle("reduced", !!s.reduced_motion);
  document.body.classList.toggle("lite", !!s.reduced_motion);
}
export { applyPrefs };

addEventListener("hashchange", route);
addEventListener("online", flushQueue);
flushQueue();
route();
