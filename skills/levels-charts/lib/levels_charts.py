#!/usr/bin/env python3
"""levels_charts — Levels.fyi editorial chart engine.

Reusable styling + builders for social-ready PNG charts (1080x1350 @2x) in the
Ramp-style editorial layout on Levels brand. Self-contained: it loads its own
bundled fonts + logo (resolved relative to THIS file) so it works from any cwd.

Quick start
-----------
    import sys; sys.path.insert(0, "<this-skill>/lib")
    from levels_charts import *
    fig, ax = new_canvas("Headline line one\\nline two",
                         "One- or two-line subtitle in gray.",
                         "Source: ...")
    vbar(ax, ["L1","L2","L3"], [160, 212, 281], BLUE)
    save(fig, "out/my_chart.png")

The frame (title -> subtitle -> chart -> footer with source + logo) is drawn by
new_canvas(); you only draw the data with one of the builders below.
"""
import io, os, urllib.request
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

# ---------------------------------------------------------------- assets
_LIB   = Path(__file__).resolve().parent
_SKILL = _LIB.parent
FONTS_DIR = _SKILL / "assets" / "fonts"
LOGO_PNG  = _SKILL / "assets" / "levels_logo_grey.png"   # bundled raster (primary, no native deps)
LOGO_SVG  = _SKILL / "assets" / "levels_logo_grey.svg"   # kept for the optional cairosvg fallback

# Fonts are required; the logo may be supplied as either the bundled PNG or the SVG.
_missing = [str(p) for p in (FONTS_DIR,) if not p.exists()]
if not LOGO_PNG.exists() and not LOGO_SVG.exists():
    _missing.append(str(LOGO_PNG))
if _missing:
    raise FileNotFoundError(
        "levels_charts: missing brand assets: " + ", ".join(_missing)
        + "\nRun the skill's scripts/setup_assets.sh to fetch them.")
for _f in sorted(FONTS_DIR.glob("*.ttf")):
    fm.fontManager.addfont(str(_f))
plt.rcParams.update({"font.family": "Nunito", "axes.unicode_minus": False,
                     "text.parse_math": False})  # parse_math off: '$' stays literal

# ---------------------------------------------------------------- palette
CREAM="#F4F3EC"; INK="#1A1712"; SUB="#5B6268"; GRID="#DCD9CE"; MUTE="#A39C90"
BLUE="#0060B9"; NAVY="#00407B"; SKY="#4F9BDC"; GREEN="#1E9E6A"; AMBER="#E08A1E"
RED="#D1495B"; GRAYBAR="#CBC5B6"; SLATEBAR="#808C93"; PALE="#E6F1FB"
# default series order for multi-series charts
PALETTE=[BLUE, AMBER, GREEN, NAVY, RED, SKY, SLATEBAR, GRAYBAR]

# ---------------------------------------------------------------- geometry
DPI = 200
LEFT = 0.072                     # left text margin (title/subtitle/source) — format-independent
# plot-left / width presets by chart family (fractions of WIDTH — both formats share width):
VBAR_LEFT=0.085; VBAR_W=0.86     # vertical bars / lines (bare y-axis)
RANGE_LEFT=0.105; RANGE_W=0.80   # dumbbell / range plots (short y category labels)
HBAR_LEFT=0.165; HBAR_W=0.66     # horizontal bars (room for long row labels on the left)
STRIP_LEFT=0.150; STRIP_W=0.80   # company strip / boxplot (logo gutter on the left)

# Output formats. "square" (1080x1080 @2x) is the DEFAULT — denser, most social-friendly,
# header condensed at top. "portrait" (1080x1350 @2x) is the original 4:5 layout.
# Both share the same WIDTH (FW=10.8); only the vertical rhythm differs.
_FORMATS = {
    "square":   dict(FW=10.8, FH=10.8, TITLE_Y=0.940, TITLE_LH=0.052, SUB_GAP=0.014,
                     SUB_LH=0.030, PLOT_GAP=0.050, FOOTER_TOP=0.118, SRC_Y=0.052,
                     TITLE_FS=35, SUB_FS=18.5),
    "portrait": dict(FW=10.8, FH=13.5, TITLE_Y=0.957, TITLE_LH=0.042, SUB_GAP=0.012,
                     SUB_LH=0.024, PLOT_GAP=0.040, FOOTER_TOP=0.110, SRC_Y=0.052,
                     TITLE_FS=35, SUB_FS=18),
    # "a4" = tall 1:1.414 page (2160x3054 @2x). Header/footer fractions are scaled DOWN from
    # portrait (by 13.5/15.27) so they stay the same ABSOLUTE size while the extra height all
    # goes to the plot — maximum vertical breathing room for many-row charts.
    "a4":       dict(FW=10.8, FH=15.27, TITLE_Y=0.962, TITLE_LH=0.0371, SUB_GAP=0.0106,
                     SUB_LH=0.0212, PLOT_GAP=0.0354, FOOTER_TOP=0.0973, SRC_Y=0.0460,
                     TITLE_FS=35, SUB_FS=18),
    # "tall" = extra-tall page (2160x4000 @2x, 1:1.85) for many-row charts (e.g. 20 grouped
    # boxplot rows with tall boxes). Header/footer fractions scaled from portrait by 13.5/20 to stay compact.
    "tall":     dict(FW=10.8, FH=20.0, TITLE_Y=0.9710, TITLE_LH=0.0284, SUB_GAP=0.0081,
                     SUB_LH=0.0162, PLOT_GAP=0.0270, FOOTER_TOP=0.0743, SRC_Y=0.0351,
                     TITLE_FS=35, SUB_FS=18),
    # "wide" = landscape 3:2 page (3240x2160 @2x) for horizontal charts (transposed vertical
    # boxplots, or multi-column layouts). Shares square's VERTICAL rhythm (FH=10.8); only FW grows.
    "wide":     dict(FW=16.2, FH=10.8, TITLE_Y=0.940, TITLE_LH=0.052, SUB_GAP=0.014,
                     SUB_LH=0.030, PLOT_GAP=0.050, FOOTER_TOP=0.118, SRC_Y=0.052,
                     TITLE_FS=35, SUB_FS=18.5),
}
FORMAT = None
def set_format(name):
    """Switch output format: 'square' (default), 'portrait', or 'a4' (tall 1:1.414 page with
    a compact header — for many-row charts that need breathing room). Call once after import,
    before any new_canvas(). Updates module geometry globals + re-derives PLOT_BOT."""
    global FORMAT
    if name not in _FORMATS:
        raise ValueError(f"unknown format {name!r}; choose from {list(_FORMATS)}")
    g = globals()
    for k, v in _FORMATS[name].items(): g[k] = v
    g["PLOT_BOT"] = g["FOOTER_TOP"] + 0.025   # default chart bottom, just above footer
    FORMAT = name
set_format("square")             # default

# ---------------------------------------------------------------- logo (in-memory)
# Self-contained: load the bundled PNG with Pillow (no native deps). If only the SVG
# is present, fall back to cairosvg *if it happens to be installed* — purely optional.
_LOGO_W_PX = 360                              # placed watermark width (figimage native px)
def _load_logo_arr():
    if LOGO_PNG.exists():
        img = Image.open(LOGO_PNG).convert("RGBA")
    else:                                     # optional fallback, only if cairosvg is available
        try:
            import cairosvg
        except Exception as e:
            raise FileNotFoundError(
                "levels_charts: no bundled logo PNG at " + str(LOGO_PNG)
                + " and cairosvg is unavailable to rasterize the SVG. "
                + "Run scripts/setup_assets.sh.") from e
        img = Image.open(io.BytesIO(
            cairosvg.svg2png(url=str(LOGO_SVG), output_width=_LOGO_W_PX * 3))).convert("RGBA")
    if img.width != _LOGO_W_PX:               # normalize to the placed size (LANCZOS = crisp supersample)
        img = img.resize((_LOGO_W_PX, round(img.height * _LOGO_W_PX / img.width)), Image.LANCZOS)
    return np.asarray(img)
LOGO_ARR = _load_logo_arr()
_LOGO_YO, _LOGO_PADR = 72, 72

# ---------------------------------------------------------------- company logos
# Company logos are an OPTIONAL convenience (used as row labels in `company_strip`).
# They are fetched on demand from logo.dev and cached under assets/company_logos/.
# BRING YOUR OWN KEY: set your logo.dev publishable token in the environment.
#   export LOGO_DEV_TOKEN="pk_your_token"        # free at https://logo.dev
# Some logo.dev keys are domain-allowlisted; if so, also set the allowed Referer:
#   export LOGO_DEV_REFERER="https://yourdomain.com"
# Without a token, company_logo() just returns None (fall back to a text label).
LOGO_DEV_TOKEN   = os.environ.get("LOGO_DEV_TOKEN", "")
LOGO_DEV_REFERER = os.environ.get("LOGO_DEV_REFERER", "")
COMPANY_LOGO_DIR = _SKILL / "assets" / "company_logos"
_logo_dev_warned = False
def company_logo(domain, *, size=256, greyscale=False, refresh=False):
    """Fetch a company's brand logo by domain (e.g. 'stripe.com') from logo.dev,
    cache it under assets/company_logos/, and return an RGBA ndarray (None on failure).
    Pass the result straight to company_strip() as a row label. Requires a logo.dev
    token in $LOGO_DEV_TOKEN (see the note above); returns None if it isn't set."""
    global _logo_dev_warned
    COMPANY_LOGO_DIR.mkdir(parents=True, exist_ok=True)
    tag = domain.replace("/", "_") + ("_grey" if greyscale else "") + f"_{size}.png"
    cache = COMPANY_LOGO_DIR / tag
    if cache.exists() and not refresh:
        return np.asarray(Image.open(cache).convert("RGBA"))
    if not LOGO_DEV_TOKEN:
        if not _logo_dev_warned:
            print("company_logo: set $LOGO_DEV_TOKEN (free key at https://logo.dev) to fetch "
                  "brand logos; using text labels until then.")
            _logo_dev_warned = True
        return None
    url = (f"https://img.logo.dev/{domain}?token={LOGO_DEV_TOKEN}&size={size}&format=png"
           + ("&greyscale=true" if greyscale else ""))
    try:
        headers = {"User-Agent": "levels-charts/1.0"}
        if LOGO_DEV_REFERER:                     # only if the key is Referer-allowlisted
            headers["Referer"] = LOGO_DEV_REFERER
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=15).read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.save(cache)
        return np.asarray(img)
    except Exception as e:
        print(f"company_logo: failed for {domain!r}: {e}")
        return None

