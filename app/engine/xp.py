"""XP, levels and streak multiplier."""
from __future__ import annotations


def level_cost(level: int, base: int = 800, per_level: int = 200) -> int:
    """XP needed to go from `level` to `level + 1`."""
    return base + per_level * level


def add_xp(level: int, xp: int, gain: int, base: int = 800, per_level: int = 200) -> tuple[int, int, int]:
    """Return (new_level, new_xp_in_level, levels_gained)."""
    xp += gain
    gained = 0
    while xp >= level_cost(level, base, per_level):
        xp -= level_cost(level, base, per_level)
        level += 1
        gained += 1
    return level, xp, gained


def multiplier(streak: int, step: float = 0.1, maximum: float = 1.5) -> float:
    return round(min(maximum, 1.0 + step * max(0, streak)), 2)


def apply_multiplier(base_xp: int, mult: float) -> int:
    return int(round(base_xp * mult))
