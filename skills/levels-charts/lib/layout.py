#!/usr/bin/env python3
"""Non-overlapping marks with labels, in plot pixels. Content-agnostic.

Promoted into the skill after being copied verbatim across four editorial packs
(pay-per-yoe, senior-offers, ai-labs, cursor-exit-map). Import as `import layout`
with this lib dir on sys.path, next to levels_charts. Callers hand in the true positions ALREADY CONVERTED TO PLOT PIXELS, plus the
artwork sizes and label widths, and get back final pixel positions and a side per label.

The three passes, in order:
  1. relax   — marks push each other apart with a weak spring back to the truth. The exclusion
               ellipse is per-mark and WIDE AND SHORT, because what collides is the label, not the
               artwork: "Palo Alto Networks" needs three times the room of "Snap".
  2. sides   — every label scores all four of its sides against real pixel boxes (each logo, each
               label already placed, any fixed furniture, the frame) and takes the cheapest. Widest
               labels go first because they are the most constrained.
  3. grow    — a mark boxed in on all four sides still loses, so if anything still touches the whole
               set re-relaxes at a larger radius until it does not.
"""
import numpy as np

AIR = 14.0                    # minimum clearance a label keeps from anything else, in px


def _infl(b, p=AIR):
    return (b[0] - p, b[1] - p, b[2] + p, b[3] + p)


def _overlap(a, b):
    return (max(0.0, min(a[2], b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[3], b[3]) - max(a[1], b[1])))


def _escape(cx, cy, hw, hh, b):
    """Shortest push that clears a mark centred at (cx, cy) from fixed box b, or None."""
    ox = min(cx + hw, b[2]) - max(cx - hw, b[0])
    oy = min(cy + hh, b[3]) - max(cy - hh, b[1])
    if ox <= 0 or oy <= 0:
        return None
    if ox < oy:
        return (ox if cx > (b[0] + b[2]) / 2 else -ox, 0.0)
    return (0.0, oy if cy > (b[1] + b[3]) / 2 else -oy)


def _seg_clear(a, b, boxes, pad=10.0, steps=24):
    """True when the segment a->b stays out of every box.

    A LEADER LINE THAT RUNS PAST SOMEBODY ELSE'S LOGO READS AS THEIR LINE. Cognition was moved to
    the nearest free spot, which put its tether straight through Cohere, and the chart then said
    Cohere was the displaced one. The ring search has to care what the line crosses, not only where
    the mark lands.
    """
    for t in np.linspace(0.12, 0.92, steps):
        p = a + (b - a) * t
        for bx in boxes:
            if bx[0] - pad <= p[0] <= bx[2] + pad and bx[1] - pad <= p[1] <= bx[3] + pad:
                return False
    return True


def _relax(pts, rx, ry, iters=900, pull=0.014, clamp=None, sizes=None, fixed=()):
    """clamp is (lo_x, lo_y, hi_x, hi_y) per mark; without it a dense cluster shoves its outliers
    clean off the canvas, which is exactly what 44 companies in one corner did.

    FIXED FURNITURE REPELS THE ARTWORK TOO, not just the labels. Scoring only the labels against it
    let a logo land squarely on a contour label — the label had dodged the mark, and the mark had
    never been told the label existed."""
    p = pts.copy()
    n = len(p)
    for _ in range(iters):
        for i in range(n):
            for j in range(i + 1, n):
                RX, RY = 0.5 * (rx[i] + rx[j]), 0.5 * (ry[i] + ry[j])
                dx, dy = (p[j, 0] - p[i, 0]) / RX, (p[j, 1] - p[i, 1]) / RY
                d = float(np.hypot(dx, dy))
                if d > 1.0:
                    continue
                if d < 1e-9:
                    p[i, 0] -= RX * 0.05; p[j, 0] += RX * 0.05
                    continue
                push = (1.0 - d) * 0.5
                ux, uy = dx / d, dy / d
                p[i, 0] -= ux * push * RX; p[i, 1] -= uy * push * RY
                p[j, 0] += ux * push * RX; p[j, 1] += uy * push * RY
        if sizes is not None and len(fixed):
            for i in range(n):
                for b in fixed:
                    esc = _escape(p[i, 0], p[i, 1], sizes[i][0] / 2 + 6, sizes[i][1] / 2 + 6, b)
                    if esc:
                        p[i, 0] += esc[0] * 0.35; p[i, 1] += esc[1] * 0.35
        p += (pts - p) * pull
        if clamp is not None:
            p[:, 0] = np.clip(p[:, 0], clamp[:, 0], clamp[:, 2])
            p[:, 1] = np.clip(p[:, 1], clamp[:, 1], clamp[:, 3])
    return p


