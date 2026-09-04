# build_apps.py
# -*- coding: utf-8 -*-
"""Bygger EN samlad Alingsås-PWA (alla klasser, klass- + lagfilter) ur
data.json/standings.json → repo-roten (Pages-URL:ens rot)."""

import os
import json
import shutil

import config
import template

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
STANDINGS_JSON = os.path.join(ROOT, "standings.json")

_MON = ["", "jan", "feb", "mar", "apr", "maj", "jun",
        "jul", "aug", "sep", "okt", "nov", "dec"]
_GENDER_ORDER = {"P": 0, "F": 1, "M": 2}


def app_manifest():
    m = dict(template.MANIFEST_BASE)
    m["name"] = f"{config.CLUB_NAME} · {config.CUP_NAME}"
    m["short_name"] = "AHK GbgCup"
    m["description"] = f"Matchschema för {config.CLUB_NAME} på {config.CUP_NAME}"
    m["start_url"] = "."
    m["scope"] = "./"
    return m


def service_worker_js():
    # Unikt cachenamn per origin (martinwelen.github.io delas med ahk-beach).
    # Tom LEGACY: får ALDRIG radera syskon-appars cache.
    return (template.SERVICE_WORKER_TPL
            .replace("__CACHE__", "gbgcup-v1")
            .replace("__LEGACY__", json.dumps([])))


def club_group(data):
    """Slår ihop alla klassers lag + matcher till EN syntetisk grupp.

    Varje lag/match bär sin egen `klass` → korrekt per-item-klass i den samlade appen."""
    teams, matches = [], []
    for g in data.get("groups", {}).values():
        teams.extend(g["teams"])
        matches.extend(g["matches"])
    matches.sort(key=lambda m: m["start_ms"])
    teams.sort(key=lambda t: (t["age"], t["gender"], t["slug"]))
    return {"age": 0, "label": config.CUP_NAME, "rule": "Classic",
            "profile": {"duration_min": 40, "has_results": True,
                        "has_tables": True, "has_playoffs": True},
            "teams": teams, "matches": matches}


def merge_standings(by_age):
    """Alla klassers tabeller+slutspel → en {groups, playoffs}-blob (klass-taggad)."""
    groups, playoffs = [], []
    for bucket in by_age.values():
        groups.extend(bucket.get("groups", []))
        playoffs.extend(bucket.get("playoffs", []))
    groups.sort(key=lambda g: (g.get("klass", ""), g.get("name", "")))
    return {"groups": groups, "playoffs": playoffs}


def _classes(group):
    """Distinkta klasser i gruppen → [{cls,label}] (P<F efter ålder, HJ/DJ sist)."""
    seen = {}
    for t in group["teams"]:
        seen.setdefault(t["klass"], (t["age"], _GENDER_ORDER.get(t["gender"], 9)))
    items = sorted(seen.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0]))
    return [{"cls": k, "label": k} for k, _ in items]


def _js_matches(group):
    name_by_slug = {t["slug"]: t["team_name"] for t in group["teams"]}
    out = []
    for m in group["matches"]:
        mini = m.get("rule") == "Mini"          # F11 m.fl.: inga resultat, ingen live-poll
        out.append({
            "ms": m["start_ms"], "t": m["tid"], "bana": m["bana"], "maps": m.get("maps"),
            "lag": name_by_slug.get(m["slug"], m["slug"]), "slug": m["slug"],
            "klass": m["klass"],
            "grp": m["grupp"], "home": m["hemma"], "away": m["borta"],
            "hb": m["hb"], "day": m["day_label"], "color": m["color"].lstrip("#"),
            "dur": (m.get("dur") or 40) * 60000,   # per-match väggklocka i ms
            "res": None if mini else m.get("result"),
            "id": None if mini else m.get("id"),
            "video": m.get("video"),
            "runda": m.get("runda"),
        })
    out.sort(key=lambda x: x["ms"])
    return out


def _teams_js(group):
    return [{"lag": t["team_name"], "slug": t["slug"], "klass": t["klass"],
             "id": t["id"], "color": t["color"].lstrip("#")} for t in group["teams"]]


def _dates(group):
    """Kompakt spann över speldagar, t.ex. '4 sep – 13 sep'."""
    ds = sorted({m["datum"] for m in group["matches"]})
    if not ds:
        return "&nbsp;"

    def sh(iso):
        y, mo, da = iso.split("-")
        return f"{int(da)} {_MON[int(mo)]}"
    return sh(ds[0]) if len(ds) == 1 else f"{sh(ds[0])} – {sh(ds[-1])}"


def render_app(group, standings, base, updated):
    """Renderar den samlade appens index.html. `standings` = mergad {groups,playoffs}."""
    st = standings if (standings and (standings.get("groups") or standings.get("playoffs"))) else None
    return (template.TEMPLATE
            .replace("__DATA__", json.dumps(_js_matches(group), ensure_ascii=False))
            .replace("__TEAMS__", json.dumps(_teams_js(group), ensure_ascii=False))
            .replace("__CLASSES__", json.dumps(_classes(group), ensure_ascii=False))
            .replace("__DUR_MIN__", str(group["profile"]["duration_min"]))
            .replace("__API_HOST__", config.API_HOST)
            .replace("__TOURNAMENT_ID__", config.TOURNAMENT_ID)
            .replace("__RESULT_URL__", config.RESULT_URL)
            .replace("__BANA_XY__", "{}")          # ingen ritad karta (inomhus, 24 hallar)
            .replace("__KLUBBTALT__", "[0,0]")
            .replace("__STANDINGS__", json.dumps(st, ensure_ascii=False))
            .replace("__ROSTERS__", "{}")          # ingen trupp v1
            .replace("__CAL_ITEMS__", "")
            .replace("__APPLABEL__", group["label"])
            .replace("__DATES__", _dates(group))
            .replace("__TEAMCOUNT__", str(len(group["teams"])))
            .replace("__BASE__", base)
            .replace("__UPDATED__", updated))


_ICONS = ("icon-192.png", "icon-512.png", "icon-512-maskable.png",
          "icon-180.png", "favicon-32.png")
_ASSETS = _ICONS + ("Alingsas_HK_logo.svg",)


def _load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    data = _load(DATA_JSON, {"groups": {}, "meta": {}})
    by_age = _load(STANDINGS_JSON, {"by_age": {}}).get("by_age", {})
    updated = data.get("meta", {}).get("generated", "")

    group = club_group(data)
    standings = merge_standings(by_age)
    base = config.PAGES_BASE
    out_dir = ROOT

    html = render_app(group, standings, base, updated)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(app_manifest(), f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "sw.js"), "w", encoding="utf-8") as f:
        f.write(service_worker_js())
    for asset in _ASSETS:
        src = os.path.join(ROOT, asset)
        dst = os.path.join(out_dir, asset)
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy(src, dst)
    sched = {"matches": _js_matches(group), "standings": standings, "updated": updated}
    with open(os.path.join(out_dir, "sched.json"), "w", encoding="utf-8") as f:
        json.dump(sched, f, ensure_ascii=False)

    print(f"Byggde samlad app: {len(group['teams'])} lag, "
          f"{len(group['matches'])} matcher, {len(_classes(group))} klasser")
    return 1


if __name__ == "__main__":
    main()
