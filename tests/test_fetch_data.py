# tests/test_fetch_data.py
# -*- coding: utf-8 -*-
import json
import os
import fetch_data
import config


def _team(tid, category_name, suffix="", club_id=config.CLUB_ID):
    return {
        "__typename": "Team", "id": tid,
        "club": {"href": f"NameClub({{id:{club_id}}})"},
        "name": {"clubName": f"Alingsås HK {category_name}",
                 "categoryName": category_name, "suffix": suffix},
    }


def test_registry_filters_to_club_only():
    store = {
        "Team({id:1})": _team(1, "P16 1"),
        "Team({id:2})": _team(2, "P16 2", club_id=999),
    }
    reg = fetch_data.build_team_registry(store)
    assert [t["id"] for t in reg] == [1]


def test_registry_derives_fields_klass_and_slug():
    store = {"Team({id:1})": _team(1, "P15")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["gender"] == "P" and t["age"] == 15 and t["klass"] == "P15"
    assert t["rule"] == "Classic" and t["age_slug"] == "P15"
    assert t["slug"] == "t-1"                     # unikt lag-id, aldrig kollision
    assert t["team_name"] == "P15"


def test_registry_junior_classes():
    store = {"Team({id:1})": _team(1, "HJ 1"), "Team({id:2})": _team(2, "DJ")}
    reg = {t["klass"]: t for t in fetch_data.build_team_registry(store)}
    assert reg["HJ"]["gender"] == "M" and reg["HJ"]["age"] == 99
    assert reg["DJ"]["gender"] == "F" and reg["DJ"]["age"] == 99


def test_registry_mini_class_gets_mini_rule():
    store = {"Team({id:1})": _team(1, "F11 Blå", suffix="Blå")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["rule"] == "Mini" and t["dur"] == 40


def test_registry_hj_duration_is_2x20():
    store = {"Team({id:1})": _team(1, "HJ 1")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["dur"] == 50


def test_registry_assigns_colors_per_klass():
    store = {
        "Team({id:1})": _team(1, "F13 Blå", suffix="Blå"),
        "Team({id:2})": _team(2, "F13 Orange", suffix="Orange"),
        "Team({id:3})": _team(3, "F13 Vit", suffix="VIT"),
    }
    reg = {t["id"]: t for t in fetch_data.build_team_registry(store)}
    assert reg[1]["color"] == config.COLOR_MAP["bla"]
    assert reg[2]["color"] == config.COLOR_MAP["orange"]
    assert reg[3]["color"] == config.COLOR_MAP["vit"]


def test_registry_single_team_klass_is_club_blue():
    store = {"Team({id:9})": _team(9, "P16 1")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["color"] == config.CLUB_BLUE


def _match(mid, start_ms, hall, home_actor, away_actor, division_name,
           home_team_id, away_team_id, result=None):
    return {
        "__typename": "Match", "id": mid, "start": start_ms,
        "arena": {"href": f"Arena({{id:{mid}}})"},
        "home": {"href": f"H({mid})"}, "away": {"href": f"A({mid})"},
        "division": {"href": f"D({mid})"}, "result": {"href": f"R({mid})"},
        "_arena": {"completeName": hall},
        "_home": {"name": {"en": home_actor}, "team": {"href": f"Team({{id:{home_team_id}}})"}},
        "_away": {"name": {"en": away_actor}, "team": {"href": f"Team({{id:{away_team_id}}})"}},
        "_division": {"name": {"sv": division_name}},
        "_result": result or {"finished": False},
    }


def _store_for_match(m):
    mid = m["id"]
    return {
        f"Arena({{id:{mid}}})": m["_arena"],
        f"H({mid})": m["_home"], f"A({mid})": m["_away"],
        f"D({mid})": m["_division"], f"R({mid})": m["_result"],
        f"Match({{id:{mid}}})": m,
    }


def _reg1():
    return {1: {"id": 1, "slug": "t-1", "age_slug": "P15", "klass": "P15",
                "gender": "P", "rule": "Classic", "dur": 40, "color": "#1f5fbf"}}


def test_normalize_match_basic_fields():
    m = _match(100, 1783585800000, "Kviberg Park Sporthall A", "Alingsås HK Blå",
               "Lugi HF 3", "Grupp 2", home_team_id=1, away_team_id=50)
    nm = fetch_data.normalize_match(m, _store_for_match(m), _reg1())
    assert nm["age_slug"] == "P15" and nm["klass"] == "P15" and nm["slug"] == "t-1"
    assert nm["bana"] == "Kviberg Park Sporthall A"       # hallnamn (sträng)
    assert "maps" in nm and "Kviberg" in nm["maps"] and nm["maps"].startswith("https://")
    assert nm["hemma"] == "Alingsås HK Blå" and nm["borta"] == "Lugi HF 3"
    assert nm["hb"] == "Hemma" and nm["mots"] == "Lugi HF 3"
    assert nm["grupp"] == "Grupp 2"
    assert nm["tid"] == "10:30"          # 1783585800000 ms = 08:30 UTC = 10:30 CEST
    assert nm["result"] is None


def test_normalize_match_away_side_and_result():
    res = {"finished": True, "homeGoals": 9, "awayGoals": 14}
    m = _match(101, 1783585800000, "ÖHK-Hallen", "IFK Kristianstad 2",
               "Alingsås HK Blå", "Grupp 2", home_team_id=50, away_team_id=1, result=res)
    nm = fetch_data.normalize_match(m, _store_for_match(m), _reg1())
    assert nm["hb"] == "Borta"
    assert nm["mots"] == "IFK Kristianstad 2"
    assert nm["result"] == {"hg": 9, "ag": 14}


def test_bucket_by_klass_groups_and_sorts_by_time():
    reg = [{"id": 1, "slug": "t-1", "age_slug": "P15", "klass": "P15", "age": 15,
            "gender": "P", "rule": "Classic", "dur": 40, "team_name": "P15",
            "suffix": "", "color": "#1f5fbf"}]
    m_late = _match(2, 1783589400000, "Hall B", "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m_early = _match(1, 1783585800000, "Hall A", "Alingsås HK Blå", "Y", "Grupp 2", 1, 50)
    store = {}
    store.update(_store_for_match(m_late))
    store.update(_store_for_match(m_early))
    groups = fetch_data.bucket_by_age_group(reg, [m_early, m_late], store)
    assert "P15" in groups
    g = groups["P15"]
    assert g["age"] == 15 and g["label"] == "P15" and g["rule"] == "Classic"
    assert [t["id"] for t in g["teams"]] == [1]
    assert [mm["start_ms"] for mm in g["matches"]] == [1783585800000, 1783589400000]


def test_normalize_match_returns_none_for_non_club_match():
    m = _match(200, 1783585800000, "Hall X", "Lugi HF", "IFK Kristianstad", "Grupp 1", 99, 88)
    assert fetch_data.normalize_match(m, _store_for_match(m), _reg1()) is None


def test_normalize_match_returns_none_for_untimed_match():
    m = _match(300, 1783585800000, "Hall X", "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m["start"] = None                        # ännu ej tidssatt (slutspels-TBD)
    assert fetch_data.normalize_match(m, _store_for_match(m), _reg1()) is None


def test_normalize_match_includes_cupmanager_id():
    import api
    e = {"id": 81848529, "home": {"href": "h"}, "away": {"href": "a"},
         "start": 1784034000000, "division": {}, "arena": {}, "result": {}}
    reg = {7: {"id": 7, "age_slug": "P15", "slug": "t-7", "klass": "P15", "gender": "P",
               "rule": "Classic", "dur": 40, "color": "#1f5fbf", "age": 15}}
    orig = (api.ref_id, api.name_of, api.store_get, api.call)
    api.store_get = lambda s, r: {"team": {"href": "Team({id:7})"}, "completeName": "Hall"}
    api.ref_id = lambda n: 7
    api.name_of = lambda x: "Lag"
    api.call = lambda q: {"responses": {}}
    try:
        m = fetch_data.normalize_match(e, {}, reg)
    finally:
        api.ref_id, api.name_of, api.store_get, api.call = orig
    assert m is not None and m["id"] == 81848529


def test_video_url_extracts_external_link():
    import api
    orig = api.call
    api.call = lambda q: {"responses": {"Video({id:1})": {"entity": {
        "__typename": "Video", "externalLink": "https://solidsport.com/x"}}}}
    try:
        assert fetch_data._video_url(123) == "https://solidsport.com/x"
        api.call = lambda q: {"responses": {}}
        assert fetch_data._video_url(123) is None
        assert fetch_data._video_url(None) is None
    finally:
        api.call = orig


def test_hash_includes_id_and_video():
    import copy
    base = {"P15": {"rule": "Classic", "teams": [{"id": 1}],
            "matches": [{"slug": "s", "start_ms": 1, "bana": "Hall A", "hemma": "a",
                         "borta": "b", "grupp": "g", "result": None,
                         "id": 10, "video": None, "runda": None}]}}
    h1 = fetch_data._hash_groups(base)
    b2 = copy.deepcopy(base); b2["P15"]["matches"][0]["video"] = "https://x"
    b3 = copy.deepcopy(base); b3["P15"]["matches"][0]["id"] = 99
    assert fetch_data._hash_groups(b2) != h1   # video ändrar hashen
    assert fetch_data._hash_groups(b3) != h1   # id ändrar hashen


def test_runda_sv_mapping():
    f = fetch_data
    assert f._runda_sv("Final") == "Final"
    assert f._runda_sv("1/2 Final") == "Semifinal"
    assert f._runda_sv("Semi final") == "Semifinal"
    assert f._runda_sv("1/4 Final") == "Kvartsfinal"
    assert f._runda_sv("Quarter final") == "Kvartsfinal"
    assert f._runda_sv("1/8 Final") == "1/8-final"
    assert f._runda_sv(None) is None
    assert f._runda_sv("Bronsmatch") == "Bronsmatch"


def test_round_name_resolves_swedish():
    import api
    orig = api.call
    api.call = lambda q: {"responses": {"r": {"entity": {
        "__typename": "Match$RoundName", "name": {"en": "1/2 Final"}}}}}
    try:
        assert fetch_data._round_name(5) == "Semifinal"
        api.call = lambda q: {"responses": {}}
        assert fetch_data._round_name(5) is None
    finally:
        api.call = orig


def test_assemble_shapes_doc_with_meta_and_groups():
    groups = {"P15": {"age": 15, "label": "P15", "rule": "Classic",
                      "profile": {"duration_min": 40}, "teams": [], "matches": []}}
    doc = fetch_data.assemble(groups, generated="2026-09-04T00:00:00Z", seq=1)
    assert doc["meta"]["club_id"] == config.CLUB_ID
    assert doc["meta"]["seq"] == 1 and "data_hash" in doc["meta"]
    assert doc["groups"]["P15"]["label"] == "P15"


def test_data_hash_stable_regardless_of_meta():
    groups = {"P15": {"age": 15, "label": "P15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    a = fetch_data.assemble(groups, generated="2026-01-01T00:00:00Z", seq=1)
    b = fetch_data.assemble(groups, generated="2026-09-09T00:00:00Z", seq=2)
    assert a["meta"]["data_hash"] == b["meta"]["data_hash"]


def test_write_if_changed_writes_then_skips(tmp_path):
    groups = {"P15": {"age": 15, "label": "P15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    path = os.path.join(tmp_path, "data.json")
    wrote1 = fetch_data.write_if_changed(groups, path, generated="2026-09-04T00:00:00Z", seq=1)
    wrote2 = fetch_data.write_if_changed(groups, path, generated="2026-09-05T00:00:00Z", seq=2)
    assert wrote1 is True and wrote2 is False
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["meta"]["seq"] == 1
