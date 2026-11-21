// Awakening: first launch, staged as a system initialisation. Body data, inventory, schedule, guided tests.
import { api } from "../api.js";
import { go } from "../app.js";
import { DAYS, h, mmss, sysText, vibrate, win } from "../ui.js";

const KEY = "override:awakening";
const EXTRA = [["BT", "Barre de traction"], ["EL", "Élastiques"], ["BC", "Banc réglable"], ["HL", "Haltères lourds"], ["GL", "Gilet lesté"]];

const TESTS = [
  { id: "pushups", kind: "count", title: "Pompes strictes max",
    how: ["Pompes au sol, corps gainé", "Poitrine à un poing du sol, bras tendus en haut", "Arrête dès que la forme se dégrade"] },
  { id: "plank", kind: "chrono", title: "Planche max",
    how: ["Avant-bras au sol, fesses serrées", "Arrête dès que le bas du dos creuse"] },
  { id: "hang", kind: "chrono", title: "Suspension max (grandes prises)",
    how: ["Grandes prises de la planche uniquement", "Bras tendus, épaules loin des oreilles", "Descends en douceur"] },
  { id: "goblet", kind: "count", max: 30, title: "Squat gobelet max à charge max",
    how: ["Un haltère à charge max contre la poitrine", "Descends entre les talons, dos neutre", "Arrêt à 30 répétitions"] },
  { id: "deep_squat", kind: "chrono", max: 120, title: "Accroupi profond, talons au sol",
    how: ["Talons au sol, pieds largeur d'épaules", "Tiens le plus longtemps possible", "Arrêt automatique à 2 min"] },
  { id: "toe_touch", kind: "cm", title: "Distance doigts-sol",
    how: ["Debout, jambes tendues, penche-toi depuis les hanches", "Mesure entre le bout des doigts et le sol", "Doigts au-dessus du sol : positif. Plus bas que le sol (sur une marche) : négatif"] },
  { id: "knee_wall", kind: "cm", title: "Genou au mur",
    how: ["Face au mur, talon au sol", "Recule le pied tant que le genou touche le mur", "Mesure orteil-mur, côté le plus raide"] },
  { id: "hands_back", kind: "cm", title: "Mains dans le dos",
    how: ["Une main par-dessus l'épaule, l'autre par le bas", "Rapproche les poings dans le dos", "Mesure l'écart entre les poings (0 s'ils se touchent, négatif s'ils se chevauchent)"] },
];

function load() { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (_) { return null; } }

