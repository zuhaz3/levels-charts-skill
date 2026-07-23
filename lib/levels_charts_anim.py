#!/usr/bin/env python3
"""levels_charts_anim — animated GIF builder for the Levels.fyi editorial charts.

Sub-module of the `levels-charts` skill. Reuses the static engine (new_canvas +
brand styling) and animates a single "value over time" line drawing itself left
to right, with a value tag that climbs with the tip, optional milestone markers
that fade in as the sweep reaches them, and a settled final frame that holds.

The look matches the static charts exactly (same cream canvas, Nunito, logo,
palette) — this just adds motion, in the spirit of the Carta-style "watch it
grow" social GIFs.

Usage
-----
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/.claude/skills/levels-charts/lib"))
    from levels_charts import *            # colors, money, presets
    from levels_charts_anim import animate_value_line

    animate_value_line("out.gif",
        title="...", subtitle="...", source="...",
        x=[2022.6, ...], y=[365, ...],     # y in the SAME units your value_fmt expects
        xticks=[2023,2024,2025,2026], yticks=[0,1000,2000,3000,4000],
        yticklabels=["$0","$1M","$2M","$3M","$4M"],
        start_note="Joined Aug 2022\\nat $70 / share",
        vmarkers=[(2026.10, "SpaceX acquires xAI\\nFeb 2026", AMBER)],
        end_label="≈ $4.2M\\nat IPO")

Rendering notes
---------------
- Frames are rendered at the engine's native DPI (so the logo + text stay crisp)
  then downscaled to `px` for the GIF, and quantized to a shared palette (taken
  from the fully-drawn final frame) with no dither for clean flat color + small
  files. The final frame holds via a long per-frame duration (no duplicate
  frames), so the loop rests on the finished chart before repeating.
- Deps are the same as the static engine (matplotlib + numpy + Pillow); no
  imagemagick / ffmpeg / extra writers required.
"""
import os
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.colors import to_rgba
from levels_charts import (  # static engine + brand tokens
    new_canvas, clean, cat_labels, money, plt, Image, legend_row, DPI,
    BLUE, GREEN, AMBER, RED, INK, SUB, MUTE, NAVY, GRAYBAR, STOCK, PALE, SKY, BARFILL,
    VBAR_LEFT, VBAR_W, STRIP_LEFT, STRIP_W, CREAM, lighten, darken,
)

_MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
def _month_label(date_str):
    """'2022-07-18' -> 'Jul 2022'."""
    y, m = date_str[:4], int(date_str[5:7])
    return f"{_MON[m]} {y}"


def _style_yticks(ax, ticks, labels):
    ax.set_yticks(ticks); ax.set_yticklabels(labels)
    for lab in ax.get_yticklabels():
        lab.set_fontweight(700); lab.set_color("#7C8288"); lab.set_fontsize(15)


