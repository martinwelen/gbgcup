# tests/test_rules.py
# -*- coding: utf-8 -*-
import rules


def test_classic_profile():
    p = rules.rule_profile("Classic")
    assert p == {"duration_min": 40, "has_results": True,
                 "has_tables": True, "has_playoffs": True}


def test_mini_profile_schedule_only():
    p = rules.rule_profile("Mini")
    assert p == {"duration_min": 40, "has_results": False,
                 "has_tables": False, "has_playoffs": False}


def test_rule_for_class_mini_set():
    assert rules.rule_for_class("F11") == "Mini"
    assert rules.rule_for_class("P10") == "Mini"
    assert rules.rule_for_class("P16") == "Classic"
    assert rules.rule_for_class("HJ") == "Classic"


def test_class_profile_duration_per_matchlength():
    # 2×15 → 40 min väggklocka; HJ 2×20 → 50.
    assert rules.class_profile("P16")["duration_min"] == 40
    assert rules.class_profile("HJ")["duration_min"] == 50
    # Mini-klass: inga resultat/tabeller.
    f11 = rules.class_profile("F11")
    assert f11["has_results"] is False and f11["has_tables"] is False
