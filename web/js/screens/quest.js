// Quest mode (full screen). The state is saved in localStorage after every set: a reload loses nothing.
import { api, completeQuest } from "../api.js";
import { go } from "../app.js";
import { h, kg, mmss, toast, vibrate, win } from "../ui.js";

const EQUIP = { H: "Haltères", P: "Planche", BT: "Barre", EL: "Élastique", HL: "Haltères lourds", BC: "Banc", GL: "Gilet lesté" };
const BLOCKS = { init: "INITIALISATION", main: "BLOC PRINCIPAL", variable: "BLOC VARIABLE", cooldown: "DÉSACTIVATION",
  recovery: "RÉCUPÉRATION", mobility: "MOBILITÉ" };

export async function render(app, [idStr]) {
  const id = Number(idStr);
  const data = await api.get(`/api/quests/${id}`);
  if (data.status === "done") {
    app.replaceChildren(win("QUÊTE TERMINÉE", h("p", {}, "Cette quête est déjà validée."),
      h("button", { class: "btn primary block", onclick: () => go("status") }, "Retour au Statut")));
    return;
  }
  const plan = data.plan;
  const steps = plan.steps;
  const KEY = `override:quest:${id}`;
  const fresh = { i: 0, phase: "work", sets: [], results: {}, adj: {}, skipped: [], suggested: {}, started: null, stepStart: null, restEnd: null };
  let st;
  try { st = { ...fresh, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch (_) { st = fresh; }
  const save = () => localStorage.setItem(KEY, JSON.stringify(st));

  // ---- timers & wake lock
  let tickFn = null;
  const interval = setInterval(() => tickFn && tickFn(), 200);
  let lock = null;
  const lockScreen = async () => { try { if ("wakeLock" in navigator && document.visibilityState === "visible") lock = await navigator.wakeLock.request("screen"); } catch (_) {} };
  const onVis = () => { if (document.visibilityState === "visible") { lockScreen(); draw(); } };
  document.addEventListener("visibilitychange", onVis);
  lockScreen();

  const exOf = (s) => (s && s.ex ? plan.exercises[s.ex] : null);
  const skipped = (s) => s && s.ex && st.skipped.includes(s.ex) && s.kind !== "timed";
  const targetOf = (s) => (s.block === "main" && st.adj[s.ex]?.target != null ? st.adj[s.ex].target : s.target);
  const loadOf = (s) => (s.block === "main" && st.adj[s.ex]?.load != null ? st.adj[s.ex].load : s.load);
  const nextIndex = (from) => { let j = from; while (j < steps.length && skipped(steps[j])) j++; return j; };

  function advance() {
    st.i = nextIndex(st.i + 1);
    st.phase = "work";
    st.stepStart = Date.now();
    st.restEnd = null;
    save();
    draw();
  }

  function startRest(sec) {
    if (sec <= 0) return advance();
    st.phase = "rest";
    st.restEnd = Date.now() + sec * 1000;
    save();
    draw();
  }

  // ---- layout pieces
  function top(s) {
    const blk = s ? (s.block === "variable" && plan.variable_name ? `${BLOCKS.variable} · ${plan.variable_name}` : BLOCKS[s.block] || "") : "";
    const pain = s && s.kind !== "timed" ? h("button", { class: "btn danger", style: "min-height:40px;padding:6px 12px", onclick: () => onPain(s) }, "Douleur") : null;
    return h("div", {},
      h("div", { class: "top" },
        h("button", { class: "btn ghost", style: "min-height:40px;padding:6px 12px", onclick: () => { save(); go("status"); } }, "Quitter"),
        h("span", { class: "grow", style: "text-align:center" }, blk),
        pain),
      h("div", { class: "prog" }, h("i", { style: `width:${(100 * st.i) / steps.length}%` })));
  }

  function exHeader(s, ex) {
    const eq = ex.equipment.map((c) => EQUIP[c] || c).join(", ") || "Poids du corps";
    const loadTxt = ex.load_mode === "pair" ? "charge par haltère" : ex.load_mode === "single" ? "1 haltère" : "";
    return h("div", {},
      h("div", { class: "muted num", style: "font-size:12px;letter-spacing:.12em" }, s.label),
      h("div", { class: "ex-name" }, ex.name),
      h("div", { class: "ex-meta" }, `Niv. ${ex.level}/${ex.max_level} · ${eq}${ex.unilateral ? " · par côté" : ""}${loadTxt ? " · " + loadTxt : ""}`),
      h("ul", { class: "cues" }, ex.cues.map((c) => h("li", {}, c))),
      ex.back_note ? h("div", { class: "backnote" }, `⚠ ${ex.back_note}`) : null);
  }

  function nextPreview(from) {
    const j = nextIndex(from);
    const n = steps[j];
    if (!n) return h("div", { class: "next" }, "Ensuite : fin de la quête");
    const ex = exOf(n);
    const name = ex ? ex.name : n.name;
    const tgt = n.kind === "timed" ? mmss(n.seconds) : ex ? (ex.type === "time" ? `${targetOf(n)} s` : `${targetOf(n)} rép.`) : "";
    const load = ex && loadOf(n) != null ? ` · ${kg(loadOf(n))}` : "";
    return h("div", { class: "next" }, `Ensuite : ${name} · ${tgt}${load}`);
  }

  // ---- screens
  function draw() {
    tickFn = null;
    st.i = nextIndex(st.i);
    if (st.i >= steps.length) return finish();
    const s = steps[st.i];
    if (!st.stepStart) { st.stepStart = Date.now(); save(); }
    let body;
    if (st.phase === "rest") body = restView(s);
    else if (s.kind === "timed") body = timedView(s);
    else if (s.kind === "amrap") body = amrapView(s);
    else if (s.kind === "chrono") body = chronoView(s);
    else body = setView(s);
    app.replaceChildren(h("div", { class: "runner" }, top(st.phase === "rest" ? null : s), h("div", { class: "body" }, body)));
  }

  function restView(s) {
    const out = h("div", { class: "bignum", style: "margin:28px 0 8px" }, mmss((st.restEnd - Date.now()) / 1000));
    tickFn = () => {
      const left = (st.restEnd - Date.now()) / 1000;
      out.textContent = mmss(left);
      if (left <= 0) { vibrate([200, 100, 200]); advance(); }
    };
    return h("div", {},
      h("div", { class: "win-h", style: "text-align:center;margin-top:30px" }, "[ REPOS ]"),
      out,
      nextPreview(st.i + 1),
      h("div", { class: "actions" }, h("button", { class: "btn primary block", onclick: advance }, "Passer")));
  }

  function timedView(s) {
    const total = s.seconds;
    const first = st.i === 0 && !st.started;
    let running = !first;
    let elapsed = 0;
    let last = Date.now();
    const perSide = (s.label || "").includes("par côté");
    let half = false;
    const out = h("div", { class: "bignum", style: "margin:20px 0" }, mmss(total));
    const btn = h("button", { class: "btn block" }, first ? "Démarrer" : "Pause");
    btn.onclick = () => {
      if (!st.started) { st.started = Date.now(); save(); }
      running = !running;
      last = Date.now();
      btn.textContent = running ? "Pause" : "Reprendre";
    };
    tickFn = () => {
      const now = Date.now();
      if (running) elapsed += (now - last) / 1000;
      last = now;
      const left = total - elapsed;
      out.textContent = mmss(left);
      if (perSide && !half && left <= total / 2) { half = true; vibrate([120, 60, 120]); toast("Change de côté"); }
      if (left <= 0) { vibrate(120); advance(); }
    };
    return h("div", {},
      h("div", { class: "muted num", style: "font-size:12px;letter-spacing:.12em" }, s.label),
      h("div", { class: "ex-name" }, s.name),
      s.cues && s.cues.length ? h("ul", { class: "cues" }, s.cues.map((c) => h("li", {}, c))) : null,
      out,
      nextPreview(st.i + 1),
      h("div", { class: "actions row" }, btn, h("button", { class: "btn primary grow", onclick: () => { if (!st.started) { st.started = Date.now(); } advance(); } }, "Suivant")));
  }

  function stepper(value, { step = 1, min = 0, max = 999, unit = "", fmt = (v) => v } = {}, onChange) {
    let v = value;
    const b = h("b", {}, fmt(v));
    const set = (nv) => { v = Math.round(Math.min(max, Math.max(min, nv)) * 100) / 100; b.textContent = fmt(v); onChange(v); };
    return h("div", { class: "stepper" },
      h("button", { onclick: () => set(v - step), "aria-label": "moins" }, "−"),
      h("div", { class: "val" }, b, h("span", {}, unit)),
      h("button", { onclick: () => set(v + step), "aria-label": "plus" }, "+"));
  }

  function setView(s) {
    const ex = exOf(s);
    const isTime = ex.type === "time";
    let done = targetOf(s);
    let load = loadOf(s);
    const parts = [exHeader(s, ex)];

    if (s.emom) {
      const clock = h("div", { class: "num muted", style: "text-align:center;margin-top:8px" });
      const upd = () => { clock.textContent = `Minute en cours : ${mmss(60 - ((Date.now() - st.stepStart) / 1000) % 60)} restantes`; };
      upd();
      parts.push(clock);
      tickFn = upd;
    }

    if (isTime) {
      const sides = ex.unilateral ? 2 : 1;
      const out = h("div", { class: "bignum", style: "margin:16px 0 4px" }, `${done}`, h("small", {}, " s"));
      const sideTxt = h("div", { class: "rir-cap" }, ex.unilateral ? `${done} s par côté` : "");
      const btn = h("button", { class: "btn primary block", style: "min-height:72px;font-size:20px" }, "Démarrer");
      const manual = h("button", { class: "btn ghost block", style: "margin-top:8px" }, "Saisir sans chrono");
      const after = h("div", { class: "hidden" });
      let phase = "idle", t0 = 0, count = 3, switched = false;
      const stopHold = () => {
        phase = "done";
        btn.classList.add("hidden");
        manual.classList.add("hidden");
        after.replaceChildren(
          stepper(done, { step: 1, min: 0, max: 600, unit: ex.unilateral ? "SECONDES PAR CÔTÉ" : "SECONDES TENUES" }, (v) => (done = v)),
          load != null ? loadStepper(ex, load, (v) => (load = v)) : null,
          rirPanel(() => record(s, ex, done, load)));
        after.classList.remove("hidden");
      };
      manual.onclick = () => { done = targetOf(s); stopHold(); };
      btn.onclick = () => {
        if (phase === "idle") { phase = "count"; count = 3; t0 = Date.now(); btn.textContent = "Stop"; out.textContent = "3"; vibrate(30); return; }
        if (phase === "run") { done = Math.floor((Date.now() - t0) / 1000 / sides); vibrate(80); stopHold(); }
      };
      const prevTick = tickFn;
      tickFn = () => {
        if (prevTick) prevTick();
        if (phase === "count") {
          const left = 3 - Math.floor((Date.now() - t0) / 1000);
          if (left !== count && left > 0) { count = left; out.textContent = String(left); vibrate(30); }
          if (left <= 0) { phase = "run"; t0 = Date.now(); vibrate(120); }
        } else if (phase === "run") {
          const tgt = targetOf(s);
          const sec = (Date.now() - t0) / 1000;
          if (sides === 2 && !switched && sec >= tgt) { switched = true; vibrate([120, 60, 120]); sideTxt.textContent = "CHANGE DE CÔTÉ"; }
          const left = tgt * sides - sec;
          out.replaceChildren(String(Math.max(0, Math.ceil(sides === 2 && !switched ? tgt - sec : left))), h("small", {}, " s"));
          if (left <= 0) { vibrate([200, 80, 200]); done = tgt; stopHold(); }
        }
      };
      parts.push(out, sideTxt, btn, manual, after);
    } else {
      parts.push(
        h("div", { class: "rir-cap", style: "margin-top:14px" }, `Cible : ${targetOf(s)} rép.${ex.unilateral ? " par côté" : ""} · plage ${ex.range[0]}-${ex.range[1]}`),
        stepper(done, { step: 1, min: 0, max: 100, unit: "RÉPÉTITIONS" }, (v) => (done = v)),
        load != null ? loadStepper(ex, load, (v) => (load = v)) : null,
        rirPanel(() => record(s, ex, done, load)));
    }
    parts.push(nextPreview(st.i + 1));
    return h("div", {}, ...parts);
  }

  function loadStepper(ex, load, onChange) {
    return stepper(load, { step: ex.load_step || 1, min: ex.load_step || 0, max: ex.max_load || 999, unit: "KG PAR HALTÈRE",
      fmt: (v) => Number(v).toLocaleString("fr-CH", { maximumFractionDigits: 2 }) }, onChange);
  }

  let pendingRir = null;
  function rirPanel(onPick) {
    const target = plan.rir_target;
    return h("div", {},
      h("div", { class: "rir-cap" }, `Répétitions en réserve · cible ${plan.rir_label || target}`),
      h("div", { class: "rir" }, [0, 1, 2, 3, 4].map((r) =>
        h("button", { class: r === target ? "target" : "", onclick: () => { pendingRir = r; vibrate(25); onPick(); } }, r === 4 ? "4+" : String(r)))));
  }

  function record(s, ex, done, load) {
    const rir = pendingRir;
    st.sets.push({ step: st.i, block: s.block, fid: ex.fid, variant_id: ex.variant_id, target: targetOf(s), load, done, rir, pain: false });
    if (!st.started) st.started = Date.now();
    save();
    const rest = s.emom ? Math.max(0, 60 - (Date.now() - st.stepStart) / 1000) : s.rest;
    const sug = s.block === "main" ? suggestion(s, ex, done, rir, load) : null;
    if (sug) return showSuggestion(sug, () => startRest(rest));
    startRest(rest);
  }

  // In-session autoregulation, from the plan's pre-computed adjustments.
  function suggestion(s, ex, done, rir, load) {
    const adj = ex.adjust || {};
    const remaining = steps.slice(st.i + 1).some((x) => x.ex === s.ex);
    if (!remaining) return null;
    if (s.set_index === 1 && rir >= 4 && !st.suggested[s.ex] && adj.up) {
      st.suggested[s.ex] = true;
      const opts = [];
      if (adj.up.target != null) opts.push([`${ex.type === "time" ? adj.up.target + " s" : adj.up.target + " rép."}`, { target: adj.up.target }]);
      if (adj.up.load != null) opts.push([`${kg(adj.up.load)}`, { load: adj.up.load }]);
      return { text: "[SYSTÈME] Marge détectée (RIR 4+). Augmentation proposée pour les séries suivantes :", opts };
    }
    if (rir === 0 && done < ex.range[0] && !st.suggested[`${s.ex}:down`] && adj.down) {
      st.suggested[`${s.ex}:down`] = true;
      const opts = [];
      if (adj.down.load != null) opts.push([`${kg(adj.down.load)}`, { load: adj.down.load }]);
      if (adj.down.target != null) opts.push([`${ex.type === "time" ? adj.down.target + " s" : adj.down.target + " rép."}`, { target: adj.down.target }]);
      return { text: "[SYSTÈME] Échec sous la plage. Réduction proposée pour les séries suivantes :", opts };
    }
    return null;
  }

  function showSuggestion(sug, then) {
    const box = h("div", { class: "suggest" }, h("div", { class: "sys" }, sug.text),
      h("div", { class: "row" },
        ...sug.opts.map(([label, change]) => h("button", { class: "btn primary grow", onclick: () => {
          const ex = steps[st.i].ex;
          st.adj[ex] = { ...(st.adj[ex] || {}), ...change };
          save(); then();
        } }, label)),
        h("button", { class: "btn ghost grow", onclick: then }, "Garder")));
    app.querySelector(".body").replaceChildren(box);
    save();
  }

  function itemsList(s) {
    return h("ul", { class: "cues" }, s.items.map((it) => {
      const ex = plan.exercises[it.ex];
      return h("li", {}, `${ex.name} · ${it.target}${ex.type === "time" ? " s" : " rép."}${ex.unilateral ? " par côté" : ""}${ex.load != null ? " · " + kg(ex.load) : ""}`);
    }));
  }

  function amrapView(s) {
    let rounds = 0, phase = "idle", t0 = 0;
    const out = h("div", { class: "bignum", style: "margin:16px 0" }, mmss(s.seconds));
    const btn = h("button", { class: "btn primary block" }, "Démarrer");
    const end = h("div", { class: "hidden" },
      stepper(0, { step: 1, min: 0, max: 99, unit: "TOURS COMPLETS" }, (v) => (rounds = v)),
      h("button", { class: "btn primary block", onclick: () => finishCircuit(s, { rounds }, rounds) }, "Valider"));
    btn.onclick = () => {
      if (phase === "idle") { phase = "run"; t0 = Date.now(); btn.textContent = "Terminer"; vibrate(120); }
      else { phase = "done"; btn.classList.add("hidden"); end.classList.remove("hidden"); }
    };
    tickFn = () => {
      if (phase !== "run") return;
      const left = s.seconds - (Date.now() - t0) / 1000;
      out.textContent = mmss(left);
      if (left <= 0) { vibrate([200, 80, 200]); phase = "done"; btn.classList.add("hidden"); end.classList.remove("hidden"); }
    };
    return h("div", {}, h("div", { class: "muted num", style: "font-size:12px;letter-spacing:.12em" }, s.label),
      h("div", { class: "ex-name" }, "Un maximum de tours"), itemsList(s), out, btn, end, nextPreview(st.i + 1));
  }

  function chronoView(s) {
    let phase = "idle", t0 = 0, sec = 0;
    const out = h("div", { class: "bignum", style: "margin:16px 0" }, "0:00");
    const btn = h("button", { class: "btn primary block" }, "Démarrer");
    btn.onclick = () => {
      if (phase === "idle") { phase = "run"; t0 = Date.now(); btn.textContent = "Terminé"; vibrate(120); return; }
      sec = Math.round((Date.now() - t0) / 1000);
      vibrate([200, 80, 200]);
      finishCircuit(s, { seconds: sec }, s.rounds);
    };
    tickFn = () => { if (phase === "run") out.textContent = mmss((Date.now() - t0) / 1000); };
    return h("div", {}, h("div", { class: "muted num", style: "font-size:12px;letter-spacing:.12em" }, s.label),
      h("div", { class: "ex-name" }, `${s.rounds} tours, le plus vite possible`), itemsList(s), out, btn, nextPreview(st.i + 1));
  }

  function finishCircuit(s, result, rounds) {
    st.results[st.i] = result;
    for (const it of s.items) {
      const ex = plan.exercises[it.ex];
      st.sets.push({ step: st.i, block: s.block, fid: ex.fid, variant_id: ex.variant_id, target: it.target,
        load: ex.load, done: it.target * rounds, rir: null, pain: false });
    }
    save();
    startRest(s.rest || 0);
  }

  function onPain(s) {
    const ex = exOf(s);
    st.sets.push({ step: st.i, block: s.block, fid: ex ? ex.fid : null, variant_id: ex ? ex.variant_id : null,
      target: s.target, load: s.load, done: null, rir: null, pain: true });
    if (s.ex) st.skipped.push(s.ex);
    save();
    vibrate([100, 50, 100]);
    toast("Douleur notée. Exercice arrêté.");
    advance();
  }

  async function finish() {
    tickFn = null;
    const box = h("div", {}, win("TRANSMISSION", h("div", { class: "sys" }, "[SYSTÈME] Envoi du rapport de quête…")));
    app.replaceChildren(box);
    const payload = { sets: st.sets, results: st.results, duration_s: st.started ? Math.round((Date.now() - st.started) / 1000) : null };
    try {
      const report = await completeQuest(id, payload);
      localStorage.removeItem(KEY);
      sessionStorage.setItem(`override:report:${id}`, JSON.stringify(report));
      go(`report/${id}`);
    } catch (e) {
      box.replaceChildren(win("CONNEXION PERDUE", h("p", {}, e.message),
        h("button", { class: "btn primary block", onclick: finish }, "Réessayer"),
        h("button", { class: "btn ghost block", style: "margin-top:8px", onclick: () => go("status") }, "Retour au Statut")));
    }
  }

  draw();
  return () => {
    clearInterval(interval);
    document.removeEventListener("visibilitychange", onVis);
    try { lock && lock.release(); } catch (_) {}
  };
}