def place(true_px, sizes, name_w, text_h, plot_w, plot_h, gap=13, fixed=(),
          grows=(1.00, 1.08, 1.17, 1.27, 1.38, 1.50, 1.64)):
    """-> (positions in px, side per label, list of remaining collision strings, spread used)."""
    n = len(true_px)
    rx = np.array([sizes[i][0] + gap + name_w[i] for i in range(n)], dtype=float)
    ry = np.array([sizes[i][1] + gap + text_h for i in range(n)], dtype=float)
    fixed = list(fixed)

    def mark_box(pos, i):
        return (pos[i, 0] - sizes[i][0] / 2, pos[i, 1] - sizes[i][1] / 2,
                pos[i, 0] + sizes[i][0] / 2, pos[i, 1] + sizes[i][1] / 2)

    def label_box(pos, i, s):
        w, aw, ah = name_w[i], sizes[i][0], sizes[i][1]
        if s == "r":
            x0, y0 = pos[i, 0] + aw / 2 + gap, pos[i, 1] - text_h / 2
        elif s == "l":
            x0, y0 = pos[i, 0] - aw / 2 - gap - w, pos[i, 1] - text_h / 2
        elif s == "t":
            x0, y0 = pos[i, 0] - w / 2, pos[i, 1] + ah / 2 + gap * 0.55
        else:
            x0, y0 = pos[i, 0] - w / 2, pos[i, 1] - ah / 2 - gap * 0.55 - text_h
        return x0, y0, x0 + w, y0 + text_h

    clamp = np.array([[sizes[i][0] / 2 + 4, sizes[i][1] / 2 + 4,
                       plot_w - sizes[i][0] / 2 - 4, plot_h - sizes[i][1] / 2 - 4]
                      for i in range(n)])
    for grow in grows:
        pos = _relax(true_px, rx * grow, ry * grow, clamp=clamp, sizes=sizes,
                     fixed=fixed)
        marks = [mark_box(pos, i) for i in range(n)]
        sides, placed = [None] * n, []
        for i in sorted(range(n), key=lambda i: -name_w[i]):
            scores = {}
            for s in ("r", "l", "t", "b"):
                b = _infl(label_box(pos, i, s))
                cost = sum(_overlap(b, marks[j]) for j in range(n) if j != i)
                cost += sum(_overlap(b, p) for p in placed + fixed)
                cost += 3 * ((max(0.0, -b[0]) + max(0.0, b[2] - plot_w)) * text_h +
                             (max(0.0, -b[1]) + max(0.0, b[3] - plot_h)) * name_w[i])
                scores[s] = cost + {"r": 0, "l": 1, "t": 2, "b": 2}[s]
            sides[i] = min(scores, key=scores.get)
            placed.append(label_box(pos, i, sides[i]))

        items = ([(i, "mark", marks[i]) for i in range(n)] +
                 [(i, sides[i], _infl(label_box(pos, i, sides[i]), AIR / 2)) for i in range(n)] +
                 [(-1 - k, "fixed", b) for k, b in enumerate(fixed)])
        bad = []
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                if items[a][0] == items[b][0]:
                    continue
                p, q = items[a][2], items[b][2]
                ox = min(p[2], q[2]) - max(p[0], q[0])
                oy = min(p[3], q[3]) - max(p[1], q[1])
                if ox > 2 and oy > 2:
                    bad.append((items[a][0], items[a][1], items[b][0], items[b][1], ox, oy))
        if not bad:
            return pos, sides, [], grow
    return pos, sides, bad, grows[-1]


