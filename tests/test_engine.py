import random
from datetime import date, timedelta

import pytest

from app.engine import checkin, generator, messages, patch, placement, rotation, safety, xp
from app.engine.catalog import Inventory, snap_down

D0 = date(2026, 11, 23)  # a Monday


# ---------------------------------------------------------------- rotation

def test_rotation_follows_last_done_quest():
    assert rotation.next_main_type(None) == "HAUT"
    assert rotation.next_main_type("HAUT") == "BAS"
    assert rotation.next_main_type("BAS") == "RECAL"
    assert rotation.next_main_type("RECAL") == "HAUT"
    assert rotation.next_main_type("RECOVERY") == "HAUT"   # not part of the cycle


def test_day_kind():
    assert rotation.day_kind(date(2026, 11, 29), 6, 5) == "rest"      # Sunday
    assert rotation.day_kind(date(2026, 11, 28), 6, 5) == "dungeon"   # Saturday
    assert rotation.day_kind(D0, 6, 5) == "main"
    assert rotation.day_kind(D0, 0, None) == "rest"


# ---------------------------------------------------------------- check-in

def test_checkin_normal():
    r = checkin.evaluate("bon", "normale", "ok")
    assert r.mode == "normal" and r.negatives == 0 and not r.no_loaded_hinge


def test_checkin_two_negatives_lightens():
    r = checkin.evaluate("mauvais", "basse", "ok")
    assert r.mode == "light" and r.set_penalty == 1 and r.rir_bonus == 1


def test_checkin_one_negative_is_normal():
    assert checkin.evaluate("mauvais", "normale", "ok").mode == "normal"


def test_checkin_tense_back_blocks_hinge_and_counts_as_negative():
    r = checkin.evaluate("mauvais", "normale", "tendu")
    assert r.no_loaded_hinge and r.mode == "light"
    assert checkin.evaluate("bon", "haute", "tendu").mode == "normal"


def test_checkin_painful_back_means_recovery():
    assert checkin.evaluate("bon", "haute", "douloureux").mode == "recovery"


def test_checkin_rejects_bad_values():
    with pytest.raises(ValueError):
        checkin.evaluate("super", "normale", "ok")


def test_physio_banner_three_alerts_in_14_days():
    h = {D0: "tendu", D0 - timedelta(days=5): "douloureux", D0 - timedelta(days=13): "tendu"}
    assert checkin.physio_banner(h, D0)
    h[D0 - timedelta(days=13)] = "ok"
    h[D0 - timedelta(days=14)] = "tendu"   # outside the window
    assert not checkin.physio_banner(h, D0)


# ---------------------------------------------------------------- back safety

def test_loaded_hinge_needs_core_level_and_clean_back():
    aw = D0 - timedelta(days=30)
    assert safety.loaded_hinge_unlocked({}, aw, D0, core_ant_level=3)
    assert not safety.loaded_hinge_unlocked({}, aw, D0, core_ant_level=2)
    assert not safety.loaded_hinge_unlocked({D0 - timedelta(days=3): "tendu"}, aw, D0, 3)
    assert safety.loaded_hinge_unlocked({D0 - timedelta(days=20): "tendu"}, aw, D0, 3)


def test_loaded_hinge_needs_two_weeks_of_history():
    assert not safety.loaded_hinge_unlocked({}, D0 - timedelta(days=5), D0, 4)


def test_lock_reason(catalog, inventory):
    rdl = catalog.variant("hinge", 4)
    assert safety.lock_reason(rdl, inventory, False) == "dos"
    assert safety.lock_reason(rdl, inventory, True) is None
    assert safety.lock_reason(catalog.variant("pull_v", 3), inventory, True) == "materiel"


# ---------------------------------------------------------------- patch & RIR

def test_rir_by_week_and_calibration(config):
    aw = D0 - timedelta(days=100)
    by = config["rir"]["by_week"]
    for week, rir in [(1, 3), (2, 2), (3, 1)]:
        info = patch.patch_info(D0, D0 + timedelta(days=7 * (week - 1)), aw)
        assert info.week == week and patch.rir_target(info, by) == rir
    s4 = patch.patch_info(D0, D0 + timedelta(days=22), aw)
    assert s4.deload and s4.week == 4
    cal = patch.patch_info(D0, D0 + timedelta(days=8), D0 + timedelta(days=5))
    assert cal.calibration and patch.rir_target(cal, by) == 3
    assert patch.rir_target(patch.patch_info(D0, D0 + timedelta(days=15), aw), by, bonus=1) == 2
    assert patch.patch_info(D0, D0 + timedelta(days=29), aw).index == 2


