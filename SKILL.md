---
name: levels-charts
description: >-
  Generate Levels.fyi-branded editorial data visualizations (social-ready PNG
  charts) from any dataset, in the clean Ramp-style layout — bold title, gray
  subtitle, direct-labeled chart, source line, and Levels logo watermark on a
  cream background — then run a visual QA review pass. Use when turning data or
  stats into polished branded charts, when the user says "make a chart in the
  Levels style", "editorial chart", "social chart", "chart pack", or asks to
  review/fix chart formatting.
---

# Levels.fyi editorial charts

Produce social-ready, on-brand charts (**square 1080×1080 by default**, or 4:5
1080×1350) that look like the Ramp "editorial" style: a bold headline, a
one/two-line gray subtitle, a clean direct-labeled chart that sits right under
the subtitle, and a footer with the source line bottom-left and the Levels logo
watermark bottom-right — all on the cream brand background. Then **review every
chart visually and fix issues**.

## When to use
Any time the user wants data turned into branded visuals: a single chart, a
themed pack (like the comp-stories pack), or a "review/fix the formatting" pass
on charts already made with this skill.

## How it works
You write a short Python script that imports the bundled engine
(`lib/levels_charts.py`) and calls `new_canvas(...)` + one builder per chart.
The engine owns ALL the styling (fonts, colors, layout, footer, logo) so charts
come out consistent. You only supply the headline, subtitle, source, and data.

The engine is **fully self-contained**: it loads its own Nunito fonts and the
bundled Levels logo PNG from this skill's `assets/` (resolved relative to the
library file), so it works from any working directory / any project. **Runtime
deps are pure-pip only — `matplotlib`, `numpy`, `Pillow`. No native libraries,
no cairo, no node.** (`ffmpeg` is optional and used only for the bonus MP4 export
of an animation; every PNG and GIF renders without it. `cairosvg` is no longer
required — it's only an optional fallback if the bundled logo PNG is ever
deleted.)

## Workflow (follow in order)

1. **Setup (once per machine).** Assets are bundled. If `lib/levels_charts.py`
   raises a missing-assets error, run `bash scripts/setup_assets.sh`.

2. **Story-first.** For each chart decide the ONE comparison it makes, then write:
   a punchy **title** (≤2 lines), a **subtitle** (≤2 lines) that states the takeaway,
   and a **source** line. Lead with the insight, like a newsroom chart.

3. **Pick the builder** from the table below by data shape.

4. **Write the render script** (see skeleton). Output is **square 1080×1080 @2×
   by default** (most social-friendly); for the taller 4:5 layout call
   `set_format("portrait")` right after import. In square, keep it clean — fold
   takeaways into the subtitle and drop standalone prose annotations so the chart
   dominates (a sparse 2-bar chart is the one exception). Save PNGs to a project
   folder (e.g. `~/Downloads/<name>/`).

5. **Render:** `python3 your_script.py`.

6. **REVIEW (required).** Render, then **Read every output PNG** and check it
   against `references/review_checklist.md`. Fix and re-render until all pass.
   For a pack of **>3 charts** or anything high-stakes, spin up a subagent for a
   fresh-eyes QA pass using the review brief in that file (this is how the
   reference comp-pack was finished). Don't report done until you've *looked*.

7. **Deliver:** list the output files and a one-line summary per chart.

## Chart types → builder
| Data shape / story | Builder | Notes |
|---|---|---|
| Trend over time, multiple series | `line` | Direct end-of-line labels (the canonical Ramp look). Use `label_offsets` to de-collide close labels. |
| Compare a metric across categories | `vbar` | Single series; supports negatives (labels flip below 0). |
| Two+ series side by side per category | `grouped_vbar` | Optional per-group `delta` callout + auto in-plot legend. |
| Ranking / leaderboard | `hbar` | Highest first; optional dashed `divider_after` + label to set a "for reference" group apart. |
| Spread / range / distribution by group | `dumbbell` | Accepts `[lo,hi]`, `[lo,med,hi]`, or `[p10,p25,p50,p75,p90]`; optional vertical `refs`. |
| Pay ranges by company (raw points) | `company_strip` | One row per company: jittered raw submissions + IQR box + median, with brand logos as row labels. Use `company_logo(domain)` + `rgb_str(company.color)`; portrait format suits 6+ rows. Logos need a free `LOGO_DEV_TOKEN` (fetched on demand; falls back to text labels) — see `references/company-logos.md`. |
| One grant repriced by the stock (Original vs Current) | `grant_growth` | Two stacked bars (base/bonus/equity) where the equity towers in the 'now' bar. Has an animated twin `animate_grant_growth` (stock segment grows along the real price path). |
| A bouncing value over time (periodic) | `bars_line` | Periodic bars + a trend line over the tops (e.g. a stock-driven grant by quarter). Animated twin `animate_bars_line` reveals bars left-to-right with the line drawing across them — use this instead of a single growing bar when the series is volatile. |
| Part-to-whole across rows | `stacked100` | 100%-stacked; in-plot legend; give `top_pad`/`bottom_pad` for legend/notes. |
| Two-axis relationship | `scatter` | Labeled points; set your own limits/ticks. |

