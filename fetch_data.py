# fetch_data.py
# -*- coding: utf-8 -*-
"""Klubbkodsdriven datahämtning → data.json (lag + matcher per klass)."""

import hashlib
import json
import os
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import api
import config
import derive
import rules


def clean_hall(name):
    """CupManagers completeName = venue + fieldName, ofta med upprepning
    ('Prioritet Serneke Arena Serneke Arena B'). Kollapsa direkt upprepade
    ord-körningar → 'Prioritet Serneke Arena B'."""
    w = (name or "").split()
    out, i = [], 0
    while i < len(w):
        collapsed = False
        for L in range((len(w) - i) // 2, 0, -1):
            if w[i:i + L] == w[i + L:i + 2 * L]:
                out.extend(w[i:i + L])
                i += 2 * L
                collapsed = True
                break
        if not collapsed:
            out.append(w[i])
            i += 1
    return " ".join(out)


def _maps_url(hall):
    """Fallback: Google Maps-sök på hallnamn (om exakta koordinater saknas)."""
    if not hall:
        return None
    q = urllib.parse.quote(f"{hall} Göteborg")
    return f"https://www.google.com/maps/search/?api=1&query={q}"


_LOC_CACHE = {}


def _arena_coords(arena):
    """Arena → Location → MapLocation ger exakt lat/lng. Cachas per Location-id.

    Returnerar (lat, lng, street) eller None."""
    loc = arena.get("location") if isinstance(arena, dict) else None
    lid = api.ref_id(loc) if loc else None
    if not lid:
        return None
    if lid in _LOC_CACHE:
        return _LOC_CACHE[lid]
    coords = None
    try:
        resp = api.call(f"Location({{id:{lid},tid:{config.TOURNAMENT_ID}}})$location")
        for v in resp.get("responses", {}).values():
            e = v.get("entity", {}) if isinstance(v, dict) else {}
            if isinstance(e, dict) and e.get("__typename") == "MapLocation":
                lat, lng = e.get("latitude"), e.get("longitude")
                if lat and lng:
                    coords = (lat, lng, e.get("street") or "")
                break
    except Exception:
        coords = None
    _LOC_CACHE[lid] = coords
    return coords


def _maps_for(arena, venue, hall):
    """Exakt koordinat-länk om möjligt, annars namnsökning på komplexet."""
    c = _arena_coords(arena)
    if c:
        return f"https://www.google.com/maps/search/?api=1&query={c[0]},{c[1]}"
    return _maps_url(venue or hall)


def build_team_registry(store):
    """Alla klubbens lag ur en entitets-store, med härledd metadata + färg.

    Returnerar en lista av dict:
      {id, gender, age, klass, rule, suffix, team_name, age_slug, slug, color, dur}
    """
    teams = []
    for e in store.values():
        if e.get("__typename") != "Team":
            continue
        if api.ref_id(e.get("club")) != config.CLUB_ID:
            continue
        nm = e.get("name") or {}
        p = derive.parse_category(nm.get("categoryName", ""))
        klass = p["klass"]
        teams.append({
            "id": e["id"],
            "gender": p["gender"], "age": p["age"], "klass": klass,
            "rule": rules.rule_for_class(klass),
            "dur": rules.class_profile(klass)["duration_min"],
            "suffix": nm.get("suffix", "") or "",
            # Visningsnamn: categoryName ("P16 2", "F13 Vit") är tydligast för en klubb-app.
            "team_name": nm.get("categoryName", "") or nm.get("clubName", ""),
            "age_slug": klass,                      # klass = grupperingsnyckel (P16≠F16)
            "slug": f"t-{e['id']}",                 # unikt → aldrig kollision Vit/Blå/1/2
        })

    # Färg tilldelas per klass (regeln behöver hela klassen).
    by_klass = defaultdict(list)
    for t in teams:
        by_klass[t["klass"]].append(t)
    for group in by_klass.values():
        colors = derive.derive_group_colors(group)
        for t in group:
            t["color"] = colors[t["id"]]

    teams.sort(key=lambda t: (t["age"], t["gender"], t["slug"]))
    return teams


_CEST = timezone(timedelta(hours=config.UTC_OFFSET_HOURS))
_SV_DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
_SV_MONTHS = ["", "januari", "februari", "mars", "april", "maj", "juni",
              "juli", "augusti", "september", "oktober", "november", "december"]


def _extract_result(res):
    if not res or not res.get("finished"):
        return None
    hg, ag = res.get("homeGoals"), res.get("awayGoals")
    if hg is None or ag is None:
        return None
    return {"hg": hg, "ag": ag}


def _runda_sv(name):
    """cupmanagers rundnamn (en) → svensk kortform."""
    if not name:
        return None
    n = name.strip()
    low = n.lower()
    if low == "final":
        return "Final"
    if "semi" in low or low == "1/2 final":
        return "Semifinal"
    if "quarter" in low or low == "1/4 final":
        return "Kvartsfinal"
    import re as _re
    m = _re.match(r"^(1/\d+)\s*final$", low)
    if m:
        return f"{m.group(1)}-final"
    return n


def _round_name(mid):
    """Resolvar Match($roundName) → svensk kortform, annars None."""
    if not mid:
        return None
    try:
        resp = api.call(f"Match({{id:{mid}}})$roundName").get("responses", {})
    except Exception:
        return None
    for v in resp.values():
        ent = v.get("entity", {}) if isinstance(v, dict) else {}
        if isinstance(ent, dict) and ent.get("__typename") == "Match$RoundName":
            nm = ent.get("name")
            en = nm.get("en") if isinstance(nm, dict) else nm
            return _runda_sv(en)
    return None


def _video_url(mid):
    """Resolvar Match($video) → solidsport externalLink, annars None."""
    if not mid:
        return None
    try:
        resp = api.call(f"Match({{id:{mid}}})$video").get("responses", {})
    except Exception:
        return None
    for v in resp.values():
        ent = v.get("entity", {}) if isinstance(v, dict) else {}
        if isinstance(ent, dict) and ent.get("__typename") == "Video":
            return ent.get("externalLink")
    return None


def normalize_match(e, store, reg_by_id):
    """En Match-entitet → normaliserad dict, knuten till klubbens lag.

    Returnerar None om matchen inte rör något av klubbens lag.
    """
    home_a = api.store_get(store, e.get("home", {}))
    away_a = api.store_get(store, e.get("away", {}))
    hid = api.ref_id(home_a.get("team")) if home_a else None
    aid = api.ref_id(away_a.get("team")) if away_a else None
    team = reg_by_id.get(hid) or reg_by_id.get(aid)
    if not team:
        return None
    start_ms = e.get("start")
    if not start_ms:                       # ännu ej tidssatt match (t.ex. slutspels-TBD)
        return None

    hb = "Hemma" if hid in reg_by_id else "Borta"
    hemma = api.name_of(home_a)
    borta = api.name_of(away_a)
    div = api.store_get(store, e.get("division", {}))
    grupp = api.name_of(div)
    arena = api.store_get(store, e.get("arena", {})) or {}
    complete = arena.get("completeName", "") or ""
    field = arena.get("fieldName", "") or ""
    # completeName = komplex + bananamn (bananamnet upprepar ofta komplexet).
    # Visning: av-dubblerad kompakt form. Maps: peka på komplexet (dit man kör).
    hall = clean_hall(complete)
    venue = complete[:-len(field)].strip() if field and complete.endswith(field) else hall
    video = _video_url(e.get("id"))        # GbgCup streamar brett – gata inte på bana
    runda = _round_name(e.get("id")) if "slutspel" in grupp.lower() else None
    dt = datetime.fromtimestamp(start_ms / 1000, _CEST)
    result = _extract_result(api.store_get(store, e.get("result", {})))

    return {
        "age_slug": team["age_slug"], "slug": team["slug"],
        "id": e.get("id"),
        "gender": team["gender"], "klass": team["klass"], "rule": team["rule"],
        "dur": team["dur"], "color": team["color"],
        "datum": f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}",
        "dag": _SV_DAYS[dt.weekday()],
        "tid": f"{dt.hour:02d}:{dt.minute:02d}",
        "bana": hall, "maps": _maps_for(arena, venue, hall),
        "video": video,
        "runda": runda,
        "hemma": hemma, "borta": borta,
        "grupp": grupp,
        "mots": borta if hb == "Hemma" else hemma,
        "hb": hb, "result": result,
        "start_ms": start_ms,
        "start_iso": dt.isoformat(timespec="minutes"),
        "day_label": f"{_SV_DAYS[dt.weekday()]} {dt.day} {_SV_MONTHS[dt.month]}",
    }


