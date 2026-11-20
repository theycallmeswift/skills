#!/usr/bin/env python3
"""
Combine several images into one labelled contact sheet for side-by-side comparison.

Each thumbnail gets a caption strip underneath: its label (default 1, 2, 3...) and the
file stem.

Usage:
    contact_sheet.py OUT IMAGE [IMAGE ...] [--labels L1,L2,...] [--cols 3] [--thumb-width 480]
Exit codes: 0 ok; 2 bad input or Pillow missing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("error: Pillow is required; run: pip install pillow", file=sys.stderr)
    sys.exit(2)

CAPTION_HEIGHT = 28
GAP = 16
CANVAS_COLOR = (255, 255, 255)
CAPTION_COLOR = (30, 30, 30)
CAPTION_SIZE = 14


def make_thumbnail(path: Path, thumb_width: int) -> Image.Image:
    """Load an image scaled to thumb_width wide, keeping aspect ratio."""
    with Image.open(path) as opened:
        rgb = opened.convert("RGB")
    height = max(1, round(rgb.height * thumb_width / rgb.width))
    return rgb.resize((thumb_width, height), Image.Resampling.LANCZOS)


def build_sheet(paths: list[Path], labels: list[str], cols: int, thumb_width: int) -> Image.Image:
    """Lay out labelled thumbnails in a grid, each row as tall as its tallest thumbnail."""
    thumbnails = [make_thumbnail(path, thumb_width) for path in paths]
    rows = [thumbnails[start : start + cols] for start in range(0, len(thumbnails), cols)]
    row_heights = [max(thumb.height for thumb in row) + CAPTION_HEIGHT for row in rows]
    sheet_width = GAP + cols * (thumb_width + GAP)
    sheet = Image.new(
        "RGB", (sheet_width, GAP + sum(height + GAP for height in row_heights)), CANVAS_COLOR
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=CAPTION_SIZE)

    index = 0
    top = GAP
    for row, row_height in zip(rows, row_heights, strict=True):
        for column, thumb in enumerate(row):
            left = GAP + column * (thumb_width + GAP)
            sheet.paste(thumb, (left, top))
            caption = f"{labels[index]}  {paths[index].stem}"
            draw.text((left, top + thumb.height + 4), caption, fill=CAPTION_COLOR, font=font)
            index += 1
        top += row_height + GAP
    return sheet


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="Build a labelled contact sheet.")
    parser.add_argument("out", type=Path)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--labels", help="comma-separated labels, one per image")
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--thumb-width", type=int, default=480)
    args = parser.parse_args(argv)

    labels = (
        args.labels.split(",")
        if args.labels
        else [str(number) for number in range(1, len(args.images) + 1)]
    )
    if len(labels) != len(args.images):
        print(f"error: {len(labels)} labels for {len(args.images)} images", file=sys.stderr)
        return 2
    if args.cols < 1 or args.thumb_width < 1:
        print("error: --cols and --thumb-width must be positive", file=sys.stderr)
        return 2

    try:
        sheet = build_sheet(args.images, labels, args.cols, args.thumb_width)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.out)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
