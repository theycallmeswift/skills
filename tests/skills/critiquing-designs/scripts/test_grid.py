"""Tests for grid.py and contact_sheet.py: geometry, no-upscale, margins, untouched content."""

from __future__ import annotations

from pathlib import Path

import contact_sheet
import grid
from PIL import Image


def gray_image(width: int, height: int) -> Image.Image:
    """Build a flat mid-gray RGB image so any blended line pixel differs visibly."""
    return Image.new("RGB", (width, height), (128, 128, 128))


def test_fit_width_shrinks_keeping_aspect():
    fitted = grid.fit_width(gray_image(2560, 1000), 1280)

    assert fitted.size == (1280, 500)


def test_fit_width_never_upscales():
    image = gray_image(400, 300)

    fitted = grid.fit_width(image, 1280)

    assert fitted.size == (400, 300)


def test_split_heights_single_part_when_short():
    assert grid.split_heights(1500, 2000) == [(0, 1500)]


def test_split_heights_balances_parts_and_covers_everything():
    ranges = grid.split_heights(4500, 2000)

    assert ranges == [(0, 1500), (1500, 3000), (3000, 4500)]


def test_split_heights_never_exceeds_max_and_is_contiguous():
    ranges = grid.split_heights(4001, 2000)

    assert all(bottom - top <= 2000 for top, bottom in ranges)
    assert ranges[0][0] == 0
    assert ranges[-1][1] == 4001
    assert all(ranges[index][1] == ranges[index + 1][0] for index in range(len(ranges) - 1))


def test_cell_bounds_tile_the_content_area_inside_the_margin():
    bounds = grid.cell_bounds(width=800, height=400, cols=8, rows=8)

    assert len(bounds) == 64
    assert bounds["A1"] == (24, 24, 124, 74)
    assert bounds["H8"] == (24 + 700, 24 + 350, 24 + 800, 24 + 400)
    assert min(left for left, _, _, _ in bounds.values()) == 24
    assert max(right for _, _, right, _ in bounds.values()) == 24 + 800
    assert max(bottom for _, _, _, bottom in bounds.values()) == 24 + 400


def test_cell_bounds_names_columns_by_letter_and_rows_by_number():
    bounds = grid.cell_bounds(width=300, height=200, cols=3, rows=2)

    assert sorted(bounds) == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert bounds["B2"] == (24 + 100, 24 + 100, 24 + 200, 24 + 200)


def test_add_grid_pads_24px_on_every_side():
    gridded = grid.add_grid(gray_image(640, 480))

    assert gridded.size == (640 + 48, 480 + 48)


def test_add_grid_leaves_content_untouched_except_grid_lines():
    original = gray_image(640, 480)
    expected_line_columns = {24 + edge for edge in (80, 160, 240, 320, 400, 480, 560)}
    expected_line_rows = {24 + edge for edge in (60, 120, 180, 240, 300, 360, 420)}

    gridded = grid.add_grid(original, cols=8, rows=8)

    changed = {
        (pixel_x, pixel_y)
        for pixel_x in range(24, 24 + 640)
        for pixel_y in range(24, 24 + 480)
        if gridded.getpixel((pixel_x, pixel_y)) != original.getpixel((pixel_x - 24, pixel_y - 24))
    }
    assert changed
    assert all(
        pixel_x in expected_line_columns or pixel_y in expected_line_rows
        for pixel_x, pixel_y in changed
    )
    assert {pixel_x for pixel_x, _ in changed} >= expected_line_columns
    assert {pixel_y for _, pixel_y in changed} >= expected_line_rows


def test_add_grid_lines_are_translucent():
    gridded = grid.add_grid(gray_image(640, 480))

    red, green, blue = gridded.crop((24 + 80, 24 + 10, 24 + 81, 24 + 11)).tobytes()
    assert (red, green, blue) != (128, 128, 128)
    assert red == green == blue
    assert 0 < red < 255


def test_line_color_is_neutral_and_contrasts_with_the_design():
    dark = Image.new("RGB", (100, 100), (20, 20, 20))
    light = Image.new("RGB", (100, 100), (240, 240, 240))

    assert grid.line_color(dark) == (255, 255, 255)
    assert grid.line_color(light) == (0, 0, 0)


def test_add_grid_draws_labels_only_in_the_margins():
    gridded = grid.add_grid(gray_image(640, 480))

    top_margin_ink = [
        gridded.getpixel((pixel_x, pixel_y)) != (255, 255, 255)
        for pixel_x in range(48, 640)
        for pixel_y in range(0, 24)
    ]
    left_margin_ink = [
        gridded.getpixel((pixel_x, pixel_y)) != (255, 255, 255)
        for pixel_x in range(0, 24)
        for pixel_y in range(48, 480)
    ]
    assert any(top_margin_ink)
    assert any(left_margin_ink)


def test_cli_writes_single_part_and_prints_path(tmp_path, capsys):
    source = tmp_path / "home.png"
    gray_image(2000, 900).save(source)
    out_dir = tmp_path / "out"

    exit_code = grid.main([str(source), "--out-dir", str(out_dir)])

    written = out_dir / "home.png"
    assert exit_code == 0
    assert capsys.readouterr().out.split() == [str(written)]
    assert Image.open(written).size == (1280 + 48, 576 + 48)


def test_cli_splits_tall_pages_into_numbered_parts(tmp_path, capsys):
    source = tmp_path / "long.png"
    gray_image(1280, 4000).save(source)
    out_dir = tmp_path / "out"

    exit_code = grid.main([str(source), "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert sorted(path.name for path in out_dir.iterdir()) == ["long-part1.png", "long-part2.png"]
    assert Image.open(out_dir / "long-part1.png").size == (1280 + 48, 2000 + 48)


def test_cli_missing_input_exits_2(tmp_path, capsys):
    exit_code = grid.main([str(tmp_path / "nope.png"), "--out-dir", str(tmp_path / "out")])

    assert exit_code == 2
    assert capsys.readouterr().err.startswith("error:")


def test_contact_sheet_combines_images_with_default_labels(tmp_path, capsys):
    paths = []
    for name in ("a", "b", "c", "d"):
        path = tmp_path / f"{name}.png"
        gray_image(600, 300).save(path)
        paths.append(str(path))
    out = tmp_path / "sheet.png"

    exit_code = contact_sheet.main([str(out), *paths, "--cols", "2", "--thumb-width", "200"])

    sheet = Image.open(out)
    assert exit_code == 0
    assert sheet.width == 16 + 2 * (200 + 16)
    assert sheet.height == 16 + 2 * (100 + 28 + 16)


def test_contact_sheet_label_count_mismatch_exits_2(tmp_path, capsys):
    path = tmp_path / "a.png"
    gray_image(100, 100).save(path)

    exit_code = contact_sheet.main([str(tmp_path / "sheet.png"), str(path), "--labels", "x,y"])

    assert exit_code == 2
    assert "labels" in capsys.readouterr().err


def test_contact_sheet_rejects_unreadable_image(tmp_path: Path, capsys):
    exit_code = contact_sheet.main([str(tmp_path / "sheet.png"), str(tmp_path / "missing.png")])

    assert exit_code == 2
