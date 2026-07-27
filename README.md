# levels-charts — Levels.fyi editorial chart skill

A Claude Code skill that turns any dataset into **social-ready, on-brand
Levels.fyi charts** — bold headline, gray subtitle, a clean direct-labeled chart,
a source line, and the Levels logo watermark on the cream brand background — then
runs a visual QA pass. Square 1080×1080 by default; 4:5 portrait available. Also
ships **animated GIF** builders (value-over-time, hold-vs-index gap race, and more).

It's **fully self-contained**: the brand fonts (Nunito + JetBrains Mono) and the
Levels logo (bundled as a PNG) live in `assets/` and load relative to the code, so
it works from any directory with no downloads. **Runtime deps are pure-pip only —
no native libraries, no cairo, no node.**

This repo is packaged as a **Claude Code plugin** (so you get auto-updates), and
the skill also works as a plain standalone skill folder.

---

## Install

### Option A — as a plugin (recommended, auto-updates)
In Claude Code:
```
/plugin marketplace add zuhaz3/levels-charts-skill
/plugin install levels-charts@levelsfyi
```
That's it — the skill auto-triggers on chart requests, or invoke it explicitly with
`/levels-charts:levels-charts`. Claude Code checks the marketplace periodically and
installs updates in the background, so you stay current automatically.

### Option B — as a standalone skill (manual updates)
Copy just the skill folder into your Claude Code skills directory (the folder name
must stay `levels-charts`):
```
git clone https://github.com/zuhaz3/levels-charts-skill.git /tmp/lc
cp -R /tmp/lc/skills/levels-charts ~/.claude/skills/levels-charts
```
To update later: re-run the copy, or see **Updating** below.

### Python dependencies (both options)
```
python3 -m pip install matplotlib pillow numpy fonttools
```
- `fonttools` is only used by `scripts/setup_assets.sh` to (re)build fonts if the
  bundled `assets/fonts/` is ever deleted — the fonts ship bundled, so it's optional.
- **Optional extras:** `ffmpeg` (on `PATH`) enables the bonus MP4 export of an
  animation — every PNG and GIF renders without it. `cairosvg` is *not* needed; it's
  only an optional fallback if the bundled logo PNG is deleted.
- **Company logos** (used as row labels in `company_strip` charts) are fetched on
  demand from [logo.dev](https://logo.dev) with your own free key — set
  `LOGO_DEV_TOKEN` in your env. Optional; charts fall back to text labels without it.
  See [`skills/levels-charts/references/company-logos.md`](skills/levels-charts/references/company-logos.md).

> **Upgrading from an earlier clone?** Early versions were cloned directly into
> `~/.claude/skills/levels-charts` (skill files at the repo root). The skill now lives
> under `skills/levels-charts/` so it can also ship as a plugin. Re-install via
> **Option A** (recommended) or **Option B** to pick up the new layout.

---

## Updating
- **Plugin install:** automatic (background). Force a check with
  `/plugin marketplace update levelsfyi`.
- **Manual install:** re-copy `skills/levels-charts` over your `~/.claude/skills/levels-charts`.

## Using with other AI tools (Codex, Cursor, plain Python…)
The Claude Code **plugin** install (auto-updates) is Claude-Code-specific, but the
**skill is just portable Python + Markdown** — it works with any tool, or none:
1. Clone the repo: `git clone https://github.com/zuhaz3/levels-charts-skill.git`
2. `pip install matplotlib pillow numpy fonttools`
3. Point your agent at [`skills/levels-charts/SKILL.md`](skills/levels-charts/SKILL.md)
   (the operating manual) and import the engine from `skills/levels-charts/lib`
   (see **Using it in code** above).

A root [`AGENTS.md`](AGENTS.md) gives Codex, Cursor, and other AGENTS.md-aware agents
the gist automatically when they work in a clone. Outside Claude Code you update with
`git pull` (there's no cross-tool auto-update standard yet).

## Quick test (no Claude needed)
From a clone of this repo:
```
cd skills/levels-charts
python3 examples/example_pack.py /tmp/levels-charts-demo
open /tmp/levels-charts-demo            # macOS (or just browse the PNGs)
```
You get one PNG per chart type (line, grouped bars, bars, leaderboard, dumbbell,
100%-stacked).

## Using it in code
```python
import sys, os
SKILL_DIR = "…"   # this skill's base directory (a manual install is
                  # ~/.claude/skills/levels-charts; a plugin install is its plugin path)
sys.path.insert(0, os.path.join(SKILL_DIR, "lib"))
from levels_charts import *            # new_canvas, save, builders, colors, money/pct
# set_format("portrait")               # optional — 4:5 instead of the square default

fig, ax = new_canvas("Headline that states the takeaway",
                     "A one- or two-line subtitle in gray.",
                     "Source: <where the data came from>.")
vbar(ax, ["L1","L2","L3"], [160, 212, 281], BLUE)
save(fig, os.path.expanduser("~/Downloads/my-chart.png"))
```

## What's inside
```
.claude-plugin/         plugin + marketplace manifests (for the plugin install)
skills/levels-charts/   the skill itself:
  SKILL.md              operating manual Claude reads (workflow, chart-type table, rules)
  lib/levels_charts.py  the engine (new_canvas, clean, save, money/pct, set_format,
                        company_logo, builders line/vbar/grouped_vbar/hbar/dumbbell/
                        stacked100/scatter/company_strip/grant_growth/bars_line)
  lib/levels_charts_anim.py  GIF animators (animate_value_line, animate_gap_race,
                        animate_grouped_vbar, animate_grant_growth, animate_bars_line)
  assets/               bundled Nunito + JetBrains Mono fonts + Levels logo PNG (+ SVG)
  examples/             one worked chart per builder + a worked animated GIF
  references/           brand.md, animation.md, company-logos.md, review_checklist.md
  scripts/setup_assets.sh   re-fetches/instances fonts if assets/ ever goes missing
```

## Notes
- Two formats via `set_format("square"|"portrait")` — square (1080²) is the default.
- Brand font is Nunito; it lacks arrow glyphs (`→`) — avoid them in text (use words).
- Output is 2× resolution (square → 2160×2160 px) for crisp social posts.

## Credits & licenses
- **This skill's code + docs:** MIT (see `LICENSE`).
- **Fonts** (bundled in `skills/levels-charts/assets/fonts/`):
  [Nunito](https://fonts.google.com/specimen/Nunito) and
  [JetBrains Mono](https://www.jetbrains.com/lp/mono/), both under the
  [SIL Open Font License 1.1](https://openfontlicense.org/) — © their respective authors,
  redistributed under the OFL.
- **Company logos** in charts are fetched on demand from [logo.dev](https://logo.dev)
  and are trademarks of their respective owners; they're used here only as data labels.
- **"Levels.fyi", the Levels.fyi wordmark, and logo** are trademarks of Levels.fyi and
  are included for use with this skill's branded output — not a grant of trademark rights.
