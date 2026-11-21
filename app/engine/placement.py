"""Awakening: place each skill from the guided tests and compute starting stats."""
from __future__ import annotations

from .catalog import Catalog, Inventory

STRENGTH_FAMILIES = ("push_h", "pull_h", "push_v", "pull_v", "squat", "lunge", "hinge")
BASE_STAT = 10


def level_from_test(value: float, levels: list[list[float]]) -> int:
    lvl = 1
    for minimum, level in levels:
        if value >= minimum:
            lvl = int(level)
    return lvl


def initial_state(catalog: Catalog, inventory: Inventory, fid: str, level: int) -> dict:
    v = catalog.variant(fid, level)
    target = v["range"][0]
    return {"level": level, "load": inventory.start_load(v), "target": target, "fail_streak": 0}


def place_skills(catalog: Catalog, inventory: Inventory, tests: dict, placement: dict) -> dict[str, dict]:
    states: dict[str, dict] = {}
    for fid, fam in catalog.families.items():
        rule = placement.get(fid)
        if rule and rule.get("test") in tests:
            level = level_from_test(float(tests[rule["test"]]), rule["levels"])
        elif fam.get("zone"):
            level = catalog.max_level(fid)          # all drills of a zone are open by default
        else:
            level = 1
        level = min(level, catalog.max_level(fid))
        # never place on a variant the inventory cannot support
        while level > 1 and not inventory.has_all(catalog.variant(fid, level)["equipment"]):
            level -= 1
        state = initial_state(catalog, inventory, fid, level)
        v = catalog.variant(fid, level)
        ratio = (rule or {}).get("target_ratio")
        if ratio and v["type"] == "time" and rule["test"] in tests:
            lo, hi = v["range"]
            state["target"] = int(max(lo, min(hi, round(float(tests[rule["test"]]) * ratio / 5) * 5)))
        states[fid] = state
    return states


def mobility_scores(tests: dict, mapping: dict) -> dict[str, float]:
    """Zone -> score in 0..1 (1 = best). Only zones with a test are scored."""
    scores = {}
    for test, m in mapping.items():
        if test.startswith("_") or test not in tests:
            continue
        worst, best = float(m["worst"]), float(m["best"])
        s = (float(tests[test]) - worst) / (best - worst) if best != worst else 0.0
        scores[m["zone"]] = round(max(0.0, min(1.0, s)), 3)
    return scores


def weakest_zone(scores: dict[str, float], default: str = "mob_hips") -> str:
    if not scores:
        return default
    return min(scores.items(), key=lambda kv: (kv[1], kv[0]))[0]


def starting_stats(catalog: Catalog, states: dict[str, dict]) -> dict[str, int]:
    """FOR gets +5 per variant level above 1 on the strength families; other stats start at 10."""
    strength = BASE_STAT + 5 * sum(max(0, states[f]["level"] - 1) for f in STRENGTH_FAMILIES if f in states)
    return {"FOR": strength, "GAB": BASE_STAT, "MOB": BASE_STAT, "VIT": BASE_STAT}
