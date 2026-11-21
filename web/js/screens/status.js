// Status (home): player window, quests of the day, next rank trial, System message.
import { api } from "../api.js";
import { applyPrefs, go } from "../app.js";
import { h, overlay, sysText, win } from "../ui.js";

const STAT_NAMES = { FOR: "FOR", GAB: "GAB", MOB: "MOB", VIT: "VIT" };
const METRIC_UNITS = { pushups: "", pullups: "", plank_s: " s", hang_s: " s", deep_squat_s: " s", side_plank_s: " s",
  arm_gain_cm: " cm", waist_gain_cm: " cm", weight_gain_kg: " kg", toe_touch_cm: " cm", cossack_reps: "", pistol_reps: "",
  palms_floor: "", farmer_20kg_s: " s", weighted_pullups_10kg: "" };

export async function render(app) {
  const st = await api.get("/api/state");
  applyPrefs(st);
  const p = st.player;
  const pct = Math.min(100, (100 * p.xp) / p.xp_next);

  const statusWin = win("STATUT",
    h("div", { class: "row" },
      h("div", { class: "grow" },
        h("div", { class: "player-name" }, p.name),
        h("div", { class: "player-title" }, p.title || "—"),
        h("div", { class: "muted num", style: "font-size:13px" }, `${p.version} · ${st.patch.label} · semaine ${st.patch.week}/4`)),
      h("div", { class: "rank-badge", style: `color:${p.rank_color}`, title: "Rang" }, p.rank)),
    h("div", { class: "spread", style: "margin-top:12px" },
      h("span", { class: "num" }, `NIV. ${p.level}`),
      h("span", { class: "num muted", style: "font-size:13px" }, `${p.xp} / ${p.xp_next} XP`)),
    h("div", { class: "bar xp" }, h("i", { style: `width:${pct}%` })),
    h("div", { class: "stats" }, Object.entries(STAT_NAMES).map(([k, n]) =>
      h("div", { class: "stat" }, h("b", {}, p.stats[k]), h("span", {}, n)))),
    h("div", { class: "spread", style: "margin-top:10px" },
      h("span", { class: "muted" }, `Série : ${p.streak} jour${p.streak > 1 ? "s" : ""}`),
      h("span", { class: "num gold" }, `×${p.multiplier.toFixed(1)}`)),
    p.focus_points ? h("div", { class: "ok", style: "font-size:13px;margin-top:4px" },
      `${p.focus_points} point${p.focus_points > 1 ? "s" : ""} de Focus en attente (placement en phase 3)`) : null,
  );

  const banner = st.physio_banner ? h("section", { class: "win warn-win" }, h("h2", { class: "win-h" }, "[ VIGILANCE ]"),
    h("p", { style: "margin:0" }, "Dos tendu ou douloureux 3 fois en 14 jours. Un avis de kiné est recommandé.")) : null;

  // ---- quests of the day
  const items = [];
  const mq = st.main_quest;
  items.push(questRow(st.checkin ? "done" : null, "CHECK-IN", st.checkin ? "Sommeil, énergie, dos : enregistrés" : "3 taps avant la quête · +5 XP",
    st.checkin ? null : h("button", { class: "btn primary", onclick: () => openCheckin(st) }, "Check-in")));
  if (st.day_kind === "rest") {
    items.push(questRow(null, "JOUR DE REPOS", "Aucune quête principale aujourd'hui."));
  } else if (!mq) {
    items.push(questRow(null, "QUÊTE PRINCIPALE", "Générée après le check-in."));
  } else if (mq.type === "AWAKENING") {
    items.push(questRow("done", "ÉVEIL", "Première quête accomplie."));
  } else {
    const sub = [`${mq.estimate_min} min`, mq.mode === "light" ? "allégée" : null, mq.rir && mq.rir !== "-" ? `RIR ${mq.rir}` : null,
      mq.variable ? `bloc ${mq.variable}` : null].filter(Boolean).join(" · ");
    items.push(questRow(mq.status === "done" ? "done" : null, `QUÊTE PRINCIPALE · ${mq.label}`, sub,
      mq.status === "done" ? h("span", { class: "gold num" }, `+${mq.xp}`) :
        h("button", { class: "btn primary", onclick: () => go(`quest/${mq.id}`) }, "Lancer")));
    for (const n of mq.notes || []) items.push(h("div", { class: "warn", style: "font-size:13px;padding:0 0 6px 38px" }, n));
  }
  const mob = st.mobility_quest;
  if (mob) {
    items.push(questRow(mob.status === "done" ? "done" : null, "MOBILITÉ", `${mob.estimate_min} min · zone prioritaire`,
      mob.status === "done" ? h("span", { class: "gold num" }, `+${mob.xp}`) :
        h("button", { class: "btn", onclick: () => go(`quest/${mob.id}`) }, "Lancer")));
  }
  const questsWin = win("QUÊTES DU JOUR", ...items);

  // ---- next rank trial
  const t = st.next_trial;
  const trialWin = t ? win(`PROCHAINE ÉPREUVE · RANG ${t.rank}`,
    h("div", { class: "muted", style: "font-size:13px;margin-bottom:6px" },
      `Fin de patch · ${t.required} épreuves sur ${t.trials.length} · réussies aujourd'hui : ${t.passed}`),
    ...t.trials.map((tr) => h("div", { class: "trial" },
      h("span", { class: `mark ${tr.ok ? "ok" : "muted"}` }, tr.ok ? "■" : "□"),
      h("span", { class: "grow" }, tr.label,
        h("span", { class: "muted", style: "display:block;font-size:12px" }, tr.conditions.map(currentValue).join(" · ")))))) : null;

  const sysWin = win("SYSTÈME", sysText(st.message));

  const links = h("div", { class: "row" },
    h("button", { class: "btn ghost grow", onclick: () => go("settings") }, "Réglages"));

  app.replaceChildren(statusWin, banner || "", questsWin, sysWin, trialWin || "", links);
}