def animate_value_line(out_path, *, title, subtitle, source, x, y,
                       color=BLUE, value_fmt=money,
                       xticks=None, xticklabels=None,
                       ymin=0, ymax=None, yticks=None, yticklabels=None, xlim=None,
                       left=VBAR_LEFT, width=VBAR_W, lw=3.4,
                       start_note=None, vmarkers=None,
                       logo=None, logo_at="header", logo_px=None,
                       end_label=None, end_color=GREEN,
                       seconds=4.5, fps=20, hold=1.4,
                       px=900, palette_colors=112, qa_frames=False):
    """Render an animated GIF of a single value-over-time line drawing itself.

    x, y           : the data points (y in whatever units `value_fmt` formats —
                     e.g. thousands for money(): 365 -> "$365K", 4196 -> "$4.2M").
    value_fmt      : tip-tag / y-axis formatter (default money()).
    xticks/yticks  : axis ticks; yticklabels lets you label $0/$1M/... explicitly.
    xlim           : (lo, hi); defaults to a small left pad + right room for tags.
    start_note     : static text pinned near the first point.
    vmarkers       : list of (x, label, color[, side]) vertical dashed milestones
                     that fade in (with a dot on the line) as the sweep reaches
                     them. Optional 4th element side="right" places the label to
                     the RIGHT of the line (default "left") — use it to clear the
                     start_note or another marker's text.
    logo           : optional RGBA logo ndarray (from company_logo("x.com")) drawn
                     static in every frame. logo_at="header" (top-right beside the
                     title, default) or "plot_tr" (top-right inside the chart area);
                     logo_px overrides its pixel height.
    end_label      : final-point callout; on the held last frame the tip becomes
                     an `end_color` dot and the tag shows this text.
    seconds/fps    : draw duration + frame rate; hold = seconds to rest on the end.
    px             : output square size in pixels (downscaled from native render).
    qa_frames      : also dump <out>_start/_mid/_final.png for visual review.
    """
    x = [float(v) for v in x]; y = [float(v) for v in y]
    fig, ax = new_canvas(title, subtitle, source, left=left, width=width)

    # ---- static frame (axes, grid, ticks, start note) ----
    if ymax is None:
        ymax = max(y) * 1.12
    ax.set_ylim(ymin, ymax)
    xr = max(x) - min(x)
    if xlim is None:
        xlim = (min(x) - xr * 0.02, max(x) + xr * 0.14)
    ax.set_xlim(*xlim)
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels(xticklabels or [str(t) for t in xticks])
    clean(ax, grid="y"); cat_labels(ax, "x", 16)
    if yticks is not None:
        _style_yticks(ax, yticks, yticklabels or [value_fmt(t) for t in yticks])
    if start_note:
        ax.text(x[0] + xr * 0.012, y[0] + (ymax - ymin) * 0.055, start_note,
                ha="left", va="bottom", fontsize=13.5, fontweight=800, color=INK,
                linespacing=1.18, zorder=8)

    # ---- optional company logo (static; appears in every frame incl. the final) ----
    if logo is not None:
        _lp = logo_px or (130 if logo_at == "header" else 100)
        _oi = OffsetImage(logo, zoom=_lp / (logo.shape[0] * DPI / 72.0))
        if logo_at == "header":                       # top-right of the canvas, beside the title
            _ab = AnnotationBbox(_oi, (0.93, 0.928), xycoords="figure fraction",
                                 frameon=False, box_alignment=(1.0, 1.0),
                                 annotation_clip=False, zorder=40)
            fig.add_artist(_ab)
        else:                                          # "plot_tr": top-right inside the chart area
            _ab = AnnotationBbox(_oi, (0.985, 0.955), xycoords="axes fraction",
                                 frameon=False, box_alignment=(1.0, 1.0),
                                 annotation_clip=False, zorder=8)
            ax.add_artist(_ab)

    # ---- dense, even-time path (constant x-velocity = constant time per frame) ----
    n_draw = max(2, int(round(seconds * fps)))
    xs = np.linspace(x[0], x[-1], n_draw)
    ys = np.interp(xs, x, y)

    # ---- animated artists ----
    (lineart,) = ax.plot([], [], color=color, lw=lw, solid_capstyle="round", zorder=5)
    tip = ax.scatter([x[0]], [y[0]], s=70, color=color, zorder=7, clip_on=False)
    tag = ax.text(x[0], y[0], "", ha="left", va="center", fontsize=15,
                  fontweight=800, color=color, zorder=9)
    end_dot = ax.scatter([x[-1]], [y[-1]], s=210, color=end_color,
                         edgecolor="white", lw=1.9, zorder=10, clip_on=False)
    end_dot.set_visible(False)

    vmark = []
    for _m in (vmarkers or []):
        mx, mlabel, mcolor = _m[0], _m[1], _m[2]
        side = _m[3] if len(_m) > 3 else "left"      # "left" = label sits left of the line (default)
        vl = ax.axvline(mx, color=mcolor, lw=2.2, ls=(0, (5, 3)), zorder=2, alpha=0.0)
        my = float(np.interp(mx, x, y))
        dot = ax.scatter([mx], [my], s=150, color=mcolor, edgecolor="white",
                         lw=1.6, zorder=6); dot.set_alpha(0.0)
        _lx = mx + xr * 0.012 if side == "right" else mx - xr * 0.012
        tl = ax.text(_lx, ymax * 0.985, mlabel,
                     ha=("left" if side == "right" else "right"), va="top",
                     fontsize=13, fontweight=800, color=mcolor, alpha=0.0,
                     linespacing=1.15, zorder=6)
        vmark.append((mx, vl, dot, tl))

    dx = xr * 0.012

    def grab():
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        return Image.fromarray(buf, "RGBA").convert("RGB").resize((px, px), Image.LANCZOS)

    frames = []
    for k in range(n_draw):
        lineart.set_data(xs[:k + 1], ys[:k + 1])
        tip.set_offsets([[xs[k], ys[k]]])
        tag.set_position((xs[k] + dx, ys[k])); tag.set_text(value_fmt(ys[k])); tag.set_color(color)
        for (mx, vl, dot, tl) in vmark:
            a = float(np.clip((xs[k] - mx) / (xr * 0.05), 0.0, 1.0))
            vl.set_alpha(a); dot.set_alpha(a); tl.set_alpha(a)
        frames.append(grab())

    # ---- settled final frame ----
    for (mx, vl, dot, tl) in vmark:
        vl.set_alpha(1.0); dot.set_alpha(1.0); tl.set_alpha(1.0)
    if end_label is not None:
        tip.set_visible(False); end_dot.set_visible(True)
        tag.set_position((x[-1] + dx, y[-1])); tag.set_text(end_label); tag.set_color(end_color)
    final = grab(); frames.append(final)

    # ---- encode GIF (shared palette from final frame; long hold on last) ----
    base = int(round(1000 / fps))
    durations = [base] * n_draw + [int(hold * 1000)]
    pal = final.quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")

    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, fr in (("start", frames[0]), ("mid", frames[len(frames) // 2]),
                            ("final", frames[-1])):
            p = f"{stem}_{tagname}.png"; fr.save(p); print("  qa frame", p)
    return out_path


def animate_gap_race(out_path, *, title, subtitle, source, x, stock, bench,
                     stock_name, stock_color=RED, bench_name="S&P 500", bench_color=INK,
                     value_fmt=money, xticks=None, xticklabels=None,
                     ymin=0, ymax=None, yticks=None, yticklabels=None, xlim=None,
                     left=VBAR_LEFT, width=VBAR_W, lw=3.4,
                     ahead_color=GREEN, behind_color=AMBER, gap_note=None, gap_glow=False,
                     start_note=None, seconds=4.6, fps=20, hold=1.9,
                     px=900, palette_colors=128, qa_frames=False):
    """Animated TWO-line 'race': a solid stock line and a dashed benchmark line draw
    together left-to-right, the gap between them shading GREEN where the stock leads and
    AMBER where the benchmark leads, value tags climbing on both tips, then it settles.

    Built for the opportunity-cost story (hold the RSU vs sell-and-index). x is shared;
    stock/bench are the two y-series in value_fmt units. gap_note (optional) is a settled
    callout, e.g. "$2,600 behind", drawn at the final gap midpoint.
    """
    x = [float(v) for v in x]; stock = [float(v) for v in stock]; bench = [float(v) for v in bench]
    fig, ax = new_canvas(title, subtitle, source, left=left, width=width)
    if ymax is None:
        ymax = max(max(stock), max(bench)) * 1.12
    ax.set_ylim(ymin, ymax)
    xr = max(x) - min(x)
    if xlim is None:
        xlim = (min(x) - xr * 0.02, max(x) + xr * 0.18)
    ax.set_xlim(*xlim)
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels(xticklabels or [str(t) for t in xticks])
    clean(ax, grid="y"); cat_labels(ax, "x", 16)
    if yticks is not None:
        _style_yticks(ax, yticks, yticklabels or [value_fmt(t) for t in yticks])
    if start_note:
        ax.text(x[0] + xr * 0.012, min(stock[0], bench[0]) - (ymax - ymin) * 0.05, start_note,
                ha="left", va="top", fontsize=13.5, fontweight=800, color=INK, linespacing=1.18, zorder=8)

    n_draw = max(2, int(round(seconds * fps)))
    xs = np.linspace(x[0], x[-1], n_draw)
    ys_s = np.interp(xs, x, stock); ys_b = np.interp(xs, x, bench)

    (line_s,) = ax.plot([], [], color=stock_color, lw=lw, solid_capstyle="round", zorder=5)
    (line_b,) = ax.plot([], [], color=bench_color, lw=lw + 0.2, ls=(0, (1.4, 2.2)),
                        solid_capstyle="round", zorder=6)
    tip_s = ax.scatter([x[0]], [stock[0]], s=62, color=stock_color, zorder=7, clip_on=False)
    tip_b = ax.scatter([x[0]], [bench[0]], s=62, color=bench_color, zorder=7, clip_on=False)
    # climbing readout as a color-coded scoreboard in the empty upper-left (tip tags would
    # collide when the two lines are close), swapped for clean end labels on the settle.
    sb_s = ax.text(0.03, 0.95, "", transform=ax.transAxes, ha="left", va="top",
                   fontsize=16.5, fontweight=800, color=stock_color, zorder=9)
    sb_b = ax.text(0.03, 0.875, "", transform=ax.transAxes, ha="left", va="top",
                   fontsize=16.5, fontweight=800, color=bench_color, zorder=9)
    dx = xr * 0.012
    fills = []

    def grab():
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        return Image.fromarray(buf, "RGBA").convert("RGB").resize((px, px), Image.LANCZOS)

    frames = []
    for k in range(n_draw):
        xk, sk, bk = xs[:k + 1], ys_s[:k + 1], ys_b[:k + 1]
        line_s.set_data(xk, sk); line_b.set_data(xk, bk)
        for f in fills:
            f.remove()
        fills = []
        if k >= 1:
            fills.append(ax.fill_between(xk, sk, bk, where=(bk >= sk), interpolate=True,
                                         color=behind_color, alpha=0.17, zorder=1))
            fills.append(ax.fill_between(xk, sk, bk, where=(sk > bk), interpolate=True,
                                         color=ahead_color, alpha=0.13, zorder=1))
        tip_s.set_offsets([[xs[k], ys_s[k]]]); tip_b.set_offsets([[xs[k], ys_b[k]]])
        sb_s.set_text(f"{stock_name}   {value_fmt(ys_s[k])}")
        sb_b.set_text(f"{bench_name}   {value_fmt(ys_b[k])}")
        frames.append(grab())

    # ---- settled: hide the climbing scoreboard, reveal clean end labels + gap ----
    hi_above = bench[-1] >= stock[-1]
    pad = (ymax - ymin) * 0.055
    tip_s.set_visible(False); tip_b.set_visible(False)
    sb_s.set_visible(False); sb_b.set_visible(False)
    ax.scatter([x[-1]], [stock[-1]], s=150, color=stock_color, edgecolor="white", lw=1.8, zorder=10, clip_on=False)
    ax.scatter([x[-1]], [bench[-1]], s=150, color=bench_color, edgecolor="white", lw=1.8, zorder=10, clip_on=False)
    ax.text(x[-1] + dx, stock[-1] + (-pad if hi_above else pad), f"{stock_name}\n{value_fmt(stock[-1])}",
            ha="left", va="center", fontsize=15, fontweight=800, color=stock_color, linespacing=1.05, zorder=9)
    ax.text(x[-1] + dx, bench[-1] + (pad if hi_above else -pad), f"{bench_name}\n{value_fmt(bench[-1])}",
            ha="left", va="center", fontsize=15, fontweight=800, color=bench_color, linespacing=1.05, zorder=9)
    if gap_note:
        ax.annotate(gap_note, xy=(x[-1], (stock[-1] + bench[-1]) / 2),
                    xytext=(x[0] + xr * 0.52, ymin + (ymax - ymin) * 0.30),
                    fontsize=14.5, fontweight=800, color="#B4632B", ha="center", va="center",
                    linespacing=1.1, zorder=9,
                    arrowprops=dict(arrowstyle="-", color="#B4632B", lw=1.4, alpha=0.6))
    frames.append(grab())

    if gap_glow:                                    # finale: the gap flashes to punctuate it
        for lg in (0.55, 0.28, 0.0):
            for f in fills:
                f.remove()
            fills = [ax.fill_between(xs, ys_s, ys_b, where=(ys_b >= ys_s), interpolate=True,
                                     color=(lighten(behind_color, lg) if lg else behind_color),
                                     alpha=0.17 + 0.12 * lg, zorder=1),
                     ax.fill_between(xs, ys_s, ys_b, where=(ys_s > ys_b), interpolate=True,
                                     color=ahead_color, alpha=0.13, zorder=1)]
            frames.append(grab())

    base = int(round(1000 / fps))
    durations = [base] * (len(frames) - 1) + [int(hold * 1000)]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, fr in (("start", frames[0]), ("mid", frames[len(frames) // 2]),
                            ("final", frames[-1])):
            p = f"{stem}_{tagname}.png"; fr.save(p); print("  qa frame", p)
    return out_path


def animate_grouped_vbar(out_path, *, title, subtitle, source, cats, series,
                         delta=None, delta_fmt=None, fmt=money, ymax=None,
                         bar_width=0.38, left=VBAR_LEFT, width=VBAR_W, legend_y=0.94,
                         seconds=2.28, fps=20, hold=0.78, px=900,
                         palette_colors=128, qa_frames=False):
    """Animated grouped vertical bars that reveal one category at a time (Carta-style).

    Mirrors the static grouped_vbar look (same colors, value labels, per-group delta,
    in-plot legend). Each category's bars ease up in sequence; its value labels and
    delta fade in as it lands; the finished chart holds before looping.

    cats   : category labels (e.g. ["L1".."L5"]).
    series : list of (name, values, color) — same shape as grouped_vbar.
    delta  : optional one-per-category callout drawn above each group (e.g. a premium %).
    Timing mirrors the value-line GIF (seconds/fps/hold); total loop ≈ seconds + hold.
    """
    cats = list(cats)
    N, n = len(cats), len(series)
    x = np.arange(N)
    offs = (np.arange(n) - (n - 1) / 2) * bar_width
    vmax = max(v for _, vals, _ in series for v in vals)
    top_lim = ymax if ymax is not None else vmax * 1.20

    fig, ax = new_canvas(title, subtitle, source, left=left, width=width)
    ax.set_ylim(0, top_lim); ax.set_xlim(-0.5, N - 0.5)

    bar_sets = []                                # (BarContainer, values)
    for s, (_, vals, color) in enumerate(series):
        bar_sets.append((ax.bar(x + offs[s], [0] * N, bar_width, color=color, zorder=3), vals))
    labels = [[None] * n for _ in range(N)]      # value labels, faded in per category
    for s, (_, vals, color) in enumerate(series):
        lc = NAVY if color == BLUE else (color if color != GRAYBAR else "#8a857a")
        lw = 700 if color == GRAYBAR else 800
        for i in range(N):
            labels[i][s] = ax.text(x[i] + offs[s], vals[i] + vmax * 0.012, fmt(vals[i]),
                                   ha="center", va="bottom", fontsize=12.5, fontweight=lw, color=lc, alpha=0)
    deltas = [None] * N
    if delta is not None:
        for i in range(N):
            top = max(series[s][1][i] for s in range(n))
            deltas[i] = ax.text(x[i], top + vmax * 0.085, delta_fmt(delta[i]) if delta_fmt else f"+{delta[i]}%",
                                ha="center", fontsize=15, fontweight=800, color=GREEN, alpha=0)

    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_yticks([])
    clean(ax, grid=None); cat_labels(ax, "x", 18)
    legend_row(ax, [(s[2], s[0]) for s in series], y=legend_y)

    ease = lambda t: 1 - (1 - t) ** 3            # easeOutCubic
    clamp = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    n_draw = max(N, int(round(seconds * fps)))

    def grab():
        fig.canvas.draw()
        return Image.fromarray(np.asarray(fig.canvas.buffer_rgba()), "RGBA").convert("RGB").resize((px, px), Image.LANCZOS)

    frames = []
    for k in range(n_draw):
        g = k / (n_draw - 1) if n_draw > 1 else 1.0
        for i in range(N):
            local = clamp((g - i / N) / (1.0 / N))   # this category's 0->1 reveal
            e = ease(local)
            for s in range(n):
                bar_sets[s][0][i].set_height(bar_sets[s][1][i] * e)
            a = clamp((local - 0.6) / 0.4)           # labels fade in as the bars land
            for s in range(n):
                labels[i][s].set_alpha(a)
            if deltas[i] is not None:
                deltas[i].set_alpha(a)
        frames.append(grab())

    base = int(round(1000 / fps))
    durations = [base] * (len(frames) - 1) + [int(hold * 1000)]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, idx in (("start", 0), ("mid", len(frames) // 2), ("final", len(frames) - 1)):
            frames[idx].save(f"{stem}_{tagname}.png"); print("  qa", f"{stem}_{tagname}.png")
    return out_path


def animate_bars_line(out_path, *, title, subtitle, source, cats, values=None, segments=None,
                      bar_color=BARFILL, line_color=NAVY, fmt=money, ymax=None, headroom=1.18,
                      end_label=None, start_note=None, legend=False, legend_y=0.965,
                      left=VBAR_LEFT, width=VBAR_W, cat_size=12, seconds=3.2, fps=20, hold=1.3,
                      px=900, palette_colors=128, qa_frames=False):
    """Sequential periodic BARS revealing left->right with a LINE drawing across their tops.

    Built for a value-over-time series that BOUNCES (e.g. a stock-driven grant repriced each
    quarter) where a single smoothly-growing bar reads as noisy. Each period's bar eases up in
    turn; the line rides the tops with a value tag at the leading edge, then settles + holds.

    Pass EITHER `values` (single-color bars) OR `segments` = [(name, per-period values, color)]
    for STACKED bars (base / bonus / stock), where the line rides the column TOTALS and
    `legend=True` draws an in-plot legend. `headroom` sets y-top = total_max * headroom — raise
    it so a tall mid-series spike + its tag never run above the legend/subtitle.
    end_label : final tag text (e.g. "Today  $3.1M"); defaults to fmt(totals[-1])."""
    cats = list(cats); N = len(cats); x = np.arange(N)
    if segments is not None:
        segs = [(nm, [float(v) for v in sv], c) for nm, sv, c in segments]
        tops = [sum(s[1][i] for s in segs) for i in range(N)]
    else:
        tops = [float(v) for v in values]
        segs = [("", tops, bar_color)]
    vmax = max(tops); top = ymax if ymax is not None else vmax * headroom

    fig, ax = new_canvas(title, subtitle, source, left=left, width=width)
    ax.set_xlim(-0.7, N - 0.3); ax.set_ylim(0, top)
    bar_layers = []                                   # one BarContainer per segment
    for nm, sv, c in segs:
        bar_layers.append((ax.bar(x, [0.0] * N, 0.66, color=c, zorder=3), sv))
    (lineart,) = ax.plot([], [], color=line_color, lw=3.4, solid_capstyle="round", zorder=5)
    tip = ax.scatter([0], [tops[0]], s=82, color=line_color, zorder=7, clip_on=False)
    tag = ax.text(0, tops[0], "", ha="center", va="bottom", fontsize=15, fontweight=800,
                  color=line_color, zorder=9)
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_yticks([])
    clean(ax, grid="y"); cat_labels(ax, "x", cat_size)
    if start_note:
        ax.text(0, tops[0] + top * 0.04, start_note, ha="left", va="bottom",
                fontsize=13, fontweight=800, color=INK, zorder=8)
    if legend and segments is not None:
        legend_row(ax, [(c, nm) for nm, _, c in segs], y=legend_y)

    ease = lambda t: 1 - (1 - t) ** 3
    clamp = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    n_draw = max(N, int(round(seconds * fps)))

    def grab():
        fig.canvas.draw()
        return Image.fromarray(np.asarray(fig.canvas.buffer_rgba()), "RGBA").convert("RGB").resize((px, px), Image.LANCZOS)

    def set_stack(scale):
        # scale: per-bar 0..1 fill factor; stack segments proportionally
        bottoms = [0.0] * N
        for bars, sv in bar_layers:
            for i in range(N):
                h = sv[i] * scale[i]
                bars[i].set_height(h); bars[i].set_y(bottoms[i]); bottoms[i] += h

    frames = []
    for k in range(n_draw):
        g = k / (n_draw - 1) if n_draw > 1 else 1.0
        lead = g * (N - 1)
        set_stack([ease(clamp(lead - (i - 1))) for i in range(N)])   # bar i fills as lead: i-1 -> i
        m = max(2, int(lead * 8) + 2)
        xs = np.linspace(0, lead, m); ys = np.interp(xs, x, tops)
        lineart.set_data(xs, ys)
        cur = float(np.interp(lead, x, tops))
        tip.set_offsets([[lead, cur]])
        tag.set_position((lead, cur + top * 0.022)); tag.set_text(fmt(cur))
        frames.append(grab())

    set_stack([1.0] * N)
    lineart.set_data(x, tops); tip.set_offsets([[x[-1], tops[-1]]])
    tag.set_position((x[-1], tops[-1] + top * 0.022)); tag.set_text(end_label or fmt(tops[-1]))
    frames.append(grab())

    base_ms = int(round(1000 / fps))
    durations = [base_ms] * (len(frames) - 1) + [int(hold * 1000)]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, i in (("start", 0), ("mid", len(frames) // 2), ("final", len(frames) - 1)):
            frames[i].save(f"{stem}_{tagname}.png"); print("  qa", f"{stem}_{tagname}.png")
    return out_path


def animate_grant_growth(out_path, *, title, subtitle, source, base, bonus, shares,
                         prices, dates, seg_colors=(GREEN, AMBER, STOCK),
                         seg_names=("Base", "Target bonus", "Stock grant"),
                         offer_label="At offer", today_label="Today",
                         left=0.085, width=0.86, bottom=0.165, legend_y=0.965,
                         seconds=3.0, fps=20, hold=1.1, px=900,
                         palette_colors=128, qa_frames=False):
    """Animated 'one grant, repriced by the stock' GIF (the Project-Equity story).

    A static left bar ('At offer') and a right bar ('Today') whose STOCK segment grows from
    the offer-date value up to today, following the REAL monthly price path. The running
    total, the date+share-price under the bar, and a big '+%' callout all climb, then settle.

    base, bonus : annual base + target bonus IN DOLLARS (fixed both bars).
    shares      : annual-grant share count (equity(t) = shares * price(t)).
    prices      : monthly split-adjusted closes IN DOLLARS, offer-date -> now (ascending).
    dates       : parallel 'YYYY-MM-DD' strings for the price path (for the climbing label).
    Same render/encode path as the other animators; total loop ~= seconds + hold."""
    prices = [float(p) for p in prices]
    idx = np.arange(len(prices))
    px_off, px_now = prices[0], prices[-1]
    baseT = base + bonus
    eqN = shares * px_now
    totalN = baseT + eqN
    ymax = totalN * 1.20
    fmt = lambda v: money(v / 1000.0)            # values are in dollars; money() wants thousands
    W = 0.52

    fig, ax = new_canvas(title, subtitle, source, left=left, width=width, bottom=bottom)
    ax.set_xlim(-0.7, 1.7); ax.set_ylim(0, ymax)

    # static LEFT bar ('At offer'): base, bonus, equity-at-offer
    eq0 = shares * px_off
    for val, col, b0 in [(base, seg_colors[0], 0.0), (bonus, seg_colors[1], base),
                         (eq0, seg_colors[2], baseT)]:
        ax.bar(0, val, W, bottom=b0, color=col, zorder=3)
    ax.text(0, baseT + eq0 + ymax * 0.015, fmt(baseT + eq0), ha="center", va="bottom",
            fontsize=16, fontweight=800, color=INK, zorder=5)

    # static RIGHT base+bonus; animated stock segment on top
    ax.bar(1, base, W, bottom=0.0, color=seg_colors[0], zorder=3)
    ax.bar(1, bonus, W, bottom=base, color=seg_colors[1], zorder=3)
    rstock = ax.bar(1, 0.0, W, bottom=baseT, color=seg_colors[2], zorder=3)[0]
    rtot = ax.text(1, baseT, "", ha="center", va="bottom", fontsize=16, fontweight=800,
                   color=INK, zorder=5)
    rstock_lab = ax.text(1, baseT, "", ha="center", va="center", color="white",
                         fontsize=13.5, fontweight=800, zorder=6)

    # x labels drawn manually (left static, right climbs along the path)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["", ""]); ax.set_yticks([])
    clean(ax, grid=None)
    xt = ax.get_xaxis_transform()
    ax.text(0, -0.03, f"{offer_label}\n{_month_label(dates[0])}  ·  ${px_off:,.2f}/sh",
            transform=xt, ha="center", va="top", fontsize=15.5, fontweight=800,
            color=INK, linespacing=1.25)
    rxlab = ax.text(1, -0.03, "", transform=xt, ha="center", va="top", fontsize=15.5,
                    fontweight=800, color=INK, linespacing=1.25)
    legend_row(ax, list(zip(seg_colors, seg_names)), y=legend_y)

    # climbing callout in the empty left-center
    cx = 0.40
    cpct = ax.text(cx, 0.66, "", transform=ax.transAxes, ha="center", va="center",
                   fontsize=36, fontweight=800, color=seg_colors[2])
    ax.text(cx, 0.585, "in annual grant value", transform=ax.transAxes, ha="center",
            va="center", fontsize=15.5, fontweight=700, color=SUB)
    ax.text(cx, 0.505, f"{shares:,} shares", transform=ax.transAxes, ha="center",
            va="center", fontsize=15, fontweight=800, color=INK)

    clamp = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    n_draw = max(2, int(round(seconds * fps)))

    def grab():
        fig.canvas.draw()
        return Image.fromarray(np.asarray(fig.canvas.buffer_rgba()), "RGBA").convert("RGB").resize((px, px), Image.LANCZOS)

    def set_frame(f):
        price = float(np.interp(f, idx, prices))
        eq = shares * price; total = baseT + eq
        rstock.set_height(eq)
        rtot.set_position((1, total + ymax * 0.015)); rtot.set_text(fmt(total))
        rstock_lab.set_position((1, baseT + eq / 2))
        rstock_lab.set_text(fmt(eq) if eq > ymax * 0.05 else "")
        di = min(int(round(f)), len(dates) - 1)
        is_end = f >= len(prices) - 1 - 1e-9
        dlab = today_label if is_end else _month_label(dates[di])
        rxlab.set_text(f"{dlab}\n${price:,.2f}/sh")
        cpct.set_text(f"+{(price / px_off - 1) * 100:,.0f}%")

    frames = []
    for k in range(n_draw):
        g = k / (n_draw - 1) if n_draw > 1 else 1.0
        set_frame(clamp(g) * (len(prices) - 1))
        frames.append(grab())
    set_frame(len(prices) - 1)                   # settled final
    frames.append(grab())

    base_ms = int(round(1000 / fps))
    durations = [base_ms] * (len(frames) - 1) + [int(hold * 1000)]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, i in (("start", 0), ("mid", len(frames) // 2), ("final", len(frames) - 1)):
            frames[i].save(f"{stem}_{tagname}.png"); print("  qa", f"{stem}_{tagname}.png")
    return out_path


def animate_company_strip(out_path, *, title, subtitle, source, rows, xticks=None, xmin=0,
                          xmax=None, fmt=money, jitter=0.16, box_h=0.38, dot=22, dot_alpha=0.55,
                          logo_x=-0.085, logo_px=100, seed=7, xlabel="Total Compensation ($K)",
                          left=STRIP_LEFT, width=STRIP_W, bottom=0.15, box_seconds=0.8,
                          dot_seconds=1.6, fps=20, hold=1.4, px=900, palette_colors=200,
                          reveal="ltr", name_dy=0.34, name_size=10.5, qa_frames=False):
    """Animated company pay-range strip (the boxplot). PHASE 1: the whiskers, IQR boxes, median
    lines and labels assemble outward from each median. PHASE 2: the raw submission dots stream
    in rapidly and simultaneously across every company, `reveal='ltr'` (left to right, low to
    high) or 'rtl' (right to left). Then it holds.

    rows: same shape as company_strip — (label, points, color), label = logo ndarray or str.
    Call set_format('portrait') first for 6+ rows (matches the static company_strip)."""
    rng = np.random.default_rng(seed)
    n = len(rows); ys = list(range(n))[::-1]
    allpts = [v for r in rows for v in r[1]]
    xmax = xmax or max(allpts) * 1.06

    fig, ax = new_canvas(title, subtitle, source, left=left, width=width, bottom=bottom)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-0.6, n - 0.4); ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)

    rd = []
    for y, r in zip(ys, rows):
        label, pts, color = r[0], r[1], r[2]
        name = r[3] if len(r) > 3 else None
        arr = np.asarray(sorted(pts), float)
        lo, hi = arr.min(), arr.max(); q1, med, q3 = np.percentile(arr, [25, 50, 75])
        jy = y + rng.uniform(-jitter, jitter, size=len(arr))
        order = np.argsort(arr) if reveal == "ltr" else np.argsort(-arr)   # ltr = low->high
        wl, = ax.plot([med, med], [y, y], color="#C9C3B4", lw=2.0, solid_capstyle="round", zorder=2)
        box = Rectangle((med, y - box_h / 2), 0, box_h, facecolor=color, alpha=0.20,
                        edgecolor=color, linewidth=1.0, zorder=4); ax.add_patch(box)
        ml, = ax.plot([med, med], [y - box_h / 2, y + box_h / 2], color=color, lw=3.2,
                      solid_capstyle="round", zorder=6, alpha=0.0)
        rgba = np.tile(np.array(to_rgba(color, dot_alpha)), (len(arr), 1)); rgba[:, 3] = 0.0
        sc = ax.scatter(arr, jy, s=dot, facecolors=rgba, edgecolors="none", zorder=3)
        tmed = ax.text(med, y + box_h / 2 + 0.10, f"Med. {fmt(med)}", ha="center", va="bottom",
                       fontsize=13.5, fontweight=800, color=INK, alpha=0.0, zorder=7)
        pad = (xmax - xmin) * 0.006
        tq1 = ax.text(q1 - pad, y - box_h / 2 - 0.10, fmt(q1), ha="right", va="top",
                      fontsize=12, fontweight=800, color="#6f7479", alpha=0.0, zorder=7)
        tq3 = ax.text(q3 + pad, y - box_h / 2 - 0.10, fmt(q3), ha="left", va="top",
                      fontsize=12, fontweight=800, color="#6f7479", alpha=0.0, zorder=7)
        if isinstance(label, np.ndarray):
            zoom = logo_px / (label.shape[0] * DPI / 72.0)
            ax.add_artist(AnnotationBbox(OffsetImage(label, zoom=zoom), (logo_x, y),
                          xycoords=("axes fraction", "data"), frameon=False,
                          box_alignment=(0.5, 0.5), annotation_clip=False))
            if name:
                ax.text(logo_x, y - name_dy, name, transform=ax.get_yaxis_transform(),
                        ha="center", va="top", fontsize=name_size, fontweight=700,
                        color=SUB, clip_on=False)
        elif label:
            ax.text(logo_x, y, str(label), transform=ax.get_yaxis_transform(),
                    ha="center", va="center", fontsize=15, fontweight=800, color=INK)
        rd.append(dict(y=y, lo=lo, hi=hi, q1=q1, med=med, q3=q3, arr=arr, order=order,
                       wl=wl, box=box, ml=ml, sc=sc, rgba=rgba, tmed=tmed, tq1=tq1, tq3=tq3))

    ease = lambda t: 1 - (1 - t) ** 3
    clamp = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    n_box = max(2, int(round(box_seconds * fps)))
    n_dot = max(2, int(round(dot_seconds * fps)))

    def grab():
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        h, w = buf.shape[:2]                         # preserve the figure aspect (portrait != square)
        return Image.fromarray(buf, "RGBA").convert("RGB").resize((px, int(round(px * h / w))), Image.LANCZOS)

    frames = []
    for k in range(n_box):                          # PHASE 1: assemble boxes outward from median
        g = ease((k + 1) / n_box)
        for r in rd:
            r["wl"].set_data([r["med"] - (r["med"] - r["lo"]) * g, r["med"] + (r["hi"] - r["med"]) * g], [r["y"], r["y"]])
            r["box"].set_x(r["med"] - (r["med"] - r["q1"]) * g)
            r["box"].set_width(((r["med"] - r["q1"]) + (r["q3"] - r["med"])) * g)
            r["ml"].set_alpha(g)
            a = clamp((g - 0.55) / 0.45)
            r["tmed"].set_alpha(a); r["tq1"].set_alpha(a); r["tq3"].set_alpha(a)
        frames.append(grab())
    for r in rd:                                    # lock boxes fully in
        r["wl"].set_data([r["lo"], r["hi"]], [r["y"], r["y"]])
        r["box"].set_x(r["q1"]); r["box"].set_width(r["q3"] - r["q1"])
        r["ml"].set_alpha(1.0); r["tmed"].set_alpha(1.0); r["tq1"].set_alpha(1.0); r["tq3"].set_alpha(1.0)

    for k in range(n_dot):                          # PHASE 2: dots stream in right -> left
        p = (k + 1) / n_dot
        for r in rd:
            nrev = int(round(p * len(r["arr"])))
            r["rgba"][:, 3] = 0.0
            r["rgba"][r["order"][:nrev], 3] = dot_alpha
            r["sc"].set_facecolors(r["rgba"])
        frames.append(grab())
    for r in rd:
        r["rgba"][:, 3] = dot_alpha; r["sc"].set_facecolors(r["rgba"])
    frames.append(grab())

    base_ms = int(round(1000 / fps))
    durations = [base_ms] * (len(frames) - 1) + [int(hold * 1000)]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        for tagname, i in (("boxes", n_box - 1), ("mid", n_box + n_dot // 2), ("final", len(frames) - 1)):
            frames[i].save(f"{stem}_{tagname}.png"); print("  qa", f"{stem}_{tagname}.png")
    return out_path


def _frames_to_mp4(frames, out_path, fps, end_hold_s=0.8, crf=18):
    """Encode a list of PIL frames to a small, crisp H.264 MP4 via ffmpeg (raw RGB over a
    pipe — no temp files). The last frame is repeated to hold at the end, mirroring the GIF's
    long final duration. yuv420p needs even dimensions, so W/H are trimmed to even. Silently
    skips if ffmpeg is absent."""
    import subprocess, shutil
    if shutil.which("ffmpeg") is None:
        print("  (ffmpeg not found — skipping mp4)"); return None
    W, H = frames[0].size
    W -= W % 2; H -= H % 2
    seq = list(frames) + [frames[-1]] * int(round(end_hold_s * fps))
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
           "-movflags", "+faststart", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for fr in seq:
        fr = fr.convert("RGB")
        if fr.size != (W, H):
            fr = fr.crop((0, 0, W, H))
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    print("wrote", out_path)
    return out_path


# ============================================================================
# animate_paired_vbox — the transposed grouped-boxplot builder (companies on X,
# vertical SWE-vs-HW/PM boxes), animated with premium editorial choreography.
#
# Sequence (Direction A, "the distribution assembles"):
#   0  scaffold  — y pay-axis gridlines + ticks fade/draw in
#   1  the wave  — company by company L->R (SWE column, then its twin at ~65%
#      overlap): raw submission DOTS rain from just above their target and
#      SPRING-settle into the column -> the IQR BOX crystallizes outward from
#      the median through the settled cloud -> WHISKERS extend to the caps ->
#      a held breath -> the MEDIAN bar draws on (the punchline) -> the "Med. $X
#      / p25-p75" CALLOUT rises a beat later. Logo + name rise as each lands.
#   2  hold  — the finished chart lives: boxes breathe, dots shimmer, one soft
#      light-sweep glides across -> hard-cut back to the empty canvas (replay).
#
# Easing: ease_out_cubic is the workhorse; ease_out_expo for the whisker/median
# "caliper" snap; a closed-form damped bounce for the dot settle. No bounce on
# the bulk. rows: (label, swPts, hwPts[, name[, baseColor]]) — same as the
# static paired_vbox, so the same render scripts feed both.
# ============================================================================
def animate_paired_vbox(out_path, *, title, subtitle, source, rows, yticks=None, ymin=0, ymax=None,
                        fmt=money, sw_light=0.30, hw_dark=0.20, group_gap=1.0, box_w=0.30, off=0.20,
                        jitter=0.115, dot=12, dot_alpha=0.55, dot_max=180, whisker=None, whisker_lw=2.2,
                        logo_px=56, name_dy=0.115, name_size=10, med_fs=10, pq_fs=8.5, declutter=True,
                        disc_names=("Software Engineer", "Product Manager"),
                        ylabel="Total Compensation ($K)", legend=True, legend_xy=(0.018, 0.905),
                        legend_dx=0.165,
                        legend_caption="left is software engineer, right is product manager for each company",
                        left=0.062, width=0.90, bottom=0.235, top_pad=0.065, src_y=0.036,
                        fps=30, co_stag=8, hw_off=10, intro_f=12, hold=2.0, px=1000,
                        palette_colors=180, seed=7, mp4=True, mp4_crf=16, box_breathe=False,
                        reorder=False, qa_frames=False):
    from matplotlib.lines import Line2D
    from matplotlib.colors import to_rgba
    rng = np.random.default_rng(seed)
    n = len(rows); xcs = [i * group_gap for i in range(n)]
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    ymax = ymax or max(allpts) * 1.06
    span = ymax - ymin

    fig, ax = new_canvas(title, subtitle, source, left=left, width=width, bottom=bottom,
                         top_pad=top_pad, src_y=src_y)
    ax.set_ylim(ymin, ymax); ax.set_xlim(-0.62, (n - 1) * group_gap + 0.62)
    ax.set_xticks([]); clean(ax, grid="y")
    if yticks is not None:
        ax.set_yticks(yticks)
        ax.set_yticklabels(["$0" if t == 0 else fmt(t) for t in yticks])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)

    # ---- easings ----------------------------------------------------------
    clamp01 = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    eoc = lambda t: 1 - (1 - t) ** 3                                  # ease-out-cubic (workhorse)
    eoe = lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t)             # ease-out-expo (caliper snap)

    # ---- per-box internal schedule (frames from that box's start) ---------
    FADE_IN = 6; FALL = 7; SETTLE = 9; RAIN = 10                       # dot rain + spring settle
    BOX_T0 = 14; BOX_F = 10                                            # box grows from median
    WHK_T0 = 22; WHK_F = 7                                             # whiskers extend + caps
    MED_T0 = 27; MED_F = 6                                             # median draws on (punchline)
    LAB_T0 = 30; LAB_F = 6                                             # callout rises a beat later
    BOX_TOTAL = 36
    FALLDIST = span * 0.15                                             # dots start this far above target
    A0 = span * 0.011; DECAY = 10.0; FREQ = 4.0                        # damped-bounce settle
    wcol = "#A79F8F"; cap = box_w * 0.30; halo = dict(boxstyle="round,pad=0.1", fc=CREAM, ec="none", alpha=0.72)

    boxes = []; comps = []
    for ci, (xc, r) in enumerate(zip(xcs, rows)):
        label = r[0]; sw = np.asarray(r[1], float); hw = np.asarray(r[2], float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        colS, colH = lighten(base, sw_light), darken(base, hw_dark)
        swq = [float(v) for v in np.percentile(sw, [25, 50, 75])]
        hwq = [float(v) for v in np.percentile(hw, [25, 50, 75])]
        med_dy = span * 0.037; nat_S = swq[2] + span * 0.020; nat_H = hwq[2] + span * 0.020
        if declutter:                                                 # stagger callouts up (as static)
            blk = span * 0.065; gap = span * 0.012
            if swq[2] <= hwq[2]:
                ry_S = nat_S; ry_H = max(nat_H, ry_S + blk + gap)
            else:
                ry_H = nat_H; ry_S = max(nat_S, ry_H + blk + gap)
        else:
            ry_S, ry_H = nat_S, nat_H
        cstart = ci * co_stag
        for arr, xb, col, (q1, med, q3), ry, t0 in (
                (sw, xc - off, colS, swq, ry_S, cstart),
                (hw, xc + off, colH, hwq, ry_H, cstart + hw_off)):
            if whisker is None:
                lo, hi = float(arr.min()), float(arr.max())
            else:
                lo, hi = (float(v) for v in np.percentile(arr, [whisker[0] * 100, whisker[1] * 100]))
            inr = arr[(arr >= ymin) & (arr <= ymax)]
            if dot_max and len(inr) > dot_max:
                inr = rng.choice(inr, size=dot_max, replace=False)
            m = len(inr)
            dx = xb + rng.uniform(-jitter, jitter, size=m)
            dyt = inr.copy()
            df0 = rng.uniform(0, RAIN, size=m)                        # per-dot rain offset
            dph = rng.uniform(0, 2 * np.pi, size=m)                   # shimmer phase (hold)
            rgba = np.tile(np.array(to_rgba(col, dot_alpha)), (m, 1)); rgba[:, 3] = 0.0
            sc = ax.scatter(dx, dyt + FALLDIST, s=dot, facecolors=rgba, edgecolors="none", zorder=3)
            box = Rectangle((xb - box_w / 2, med), box_w, 0.0, facecolor=col, alpha=0.0,
                            edgecolor=col, linewidth=2.0, zorder=4); ax.add_patch(box)
            e1, = ax.plot([xb - box_w / 2, xb + box_w / 2], [med, med], color=col, lw=1.6, zorder=5, alpha=0.0)
            e3, = ax.plot([xb - box_w / 2, xb + box_w / 2], [med, med], color=col, lw=1.6, zorder=5, alpha=0.0)
            wlo, = ax.plot([xb, xb], [q1, q1], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            whi, = ax.plot([xb, xb], [q3, q3], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            clo, = ax.plot([xb - cap, xb + cap], [lo, lo], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            chi, = ax.plot([xb - cap, xb + cap], [hi, hi], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            ml, = ax.plot([xb - box_w / 2, xb - box_w / 2], [med, med], color=darken(col, 0.4),
                          lw=4.0, solid_capstyle="butt", zorder=6, alpha=0.0)
            tmed = ax.text(xb, ry + med_dy, f"Med. {fmt(med)}", ha="center", va="bottom", fontsize=med_fs,
                           fontweight=800, color=INK, zorder=8, bbox=halo, alpha=0.0)
            tpq = ax.text(xb, ry, f"{fmt(q1)}-{fmt(q3)}", ha="center", va="bottom", fontsize=pq_fs,
                          fontweight=700, color="#6f7479", zorder=8, bbox=halo, alpha=0.0)
            boxes.append(dict(xb=xb, col=col, q1=q1, med=med, q3=q3, lo=lo, hi=hi, t0=t0, m=m,
                              dx=dx, dyt=dyt, df0=df0, dph=dph, rgba=rgba, sc=sc, box=box, e1=e1, e3=e3,
                              wlo=wlo, whi=whi, clo=clo, chi=chi, ml=ml, tmed=tmed, tpq=tpq,
                              ry=ry, med_dy=med_dy))
        # company logo + name (revealed a beat after the SWE median lands). NOTE: OffsetImage
        # ignores set_alpha for its bitmap, so we fade the logo by premultiplying its alpha
        # channel and toggle the AnnotationBbox visibility (hidden until its company lands).
        oi = ab = nm_txt = arr0 = None
        if isinstance(label, np.ndarray):
            arr0 = label
            zoom = logo_px / (label.shape[0] * DPI / 72.0)
            oi = OffsetImage(label, zoom=zoom)
            ab = AnnotationBbox(oi, (xc, -0.035), xycoords=("data", "axes fraction"),
                                frameon=False, box_alignment=(0.5, 1.0), annotation_clip=False)
            ax.add_artist(ab); ab.set_visible(False)
            if name:
                nm_txt = ax.text(xc, -name_dy, name, transform=ax.get_xaxis_transform(), ha="center",
                                 va="top", fontsize=name_size, fontweight=700, color=SUB, clip_on=False, alpha=0.0)
        elif label:
            nm_txt = ax.text(xc, -0.05, str(label), transform=ax.get_xaxis_transform(), ha="center",
                             va="top", fontsize=13, fontweight=800, color=INK, clip_on=False, alpha=0.0)
        comps.append(dict(oi=oi, ab=ab, arr0=arr0, nm=nm_txt, land=cstart + MED_T0))

    def set_logo_alpha(c, a):
        if c["ab"] is None:
            return
        if a <= 0.02:
            c["ab"].set_visible(False); return
        c["ab"].set_visible(True)
        arr = c["arr0"]
        if arr.ndim == 3 and arr.shape[-1] == 4:                    # premultiply alpha for a real fade
            f = arr.copy(); f[..., 3] = arr[..., 3] * a; c["oi"].set_data(f)

    # legend (drawn once, faded in with the scaffold) -----------------------
    leg_artists = []
    if legend:
        lx, ly = legend_xy; demo = "#6C7176"
        sq = dict(s=150, marker="s", transform=ax.transAxes, clip_on=False, zorder=12)
        leg_artists.append(ax.scatter([lx], [ly], color=lighten(demo, sw_light + 0.12), **sq))
        leg_artists.append(ax.text(lx + 0.017, ly, disc_names[0], transform=ax.transAxes, fontsize=12.5,
                                   fontweight=800, color=INK, va="center", ha="left"))
        x2 = lx + legend_dx
        leg_artists.append(ax.scatter([x2], [ly], color=darken(demo, hw_dark), **sq))
        leg_artists.append(ax.text(x2 + 0.017, ly, disc_names[1], transform=ax.transAxes, fontsize=12.5,
                                   fontweight=800, color=INK, va="center", ha="left"))
        if legend_caption:
            leg_artists.append(ax.text(lx, ly - 0.052, legend_caption, transform=ax.transAxes,
                                       fontsize=10.5, fontweight=600, color=SUB, va="center", ha="left"))

    grids = ax.get_ygridlines(); yticklabels = ax.get_yticklabels()
    for a in leg_artists:
        a.set_alpha(0.0)
    for gl in grids:
        gl.set_alpha(0.0)
    for tl in yticklabels:
        tl.set_alpha(0.0)
    ax.yaxis.label.set_alpha(0.0)

    def grab():
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        h, w = buf.shape[:2]
        return Image.fromarray(buf, "RGBA").convert("RGB").resize((px, int(round(px * h / w))), Image.LANCZOS)

    def draw_box(b, bl, hold_tau=None):
        """Render one box at its local frame `bl` (frames since the box started).
        hold_tau not None => idle-motion overlay (breathe + shimmer)."""
        xb, med = b["xb"], b["med"]
        # dots: rain (gravity) then damped-spring settle
        local = bl - b["df0"]
        ys = np.where(local <= 0, b["dyt"] + FALLDIST, b["dyt"])
        al = np.zeros(b["m"])
        fall = (local > 0) & (local < FALL)
        tf = np.clip(local / FALL, 0, 1)
        ys = np.where(fall, (b["dyt"] + FALLDIST) + (b["dyt"] - (b["dyt"] + FALLDIST)) * (tf * tf), ys)
        settling = local >= FALL
        ts = np.clip(local - FALL, 0, SETTLE) / fps
        yset = b["dyt"] - A0 * np.exp(-DECAY * ts) * np.cos(2 * np.pi * FREQ * ts)
        ys = np.where(settling & (local - FALL < SETTLE), yset, ys)
        ys = np.where(local - FALL >= SETTLE, b["dyt"], ys)
        al = np.where(local > 0, np.clip(local / FADE_IN, 0, 1) * dot_alpha, 0.0)
        if hold_tau is not None:                                     # shimmer during the hold
            ramp = clamp01(hold_tau / 10.0)
            al = np.clip(dot_alpha + ramp * 0.05 * np.sin(2 * np.pi * hold_tau / 20.0 + b["dph"]), 0, 1)
            ys = b["dyt"]
        b["rgba"][:, 3] = al; b["sc"].set_facecolors(b["rgba"])
        b["sc"].set_offsets(np.column_stack([b["dx"], ys]))
        # box grows from the median outward
        gb = eoc(clamp01((bl - BOX_T0) / BOX_F))
        q1d = med - (med - b["q1"]) * gb; q3d = med + (b["q3"] - med) * gb
        if hold_tau is not None and box_breathe:                     # optional vertical breathe about the median
            sc_ = 1 + 0.013 * np.sin(2 * np.pi * hold_tau / 30.0)     # OFF by default: it stretches p25/p75 (misleads)
            q1d = med - (med - b["q1"]) * sc_; q3d = med + (b["q3"] - med) * sc_
        b["box"].set_y(q1d); b["box"].set_height(q3d - q1d)
        ba = 0.15 * clamp01((gb - 0.15) / 0.85) if hold_tau is None else 0.15
        b["box"].set_alpha(ba)
        ea = clamp01((gb - 0.15) / 0.6) if hold_tau is None else 1.0
        b["e1"].set_ydata([q1d, q1d]); b["e1"].set_alpha(ea)
        b["e3"].set_ydata([q3d, q3d]); b["e3"].set_alpha(ea)
        # whiskers extend from the box edges out to the caps
        gw = eoe(clamp01((bl - WHK_T0) / WHK_F))
        lod = b["q1"] - (b["q1"] - b["lo"]) * gw; hid = b["q3"] + (b["hi"] - b["q3"]) * gw
        b["wlo"].set_ydata([b["q1"], lod]); b["wlo"].set_alpha(1.0 if gw > 0 else 0.0)
        b["whi"].set_ydata([b["q3"], hid]); b["whi"].set_alpha(1.0 if gw > 0 else 0.0)
        ca = clamp01((gw - 0.8) / 0.2)
        b["clo"].set_ydata([lod, lod]); b["clo"].set_alpha(ca)
        b["chi"].set_ydata([hid, hid]); b["chi"].set_alpha(ca)
        # median bar draws on left -> right (the punchline)
        gm = eoc(clamp01((bl - MED_T0) / MED_F))
        x0 = xb - box_w / 2; x1 = x0 + box_w * gm
        b["ml"].set_xdata([x0, x1]); b["ml"].set_alpha(1.0 if gm > 0 else 0.0)
        # callout rises + fades a beat later
        gl = eoc(clamp01((bl - LAB_T0) / LAB_F))
        b["tmed"].set_alpha(gl); b["tpq"].set_alpha(gl)
        b["tmed"].set_y(b["ry"] + b["med_dy"] - span * 0.02 * (1 - gl))
        b["tpq"].set_y(b["ry"] - span * 0.02 * (1 - gl))

    frames = []
    # ---- beat 0: scaffold draws in ----------------------------------------
    for k in range(intro_f):
        g = eoc((k + 1) / intro_f)
        for gl in grids:
            gl.set_alpha(0.32 * g)
        for tl in yticklabels:
            tl.set_alpha(g)
        ax.yaxis.label.set_alpha(g)
        for a in leg_artists:
            a.set_alpha(g)
        frames.append(grab())
    for gl in grids:
        gl.set_alpha(0.32)
    for tl in yticklabels:
        tl.set_alpha(1.0)
    ax.yaxis.label.set_alpha(1.0)
    for a in leg_artists:
        a.set_alpha(1.0)

    # ---- beat 1: the wave -------------------------------------------------
    wave_len = (n - 1) * co_stag + hw_off + BOX_TOTAL
    for f in range(wave_len):
        for b in boxes:
            draw_box(b, f - b["t0"])
        for c in comps:
            gl = eoc(clamp01((f - c["land"]) / 8.0))
            set_logo_alpha(c, gl)
            if c["nm"] is not None:
                c["nm"].set_alpha(gl)
        frames.append(grab())
    for b in boxes:                                                  # lock fully assembled
        draw_box(b, BOX_TOTAL + 5)
    for c in comps:
        set_logo_alpha(c, 1.0)
        if c["nm"] is not None:
            c["nm"].set_alpha(1.0)

    # ---- beat 1.5: reorder companies by the SWE-PM median gap (optional) ---
    if reorder:
        def _snap(b):                                                # freeze assembled geometry
            b["_sc"] = np.array(b["sc"].get_offsets(), float)
            b["_bx"], b["_by"] = b["box"].get_x(), b["box"].get_y()
            for k in ("e1", "e3", "wlo", "whi", "clo", "chi", "ml"):
                b["_" + k] = (np.array(b[k].get_xdata(), float), np.array(b[k].get_ydata(), float))
            b["_tm"] = b["tmed"].get_position(); b["_tp"] = b["tpq"].get_position()
        def _place(b, dx, dy):                                       # slide the whole box as a rigid unit
            o = b["_sc"].copy(); o[:, 0] += dx; o[:, 1] += dy; b["sc"].set_offsets(o)
            b["box"].set_x(b["_bx"] + dx); b["box"].set_y(b["_by"] + dy)
            for k in ("e1", "e3", "wlo", "whi", "clo", "chi", "ml"):
                xd, yd = b["_" + k]; b[k].set_xdata(xd + dx); b[k].set_ydata(yd + dy)
            xm, ym = b["_tm"]; b["tmed"].set_position((xm + dx, ym + dy))
            xp, yp = b["_tp"]; b["tpq"].set_position((xp + dx, yp + dy))
        for b in boxes:
            _snap(b)
        home = [ci * group_gap for ci in range(n)]
        gapv = [boxes[2 * ci + 1]["med"] - boxes[2 * ci]["med"] for ci in range(n)]  # PM med - SWE med
        order = sorted(range(n), key=lambda i: gapv[i])             # SWE-wins (neg) left -> PM-wins (pos) right
        targ = [0.0] * n
        for rank, ci in enumerate(order):
            targ[ci] = rank * group_gap
        trav = [abs(targ[ci] - home[ci]) for ci in range(n)]; mxt = max(trav) or 1.0
        eio = lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
        REORD_F = 34
        for f in range(REORD_F):
            p = eio(clamp01((f + 1) / REORD_F))
            cf = 1 - clamp01(f / (REORD_F * 0.45))                  # callouts fade while sliding (no text soup)
            for ci in range(n):
                dx = (targ[ci] - home[ci]) * p
                dy = span * 0.05 * (trav[ci] / mxt) * np.sin(np.pi * p)   # sin-arc lift so crossers pass cleanly
                for bi in (2 * ci, 2 * ci + 1):
                    b = boxes[bi]; b["box"].set_zorder(4 + trav[ci])
                    b["tmed"].set_alpha(cf); b["tpq"].set_alpha(cf); _place(b, dx, dy)
                c = comps[ci]
                if c["ab"] is not None:
                    c["ab"].xy = (home[ci] + dx, -0.035); c["ab"].xybox = (home[ci] + dx, -0.035)
                if c["nm"] is not None:
                    c["nm"].set_position((home[ci] + dx, c["nm"].get_position()[1]))
            frames.append(grab())
        for ci in range(n):                                         # commit new home so the hold continues here
            dx = targ[ci] - home[ci]
            for bi in (2 * ci, 2 * ci + 1):
                b = boxes[bi]; _place(b, dx, 0.0); b["box"].set_zorder(4)
                b["xb"] += dx; b["dx"] = b["dx"] + dx
                b["tmed"].set_alpha(0.0); b["tpq"].set_alpha(0.0)
            c = comps[ci]
            if c["ab"] is not None:
                c["ab"].xy = (targ[ci], -0.035); c["ab"].xybox = (targ[ci], -0.035)
            if c["nm"] is not None:
                c["nm"].set_position((targ[ci], c["nm"].get_position()[1]))
        for f in range(10):                                         # settle: callouts fade back at the new spots
            a = eoc(clamp01((f + 1) / 10))
            for b in boxes:
                b["tmed"].set_alpha(a); b["tpq"].set_alpha(a)
            frames.append(grab())

    # ---- beat 2: living hold + light-sweep --------------------------------
    hold_f = int(round(hold * fps))
    sweep = Rectangle((-0.2, 0), 0.16, 1.0, transform=ax.transAxes, facecolor="white",
                      alpha=0.0, edgecolor="none", zorder=11, clip_on=False); ax.add_patch(sweep)
    for tau in range(1, hold_f + 1):
        for b in boxes:
            draw_box(b, BOX_TOTAL + 5, hold_tau=tau)
        sp = clamp01((tau - 8) / 30.0)                              # one L->R sheen, gone before the loop
        sweep.set_x(-0.2 + 1.4 * sp)
        sweep.set_alpha(0.06 * np.sin(np.pi * sp) if 0 < sp < 1 else 0.0)
        frames.append(grab())

    base_ms = int(round(1000 / fps))
    durations = [base_ms] * (len(frames) - 1) + [800]                # brief rest on the finished frame
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    if mp4:                                                          # small, crisp companion for social
        _frames_to_mp4(frames, os.path.splitext(out_path)[0] + ".mp4", fps, end_hold_s=0.8, crf=mp4_crf)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps, wave {wave_len}f + hold {hold_f}f)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        marks = (("scaffold", intro_f - 1), ("wave_early", intro_f + wave_len // 3),
                 ("wave_mid", intro_f + 2 * wave_len // 3), ("assembled", intro_f + wave_len - 1),
                 ("hold", len(frames) - 1))
        for tagname, i in marks:
            frames[min(i, len(frames) - 1)].save(f"{stem}_{tagname}.png"); print("  qa", f"{stem}_{tagname}.png")
    return out_path


# ============================================================================
# animate_paired_vbox_story — "Direction B", the narrative payoff. Builds on the
# same paired-vbox glyph as animate_paired_vbox, but the MOTION argues the thesis:
#   Act 1  the SWE boxes assemble in an L->R wave (read the engineer landscape)
#   Act 2  the PM boxes land beside them (the comparison appears)
#   Act 3  every company slides into GAP order (SWE-wins left -> PM-wins right),
#          rigid-unit position tween + a sin-arc lift so crossing units pass over
#   Act 4  all the gap connectors fire top-down in unison, each delta counting up,
#          and a hero stat locks in -> long rest -> hard-cut replay.
# rows: (label, swPts_$K, pmPts_$K[, name[, baseColor]]) — same as the static/A.
# ============================================================================
SW_WIN = BLUE          # scannable winner accents, independent of company color
PM_WIN = "#D9701C"

def animate_paired_vbox_story(out_path, *, title, subtitle, source, rows, hero_stat, hero_sub="",
                              yticks=None, ymin=0, ymax=None, fmt=money, sw_light=0.30, hw_dark=0.20,
                              group_gap=1.0, box_w=0.30, off=0.20, jitter=0.115, dot=12, dot_alpha=0.55,
                              dot_max=150, whisker=None, whisker_lw=2.2, logo_px=56, name_dy=0.115,
                              name_size=10, med_fs=10, pq_fs=8.5, declutter=True,
                              disc_names=("Software Engineer", "Product Manager"),
                              ylabel="Total Compensation ($K)", legend=True, legend_xy=(0.018, 0.905),
                              legend_dx=0.165,
                              legend_caption="left is software engineer, right is product manager for each company",
                              left=0.062, width=0.90, bottom=0.235, top_pad=0.065, src_y=0.036,
                              full_bleed=False, fb_rect=(0.052, 0.132, 0.936, 0.80), fb_logo_pts=46,
                              fb_logo_xy=(0.012, 0.02), legend_scale=1.0, hero_fs=24, hero_sub_fs=13.5,
                              fps=30, co_stag=5, intro_f=12, px=1400, palette_colors=256, seed=7,
                              mp4=True, mp4_crf=16, qa_frames=False):
    from matplotlib.colors import to_rgba
    import levels_charts as _LC
    rng = np.random.default_rng(seed)
    n = len(rows); xcs = [i * group_gap for i in range(n)]
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    ymax = ymax or max(allpts) * 1.06
    span = ymax - ymin

    if full_bleed:      # no header/subheader/source, no bottom logo — chart fills the frame
        fig = plt.figure(figsize=(_LC.FW, _LC.FH), dpi=_LC.DPI); fig.patch.set_facecolor(CREAM)
        ax = fig.add_axes(fb_rect); ax.set_facecolor(CREAM)
    else:
        fig, ax = new_canvas(title, subtitle, source, left=left, width=width, bottom=bottom,
                             top_pad=top_pad, src_y=src_y)
    ax.set_ylim(ymin, ymax); ax.set_xlim(-0.62, (n - 1) * group_gap + 0.62)
    ax.set_xticks([]); clean(ax, grid="y")
    if yticks is not None:
        ax.set_yticks(yticks)
        ax.set_yticklabels(["$0" if t == 0 else fmt(t) for t in yticks])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)

    clamp01 = lambda v: 0.0 if v < 0 else (1.0 if v > 1 else v)
    eoc = lambda t: 1 - (1 - t) ** 3
    eoe = lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t)
    eio = lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2   # ease-in-out-cubic (reorder)

    FADE_IN = 6; FALL = 7; SETTLE = 9; RAIN = 10
    BOX_T0 = 14; BOX_F = 10; WHK_T0 = 22; WHK_F = 7; MED_T0 = 27; MED_F = 6; LAB_T0 = 30; LAB_F = 6
    BOX_TOTAL = 36
    FALLDIST = span * 0.15; A0 = span * 0.011; DECAY = 10.0; FREQ = 4.0
    wcol = "#A79F8F"; cap = box_w * 0.30; halo = dict(boxstyle="round,pad=0.1", fc=CREAM, ec="none", alpha=0.72)

    SWE_WAVE = (n - 1) * co_stag + BOX_TOTAL + 10        # act-1 span before PM starts
    boxes = []; units = []
    for ci, (xc, r) in enumerate(zip(xcs, rows)):
        label = r[0]; sw = np.asarray(r[1], float); pm = np.asarray(r[2], float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        colS, colH = lighten(base, sw_light), darken(base, hw_dark)
        swq = [float(v) for v in np.percentile(sw, [25, 50, 75])]
        pmq = [float(v) for v in np.percentile(pm, [25, 50, 75])]
        med_dy = span * 0.037; nat_S = swq[2] + span * 0.020; nat_H = pmq[2] + span * 0.020
        if declutter:
            blk = span * 0.065; gap = span * 0.012
            if swq[2] <= pmq[2]:
                ry_S = nat_S; ry_H = max(nat_H, ry_S + blk + gap)
            else:
                ry_H = nat_H; ry_S = max(nat_S, ry_H + blk + gap)
        else:
            ry_S, ry_H = nat_S, nat_H
        ubox = []
        for arr, xb, col, (q1, med, q3), ry, t0 in (
                (sw, xc - off, colS, swq, ry_S, ci * co_stag),
                (pm, xc + off, colH, pmq, ry_H, SWE_WAVE + ci * co_stag)):
            if whisker is None:
                lo, hi = float(arr.min()), float(arr.max())
            else:
                lo, hi = (float(v) for v in np.percentile(arr, [whisker[0] * 100, whisker[1] * 100]))
            inr = arr[(arr >= ymin) & (arr <= ymax)]
            if dot_max and len(inr) > dot_max:
                inr = rng.choice(inr, size=dot_max, replace=False)
            m = len(inr)
            dx = xb + rng.uniform(-jitter, jitter, size=m); dyt = inr.copy()
            df0 = rng.uniform(0, RAIN, size=m)
            rgba = np.tile(np.array(to_rgba(col, dot_alpha)), (m, 1)); rgba[:, 3] = 0.0
            sc = ax.scatter(dx, dyt + FALLDIST, s=dot, facecolors=rgba, edgecolors="none", zorder=3)
            box = Rectangle((xb - box_w / 2, med), box_w, 0.0, facecolor=col, alpha=0.0,
                            edgecolor=col, linewidth=2.0, zorder=4); ax.add_patch(box)
            e1, = ax.plot([xb - box_w / 2, xb + box_w / 2], [med, med], color=col, lw=1.6, zorder=5, alpha=0.0)
            e3, = ax.plot([xb - box_w / 2, xb + box_w / 2], [med, med], color=col, lw=1.6, zorder=5, alpha=0.0)
            wlo, = ax.plot([xb, xb], [q1, q1], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            whi, = ax.plot([xb, xb], [q3, q3], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            clo, = ax.plot([xb - cap, xb + cap], [lo, lo], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            chi, = ax.plot([xb - cap, xb + cap], [hi, hi], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2, alpha=0.0)
            ml, = ax.plot([xb - box_w / 2, xb - box_w / 2], [med, med], color=darken(col, 0.4),
                          lw=4.0, solid_capstyle="butt", zorder=6, alpha=0.0)
            tmed = ax.text(xb, ry + med_dy, f"Med. {fmt(med)}", ha="center", va="bottom", fontsize=med_fs,
                           fontweight=800, color=INK, zorder=8, bbox=halo, alpha=0.0)
            tpq = ax.text(xb, ry, f"{fmt(q1)}-{fmt(q3)}", ha="center", va="bottom", fontsize=pq_fs,
                          fontweight=700, color="#6f7479", zorder=8, bbox=halo, alpha=0.0)
            b = dict(xb=xb, col=col, q1=q1, med=med, q3=q3, lo=lo, hi=hi, t0=t0, m=m, dx=dx, dyt=dyt,
                     df0=df0, rgba=rgba, sc=sc, box=box, e1=e1, e3=e3, wlo=wlo, whi=whi, clo=clo, chi=chi,
                     ml=ml, tmed=tmed, tpq=tpq, ry=ry, med_dy=med_dy)
            boxes.append(b); ubox.append(b)
        # logo + name
        oi = ab = nm_txt = arr0 = None
        if isinstance(label, np.ndarray):
            arr0 = label; zoom = logo_px / (label.shape[0] * DPI / 72.0)
            oi = OffsetImage(label, zoom=zoom)
            ab = AnnotationBbox(oi, (xc, -0.035), xycoords=("data", "axes fraction"), frameon=False,
                                box_alignment=(0.5, 1.0), annotation_clip=False)
            ax.add_artist(ab); ab.set_visible(False)
            if name:
                nm_txt = ax.text(xc, -name_dy, name, transform=ax.get_xaxis_transform(), ha="center",
                                 va="top", fontsize=name_size, fontweight=700, color=SUB, clip_on=False, alpha=0.0)
        elif label:
            nm_txt = ax.text(xc, -0.05, str(label), transform=ax.get_xaxis_transform(), ha="center",
                             va="top", fontsize=13, fontweight=800, color=INK, clip_on=False, alpha=0.0)
        units.append(dict(sw=ubox[0], pm=ubox[1], oi=oi, ab=ab, arr0=arr0, nm=nm_txt, xc=xc, ci=ci,
                          medS=swq[1], medP=pmq[1], gap=pmq[1] - swq[1], land=ci * co_stag + MED_T0,
                          ry_top=max(ry_S, ry_H) + med_dy + span * 0.03,
                          nm_y=(-name_dy if isinstance(label, np.ndarray) else -0.05)))

    def set_logo_alpha(u, a):
        if u["ab"] is None:
            return
        if a <= 0.02:
            u["ab"].set_visible(False); return
        u["ab"].set_visible(True)
        arr = u["arr0"]
        if arr is not None and arr.ndim == 3 and arr.shape[-1] == 4:
            f = arr.copy(); f[..., 3] = arr[..., 3] * a; u["oi"].set_data(f)

    leg_artists = []
    if legend:
        lx, ly = legend_xy; demo = "#6C7176"; s = legend_scale
        sq = dict(s=150 * s * s, marker="s", transform=ax.transAxes, clip_on=False, zorder=12)
        leg_artists.append(ax.scatter([lx], [ly], color=lighten(demo, sw_light + 0.12), **sq))
        leg_artists.append(ax.text(lx + 0.017 * s, ly, disc_names[0], transform=ax.transAxes,
                                   fontsize=12.5 * s, fontweight=800, color=INK, va="center", ha="left"))
        x2 = lx + legend_dx * s
        leg_artists.append(ax.scatter([x2], [ly], color=darken(demo, hw_dark), **sq))
        leg_artists.append(ax.text(x2 + 0.017 * s, ly, disc_names[1], transform=ax.transAxes,
                                   fontsize=12.5 * s, fontweight=800, color=INK, va="center", ha="left"))
        if legend_caption:
            leg_artists.append(ax.text(lx, ly - 0.052 * s, legend_caption, transform=ax.transAxes,
                                       fontsize=10.5 * s, fontweight=600, color=SUB, va="center", ha="left"))
    if full_bleed:      # levels.fyi attribution in the BOTTOM-LEFT corner inside the plot (persists every act)
        lg = _LC.LOGO_ARR
        zoom_l = fb_logo_pts / (lg.shape[0] * _LC.DPI / 72.0)
        ax.add_artist(AnnotationBbox(OffsetImage(lg, zoom=zoom_l), fb_logo_xy, xycoords="axes fraction",
                      frameon=False, box_alignment=(0.0, 0.0), annotation_clip=False, zorder=14))
    grids = ax.get_ygridlines(); yticklabels = ax.get_yticklabels()
    for a in leg_artists + list(grids) + list(yticklabels):
        a.set_alpha(0.0)
    ax.yaxis.label.set_alpha(0.0)

    def grab():
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba()); h, w = buf.shape[:2]
        return Image.fromarray(buf, "RGBA").convert("RGB").resize((px, int(round(px * h / w))), Image.LANCZOS)

    def draw_box(b, bl):
        med = b["med"]
        local = bl - b["df0"]
        ys = np.where(local <= 0, b["dyt"] + FALLDIST, b["dyt"])
        fall = (local > 0) & (local < FALL); tf = np.clip(local / FALL, 0, 1)
        ys = np.where(fall, (b["dyt"] + FALLDIST) + (b["dyt"] - (b["dyt"] + FALLDIST)) * (tf * tf), ys)
        ts = np.clip(local - FALL, 0, SETTLE) / fps
        yset = b["dyt"] - A0 * np.exp(-DECAY * ts) * np.cos(2 * np.pi * FREQ * ts)
        ys = np.where((local >= FALL) & (local - FALL < SETTLE), yset, ys)
        ys = np.where(local - FALL >= SETTLE, b["dyt"], ys)
        al = np.where(local > 0, np.clip(local / FADE_IN, 0, 1) * dot_alpha, 0.0)
        b["rgba"][:, 3] = al; b["sc"].set_facecolors(b["rgba"])
        b["sc"].set_offsets(np.column_stack([b["dx"], ys]))
        gb = eoc(clamp01((bl - BOX_T0) / BOX_F))
        q1d = med - (med - b["q1"]) * gb; q3d = med + (b["q3"] - med) * gb
        b["box"].set_y(q1d); b["box"].set_height(q3d - q1d)
        b["box"].set_alpha(0.15 * clamp01((gb - 0.15) / 0.85))
        ea = clamp01((gb - 0.15) / 0.6)
        b["e1"].set_ydata([q1d, q1d]); b["e1"].set_alpha(ea)
        b["e3"].set_ydata([q3d, q3d]); b["e3"].set_alpha(ea)
        gw = eoe(clamp01((bl - WHK_T0) / WHK_F))
        lod = b["q1"] - (b["q1"] - b["lo"]) * gw; hid = b["q3"] + (b["hi"] - b["q3"]) * gw
        b["wlo"].set_ydata([b["q1"], lod]); b["wlo"].set_alpha(1.0 if gw > 0 else 0.0)
        b["whi"].set_ydata([b["q3"], hid]); b["whi"].set_alpha(1.0 if gw > 0 else 0.0)
        ca = clamp01((gw - 0.8) / 0.2)
        b["clo"].set_ydata([lod, lod]); b["clo"].set_alpha(ca)
        b["chi"].set_ydata([hid, hid]); b["chi"].set_alpha(ca)
        gm = eoc(clamp01((bl - MED_T0) / MED_F))
        x0 = b["xb"] - box_w / 2
        b["ml"].set_xdata([x0, x0 + box_w * gm]); b["ml"].set_alpha(1.0 if gm > 0 else 0.0)
        glb = eoc(clamp01((bl - LAB_T0) / LAB_F))
        b["tmed"].set_alpha(glb); b["tpq"].set_alpha(glb)
        b["tmed"].set_y(b["ry"] + b["med_dy"] - span * 0.02 * (1 - glb))
        b["tpq"].set_y(b["ry"] - span * 0.02 * (1 - glb))

    def snapshot(b):                                                 # freeze final geometry for the slide
        b["_sc"] = np.array(b["sc"].get_offsets(), float)
        b["_box"] = (b["box"].get_x(), b["box"].get_y())
        for k in ("e1", "e3", "wlo", "whi", "clo", "chi", "ml"):
            b["_" + k] = (np.array(b[k].get_xdata(), float), np.array(b[k].get_ydata(), float))
        b["_tmed"] = b["tmed"].get_position(); b["_tpq"] = b["tpq"].get_position()

    def place_box(b, dx, dy):
        o = b["_sc"].copy(); o[:, 0] += dx; o[:, 1] += dy; b["sc"].set_offsets(o)
        b["box"].set_x(b["_box"][0] + dx); b["box"].set_y(b["_box"][1] + dy)
        for k in ("e1", "e3", "wlo", "whi", "clo", "chi", "ml"):
            xd, yd = b["_" + k]; b[k].set_xdata(xd + dx); b[k].set_ydata(yd + dy)
        px_, py_ = b["_tmed"]; b["tmed"].set_position((px_ + dx, py_ + dy))
        px_, py_ = b["_tpq"]; b["tpq"].set_position((px_ + dx, py_ + dy))

    def place_unit(u, dx, dy):
        place_box(u["sw"], dx, dy); place_box(u["pm"], dx, dy)
        if u["ab"] is not None:
            u["ab"].xy = (u["xc"] + dx, -0.035); u["ab"].xybox = (u["xc"] + dx, -0.035)
        if u["nm"] is not None:
            u["nm"].set_position((u["xc"] + dx, u["nm_y"]))

    frames = []
    # ---- intro scaffold ----
    for k in range(intro_f):
        g = eoc((k + 1) / intro_f)
        for gl in grids:
            gl.set_alpha(0.32 * g)
        for tl in yticklabels:
            tl.set_alpha(g)
        ax.yaxis.label.set_alpha(g)
        for a in leg_artists:
            a.set_alpha(g)
        frames.append(grab())
    for gl in grids:
        gl.set_alpha(0.32)
    for tl in yticklabels:
        tl.set_alpha(1.0)
    ax.yaxis.label.set_alpha(1.0)
    for a in leg_artists:
        a.set_alpha(1.0)

    # ---- Acts 1-2: SWE wave, then PM wave (assembly) ----
    assembly_len = SWE_WAVE + (n - 1) * co_stag + BOX_TOTAL + 16
    for f in range(assembly_len):
        for b in boxes:
            draw_box(b, f - b["t0"])
        for u in units:
            set_logo_alpha(u, eoc(clamp01((f - u["land"]) / 8.0)))
            if u["nm"] is not None:
                u["nm"].set_alpha(eoc(clamp01((f - u["land"]) / 8.0)))
        frames.append(grab())
    for b in boxes:
        draw_box(b, BOX_TOTAL + 5); snapshot(b)
    for u in units:
        set_logo_alpha(u, 1.0)
        if u["nm"] is not None:
            u["nm"].set_alpha(1.0)

    # ---- Act 3: reorder into GAP order (SWE-wins left -> PM-wins right) ----
    order = sorted(range(n), key=lambda i: units[i]["gap"])          # ascending signed gap
    target_x = [0.0] * n
    for rank, ci in enumerate(order):
        target_x[ci] = rank * group_gap
    travel = [abs(target_x[ci] - units[ci]["xc"]) for ci in range(n)]
    maxtrav = max(travel) or 1.0
    REORD_F = 33
    for f in range(REORD_F):
        p = eio(clamp01((f + 1) / REORD_F))
        cf = 1 - clamp01(f / (REORD_F * 0.45))                       # callouts fade out — only shapes move
        for ci, u in enumerate(units):
            dx = (target_x[ci] - u["xc"]) * p
            dy = span * 0.05 * (travel[ci] / maxtrav) * np.sin(np.pi * p)   # sin-arc lift for movers
            u["sw"]["box"].set_zorder(4 + travel[ci]); u["pm"]["box"].set_zorder(4 + travel[ci])
            for b in (u["sw"], u["pm"]):
                b["tmed"].set_alpha(cf); b["tpq"].set_alpha(cf)
            place_unit(u, dx, dy)
        frames.append(grab())
    for ci, u in enumerate(units):                                  # settle exactly, re-snapshot at new home
        place_unit(u, target_x[ci] - u["xc"], 0.0)
        for b in (u["sw"], u["pm"]):
            b["tmed"].set_alpha(0.0); b["tpq"].set_alpha(0.0)
        snapshot(u["sw"]); snapshot(u["pm"])
        u["cx"] = target_x[ci]
    for _ in range(14):                                             # a clean, unlabeled breath before the payoff
        frames.append(grab())

    # ---- Act 4: gap connectors fire top-down in unison + hero stat ----
    conns = []
    for u in units:
        cx = u["cx"]; mlo, mhi = min(u["medS"], u["medP"]), max(u["medS"], u["medP"])
        win = PM_WIN if u["gap"] > 0 else SW_WIN
        ln, = ax.plot([cx, cx], [mhi, mhi], color=win, lw=3.8 * (1 + 0.35 * (legend_scale - 1)),
                      solid_capstyle="round", zorder=7, alpha=0.0)
        tx = ax.text(cx, u["ry_top"], "", ha="center", va="bottom", color=win, fontsize=12.5 * legend_scale,
                     fontweight=800, zorder=9, bbox=halo, alpha=0.0)
        conns.append(dict(ln=ln, tx=tx, u=u, mlo=mlo, mhi=mhi, gap=u["gap"]))
    hero_t = ax.text(0.5, 0.9, hero_stat, transform=ax.transAxes, ha="center", va="center",
                     fontsize=hero_fs, fontweight=800, color=INK, zorder=13, alpha=0.0,
                     bbox=dict(boxstyle="round,pad=0.5", fc=CREAM, ec="none", alpha=0.92))
    hero_s = ax.text(0.5, 0.842, hero_sub, transform=ax.transAxes, ha="center", va="center",
                     fontsize=hero_sub_fs, fontweight=700, color=SUB, zorder=13, alpha=0.0,
                     bbox=dict(boxstyle="round,pad=0.3", fc=CREAM, ec="none", alpha=0.92)) if hero_sub else None
    GAP_F = 22
    for f in range(GAP_F):
        p = eoc(clamp01((f + 1) / GAP_F))
        for a in leg_artists:                                        # legend yields the top to the hero stat
            a.set_alpha(1 - p)
        for c in conns:                                              # connectors fire top-down, deltas count up
            c["ln"].set_ydata([c["mhi"], c["mhi"] - (c["mhi"] - c["mlo"]) * p]); c["ln"].set_alpha(1.0)
            val = round(abs(c["gap"]) * p)
            c["tx"].set_text(("+" if c["gap"] > 0 else "−") + fmt(val)); c["tx"].set_alpha(p)
        frames.append(grab())
    for a in leg_artists:
        a.set_alpha(0.0)
    for f in range(26):                                             # hero stat rises + rests
        p = eoc(clamp01((f + 1) / 12))
        hero_t.set_alpha(p); hero_t.set_position((0.5, 0.9 - 0.015 * (1 - p)))
        if hero_s is not None:
            hero_s.set_alpha(p)
        frames.append(grab())
    for _ in range(40):                                             # long rest on the thesis frame
        frames.append(grab())

    base_ms = int(round(1000 / fps))
    durations = [base_ms] * (len(frames) - 1) + [1400]
    pal = frames[-1].quantize(colors=palette_colors, method=Image.MEDIANCUT)
    framesP = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    framesP[0].save(out_path, save_all=True, append_images=framesP[1:], loop=0,
                    duration=durations, optimize=True, disposal=2)
    if mp4:
        _frames_to_mp4(frames, os.path.splitext(out_path)[0] + ".mp4", fps, end_hold_s=1.4, crf=mp4_crf)
    plt.close(fig)
    print("wrote", out_path, f"({len(framesP)} frames @ {px}px, {fps}fps)")
    if qa_frames:
        stem = os.path.splitext(out_path)[0]
        a1 = intro_f + SWE_WAVE // 2; a2 = intro_f + assembly_len - 1
        a3 = a2 + REORD_F + 14; a4 = len(frames) - 1
        for tag, i in (("act1_swe", a1), ("act2_pm", a2), ("act3_reorder", a3), ("act4_gaps", a4)):
            frames[min(i, len(frames) - 1)].save(f"{stem}_{tag}.png"); print("  qa", f"{stem}_{tag}.png")
    return out_path
