#!/bin/bash
# Generate favicon.png from source favicon image
# Resizes to 52x52, pads to 64x64 with dark bg, rounds corners, transparent outside

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"

SRC="$DIR/favicon.png"
OUT="$ROOT/static/favicon.png"

magick "$SRC" \
  -resize 41x41 \
  -gravity center -background "#0a0a23" -extent 64x64 \
  \( +clone -alpha extract -fill black -colorize 100 \
     -fill white -draw "roundrectangle 0,0,63,63,12,12" \) \
  -alpha off -compose CopyOpacity -composite \
  PNG32:"$OUT"

echo "Created $OUT"
