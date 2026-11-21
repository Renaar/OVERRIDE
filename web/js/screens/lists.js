// Skills tree, inventory and System journal.
import { api } from "../api.js";
import { h, win } from "../ui.js";

const CATS = [["main", "MOUVEMENTS PRINCIPAUX"], ["core", "GAINAGE · SUSPENSION · PORTER"], ["accessory", "ACCESSOIRES"],
  ["mobility", "MOBILITÉ"], ["iso", "ISOMÉTRIES"]];
const LOCKS = { materiel: "matériel", dos: "verrou dos", niveau: "niveau précédent" };

export async function skills(app) {
  const list = await api.get("/api/skills");
  app.replaceChildren(...CATS.map(([cat, title]) => {
    const fams = list.filter((f) => f.category === cat);
    if (!fams.length) return "";
    return win(title, ...fams.map((f) => {
      const cur = f.variants.find((v) => v.current) || f.variants[0];
      const details = h("div", { class: "hidden", style: "margin-top:6px" }, f.variants.map((v) =>
        h("div", { class: `variant ${v.current ? "cur" : ""} ${v.lock ? "locked" : ""}` },
          h("span", { class: "lv" }, `N${v.level}`),
          h("span", { class: "grow" }, v.name, v.lock ? h("span", { class: "muted" }, ` · 🔒 ${LOCKS[v.lock] || v.lock}`) : null))));
      const extra = [f.load != null ? `${f.load} kg` : null, f.target != null && !f.zone ? `cible ${f.target}${cur.type === "time" ? " s" : " rép."}` : null].filter(Boolean).join(" · ");
      return h("div", { class: "list-item", onclick: () => details.classList.toggle("hidden"), style: "cursor:pointer" },
        h("div", { class: "spread" }, h("b", {}, f.name), h("span", { class: "num muted" }, f.zone ? `${f.level}/${f.max_level} ouverts` : `NIV. ${f.level}/${f.max_level}`)),
        h("div", { style: "font-size:14px" }, cur.name, extra ? h("span", { class: "muted" }, ` · ${extra}`) : null),
        h("div", { class: "bar", style: "margin-top:6px;height:4px" }, h("i", { style: `width:${(100 * f.level) / f.max_level}%` })),
        details);
    }));
  }));
}

export async function inventory(app) {
  const items = await api.get("/api/inventory");
  const owned = items.filter((i) => i.owned), missing = items.filter((i) => !i.owned);
  app.replaceChildren(
    win("INVENTAIRE", ...owned.map((i) => h("div", { class: "list-item spread" }, h("b", {}, i.name),
      h("span", { class: "muted num" }, i.max_load ? `max ${i.max_load} kg · pas ${i.step} kg` : "")))),
    win("NON POSSÉDÉ", ...missing.map((i) => h("div", { class: "list-item muted" }, i.name)),
      h("p", { class: "muted", style: "font-size:13px" }, "Les mises à niveau matérielles arriveront avec la phase 2.")));
}

export async function journal(app) {
  const events = await api.get("/api/journal");
  const fmt = (ts) => ts.replace("T", " ").slice(5, 16);
  app.replaceChildren(win("JOURNAL DU SYSTÈME", h("div", { class: "log" },
    events.length ? events.map((e) => h("div", { class: "ln" },
      h("span", { class: "ts" }, `${fmt(e.ts)} `), h("span", { class: "ty" }, `${e.type.toUpperCase()} `),
      e.message ? h("div", {}, e.message) : null)) : h("div", { class: "muted" }, "Aucun événement."))));
}
