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