# ---------------------------------------------------------------- XP

def test_level_cost_formula():
    assert xp.level_cost(1) == 1000
    assert xp.level_cost(5) == 1800


def test_add_xp_multiple_levels():
    assert xp.add_xp(1, 900, 150) == (2, 50, 1)
    assert xp.add_xp(1, 0, 1000 + 1200 + 10) == (3, 10, 2)
    assert xp.add_xp(3, 10, 5) == (3, 15, 0)


def test_multiplier_caps_at_1_5():
    assert xp.multiplier(0) == 1.0
    assert xp.multiplier(3) == 1.3
    assert xp.multiplier(12) == 1.5
    assert xp.apply_multiplier(100, 1.3) == 130


# ---------------------------------------------------------------- placement

def test_placement_from_tests(catalog, inventory, config):
    tests = {"pushups": 22, "plank": 70, "hang": 20, "goblet": 30, "deep_squat": 40}
    states = placement.place_skills(catalog, inventory, tests, config["placement"])
    assert states["push_h"]["level"] == 3
    assert states["squat"]["level"] == 3
    assert states["core_ant"]["level"] == 3
    assert states["hang"]["level"] == 3
    assert states["pull_v"]["level"] == 1
    assert states["mob_hips"]["level"] == 3
    assert states["squat"]["load"] == 10.0          # goblet starts at max load
    assert states["lateral"]["load"] == 4.0         # 40 % of 10 kg
    stats = placement.starting_stats(catalog, states)
    assert stats["FOR"] == 10 + 5 * (2 + 2 + 1) and stats["MOB"] == 10


def test_placement_never_uses_missing_equipment(catalog, config):
    inv = Inventory({"H"}, {"H": (10.0, 1.0)})      # no hangboard
    states = placement.place_skills(catalog, inv, {"hang": 50}, config["placement"])
    assert states["hang"]["level"] == 1


def test_plank_target_from_test(catalog, inventory, config):
    states = placement.place_skills(catalog, inventory, {"plank": 100}, config["placement"])
    assert states["core_ant"]["level"] == 4 and states["core_ant"]["target"] == 60


def test_weakest_zone(config):
    scores = placement.mobility_scores({"deep_squat": 90, "toe_touch": 20, "knee_wall": 10, "hands_back": 0},
                                       config["mobility_tests"])
    assert placement.weakest_zone(scores) == "mob_hams"


def test_snap_down():
    assert snap_down(4.3, 1.0, 10) == 4.0
    assert snap_down(0.2, 2.5, 10) == 2.5
    assert snap_down(12, 1.0, 10) == 10


# ---------------------------------------------------------------- generator

def ctx_for(catalog, inventory, config, qtype="HAUT", ci=None, day=D0, week_offset=0, **kw):
    tests = {"pushups": 15, "plank": 45, "hang": 20, "goblet": 25, "deep_squat": 40}
    skills = placement.place_skills(catalog, inventory, tests, config["placement"])
    aw = day - timedelta(days=30)
    info = patch.patch_info(day - timedelta(days=week_offset * 7), day, aw)
    ci = ci or checkin.evaluate("bon", "normale", "ok")
    return generator.GenContext(day=day, quest_type=qtype, checkin=ci, patch=info,
                                rir=patch.rir_target(info, config["rir"]["by_week"], ci.rir_bonus),
                                skills=skills, inventory=inventory, hinge_unlocked=False, **kw)


@pytest.mark.parametrize("qtype", ["HAUT", "BAS", "RECAL"])
def test_main_quest_fits_25_minutes(catalog, inventory, config, qtype):
    for i in range(30):
        ctx = ctx_for(catalog, inventory, config, qtype, day=D0 + timedelta(days=i))
        plan = generator.generate_main(catalog, ctx, config)
        assert plan["estimate_s"] <= 25 * 60, (qtype, i, plan["estimate_s"])
        assert plan["type"] == qtype
        blocks = [s["block"] for s in plan["steps"]]
        assert blocks[0] == "init" and blocks[-1] == "cooldown" and "main" in blocks


def test_trimming_removes_variable_sets_first(catalog, inventory, config):
    cfg = {**config, "quest": {**config["quest"], "max_minutes": 22}}
    ctx = ctx_for(catalog, inventory, config, "HAUT")
    full = generator.generate_main(catalog, ctx, config)
    short = generator.generate_main(catalog, ctx, cfg)
    main_sets = lambda p: sum(1 for s in p["steps"] if s["block"] == "main")
    assert short["estimate_s"] <= 22 * 60
    assert main_sets(short) == main_sets(full)        # main block untouched
    var = lambda p: sum(1 for s in p["steps"] if s["block"] == "variable")
    assert var(short) <= var(full)


