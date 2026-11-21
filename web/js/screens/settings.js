// Settings (phase 1 subset: schedule, rest timers, animations).
import { api } from "../api.js";
import { applyPrefs, go } from "../app.js";
import { DAYS, h, toast, win } from "../ui.js";

export async function render(app) {
  const s = await api.get("/api/settings");
  const num = (key, label) => h("label", { class: "f" }, h("span", {}, label),
    h("input", { class: "in", inputmode: "numeric", value: s[key], oninput: (e) => (s[key] = Number(e.target.value) || 0) }));
  const day = (key, label) => h("label", { class: "f" }, h("span", {}, label),
    h("select", { class: "in", onchange: (e) => (s[key] = Number(e.target.value)) },
      DAYS.map((d, i) => h("option", { value: i, selected: i === Number(s[key]) }, d))));
  const tog = (key, label) => h("label", { class: "toggle" },
    h("input", { type: "checkbox", checked: !!s[key], onchange: (e) => (s[key] = e.target.checked) }), label);
  app.replaceChildren(
    win("RÉGLAGES",
      day("rest_day", "Jour de repos"), day("dungeon_day", "Jour du Donjon"),
      h("label", { class: "f" }, h("span", {}, "Heure de la quête"),
        h("input", { class: "in", type: "time", value: s.quest_hour, onchange: (e) => (s.quest_hour = e.target.value) })),
      num("rest_seconds", "Repos entre les séries (s)"), num("superset_rest_seconds", "Repos dans un superset (s)"),
      tog("reduced_motion", "Animations réduites (et sans flou)"),
      h("p", { class: "muted", style: "font-size:13px" }, "Les nouveaux réglages s'appliquent à la prochaine quête générée.")),
    h("div", { class: "row" },
      h("button", { class: "btn ghost grow", onclick: () => go("status") }, "Retour"),
      h("button", { class: "btn primary grow", onclick: async () => {
        const saved = await api.put("/api/settings", s);
        applyPrefs({ settings: saved });
        toast("Réglages enregistrés.");
      } }, "Enregistrer")));
}
