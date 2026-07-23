# Chart review — acceptance criteria + subagent brief

**Reviewing is part of the job.** After rendering, Read every PNG and verify it
against the checklist. Fix in the render script, re-render, re-view — iterate
until all pass. For a pack of >3 charts (or anything you'll publish), delegate a
fresh-eyes pass to a subagent using the brief at the bottom.

## Acceptance checklist (every chart must pass)
**Layout & density**
- [ ] Chart body begins just below the subtitle with a small, intentional gap —
      NO large empty band under the header (the most common defect).
- [ ] Chart fills the canvas; not floating in the lower half.
- [ ] Title ≤2 lines, subtitle ≤2 lines; nothing in the header is clipped.

**Footer**
- [ ] Source line bottom-left, within the left ~60% width, wrapped (not clipped).
- [ ] Logo bottom-right with a clear gap from the source text.
- [ ] No chart element (bar, label, note, legend) overlaps the footer or logo.

**Chart body**
- [ ] No overlapping text (value labels, category labels, annotations, legends).
- [ ] No text clipped at any edge (watch right-end value labels & reference-line
      labels — stagger or shorten if they collide).
- [ ] No missing-glyph "tofu" boxes (use drawn markers via `legmark`/`legend_row`,
      not unicode bullets; use `pct()` for the − minus).
- [ ] Legends sit inside the plot, not above it.
- [ ] Direct labels are legible and attached to the right series/bar.

**Brand & data integrity**
- [ ] Brand palette + Nunito only; cream background; logo undistorted.
- [ ] Numbers/labels match the source data; estimates marked "(est.)"; small
      samples flagged; non-Levels figures cited.
- [ ] The set is consistent: same margins, title position, footer treatment.

## How to fix common issues
- **Empty band under header** → never hardcode a rect; rely on `new_canvas`. If a
  builder leaves interior whitespace (few bars / bars hanging off a zero line),
  add modest `ylim` headroom and place a note/legend in it.
- **Clipped right-edge value label** → raise `xmax` (the builders accept it) or
  shorten the label.
- **Colliding line-end labels** → pass `label_offsets={name: dy}` to `line`.
- **Colliding reference-line labels** (`dumbbell` refs) → shorten them or place at
  staggered y via separate `ax.text` calls.
- **Legend over the subtitle** → give the axes ylim headroom and drop the legend
  to an in-plot y (~0.93–0.95 axes fraction).
- **Footer/source clipped or hitting the logo** → shorten the source; it wraps
  automatically via `src_wrap`.

## Subagent review brief (paste, adjust paths)
> You are a meticulous data-viz designer doing a visual QA pass on a pack of
> Levels.fyi editorial charts (Ramp-style: bold title → gray subtitle → chart
> tight under the subtitle → footer with source bottom-left + logo bottom-right,
> on cream). The render script is `<PATH>/make_charts.py` (it imports the
> `levels-charts` skill engine); outputs are the `*.png` beside it. Render with
> `python3 <PATH>/make_charts.py`. Iterate: edit the script, re-render, **Read
> every PNG**, and fix until all pass the acceptance checklist in this skill's
> `references/review_checklist.md`. Priority issues: (1) no empty band between
> subtitle and chart — the chart must sit tight under the subhead and fill the
> canvas; (2) footer cleanly sectioned — source bottom-left (wrapped, not
> clipped), logo bottom-right, clear gap, nothing overlapping. Also fix any
> clipped/overlapping text, tofu glyphs, and legend placement. Do NOT change data
> values or claims (you may minimally rewrap/shorten a source line to fit). Keep
> Nunito + brand palette + logo + size. Report: global changes, per-chart fixes,
> and confirmation you viewed the final render of all charts.