def rgb_str(s, fallback="#0060B9"):
    """Levels company.color -> hex. Accepts a list/tuple [94,115,224], a '94,115,224'
    string, or '[94, 115, 224]' (how pg JSON-serializes the column). Fallback if unparseable."""
    try:
        if isinstance(s, (list, tuple)):
            r, g, b = [int(x) for x in s[:3]]
        else:
            parts = str(s).replace("[", "").replace("]", "").split(",")
            r, g, b = [int(float(x)) for x in parts[:3]]
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return fallback

def logo_color(arr, fallback="#0060B9"):
    """Dominant vivid brand color from an RGBA logo ndarray (from company_logo()).
    Picks the most common saturated, opaque, non-white color; for a black/gray mark
    (no saturated pixels) returns its darkest opaque color."""
    a = np.asarray(arr)
    if a.ndim != 3 or a.shape[2] < 3:
        return fallback
    rgb = a[..., :3].reshape(-1, 3).astype(float)
    alpha = a[..., 3].reshape(-1) if a.shape[2] == 4 else np.full(rgb.shape[0], 255.0)
    mx, mn = rgb.max(1), rgb.min(1)
    colorful = (alpha > 200) & ((mx - mn) > 40) & (mx > 40) & (mx < 250)
    if colorful.sum() >= 10:
        q = (rgb[colorful] // 32 * 32 + 16).astype(int)
        uniq, counts = np.unique(q, axis=0, return_counts=True)
        c = uniq[counts.argmax()]
    else:
        opaque = alpha > 200
        if not opaque.any():
            return fallback
        c = rgb[opaque][rgb[opaque].sum(1).argmin()]
    return "#%02X%02X%02X" % tuple(int(min(255, max(0, v))) for v in c)

# ---------------------------------------------------------------- formatters
def money(k):
    """Value in THOUSANDS -> '$160K' / '$1.02M'.  money(160)->$160K, money(1025)->$1.02M"""
    if abs(k) >= 1000:
        return f"${f'{k/1000.0:.2f}'.rstrip('0').rstrip('.')}M"
    return f"${k:.0f}K"

def pct(v, signed=True):
    """44 -> '+44%' (signed) ; use signed=False for plain '44%'. Uses a real minus (−)."""
    s = f"{v:+.0f}%" if signed else f"{abs(v):.0f}%"
    return s.replace("-", "−")

def _wrap(text, max_chars):
    out = []
    for para in text.split("\n"):
        line = ""
        for w in para.split(" "):
            cand = w if not line else line + " " + w
            if len(cand) > max_chars and line:
                out.append(line); line = w
            else:
                line = cand
        out.append(line)
    return "\n".join(out)

def _fit_to_width(fig, txt, right=0.955):
    """Clamp a header Text object to the page: shrink its font until the widest line fits
    between LEFT and `right` (figure fraction). Measured, so it never clips regardless of font."""
    try:
        r = fig.canvas.get_renderer()
    except Exception:
        return
    max_px = (right - LEFT) * fig.get_figwidth() * fig.dpi
    for _ in range(14):
        if txt.get_window_extent(renderer=r).width <= max_px or txt.get_fontsize() <= 9:
            return
        txt.set_fontsize(txt.get_fontsize() * 0.96)

# ---------------------------------------------------------------- frame
def new_canvas(title, subtitle, source, *, left=None, width=None,
               bottom=None, top_pad=None, src_wrap=78, sub_wrap=76, add_axes=True, src_y=None):
    """Draw the editorial frame and return (fig, ax) for the plot area.

    The plot TOP is derived from the header height (title + subtitle line counts),
    so the chart always sits just under the subtitle — never hardcode a rect.
    `left`/`width` pick the horizontal plot box (use the *_LEFT / *_W presets).
    Title/subtitle may contain explicit \\n line breaks; keep title <=2 lines and
    subtitle <=2 lines for the intended density. Geometry follows the active
    format (see set_format); defaults resolve at call time so it tracks the format.
    With add_axes=False, returns (fig, (left, bottom, width, height)) instead of adding
    the axes — for multi-panel layouts that split the plot rect into several axes.
    """
    left = VBAR_LEFT if left is None else left
    width = VBAR_W if width is None else width
    bottom = PLOT_BOT if bottom is None else bottom
    top_pad = PLOT_GAP if top_pad is None else top_pad
    subtitle = _wrap(subtitle, sub_wrap)      # reflow long subtitles to full-size lines (clamp is the net)
    n_t = title.count("\n") + 1
    fig = plt.figure(figsize=(FW, FH), dpi=DPI); fig.patch.set_facecolor(CREAM)
    tobj = fig.text(LEFT, TITLE_Y, title, fontsize=TITLE_FS, fontweight=800, color=INK,
                    va="top", ha="left", linespacing=1.04)
    _fit_to_width(fig, tobj)
    sub_y = TITLE_Y - n_t*TITLE_LH - SUB_GAP
    sobj = fig.text(LEFT, sub_y, subtitle, fontsize=SUB_FS, fontweight=600, color=SUB,
                    va="top", ha="left", linespacing=1.3)
    _fit_to_width(fig, sobj)
    # footer: source bottom-left (wrapped so it never reaches the logo); logo bottom-right
    fig.text(LEFT, SRC_Y if src_y is None else src_y, _wrap(source, src_wrap), fontsize=11.5,
             fontweight=600, color=MUTE, va="bottom", ha="left", linespacing=1.34)
    fig.figimage(LOGO_ARR, xo=int(FW*DPI-LOGO_ARR.shape[1]-_LOGO_PADR),
                 yo=_LOGO_YO, zorder=30, alpha=0.95)
    sub_bot = sub_y - (subtitle.count("\n")+1)*SUB_LH
    top = sub_bot - top_pad
    if not add_axes:
        return fig, (left, bottom, width, top - bottom)
    ax = fig.add_axes((left, bottom, width, top - bottom)); ax.set_facecolor(CREAM)
    return fig, ax

# ---------------------------------------------------------------- styling helpers
def clean(ax, grid="y"):
    """Strip spines/ticks, add a light grid on the chosen axis ('x'|'y'|'both'|None)."""
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    axes_for = {"x": ["x"], "y": ["y"], "both": ["x", "y"]}.get(grid, [])
    for g in axes_for:
        ax.grid(axis=g, color=GRID, linewidth=1.1, zorder=0)
    if axes_for: ax.set_axisbelow(True)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontweight(700); lab.set_color("#7C8288"); lab.set_fontsize(15)

def cat_labels(ax, axis="x", size=18, color=INK, weight=800):
    """Restyle the CATEGORY tick labels (call after set_xticklabels/set_yticklabels)."""
    labs = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
    for l in labs:
        l.set_fontsize(size); l.set_color(color); l.set_fontweight(weight)

def legmark(ax, x, y, color, label, outline=False, size=14):
    """One legend swatch + label at axes-fraction (x, y). Draw legends INSIDE the
    plot (give the axes ylim headroom first) — never above, where they hit the subtitle."""
    if outline:
        ax.scatter([x], [y], s=150, facecolors="none", edgecolors=color, lw=2.4,
                   marker="s", transform=ax.transAxes, clip_on=False, zorder=12)
    else:
        ax.scatter([x], [y], s=185, color=color, marker="o",
                   transform=ax.transAxes, clip_on=False, zorder=12)
    ax.text(x+0.028, y, label, transform=ax.transAxes, fontsize=size,
            fontweight=800, color=color, va="center", ha="left")

def legend_row(ax, items, y=0.95, x0=0.0, dx=0.30):
    """Horizontal legend inside the plot. items: list of (color,label[,outline])."""
    x = x0
    for it in items:
        color, label = it[0], it[1]
        outline = it[2] if len(it) > 2 else False
        legmark(ax, x, y, color, label, outline=outline)
        x += dx

def save(fig, path):
    """Save PNG at full res to `path` (absolute or relative). Creates parent dirs."""
    path = os.fspath(path)
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=CREAM); plt.close(fig); print("wrote", path)

