# derive.py
# -*- coding: utf-8 -*-
"""Rena härledningsfunktioner: slug, kategoritolkning, färgregel. Ingen I/O."""

import re

_SV = str.maketrans({"å": "a", "ä": "a", "ö": "o", "é": "e",
                     "Å": "a", "Ä": "a", "Ö": "o", "É": "e"})


def slugify(s):
    s = (s or "").translate(_SV).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# Göteborg Cup: klass-token inleder categoryName, t.ex. "P16 2", "F13 Vit", "P15",
# "HJ 1", "DJ". Klassen kommer från kategorin — INTE Åhus "(f. 2011)"-formatet.
_GBG_CLASS_RE = re.compile(r"^\s*(P\d+|F\d+|HJ|DJ)\b")


def parse_category(category_name):
    """'P16 2' / 'F13 Vit' / 'HJ 1' / 'DJ' -> {gender, age, klass}.

    `klass` är den rena klass-etiketten (P16/F13/HJ/DJ) som filtret använder.
    Juniorer: HJ = herrjunior (M), DJ = damjunior (F); age=99 → sorteras sist.
    Failar högt på okänt namn (hellre synligt fel än tyst felgruppering)."""
    name = (category_name or "").strip()
    m = _GBG_CLASS_RE.match(name)
    if not m:
        raise ValueError(f"Okänd klass i categoryName: {name!r}")
    klass = m.group(1)
    if klass[0] == "P":
        return {"gender": "P", "age": int(klass[1:]), "klass": klass}
    if klass[0] == "F":
        return {"gender": "F", "age": int(klass[1:]), "klass": klass}
    if klass == "HJ":
        return {"gender": "M", "age": 99, "klass": "HJ"}
    return {"gender": "F", "age": 99, "klass": "DJ"}


import config


def _color_word(suffix):
    """Returnerar färgnyckel (COLOR_MAP) om suffixet innehåller ett färgord, annars None."""
    tokens = slugify(suffix).split("-")
    for t in tokens:
        if t in config.COLOR_MAP:
            return t
    return None


def derive_group_colors(teams):
    """teams: lista av dict med 'id' och 'suffix' (en klass).

    Regel: ett lag → klubbens blå; alla har färgsuffix → den färgen;
    annars → palett per index. Returnerar {team_id: hexfärg}.
    """
    if len(teams) == 1:
        return {teams[0]["id"]: config.CLUB_BLUE}
    words = [_color_word(t["suffix"]) for t in teams]
    if all(w is not None for w in words):
        return {t["id"]: config.COLOR_MAP[w] for t, w in zip(teams, words)}
    return {t["id"]: config.PALETTE[i % len(config.PALETTE)]
            for i, t in enumerate(teams)}
