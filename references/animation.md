# Animated GIFs — value-over-time charts

A sub-capability of `levels-charts`: turn a time series into a social GIF where
the line **draws itself** and the value **climbs with the tip**, in the same
cream/Nunito/logo editorial look as the static charts. Inspired by the Carta
"watch it grow" debut-day GIFs. Great for IPO/valuation/comp-over-time stories.

## Engine
`lib/levels_charts_anim.py` → `animate_value_line(out_path, ...)`. It reuses the
static engine (`new_canvas` + brand styling), so the frame, footer, and logo are
identical to a still chart — it only adds motion.

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/levels-charts/lib"))
from levels_charts import *                 # colors, money, presets
from levels_charts_anim import animate_value_line

animate_value_line(
    os.path.expanduser("~/Downloads/x/grant.gif"),
    title="A $365K grant\nbecame about $4.2M",
    subtitle="One line, in gray. Two lines max.",
    source="Source: ...",
    x=[2022.6, 2023.96, 2024.96, 2025.96, 2026.45],
    y=[365, 506, 965, 2195, 4196],          # y in the units your value_fmt formats
    xticks=[2023, 2024, 2025, 2026], xlim=(2022.45, 2027.15),
    ymin=0, ymax=4750, yticks=[0,1000,2000,3000,4000],
    yticklabels=["$0","$1M","$2M","$3M","$4M"],
    start_note="Joined Aug 2022\nat $70 / share",      # pinned at the first point
    vmarkers=[(2026.10, "SpaceX acquires xAI\nFeb 2026", AMBER)],  # fades in when reached
    end_label="≈ $4.2M\nat IPO", end_color=GREEN,      # settled final callout
    seconds=4.5, fps=20, hold=1.4, px=900, qa_frames=True)
```

## What it animates
- The line reveals **left to right at constant time-velocity** (even time per
  frame — truthful for a time series), interpolated through your data points.
- A **tip dot + value tag** rides the leading edge, the tag reading `value_fmt`
  of the current (interpolated) value — this is the "number going up" beat.
- Each `vmarkers` entry is a **vertical dashed milestone** (+ a dot on the line)
  that **fades in** as the sweep passes its x — use it to mark events (an
  acquisition, a raise, a launch).
- The **final frame settles**: the tip becomes an `end_color` dot and the tag
  switches to `end_label`. It holds for `hold` seconds before the loop repeats.

## Key parameters
| param | purpose |
|---|---|
| `x`, `y` | data points; `y` in the units `value_fmt` expects (money() → thousands). |
| `value_fmt` | tip-tag + y-axis formatter (default `money`); pass any `lambda v: ...`. |
| `xticks/yticks/yticklabels/xlim/ymin/ymax` | axis setup (fixed for the whole animation so the line grows into a stable frame). |
| `start_note` | static text at the first point (e.g. the starting price). |
| `vmarkers` | `[(x, "label", color), ...]` milestone lines that fade in. |
| `end_label`, `end_color` | the settled final-point callout. |
| `seconds`, `fps`, `hold` | draw duration, frame rate, end-hold seconds. |
| `px`, `palette_colors` | output square size + GIF palette size (size/quality knobs). |
| `qa_frames` | also dump `<out>_start/_mid/_final.png` for the review pass. |

## Workflow (same discipline as static charts)
1. Build the matching **static** chart first (it's your composition reference).
2. Call `animate_value_line(..., qa_frames=True)`.
3. **REVIEW (required):** `Read` the three `_start/_mid/_final.png` frames. The
   **final** frame must match the static chart (same labels, no overlaps); the
   **start/mid** frames legitimately have empty upper space (the line is still
   climbing into it — that is *not* the "empty band" defect for an animation).
4. Check the file size (`ls -lh`). Then delete the QA PNGs.
5. Preview the motion: open the `.gif` in a **browser** (Safari) — Finder/Preview
   may show only a frame.

## Sizing & encoding notes
- Frames render at the engine's **native DPI** (logo/text stay crisp), then
  downscale to `px` and quantize to a **shared palette taken from the final
  frame** (which contains every color), `dither=NONE` for clean flat fills.
- The end-hold uses a **long duration on the last frame** (no duplicate frames),
  so the rest-on-finished look costs ~0 bytes.
- Ballpark: `px=900`, `fps=20`, ~4.5s → ~90 frames → **~5 MB**. To shrink: lower
  `px` (800), `palette_colors` (96/64), or `seconds`. Twitter auto-converts GIFs
  to MP4 (≤15 MB); LinkedIn posts GIFs directly.

## Sequential grouped bars — `animate_grouped_vbar`
For a cross-section (compare a metric across categories/levels) rather than a time
series, use `animate_grouped_vbar` — the animated twin of the static `grouped_vbar`.
Bars **ease up one category at a time** (left to right), and each category's value
labels + optional per-group `delta` callout **fade in as its bars land**, then the
finished chart holds. Same look as the static builder (colors, in-plot legend).

```python
from levels_charts import *
from levels_charts_anim import animate_grouped_vbar
animate_grouped_vbar("out.gif", title="...", subtitle="...", source="...",
    cats=["L1","L2","L3","L4","L5"],
    series=[("All other engineers", [165,212,273,352,453], GRAYBAR),
            ("AI / ML engineers",   [183,258,364,514,725], BLUE)],
    delta=[11,22,33,46,60], delta_fmt=lambda d: f"+{d}%", ymax=900,
    seconds=2.28, fps=20, hold=0.78, px=900, qa_frames=True)
