import shutil
from datetime import date, timedelta

import pytest

from app.service import Game, GameError
from conftest import ROOT

MON = date(2026, 11, 23)

AWAKENING = {
    "name": "Loïc", "weight": 75, "arm": 32, "chest": 98, "waist": 84, "thigh": 55,
    "dumbbell_max": 10, "dumbbell_step": 1, "rest_day": 6, "quest_hour": "19:00",
    "tests": {"pushups": 18, "plank": 50, "hang": 22, "goblet": 30, "deep_squat": 45,
              "toe_touch": 8, "knee_wall": 9, "hands_back": 12},
}


@pytest.fixture
def game(tmp_path):
    for f in ("config", "skills", "ranks", "titles", "system_messages"):
        shutil.copy(ROOT / "data" / f"{f}.json", tmp_path / f"{f}.json")
    return Game(tmp_path, seed=1)


def awaken(game, day=MON - timedelta(days=1)):
    with game.connect() as con:
        return game.awaken(con, AWAKENING, day)


def do(game, fn, *args):
    with game.connect() as con:
        return getattr(game, fn)(con, *args)


def play(game, qid, rir=2, pain_first=False, day=MON):
    plan = do(game, "quest_plan", qid)["plan"]
    sets = []
    for i, s in enumerate(plan["steps"]):
        if s["kind"] == "timed":
            continue
        ex = plan["exercises"][s["ex"]]
        sets.append({"step": i, "block": s["block"], "fid": ex["fid"], "variant_id": ex["variant_id"],
                     "target": s.get("target"), "load": s.get("load"), "done": s.get("target"), "rir": rir,
                     "pain": pain_first and i == 0})
    with game.connect() as con:
        return game.complete(con, qid, {"sets": sets, "duration_s": 1400}, day)


def test_state_before_awakening(game):
    assert do(game, "state", MON) == {"app_name": "OVERRIDE", "awakened": False}


def test_awakening_sets_up_player(game):
    r = awaken(game)
    p = r["player"]
    assert p["name"] == "Loïc" and p["rank"] == "E" and p["version_major"] == 1 and p["version_minor"] == 0
    assert p["xp"] == 100 and p["level"] == 1
    assert p["weakest_zone"] in ("mob_hams", "mob_shoulders", "mob_hips", "mob_ankles")
    assert r["message"].startswith("[SYSTÈME]")
    with pytest.raises(GameError):
        awaken(game)
    st = do(game, "state", MON - timedelta(days=1))
    assert st["main_quest"]["type"] == "AWAKENING" and st["main_quest"]["status"] == "done"
    assert st["player"]["title"] == "Éveillé"
    assert st["next_trial"]["rank"] == "D"


def test_checkin_generates_first_quest_haut(game):
    awaken(game)
    r = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON)
    assert r["xp"]["gain"] == 5
    assert r["quest"]["subtype"] == "HAUT"
    # reload = same quest, check-in only once
    again = do(game, "do_checkin", {"sleep": "mauvais", "energy": "basse", "back": "ok"}, MON)
    assert again["quest"]["id"] == r["quest"]["id"]
    assert do(game, "quest_plan", r["quest"]["id"])["plan"] == r["quest"]["plan"]


def test_complete_quest_xp_streak_and_rotation(game):
    awaken(game)
    q = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON)["quest"]
    rep = play(game, q["id"])
    assert rep["xp"]["gain"] == 100 and rep["streak"] == 1 and rep["multiplier_next"] == 1.1
    assert play(game, q["id"]) == rep                       # idempotent retry
    st = do(game, "state", MON)
    assert st["main_quest"]["status"] == "done"
    assert st["player"]["xp"] == 100 + 5 + 100
    # next day: BAS, with the multiplier
    q2 = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON + timedelta(days=1))["quest"]
    assert q2["subtype"] == "BAS"
    rep2 = play(game, q2["id"])
    assert rep2["xp"]["multiplier"] == 1.1 and rep2["xp"]["gain"] == 110


def test_rotation_ignores_date_when_a_day_is_skipped(game):
    awaken(game)
    q = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON)["quest"]
    assert q["subtype"] == "HAUT"
    # Monday's quest not done; Wednesday still gets HAUT
    q3 = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON + timedelta(days=2))["quest"]
    assert q3["subtype"] == "HAUT"


def test_painful_back_gives_recovery_quest(game):
    awaken(game)
    q = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "douloureux"}, MON)["quest"]
    assert q["subtype"] == "RECOVERY"
    rep = play(game, q["id"])
    assert rep["xp"]["gain"] == 50


def test_light_quest_xp(game):
    awaken(game)
    q = do(game, "do_checkin", {"sleep": "mauvais", "energy": "basse", "back": "ok"}, MON)["quest"]
    assert q["plan"]["mode"] == "light"
    assert play(game, q["id"])["xp"]["gain"] == 70


def test_rest_day_has_no_main_quest(game):
    awaken(game)
    sunday = MON + timedelta(days=6)
    r = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, sunday)
    assert r["quest"] is None
    assert do(game, "state", sunday)["day_kind"] == "rest"


def test_recal_validates_mobility(game):
    awaken(game)
    for i in range(3):
        d = MON + timedelta(days=i)
        q = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, d)["quest"]
        rep = play(game, q["id"], day=d)
    assert q["subtype"] == "RECAL" and rep["extra"]
    assert do(game, "state", MON + timedelta(days=2))["mobility_quest"]["status"] == "done"


def test_calibration_keeps_adjusted_load(game):
    awaken(game)
    q = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, MON)["quest"]
    plan = q["plan"]
    ex = plan["exercises"]["push_v"]
    sets = [{"step": 0, "block": "main", "fid": "push_v", "variant_id": ex["variant_id"], "target": 10,
             "load": ex["load"] - 1, "done": 10, "rir": 3}]
    with game.connect() as con:
        game.complete(con, q["id"], {"sets": sets}, MON)
    st = do(game, "skill_states")["push_v"]
    assert st["load"] == ex["load"] - 1 and st["target"] == 10


def test_level_up_gives_focus_point(game):
    awaken(game)
    with game.connect() as con:
        p = game.player(con)
        info = game.gain_xp(con, p, 1000, use_multiplier=False)
    assert info["levels_gained"] == 1
    st = do(game, "state", MON)
    assert st["player"]["level"] == 2 and st["player"]["focus_points"] == 1


def test_physio_banner(game):
    awaken(game)
    for i in range(3):
        do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "tendu"}, MON + timedelta(days=i))
    assert do(game, "state", MON + timedelta(days=2))["physio_banner"]


def test_summary_for_homepage(game):
    assert do(game, "summary", MON)["awakened"] is False
    awaken(game)
    s = do(game, "summary", MON)
    assert s == {"app": "OVERRIDE", "level": 1, "rank": "E", "version": "v1.0", "multiplier": "x1.0", "quest_done": "non"}


def test_messages_do_not_repeat(game):
    awaken(game)
    seen = []
    for i in range(12):
        d = MON + timedelta(days=i)
        r = do(game, "do_checkin", {"sleep": "bon", "energy": "normale", "back": "ok"}, d)
        if r["quest"]:
            play(game, r["quest"]["id"], day=d)
    ids = do(game, "recent_message_ids")
    assert len(ids) == 10
