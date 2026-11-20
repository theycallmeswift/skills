"""Tests for contrast.py: hex parsing, WCAG maths, thresholds, CLI output and exit codes."""

from __future__ import annotations

import json

import contrast
import pytest


def test_black_on_white_is_21():
    ratio = contrast.contrast_ratio(contrast.parse_hex("#000"), contrast.parse_hex("#fff"))

    assert round(ratio, 2) == 21.00


def test_ratio_is_symmetric():
    forward = contrast.contrast_ratio((10, 20, 30), (200, 210, 220))
    backward = contrast.contrast_ratio((200, 210, 220), (10, 20, 30))

    assert forward == backward


def test_777_on_white_fails_aa_normal():
    result = contrast.evaluate_pair("#777", "#fff")

    assert result["ratio"] == 4.48
    assert result["aa_normal"] is False
    assert result["aa_large"] is True


def test_767676_on_white_passes_aa_normal():
    result = contrast.evaluate_pair("#767676", "#ffffff")

    assert result["ratio"] == 4.54
    assert result["aa_normal"] is True
    assert result["aaa_normal"] is False


def test_threshold_compares_unrounded_ratio():
    result = contrast.evaluate_pair("#777777", "#ffffff")

    assert result["ratio"] == 4.48
    assert result["aa_normal"] is False


@pytest.mark.parametrize("text", ["#abc", "abc", "#aabbcc", "AABBCC"])
def test_parse_hex_accepts_short_long_and_hashless(text):
    assert contrast.parse_hex(text) == (170, 187, 204)


@pytest.mark.parametrize("text", ["#abcd", "xyz", "", "#12345g"])
def test_parse_hex_rejects_bad_input(text):
    with pytest.raises(ValueError):
        contrast.parse_hex(text)


def test_cli_prints_one_line_per_pair(capsys):
    exit_code = contrast.main(["#000", "#fff", "#777", "#fff"])

    lines = capsys.readouterr().out.splitlines()
    assert exit_code == 0
    assert lines[0] == (
        "#000 on #fff: 21.00:1  AA normal PASS  AA large PASS  AAA normal PASS  AAA large PASS"
    )
    assert lines[1] == (
        "#777 on #fff: 4.48:1  AA normal FAIL  AA large PASS  AAA normal FAIL  AAA large FAIL"
    )


def test_cli_json_lists_objects(capsys):
    exit_code = contrast.main(["#000", "#fff", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == [
        {
            "fg": "#000",
            "bg": "#fff",
            "ratio": 21.0,
            "aa_normal": True,
            "aa_large": True,
            "aaa_normal": True,
            "aaa_large": True,
        }
    ]


def test_cli_odd_colour_count_exits_2(capsys):
    exit_code = contrast.main(["#000"])

    assert exit_code == 2
    assert "pairs" in capsys.readouterr().err


def test_cli_bad_hex_exits_2(capsys):
    exit_code = contrast.main(["#000", "nope"])

    assert exit_code == 2
    assert "not a hex colour" in capsys.readouterr().err