# ================================================================ builders
def vbar(ax, cats, values, colors=BLUE, *, fmt=money, ymax=None, ymin=None,
         label=True, label_color=None, cat_size=18, zero_line=False, pad=0.16):
    """Single-series vertical bars (supports negative values; labels flip below 0)."""
    x = np.arange(len(cats))
    cols = [colors]*len(cats) if isinstance(colors, str) else list(colors)
    ax.bar(x, values, 0.6, color=cols, zorder=3)
    if zero_line: ax.axhline(0, color="#B9B4A6", lw=1.6, zorder=2)
    vmax = max(list(values) + [0]); vmin = min(list(values) + [0]); span = (vmax - vmin) or 1
    ax.set_ylim(vmin - (span*pad if vmin < 0 else 0) if ymin is None else ymin,
                vmax + span*pad if ymax is None else ymax)
    if label:
        off = span*0.02
        for xi, v in zip(x, values):
            c = label_color or (cols[xi] if cols[xi] != GRAYBAR else "#8a857a")
            ax.text(xi, v + (off if v >= 0 else -off), fmt(v), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=15, fontweight=800, color=c)
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_yticks([]); clean(ax, grid=None)
    cat_labels(ax, "x", cat_size)
    return x

def grouped_vbar(ax, cats, series, *, fmt=money, ymax=None, width=0.38, cat_size=18,
                 legend=True, legend_y=0.94, delta=None, delta_fmt=None):
    """Grouped vertical bars. series: list of (name, values, color).
    `delta`: optional one-per-category callout drawn above each group (e.g. a premium %)."""
    x = np.arange(len(cats)); n = len(series)
    offs = (np.arange(n) - (n-1)/2) * width
    vmax = max(v for _, vals, _ in series for v in vals)
    ax.set_ylim(0, vmax*1.20 if ymax is None else ymax)
    for (name, vals, color), off in zip(series, offs):
        ax.bar(x+off, vals, width, color=color, zorder=3)
        for xi, v in zip(x, vals):
            c = NAVY if color == BLUE else (color if color != GRAYBAR else "#8a857a")
            ax.text(xi+off, v + vmax*0.012, fmt(v), ha="center", va="bottom",
                    fontsize=12.5, fontweight=(700 if color == GRAYBAR else 800), color=c)
    if delta is not None:
        for xi, d in zip(x, delta):
            top = max(s[1][xi] for s in series)
            ax.text(xi, top + vmax*0.085, delta_fmt(d) if delta_fmt else f"+{d}%",
                    ha="center", fontsize=15, fontweight=800, color=GREEN)
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_yticks([]); clean(ax, grid=None)
    cat_labels(ax, "x", cat_size)
    if legend: legend_row(ax, [(s[2], s[0]) for s in series], y=legend_y)
    return x

def hbar(ax, rows, *, fmt=money, xmax=None, xticks=None, bar_h=0.62, name_size=15.5,
         divider_after=None, divider_label=None):
    """Horizontal bars, FIRST row at TOP. rows: (name, value, bar_color[, name_color]).
    Optional dashed divider + caption inserted after row index `divider_after`
    (use it to set a 'for reference' group apart, like FAANG below AI labs)."""
    vals = [r[1] for r in rows]
    xmax = xmax or max(vals)*1.16
    total = len(rows) + (1 if divider_after is not None else 0)
    y = total - 1
    for i, r in enumerate(rows):
        name, val, col = r[0], r[1], r[2]; ncol = r[3] if len(r) > 3 else INK
        ax.barh(y, val, height=bar_h, color=col, zorder=3)
        ax.text(val + xmax*0.012, y, fmt(val), va="center", ha="left",
                fontsize=14, fontweight=800, color=col)
        ax.text(-xmax*0.015, y, name, va="center", ha="right",
                fontsize=name_size, fontweight=800, color=ncol)
        y -= 1
        if divider_after is not None and i == divider_after:
            ax.axhline(y + 0.5, color="#CFC9BA", lw=1.2, ls=(0, (4, 3)))
            if divider_label:
                ax.text(0, y, divider_label, va="center", ha="left",
                        fontsize=12.5, fontweight=700, color=MUTE)
            y -= 1
    ax.set_xlim(0, xmax); ax.set_ylim(-0.7, total - 0.3); ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])

def dumbbell(ax, cats, data, *, fmt=money, color=BLUE, colors=None, xmax=None,
             xticks=None, refs=None, median_label=True, lo_label=False, cat_size=18):
    """Range / dumbbell plot, FIRST cat at BOTTOM. Each `data` row is one of:
        [lo, hi]                       -> single range bar
        [lo, median, hi]               -> range bar + median dot
        [p10, p25, p50, p75, p90]      -> thin p10-p90 + thick IQR + median dot
    `refs`: list of (x, label, color) vertical dashed reference lines."""
    n = len(cats); ys = np.arange(n)
    cols = colors or [color]*n
    flat = [v for d in data for v in d]; xmax = xmax or max(flat)*1.12
    for y, d, c in zip(ys, data, cols):
        med = None
        if len(d) == 5:
            lo, q1, med, q3, hi = d
            ax.plot([lo, hi], [y, y], color=c, lw=4, solid_capstyle="round", alpha=.40, zorder=2)
            ax.plot([q1, q3], [y, y], color=c, lw=11, solid_capstyle="round", alpha=.9, zorder=3)
        elif len(d) == 3:
            lo, med, hi = d
            ax.plot([lo, hi], [y, y], color=c, lw=10, solid_capstyle="round", alpha=.92, zorder=3)
        else:
            lo, hi = d
            ax.plot([lo, hi], [y, y], color=c, lw=10, solid_capstyle="round", alpha=.92, zorder=3)
        if med is not None:
            ax.scatter([med], [y], s=140, color="white", edgecolor=c, lw=2.8, zorder=5)
            if median_label:
                ax.text(med, y+0.24, fmt(med), va="bottom", ha="center",
                        fontsize=12, fontweight=800, color=c)
        ax.text(hi + xmax*0.012, y, fmt(hi), va="center", ha="left",
                fontsize=13.5, fontweight=800, color=c)
        if lo_label:
            ax.text(lo - xmax*0.012, y, fmt(lo), va="center", ha="right",
                    fontsize=12.5, fontweight=700, color="#9aa0a4")
    top_pad = 0.45 if refs else 0.15
    if refs:
        for rx, rlabel, rcolor in refs:
            ax.axvline(rx, color=rcolor, lw=2, ls=(0, (5, 3)), zorder=1, alpha=.85)
            ax.text(rx, n - 0.9 + top_pad, rlabel, ha="center", va="bottom",
                    fontsize=11.5, fontweight=800, color=rcolor)
    ax.set_yticks(ys); ax.set_yticklabels(cats)
    ax.set_ylim(-0.6, n - 1 + top_pad + 0.35); ax.set_xlim(0, xmax); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    cat_labels(ax, "y", cat_size)

def stacked100(ax, rows, seg_colors, seg_labels=None, *, legend=True, legend_y=0.93,
               min_label=14, top_pad=1.0, bottom_pad=0.0):
    """100%-stacked horizontal bars, FIRST row at TOP. rows: (name, [seg_pcts...]).
    Give top_pad headroom for the in-plot legend; bottom_pad if you add a note below."""
    n = len(rows); y = n
    for name, segs in rows:
        y -= 1; left = 0
        for s, c in zip(segs, seg_colors):
            if s <= 0: continue
            ax.barh(y, s, left=left, height=0.6, color=c, zorder=3)
            if s >= min_label:
                ax.text(left + s/2, y, f"{s:.0f}%", va="center", ha="center",
                        fontsize=13.5, fontweight=800, color="white")
            left += s
        ax.text(-3, y, name, va="center", ha="right", fontsize=16, fontweight=800, color=INK)
    ax.set_xlim(0, 100); ax.set_ylim(-0.7 - bottom_pad, n - 0.3 + top_pad)
    ax.set_xticks([]); ax.set_yticks([]); clean(ax, grid=None)
    if legend and seg_labels:
        legend_row(ax, list(zip(seg_colors, seg_labels)), y=legend_y)

def line(ax, x, series, *, fmt=None, end_labels=True, label_dx=None, lw=3.0,
         label_offsets=None, xticks=None, xticklabels=None, ymax=None, ymin=0, grid="y",
         left_pad=0.045):
    """Multi-line time series with DIRECT end-of-line labels (the canonical look).
    series: list of (name, yvalues, color). `label_offsets`: {name: dy} to de-collide
    labels whose line ends are close. Leaves right padding for the labels, and a small
    left pad so the first x-label doesn't collide with the y-axis tick labels."""
    label_offsets = label_offsets or {}
    xr = max(x) - min(x); dx = label_dx if label_dx is not None else xr*0.015
    for name, ys, color in series:
        ax.plot(x, ys, color=color, lw=lw, solid_capstyle="round", zorder=3)
        if end_labels:
            ax.text(x[-1] + dx, ys[-1] + label_offsets.get(name, 0), name,
                    va="center", ha="left", fontsize=15, fontweight=800, color=color)
    ax.set_xlim(min(x) - xr*left_pad, max(x) + xr*0.14)
    if ymax is not None: ax.set_ylim(ymin, ymax)
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels(xticklabels or [str(t) for t in xticks])
    clean(ax, grid=grid)
    cat_labels(ax, "x", 16)
    if fmt is not None:
        ax.set_yticklabels([fmt(t) for t in ax.get_yticks()])