## Minimal skeleton
```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/levels-charts/lib"))
from levels_charts import *           # new_canvas, save, builders, colors, money/pct
# Square 1080x1080 is the default. For the 4:5 portrait layout: set_format("portrait")

OUT = os.path.expanduser("~/Downloads/my-charts")

fig, ax = new_canvas(
    "Headline that states the takeaway",            # ≤2 lines (use \n)
    "A subtitle that explains the chart in one or\ntwo lines, in gray.",
    "Source: <where the data came from>.",
    left=VBAR_LEFT, width=VBAR_W)                    # preset for the builder
grouped_vbar(ax, ["L1","L2","L3","L4","L5"],
    [("Baseline",[160,212,281,373,496],GRAYBAR),
     ("Specialist",[185,258,361,505,706],BLUE)],
    delta=[16,22,28,35,43], delta_fmt=lambda d:f"+{d}%")
save(fig, os.path.join(OUT, "01_my_chart.png"))
```
See `examples/example_pack.py` for one worked chart per builder — copy it.

## House rules (the engine enforces the look; you keep these)
- **Never hardcode the plot rectangle.** `new_canvas()` derives the chart top from
  the header so it sits tight under the subtitle. Only pass `left`/`width`
  (the `VBAR_/RANGE_/HBAR_` presets) and, rarely, `bottom`.
- **Legends go INSIDE the plot**, never above (they'd collide with the subtitle).
  `grouped_vbar`/`stacked100` handle this; for manual legends give the axes ylim
  headroom and use `legend_row(ax, …)` / `legmark`.
- **Footer is automatic and sectioned**: source wraps bottom-left, logo bottom-right.
  Keep the source short; don't place chart annotations in the bottom ~11% band.
- **Notes/annotations** belong in the chart's own empty space via `ax.text(...,
  transform=ax.transAxes, ...)`, not in the footer.
- **Titles ≤2 lines, subtitles ≤2 lines.** Longer headers eat the chart.
- **Money** via `money()` (thousands → `$160K`/`$1.02M`); **percents** via `pct()`
  (uses a real − minus). `$` is safe in any text (`text.parse_math` is off).
- **Be honest with data**: flag small samples in the source line; label estimates
  as "(est.)"; cite non-Levels figures.
- Colors: brand palette only (`BLUE`, `NAVY`, `GREEN`, `AMBER`, `RED`, `SKY`,
  `SLATEBAR`, `GRAYBAR`, plus `INK`/`SUB`/`MUTE` for text). `PALETTE` = default
  multi-series order. Full reference in `references/brand.md`.

## Formats
- **`square` (1080×1080 @2×) — DEFAULT.** Densest, most social-friendly; header
  condensed at top, chart fills the frame. Drop standalone prose annotations
  here (fold the point into the subtitle) so the chart dominates.
- **`portrait` (1080×1350 @2×)** — the original 4:5 layout, more vertical room for
  in-chart notes. Switch with `set_format("portrait")` right after import,
  before any `new_canvas`.
- Both formats share the same width, builders, and palette — only the vertical
  rhythm differs (`_FORMATS` in `lib/levels_charts.py`). Regenerate brand assets
  anywhere with `bash scripts/setup_assets.sh`.

## Animated GIFs
Turn a chart into a social GIF in the same editorial look (cream, Nunito, logo).
All animators live in `lib/levels_charts_anim.py`; each dumps `_start/_mid/_final.png`
QA frames with `qa_frames=True`. Full guide + worked examples in
`references/animation.md`. Pick by what the data is doing:

| Story | Animator | Motion |
|---|---|---|
| One value over time (IPO / valuation / a grant repriced) | `animate_value_line` | Line draws itself; value tag climbs on the tip; `vmarkers` milestones fade in; settles on `end_label`. |
| **Stock vs benchmark ("hold vs sell-and-index")** | **`animate_gap_race`** | **Two lines race out together; the gap shades green where the stock leads, amber where the benchmark leads; a color-coded scoreboard counts both up; optional `gap_glow` flash finale.** |
| Compare a metric across levels/categories | `animate_grouped_vbar` | Bars ease up one category at a time; labels + deltas fade in as each lands. |
| A volatile value over time (grant repriced per quarter) | `animate_bars_line` | Periodic bars reveal L→R with a line drawing across their tops. |
| One grant, "watch the equity grow" | `animate_grant_growth` | An "at offer" bar and a "today" bar whose stock segment grows along the real price path. |

```python
from levels_charts import *                          # colors, money, presets
from levels_charts_anim import animate_gap_race
animate_gap_race("out.gif", title="...", subtitle="...", source="...",
    x=[2022.95, 2023.95, 2024.95, 2025.95, 2026.55],
    stock=[200, 317, 357, 412, 340], bench=[200, 234, 312, 344, 390],  # value_fmt units
    stock_name="Microsoft, held", bench_name="S&P 500",
    stock_color=BLUE, bench_color=INK, value_fmt=money,
    xticks=[2023,2024,2025,2026], ymin=0, ymax=460, yticks=[0,100,200,300,400],
    yticklabels=["$0","$100K","$200K","$300K","$400K"],
    gap_note="about $50K\nleft on the table",         # settled callout on the final gap
    gap_glow=True, seconds=2.5, fps=25, hold=3.0, px=900, qa_frames=True)