function currentValue(c) {
  const unit = METRIC_UNITS[c.metric] ?? "";
  const cur = c.current == null ? "?" : `${c.current}${unit}`;
  const goal = c.min != null ? `≥ ${c.min}${unit}` : `≤ ${c.max}${unit}`;
  return `actuel ${cur} / ${goal}`;
}

function questRow(state, title, sub, action) {
  return h("div", { class: "quest" },
    h("div", { class: `check ${state === "done" ? "done" : ""}` }, state === "done" ? "✓" : ""),
    h("div", { class: "q-main" }, h("div", { class: "q-title" }, title), sub ? h("div", { class: "q-sub" }, sub) : null),
    action || null);
}

function openCheckin(st) {
  const sel = {};
  const groups = [
    ["sleep", "SOMMEIL", [["mauvais", "Mauvais", "bad"], ["correct", "Correct", "mid"], ["bon", "Bon", ""]]],
    ["energy", "ÉNERGIE", [["basse", "Basse", "bad"], ["normale", "Normale", "mid"], ["haute", "Haute", ""]]],
    ["back", "DOS", [["ok", "OK", ""], ["tendu", "Tendu", "mid"], ["douloureux", "Douloureux", "bad"]]],
  ];
  const go_ = h("button", { class: "btn primary block", disabled: true }, "Valider");
  const body = h("div", {}, ...groups.map(([key, label, opts]) => {
    const row = h("div", { class: "choice" });
    opts.forEach(([v, l, tone]) => row.append(h("button", {
      class: tone, onclick: (e) => {
        sel[key] = v;
        row.querySelectorAll("button").forEach((b) => b.classList.remove("sel"));
        e.currentTarget.classList.add("sel");
        go_.disabled = Object.keys(sel).length < 3;
      } }, l)));
    return h("div", {}, h("div", { class: "num muted", style: "font-size:12px;letter-spacing:.14em" }, label), row);
  }), go_);
  const o = overlay(win("CHECK-IN", body), { onClose: () => {} });
  go_.onclick = async () => {
    go_.disabled = true;
    try {
      const r = await api.post("/api/checkin", sel);
      o.remove();
      const q = r.quest;
      const plan = q && q.plan;
      const res = overlay(win("ANALYSE", sysText(r.message || ""),
        plan ? h("div", { class: "spread", style: "margin-top:12px" }, h("b", { class: "num" }, plan.label), h("span", { class: "num" }, `${plan.estimate_min} min`)) : null,
        h("div", { class: "row", style: "margin-top:14px" },
          h("button", { class: "btn ghost grow", onclick: () => { res.remove(); render(document.querySelector("#app")); } }, "Plus tard"),
          plan && q.status !== "done" && q.subtype !== "AWAKENING" ? h("button", { class: "btn primary grow", onclick: () => { res.remove(); go(`quest/${q.id}`); } }, "Lancer") : null)));
    } catch (e) {
      go_.disabled = false;
      body.append(h("p", { class: "alert" }, e.message));
    }
  };
}