def scatter(ax, points, *, label_dy=0.0, dot=300, grid="both"):
    """Labeled scatter. points: list of (x, y, label, color). Good for 2-axis stories
    (e.g. pay vs retention). Set axis limits/ticks yourself after calling."""
    for x, y, lab, c in points:
        ax.scatter([x], [y], s=dot, color=c, edgecolor="white", lw=1.6, zorder=4)
        ax.text(x, y + label_dy, lab, ha="center", va="bottom",
                fontsize=14, fontweight=800, color=c)
    clean(ax, grid=grid)

def company_strip(ax, rows, *, xticks=None, xmin=0, xmax=None, fmt=money,
                  jitter=0.20, box_h=0.42, dot=26, dot_alpha=0.5, logo_x=-0.085,
                  logo_px=92, med_label=True, edge_labels=True, seed=7, whisker=None, dot_max=None,
                  xlabel="Total Compensation ($K)", name_dy=0.34, name_size=10.5):
    """Per-company pay-distribution strip (the 'pay ranges by company' look). One row per
    company; each shows the raw submissions as jittered dots, an IQR box (p25-p75) with a
    median line, the median labelled above and p25/p75 below, on a shared x-axis. FIRST row
    at TOP — pass rows pre-sorted (e.g. ascending median) for a clean ladder.

    rows: list of (label, points, color[, name]):
      - label : an RGBA logo ndarray (from company_logo()) OR a string (drawn as text).
      - points: raw values in the units `fmt` formats (money() -> thousands; 213 == $213K).
      - color : the company's dot / box / median color (e.g. rgb_str(company.color)).
      - name  : OPTIONAL company name drawn under the logo (useful for less-famous logos).
    p25 / median / p75 / min / max are computed FROM `points`, so the dots are exactly the
    data the box summarizes (honest). Use STRIP_LEFT / STRIP_W in new_canvas, and give the
    axes a slightly higher `bottom` so the x-axis label clears the footer."""
    rng = np.random.default_rng(seed)
    n = len(rows); ys = list(range(n))[::-1]          # first row at top
    allpts = [v for r in rows for v in r[1]]
    xmax = xmax or max(allpts) * 1.06
    for y, r in zip(ys, rows):
        label, pts, color = r[0], r[1], r[2]
        name = r[3] if len(r) > 3 else None
        arr = np.asarray(sorted(pts), float)
        if whisker is None:                             # min-max, or percentile whiskers for skewed pay
            lo, hi = arr.min(), arr.max()
        else:
            lo, hi = (float(v) for v in np.percentile(arr, [whisker[0] * 100, whisker[1] * 100]))
        q1, med, q3 = np.percentile(arr, [25, 50, 75])  # box/median always from ALL points
        ax.plot([lo, hi], [y, y], color="#C9C3B4", lw=2.0, solid_capstyle="round", zorder=2)
        disp = arr[(arr >= xmin) & (arr <= (xmax if xmax else arr.max()))]   # dots within view only
        if dot_max and len(disp) > dot_max:             # subsample dense clouds (box uses all points)
            disp = rng.choice(disp, size=dot_max, replace=False)
        jy = y + rng.uniform(-jitter, jitter, size=len(disp))
        ax.scatter(disp, jy, s=dot, color=color, alpha=dot_alpha, edgecolors="none", zorder=3)
        ax.add_patch(Rectangle((q1, y - box_h/2), q3 - q1, box_h, facecolor=color,
                               alpha=0.20, edgecolor=color, linewidth=1.0, zorder=4))
        ax.plot([med, med], [y - box_h/2, y + box_h/2], color=color, lw=3.2,
                solid_capstyle="round", zorder=6)
        if med_label:
            ax.text(med, y + box_h/2 + 0.10, f"Med. {fmt(med)}", ha="center", va="bottom",
                    fontsize=13.5, fontweight=800, color=INK, zorder=7)
        if edge_labels:
            pad = (xmax - xmin) * 0.006                 # anchor outward so narrow boxes don't collide
            ax.text(q1 - pad, y - box_h/2 - 0.10, fmt(q1), ha="right", va="top",
                    fontsize=12, fontweight=800, color="#6f7479", zorder=7)
            ax.text(q3 + pad, y - box_h/2 - 0.10, fmt(q3), ha="left", va="top",
                    fontsize=12, fontweight=800, color="#6f7479", zorder=7)
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
    ax.set_xlim(xmin, xmax); ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    return ys

# discipline colors for the paired (two-role) strip — colorblind-safe blue/orange pair
DISC_SW = BLUE          # software = brand blue
DISC_HW = "#E07B27"     # hardware = warm orange (reads clearly on cream, distinct from blue)
def _hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _rgb2hex(t):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(c)))) for c in t)
def mix(c1, c2, t):
    """Linear blend of two hex colors; t in [0,1] moves from c1 toward c2."""
    a, b = _hex2rgb(c1), _hex2rgb(c2)
    return _rgb2hex(tuple(a[i] * (1 - t) + b[i] * t for i in range(3)))
def lighten(c, t=0.40): return mix(c, "#FFFFFF", t)
def darken(c, t=0.25):  return mix(c, "#000000", t)

def paired_strip(ax, rows, *, xticks=None, xmin=0, xmax=None, fmt=money,
                 colors=(DISC_SW, DISC_HW), per_company=False, sw_light=0.32, hw_dark=0.24,
                 disc_names=("Software", "Hardware"),
                 jitter=0.085, box_h=0.15, offset=0.19, dot=13, dot_alpha=0.50,
                 logo_x=-0.10, logo_px=66, seed=7, xlabel="Total Compensation ($K)",
                 name_dy=0.42, name_size=8.5, med_fs=10.5, delta_col=True,
                 delta_header=None, legend=True, legend_style="hue",
                 legend_xy=((0.52, 0.975), (0.73, 0.975))):
    """Two disciplines per company on ONE shared pay axis — a mirrored split strip.
    Each company is a lane: the first series (Software) fans UP from the lane center,
    the second (Hardware) fans DOWN, each as its own jittered-dot + IQR-box + median
    strip. A thin connector joins the two medians (it tilts toward whichever pays more),
    a faint band shades the dollar gap between them, and (delta_col) a right-hand column
    prints the signed gap. Pre-sort rows (e.g. ascending by the two-median average).

    Two color modes:
      - default (per_company=False): color encodes DISCIPLINE globally via `colors`
        (blue software / orange hardware); identity comes from the left logo.
      - per_company=True: each row carries its OWN base color (5th tuple element) and the
        two disciplines are two SHADES of it — software the LIGHTER shade (mix toward white,
        `sw_light`), hardware the DARKER (mix toward black, `hw_dark`). This keeps every
        company visually distinct while lightness separates the roles. Median/value/delta
        text switches to INK for legibility; pass legend_style="shade" for a neutral
        light/dark key (and encode the convention in the subtitle).

    rows: list of (label, swPoints, hwPoints[, name[, baseColor]]):
      - label     : RGBA logo ndarray (company_logo()) OR a string.
      - swPoints  : software raw values in `fmt` units (money() -> thousands).
      - hwPoints  : hardware raw values, same units.
      - name      : OPTIONAL company name drawn under the logo (keep SINGLE-LINE so it
                    doesn't reach the logo of the row below).
      - baseColor : per-company base hex (required when per_company=True)."""
    rng = np.random.default_rng(seed)
    n = len(rows); ys = list(range(n))[::-1]
    cS_g, cH_g = colors
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    xmax = xmax or max(allpts) * 1.06
    for y, r in zip(ys, rows):
        label = r[0]
        sw = np.asarray(sorted(r[1]), float); hw = np.asarray(sorted(r[2]), float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else None
        yS, yH = y + offset, y - offset
        medS = float(np.percentile(sw, 50)); medH = float(np.percentile(hw, 50))
        if per_company and base:
            cS = lighten(base, sw_light); cH = darken(base, hw_dark)
            cS_tick = lighten(base, sw_light * 0.55); cH_tick = cH      # keep the light median tick readable
            band_c, con_c = base, darken(base, hw_dark)
            lab_s = lab_h = delta_c = INK
        else:
            cS, cH = cS_g, cH_g; cS_tick, cH_tick = cS, cH
            win = cH if medH >= medS else cS
            band_c = con_c = delta_c = win; lab_s, lab_h = cS, cH
        gx0, gx1 = sorted((medS, medH))
        top, bot = yS + box_h/2 + 0.03, yH - box_h/2 - 0.03
        ax.add_patch(Rectangle((gx0, bot), gx1 - gx0, top - bot, facecolor=band_c,
                               alpha=0.09, edgecolor="none", zorder=1))
        for arr, yb, col, tick in ((sw, yS, cS, cS_tick), (hw, yH, cH, cH_tick)):
            lo, hi = arr.min(), arr.max(); q1, med, q3 = np.percentile(arr, [25, 50, 75])
            ax.plot([lo, hi], [yb, yb], color="#CBC5B6", lw=1.3, solid_capstyle="round", zorder=2)
            jy = yb + rng.uniform(-jitter, jitter, size=len(arr))
            ax.scatter(arr, jy, s=dot, color=col, alpha=dot_alpha, edgecolors="none", zorder=3)
            ax.add_patch(Rectangle((q1, yb - box_h/2), q3 - q1, box_h, facecolor=col,
                                   alpha=0.22, edgecolor=col, linewidth=1.0, zorder=4))
            ax.plot([med, med], [yb - box_h/2, yb + box_h/2], color=tick, lw=3.2,
                    solid_capstyle="round", zorder=6)
        ax.plot([medS, medH], [yS, yH], color=con_c, lw=2.0, alpha=0.82,
                solid_capstyle="round", zorder=5)
        ax.text(medS, yS + box_h/2 + 0.04, fmt(medS), ha="center", va="bottom",
                fontsize=med_fs, fontweight=800, color=lab_s, zorder=7)
        ax.text(medH, yH - box_h/2 - 0.04, fmt(medH), ha="center", va="top",
                fontsize=med_fs, fontweight=800, color=lab_h, zorder=7)
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
                    ha="center", va="center", fontsize=14, fontweight=800, color=INK)
        if delta_col:
            d = abs(medH - medS); tag = "HW" if medH >= medS else "SW"
            ax.text(1.015, y, f"{tag} +{fmt(d)}", transform=ax.get_yaxis_transform(),
                    ha="left", va="center", fontsize=12, fontweight=800, color=delta_c,
                    clip_on=False)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-0.72, n - 0.12)
    ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    if delta_col and delta_header:
        ax.text(1.015, ys[0] + 0.52, delta_header, transform=ax.get_yaxis_transform(),
                ha="left", va="bottom", fontsize=10.5, fontweight=800, color=SUB, clip_on=False)
    if legend:
        if legend_style == "shade":
            # neutral light/dark swatches show the lighter=software / darker=hardware convention;
            # keep the LABEL text dark (INK) so the light swatch's word stays readable.
            for (lx, ly), sw_c, lab in ((legend_xy[0], "#9AA1A6", disc_names[0]),
                                        (legend_xy[1], "#4E555A", disc_names[1])):
                ax.scatter([lx], [ly], s=185, color=sw_c, marker="o", transform=ax.transAxes,
                           clip_on=False, zorder=12)
                ax.text(lx + 0.028, ly, lab, transform=ax.transAxes, fontsize=13,
                        fontweight=800, color=INK, va="center", ha="left")
        else:
            legmark(ax, legend_xy[0][0], legend_xy[0][1], cS_g, disc_names[0], size=13)
            legmark(ax, legend_xy[1][0], legend_xy[1][1], cH_g, disc_names[1], size=13)
    return ys

