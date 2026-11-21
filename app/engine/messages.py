"""System message engine.

A provider turns (event, rank, context) into a message. V1 ships `LibraryProvider`, backed by
data/system_messages.json. A future AI provider only needs the same `render()` signature.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

RANKS = "EDCBAS"
NO_REPEAT = 10


@dataclass(frozen=True)
class Message:
    id: str
    text: str


class MessageProvider(Protocol):
    def render(self, event: str, rank: str, ctx: dict, recent_ids: list[str]) -> Message | None: ...


class _SafeDict(dict):
    def __missing__(self, key):  # unknown variables stay visible instead of crashing
        return "{" + key + "}"


def _fmt(value):
    return f"{value:.1f}" if isinstance(value, float) else value


def rank_in(rank: str, bounds: list[str]) -> bool:
    lo, hi = bounds
    return RANKS.index(lo) <= RANKS.index(rank) <= RANKS.index(hi)


def conditions_met(conditions: dict, ctx: dict) -> bool:
    for var, rule in conditions.items():
        if var not in ctx:
            return False
        val = ctx[var]
        if "min" in rule and not val >= rule["min"]:
            return False
        if "max" in rule and not val <= rule["max"]:
            return False
        if "eq" in rule and val != rule["eq"]:
            return False
    return True


class LibraryProvider:
    def __init__(self, library: dict, rng: random.Random | None = None):
        self.messages = library["messages"]
        self.rng = rng or random.Random()

    def candidates(self, event: str, rank: str, ctx: dict) -> list[dict]:
        return [m for m in self.messages
                if m["event"] == event and rank_in(rank, m["ranks"]) and conditions_met(m.get("conditions", {}), ctx)]

    def render(self, event: str, rank: str, ctx: dict, recent_ids: list[str]) -> Message | None:
        cands = self.candidates(event, rank, ctx)
        if not cands:
            return None
        recent = set(recent_ids[-NO_REPEAT:])
        fresh = [m for m in cands if m["id"] not in recent] or cands
        # messages with conditions are more specific: prefer them
        specific = [m for m in fresh if m.get("conditions")]
        m = self.rng.choice(specific or fresh)
        text = m["text"].format_map(_SafeDict({k: _fmt(v) for k, v in ctx.items()}))
        return Message(m["id"], text)
