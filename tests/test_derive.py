# tests/test_derive.py
# -*- coding: utf-8 -*-
import derive


def test_slugify_lowercases_and_hyphenates():
    assert derive.slugify("Lag Blå") == "lag-bla"


def test_slugify_maps_swedish_vowels():
    assert derive.slugify("Gulö Ärt") == "gulo-art"


def test_slugify_strips_non_alnum_and_collapses():
    assert derive.slugify("AHK  2 / B") == "ahk-2-b"


def test_slugify_empty_is_empty():
    assert derive.slugify("") == ""


def test_parse_category_boys_with_team_number():
    p = derive.parse_category("P16 2")
    assert p == {"gender": "P", "age": 16, "klass": "P16"}


def test_parse_category_girls_with_color():
    p = derive.parse_category("F13 Vit")
    assert p == {"gender": "F", "age": 13, "klass": "F13"}


def test_parse_category_no_suffix():
    p = derive.parse_category("P15")
    assert p == {"gender": "P", "age": 15, "klass": "P15"}


def test_parse_category_boys_junior():
    p = derive.parse_category("HJ 1")
    assert p == {"gender": "M", "age": 99, "klass": "HJ"}


def test_parse_category_girls_junior():
    p = derive.parse_category("DJ")
    assert p == {"gender": "F", "age": 99, "klass": "DJ"}


def test_parse_category_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        derive.parse_category("Herrar A")


import config


def _team(suffix):
    return {"id": hash(suffix) & 0xffff, "suffix": suffix}


def test_colors_single_team_is_club_blue():
    teams = [_team("1")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.CLUB_BLUE


def test_colors_all_color_suffixes_use_color_map():
    teams = [_team("Blå"), _team("Vit"), _team("Orange")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.COLOR_MAP["bla"]
    assert out[teams[1]["id"]] == config.COLOR_MAP["vit"]
    assert out[teams[2]["id"]] == config.COLOR_MAP["orange"]


def test_colors_mixed_suffixes_use_palette_by_index():
    teams = [_team("Blå"), _team("1"), _team("Vit")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.PALETTE[0]
    assert out[teams[1]["id"]] == config.PALETTE[1]
    assert out[teams[2]["id"]] == config.PALETTE[2]


def test_colors_multiword_color_suffix_detected():
    teams = [_team("Lag Blå"), _team("Lag Vit")]
    out = derive.derive_group_colors(teams)
    assert out[teams[0]["id"]] == config.COLOR_MAP["bla"]
