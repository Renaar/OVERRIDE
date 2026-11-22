"""Glue between the database and the pure engine. No game rule lives here, only loading and saving."""
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from . import db, settings as S
from .engine import checkin as ck
from .engine import generator, patch, placement, ranks, rotation, safety, xp
from .engine.catalog import Catalog, Inventory
from .engine.messages import LibraryProvider, MessageProvider

EQUIPMENT_START = ("H", "P")
BODY_PARTS = ("arm", "chest", "waist", "thigh")
TESTS = ("pushups", "plank", "hang", "goblet", "deep_squat", "toe_touch", "knee_wall", "hands_back")
# awakening test -> metric used by ranks/titles, and whether lower is better
TEST_METRICS = {"pushups": ("pushups", False), "plank": ("plank_s", False), "hang": ("hang_s", False),
                "deep_squat": ("deep_squat_s", False), "toe_touch": ("toe_touch_cm", True),
                "goblet": ("goblet_reps", False), "pullups": ("pullups", False),
                "side_plank": ("side_plank_s", False), "cossack": ("cossack_reps", False),
                "pistol": ("pistol_reps", False), "palms_floor": ("palms_floor", False),
                "farmer_20kg": ("farmer_20kg_s", False), "weighted_pullups_10kg": ("weighted_pullups_10kg", False)}


