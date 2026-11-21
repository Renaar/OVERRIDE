"""SQLite storage. One file, one connection per request, JSON columns for structured data."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS player (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    title TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    version_major INTEGER NOT NULL DEFAULT 1,
    version_minor INTEGER NOT NULL DEFAULT 0,
    rank TEXT NOT NULL DEFAULT 'E',
    stats TEXT NOT NULL,
    stats_max TEXT NOT NULL,
    streak INTEGER NOT NULL DEFAULT 0,
    saved_streak INTEGER,
    focus_points INTEGER NOT NULL DEFAULT 0,
    awakened_on TEXT NOT NULL,
    patch_start TEXT NOT NULL,
    weakest_zone TEXT,
    mobility_scores TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory (
    code TEXT PRIMARY KEY, owned INTEGER NOT NULL DEFAULT 0,
    max_load REAL, step REAL, acquired_on TEXT
);
CREATE TABLE IF NOT EXISTS skill_state (
    fid TEXT PRIMARY KEY, level INTEGER NOT NULL, load REAL, target INTEGER,
    fail_streak INTEGER NOT NULL DEFAULT 0, pending TEXT
);
CREATE TABLE IF NOT EXISTS checkins (
    date TEXT PRIMARY KEY, sleep TEXT NOT NULL, energy TEXT NOT NULL, back TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL, kind TEXT NOT NULL, subtype TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    plan TEXT, result TEXT, xp INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL, completed_at TEXT
);
CREATE INDEX IF NOT EXISTS quests_date ON quests (date, kind);
CREATE TABLE IF NOT EXISTS set_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
    step INTEGER NOT NULL, block TEXT, fid TEXT, variant_id TEXT,
    target INTEGER, load REAL, done INTEGER, rir INTEGER, pain INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, kind TEXT NOT NULL, value REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, context TEXT NOT NULL,
    test TEXT NOT NULL, value REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, type TEXT NOT NULL,
    data TEXT, message TEXT, message_id TEXT
);
"""

_JSON_COLS = {"stats", "stats_max", "mobility_scores", "pending", "plan", "result", "data", "value"}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def init(path: Path) -> None:
    with closing(path) as con:
        con.executescript(SCHEMA)


@contextmanager
def closing(path: Path):
    con = connect(path)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in _JSON_COLS & d.keys():
        if isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


def rows(rs) -> list[dict]:
    return [row(r) for r in rs]


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)