def bucket_by_age_group(registry, match_entities, store):
    """Bygger {klass: {age,label,rule,profile,teams,matches}} ur lag + matcher."""
    reg_by_id = {t["id"]: t for t in registry}
    groups = {}
    for t in registry:
        a = t["age_slug"]
        if a not in groups:
            groups[a] = {"age": t["age"], "label": t["klass"],
                         "rule": t["rule"], "profile": rules.class_profile(t["klass"]),
                         "teams": [], "matches": []}
        groups[a]["teams"].append(t)

    for e in match_entities:
        nm = normalize_match(e, store, reg_by_id)
        if nm and nm["age_slug"] in groups:
            groups[nm["age_slug"]]["matches"].append(nm)

    for g in groups.values():
        g["matches"].sort(key=lambda m: (m["start_ms"], str(m["bana"])))
    return groups


def _hash_groups(groups):
    key = []
    for a in sorted(groups):
        g = groups[a]
        key.append((a, g["rule"], [t["id"] for t in g["teams"]],
                    [(m["slug"], m["start_ms"], str(m["bana"]), m.get("maps"),
                      m["hemma"], m["borta"], m["grupp"], m.get("result"),
                      m.get("id"), m.get("video"), m.get("runda"))
                     for m in g["matches"]]))
    return hashlib.sha256(json.dumps(key, ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def assemble(groups, generated, seq):
    return {
        "meta": {
            "source": f"cupmanager API (klubbkod {config.CLUB_ID}, "
                      f"tournamentId {config.TOURNAMENT_ID})",
            "club_id": config.CLUB_ID,
            "generated": generated, "seq": seq,
            "data_hash": _hash_groups(groups),
        },
        "groups": groups,
    }


def write_if_changed(groups, path, generated, seq):
    """Skriver data.json bara om innehållet ändrats. Returnerar True om skrivet."""
    new_hash = _hash_groups(groups)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("meta", {}).get("data_hash") == new_hash:
                return False
        except Exception:
            pass
    doc = assemble(groups, generated, seq)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return True


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")


def main():
    try:
        store = api.fetch_store()
    except Exception as e:
        print("FEL vid hämtning:", e, "- lämnar data.json orörd")
        return 0
    registry = build_team_registry(store)
    if not registry:
        print("0 lag för klubbkoden - lämnar data.json orörd")
        return 0
    match_entities = [e for e in store.values() if e.get("__typename") == "Match"]
    groups = bucket_by_age_group(registry, match_entities, store)
    now = datetime.now(timezone.utc)
    wrote = write_if_changed(groups, DATA_JSON,
                             generated=now.isoformat(timespec="seconds"),
                             seq=int(now.timestamp()))
    n_t = sum(len(g["teams"]) for g in groups.values())
    n_m = sum(len(g["matches"]) for g in groups.values())
    print(f"{'Skrev' if wrote else 'Ingen ändring;'} {len(groups)} "
          f"klasser, {n_t} lag, {n_m} matcher"
          + ("" if wrote else " (skrev inte om)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
