#!/usr/bin/env python3
"""Worked example: company_strip — per-company pay ranges (boxplot + jittered raw points).

Pattern:
  1. Get RAW individual submissions per company (the dots ARE the data the box summarizes).
     Prefer the repo DB / API over the MCP distribution endpoint, which caps per-company
     samples (~30) and can skew high; the DB salary_percentile table matches the published
     site numbers. Verify a couple of medians against the MCP before publishing.
  2. Brand colors come straight from Levels' own company.color ("r,g,b" -> rgb_str()); logos
     from company_logo(domain) (cached under assets/company_logos/).
  3. Sort rows by ascending median for a clean ladder (first row renders at TOP).
  4. 6+ rows want the portrait format for vertical label room.
"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/levels-charts/lib"))
from levels_charts import (new_canvas, save, company_strip, company_logo, rgb_str,
                           set_format, STRIP_LEFT, STRIP_W)

set_format("portrait")

# (domain, brand_color "r,g,b", raw TC submissions in $K). In real use, points come from the DB.
DATA = [
    ("stripe.com",   "94,115,224", [300, 480, 543, 600, 667, 700, 753, 884, 980, 1152]),
    ("coinbase.com", "22,82,240",  [420, 495, 520, 540, 562, 570, 575, 636, 690, 770]),
    ("robinhood.com","33,206,153", [276, 450, 525, 535, 552, 565, 580, 602, 650, 841]),
]

rows = []
for domain, color, pts in DATA:
    med = sorted(pts)[len(pts) // 2]
    logo = company_logo(domain)
    rows.append(((logo if logo is not None else domain.split(".")[0]),
                 pts, rgb_str(color), med))
rows.sort(key=lambda r: r[3])
rows = [(lbl, pts, c) for (lbl, pts, c, _) in rows]

fig, ax = new_canvas(
    "Senior SWE Pay Ranges",
    "US Senior (L4) software engineer total comp, last 24 months.\n"
    "Each dot is one submission; the box spans p25 to p75 with the median marked.",
    "Source: Levels.fyi. Illustrative example.",
    left=STRIP_LEFT, width=STRIP_W, bottom=0.150)

company_strip(ax, rows, xticks=[200, 400, 600, 800, 1000, 1200], xmin=120, xmax=1240,
              jitter=0.16, box_h=0.38)

save(fig, os.path.expanduser("~/Downloads/example_strip.png"))
