"""Patch calendar (4-week cycles) and RIR targets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PatchInfo:
    index: int        # 1-based patch counter since the Awakening
    week: int         # 1..4
    day: int          # 0..27
    deload: bool
    calibration: bool


def patch_info(patch_start: date, today: date, awakened: date, days: int = 28,
               calibration_days: int = 7) -> PatchInfo:
    elapsed = max(0, (today - patch_start).days)
    day = elapsed % days
    week = day // 7 + 1
    return PatchInfo(
        index=elapsed // days + 1,
        week=week,
        day=day,
        deload=week == 4,
        calibration=(today - awakened).days < calibration_days,
    )


def rir_target(info: PatchInfo, by_week: dict[str, int], bonus: int = 0) -> int:
    base = 3 if info.calibration else int(by_week[str(info.week)])
    return min(4, base + bonus)
