# Changelog

All notable changes to the **levels-charts** plugin.

## How releases work (for maintainers)
This repo is a Claude Code plugin + marketplace. Publishing an update:

1. Make your edits under `skills/levels-charts/`.
2. Bump `version` in `.claude-plugin/plugin.json` (semver) and add an entry below.
3. Commit and push to `main`.

Users on the plugin install auto-receive updates in the background (Claude Code
tracks this repo's marketplace). The marketplace entry has no pinned version, so
**every push to `main` propagates** — keep `main` releasable. Bumping the plugin
`version` is what gives each release a clean, human-readable label here.

---

## 1.1.0 — Measured craft utilities
Promoted from the shipped editorial packs (ai-labs, cursor-exit-map, yoe-pyramid): the
content-agnostic machinery every large chart was rebuilding by hand. Classic builders and
social formats are untouched; everything here is additive.

- `audit(fig, ax, ..., keepout=[...])` — measured collision audit: text-vs-text, off-plot,
  and text-vs-art via keepout rects (data coords; `(ax, rect)` entries for multi-panel).
  Treat nonzero as a build failure.
- `lib/layout.py` — the mark/label placement engine (`place`, `place_exact`, `label_anchor`)
  that shipped verbatim in four packs; now one canonical copy.
- `brand_mark(domain)` / `place_mark(...)` — marks with a REAL alpha channel (plates
  un-blended, never ramped) placed by area-equivalent size, returning measured width.
- `register_format(name, FW, FH)` + pre-registered `"xl"` (3000x3000) and `"xltall"`
  (3300x4200); the editorial page rhythm is a named tuning (`EDITORIAL_PROPS`).
- `text_w(fig, s, fs)` measured text width; `usd(v)` dollar formatter with a B tier.
- `new_canvas(..., logo=False)` for co-brand-free exports; `save(..., close=False)` for
  animation frames and variants.
- SKILL.md: new "Measured craft utilities" and "Craft rules (hard-won)" sections.

Recorded direction (deliberately not in this release): re-expressing the social formats
through `register_format`; making un-blend the default inside `company_logo` and migrating
`company_strip`; a shared compaction core under `money()`/`usd()`; deduplicating
`layout.py`'s two side-scoring passes.


## 1.0.0 — Initial release
- Levels.fyi editorial chart engine (`lib/levels_charts.py`): `new_canvas` + builders
  `line / vbar / grouped_vbar / hbar / dumbbell / stacked100 / scatter / company_strip /
  grant_growth / bars_line`, square + portrait formats, brand palette, visual-QA workflow.
- Animation sub-engine (`lib/levels_charts_anim.py`): `animate_value_line`,
  `animate_gap_race` (hold-vs-index race with gap shading + scoreboard + glow finale),
  `animate_grouped_vbar`, `animate_grant_growth`, `animate_bars_line`.
- Fully self-contained runtime: pure-pip (`matplotlib` / `numpy` / `Pillow`); Levels logo
  bundled as a PNG (no cairo/node). `ffmpeg` optional (MP4 export only).
- Company logos fetched on demand from logo.dev via your own `LOGO_DEV_TOKEN` (not bundled).
- Packaged as a Claude Code plugin (`.claude-plugin/`) with a `levelsfyi` marketplace.
