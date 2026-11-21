"""Rank trials and fact-based conditions (shared with titles)."""
from __future__ import annotations

RANKS = "EDCBAS"


def next_rank(rank: str) -> str | None:
    i = RANKS.index(rank)
    return RANKS[i + 1] if i + 1 < len(RANKS) else None


def condition_ok(cond: dict, metrics: dict) -> bool:
    val = metrics.get(cond["metric"])
    if val is None:
        return False
    if "min" in cond and val < cond["min"]:
        return False
    if "max" in cond and val > cond["max"]:
        return False
    return True


def evaluate_trials(rank_def: dict, metrics: dict) -> list[dict]:
    """For each trial: passed or not, plus the current values to show what is missing."""
    out = []
    for t in rank_def["trials"]:
        options = [all(condition_ok(c, metrics) for c in opt) for opt in t["options"]]
        conds = [{"metric": c["metric"], "current": metrics.get(c["metric"]),
                  "min": c.get("min"), "max": c.get("max"), "ok": condition_ok(c, metrics)}
                 for opt in t["options"] for c in opt]
        out.append({"label": t["label"], "ok": any(options), "conditions": conds})
    return out


def trials_passed(results: list[dict]) -> int:
    return sum(1 for r in results if r["ok"])
