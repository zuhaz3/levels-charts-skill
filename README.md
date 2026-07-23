# levels-charts — Levels.fyi editorial chart skill

A Claude Code (Agent) skill that turns any dataset into **social-ready,
on-brand Levels.fyi charts** — bold headline, gray subtitle, a clean
direct-labeled chart, a source line, and the Levels logo watermark on the cream
brand background — then runs a visual QA pass. Square 1080×1080 by default;
4:5 portrait available.

It's **fully self-contained**: the brand fonts (Nunito + JetBrains Mono) and the
Levels logo (bundled as a PNG) live in `assets/` and load relative to the code,
so it works from any directory with no downloads. **Runtime deps are pure-pip
only — no native libraries, no cairo, no node.**

## Install
1. Clone (or copy) this repo into your Claude Code skills directory as
   `levels-charts` — **the folder name must stay `levels-charts`**:
   ```
   git clone https://github.com/zuhaz3/levels-charts-skill.git ~/.claude/skills/levels-charts
   ```
   (macOS/Linux. Or download the ZIP and unzip it there.)
2. Install the Python dependencies (all pure-pip, no system libraries):
   ```
   python3 -m pip install matplotlib pillow numpy fonttools
   ```
   - `fonttools` is only used by `scripts/setup_assets.sh` to (re)build fonts if
     `assets/` is ever deleted — the fonts ship bundled, so it's optional.
   - **Optional extras:** `ffmpeg` (on `PATH`) enables the bonus MP4 export of an
     animation — every PNG and GIF renders without it. `cairosvg` is *not* needed;
     it's only an optional fallback if the bundled logo PNG is deleted.
   - **Company logos** (used as row labels in `company_strip` charts) are fetched on
     demand from [logo.dev](https://logo.dev) with your own free key — set
     `LOGO_DEV_TOKEN` in your env. Optional; charts fall back to text labels without it.
     See [`references/company-logos.md`](references/company-logos.md).
3. That's it. In Claude Code the skill auto-triggers on chart requests, or invoke
   it explicitly with `/levels-charts`. Ask for "Levels-style charts from this data".

## Quick test (no Claude needed)
```
cd ~/.claude/skills/levels-charts
python3 examples/example_pack.py /tmp/levels-charts-demo
open /tmp/levels-charts-demo            # macOS (or just browse the PNGs)
```
You should get one PNG per chart type (line, grouped bars, bars, leaderboard,
dumbbell, 100%-stacked).

## Using it in code
```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/levels-charts/lib"))
from levels_charts import *            # new_canvas, save, builders, colors, money/pct
# set_format("portrait")               # optional — 4:5 instead of the square default

fig, ax = new_canvas("Headline that states the takeaway",
                     "A one- or two-line subtitle in gray.",
                     "Source: <where the data came from>.")
vbar(ax, ["L1","L2","L3"], [160, 212, 281], BLUE)
save(fig, os.path.expanduser("~/Downloads/my-chart.png"))
```

## What's inside
- `SKILL.md` — the operating manual Claude reads (workflow, chart-type table, rules).
- `lib/levels_charts.py` — the engine: `new_canvas`, `clean`, `legmark`, `save`,
  `money`/`pct`, `set_format`, `company_logo`, and builders `line / vbar / grouped_vbar /
  hbar / dumbbell / stacked100 / scatter / company_strip / grant_growth / bars_line`.
- `lib/levels_charts_anim.py` — GIF animators: `animate_value_line`, `animate_gap_race`
  (hold-vs-index race with gap shading), `animate_grouped_vbar`, `animate_grant_growth`,
  `animate_bars_line`. See `references/animation.md`.
- `assets/` — bundled Nunito + JetBrains Mono fonts and the Levels logo **PNG** (+ source SVG).
  (Company logos are fetched on demand into `assets/company_logos/`, not bundled.)
- `examples/example_pack.py` — one worked chart per builder (copy as a template).
- `examples/example_anim.py` — worked animated GIF (copy as a template).
- `references/brand.md` — palette, fonts, layout constants, formats.
- `references/animation.md` — the animation sub-skill guide (animators, pacing, sample prompts).
- `references/company-logos.md` — fetching + using brand logos (needs a free logo.dev key).
- `references/review_checklist.md` — QA acceptance criteria + a subagent review brief.
- `scripts/setup_assets.sh` — re-fetches/instances the fonts + logo if `assets/` is
  ever missing (not needed for a normal install — they're bundled).

## Notes
- Two formats via `set_format("square"|"portrait")` — square (1080²) is the default.
- Brand font is Nunito; it lacks arrow glyphs (`→`) — avoid them in text (use words).
- Output is 2× resolution (square → 2160×2160 px) for crisp social posts.

## Credits & licenses
- **This skill's code + docs:** MIT (see `LICENSE`).
- **Fonts** (bundled in `assets/fonts/`): [Nunito](https://fonts.google.com/specimen/Nunito)
  and [JetBrains Mono](https://www.jetbrains.com/lp/mono/), both under the
  [SIL Open Font License 1.1](https://openfontlicense.org/) — © their respective authors,
  redistributed under the OFL.
- **Company logos** in charts are fetched on demand from [logo.dev](https://logo.dev)
  and are trademarks of their respective owners; they're used here only as data labels.
- **"Levels.fyi", the Levels.fyi wordmark, and logo** are trademarks of Levels.fyi and
  are included for use with this skill's branded output — not a grant of trademark rights.
