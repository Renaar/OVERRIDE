"""Read-only access to the skill tree (data/skills.json)."""
from __future__ import annotations

import math


class Catalog:
    def __init__(self, skills: dict):
        self.raw = skills
        self.families: dict[str, dict] = {f["id"]: f for f in skills["families"]}
        self.warmups: dict[str, list] = skills.get("warmups", {})
        self.cooldown: list = skills.get("cooldown", [])
        self.recovery: list = skills.get("recovery", [])
        self.groups: dict[str, str] = skills.get("groups", {})
        self.equipment: dict[str, str] = skills.get("equipment", {})

    def family(self, fid: str) -> dict:
        return self.families[fid]

    def variants(self, fid: str) -> list[dict]:
        return self.families[fid]["variants"]

    def variant(self, fid: str, level: int) -> dict:
        vs = self.variants(fid)
        return vs[max(1, min(level, len(vs))) - 1]

    def max_level(self, fid: str) -> int:
        return len(self.variants(fid))

    def is_zone(self, fid: str) -> bool:
        return bool(self.families[fid].get("zone"))


class Inventory:
    """What the player owns. `owned` holds equipment codes; loads are per dumbbell (kg)."""

    def __init__(self, owned: set[str], limits: dict[str, tuple[float, float]] | None = None):
        self.owned = set(owned)
        # code -> (max_load, step); H and HL are the loaded items.
        self.limits = limits or {}

    def has_all(self, codes: list[str]) -> bool:
        return all(c in self.owned for c in codes)

    def load_limits(self, variant: dict) -> tuple[float, float] | None:
        """(max, step) of the dumbbells this variant uses, or None if it carries no load."""
        if variant.get("load_mode", "none") == "none":
            return None
        code = "HL" if "HL" in variant["equipment"] else "H"
        return self.limits.get(code)

    def start_load(self, variant: dict) -> float | None:
        lim = self.load_limits(variant)
        if not lim:
            return None
        mx, step = lim
        ratio = variant.get("start_load_ratio", 1.0)
        return snap_down(mx * ratio, step, mx)


def snap_down(value: float, step: float, maximum: float) -> float:
    """Round down to the dumbbell step, at least one step, at most the max."""
    if step <= 0:
        return round(min(value, maximum), 2)
    n = max(1, math.floor(value / step + 1e-9))
    return round(min(n * step, maximum), 2)