def label_anchor(pos, i, side, sizes, name_w, text_h, gap=13):
    """Centre of the label box, so the caller can draw it with ha/va both 'center'."""
    w, aw, ah = name_w[i], sizes[i][0], sizes[i][1]
    if side == "r":
        return pos[i, 0] + aw / 2 + gap + w / 2, pos[i, 1]
    if side == "l":
        return pos[i, 0] - aw / 2 - gap - w / 2, pos[i, 1]
    if side == "t":
        return pos[i, 0], pos[i, 1] + ah / 2 + gap * 0.55 + text_h / 2
    return pos[i, 0], pos[i, 1] - ah / 2 - gap * 0.55 - text_h / 2


def place_exact(true_px, sizes, name_w, text_h, plot_w, plot_h, gap=13, fixed=(), max_moves=3,
                priority=None, vis_tol=0.0):
    """Pin every mark to its TRUE position; move only the ones that physically cannot stay.

    The relax in place() nudges everything a little, which is fine for a dense scatter but wrong
    when the reader is meant to trust the position: twenty leader lines say "none of these are
    where they look". Here the marks are laid down in priority order at their exact coordinates,
    and only a mark whose artwork would overlap one already down gets moved — by the shortest
    offset that clears it, found on an expanding ring so the displacement stays minimal.

    Returns (pos, sides, moved_indices, collisions).
    """
    n = len(true_px)
    fixed = list(fixed)
    order = sorted(range(n), key=lambda i: -(priority[i] if priority else 0))
    pos = true_px.astype(float).copy()

    def mbox(p, i, pad=0.0):
        return (p[0] - sizes[i][0] / 2 - pad, p[1] - sizes[i][1] / 2 - pad,
                p[0] + sizes[i][0] / 2 + pad, p[1] + sizes[i][1] / 2 + pad)

    # SEPARATE NEAR-TWINS SYMMETRICALLY FIRST. Two labs whose medians are a few thousand dollars
    # apart cannot both sit still, but moving one of them the whole way puts it a long way from
    # home and needs a leader line that then points straight at its twin. Pushing BOTH apart by
    # half each halves the error, keeps the pair reading as a pair, and usually leaves both inside
    # the no-leader threshold.
    for _ in range(140):
        moved_any = False
        for a in range(n):
            for b in range(a + 1, n):
                d = pos[b] - pos[a]
                need = np.array([(sizes[a][0] + sizes[b][0]) / 2 + 8,
                                 (sizes[a][1] + sizes[b][1]) / 2 + 8])
                ov = need - np.abs(d)
                if ov[0] <= 0 or ov[1] <= 0:
                    continue
                axis = 0 if ov[0] < ov[1] else 1          # escape by the shorter side
                step = ov[axis] / 2 + 0.5
                sign = 1.0 if d[axis] >= 0 else -1.0
                pos[a][axis] -= sign * step
                pos[b][axis] += sign * step
                moved_any = True
        for i in range(n):
            pos[i][0] = min(max(pos[i][0], sizes[i][0] / 2 + 2), plot_w - sizes[i][0] / 2 - 2)
            pos[i][1] = min(max(pos[i][1], sizes[i][1] / 2 + 2), plot_h - sizes[i][1] / 2 - 2)
        if not moved_any:
            break

    down, moved = [], []
    for i in order:
        b = mbox(pos[i], i, 5)
        clash = any(_overlap(b, f) > 0 for f in fixed)
        if not clash:
            down.append(i)
            continue
        # expanding ring search for the nearest spot that clears everything already placed
        best = None
        for r in range(12, 500, 8):
            for a in range(0, 360, 12):
                cand = pos[i] + np.array([r * np.cos(np.radians(a)), r * np.sin(np.radians(a))])
                if not (sizes[i][0] / 2 + 2 < cand[0] < plot_w - sizes[i][0] / 2 - 2
                        and sizes[i][1] / 2 + 2 < cand[1] < plot_h - sizes[i][1] / 2 - 2):
                    continue
                cb = mbox(cand, i, 5)
                if (any(_overlap(cb, mbox(pos[j], j, 5)) > 0 for j in down)
                        or any(_overlap(cb, f) > 0 for f in fixed)):
                    continue
                if not _seg_clear(true_px[i], cand,
                                  [mbox(pos[j], j) for j in down] + list(fixed)):
                    continue
                best = cand
                break
            if best is not None:
                break
        if best is not None:
            pos[i] = best
        moved.append(i)
        down.append(i)

    def label_box(i, s):
        w, aw, ah = name_w[i], sizes[i][0], sizes[i][1]
        if s == "r":
            x0, y0 = pos[i, 0] + aw / 2 + gap, pos[i, 1] - text_h / 2
        elif s == "l":
            x0, y0 = pos[i, 0] - aw / 2 - gap - w, pos[i, 1] - text_h / 2
        elif s == "t":
            x0, y0 = pos[i, 0] - w / 2, pos[i, 1] + ah / 2 + gap * 0.55
        else:
            x0, y0 = pos[i, 0] - w / 2, pos[i, 1] - ah / 2 - gap * 0.55 - text_h
        return x0, y0, x0 + w, y0 + text_h

    def solve_sides():
        marks = [mbox(pos[i], i) for i in range(n)]
        sides, placed = [None] * n, []
        for i in sorted(range(n), key=lambda i: -name_w[i]):
            scores = {}
            for s in ("r", "l", "t", "b"):
                b = _infl(label_box(i, s))
                cost = sum(_overlap(b, marks[j]) for j in range(n) if j != i)
                cost += sum(_overlap(b, p) for p in placed + fixed)
                cost += 3 * ((max(0.0, -b[0]) + max(0.0, b[2] - plot_w)) * text_h +
                             (max(0.0, -b[1]) + max(0.0, b[3] - plot_h)) * name_w[i])
                scores[s] = cost + {"r": 0, "l": 1, "t": 2, "b": 2}[s]
            sides[i] = min(scores, key=scores.get)
            placed.append(label_box(i, sides[i]))
        items = ([(i, "mark", marks[i]) for i in range(n)] +
                 [(i, sides[i], _infl(label_box(i, sides[i]), AIR / 2)) for i in range(n)] +
                 [(-1 - k, "fixed", b) for k, b in enumerate(fixed)])
        bad = []
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                if items[a][0] == items[b][0]:
                    continue
                p, qq = items[a][2], items[b][2]
                ox = min(p[2], qq[2]) - max(p[0], qq[0])
                oy = min(p[3], qq[3]) - max(p[1], qq[1])
                if ox > 2 and oy > 2:
                    bad.append((items[a][0], items[a][1], items[b][0], items[b][1], ox, oy))
        return sides, bad

    sides, bad = solve_sides()

    # REPAIR PASS. Pinning every mark resolves artwork overlaps but says nothing about LABELS, and
    # a label has only four sides to choose from. Where one is still stuck, the lowest-priority
    # company involved is walked out on the same expanding ring until the whole page is clean —
    # capped, because each repair costs a leader line.
    # only a move big enough to need a leader line counts against the budget; the sub-threshold
    # nudges that separate near-coincident twins are free
    def visible():
        return [i for i in moved if float(np.hypot(*(pos[i] - true_px[i]))) > vis_tol]

    budget = max_moves - len(visible())
    while bad and budget > 0:
        involved = [i for tup in bad for i in (tup[0], tup[2]) if i >= 0 and i not in moved]
        if not involved:
            break
        i = min(involved, key=lambda i: (priority[i] if priority else 0))
        home, best = pos[i].copy(), None
        for r in range(20, 420, 10):
            for a in range(0, 360, 10):
                cand = home + np.array([r * np.cos(np.radians(a)), r * np.sin(np.radians(a))])
                if not (sizes[i][0] / 2 + 2 < cand[0] < plot_w - sizes[i][0] / 2 - 2
                        and sizes[i][1] / 2 + 2 < cand[1] < plot_h - sizes[i][1] / 2 - 2):
                    continue
                if not _seg_clear(home, cand,
                                  [mbox(pos[j], j) for j in range(n) if j != i] + list(fixed)):
                    continue
                pos[i] = cand
                _, nb = solve_sides()
                if len(nb) < len(bad):
                    best, bad_new = cand, nb
                    if not nb:
                        break
            if best is not None and not bad_new:
                break
        if best is None:
            pos[i] = home
            break
        pos[i] = best
        if i not in moved:
            moved.append(i)
        budget = max_moves - len(visible())
        sides, bad = solve_sides()

    return pos, sides, moved, bad
