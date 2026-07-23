#!/usr/bin/env python3
"""Worked example for the levels-charts skill — one chart per builder.

Run:  python3 example_pack.py [OUT_DIR]      (default: ./levels-charts-example)
Use this as a copy-paste template: pick the builder that matches your data shape,
swap in your numbers + headline, and render. (Data below is illustrative.)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from levels_charts import *   # new_canvas, save, builders, palette, money/pct

OUT = sys.argv[1] if len(sys.argv) > 1 else "levels-charts-example"
SRC = "Source: Levels.fyi · illustrative example data."

# 1) LINE — multi-series time trend with direct end-of-line labels (the canonical look)
def ex_line():
    fig, ax = new_canvas("Adoption keeps climbing",
        "An illustrative multi-line trend with direct end-of-line labels.", SRC,
        left=VBAR_LEFT, width=VBAR_W)
    x = list(range(2021, 2027))
    series = [
        ("Overall", [22, 31, 38, 44, 49, 54], INK),
        ("Product A", [18, 27, 33, 36, 40, 41], BLUE),
        ("Product B", [2, 4, 7, 12, 22, 39], AMBER),
        ("Product C", [5, 6, 6, 7, 7, 8], RED),
    ]
    line(ax, x, series, ymax=60, xticks=x,
         label_offsets={"Overall": 1.2, "Product A": 1.8, "Product B": -2.2})
    ax.set_yticks([0, 20, 40, 60]); ax.set_yticklabels(["0", "20", "40", "60%"])
    save(fig, os.path.join(OUT, "ex_line.png"))

# 2) GROUPED VBAR — two series + a per-group delta callout + in-plot legend
def ex_grouped():
    fig, ax = new_canvas("The gap widens with seniority",
        "Two series compared at each level, with the premium called out above.", SRC)
    grouped_vbar(ax, ["L1", "L2", "L3", "L4", "L5"],
                 [("Baseline", [160, 212, 281, 373, 496], GRAYBAR),
                  ("Specialist", [185, 258, 361, 505, 706], BLUE)],
                 delta=[16, 22, 28, 35, 43], delta_fmt=lambda d: f"+{d}%")
    save(fig, os.path.join(OUT, "ex_grouped_vbar.png"))

# 3) VBAR — single series with negatives (labels flip below the zero line)
def ex_vbar_neg():
    fig, ax = new_canvas("A discount that fades with level",
        "Single-series vertical bars; negative values label below the axis.", SRC)
    vbar(ax, ["L1", "L2", "L3", "L4", "L5"], [-20.5, -16.7, -12.7, -8.5, -4.2],
         [RED, "#D9626F", "#DC8088", "#D9A6A3", "#CFC2B5"],
         fmt=lambda v: pct(v), zero_line=True)
    save(fig, os.path.join(OUT, "ex_vbar_negative.png"))

# 4) HBAR — ranked horizontal bars with a 'for reference' divider group
def ex_hbar():
    fig, ax = new_canvas("Ranked leaderboard",
        "Horizontal bars, highest first, with a reference group set apart below.", SRC,
        left=0.235, width=0.59)
    rows = [("Alpha", 1025, NAVY), ("Bravo", 982, BLUE), ("Charlie", 887, BLUE),
            ("Delta", 684, SLATEBAR), ("Echo", 675, BLUE),
            ("Foxtrot", 579, RED, RED), ("Golf", 409, RED, RED)]
    hbar(ax, rows, divider_after=4, divider_label="— for reference —",
         xticks=[0, 250, 500, 750, 1000])
    save(fig, os.path.join(OUT, "ex_hbar.png"))

# 5) DUMBBELL — p10–p90 range + median dot, with vertical reference lines
def ex_dumbbell():
    fig, ax = new_canvas("The range explodes as you climb",
        "p10–p90 spread with the median as a dot; dashed lines mark references.", SRC,
        left=RANGE_LEFT, width=RANGE_W)
    data = [[99, 124, 160, 191, 212], [118, 153, 212, 273, 325],
            [141, 188, 281, 389, 498], [168, 232, 373, 555, 764],
            [200, 285, 495, 792, 1172]]
    dumbbell(ax, ["L1", "L2", "L3", "L4", "L5"], data,
             colors=[SKY, BLUE, BLUE, NAVY, NAVY], lo_label=True,
             xticks=[0, 250, 500, 750, 1000, 1250],
             refs=[(500, "reference  $500K", RED)])
    save(fig, os.path.join(OUT, "ex_dumbbell.png"))

# 6) STACKED100 — part-to-whole across rows, with in-plot legend + a note below
def ex_stacked():
    fig, ax = new_canvas("Composition varies by group",
        "100%-stacked bars; legend sits inside the plot, note below the bars.", SRC,
        left=HBAR_LEFT, width=HBAR_W)
    stacked100(ax, [("Group A", [36, 64]), ("Group B", [55, 45]),
                    ("Group C", [100, 0]), ("Group D", [92, 8])],
               [GREEN, AMBER], ["Share one", "Share two"],
               top_pad=1.0, bottom_pad=0.8)
    ax.text(0.0, 0.16, "A note placed in the bottom headroom, inside the plot.",
            transform=ax.transAxes, fontsize=15, fontweight=600, color=SUB, va="top")
    save(fig, os.path.join(OUT, "ex_stacked100.png"))

if __name__ == "__main__":
    for fn in [ex_line, ex_grouped, ex_vbar_neg, ex_hbar, ex_dumbbell, ex_stacked]:
        fn()
    print("DONE ->", os.path.abspath(OUT))
