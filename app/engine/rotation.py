"""Which main quest comes next. Rotation follows the last quest done, never the date."""
from __future__ import annotations

from datetime import date

ROTATION = ["HAUT", "BAS", "RECAL"]


def next_main_type(last_done: str | None, rotation: list[str] = ROTATION) -> str:
    if last_done not in rotation:
        return rotation[0]
    return rotation[(rotation.index(last_done) + 1) % len(rotation)]


def day_kind(day: date, rest_day: int, dungeon_day: int | None) -> str:
    """'rest', 'dungeon' or 'main'. Days use Python's weekday(): 0 = Monday."""
    if day.weekday() == rest_day:
        return "rest"
    if dungeon_day is not None and day.weekday() == dungeon_day:
        return "dungeon"
    return "main"