export function render(app) {
  const s = load() || {
    step: 0, name: "", weight: "", arm: "", chest: "", waist: "", thigh: "",
    dumbbell_max: 10, dumbbell_step: 1, owned: ["H", "P"], rest_day: 6, quest_hour: "19:00", tests: {},
  };
  const save = () => localStorage.setItem(KEY, JSON.stringify(s));
  let timer = null;
  const stop = () => { if (timer) clearInterval(timer); timer = null; };

  const steps = [intro, identity, body, inventory, schedule, ...TESTS.map((t) => () => test(t)), confirm];
  const next = () => { stop(); s.step = Math.min(steps.length - 1, s.step + 1); save(); draw(); };
  const prev = () => { stop(); s.step = Math.max(0, s.step - 1); save(); draw(); };

  function draw() {
    app.replaceChildren(
      h("div", { class: "muted num", style: "font-size:12px;letter-spacing:.2em;margin-bottom:8px" },
        `ÉVEIL · ${String(s.step + 1).padStart(2, "0")}/${steps.length}`),
      steps[s.step](),
    );
  }

  const nav = (canNext = () => true, label = "Suivant") => {
    const b = h("button", { class: "btn primary grow", onclick: () => canNext() && next() }, label);
    return h("div", { class: "row actions", style: "margin-top:16px" },
      s.step > 0 ? h("button", { class: "btn ghost", onclick: prev }, "Retour") : null, b);
  };

  const field = (key, label, attrs = {}) => h("label", { class: "f" }, h("span", {}, label),
    h("input", { class: "in", value: s[key], inputmode: "decimal", ...attrs,
      oninput: (e) => { s[key] = e.target.value; save(); } }));

  function intro() {
    return h("div", {},
      win("INITIALISATION", sysText("[SYSTÈME] Nouveau joueur détecté.\nAnalyse de l'hôte en cours…\nProtocole d'Éveil prêt. Durée : 15 à 20 min. Prévois tes haltères, ta planche de suspension, un mètre ruban et un chrono."),
        nav(() => true, "Lancer l'Éveil")));
  }

  function identity() {
    return win("IDENTIFICATION", sysText("[SYSTÈME] Identifie-toi."),
      h("div", { style: "margin-top:12px" }, field("name", "Nom du joueur", { inputmode: "text", maxlength: 40, autocomplete: "given-name" })),
      nav(() => s.name.trim().length > 0));
  }

  function body() {
    return win("SCAN CORPOREL", sysText("[SYSTÈME] Mesures de référence. Ruban à plat, sans serrer, toujours au même endroit."),
      h("div", { class: "grid2", style: "margin-top:12px" },
        field("weight", "Poids (kg)"), field("arm", "Bras contracté (cm)"),
        field("chest", "Poitrine (cm)"), field("waist", "Taille, au nombril (cm)"),
        field("thigh", "Cuisse (cm)")),
      nav(() => s.weight !== "" && s.waist !== ""));
  }

  function inventory() {
    const box = (code, label) => h("label", { class: "toggle" },
      h("input", { type: "checkbox", checked: s.owned.includes(code),
        onchange: (e) => { s.owned = e.target.checked ? [...new Set([...s.owned, code])] : s.owned.filter((c) => c !== code); save(); } }),
      label);
    return win("INVENTAIRE", sysText("[SYSTÈME] Recensement du matériel."),
      h("div", { class: "grid2", style: "margin-top:12px" },
        field("dumbbell_max", "Haltères : charge max (kg)"), field("dumbbell_step", "Pas de réglage (kg)")),
      box("P", "Planche de suspension"),
      h("p", { class: "muted", style: "font-size:13px;margin:8px 0 0" }, "Autre matériel déjà possédé :"),
      ...EXTRA.map(([c, l]) => box(c, l)),
      nav(() => Number(s.dumbbell_max) > 0 && Number(s.dumbbell_step) > 0));
  }

  function schedule() {
    return win("PLANIFICATION", sysText("[SYSTÈME] Fenêtre d'exécution. Six jours de quête, un jour de repos."),
      h("label", { class: "f", style: "margin-top:12px" }, h("span", {}, "Jour de repos"),
        h("select", { class: "in", onchange: (e) => { s.rest_day = Number(e.target.value); save(); } },
          DAYS.map((d, i) => h("option", { value: i, selected: i === Number(s.rest_day) }, d)))),
      h("label", { class: "f" }, h("span", {}, "Heure de la quête"),
        h("input", { class: "in", type: "time", value: s.quest_hour, onchange: (e) => { s.quest_hour = e.target.value; save(); } })),
      nav());
  }

  function test(t) {
    const val = () => s.tests[t.id];
    const set = (v) => { s.tests[t.id] = v; save(); out.textContent = display(); };
    const display = () => val() == null ? "—" : t.kind === "chrono" ? mmss(val()) : t.kind === "cm" ? `${val()} cm` : String(val());
    const out = h("div", { class: "bignum", style: "margin:12px 0" }, display());
    let tool;
    if (t.kind === "count") {
      tool = h("div", {},
        h("button", { class: "btn primary block", style: "min-height:96px;font-size:22px",
          onclick: () => { const v = Math.min(t.max || 999, (val() || 0) + 1); set(v); vibrate(15); if (v === t.max) vibrate([80, 60, 80]); } }, "+1 répétition"),
        h("div", { class: "row", style: "margin-top:8px" },
          h("button", { class: "btn ghost grow", onclick: () => set(Math.max(0, (val() || 0) - 1)) }, "−1"),
          h("button", { class: "btn ghost grow", onclick: () => set(0) }, "Zéro")));
    } else if (t.kind === "chrono") {
      const btn = h("button", { class: "btn primary block", style: "min-height:96px;font-size:22px" }, "Démarrer");
      let start = 0;
      btn.onclick = () => {
        if (timer) { stop(); vibrate([80, 60, 80]); btn.textContent = "Recommencer"; return; }
        let count = 3;
        btn.textContent = "Stop";
        out.textContent = count;
        timer = setInterval(() => {
          if (count > 1) { count -= 1; out.textContent = count; vibrate(30); return; }
          if (count === 1) { count = 0; start = Date.now(); vibrate(120); }
          const sec = Math.floor((Date.now() - start) / 1000);
          if (t.max && sec >= t.max) { set(t.max); stop(); vibrate([200, 80, 200]); btn.textContent = "Recommencer"; return; }
          set(sec);
        }, 250);
      };
      tool = h("div", {}, btn,
        h("div", { class: "row", style: "margin-top:8px" },
          h("button", { class: "btn ghost grow", onclick: () => set(Math.max(0, (val() || 0) - 1)) }, "−1 s"),
          h("button", { class: "btn ghost grow", onclick: () => set((val() || 0) + 1) }, "+1 s")));
    } else {
      tool = h("label", { class: "f" }, h("span", {}, "Mesure (cm)"),
        h("input", { class: "in", inputmode: "decimal", value: val() ?? "", oninput: (e) => {
          const v = e.target.value.replace(",", ".");
          if (v === "" || v === "-") { delete s.tests[t.id]; save(); out.textContent = "—"; return; }
          if (!Number.isNaN(Number(v))) set(Number(v));
        } }));
    }
    return win(`TEST · ${t.title}`,
      h("ul", { class: "cues" }, t.how.map((x) => h("li", {}, x))),
      out, tool,
      nav(() => val() != null, "Valider"),
      h("button", { class: "btn ghost block", style: "margin-top:8px", onclick: () => { delete s.tests[t.id]; save(); next(); } }, "Passer ce test"));
  }

  function confirm() {
    const status = h("div");
    const submit = async (btn) => {
      btn.disabled = true;
      try {
        const payload = { ...s, rest_day: Number(s.rest_day) };
        for (const k of ["weight", "arm", "chest", "waist", "thigh", "dumbbell_max", "dumbbell_step"]) {
          payload[k] = s[k] === "" ? null : Number(String(s[k]).replace(",", "."));
        }
        const r = await api.post("/api/awakening", payload);
        localStorage.removeItem(KEY);
        status.replaceChildren(
          win("ÉVEIL TERMINÉ", sysText(r.message || ""),
            h("div", { class: "spread", style: "margin-top:12px" }, h("span", {}, "Version"), h("b", { class: "num" }, "v1.0")),
            h("div", { class: "spread" }, h("span", {}, "Rang"), h("b", { class: "num" }, "E")),
            h("div", { class: "spread" }, h("span", {}, "XP"), h("b", { class: "num gold" }, `+${r.xp.gain}`))),
          win("COMPÉTENCES PLACÉES", ...Object.entries(r.placement)
            .filter(([fid]) => ["push_h", "pull_h", "push_v", "pull_v", "squat", "lunge", "hinge", "core_ant", "hang"].includes(fid))
            .map(([, p]) => h("div", { class: "spread", style: "font-size:14px;padding:3px 0" }, h("span", {}, p.name), h("b", { class: "num" }, `Niv. ${p.level}`)))),
          h("button", { class: "btn primary block", onclick: () => go("status") }, "Entrer dans le Système"));
        btn.remove();
      } catch (e) {
        btn.disabled = false;
        status.replaceChildren(h("p", { class: "alert" }, e.message));
      }
    };
    const btn = h("button", { class: "btn primary block", onclick: (e) => submit(e.currentTarget) }, "Compiler v1.0");
    return h("div", {},
      win("RÉCAPITULATIF",
        h("div", { class: "spread" }, h("span", {}, "Joueur"), h("b", {}, s.name)),
        ...TESTS.map((t) => h("div", { class: "spread", style: "font-size:14px" }, h("span", { class: "muted" }, t.title),
          h("b", { class: "num" }, s.tests[t.id] == null ? "—" : t.kind === "chrono" ? mmss(s.tests[t.id]) : s.tests[t.id]))),
        h("p", { class: "muted", style: "font-size:13px" }, "La 1re semaine sert de calibration : RIR cible 3, ajustements de ±2 crans autorisés.")),
      btn, status,
      h("button", { class: "btn ghost block", style: "margin-top:8px", onclick: prev }, "Retour"));
  }

  draw();
  return stop;
}
