#!/usr/bin/env bash
# Bootstrap the Levels.fyi chart assets: Nunito + JetBrains Mono static weights
# and the Levels logo. Idempotent — no-ops if assets are already present.
#
# The engine is self-contained at RUNTIME: it needs only pip packages
# (matplotlib, numpy, Pillow) and loads the bundled logo PNG — no native libs,
# no cairo, no node. This script only regenerates assets if they were deleted.
# Needs: python3 (+pip for fonttools), curl, internet. cairosvg is OPTIONAL and
# only used here to (re)build the logo PNG from the SVG if the PNG is missing.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS="$SKILL_DIR/assets/fonts"
LOGO_SVG="$SKILL_DIR/assets/levels_logo_grey.svg"
LOGO_PNG="$SKILL_DIR/assets/levels_logo_grey.png"
mkdir -p "$FONTS"

if [ -f "$FONTS/Nunito-800.ttf" ] && [ -f "$LOGO_PNG" ]; then
  echo "Assets already present — nothing to do."
  exit 0
fi

# ---- fonts (instanced from Google's variable fonts) ------------------------
if [ ! -f "$FONTS/Nunito-800.ttf" ]; then
  echo "Installing fonttools…"
  python3 -m pip install -q fonttools >/dev/null 2>&1 || true
  echo "Downloading variable fonts…"
  curl -fsSL "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf" -o "$FONTS/Nunito-var.ttf"
  curl -fsSL "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf" -o "$FONTS/JBMono-var.ttf"
  echo "Instancing static weights…"
  for w in 400 600 700 800 900; do
    python3 -m fontTools.varLib.instancer "$FONTS/Nunito-var.ttf" wght=$w -o "$FONTS/Nunito-$w.ttf" >/dev/null 2>&1
  done
  for w in 500 700; do
    python3 -m fontTools.varLib.instancer "$FONTS/JBMono-var.ttf" wght=$w -o "$FONTS/JBMono-$w.ttf" >/dev/null 2>&1
  done
  rm -f "$FONTS/Nunito-var.ttf" "$FONTS/JBMono-var.ttf"
fi

# ---- logo: bundled PNG is primary; rebuild from SVG only if it's missing ----
if [ ! -f "$LOGO_PNG" ]; then
  [ -f "$LOGO_SVG" ] || { echo "Fetching logo SVG…"; \
    curl -fsSL --compressed "https://www.levels.fyi/assets/logo/full_grey/full_logo.svg" -o "$LOGO_SVG"; }
  echo "Rasterizing logo PNG…"
  python3 - "$LOGO_SVG" "$LOGO_PNG" <<'PY' || \
    echo "  (cairosvg not installed — skipped; the engine will rasterize the SVG on demand if cairosvg is later available, or just re-bundle levels_logo_grey.png)"
import sys, io
try:
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(url=sys.argv[1], output_width=1080)
    Image.open(io.BytesIO(png)).convert("RGBA").save(sys.argv[2])
    print("  wrote", sys.argv[2])
except Exception as e:
    raise SystemExit(1)
PY
fi

echo "Done. Fonts in $FONTS:"
ls -1 "$FONTS"
