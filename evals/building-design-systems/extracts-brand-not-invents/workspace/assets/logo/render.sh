#!/usr/bin/env bash
# Export PNG variants of the logo for the README, social cards and the favicon.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
for size in 32 180 512; do
  rsvg-convert -w "$size" lumen-mark.svg > "out/lumen-mark-$size.png"
done
rsvg-convert -w 960 lumen-wordmark.svg > out/lumen-wordmark-960.png
# Social card: wordmark on paper.
rsvg-convert -w 1200 -b '#F4F1EC' lumen-wordmark.svg > out/lumen-social.png