# gap accents — a FIXED, scannable "who pays more" pair, independent of per-company colors
SW_WIN = BLUE          # software pays more  (blue)
HW_WIN = "#D9701C"     # hardware pays more  (orange)

def _paired_gap(ax, medS, medH, yS, yH, accS, accH, *, lw=2.6, scale=16):
    """Winner arrow between two medians: tail at the lower-paying role, head at the higher.
    Because the higher median is always further right, the arrow points rightward-and-toward
    the winning band (up=software / down=hardware). Returns (delta, tag, winColor)."""
    if medH >= medS:
        (x0, y0), (x1, y1), win, tag = (medS, yS), (medH, yH), accH, "HW"
    else:
        (x0, y0), (x1, y1), win, tag = (medH, yH), (medS, yS), accS, "SW"
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=5,
                arrowprops=dict(arrowstyle="-|>", color=win, lw=lw, mutation_scale=scale,
                                shrinkA=1.5, shrinkB=1.5))
    return abs(medH - medS), tag, win

def _gap_chip(ax, y, tag, d, win, fmt, x=1.035, fs=11.5):
    ax.text(x, y, f"{tag}  +{fmt(d)}", transform=ax.get_yaxis_transform(), ha="left",
            va="center", fontsize=fs, fontweight=800, color="white", clip_on=False, zorder=9,
            bbox=dict(boxstyle="round,pad=0.34", fc=win, ec="none"))

def _logo_name(ax, label, y, name, base, logo_x, logo_px, name_dy, name_size, company_tab):
    if isinstance(label, np.ndarray):
        zoom = logo_px / (label.shape[0] * DPI / 72.0)
        ax.add_artist(AnnotationBbox(OffsetImage(label, zoom=zoom), (logo_x, y),
                      xycoords=("axes fraction", "data"), frameon=False,
                      box_alignment=(0.5, 0.5), annotation_clip=False))
        if name:
            ax.text(logo_x, y - name_dy, name, transform=ax.get_yaxis_transform(),
                    ha="center", va="top", fontsize=name_size, fontweight=700,
                    color=SUB, clip_on=False)
            if company_tab and base:                       # company-color underline (identity in hue mode)
                ax.plot([logo_x - 0.028, logo_x + 0.028], [y - name_dy - 0.11] * 2,
                        transform=ax.get_yaxis_transform(), color=base, lw=3.2,
                        solid_capstyle="round", clip_on=False, zorder=6)
    elif label:
        ax.text(logo_x, y, str(label), transform=ax.get_yaxis_transform(),
                ha="center", va="center", fontsize=14, fontweight=800, color=INK)

def paired_split(ax, rows, *, xticks=None, xmin=0, xmax=None, fmt=money,
                 disc_style="shade", sw_light=0.34, hw_dark=0.26, hue_colors=(DISC_SW, DISC_HW),
                 company_tab=False, offset=0.16, box_h=0.12, jitter=0.062, dot=12, dot_alpha=0.50,
                 logo_x=-0.10, logo_px=64, name_dy=0.40, name_size=8.5, med_fs=10,
                 pq_labels=False, pq_fs=None, med_pad=0.05, pq_pad=0.035, whisker_lw=1.1,
                 gap_accents=(SW_WIN, HW_WIN), separators=True, seed=7,
                 xlabel="Total Compensation ($K)", disc_names=("Software", "Hardware"),
                 legend=True, legend_xy=(0.48, 0.975), delta_header="Who pays more"):
    """Mirrored split strip: software up / hardware down, companies separated by faint rules,
    with a visual gap encoding (winner-colored arrow + a colored right CHIP; blue = software pays
    more, orange = hardware). Three discipline styles:
      - "shade": each company in its OWN color; software the lighter shade, hardware the darker.
      - "fill" : each company its own color; software HOLLOW (outline), hardware SOLID.
      - "hue"  : software blue / hardware orange (fixed); identity via logo (+ company_tab underline).
    Two label modes:
      - default: just the median value above/below each band; a DIAGONAL median-to-median arrow.
      - pq_labels=True (the roomy 'full boxplot' look, pair it with set_format('a4')): each band gets
        the company_strip treatment — 'Med. $X' on the OUTER edge and p25 / p75 at the box corners
        toward the center; the gap arrow becomes a HORIZONTAL bar in the clear center corridor. Use a
        larger `offset` so the corridor holds the p-labels + arrow without collision.
    rows: (label, swPts, hwPts[, name[, baseColor]]) — baseColor needed for shade/fill/tab."""
    rng = np.random.default_rng(seed)
    n = len(rows); ys = list(range(n))[::-1]
    accS, accH = gap_accents
    pq_fs = (med_fs - 1.5) if pq_fs is None else pq_fs
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    xmax = xmax or max(allpts) * 1.06
    epad = (xmax - xmin) * 0.006
    for y, r in zip(ys, rows):
        label = r[0]
        sw = np.asarray(sorted(r[1]), float); hw = np.asarray(sorted(r[2]), float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        yS, yH = y + offset, y - offset
        q1S, medS, q3S = (float(v) for v in np.percentile(sw, [25, 50, 75]))
        q1H, medH, q3H = (float(v) for v in np.percentile(hw, [25, 50, 75]))
        if disc_style == "shade":
            colS, colH = lighten(base, sw_light), darken(base, hw_dark)
            tickS, tickH, hollowS = lighten(base, sw_light * 0.5), colH, False
        elif disc_style == "fill":
            colS = colH = tickS = tickH = base; hollowS = True
        else:  # hue
            colS, colH = hue_colors; tickS, tickH, hollowS = colS, colH, False
        if separators and y != ys[-1]:
            ax.axhline(y - 0.5, color="#E6E3D8", lw=1.0, zorder=0)
        for arr, yb, col, tick, hollow, q1, med, q3 in (
                (sw, yS, colS, tickS, hollowS, q1S, medS, q3S),
                (hw, yH, colH, tickH, False, q1H, medH, q3H)):
            lo, hi = arr.min(), arr.max()
            ax.plot([lo, hi], [yb, yb], color="#CBC5B6", lw=whisker_lw, solid_capstyle="round", zorder=2)
            jy = yb + rng.uniform(-jitter, jitter, size=len(arr))
            if hollow:
                ax.scatter(arr, jy, s=dot, facecolors="none", edgecolors=col, linewidths=0.8,
                           alpha=min(1.0, dot_alpha + 0.25), zorder=3)
                ax.add_patch(Rectangle((q1, yb - box_h/2), q3 - q1, box_h, facecolor="none",
                                       edgecolor=col, linewidth=1.5, zorder=4))
            else:
                ax.scatter(arr, jy, s=dot, color=col, alpha=dot_alpha, edgecolors="none", zorder=3)
                ax.add_patch(Rectangle((q1, yb - box_h/2), q3 - q1, box_h, facecolor=col,
                                       alpha=0.22, edgecolor=col, linewidth=1.0, zorder=4))
            ax.plot([med, med], [yb - box_h/2, yb + box_h/2], color=tick, lw=3.0,
                    solid_capstyle="round", zorder=6)
        d = abs(medH - medS); tag = "HW" if medH >= medS else "SW"
        win = accH if medH >= medS else accS
        if pq_labels:
            # gap arrow gets the (now clear) center corridor; p25/p75 + median stack OUTWARD
            # (software above its box, hardware below), median furthest out — company_strip style.
            lo_m, hi_m = sorted((medS, medH))
            ax.annotate("", xy=(hi_m, y), xytext=(lo_m, y), zorder=5,
                        arrowprops=dict(arrowstyle="-|>", color=win, lw=3.0, mutation_scale=18,
                                        shrinkA=0, shrinkB=0))
            for q1_, med_, q3_, yb_, sgn, va_ in ((q1S, medS, q3S, yS, 1, "bottom"),
                                                  (q1H, medH, q3H, yH, -1, "top")):
                py = yb_ + sgn * (box_h/2 + pq_pad)
                ax.text(q1_ - epad, py, fmt(q1_), ha="right", va=va_, fontsize=pq_fs,
                        fontweight=800, color="#7A7F84", zorder=7)
                ax.text(q3_ + epad, py, fmt(q3_), ha="left", va=va_, fontsize=pq_fs,
                        fontweight=800, color="#7A7F84", zorder=7)
                ax.text(med_, yb_ + sgn * (box_h/2 + pq_pad + med_pad), f"Med. {fmt(med_)}",
                        ha="center", va=va_, fontsize=med_fs, fontweight=800, color=INK, zorder=7)
        else:
            _paired_gap(ax, medS, medH, yS, yH, accS, accH)
            ax.text(medS, yS + box_h/2 + 0.03, fmt(medS), ha="center", va="bottom",
                    fontsize=med_fs, fontweight=800, color=INK, zorder=7)
            ax.text(medH, yH - box_h/2 - 0.03, fmt(medH), ha="center", va="top",
                    fontsize=med_fs, fontweight=800, color=INK, zorder=7)
        _logo_name(ax, label, y, name, base, logo_x, logo_px, name_dy, name_size, company_tab)
        _gap_chip(ax, y, tag, d, win, fmt)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-0.72, n + 0.05)
    ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    if delta_header:
        ax.text(1.035, ys[0] + 0.62, delta_header, transform=ax.get_yaxis_transform(),
                ha="left", va="bottom", fontsize=10.5, fontweight=800, color=SUB, clip_on=False)
    if legend:
        _paired_key(ax, disc_style, legend_xy, disc_names, hue_colors, sw_light, hw_dark)
    return ys