```

### Creative touches (opt-in, all backward-compatible)
- **`animate_value_line`** takes `logo=company_logo("microsoft.com")` + `logo_at="header"`
  (top-right by the title) or `"plot_tr"` (inside the chart) to brand a frame; and
  `vmarkers` entries accept an optional 4th element `"right"` to put a milestone label
  on the right of its line so it clears the `start_note`.
- **`animate_gap_race`** shades the lead/deficit automatically (`ahead_color`/`behind_color`),
  keeps the climbing numbers in a non-colliding scoreboard, and `gap_glow=True` flashes the
  final gap to punctuate it.

### Pacing (this is what makes it feel good)
- **`seconds`** = draw time, **`fps`** = smoothness, **`hold`** = seconds the finished
  frame rests before looping. Total loop ≈ `seconds + hold`.
- **Punchy / social default: `seconds≈2.3–2.6`, `fps=25`.** The first slow pass we shipped
  (`seconds=4.6, fps=20`) read as sluggish — prefer the faster settings.
- **Hold long enough to read the end state.** Bump `hold` to **2.5–3.0** so viewers absorb the
  final numbers; it costs ~0 bytes (one long-duration frame, not duplicated frames).
- **Size:** ~900px/25fps/2.5s ≈ 3–5 MB (LinkedIn posts GIFs directly). Shrink via `px`,
  `palette_colors`, or `seconds`.

Build the matching **static** chart first as the composition reference. REVIEW is still
required: `Read` the QA frames — the **final** must match the static; **start/mid**
legitimately have empty upper space (the line is still climbing, *not* the empty-band
defect). Preview the `.gif` in a **browser** (Finder/Preview may show one frame).

### Sample prompts (that produced the shipped work)
- "Turn this into a fast-paced animated GIF — line draws itself, the value climbs on the tip,
  and the acquisition date fades in as a milestone." → `animate_value_line`
- "Animate hold-vs-index: race the Microsoft grant against the S&P 500, shade the gap, and
  flash the amount left on the table at the end." → `animate_gap_race` with `gap_glow`
- "Make it faster than the last one and pause longer on the end so people can read it."
  → lower `seconds` / raise `fps`, raise `hold`
- "Add the company logo to the top-right of the animation." → `logo=` + `logo_at="header"`

## Files in this skill
- `lib/levels_charts.py` — the engine: `new_canvas`, `clean`, `legmark`,
  `legend_row`, `save`, `money`, `pct`, `company_logo` (fetch+cache a brand logo by
  domain via logo.dev), `rgb_str` (Levels `company.color` "r,g,b" → hex), and builders
  `line / vbar / grouped_vbar / hbar / dumbbell / stacked100 / scatter / company_strip / grant_growth / bars_line`.
  Also `logo_color(arr)` (dominant brand color from a logo). NOTE: Levels `company.color` is
  an ARRAY (`[94,115,224]`) — `rgb_str` handles list / "r,g,b" / "[r, g, b]" forms.
- `lib/levels_charts_anim.py` — animation sub-engine (GIFs): `animate_value_line` (+ optional
  `logo`/`logo_at` and `vmarkers` right-side labels), `animate_gap_race` (two-line hold-vs-index
  race with gap shading, scoreboard, `gap_glow` finale), `animate_grouped_vbar`,
  `animate_grant_growth`, `animate_bars_line`. Optional `ffmpeg`-only MP4 export degrades gracefully.
- `assets/` — bundled Nunito + JetBrains Mono fonts and the Levels logo **PNG** (loaded at runtime,
  no native deps) + its source SVG. Company logos are fetched on demand via logo.dev
  (needs `LOGO_DEV_TOKEN`), cached in `assets/company_logos/` — see `references/company-logos.md`.
- `examples/example_pack.py` — one worked chart per builder (copy as a template).
- `examples/example_anim.py` — worked animated value-over-time GIF (copy as a template).
- `examples/example_strip.py` — worked `company_strip` pay-ranges-by-company chart.
- `references/brand.md` — palette, fonts, layout constants, density rules.
- `references/animation.md` — animated-GIF sub-skill guide (`animate_value_line`).
- `references/review_checklist.md` — QA acceptance criteria + subagent review brief.
- `scripts/setup_assets.sh` — re-fetch/instance fonts + logo if `assets/` is missing.
