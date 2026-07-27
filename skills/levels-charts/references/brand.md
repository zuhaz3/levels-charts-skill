# Levels.fyi chart brand reference

The engine (`lib/levels_charts.py`) bakes all of this in. This file documents the
system so you can extend it deliberately and stay on-brand.

## Canvas
- **Formats** (`set_format(...)`, both share the same width): `square` **default**
  → **2160 × 2160 px** (1080² @2×, social-friendly, condensed header); `portrait`
  → **2160 × 2700 px** (1080×1350, 4:5). Defined in `_FORMATS` in the engine.
- **Background:** cream `#F4F3EC` (figure and axes).
- **Vertical structure (figure fraction):** title block at top (`TITLE_Y≈0.957`)
  → subtitle below it → chart top auto-derived ~`0.028` under the subtitle → chart
  fills down to ~`0.135` → **footer band** `y∈[0.035, 0.11]`: source line
  bottom-left, logo bottom-right. The chart must sit *tight* under the subtitle —
  no large empty band (this is the #1 thing to get right).

## Type
- **Font:** Nunito (bundled weights 400/600/700/800/900). JetBrains Mono
  (500/700) is bundled for an optional "data" register but the default look is
  Nunito throughout, like the reference.
- **Title:** Nunito **800**, 35pt, ink `#1A1712`, ≤2 lines.
- **Subtitle:** Nunito 600, 18pt, slate `#5B6268`, ≤2 lines.
- **Category labels:** Nunito 800, 18pt, ink. **Axis ticks:** 15pt, `#7C8288`.
- **Data labels:** Nunito 700–800, 12–16pt, usually the series color.
- **Source:** Nunito 600, 11.5pt, muted `#A39C90`, bottom-left, auto-wrapped.

## Palette
| Token | Hex | Use |
|---|---|---|
| `INK` | `#1A1712` | title, category labels, "hero" series |
| `SUB` | `#5B6268` | subtitle, in-chart notes |
| `MUTE` | `#A39C90` | source line, de-emphasized labels |
| `GRID` | `#DCD9CE` | gridlines |
| `CREAM` | `#F4F3EC` | background |
| `BLUE` | `#0060B9` | primary brand / main series |
| `NAVY` | `#00407B` | emphasis / top item |
| `SKY` | `#4F9BDC` | secondary blue |
| `GREEN` | `#1E9E6A` | positive / "good" |
| `AMBER` | `#E08A1E` | warning / "locked" / contrast |
| `RED` | `#D1495B` | negative / "for reference" / alarm |
| `SLATEBAR` | `#808C93` | neutral series |
| `GRAYBAR` | `#CBC5B6` | baseline / muted bar |
| `PALE` | `#E6F1FB` | pale fills |

`PALETTE = [BLUE, AMBER, GREEN, NAVY, RED, SKY, SLATEBAR, GRAYBAR]` is the default
order for multi-series charts.

## Chart conventions (the editorial look)
- No chart borders/spines. **Light horizontal grid only** for value axes
  (`clean(ax, grid="x"|"y")`); none on category axes.
- **Direct labels over legends** wherever possible (label the line end / the bar).
  When a legend is needed, put it **inside** the plot's empty space.
- Rounded bar/line caps; generous spacing; let the chart breathe but fill the canvas.
- One idea per chart. The subtitle states the takeaway; the chart proves it.

## Logo
- Bundled as `assets/levels_logo_grey.png` (slate wordmark + staircase mark), loaded
  with Pillow and placed as a 360px-wide watermark, bottom-right, ~0.95 alpha. Don't
  distort or recolor it. (`levels_logo_grey.svg` is kept only as the source / optional
  cairosvg fallback — the engine needs no native libs at runtime.)

## Layout constants (figure fraction)
`LEFT=0.072` (text margin) · `TITLE_Y=0.957` · `TITLE_LH=0.0515` · `SUB_GAP=0.024`
· `SUB_LH=0.0212` · `PLOT_GAP=0.028` · `FOOTER_TOP=0.11` · `SRC_Y=0.052`.
Plot box presets: `VBAR_LEFT/W=0.085/0.86`, `RANGE_LEFT/W=0.105/0.80`,
`HBAR_LEFT/W=0.165/0.66`.