def _paired_key(ax, disc_style, xy, disc_names, hue_colors, sw_light, hw_dark):
    lx, ly = xy
    if disc_style == "shade":
        demo = "#6C7176"
        ax.scatter([lx], [ly], s=175, color=lighten(demo, sw_light + 0.08), marker="s",
                   transform=ax.transAxes, clip_on=False, zorder=12)
        ax.scatter([lx + 0.032], [ly], s=175, color=darken(demo, hw_dark), marker="s",
                   transform=ax.transAxes, clip_on=False, zorder=12)
        ax.text(lx + 0.066, ly, f"lighter = {disc_names[0]}   ·   darker = {disc_names[1]}",
                transform=ax.transAxes, fontsize=12, fontweight=800, color=INK, va="center", ha="left")
        ax.text(lx, ly - 0.030, "each company shown in its own color", transform=ax.transAxes,
                fontsize=10.5, fontweight=600, color=SUB, va="center", ha="left")
    elif disc_style == "fill":
        ax.scatter([lx], [ly], s=150, facecolors="none", edgecolors="#4E555A", linewidths=1.9,
                   marker="o", transform=ax.transAxes, clip_on=False, zorder=12)
        ax.text(lx + 0.026, ly, f"{disc_names[0]} (outline)", transform=ax.transAxes,
                fontsize=12, fontweight=800, color=INK, va="center", ha="left")
        ax.scatter([lx + 0.26], [ly], s=150, color="#4E555A", marker="o",
                   transform=ax.transAxes, clip_on=False, zorder=12)
        ax.text(lx + 0.286, ly, f"{disc_names[1]} (solid)", transform=ax.transAxes,
                fontsize=12, fontweight=800, color=INK, va="center", ha="left")
        ax.text(lx, ly - 0.030, "each company shown in its own color", transform=ax.transAxes,
                fontsize=10.5, fontweight=600, color=SUB, va="center", ha="left")
    else:  # hue
        legmark(ax, lx, ly, hue_colors[0], disc_names[0], size=12)
        legmark(ax, lx + 0.24, ly, hue_colors[1], disc_names[1], size=12)

def paired_dumbbell(ax, rows, *, xticks=None, xmin=0, xmax=None, fmt=money, iqr=True,
                    box_h=0.17, msize=155, logo_x=-0.10, logo_px=64, name_dy=0.36, name_size=8.5,
                    val_fs=9.5, gap_accents=(SW_WIN, HW_WIN), separators=True, seed=7,
                    xlabel="Total Compensation ($K)", disc_names=("Software", "Hardware"),
                    legend=True, legend_xy=(0.48, 0.975), delta_header="Who pays more"):
    """One line per company: software = CIRCLE, hardware = DIAMOND (both in the company's own
    color), joined by a winner-colored bar/arrow whose length IS the pay gap and whose head
    points to the higher-paying role. Faint IQR boxes (p25-p75) sit behind. Right chip repeats
    the signed gap. Maximal grouping (both roles on one line) and gap-forward.
    rows: (label, swPts, hwPts[, name[, baseColor]])."""
    n = len(rows); ys = list(range(n))[::-1]
    accS, accH = gap_accents
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    xmax = xmax or max(allpts) * 1.06
    for y, r in zip(ys, rows):
        label = r[0]
        sw = np.asarray(r[1], float); hw = np.asarray(r[2], float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        medS = float(np.percentile(sw, 50)); medH = float(np.percentile(hw, 50))
        if separators and y != ys[-1]:
            ax.axhline(y - 0.5, color="#E6E3D8", lw=1.0, zorder=0)
        if iqr:
            for arr in (sw, hw):
                q1, q3 = np.percentile(arr, [25, 75])
                ax.add_patch(Rectangle((q1, y - box_h/2), q3 - q1, box_h, facecolor=base,
                                       alpha=0.10, edgecolor="none", zorder=2))
        d, tag, win = _paired_gap(ax, medS, medH, y, y, accS, accH, lw=4.2, scale=20)
        ax.scatter([medS], [y], s=msize, color=base, marker="o", edgecolors="white",
                   linewidths=1.4, zorder=6)
        ax.scatter([medH], [y], s=msize, color=base, marker="D", edgecolors="white",
                   linewidths=1.4, zorder=6)
        ax.text(medS, y + 0.22, f"{fmt(medS)}", ha="center", va="bottom", fontsize=val_fs,
                fontweight=800, color=INK, zorder=7)
        ax.text(medH, y - 0.22, f"{fmt(medH)}", ha="center", va="top", fontsize=val_fs,
                fontweight=800, color=INK, zorder=7)
        _logo_name(ax, label, y, name, base, logo_x, logo_px, name_dy, name_size, False)
        _gap_chip(ax, y, tag, d, win, fmt)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-0.72, n + 0.05)
    ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    if delta_header:
        ax.text(1.035, ys[0] + 0.62, delta_header, transform=ax.get_yaxis_transform(),
                ha="left", va="bottom", fontsize=10.5, fontweight=800, color=SUB, clip_on=False)
    if legend:
        lx, ly = legend_xy
        ax.scatter([lx], [ly], s=150, color="#4E555A", marker="o", transform=ax.transAxes,
                   clip_on=False, zorder=12)
        ax.text(lx + 0.026, ly, f"{disc_names[0]} (circle)", transform=ax.transAxes,
                fontsize=12, fontweight=800, color=INK, va="center", ha="left")
        ax.scatter([lx + 0.25], [ly], s=135, color="#4E555A", marker="D", transform=ax.transAxes,
                   clip_on=False, zorder=12)
        ax.text(lx + 0.276, ly, f"{disc_names[1]} (diamond)", transform=ax.transAxes,
                fontsize=12, fontweight=800, color=INK, va="center", ha="left")
        ax.text(lx, ly - 0.030, "each company shown in its own color", transform=ax.transAxes,
                fontsize=10.5, fontweight=600, color=SUB, va="center", ha="left")
    return ys

