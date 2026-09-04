# rules.py
# -*- coding: utf-8 -*-
"""Format-profil per regeltyp/klass för Göteborg Cup (inomhus).

Mini = schema bara (inga resultat/tabeller/slutspel) — gäller de yngsta klasserna
(P10/F10/P11/F11, födda 2015/16) enligt Svensk Handbolls regler. Övriga = Classic
(grupptabell + A/B-slutspel).

Matchlängd (goteborgcup.com/sv/tavlingsregler): 2×15 min alla klasser UTOM HJ = 2×20.
`duration_min` här är väggklocke-DUR (spel + halvlek + marginal) som driver live-läget
(`state()` markerar "past" efter start+DUR), inte ren speltid."""

# Yngsta klasserna: inga resultat/tabeller/slutspel.
MINI_CLASSES = {"P10", "F10", "P11", "F11"}

_PROFILES = {
    "Classic": {"duration_min": 40, "has_results": True,
                "has_tables": True, "has_playoffs": True},
    "Mini":    {"duration_min": 40, "has_results": False,
                "has_tables": False, "has_playoffs": False},
}

_DEFAULT = dict(_PROFILES["Classic"])


def rule_for_class(klass):
    """Klass-token (t.ex. 'P16','F11','HJ') → regeltyp ('Mini'/'Classic')."""
    return "Mini" if klass in MINI_CLASSES else "Classic"


def rule_profile(rule):
    return dict(_PROFILES.get(rule, _DEFAULT))


def class_profile(klass):
    """Profil för en klass, med väggklocke-duration per matchlängd."""
    prof = dict(_PROFILES[rule_for_class(klass)])
    prof["duration_min"] = 50 if klass == "HJ" else 40   # HJ = 2×20, övriga 2×15
    return prof
