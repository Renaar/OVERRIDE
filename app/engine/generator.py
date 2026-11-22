"""Quest generation: main quest (HAUT / BAS / RECAL), recovery quest and daily mobility quest.

The output is a plain JSON-able plan. `steps` is the flat list the quest runner plays one by one.
Step kinds:
  timed  : a countdown that auto-advances (warm-up, cool-down, mobility drills)
  set    : one set, reps or time, validated with a RIR tap
  amrap  : as many rounds as possible in `seconds`; the player enters the rounds done
  chrono : complete `rounds` of the items as fast as possible; the elapsed time is recorded
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from .catalog import Catalog, Inventory
from .checkin import CheckinResult
from .patch import PatchInfo
from .safety import lock_reason

LABELS = {"HAUT": "HAUT DU CORPS", "BAS": "BAS DU CORPS", "RECAL": "RECALIBRAGE",
          "RECOVERY": "RÉCUPÉRATION", "MOBILITY": "MOBILITÉ"}

# Variable block sizes: (default, minimum). EMOM/AMRAP in minutes, ECHELLE in rungs, CHRONO/ISO in rounds.
VAR_SIZES = {"EMOM": (5, 2), "ECHELLE": (4, 2), "CHRONO": (3, 1), "AMRAP": (5, 2), "ISO": (3, 1)}
VAR_NAMES = {"EMOM": "EMOM", "ECHELLE": "ÉCHELLE", "CHRONO": "CHRONO", "AMRAP": "AMRAP", "ISO": "ISOMÉTRIE"}

TENSE_POOL = ["core_ant", "core_lat", "anti_rot", "mob_hips", "mob_thoracic"]
TENSE_ISO_POOL = ["core_ant", "core_lat"]


@dataclass
class GenContext:
    day: date
    quest_type: str                       # HAUT | BAS | RECAL
    checkin: CheckinResult
    patch: PatchInfo
    rir: int
    skills: dict[str, dict]               # fid -> {"level", "load", "target", ...}
    inventory: Inventory
    hinge_unlocked: bool
    last_format: str | None = None
    rest_seconds: int = 60
    superset_rest_seconds: int = 20
    weakest_zone: str = "mob_hips"
    deficits: dict[str, int] = field(default_factory=dict)      # group -> missing sets this week
    extra_rounds: dict[str, int] = field(default_factory=dict)  # fid -> extra rounds (Focus, volume)


# ---------------------------------------------------------------- exercises

def resolve_variant(catalog: Catalog, fid: str, level: int, inventory: Inventory,
                    hinge_unlocked: bool) -> tuple[dict | None, int]:
    """Highest usable variant at or below `level`."""
    for lvl in range(min(level, catalog.max_level(fid)), 0, -1):
        v = catalog.variant(fid, lvl)
        if lock_reason(v, inventory, hinge_unlocked) is None:
            return v, lvl
    return None, 0


def prescribe(catalog: Catalog, fid: str, state: dict | None, inventory: Inventory,
              hinge_unlocked: bool, rng: random.Random | None = None) -> dict | None:
    state = state or {"level": 1, "load": None, "target": None}
    if catalog.is_zone(fid):
        # a mobility zone: pick one open drill
        opts = [v for v in catalog.variants(fid)[: state["level"]]
                if lock_reason(v, inventory, hinge_unlocked) is None]
        if not opts:
            return None
        v = (rng or random.Random(0)).choice(opts)
        level, same = v["level"], False
    else:
        v, level = resolve_variant(catalog, fid, state["level"], inventory, hinge_unlocked)
        if v is None:
            return None
        same = level == state["level"]
    lo, hi = v["range"]
    target = state.get("target") if same and state.get("target") else lo
    load = state.get("load") if same and state.get("load") is not None else inventory.start_load(v)
    lim = inventory.load_limits(v)
    if lim is None:
        load = None
    else:
        load = min(load, lim[0])
    return {
        "fid": fid, "variant_id": v["id"], "name": v["name"], "level": level,
        "max_level": catalog.max_level(fid), "type": v["type"], "range": [lo, hi],
        "target": int(target), "load": load, "load_mode": v.get("load_mode", "none"),
        "max_load": lim[0] if lim else None, "load_step": lim[1] if lim else None,
        "unilateral": bool(v.get("unilateral")), "rep_s": v.get("rep_s", 3),
        "cues": v["cues"], "back_note": v.get("back_note", ""), "equipment": v["equipment"],
        "groups": v["groups"], **howto(v),
    }


def work_seconds(ex: dict, target: int | None = None) -> int:
    t = ex["target"] if target is None else target
    per = t * ex["rep_s"] if ex["type"] == "reps" else t
    return int(per * (2 if ex["unilateral"] else 1))


def adjustments(ex: dict, calibration: bool, calibration_steps: int = 2) -> dict:
    """Pre-computed in-session suggestions. up: after a first set at RIR 4+. down: RIR 0 under the range."""
    k = calibration_steps if calibration else 1
    up: dict = {}
    down: dict = {}
    if ex["type"] == "reps":
        up["target"] = ex["target"] + 2 * k
    else:
        up["target"] = ex["target"] + 5 * k
    if ex["load"] is not None and ex["load_step"]:
        hi = round(ex["load"] + k * ex["load_step"], 2)
        if hi <= ex["max_load"] + 1e-9:
            up["load"] = hi
        lo = round(ex["load"] - k * ex["load_step"], 2)
        if lo >= ex["load_step"] - 1e-9:
            down["load"] = lo
    if "load" not in down:
        down["target"] = max(1, ex["target"] - (2 if ex["type"] == "reps" else 5) * k)
    return {"up": up, "down": down}


def _step(key: str, ex: dict, block: str, label: str, rest: int, target: int | None = None,
          kind: str = "set", **extra) -> dict:
    t = ex["target"] if target is None else int(target)
    return {"kind": kind, "block": block, "ex": key, "label": label, "target": t, "load": ex["load"],
            "rest": int(rest), "work": work_seconds(ex, t), **extra}


HOWTO_KEYS = ("steps", "mistakes", "figure", "figure_tempo", "video_query", "video_url")


def howto(item: dict) -> dict:
    """Explanation fields shown by the 'Comment faire ?' sheet (figure, detailed steps, video search)."""
    out = {k: item[k] for k in HOWTO_KEYS if item.get(k)}
    out.setdefault("video_url", "")
    return out


def _timed(block: str, name: str, seconds: int, label: str = "", item: dict | None = None) -> dict:
    item = item or {}
    return {"kind": "timed", "block": block, "name": name, "label": label, "seconds": int(seconds),
            "work": int(seconds), "rest": 0, "cues": item.get("cues", []),
            "back_note": item.get("back_note", ""), **howto(item)}


# ---------------------------------------------------------------- estimation

def estimate_seconds(steps: list[dict], transition: int = 15) -> int:
    """Work + rest + a transition whenever a new exercise starts (superset alternation is free)."""
    total = 0
    recent: list[str] = []
    for s in steps:
        total += s["work"] + s["rest"]
        if s["kind"] != "timed":
            if s["ex"] not in recent[-2:]:
                total += transition
            recent.append(s["ex"])
    return total


# ---------------------------------------------------------------- variable block

def _fits_format(fmt: str, ex: dict) -> bool:
    if fmt == "ECHELLE":
        return ex["type"] == "reps"
    if fmt == "ISO":
        return ex["type"] == "time"
    return True


def _pick(catalog: Catalog, ctx: GenContext, pool: list[str], fmt: str, rng: random.Random,
          exclude: set[str], n: int = 2) -> list[dict]:
    cands = []
    for fid in pool:
        if fid in exclude or fid not in catalog.families:
            continue
        ex = prescribe(catalog, fid, ctx.skills.get(fid), ctx.inventory, ctx.hinge_unlocked, rng)
        if ex and _fits_format(fmt, ex):
            cands.append(ex)
    rng.shuffle(cands)
    # groups behind their weekly target come first
    cands.sort(key=lambda e: -max([ctx.deficits.get(g, 0) for g in e["groups"]] or [0]))
    return cands[:n]


def build_variable(fmt: str, exes: list[dict], size: int) -> list[dict]:
    if not exes or size <= 0:
        return []
    keys = [f"v:{e['fid']}" for e in exes]
    title = VAR_NAMES[fmt]
    steps: list[dict] = []
    if fmt == "EMOM":
        for m in range(size):
            i = m % len(exes)
            ex = exes[i]
            if ex["type"] == "reps":
                per_rep = ex["rep_s"] * (2 if ex["unilateral"] else 1)
                t = max(3, min(round(ex["target"] * 0.6), 40 // per_rep))
            else:
                t = min(ex["target"], 20 if ex["unilateral"] else 40)
            s = _step(keys[i], ex, "variable", f"{title} · minute {m + 1}/{size}", 0, t, emom=60)
            s["rest"] = max(0, 60 - s["work"])
            steps.append(s)
    elif fmt == "ECHELLE":
        for k in range(1, size + 1):
            for i, ex in enumerate(exes):
                t = max(2, round(ex["target"] * k / size))
                steps.append(_step(keys[i], ex, "variable", f"{title} · palier {k}/{size}", 15, t))
    elif fmt == "ISO":
        for r in range(1, size + 1):
            for i, ex in enumerate(exes):
                steps.append(_step(keys[i], ex, "variable", f"{title} · tour {r}/{size}", 20))
    elif fmt in ("AMRAP", "CHRONO"):
        ratio = 0.5 if fmt == "AMRAP" else 0.7
        items = [{"ex": keys[i], "target": max(3, round(ex["target"] * ratio))} for i, ex in enumerate(exes)]
        round_work = sum(work_seconds(ex, it["target"]) for ex, it in zip(exes, items))
        if fmt == "AMRAP":
            steps.append({"kind": "amrap", "block": "variable", "ex": keys[0], "label": f"{title} · {size} min",
                          "items": items, "seconds": size * 60, "work": size * 60, "rest": 0})
        else:
            steps.append({"kind": "chrono", "block": "variable", "ex": keys[0],
                          "label": f"{title} · {size} tours", "items": items, "rounds": size,
                          "work": int(size * round_work * 1.15), "rest": 0})
    return steps


# ---------------------------------------------------------------- main quest

def _main_rounds(ctx: GenContext, fid: str, cfg: dict, rir_cfg: dict) -> int:
    base = cfg["base_rounds"] + ctx.extra_rounds.get(fid, 0)
    if ctx.patch.deload:
        base = round(base * rir_cfg.get("deload_sets_ratio", 0.6))
    base -= ctx.checkin.set_penalty
    return max(cfg["min_rounds"], base)


def generate_main(catalog: Catalog, ctx: GenContext, config: dict) -> dict:
    qcfg, rir_cfg = config["quest"], config["rir"]
    tpl = config["templates"][ctx.quest_type]
    rng = random.Random(f"{ctx.day.isoformat()}:{ctx.quest_type}")
    notes: list[str] = []

    supersets = [list(ss) for ss in tpl["supersets"]]
    pool, iso_pool = list(tpl["variable_pool"]), list(tpl["iso_pool"])
    if ctx.checkin.no_loaded_hinge:
        used = {f for ss in supersets for f in ss}
        for ss in supersets:
            if "hinge" in ss:
                ss[ss.index("hinge")] = "anti_rot" if "anti_rot" not in used else "core_ant"
                notes.append("Dos tendu : charnière remplacée par du gainage.")
        pool, iso_pool = TENSE_POOL, TENSE_ISO_POOL

    # --- main block
    exercises: dict[str, dict] = {}
    main_ss: list[list[str]] = []
    for ss in supersets:
        keys = []
        for fid in ss:
            ex = prescribe(catalog, fid, ctx.skills.get(fid), ctx.inventory, ctx.hinge_unlocked, rng)
            if ex is None:
                notes.append(f"{catalog.family(fid)['name']} : aucune variante disponible.")
                continue
            ex["adjust"] = adjustments(ex, ctx.patch.calibration, rir_cfg.get("calibration_steps", 2))
            ex["main"] = True
            exercises[fid] = ex
            keys.append(fid)
        if keys:
            main_ss.append(keys)
    rounds = [max(_main_rounds(ctx, k, qcfg, rir_cfg) for k in ss) for ss in main_ss]

    # --- variable block: a format different from last time
    formats = [f for f in qcfg["variable_formats"] if f != ctx.last_format]
    rng.shuffle(formats)
    fmt, var_exes = None, []
    for f in formats:
        var_exes = _pick(catalog, ctx, iso_pool if f == "ISO" else pool, f, rng, set(exercises))
        if var_exes:
            fmt = f
            break
    var_size = 0
    if fmt:
        default, vmin = VAR_SIZES[fmt]
        var_size = default
        if ctx.patch.deload:
            var_size = max(vmin, round(default * rir_cfg.get("deload_sets_ratio", 0.6)))
        if ctx.checkin.set_penalty:
            var_size = max(vmin, var_size - ctx.checkin.set_penalty)
        for e in var_exes:
            exercises[f"v:{e['fid']}"] = e

    warm = catalog.warmups.get(ctx.quest_type, [])
    cool = catalog.cooldown
    max_s = qcfg["max_minutes"] * 60

    def build() -> list[dict]:
        steps = [_timed("init", w["name"], w["seconds"], "Initialisation", w) for w in warm]
        for si, ss in enumerate(main_ss):
            n = rounds[si]
            for r in range(1, n + 1):
                for j, key in enumerate(ss):
                    last = j == len(ss) - 1
                    rest = ctx.rest_seconds if last else ctx.superset_rest_seconds
                    steps.append(_step(key, exercises[key], "main",
                                       f"Superset {si + 1} · tour {r}/{n}", rest,
                                       set_index=r, sets_total=n))
        if fmt and var_size > 0:
            steps += build_variable(fmt, var_exes, var_size)
        steps += [_timed("cooldown", c["name"], c["seconds"], "Désactivation", c) for c in cool]
        return steps

    steps = build()
    while estimate_seconds(steps, qcfg["transition_seconds"]) > max_s:
        if fmt and var_size > VAR_SIZES[fmt][1]:
            var_size -= 1
        elif fmt and var_size > 0:
            var_size = 0
            notes.append("Bloc variable retiré pour tenir en 25 min.")
        else:
            i = max(range(len(rounds)), key=lambda k: (rounds[k], k)) if rounds else None
            if i is None or rounds[i] <= qcfg["min_rounds"]:
                break
            rounds[i] -= 1
        steps = build()
    if not var_size:
        fmt = None
        for e in var_exes:
            exercises.pop(f"v:{e['fid']}", None)

    est = estimate_seconds(steps, qcfg["transition_seconds"])
    rir_label = "3-4" if ctx.patch.deload else str(ctx.rir)
    return {
        "kind": "main", "type": ctx.quest_type, "label": LABELS[ctx.quest_type], "mode": ctx.checkin.mode,
        "deload": ctx.patch.deload, "calibration": ctx.patch.calibration, "week": ctx.patch.week,
        "rir_target": ctx.rir, "rir_label": rir_label, "variable_format": fmt,
        "variable_name": VAR_NAMES.get(fmt) if fmt else None,
        "estimate_s": est, "estimate_min": round(est / 60), "exercises": exercises,
        "steps": steps, "notes": notes,
    }


# ---------------------------------------------------------------- recovery & mobility

def generate_recovery(catalog: Catalog) -> dict:
    steps = [_timed("recovery", r["name"], r["seconds"], "Récupération", r) for r in catalog.recovery]
    est = estimate_seconds(steps)
    return {"kind": "main", "type": "RECOVERY", "label": LABELS["RECOVERY"], "mode": "recovery",
            "rir_target": None, "rir_label": "-", "variable_format": None, "estimate_s": est,
            "estimate_min": round(est / 60), "exercises": {}, "steps": steps,
            "notes": ["Dos douloureux : mobilité douce uniquement. Aucune pénalité."]}


MOBILITY_ZONES = ["mob_hips", "mob_thoracic", "mob_shoulders", "mob_ankles", "mob_hams"]


def generate_mobility(catalog: Catalog, day: date, skills: dict[str, dict], inventory: Inventory,
                      weakest_zone: str, total_seconds: int = 300, drill_seconds: int = 60,
                      extra_seconds: int = 0) -> dict:
    """Daily 5-min mobility: the weakest zone first, then other zones."""
    rng = random.Random(f"{day.isoformat()}:mobility")
    n = max(1, (total_seconds + extra_seconds) // drill_seconds)

    def drills(zone: str) -> list[dict]:
        lvl = (skills.get(zone) or {}).get("level", catalog.max_level(zone))
        out = [v for v in catalog.variants(zone)[:lvl] if inventory.has_all(v["equipment"])]
        rng.shuffle(out)
        return out

    chosen = drills(weakest_zone)[:2]
    others = [z for z in MOBILITY_ZONES if z != weakest_zone and z in catalog.families]
    rng.shuffle(others)
    while len(chosen) < n and others:
        for z in list(others):
            pick = [d for d in drills(z) if d not in chosen]
            if pick:
                chosen.append(pick[0])
            others.remove(z)
            if len(chosen) >= n:
                break
    steps = []
    for d in chosen[:n]:
        label = "Mobilité · par côté" if d.get("unilateral") else "Mobilité"
        steps.append(_timed("mobility", d["name"], drill_seconds, label, d))
    est = estimate_seconds(steps)
    return {"kind": "mobility", "type": "MOBILITY", "label": LABELS["MOBILITY"], "zone": weakest_zone,
            "estimate_s": est, "estimate_min": round(est / 60), "exercises": {}, "steps": steps, "notes": []}
