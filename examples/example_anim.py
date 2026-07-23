#!/usr/bin/env python3
"""Worked example for the levels-charts animation sub-skill.

Renders one animated "value over time" GIF (line draws itself, value tag climbs,
a milestone fades in, settles on the final callout). Copy + swap in your data.

Run:  python3 example_anim.py [OUT_DIR]      (default: ./levels-charts-example)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from levels_charts import *                 # colors, money, presets
from levels_charts_anim import animate_value_line

OUT = sys.argv[1] if len(sys.argv) > 1 else "levels-charts-example"

# Illustrative: an equity grant climbing over four years to an IPO.
animate_value_line(
    os.path.join(OUT, "ex_value_line.gif"),
    title="A $365K grant\nbecame about $4.2M",
    subtitle="An illustrative value-over-time line that draws itself, with the\n"
             "value climbing on the tip and a milestone marked on the timeline.",
    source="Source: Levels.fyi · illustrative example data.",
    x=[2022.6, 2023.96, 2024.96, 2025.54, 2025.96, 2026.10, 2026.45],
    y=[365, 506, 965, 1105, 2195, 2743, 4196],     # $K (money() formats these)
    xticks=[2023, 2024, 2025, 2026], xlim=(2022.45, 2027.15),
    ymin=0, ymax=4750, yticks=[0, 1000, 2000, 3000, 4000],
    yticklabels=["$0", "$1M", "$2M", "$3M", "$4M"],
    start_note="Start: Aug 2022\nat $70 / share",
    vmarkers=[(2026.10, "Milestone event\nFeb 2026", AMBER)],
    end_label="≈ $4.2M\nat IPO", end_color=GREEN,
    seconds=4.5, fps=20, hold=1.4, px=900, qa_frames=True,
)
print("DONE ->", os.path.abspath(OUT))