def test_trimming_reaches_main_block_last(catalog, inventory, config):
    cfg = {**config, "quest": {**config["quest"], "max_minutes": 15}}
    plan = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "HAUT"), cfg)
    assert plan["variable_format"] is None
    assert not any(s["block"] == "variable" for s in plan["steps"])


def test_generation_is_deterministic(catalog, inventory, config):
    a = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "BAS"), config)
    b = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "BAS"), config)
    assert a == b


def test_variable_format_differs_from_last(catalog, inventory, config):
    for i in range(20):
        ctx = ctx_for(catalog, inventory, config, "HAUT", day=D0 + timedelta(days=i), last_format="EMOM")
        plan = generator.generate_main(catalog, ctx, config)
        assert plan["variable_format"] != "EMOM"


def test_main_supersets_are_fixed(catalog, inventory, config):
    for i in range(10):
        plan = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "HAUT", day=D0 + timedelta(days=i)), config)
        mains = {s["ex"] for s in plan["steps"] if s["block"] == "main"}
        assert mains == {"push_h", "pull_h", "push_v", "pull_v"}


def test_light_checkin_removes_a_set_and_raises_rir(catalog, inventory, config):
    normal = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "BAS"), config)
    light_ci = checkin.evaluate("mauvais", "basse", "ok")
    light = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "BAS", ci=light_ci), config)
    count = lambda p: sum(1 for s in p["steps"] if s["block"] == "main" and s["ex"] == "squat")
    assert count(light) == count(normal) - 1
    assert light["rir_target"] == normal["rir_target"] + 1
    assert light["mode"] == "light"


def test_tense_back_removes_hinge(catalog, inventory, config):
    ci = checkin.evaluate("bon", "normale", "tendu")
    plan = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "BAS", ci=ci), config)
    fids = {e["fid"] for e in plan["exercises"].values()}
    assert "hinge" not in fids
    assert "anti_rot" in fids
    assert all(e["groups"] != ["glutes_hams"] or e["fid"] != "hinge" for e in plan["exercises"].values())


def test_loaded_hinge_falls_back_when_locked(catalog, inventory, config):
    ctx = ctx_for(catalog, inventory, config, "BAS")
    ctx.skills["hinge"] = {"level": 5, "load": 10.0, "target": 8}
    plan = generator.generate_main(catalog, ctx, config)
    assert plan["exercises"]["hinge"]["level"] == 3            # back lock: hip thrust one leg
    ctx.hinge_unlocked = True
    plan = generator.generate_main(catalog, ctx, config)
    assert plan["exercises"]["hinge"]["level"] == 5


def test_deload_week(catalog, inventory, config):
    plan = generator.generate_main(catalog, ctx_for(catalog, inventory, config, "HAUT", week_offset=3), config)
    assert plan["deload"] and plan["rir_label"] == "3-4"
    assert max(s["sets_total"] for s in plan["steps"] if s["block"] == "main") == 2


def test_in_session_adjustments(catalog, inventory, config):
    ctx = ctx_for(catalog, inventory, config, "BAS")
    ctx.skills["squat"]["load"] = 8.0
    plan = generator.generate_main(catalog, ctx, config)
    adj = plan["exercises"]["squat"]["adjust"]
    assert adj["up"]["load"] == 9.0 and adj["down"]["load"] == 7.0
    assert adj["up"]["target"] == plan["exercises"]["squat"]["target"] + 2


def test_calibration_allows_two_steps(catalog, inventory, config):
    ctx = ctx_for(catalog, inventory, config, "BAS")
    ctx.patch = patch.patch_info(D0, D0, D0)
    ctx.skills["squat"]["load"] = 6.0
    adj = generator.generate_main(catalog, ctx, config)["exercises"]["squat"]["adjust"]
    assert adj["up"]["load"] == 8.0 and adj["down"]["load"] == 4.0


def test_at_max_load_no_up_load(catalog, inventory, config):
    ctx = ctx_for(catalog, inventory, config, "BAS")
    adj = generator.generate_main(catalog, ctx, config)["exercises"]["squat"]["adjust"]
    assert "load" not in adj["up"]       # goblet already at 10 kg


