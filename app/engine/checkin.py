"""Pre-quest check-in rules (3 taps: sleep, energy, back)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

SLEEP = ("mauvais", "correct", "bon")
ENERGY = ("basse", "normale", "haute")
BACK = ("ok", "tendu", "douloureux")


@dataclass(frozen=True)
class CheckinResult:
    mode: str               # 'normal' | 'light' | 'recovery'
    negatives: int
    back_tense: bool
    no_loaded_hinge: bool
    rir_bonus: int          # added to the RIR target
    set_penalty: int        # sets removed per exercise


def evaluate(sleep: str, energy: str, back: str, light_threshold: int = 2) -> CheckinResult:
    if sleep not in SLEEP or energy not in ENERGY or back not in BACK:
        raise ValueError("invalid check-in value")
    negatives = (sleep == "mauvais") + (energy == "basse") + (back != "ok")
    if back == "douloureux":
        return CheckinResult("recovery", negatives, False, True, 0, 0)
    tense = back == "tendu"
    light = negatives >= light_threshold
    return CheckinResult(
        mode="light" if light else "normal",
        negatives=negatives,
        back_tense=tense,
        no_loaded_hinge=tense,
        rir_bonus=1 if light else 0,
        set_penalty=1 if light else 0,
    )


def back_alerts(history: dict[date, str], today: date, window_days: int = 14) -> int:
    """Number of 'tendu'/'douloureux' check-ins in the last `window_days` days (today included)."""
    start = today - timedelta(days=window_days - 1)
    return sum(1 for d, b in history.items() if start <= d <= today and b in ("tendu", "douloureux"))


def physio_banner(history: dict[date, str], today: date, window_days: int = 14, threshold: int = 3) -> bool:
    return back_alerts(history, today, window_days) >= threshold