def _boxrow(ax, arr, yb, color, *, box_h, jitter, dot, dot_alpha, rng, whisker_lw, fmt,
            med_fs, pq_fs, med_pad, pq_pad, epad, med_side=1, pq_side=-1):
    """Draw ONE clean company_strip-style horizontal boxplot at row y=yb: whisker (min-max),
    jittered dots, IQR box (p25-p75), median line, 'Med. $X' on the med_side edge and p25/p75
    on the pq_side edge (+1 = above, -1 = below). Returns the median."""
    lo, hi = arr.min(), arr.max(); q1, med, q3 = (float(v) for v in np.percentile(arr, [25, 50, 75]))
    wcol, cap = "#A79F8F", box_h * 0.6                     # whisker color + end-cap half-reach
    ax.plot([lo, hi], [yb, yb], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2)
    for xx in (lo, hi):                                    # vertical end-caps give the whisker visible height
        ax.plot([xx, xx], [yb - cap/2, yb + cap/2], color=wcol, lw=whisker_lw,
                solid_capstyle="round", zorder=2)
    ax.scatter(arr, yb + rng.uniform(-jitter, jitter, size=len(arr)), s=dot, color=color,
               alpha=dot_alpha, edgecolors="white", linewidths=0.3, zorder=3)   # white rim separates overlaps
    ax.add_patch(Rectangle((q1, yb - box_h/2), q3 - q1, box_h, facecolor=color, alpha=0.14,
                           edgecolor=color, linewidth=2.0, zorder=4))           # bold box outline = p25/p75
    ax.plot([q1, q1], [yb - box_h/2, yb + box_h/2], color=color, lw=2.0, solid_capstyle="round", zorder=5)
    ax.plot([q3, q3], [yb - box_h/2, yb + box_h/2], color=color, lw=2.0, solid_capstyle="round", zorder=5)
    ax.plot([med, med], [yb - box_h/2, yb + box_h/2], color=darken(color, 0.4), lw=5.0,
            solid_capstyle="butt", zorder=6)                                    # bold dark median
    ax.text(med, yb + med_side * (box_h/2 + med_pad), f"Med. {fmt(med)}", ha="center",
            va=("bottom" if med_side > 0 else "top"), fontsize=med_fs, fontweight=800, color=INK, zorder=7)
    yy = yb + pq_side * (box_h/2 + pq_pad); va = "bottom" if pq_side > 0 else "top"
    ax.text(q1 - epad, yy, fmt(q1), ha="right", va=va, fontsize=pq_fs, fontweight=800, color="#6f7479", zorder=7)
    ax.text(q3 + epad, yy, fmt(q3), ha="left", va=va, fontsize=pq_fs, fontweight=800, color="#6f7479", zorder=7)
    return med

def paired_lanes(ax, rows, *, xticks=None, xmin=0, xmax=None, fmt=money, intra=0.21, box_h=0.20,
                 jitter=0.09, dot=16, dot_alpha=0.5, whisker_lw=2.2, row_gap=1.18, logo_x=-0.155,
                 logo_px=68, name_dy=0.30, name_size=9.5, med_fs=11, pq_fs=9.5, med_pad=0.075,
                 pq_pad=0.02, card=True, card_h=0.46, tag_x=-0.012, tag_fs=9.5,
                 disc_names=("Software", "Hardware"), gap_accents=(SW_WIN, HW_WIN),
                 winner_chip=True, seed=7, xlabel="Total Compensation ($K)", delta_header="Who pays more"):
    """Side-by-side (stacked, NOT overlaid) boxplots — each company gets TWO clean company_strip
    rows: software on top, hardware below, grouped close together with big margins between companies.
    Each row is a full labeled boxplot (dots + IQR box + median line; 'Med. $X' on the OUTER edge,
    p25/p75 on the INNER edge so the center between the pair stays clear). One company color for both
    rows; a discipline tag per row; one logo + name per company; optional winner chip on the right.
    Pair with set_format('tall'). rows: (label, swPts, hwPts[, name[, baseColor]])."""
    rng = np.random.default_rng(seed)
    n = len(rows); ycs = [i * row_gap for i in range(n)][::-1]
    accS, accH = gap_accents
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    xmax = xmax or max(allpts) * 1.06
    epad = (xmax - xmin) * 0.006
    for yc, r in zip(ycs, rows):
        label = r[0]
        sw = np.asarray(sorted(r[1]), float); hw = np.asarray(sorted(r[2]), float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        ySW, yHW = yc + intra, yc - intra
        if card:
            ax.add_patch(Rectangle((xmin, yc - card_h), xmax - xmin, 2 * card_h, facecolor=base,
                                   alpha=0.05, edgecolor="none", zorder=0))
        bk = dict(box_h=box_h, jitter=jitter, dot=dot, dot_alpha=dot_alpha, rng=rng,
                  whisker_lw=whisker_lw, fmt=fmt, med_fs=med_fs, pq_fs=pq_fs, med_pad=med_pad,
                  pq_pad=pq_pad, epad=epad)
        # labels stack OUTWARD (software above, hardware below) so the space between the two
        # boxes stays clean and they read as two distinct side-by-side boxplots.
        medS = _boxrow(ax, sw, ySW, base, med_side=+1, pq_side=+1, **bk)
        medH = _boxrow(ax, hw, yHW, base, med_side=-1, pq_side=-1, **bk)
        ax.text(tag_x, ySW, disc_names[0], transform=ax.get_yaxis_transform(), ha="right",
                va="center", fontsize=tag_fs, fontweight=700, color=SUB, clip_on=False)
        ax.text(tag_x, yHW, disc_names[1], transform=ax.get_yaxis_transform(), ha="right",
                va="center", fontsize=tag_fs, fontweight=700, color=SUB, clip_on=False)
        _logo_name(ax, label, yc, name, base, logo_x, logo_px, name_dy, name_size, False)
        if winner_chip:
            d = abs(medH - medS); tag = "HW" if medH >= medS else "SW"
            _gap_chip(ax, yc, tag, d, (accH if medH >= medS else accS), fmt)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-card_h - 0.06, (n - 1) * row_gap + card_h + 0.06)
    ax.set_yticks([]); clean(ax, grid="x")
    if xticks is not None:
        ax.set_xticks(xticks); ax.set_xticklabels([fmt(t) for t in xticks])
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    if winner_chip and delta_header:
        ax.text(1.02, ycs[0] + card_h * 0.7, delta_header, transform=ax.get_yaxis_transform(),
                ha="left", va="bottom", fontsize=10.5, fontweight=800, color=SUB, clip_on=False)
    return ycs

