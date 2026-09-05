# -*- coding: utf-8 -*-
import json
import build_apps
import config


def _team(tid, klass, gender=None, color="#1f5fbf"):
    g = gender or (klass[0] if klass[0] in "PF" else "M")
    age = int(klass[1:]) if klass[1:].isdigit() else 99
    return {"id": tid, "slug": f"t-{tid}", "team_name": f"{klass} {tid}",
            "color": color, "gender": g, "age": age, "klass": klass}


def _m(slug, klass, rule="Classic", result=None, mid=99, dur=40):
    return {"start_ms": 1, "tid": "10:00", "bana": "Kviberg A", "maps": "https://maps/x",
            "slug": slug, "klass": klass, "grupp": "G1", "hemma": "A", "borta": "B",
            "hb": "Hemma", "day_label": "Fredag 4 september", "datum": "2026-09-04",
            "color": "#1f5fbf", "rule": rule, "dur": dur, "result": result,
            "id": mid, "video": None, "runda": None,
            "lat": 57.7384, "lng": 12.0352, "street": "Krutvägen 2-4"}


def _group(klass="P16", teams=None, matches=None):
    return {"age": 16, "label": klass, "rule": "Classic",
            "profile": {"duration_min": 40, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": teams if teams is not None else [_team(1, klass)],
            "matches": matches or []}


def test_club_group_merges_all_classes():
    data = {"groups": {
        "P16": _group("P16", [_team(1, "P16")], [_m("t-1", "P16")]),
        "F13": _group("F13", [_team(2, "F13")], [_m("t-2", "F13")]),
    }}
    g = build_apps.club_group(data)
    assert {t["klass"] for t in g["teams"]} == {"P16", "F13"}
    assert len(g["matches"]) == 2
    assert g["profile"]["has_tables"] is True     # tillåtande → tabell-fliken gatas ej bort


def test_classes_distinct_sorted_juniors_last():
    g = _group()
    g["teams"] = [_team(1, "P16"), _team(2, "F13"), _team(3, "HJ"), _team(4, "P15")]
    classes = [c["cls"] for c in build_apps._classes(g)]
    assert classes == ["F13", "P15", "P16", "HJ"]   # ålder asc, P<F, junior sist


def test_js_matches_per_item_klass_and_maps():
    g = _group("F13", [_team(2, "F13")], [_m("t-2", "F13")])
    m = build_apps._js_matches(g)[0]
    assert m["klass"] == "F13"
    assert m["maps"] == "https://maps/x" and m["bana"] == "Kviberg A"
    assert m["lag"] == "F13 2"                       # team_name, inte slug


def test_js_matches_mini_hides_result_and_id():
    # Landmina B: Mini-klass (F11) → ingen live-poll (id None), inget resultat.
    g = _group("F11", [_team(9, "F11")],
               [_m("t-9", "F11", rule="Mini", result={"hg": 5, "ag": 3}, mid=555)])
    m = build_apps._js_matches(g)[0]
    assert m["id"] is None and m["res"] is None


def test_js_matches_classic_keeps_result_and_id():
    g = _group("P16", [_team(1, "P16")],
               [_m("t-1", "P16", result={"hg": 20, "ag": 18}, mid=777)])
    m = build_apps._js_matches(g)[0]
    assert m["id"] == 777 and m["res"] == {"hg": 20, "ag": 18}


def test_js_matches_includes_datum():
    g = _group("P16", [_team(1, "P16")], [_m("t-1", "P16")])
    assert build_apps._js_matches(g)[0]["datum"] == "2026-09-04"


def test_js_matches_dur_in_ms():
    g = _group("HJ", [_team(1, "HJ")], [_m("t-1", "HJ", dur=50)])
    assert build_apps._js_matches(g)[0]["dur"] == 50 * 60000


def test_js_matches_strips_hash_from_color():
    g = _group("P16", [_team(1, "P16")], [_m("t-1", "P16")])
    assert build_apps._js_matches(g)[0]["color"] == "1f5fbf"


def test_teams_js_klass_and_numeric_id():
    g = _group("P16", [_team(999001, "P16")])
    t = build_apps._teams_js(g)[0]
    assert t["id"] == 999001 and t["slug"] == "t-999001" and t["klass"] == "P16"


def test_venues_aggregates_distinct_halls_by_count():
    g = _group("P16", [_team(1, "P16")], [_m("t-1", "P16"), _m("t-1", "P16")])
    v = build_apps._venues(g)
    assert len(v) == 1                          # båda matcherna i samma hall
    assert v[0]["hall"] == "Kviberg A" and v[0]["n"] == 2
    assert v[0]["lat"] == 57.7384 and v[0]["street"] == "Krutvägen 2-4"


def test_merge_standings_concats_and_sorts():
    by_age = {
        "P16": {"groups": [{"klass": "P16", "name": "Grupp I"}], "playoffs": [{"klass": "P16"}]},
        "F13": {"groups": [{"klass": "F13", "name": "Grupp K"}], "playoffs": []},
    }
    st = build_apps.merge_standings(by_age)
    assert [g["klass"] for g in st["groups"]] == ["F13", "P16"]   # sorterat (klass,name)
    assert [p["klass"] for p in st["playoffs"]] == ["P16"]


def test_service_worker_gbgcup_cache_empty_legacy():
    sw = build_apps.service_worker_js()
    assert 'const C = "gbgcup-v1";' in sw
    assert "const LEGACY = [];" in sw     # får ALDRIG radera syskon-appars cache
    assert "__CACHE__" not in sw and "ahus" not in sw


def test_app_manifest_identity():
    m = build_apps.app_manifest()
    assert m["name"] == "Alingsås HK · Göteborg Cup"
    assert m["start_url"] == "." and m["scope"] == "./"


def test_render_app_no_placeholders_and_embeds_config():
    data = {"groups": {"P16": _group("P16", [_team(1, "P16")], [_m("t-1", "P16")])}}
    g = build_apps.club_group(data)
    html = build_apps.render_app(g, standings={"groups": [], "playoffs": []},
                                 base="https://x/gbgcup", updated="nyss")
    for ph in ("__DATA__", "__STANDINGS__", "__APPLABEL__", "__CLASSES__",
               "__BANA_XY__", "__KLUBBTALT__", "__ROSTERS__", "__API_HOST__",
               "__TOURNAMENT_ID__", "__RESULT_URL__", "__DATES__", "__TEAMCOUNT__"):
        assert ph not in html
    assert config.API_HOST in html and config.TOURNAMENT_ID in html
    assert config.RESULT_URL in html
    assert "const BANA_XY = {};" in html          # ingen ritad karta
    assert "Göteborg Cup" in html
    assert html.startswith("<!doctype html>")


def test_main_writes_single_app_at_root(tmp_path, monkeypatch):
    data = {"meta": {"generated": "2026-09-04T00:00:00Z"},
            "groups": {"P16": _group("P16", [_team(1, "P16")], [_m("t-1", "P16")]),
                       "F13": _group("F13", [_team(2, "F13")], [_m("t-2", "F13")])}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    for ic in ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
               "icon-180.png", "favicon-32.png", "Alingsas_HK_logo.svg"):
        (tmp_path / ic).write_bytes(b"x")
    monkeypatch.setattr(build_apps, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_apps, "DATA_JSON", str(tmp_path / "data.json"))
    monkeypatch.setattr(build_apps, "STANDINGS_JSON", str(tmp_path / "nope.json"))
    n = build_apps.main()
    assert n == 1
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "sw.js").exists()
    sj = json.loads((tmp_path / "sched.json").read_text(encoding="utf-8"))
    assert isinstance(sj["matches"], list) and len(sj["matches"]) == 2
    assert "standings" in sj