class GameError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# sha256 of program files shipped before the manifest existed (phase 1), so they can be updated safely.
LEGACY_DEFAULTS = {
    "config": {"a7196d6f4442dc4588727839bd6b8423e58c99888f4eda9a55e7f42a342578c3"},
    "skills": {"c4254d459bfa5baeef95219557acabf39c61340004013999235aae1a5bf01aa5"},
    "ranks": {"d76ade5cd11361aeec5298d82b6687cac83aded24fe258888675c5a00ae8e2d8"},
    "titles": {"83127b8f47caf50b98366945a9d6001741066bb555c1308b8648067cce9824fc"},
    "system_messages": {"c1b5d270bafea30abb0204082284158fdc074c2388c1a8c903ad73b085dd808e"},
}
MANIFEST = ".defaults.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_data_files(data_dir: Path = S.DATA_DIR, defaults_dir: Path = S.DEFAULTS_DIR) -> list[str]:
    """Install or update the program JSON files in the data volume.

    A file is replaced by the new default only if the player never edited it (its hash matches the
    default installed last time). An edited file is kept; the new default is written next to it as
    `<name>.nouveau.json`. Returns a log of what happened.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(data_dir, os.W_OK):
        raise RuntimeError(f"{data_dir} n'est pas accessible en écriture. Sur le serveur : sudo chown -R 1000:1000 data")
    if data_dir.resolve() == defaults_dir.resolve():
        return []                                   # development: the repo's data/ is the source
    man_path = data_dir / MANIFEST
    try:
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    log = []
    for name in S.DATA_FILES:
        src, dst = defaults_dir / f"{name}.json", data_dir / f"{name}.json"
        if not src.exists():
            continue
        new = _sha(src)
        if not dst.exists():
            shutil.copyfile(src, dst)
            log.append(f"{name}: installé")
        else:
            cur = _sha(dst)
            installed = manifest.get(name) or (cur if cur in LEGACY_DEFAULTS.get(name, ()) else None)
            if cur == new:
                pass
            elif cur == installed:
                shutil.copyfile(src, dst)
                log.append(f"{name}: mis à jour")
            else:
                shutil.copyfile(src, data_dir / f"{name}.nouveau.json")
                log.append(f"{name}: modifié par le joueur, conservé (nouvelle version : {name}.nouveau.json)")
                continue
        manifest[name] = new
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for line in log:
        print(f"[data] {line}", flush=True)
    return log


def now() -> datetime:
    return datetime.now(S.TZ)


def today() -> date:
    return now().date()


class Game:
    def __init__(self, data_dir: Path = S.DATA_DIR, db_path: Path | None = None,
                 provider: MessageProvider | None = None, seed: int | None = None):
        self.data_dir = data_dir
        self.db_path = db_path or data_dir / "override.db"
        load = lambda n: json.loads((data_dir / f"{n}.json").read_text(encoding="utf-8"))
        self.config = load("config")
        self.skills_data = load("skills")
        self.ranks_data = load("ranks")
        self.titles_data = load("titles")
        self.catalog = Catalog(self.skills_data)
        self.provider = provider or LibraryProvider(load("system_messages"), random.Random(seed))
        db.init(self.db_path)

    def connect(self):
        return db.closing(self.db_path)

    # ------------------------------------------------------------ reads

    def player(self, con) -> dict | None:
        return db.row(con.execute("SELECT * FROM player WHERE id = 1").fetchone())

    def require_player(self, con) -> dict:
        p = self.player(con)
        if not p:
            raise GameError("Éveil requis.", 409)
        return p

    def settings(self, con) -> dict:
        sched, q = self.config["schedule"], self.config["quest"]
        out = {"rest_day": sched["rest_day"], "dungeon_day": sched["dungeon_day"],
               "quest_hour": sched["quest_hour"], "rest_seconds": q["rest_seconds"],
               "superset_rest_seconds": q["superset_rest_seconds"], "sound": True, "reduced_motion": False}
        for r in con.execute("SELECT key, value FROM settings"):
            out[r["key"]] = json.loads(r["value"])
        return out

    def set_settings(self, con, values: dict) -> dict:
        allowed = self.settings(con).keys()
        for k, v in values.items():
            if k in allowed:
                con.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, db.dumps(v)))
        return self.settings(con)

    def inventory(self, con) -> Inventory:
        owned, limits = set(), {}
        for r in con.execute("SELECT * FROM inventory"):
            if r["owned"]:
                owned.add(r["code"])
                if r["max_load"]:
                    limits[r["code"]] = (float(r["max_load"]), float(r["step"] or 1))
        return Inventory(owned, limits)

    def skill_states(self, con) -> dict[str, dict]:
        return {r["fid"]: db.row(r) for r in con.execute("SELECT * FROM skill_state")}

    def back_history(self, con) -> dict[date, str]:
        return {date.fromisoformat(r["date"]): r["back"] for r in con.execute("SELECT date, back FROM checkins")}

    def checkin_of(self, con, day: date) -> dict | None:
        return db.row(con.execute("SELECT * FROM checkins WHERE date = ?", (day.isoformat(),)).fetchone())

    def quest_of(self, con, day: date, kind: str) -> dict | None:
        return db.row(con.execute("SELECT * FROM quests WHERE date = ? AND kind = ? ORDER BY id DESC LIMIT 1",
                                  (day.isoformat(), kind)).fetchone())

    def quest(self, con, qid: int) -> dict:
        q = db.row(con.execute("SELECT * FROM quests WHERE id = ?", (qid,)).fetchone())
        if not q:
            raise GameError("Quête introuvable.", 404)
        return q

    def last_done_type(self, con) -> str | None:
        rot = self.config["rotation"]
        r = con.execute(f"SELECT subtype FROM quests WHERE kind = 'main' AND status = 'done' AND subtype IN "
                        f"({','.join('?' * len(rot))}) ORDER BY date DESC, id DESC LIMIT 1", rot).fetchone()
        return r["subtype"] if r else None

    def last_variable_format(self, con) -> str | None:
        for r in con.execute("SELECT plan FROM quests WHERE kind = 'main' AND plan IS NOT NULL "
                             "ORDER BY date DESC, id DESC LIMIT 5"):
            fmt = json.loads(r["plan"]).get("variable_format")
            if fmt:
                return fmt
        return None

    def recent_message_ids(self, con) -> list[str]:
        rs = con.execute("SELECT message_id FROM events WHERE message_id IS NOT NULL ORDER BY id DESC LIMIT 10")
        return [r["message_id"] for r in rs][::-1]

    def metrics(self, con, p: dict) -> dict:
        """Best recorded value of each test, plus body gains since the Awakening."""
        m: dict = {}
        for test, (metric, lower) in TEST_METRICS.items():
            agg = "MIN" if lower else "MAX"
            r = con.execute(f"SELECT {agg}(value) AS v FROM tests WHERE test = ?", (test,)).fetchone()
            if r["v"] is not None:
                m[metric] = r["v"]
        for part in ("arm", "waist", "chest", "thigh", "weight"):
            first = con.execute("SELECT value FROM measurements WHERE kind = ? ORDER BY date, id LIMIT 1", (part,)).fetchone()
            last = con.execute("SELECT value FROM measurements WHERE kind = ? ORDER BY date DESC, id DESC LIMIT 1", (part,)).fetchone()
            if first and last:
                key = "weight_gain_kg" if part == "weight" else f"{part}_gain_cm"
                m[key] = round(last["value"] - first["value"], 2)
        return m

    # ------------------------------------------------------------ events & messages

    def message(self, con, event: str, rank: str, ctx: dict):
        return self.provider.render(event, rank, ctx, self.recent_message_ids(con))

    def log(self, con, type_: str, data: dict | None = None, event: str | None = None,
            rank: str = "E", ctx: dict | None = None) -> str | None:
        msg = self.message(con, event, rank, ctx or {}) if event else None
        con.execute("INSERT INTO events (ts, type, data, message, message_id) VALUES (?, ?, ?, ?, ?)",
                    (now().isoformat(timespec="seconds"), type_, db.dumps(data or {}),
                     msg.text if msg else None, msg.id if msg else None))
        return msg.text if msg else None

    def gain_xp(self, con, p: dict, base: int, use_multiplier: bool = True) -> dict:
        """Add XP to the player. Returns the gain details (multiplier applied before any streak change)."""
        mult = xp.multiplier(p["streak"], **self._streak_cfg()) if use_multiplier else 1.0
        gain = xp.apply_multiplier(base, mult)
        lv_cfg = self.config["level"]
        level, cur, gained = xp.add_xp(p["level"], p["xp"], gain, lv_cfg["base_cost"], lv_cfg["cost_per_level"])
        con.execute("UPDATE player SET level = ?, xp = ?, focus_points = focus_points + ? WHERE id = 1",
                    (level, cur, gained))
        before = p["level"]
        p.update(level=level, xp=cur, focus_points=p["focus_points"] + gained)
        return {"base": base, "multiplier": mult, "gain": gain, "level_before": before,
                "level_after": level, "levels_gained": gained}

    def _streak_cfg(self) -> dict:
        s = self.config["streak"]
        return {"step": s["step"], "maximum": s["max_multiplier"]}

    def _level_up_messages(self, con, p: dict, info: dict) -> list[str]:
        out = []
        for lvl in range(info["level_before"] + 1, info["level_after"] + 1):
            out.append(self.log(con, "level_up", {"level": lvl}, "level_up", p["rank"],
                                {"level": lvl, "name": p["name"]}))
        return out

    # ------------------------------------------------------------ awakening

    def awaken(self, con, data: dict, day: date) -> dict:
        if self.player(con):
            raise GameError("L'Éveil a déjà eu lieu.", 409)
        name = (data.get("name") or "").strip()[:40]
        if not name:
            raise GameError("Nom requis.")
        tests = {k: float(data["tests"][k]) for k in TESTS if data.get("tests", {}).get(k) is not None}
        if "goblet" in tests:
            tests["goblet"] = min(tests["goblet"], 30)
        if "deep_squat" in tests:
            tests["deep_squat"] = min(tests["deep_squat"], 120)
        dmax, dstep = float(data.get("dumbbell_max") or 10), float(data.get("dumbbell_step") or 1)
        owned = set(data.get("owned") or EQUIPMENT_START) | {"H"}

        for code in self.catalog.equipment:
            lim = (dmax, dstep) if code == "H" else (None, None)
            con.execute("INSERT INTO inventory (code, owned, max_load, step, acquired_on) VALUES (?, ?, ?, ?, ?)",
                        (code, int(code in owned), lim[0], lim[1], day.isoformat() if code in owned else None))
        inv = self.inventory(con)
        states = placement.place_skills(self.catalog, inv, tests, self.config["placement"])
        for fid, st in states.items():
            con.execute("INSERT INTO skill_state (fid, level, load, target, fail_streak) VALUES (?, ?, ?, ?, 0)",
                        (fid, st["level"], st["load"], st["target"]))
        scores = placement.mobility_scores(tests, self.config["mobility_tests"])
        stats = placement.starting_stats(self.catalog, states)
        con.execute("INSERT INTO player (id, name, title, stats, stats_max, awakened_on, patch_start, weakest_zone, "
                    "mobility_scores) VALUES (1, ?, 'awakened', ?, ?, ?, ?, ?, ?)",
                    (name, db.dumps(stats), db.dumps(stats), day.isoformat(), day.isoformat(),
                     placement.weakest_zone(scores), db.dumps(scores)))
        for k in ("weight", *BODY_PARTS):
            if data.get(k) not in (None, ""):
                con.execute("INSERT INTO measurements (date, kind, value) VALUES (?, ?, ?)",
                            (day.isoformat(), k, float(data[k])))
        for k, v in tests.items():
            con.execute("INSERT INTO tests (date, context, test, value) VALUES (?, 'awakening', ?, ?)",
                        (day.isoformat(), k, v))
        self.set_settings(con, {k: data[k] for k in ("rest_day", "quest_hour") if data.get(k) is not None})

        # The Awakening is the first quest of the first evening.
        con.execute("INSERT INTO quests (date, kind, subtype, status, plan, result, xp, created_at, completed_at) "
                    "VALUES (?, 'main', 'AWAKENING', 'done', NULL, ?, ?, ?, ?)",
                    (day.isoformat(), db.dumps({"tests": tests}), self.config["xp"]["awakening"],
                     now().isoformat(timespec="seconds"), now().isoformat(timespec="seconds")))
        p = self.player(con)
        gain = self.gain_xp(con, p, self.config["xp"]["awakening"], use_multiplier=False)
        msg = self.log(con, "awakening", {"tests": tests, "stats": stats}, "awakening_done", "E", {"name": name})
        self.log(con, "title", {"title": "awakened"})
        return {"player": self.player(con), "message": msg, "xp": gain,
                "placement": {fid: {"level": s["level"], "name": self.catalog.variant(fid, s["level"])["name"]}
                              for fid, s in states.items()}}

    # ------------------------------------------------------------ day & check-in

    def day_kind(self, con, day: date) -> str:
        st = self.settings(con)
        kind = rotation.day_kind(day, int(st["rest_day"]), int(st["dungeon_day"]))
        return "main" if kind == "dungeon" else kind     # the Donjon arrives in phase 3

    def patch_info(self, p: dict, day: date) -> patch.PatchInfo:
        return patch.patch_info(date.fromisoformat(p["patch_start"]), day, date.fromisoformat(p["awakened_on"]),
                                self.config["patch"]["days"], self.config["rir"]["calibration_days"])

    def hinge_unlocked(self, con, p: dict, day: date) -> bool:
        core = self.skill_states(con).get("core_ant", {"level": 1})["level"]
        sc = self.config["safety"]
        return safety.loaded_hinge_unlocked(self.back_history(con), date.fromisoformat(p["awakened_on"]), day,
                                            core, sc["loaded_hinge_clean_days"], sc["loaded_hinge_core_level"])

    def do_checkin(self, con, data: dict, day: date) -> dict:
        p = self.require_player(con)
        existing = self.checkin_of(con, day)
        if existing:
            return {"checkin": existing, "quest": self.quest_of(con, day, "main"), "message": None, "xp": None}
        res = ck.evaluate(data.get("sleep"), data.get("energy"), data.get("back"),
                          self.config["checkin"]["light_threshold"])
        con.execute("INSERT INTO checkins (date, sleep, energy, back, created_at) VALUES (?, ?, ?, ?, ?)",
                    (day.isoformat(), data["sleep"], data["energy"], data["back"], now().isoformat(timespec="seconds")))
        gain = self.gain_xp(con, p, self.config["xp"]["checkin"])
        event = {"recovery": "checkin_recovery", "light": "checkin_light"}.get(res.mode)
        if not event:
            event = "checkin_tense" if res.back_tense else "checkin_good"
        msg = self.log(con, "checkin", {"sleep": data["sleep"], "energy": data["energy"], "back": data["back"],
                                        "mode": res.mode, "xp": gain["gain"]}, event, p["rank"], {"name": p["name"]})
        self._level_up_messages(con, p, gain)
        quest = self.ensure_main_quest(con, day)
        return {"checkin": self.checkin_of(con, day), "quest": quest, "message": msg, "xp": gain}

    def ensure_main_quest(self, con, day: date) -> dict | None:
        """Return today's main quest, generating and saving it once (a reload gives the same quest)."""
        q = self.quest_of(con, day, "main")
        if q:
            return q
        if self.day_kind(con, day) == "rest":
            return None
        c = self.checkin_of(con, day)
        if not c:
            return None
        p = self.require_player(con)
        res = ck.evaluate(c["sleep"], c["energy"], c["back"], self.config["checkin"]["light_threshold"])
        if res.mode == "recovery":
            plan = generator.generate_recovery(self.catalog)
        else:
            info = self.patch_info(p, day)
            st = self.settings(con)
            ctx = generator.GenContext(
                day=day, quest_type=rotation.next_main_type(self.last_done_type(con), self.config["rotation"]),
                checkin=res, patch=info, rir=patch.rir_target(info, self.config["rir"]["by_week"], res.rir_bonus),
                skills=self.skill_states(con), inventory=self.inventory(con),
                hinge_unlocked=self.hinge_unlocked(con, p, day), last_format=self.last_variable_format(con),
                rest_seconds=int(st["rest_seconds"]), superset_rest_seconds=int(st["superset_rest_seconds"]),
                weakest_zone=p["weakest_zone"] or "mob_hips")
            plan = generator.generate_main(self.catalog, ctx, self.config)
        con.execute("INSERT INTO quests (date, kind, subtype, status, plan, created_at) VALUES (?, 'main', ?, 'pending', ?, ?)",
                    (day.isoformat(), plan["type"], db.dumps(plan), now().isoformat(timespec="seconds")))
        ctx_msg = {"name": p["name"], "quest_label": plan["label"], "minutes": plan["estimate_min"],
                   "rir": plan.get("rir_label"), "streak": p["streak"],
                   "multiplier": xp.multiplier(p["streak"], **self._streak_cfg()),
                   "calibration": int(bool(plan.get("calibration")))}
        self.log(con, "briefing", {"type": plan["type"], "minutes": plan["estimate_min"]}, "briefing", p["rank"], ctx_msg)
        return self.quest_of(con, day, "main")

    def ensure_mobility_quest(self, con, day: date) -> dict:
        q = self.quest_of(con, day, "mobility")
        if q:
            return q
        p = self.require_player(con)
        mq = self.config["mobility_quest"]
        plan = generator.generate_mobility(self.catalog, day, self.skill_states(con), self.inventory(con),
                                           p["weakest_zone"] or "mob_hips", mq["seconds"], mq["drill_seconds"])
        con.execute("INSERT INTO quests (date, kind, subtype, status, plan, created_at) VALUES (?, 'mobility', ?, 'pending', ?, ?)",
                    (day.isoformat(), plan["zone"], db.dumps(plan), now().isoformat(timespec="seconds")))
        return self.quest_of(con, day, "mobility")

    # ------------------------------------------------------------ completion

    def complete(self, con, qid: int, data: dict, day: date) -> dict:
        q = self.quest(con, qid)
        if q["status"] == "done":                 # retries after a network cut get the same report
            return q["result"]["report"]
        p = self.require_player(con)
        plan = q["plan"] or {}
        sets = data.get("sets") or []
        ts = now().isoformat(timespec="seconds")
        for s in sets:
            con.execute("INSERT INTO set_logs (quest_id, step, block, fid, variant_id, target, load, done, rir, pain, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (qid, s.get("step"), s.get("block"), s.get("fid"), s.get("variant_id"), s.get("target"),
                         s.get("load"), s.get("done"), s.get("rir"), int(bool(s.get("pain"))), ts))
        if q["kind"] == "main":
            self._keep_calibration(con, plan, sets)

        xpc = self.config["xp"]
        if q["kind"] == "mobility":
            base, event = xpc["mobility"], "mobility_report"
        elif plan.get("mode") == "recovery":
            base, event = xpc["main_recovery"], "recovery_report"
        elif plan.get("mode") == "light":
            base, event = xpc["main_light"], "quest_report"
        else:
            base, event = xpc["main"], "quest_report"
        gain = self.gain_xp(con, p, base)
        extra = []
        if q["kind"] == "main":
            con.execute("UPDATE player SET streak = streak + 1 WHERE id = 1")
            p["streak"] += 1
            if plan.get("type") == "RECAL":
                extra.append(self._auto_validate_mobility(con, day, p))
        pain = sum(1 for s in sets if s.get("pain"))
        work_sets = sum(1 for s in sets if s.get("block") in ("main", "variable"))
        minutes = round((data.get("duration_s") or plan.get("estimate_s") or 0) / 60)
        ctx = {"name": p["name"], "xp": gain["gain"], "sets": work_sets, "minutes": minutes, "streak": p["streak"],
               "light": int(plan.get("mode") == "light"), "pain": pain, "zone": plan.get("zone", "")}
        msg = self.log(con, "quest_done", {"quest_id": qid, "type": plan.get("type"), "xp": gain["gain"],
                                           "sets": work_sets, "pain": pain}, event, p["rank"], ctx)
        level_msgs = self._level_up_messages(con, p, gain)
        lv = self.config["level"]
        report = {"quest_id": qid, "type": plan.get("type"), "label": plan.get("label"), "xp": gain,
                  "level": p["level"], "xp_in_level": p["xp"],
                  "xp_next": xp.level_cost(p["level"], lv["base_cost"], lv["cost_per_level"]),
                  "streak": p["streak"], "multiplier_next": xp.multiplier(p["streak"], **self._streak_cfg()),
                  "sets": work_sets, "pain": pain, "minutes": minutes, "message": msg,
                  "level_messages": [m for m in level_msgs if m], "extra": [e for e in extra if e],
                  "records": [], "skill_ups": [], "stats": {}}
        con.execute("UPDATE quests SET status = 'done', result = ?, xp = ?, completed_at = ? WHERE id = ?",
                    (db.dumps({"report": report, "results": data.get("results") or {}}), gain["gain"], ts, qid))
        return report

    def _auto_validate_mobility(self, con, day: date, p: dict) -> dict | None:
        mq = self.ensure_mobility_quest(con, day)
        if mq["status"] == "done":
            return None
        gain = self.gain_xp(con, p, self.config["xp"]["mobility"])
        report = {"auto": True, "xp": gain}
        con.execute("UPDATE quests SET status = 'done', result = ?, xp = ?, completed_at = ? WHERE id = ?",
                    (db.dumps({"report": report}), gain["gain"], now().isoformat(timespec="seconds"), mq["id"]))
        self.log(con, "quest_done", {"quest_id": mq["id"], "type": "MOBILITY", "auto": True, "xp": gain["gain"]})
        return {"label": "Mobilité validée d'office (Recalibrage)", "xp": gain["gain"]}

    def _keep_calibration(self, con, plan: dict, sets: list[dict]) -> None:
        """Keep the last load and target the player actually used on each main exercise."""
        last: dict[str, dict] = {}
        for s in sets:
            if s.get("block") == "main" and s.get("fid") and not s.get("pain"):
                last[s["fid"]] = s
        for fid, s in last.items():
            ex = plan.get("exercises", {}).get(fid)
            if not ex or s.get("variant_id") != ex["variant_id"]:
                continue
            load = s.get("load") if ex["load"] is not None else None
            con.execute("UPDATE skill_state SET load = COALESCE(?, load), target = COALESCE(?, target) "
                        "WHERE fid = ? AND level = ?", (load, s.get("target"), fid, ex["level"]))

    # ------------------------------------------------------------ status screen

    def state(self, con, day: date) -> dict:
        p = self.player(con)
        if not p:
            return {"app_name": S.APP_NAME, "awakened": False}
        lv = self.config["level"]
        info = self.patch_info(p, day)
        kind = self.day_kind(con, day)
        c = self.checkin_of(con, day)
        main = self.ensure_main_quest(con, day) if c else self.quest_of(con, day, "main")
        mob = self.ensure_mobility_quest(con, day)
        hist = self.back_history(con)
        rank_defs = {r["id"]: r for r in self.ranks_data["ranks"]}
        nxt = ranks.next_rank(p["rank"])
        metrics = self.metrics(con, p)
        trial = None
        if nxt:
            res = ranks.evaluate_trials(rank_defs[nxt], metrics)
            trial = {"rank": nxt, "color": rank_defs[nxt]["color"], "required": self.ranks_data["required_trials"],
                     "passed": ranks.trials_passed(res), "trials": res}
        message = self._status_message(con, p, day, kind, main)
        return {
            "app_name": S.APP_NAME, "awakened": True, "today": day.isoformat(), "day_kind": kind,
            "player": {
                "name": p["name"], "title": self._title_name(p["title"]),
                "version": f"v{p['version_major']}.{p['version_minor']}", "level": p["level"], "xp": p["xp"],
                "xp_next": xp.level_cost(p["level"], lv["base_cost"], lv["cost_per_level"]),
                "rank": p["rank"], "rank_color": rank_defs[p["rank"]]["color"], "stats": p["stats_max"],
                "streak": p["streak"], "multiplier": xp.multiplier(p["streak"], **self._streak_cfg()),
                "focus_points": p["focus_points"],
            },
            "patch": {"label": f"Patch {p['version_major']}.{p['version_minor'] + 1}", "week": info.week,
                      "day": info.day + 1, "deload": info.deload, "calibration": info.calibration},
            "checkin": c,
            "main_quest": self._quest_summary(main),
            "mobility_quest": self._quest_summary(mob),
            "physio_banner": ck.physio_banner(hist, day, self.config["checkin"]["physio_window_days"],
                                              self.config["checkin"]["physio_threshold"]),
            "next_trial": trial,
            "message": message,
            "settings": self.settings(con),
        }

    def _title_name(self, tid: str | None) -> str:
        for t in self.titles_data["titles"]:
            if t["id"] == tid:
                return t["name"]
        return ""

    @staticmethod
    def _quest_summary(q: dict | None) -> dict | None:
        if not q:
            return None
        plan = q["plan"] or {}
        return {"id": q["id"], "status": q["status"], "type": q["subtype"], "label": plan.get("label"),
                "estimate_min": plan.get("estimate_min"), "mode": plan.get("mode"), "xp": q["xp"],
                "variable": plan.get("variable_name"), "rir": plan.get("rir_label"), "notes": plan.get("notes", [])}

    def _status_message(self, con, p: dict, day: date, kind: str, main: dict | None) -> str:
        r = con.execute("SELECT message FROM events WHERE message IS NOT NULL AND ts >= ? ORDER BY id DESC LIMIT 1",
                        (day.isoformat(),)).fetchone()
        if r:
            return r["message"]
        event = "status_rest" if kind == "rest" else "status_done" if main and main["status"] == "done" else "status_idle"
        msgs = self.provider.candidates(event, p["rank"], {}) if hasattr(self.provider, "candidates") else []
        if not msgs:
            return ""
        return random.Random(day.isoformat()).choice(msgs)["text"]

    def quest_plan(self, con, qid: int) -> dict:
        q = self.quest(con, qid)
        return {"id": q["id"], "status": q["status"], "kind": q["kind"], "date": q["date"], "plan": q["plan"],
                "settings": self.settings(con)}

    # ------------------------------------------------------------ simple lists

    def skills_view(self, con, day: date) -> list[dict]:
        p = self.require_player(con)
        states, inv = self.skill_states(con), self.inventory(con)
        unlocked = self.hinge_unlocked(con, p, day)
        out = []
        for fid, fam in self.catalog.families.items():
            st = states.get(fid, {"level": 1, "load": None, "target": None})
            variants = []
            for v in fam["variants"]:
                reason = safety.lock_reason(v, inv, unlocked)
                if reason is None and v["level"] > st["level"] and not fam.get("zone"):
                    reason = "niveau"
                variants.append({"level": v["level"], "name": v["name"], "equipment": v["equipment"],
                                 "type": v["type"], "range": v["range"], "lock": reason,
                                 "current": v["level"] == st["level"], "cues": v["cues"],
                                 "back_note": v.get("back_note", ""), "unilateral": bool(v.get("unilateral")),
                                 **generator.howto(v)})
            out.append({"id": fid, "name": fam["name"], "category": fam["category"], "level": st["level"],
                        "max_level": len(fam["variants"]), "load": st["load"], "target": st["target"],
                        "zone": bool(fam.get("zone")), "variants": variants})
        return out

    def inventory_view(self, con) -> list[dict]:
        names = self.catalog.equipment
        return [{"code": r["code"], "name": names.get(r["code"], r["code"]), "owned": bool(r["owned"]),
                 "max_load": r["max_load"], "step": r["step"], "acquired_on": r["acquired_on"]}
                for r in con.execute("SELECT * FROM inventory")]

    def journal(self, con, limit: int = 200) -> list[dict]:
        return db.rows(con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)))

    def summary(self, con, day: date) -> dict:
        p = self.player(con)
        if not p:
            return {"app": S.APP_NAME, "awakened": False}
        main = self.quest_of(con, day, "main")
        kind = self.day_kind(con, day)
        return {"app": S.APP_NAME, "level": p["level"], "rank": p["rank"],
                "version": f"v{p['version_major']}.{p['version_minor']}",
                "multiplier": f"x{xp.multiplier(p['streak'], **self._streak_cfg()):.1f}",
                "quest_done": "repos" if kind == "rest" else ("oui" if main and main["status"] == "done" else "non")}