```
Args mirror `grouped_vbar` (`cats`, `series`, `delta`/`delta_fmt`, `fmt`, `ymax`)
plus the shared timing/encoding knobs (`seconds`/`fps`/`hold`/`px`). Each category
gets `1/len(cats)` of the draw window; total loop ≈ `seconds + hold`. REVIEW the
same way: the **mid** QA frame should show earlier levels fully built (with labels)
while later ones are still empty/growing; the **final** frame must match the static
chart exactly.

## Stock vs benchmark — `animate_gap_race`
The opportunity-cost story ("hold the RSU vs sell at vest and buy the index"). Two lines —
a solid `stock` and a dashed `bench` — **draw out together** left to right from a shared start.
The gap between them **shades live**: `ahead_color` (green) where the stock leads, `behind_color`
(amber) where the benchmark leads, so a mid-series lead that flips to a deficit reads instantly.
A **color-coded scoreboard** in the upper-left counts both values up (tip tags would collide when
the lines are close, so the running numbers live there instead), then the frame settles to clean
end labels + an optional `gap_note`. Static twin: a `line` chart with `fill_between` on the gap.

```python
from levels_charts import *
from levels_charts_anim import animate_gap_race
animate_gap_race("out.gif", title="...", subtitle="...", source="...",
    x=[2022.95, 2023.95, 2024.95, 2025.95, 2026.55],   # shared x
    stock=[200, 317, 357, 412, 340], bench=[200, 234, 312, 344, 390],   # value_fmt units
    stock_name="Microsoft, held", bench_name="S&P 500",
    stock_color=BLUE, bench_color=INK, value_fmt=money,
    xticks=[2023,2024,2025,2026], ymin=0, ymax=460, yticks=[0,100,200,300,400],
    yticklabels=["$0","$100K","$200K","$300K","$400K"],
    gap_note="about $50K\nleft on the table",   # settled callout at the final gap midpoint
    gap_glow=True,                              # finale: the gap flashes to punctuate it
    seconds=2.5, fps=25, hold=3.0, px=900, qa_frames=True)
```
- **`stock`/`bench`** share one `x` and are in `value_fmt` units (default `money`, which wants
  thousands: `340` → `$340K`). Index both to the same start value for a clean "$X became…" read.
- **`gap_glow=True`** adds a short amber flash of the final gap before the hold — great for
  landing "$X left on the table".
- **The scoreboard, not tip tags.** Don't try to tag both moving tips; when the lines cross they
  overlap. The animator already routes the climbing numbers to the upper-left. Leave that space.
- REVIEW the QA frames: **mid** shows the scoreboard mid-climb with the gap shading; **final**
  must match the static (clean end labels, `gap_note`, no overlaps).

## Stock-grant growth — `animate_grant_growth`
The "Project Equity / watch your grant grow" story: a static **left** bar ("At offer") and a
**right** bar ("Today") whose **stock segment grows along the REAL monthly price path**, with
the running total, the date + share price under the bar, and a big "+%" callout all climbing,
then settling. Static twin is `grant_growth`.

```python
from levels_charts_anim import animate_grant_growth
animate_grant_growth("grant.gif", title="...", subtitle="...", source="...",
    base=350000, bonus=50000, shares=90633,            # base/bonus in DOLLARS; equity(t)=shares*price(t)
    prices=[8.22, 9.05, ...], dates=["2022-07-18","2022-07-29", ...],  # split-adjusted closes, ascending
    seconds=3.0, fps=20, hold=1.2, px=900, qa_frames=True)
