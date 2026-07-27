# AGENTS.md — levels-charts

Instructions for any AI coding agent (Codex, Cursor, Claude Code, Gemini CLI, …)
working in or with this repo. This repo is a **charting skill/library**: it turns
datasets into social-ready, on-brand Levels.fyi editorial charts (PNG) and animated
GIFs, in a clean Ramp-style layout. The full operating manual is
[`skills/levels-charts/SKILL.md`](skills/levels-charts/SKILL.md) — read it first.

## What it is
- A self-contained Python engine (matplotlib) + Markdown instructions.
- Pure-pip runtime: `matplotlib`, `numpy`, `Pillow`. No native libs (no cairo, no node).
- Bundled brand fonts + Levels logo, so charts come out on-brand from any directory.

## Setup
```
python3 -m pip install matplotlib pillow numpy fonttools
```
Optional: `ffmpeg` on `PATH` for MP4 export; `LOGO_DEV_TOKEN` for company logos
(see `skills/levels-charts/references/company-logos.md`).

## Use it (the pattern)
Point Python at the engine, then call `new_canvas(...)` + one builder:
```python
import sys, os
sys.path.insert(0, "skills/levels-charts/lib")   # from a clone of this repo
from levels_charts import *
fig, ax = new_canvas("Headline that states the takeaway",
                     "A subtitle that explains the chart, in gray.",
                     "Source: <where the data came from>.",
                     left=VBAR_LEFT, width=VBAR_W)
vbar(ax, ["L1","L2","L3"], [160, 212, 281], BLUE)
save(fig, "out/chart.png")
```
Builders: `line / vbar / grouped_vbar / hbar / dumbbell / stacked100 / scatter /
company_strip / grant_growth / bars_line`. Animated GIFs are in
`levels_charts_anim.py` (`animate_value_line`, `animate_gap_race`, …).

## Workflow (follow SKILL.md)
1. **Story-first:** one punchy title, a subtitle that states the takeaway, a source line.
2. **Pick the builder** by data shape (table in SKILL.md).
3. **Render:** `python3 your_script.py`.
4. **REVIEW (required):** open every output PNG and check it against
   `skills/levels-charts/references/review_checklist.md`; fix and re-render until clean.

## Rules
- Titles ≤2 lines, subtitles ≤2 lines. Legends go INSIDE the plot. Brand palette only.
- Format with `money()` / `pct()`. Nunito lacks arrow glyphs (`→`) — use words.
- Be honest with data: flag small samples, mark estimates, cite non-Levels sources.

Full detail — every builder, formats, the animation guide, brand tokens — lives under
`skills/levels-charts/` (`SKILL.md` + `references/`).