def test_recovery_quest_is_about_10_minutes(catalog):
    plan = generator.generate_recovery(catalog)
    assert 540 <= plan["estimate_s"] <= 660
    assert all(s["kind"] == "timed" for s in plan["steps"])


def test_mobility_quest_targets_weakest_zone(catalog, inventory):
    plan = generator.generate_mobility(catalog, D0, {}, inventory, "mob_hips")
    assert plan["estimate_s"] == 300
    hips = {v["name"] for v in catalog.variants("mob_hips")}
    assert plan["steps"][0]["name"] in hips


def test_variable_builders_shapes(catalog, inventory):
    ex = generator.prescribe(catalog, "curl", None, inventory, False)
    ex2 = generator.prescribe(catalog, "triceps", None, inventory, False)
    assert len(generator.build_variable("EMOM", [ex, ex2], 5)) == 5
    assert len(generator.build_variable("ECHELLE", [ex, ex2], 4)) == 8
    assert generator.build_variable("AMRAP", [ex, ex2], 4)[0]["seconds"] == 240
    assert generator.build_variable("CHRONO", [ex, ex2], 3)[0]["rounds"] == 3
    emom = generator.build_variable("EMOM", [ex], 2)[0]
    assert emom["work"] + emom["rest"] == 60


# ---------------------------------------------------------------- messages

LIB = {"messages": [
    {"id": "a", "event": "briefing", "ranks": ["E", "E"], "conditions": {}, "text": "E {minutes} min"},
    {"id": "b", "event": "briefing", "ranks": ["E", "C"], "conditions": {}, "text": "EC {name}"},
    {"id": "c", "event": "briefing", "ranks": ["B", "S"], "conditions": {}, "text": "B+"},
    {"id": "d", "event": "briefing", "ranks": ["E", "S"], "conditions": {"streak": {"min": 5}}, "text": "streak {streak}"},
]}


def test_message_rank_filter_and_vars():
    p = messages.LibraryProvider(LIB, random.Random(1))
    for _ in range(20):
        m = p.render("briefing", "E", {"minutes": 23, "name": "Loïc", "streak": 0}, [])
        assert m.id in ("a", "b")
        assert "{" not in m.text
    assert p.render("briefing", "A", {"streak": 0}, []).id == "c"


def test_message_conditions_preferred():
    p = messages.LibraryProvider(LIB, random.Random(1))
    assert p.render("briefing", "D", {"streak": 6}, []).text == "streak 6"


def test_message_no_repeat_of_last_10():
    p = messages.LibraryProvider(LIB, random.Random(3))
    for _ in range(20):
        assert p.render("briefing", "E", {"streak": 0}, ["a"]).id == "b"


def test_message_library_is_valid():
    import json
    from pathlib import Path
    lib = json.loads((Path(__file__).parents[1] / "data" / "system_messages.json").read_text())
    ids = [m["id"] for m in lib["messages"]]
    assert len(ids) == len(set(ids))
    for m in lib["messages"]:
        assert m["ranks"][0] in messages.RANKS and m["ranks"][1] in messages.RANKS


def test_skills_json_is_consistent(catalog):
    codes = set(catalog.equipment)
    for fid, fam in catalog.families.items():
        for i, v in enumerate(fam["variants"], 1):
            assert v["level"] == i and v["id"] == f"{fid}_{i}"
            assert v["type"] in ("reps", "time")
            assert set(v["equipment"]) <= codes
            assert 2 <= len(v["cues"]) <= 3
            assert v["video_url"] == ""
            assert set(v["groups"]) <= set(catalog.groups)


# ---------------------------------------------------------------- ranks (preview)

def test_rank_trials_preview():
    import json
    from pathlib import Path
    from app.engine import ranks
    data = json.loads((Path(__file__).parents[1] / "data" / "ranks.json").read_text())
    d = next(r for r in data["ranks"] if r["id"] == "D")
    res = ranks.evaluate_trials(d, {"pushups": 22, "arm_gain_cm": 0.5, "deep_squat_s": 61, "plank_s": 40})
    assert [r["ok"] for r in res] == [True, False, True, False]
    assert ranks.trials_passed(res) == 2
    c = next(r for r in data["ranks"] if r["id"] == "C")
    res = ranks.evaluate_trials(c, {"pushups": 10, "pullups": 3, "weight_gain_kg": 2.5, "waist_gain_cm": 3})
    assert res[0]["ok"] and not res[1]["ok"]
    assert ranks.next_rank("E") == "D" and ranks.next_rank("S") is None