```
- **Data source:** real Levels.fyi offer (base / bonus / annual stock grant + offer date) +
  Alpha Vantage **`TIME_SERIES_MONTHLY_ADJUSTED`** (free; `DAILY_ADJUSTED` is premium). The app's
  own `stock.api.ts` methodology: `shares = annualGrant / priceAtOffer`, `value(t) = shares * price(t)`.
- **Make frame 0 match the static** (and subtitle): the monthly series starts at the month-END
  close, not the offer-date price. Prepend the actual offer-date price + date to `prices`/`dates`
  so the first frame equals `grant_growth`'s offer bar.
- REVIEW the QA frames as usual: **start** = both bars equal at +0%; **mid** = right bar partway
  up at a real intermediate date/price; **final** = settled totals matching the static chart.

## Bouncing value over time — `animate_bars_line`
When a value-over-time series is **volatile** (a stock-driven grant repriced over time), a single
smoothly-growing bar reads as noisy jitter. Instead use periodic bars + a line over the tops:
each period's bar eases up left-to-right while the line draws across them with a value tag at the
leading edge, then settles. Static twin is `bars_line`.

```python
from levels_charts_anim import animate_bars_line
animate_bars_line("out.gif", title="...", subtitle="...", source="...",
    cats=["Q1'23","Q2'23", ...],
    # STACKED bars (base/bonus/stock) — the line rides the column TOTALS; or pass values=[...] for single bars
    segments=[("Base",[b]*N,GREEN), ("Target bonus",[bo]*N,AMBER), ("Annual stock grant", stock_per_q, STOCK)],
    legend=True, headroom=1.30,                             # raise headroom so a mid-series SPIKE + tag clear the legend
    fmt=lambda v: money(v/1000.0),                          # <-- if values are in DOLLARS (money() wants thousands)
    line_color=NAVY, start_note="Offer ...", end_label="Today  $3.1M",
    seconds=3.4, fps=20, hold=1.4, px=900, qa_frames=True)
```
- **Gotcha:** the moving tag uses `fmt` (default `money`, which expects THOUSANDS). If values are raw
  dollars, pass `fmt=lambda v: money(v/1000.0)` or the tag shows e.g. "$4050.54M" instead of "$4.05M".
- **Spike headroom:** when an intermediate period is HIGHER than the last (volatile stock peaking
  mid-series), bump `headroom` (e.g. 1.30) so the peak bar + its value tag stay below the legend/subtitle.
- **Stock = ANNUAL grant** (`avg_annual_stock_grant_value`, not the multi-year total): base + bonus +
  annual stock should equal `total_compensation`. Stacking the three makes the annualization visible.

## Levels normalized ladder (label correctly!)
L1 Entry · L2 Mid · **L3 Senior** · L4 Staff · L5 Principal · L6 Distinguished
(`apps/frontend/data-explorer/src/lib/benchmark/url-generator.ts`). A "Senior SWE" chart filters
**normalizedLevels=["L3"]** — L4 is Staff, not Senior. Don't confuse normalized levels with a
company's internal level names.

## Pacing — the knobs that make it feel good
Every animator shares `seconds` (draw time), `fps` (smoothness), `hold` (seconds the finished
frame rests before the loop). Total loop ≈ `seconds + hold`.
- **Punchy social default: `seconds≈2.3–2.6`, `fps=25`.** Our first pass shipped at
  `seconds=4.6, fps=20` and read as *sluggish* — go faster unless the series has many points that
  each need a beat.
- **Hold long enough to read the end.** Raise `hold` to **2.5–3.0** so viewers absorb the final
  numbers. It's nearly free: the last frame is encoded once with a long duration (not duplicated),
  so a longer hold adds ~0 bytes.
- **File size:** ~900px / 25fps / 2.5s ≈ 3–5 MB. Shrink with `px` (800), `palette_colors` (96/64),
  or a shorter `seconds`. LinkedIn posts GIFs directly; Twitter re-encodes to MP4 (≤15 MB).

## Creative touches (opt-in, all backward-compatible)
- **Brand a frame** — `animate_value_line(..., logo=company_logo("microsoft.com"), logo_at="header")`
  (top-right by the title) or `logo_at="plot_tr"` (inside the chart, top-right). Pass `logo_px` to size it.
- **Right-side milestone labels** — a `vmarkers` entry may take an optional 4th element `"right"`:
  `(2023.72, "IPO Sep 2023\nat $30", RED, "right")` puts the label on the right of its line so it
  clears the `start_note`.
- **Gap flash finale** — `animate_gap_race(..., gap_glow=True)` flashes the settled gap once to
  punctuate the "$X left on the table" moment.

## Sample prompts (these produced the shipped work)
- "Turn this into a fast-paced animated GIF where the line draws itself, the value climbs on the
  tip, and the acquisition date fades in as a milestone." → `animate_value_line` (`vmarkers`)
- "Animate hold-vs-index: race the Microsoft grant against the S&P 500, shade the gap green while
  ahead and amber once behind, and flash the amount left on the table at the end." → `animate_gap_race`
  with `gap_glow=True`
- "Make it faster than the last one, and pause longer on the final frame so people can read it."
  → lower `seconds`, raise `fps`, raise `hold` (e.g. `seconds=2.5, fps=25, hold=3.0`)
- "Add the Microsoft logo to the top-right of the header in the animation." → `logo=` + `logo_at="header"`
- "Reveal the AI-vs-generalist premium one level at a time, deltas popping in as each pair lands."
  → `animate_grouped_vbar`

## Honesty
Same rules as static charts — flag estimates, cite non-Levels figures in the
source line, and don't let motion imply precision the data doesn't have.
