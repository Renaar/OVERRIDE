"""Back safety: locks on the loaded hinge and availability of variants."""
from __future__ import annotations

from datetime import date, timedelta

from .catalog import Inventory


def loaded_hinge_unlocked(back_history: dict[date, str], awakened: date, today: date,
                          core_ant_level: int, clean_days: int = 14, core_level: int = 3) -> bool:
    """Loaded hinge (RDL) needs `clean_days` with no tense/painful back AND anterior core level >= `core_level`."""
    if core_ant_level < core_level:
        return False
    since = today - timedelta(days=clean_days)
    if awakened > since:                      # not enough history yet
        return False
    return not any(since < d <= today and b in ("tendu", "douloureux") for d, b in back_history.items())


def lock_reason(variant: dict, inventory: Inventory, hinge_unlocked: bool) -> str | None:
    """Why a variant cannot be used right now: 'materiel', 'dos' or None."""
    if not inventory.has_all(variant["equipment"]):
        return "materiel"
    if variant.get("back_lock") and not hinge_unlocked:
        return "dos"
    return None
