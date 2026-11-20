#!/usr/bin/env python3
"""
Prepare screenshots for vision-model critique: fit, split tall pages, overlay a labelled grid.

Each image is shrunk to fit --max-width (never enlarged), cut into parts that fit
--max-height, and each part gets a margin on every side holding column labels (A-H)
above and below and row labels (1-8) left and right. Thin translucent lines divide the
content into cols x rows cells; nothing else is drawn over the content. The margin is reserved
inside the limits, so outputs are at most --max-width wide and --max-height tall.

Usage:
    grid.py IMAGE [IMAGE ...] --out-dir DIR [--max-width 1280] [--max-height 2000]
            [--cols 8] [--rows 8]
Prints one output path per line: <stem>.png, or <stem>-part1.png, -part2.png ... when split.
Exit codes: 0 ok; 2 bad input, duplicate output names or Pillow missing.
"""

from __future__ import annotations

import argparse
import math
import string
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError:
    print("error: Pillow is required; run: pip install pillow", file=sys.stderr)
    sys.exit(2)

MARGIN = 24
LINE_ALPHA = 69  # about 27% opacity: visible without hiding content
DARK_LINE = (0, 0, 0)  # neutral, so models don't read the grid as a design colour
LIGHT_LINE = (255, 255, 255)
LABEL_COLOR = (60, 60, 60)
LABEL_SIZE = 12
CANVAS_COLOR = (255, 255, 255)

Bounds = tuple[int, int, int, int]


def fit_width(image: Image.Image, max_width: int) -> Image.Image:
    """Shrink to at most max_width keeping aspect ratio; never upscale."""
    if image.width <= max_width:
        return image
    height = max(1, round(image.height * max_width / image.width))
    return image.resize((max_width, height), Image.Resampling.LANCZOS)


def split_heights(height: int, max_height: int) -> list[tuple[int, int]]:
    """Return (top, bottom) row ranges covering height in equal parts of at most max_height."""
    part_count = math.ceil(height / max_height)
    part_height = math.ceil(height / part_count)
    return [(top, min(top + part_height, height)) for top in range(0, height, part_height)]


def _edges(length: int, count: int) -> list[int]:
    """Return count + 1 evenly spaced integer boundaries from 0 to length."""
    return [round(length * index / count) for index in range(count + 1)]


def cell_bounds(
    width: int, height: int, cols: int, rows: int, margin: int = MARGIN
) -> dict[str, Bounds]:
    """Map cell names like "A1" to (left, top, right, bottom) in the margin-padded image.

    Columns are lettered from A, rows numbered from 1. Content starts at (margin, margin).
    """
    column_edges = _edges(width, cols)
    row_edges = _edges(height, rows)
    return {
        f"{string.ascii_uppercase[col]}{row + 1}": (
            margin + column_edges[col],
            margin + row_edges[row],
            margin + column_edges[col + 1],
            margin + row_edges[row + 1],
        )
        for row in range(rows)
        for col in range(cols)
    }


def line_color(canvas: Image.Image) -> tuple[int, int, int]:
    """Pick white lines on a dark design and black lines on a light one."""
    mean_luminance = ImageStat.Stat(canvas.convert("L")).mean[0]
    return LIGHT_LINE if mean_luminance < 128 else DARK_LINE


def _draw_lines(
    canvas: Image.Image, width: int, height: int, cols: int, rows: int, margin: int
) -> Image.Image:
    """Blend the cell dividers over the content area of canvas."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    color = (*line_color(canvas), LINE_ALPHA)
    for edge in _edges(width, cols)[1:-1]:
        line_x = margin + min(edge, width - 1)
        draw.line([(line_x, margin), (line_x, margin + height - 1)], fill=color)
    for edge in _edges(height, rows)[1:-1]:
        line_y = margin + min(edge, height - 1)
        draw.line([(margin, line_y), (margin + width - 1, line_y)], fill=color)
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _draw_labels(
    canvas: Image.Image, width: int, height: int, cols: int, rows: int, margin: int
) -> None:
    """Write column letters in the top and bottom margins and row numbers in the side margins."""
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=LABEL_SIZE)
    column_edges = _edges(width, cols)
    row_edges = _edges(height, rows)
    for col in range(cols):
        center_x = margin + (column_edges[col] + column_edges[col + 1]) / 2
        letter = string.ascii_uppercase[col]
        for center_y in (margin / 2, margin + height + margin / 2):
            draw.text((center_x, center_y), letter, fill=LABEL_COLOR, font=font, anchor="mm")
    for row in range(rows):
        center_y = margin + (row_edges[row] + row_edges[row + 1]) / 2
        for center_x in (margin / 2, margin + width + margin / 2):
            draw.text((center_x, center_y), str(row + 1), fill=LABEL_COLOR, font=font, anchor="mm")


def add_grid(image: Image.Image, cols: int = 8, rows: int = 8, margin: int = MARGIN) -> Image.Image:
    """Return image padded with a labelled margin and divided by translucent grid lines."""
    source = image.convert("RGB")
    width, height = source.size
    canvas = Image.new("RGB", (width + 2 * margin, height + 2 * margin), CANVAS_COLOR)
    canvas.paste(source, (margin, margin))
    canvas = _draw_lines(canvas, width, height, cols, rows, margin)
    _draw_labels(canvas, width, height, cols, rows, margin)
    return canvas


def process_image(path: Path, out_dir: Path, args: argparse.Namespace) -> list[Path]:
    """Fit, split and grid one image file; return the written paths."""
    with Image.open(path) as opened:
        fitted = fit_width(opened.convert("RGB"), args.max_width - 2 * MARGIN)

    ranges = split_heights(fitted.height, args.max_height - 2 * MARGIN)
    written = []
    for number, (top, bottom) in enumerate(ranges, start=1):
        part = fitted.crop((0, top, fitted.width, bottom))
        name = f"{path.stem}.png" if len(ranges) == 1 else f"{path.stem}-part{number}.png"
        target = out_dir / name
        add_grid(part, cols=args.cols, rows=args.rows).save(target)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="Overlay a labelled grid on screenshots.")
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-width", type=int, default=1280)
    parser.add_argument("--max-height", type=int, default=2000)
    parser.add_argument("--cols", type=int, default=8)
    parser.add_argument("--rows", type=int, default=8)
    args = parser.parse_args(argv)

    if not 1 <= args.cols <= len(string.ascii_uppercase) or args.rows < 1:
        print("error: --cols must be 1-26 and --rows at least 1", file=sys.stderr)
        return 2
    if args.max_width <= 2 * MARGIN or args.max_height <= 2 * MARGIN:
        print(f"error: --max-width and --max-height must exceed {2 * MARGIN}", file=sys.stderr)
        return 2
    stems = [path.stem for path in args.images]
    duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
    if duplicates:
        print(
            f"error: inputs share a file stem and would overwrite each other: "
            f"{', '.join(duplicates)}; rename them",
            file=sys.stderr,
        )
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for path in args.images:
            for written in process_image(path, args.out_dir, args):
                print(written)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