def paired_vbox(ax, rows, *, yticks=None, ymin=0, ymax=None, fmt=money, per_company=True,
                sw_light=0.30, hw_dark=0.20, colors=(DISC_SW, DISC_HW), group_gap=1.0, box_w=0.30,
                off=0.20, jitter=0.115, dot=12, dot_alpha=0.55, dot_max=None, whisker_lw=2.2, logo_px=56,
                name_dy=0.115, name_size=10, med_fs=10, pq_fs=8.5, overflow=True,
                overflow_style="stub", over_frac=0.07, declutter=True, whisker=None,
                disc_names=("Software", "Hardware"), seed=7, ylabel="Total Compensation ($K)",
                legend=True, legend_xy=(0.018, 0.905), legend_dx=0.118,
                legend_caption="left is software, right is hardware for each company"):
    """TRANSPOSED grouped boxplots — companies along the X-axis, pay on the Y-axis, VERTICAL
    boxplots. Each company = two boxes side by side (software left, hardware right), each with
    whisker+caps, jittered dots, IQR box, bold median bar, and a detailed callout ('Med. $X' plus
    the p25–p75 range) above it. Logo + name under the axis. Two color modes: per_company=True uses
    each company's OWN color (software the lighter shade, hardware the darker); else fixed discipline
    hues. overflow=True draws whiskers that exceed ymax as a short stub OUTSIDE the plot top (clip
    off) with the true max labeled — shows the tail without rescaling. rows: (label, swPts, hwPts[,
    name[, baseColor]])."""
    rng = np.random.default_rng(seed)
    n = len(rows); xcs = [i * group_gap for i in range(n)]
    allpts = [v for r in rows for v in (list(r[1]) + list(r[2]))]
    ymax = ymax or max(allpts) * 1.06
    span = ymax - ymin; maxhi = max(allpts)
    halo = dict(boxstyle="round,pad=0.1", fc=CREAM, ec="none", alpha=0.72)
    for xc, r in zip(xcs, rows):
        label = r[0]
        sw = np.asarray(r[1], float); hw = np.asarray(r[2], float)
        name = r[3] if len(r) > 3 else None
        base = r[4] if len(r) > 4 else INK
        colS, colH = (lighten(base, sw_light), darken(base, hw_dark)) if per_company else colors
        swq = [float(v) for v in np.percentile(sw, [25, 50, 75])]
        hwq = [float(v) for v in np.percentile(hw, [25, 50, 75])]
        # location-aware placement: stagger the two callouts UP so the wide Med/range text never
        # overlaps when the software and hardware boxes sit at a similar height (push only as needed).
        med_dy = span * 0.037; nat_S = swq[2] + span * 0.020; nat_H = hwq[2] + span * 0.020
        if declutter:
            blk = span * 0.065; gap = span * 0.012
            if swq[2] <= hwq[2]:
                ry_S = nat_S; ry_H = max(nat_H, ry_S + blk + gap)
            else:
                ry_H = nat_H; ry_S = max(nat_S, ry_H + blk + gap)
        else:
            ry_S, ry_H = nat_S, nat_H
        for arr, xb, col, (q1, med, q3), ry in ((sw, xc - off, colS, swq, ry_S),
                                                (hw, xc + off, colH, hwq, ry_H)):
            if whisker is None:
                lo, hi = float(arr.min()), float(arr.max())
            else:                                          # percentile whiskers (skewed pay data)
                lo, hi = (float(v) for v in np.percentile(arr, [whisker[0] * 100, whisker[1] * 100]))
            wcol, cap = "#A79F8F", box_w * 0.30
            ax.plot([xb, xb], [lo, min(hi, ymax)], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2)
            ax.plot([xb - cap, xb + cap], [lo, lo], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2)
            if hi <= ymax:
                ax.plot([xb - cap, xb + cap], [hi, hi], color=wcol, lw=whisker_lw, solid_capstyle="round", zorder=2)
            inr = arr[(arr >= ymin) & (arr <= ymax)]        # dots above the cap are conveyed by the tail, not piled
            if dot_max and len(inr) > dot_max:              # subsample big clouds (box/median use ALL points)
                inr = rng.choice(inr, size=dot_max, replace=False)
            ax.scatter(xb + rng.uniform(-jitter, jitter, size=len(inr)), inr, s=dot, color=col,
                       alpha=dot_alpha, edgecolors="white", linewidths=0.3, zorder=3)
            ax.add_patch(Rectangle((xb - box_w/2, q1), box_w, q3 - q1, facecolor=col, alpha=0.15,
                                   edgecolor=col, linewidth=2.0, zorder=4))
            for yy in (q1, q3):
                ax.plot([xb - box_w/2, xb + box_w/2], [yy, yy], color=col, lw=1.6, zorder=5)
            ax.plot([xb - box_w/2, xb + box_w/2], [med, med], color=darken(col, 0.4), lw=4.0,
                    solid_capstyle="butt", zorder=6)
            ax.text(xb, ry + med_dy, f"Med. {fmt(med)}", ha="center", va="bottom", fontsize=med_fs,
                    fontweight=800, color=INK, zorder=8, bbox=halo)
            ax.text(xb, ry, f"{fmt(q1)}–{fmt(q3)}", ha="center", va="bottom",
                    fontsize=pq_fs, fontweight=700, color="#6f7479", zorder=8, bbox=halo)
            if overflow and hi > ymax:                    # draw the cut-off tail OUTSIDE the plot top
                if overflow_style == "fade" and maxhi > ymax:   # height ∝ true max, and fades upward
                    over = ymax + span * over_frac * (hi - ymax) / (maxhi - ymax)
                    nseg = 12
                    for k in range(nseg):
                        y0 = ymax + (over - ymax) * k / nseg
                        y1 = ymax + (over - ymax) * (k + 1) / nseg
                        ax.plot([xb, xb], [y0, y1], color=wcol, lw=whisker_lw, clip_on=False,
                                alpha=max(0.08, 1.0 - 0.92 * k / (nseg - 1)), solid_capstyle="butt", zorder=2)
                else:                                     # fixed stub with a cap
                    over = ymax + span * 0.045
                    ax.plot([xb, xb], [ymax, over], color=wcol, lw=whisker_lw, clip_on=False, zorder=2)
                    ax.plot([xb - cap, xb + cap], [over, over], color=wcol, lw=whisker_lw,
                            clip_on=False, solid_capstyle="round", zorder=2)
                ax.text(xb, over + span * 0.012, fmt(hi), ha="center", va="bottom", fontsize=pq_fs,
                        fontweight=800, color=wcol, clip_on=False, zorder=8)
        if isinstance(label, np.ndarray):
            zoom = logo_px / (label.shape[0] * DPI / 72.0)
            ax.add_artist(AnnotationBbox(OffsetImage(label, zoom=zoom), (xc, -0.035),
                          xycoords=("data", "axes fraction"), frameon=False,
                          box_alignment=(0.5, 1.0), annotation_clip=False))
            if name:
                ax.text(xc, -name_dy, name, transform=ax.get_xaxis_transform(), ha="center",
                        va="top", fontsize=name_size, fontweight=700, color=SUB, clip_on=False)
        elif label:
            ax.text(xc, -0.05, str(label), transform=ax.get_xaxis_transform(), ha="center",
                    va="top", fontsize=13, fontweight=800, color=INK, clip_on=False)
    ax.set_ylim(ymin, ymax); ax.set_xlim(-0.62, (n - 1) * group_gap + 0.62)
    ax.set_xticks([]); clean(ax, grid="y")
    if yticks is not None:
        ax.set_yticks(yticks)
        ax.set_yticklabels(["$0" if t == 0 else fmt(t) for t in yticks])   # clean "$0", not "$0K"
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    if legend:
        if per_company:
            # a clean shade key: each swatch sits directly beside its label, the two pairs well
            # separated, with a muted caption underneath — generous white space, nothing cramped.
            lx, ly = legend_xy; demo = "#6C7176"
            sq = dict(s=150, marker="s", transform=ax.transAxes, clip_on=False, zorder=12)
            ax.scatter([lx], [ly], color=lighten(demo, sw_light + 0.12), **sq)
            ax.text(lx + 0.017, ly, disc_names[0], transform=ax.transAxes, fontsize=12.5,
                    fontweight=800, color=INK, va="center", ha="left")
            x2 = lx + legend_dx
            ax.scatter([x2], [ly], color=darken(demo, hw_dark), **sq)
            ax.text(x2 + 0.017, ly, disc_names[1], transform=ax.transAxes, fontsize=12.5,
                    fontweight=800, color=INK, va="center", ha="left")
            if legend_caption:
                ax.text(lx, ly - 0.052, legend_caption, transform=ax.transAxes,
                        fontsize=10.5, fontweight=600, color=SUB, va="center", ha="left")
        else:
            legmark(ax, legend_xy[0], legend_xy[1], colors[0], disc_names[0], size=13)
            legmark(ax, legend_xy[0] + 0.135, legend_xy[1], colors[1], disc_names[1], size=13)
    return xcs

# equity / stock-grant story palette (base salary, bonus, equity)
STOCK = "#0060B9"      # equity is the hero segment — brand blue
def grant_growth(ax, segs_orig, segs_now, *, seg_colors=(GREEN, AMBER, STOCK),
                 seg_names=("Base", "Target bonus", "Stock grant"),
                 xlabels=("At offer", "Today"), fmt=money, ymax=None, width=0.52,
                 legend=True, legend_y=0.965, total_labels=True, stock_value_labels=True,
                 bottom_pad=0.0):
    """Two stacked vertical bars comparing annual comp composition Original vs Current, for
    the 'one grant, repriced by the stock' story. `segs_orig` / `segs_now` are
    [base, bonus, equity] in the units `fmt` formats (money() -> thousands). The equity
    (last) segment is the hero and usually towers in the 'now' bar. Returns ymax used.
    Annotate shares / price / multiple yourself with ax.text (axes fraction)."""
    xs = [0, 1]; data = [list(segs_orig), list(segs_now)]
    totals = [sum(s) for s in data]
    ymax = ymax or max(totals) * 1.20
    for x, segs in zip(xs, data):
        bottom = 0.0
        last = len(segs) - 1
        for j, (val, col) in enumerate(zip(segs, seg_colors)):
            ax.bar(x, val, width, bottom=bottom, color=col, zorder=3)
            if stock_value_labels and j == last and val > ymax * 0.05:
                ax.text(x, bottom + val / 2, fmt(val), ha="center", va="center",
                        color="white", fontsize=13.5, fontweight=800, zorder=5)
            bottom += val
        if total_labels:
            ax.text(x, bottom + ymax * 0.015, fmt(bottom), ha="center", va="bottom",
                    fontsize=17, fontweight=800, color=INK, zorder=5)
    ax.set_xlim(-0.7, 1.7); ax.set_ylim(-ymax * bottom_pad, ymax)
    ax.set_xticks(xs); ax.set_xticklabels(xlabels); ax.set_yticks([])
    clean(ax, grid=None); cat_labels(ax, "x", 17)
    if legend: legend_row(ax, list(zip(seg_colors, seg_names)), y=legend_y)
    return ymax

BARFILL = "#BCD2F0"      # visible light-blue bar fill on cream (PALE is too faint here)
def bars_line(ax, cats, values=None, *, segments=None, bar_color=BARFILL, line_color=NAVY,
              fmt=money, ymax=None, headroom=1.18, value_labels=None, cat_size=12, dot=30,
              lw=3.2, legend=False, legend_y=0.965, xlabel=None):
    """Periodic bars with a trend LINE riding the tops — for a value-over-time series that
    bounces (e.g. a stock-driven grant by quarter). The line traces the total trajectory.

    Pass EITHER `values` (single-color bars) OR `segments` = [(name, per-period values, color)]
    for STACKED bars (e.g. base / bonus / stock), in which case the line rides the column TOTALS
    and `legend=True` draws an in-plot legend. `headroom` sets the y-top as total_max * headroom
    (raise it so a tall mid-series spike + its label clear the legend/subtitle). `value_labels`:
    list of (index, text) annotated above the totals. Animated twin: animate_bars_line."""
    x = np.arange(len(cats)); n = len(cats)
    if segments is not None:
        tops = [sum(float(seg[1][i]) for seg in segments) for i in range(n)]
        bottoms = [0.0] * n
        for name, svals, col in segments:
            ax.bar(x, [float(v) for v in svals], 0.66, bottom=bottoms, color=col, zorder=3)
            bottoms = [b + float(v) for b, v in zip(bottoms, svals)]
    else:
        tops = [float(v) for v in values]
        ax.bar(x, tops, 0.66, color=bar_color, zorder=3)
    vmax = max(tops)
    ax.plot(x, tops, color=line_color, lw=lw, solid_capstyle="round", zorder=5)
    ax.scatter(x, tops, s=dot, color=line_color, zorder=6)
    ax.set_xlim(-0.7, n - 0.3); ax.set_ylim(0, ymax or vmax * headroom)
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_yticks([]); clean(ax, grid="y")
    cat_labels(ax, "x", cat_size)
    for i, t in (value_labels or []):
        ax.text(x[i], tops[i] + vmax * 0.025, t, ha="center", va="bottom",
                fontsize=13, fontweight=800, color=line_color, zorder=8)
    if legend and segments:
        legend_row(ax, [(c, nm) for nm, _, c in segments], y=legend_y)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=13.5, fontweight=700, color=SUB, labelpad=8)
    return x
