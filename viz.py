# -*- coding: utf-8 -*-
"""Decoda infographic layer: brand-consistent B&W SVG generators, used by both
build_v2 (Self) and build_two (Two). Everything is thin-line, monochrome, no
colour, matching the landing + PDF design language. Each function returns an SVG
string to drop straight into the HTML the renderer feeds weasyprint.

`color` is the ink to draw with: pass the page's foreground (#0B0B0B on light
pages, #F2EFE6 on dark pages)."""

import math

INK = "#0B0B0B"
PAPER = "#F2EFE6"

_EL_ORDER = ["Wood", "Fire", "Earth", "Metal", "Water"]


def _short(name):
    """First token of a name, so column headers never overflow."""
    return str(name or "").strip().split(" ")[0][:12] or "A"


def element_bars(elements, color=INK, w=150, title=None, maxv=None):
    """Horizontal bar chart of the five BaZi elements. `elements` = dict el->count."""
    maxv = maxv or max(max(elements.values()), 1)
    rows, y, rh, bw = [], 0, 9.2, w - 46
    for el in _EL_ORDER:
        v = elements.get(el, 0)
        ln = (v / maxv) * bw
        rows.append(
            f'<text x="0" y="{y+5.6:.1f}" font-family="Montserrat" font-size="5.4" '
            f'fill="{color}" opacity="0.75" letter-spacing="0.6">{el.upper()}</text>'
            f'<line x1="34" y1="{y+3.3:.1f}" x2="{34+bw:.1f}" y2="{y+3.3:.1f}" '
            f'stroke="{color}" stroke-width="0.4" opacity="0.18"/>'
            f'<line x1="34" y1="{y+3.3:.1f}" x2="{34+ln:.1f}" y2="{y+3.3:.1f}" '
            f'stroke="{color}" stroke-width="2.4"/>'
            f'<text x="{w:.1f}" y="{y+5.6:.1f}" font-family="Montserrat" font-size="5.4" '
            f'fill="{color}" opacity="0.65" text-anchor="end">{v}</text>')
        y += rh
    head = (f'<text x="0" y="-4" font-family="Montserrat" font-size="5" fill="{color}" '
            f'opacity="0.5" letter-spacing="1.4">{title.upper()}</text>') if title else ""
    return (f'<svg viewBox="-2 {-12 if title else -2} {w+6} {y+11}" '
            f'width="100%" xmlns="http://www.w3.org/2000/svg">{head}{"".join(rows)}</svg>')


_PLANET_GLYPH = {"Sun": "Sun", "Moon": "Moon", "Mercury": "Mercury",
                 "Venus": "Venus", "Mars": "Mars", "Rising": "Rising"}
_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Rising"]


def synastry_map(aspects, name_a="A", name_b="B", color=INK, top=6):
    """Two columns of planets (A left, B right); lines drawn for each cross-aspect.
    Line style encodes quality: flow=solid thin, blend=solid thick, tension=dashed."""
    W, H = 160, 118
    lx, rx, top_y, gap = 30, 130, 20, 15.5
    ya = {p: top_y + i * gap for i, p in enumerate(_ORDER)}
    dots, lines = [], []
    for i, p in enumerate(_ORDER):
        y = top_y + i * gap
        dots.append(
            f'<circle cx="{lx}" cy="{y}" r="1.7" fill="{color}"/>'
            f'<text x="{lx-4}" y="{y+2}" font-family="Montserrat" font-size="5.2" '
            f'fill="{color}" text-anchor="end">{p}</text>'
            f'<circle cx="{rx}" cy="{y}" r="1.7" fill="{color}"/>'
            f'<text x="{rx+4}" y="{y+2}" font-family="Montserrat" font-size="5.2" '
            f'fill="{color}">{p}</text>')
    for a in aspects[:top]:
        y1, y2 = ya[a["a"]], ya[a["b"]]
        q = a["quality"]
        if q == "tension":
            style = f'stroke="{color}" stroke-width="0.7" stroke-dasharray="2 1.8" opacity="0.7"'
        elif q == "blend":
            style = f'stroke="{color}" stroke-width="1.7" opacity="0.85"'
        else:  # flow
            style = f'stroke="{color}" stroke-width="0.7" opacity="0.75"'
        lines.append(f'<line x1="{lx+3}" y1="{y1}" x2="{rx-3}" y2="{y2}" {style}/>')
    # heads: start/end anchored (weasyprint miscentres text-anchor=middle for multi-char labels)
    heads = (f'<text x="6" y="9" font-family="DeFonte,Montserrat" font-size="5.2" fill="{color}" '
             f'opacity="0.65" text-anchor="start">{_short(name_a).upper()}</text>'
             f'<text x="{W-6}" y="9" font-family="DeFonte,Montserrat" font-size="5.2" fill="{color}" '
             f'opacity="0.65" text-anchor="end">{_short(name_b).upper()}</text>')
    legend = (f'<g transform="translate(0,{H-4})" font-family="Montserrat" font-size="4.3" fill="{color}" opacity="0.6">'
              f'<line x1="0" y1="-1" x2="7" y2="-1" stroke="{color}" stroke-width="0.7"/><text x="9" y="0.6">flow</text>'
              f'<line x1="30" y1="-1" x2="37" y2="-1" stroke="{color}" stroke-width="1.7"/><text x="39" y="0.6">blend</text>'
              f'<line x1="62" y1="-1" x2="69" y2="-1" stroke="{color}" stroke-width="0.7" stroke-dasharray="2 1.8"/><text x="71" y="0.6">tension</text></g>')
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">'
            f'{heads}{"".join(lines)}{"".join(dots)}{legend}</svg>')


def element_flow(relation, ea, eb, color=INK, name_a="A", name_b="B"):
    """Two element nodes with a relation between them. Rendered as HTML (weasyprint
    miscentres SVG text-anchor=middle), so all labels stay reliable.
    relation in same/a_feeds_b/b_feeds_a/a_checks_b/b_checks_a/neutral."""
    arrows = {"a_feeds_b": ("feeds", "&#8594;"), "b_feeds_a": ("feeds", "&#8592;"),
              "a_checks_b": ("steadies", "&#8594;"), "b_checks_a": ("steadies", "&#8592;"),
              "same": ("mirror", "="), "neutral": ("at an angle", "&#183;")}
    mid, arr = arrows.get(relation, ("at an angle", "&#183;"))

    def node(el, who):
        return (f'<div style="text-align:center">'
                f'<div style="width:24mm;height:24mm;border:0.4mm solid {color};border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;font-family:\'DeFonte\',sans-serif;'
                f'font-size:14pt;color:{color}">{el}</div>'
                f'<div style="font-family:\'Montserrat\';font-size:7pt;letter-spacing:.1em;opacity:.6;'
                f'margin-top:2mm;color:{color}">{_short(who).upper()}</div></div>')
    return (f'<div style="display:flex;align-items:center;justify-content:center;gap:6mm">'
            f'{node(ea,name_a)}'
            f'<div style="text-align:center;color:{color};min-width:26mm">'
            f'<div style="font-family:\'Montserrat\';font-size:7pt;letter-spacing:.2em;'
            f'text-transform:uppercase;opacity:.7">{mid}</div>'
            f'<div style="font-size:16pt;line-height:1;margin-top:1mm">{arr}</div></div>'
            f'{node(eb,name_b)}</div>')


def hd_connection_stats(hd, color=INK):
    """Four-count stat row for the HD relationship circuitry. HTML for reliable text."""
    items = [("Electromagnetic", len(hd.get("electromagnetic", [])), "pull"),
             ("Dominance", len(hd.get("dominance", [])), "who leads"),
             ("Companionship", len(hd.get("companionship", [])), "shared"),
             ("Compromise", len(hd.get("compromise", [])), "both stuck")]
    cells = []
    for i, (lab, n, sub) in enumerate(items):
        bl = f"border-left:0.3mm solid {color}30;" if i else ""
        cells.append(
            f'<div style="flex:1;text-align:center;padding:0 2mm;{bl}color:{color}">'
            f'<div style="font-family:\'DeFonte\',sans-serif;font-size:30pt;line-height:1">{n}</div>'
            f'<div style="font-family:\'Montserrat\';font-size:6.4pt;letter-spacing:.11em;'
            f'text-transform:uppercase;opacity:.82;margin-top:2mm">{lab}</div>'
            f'<div style="font-family:\'Montserrat\';font-size:6pt;opacity:.5;margin-top:.5mm">{sub}</div></div>')
    return f'<div style="display:flex;align-items:flex-start">{"".join(cells)}</div>'


def convergence_diagram(color=INK, agree=True):
    """Three overlapping circles (the three systems). Shaded centre when agree=True."""
    # The three centres sit on an equilateral triangle, so the triple-overlap
    # region is symmetric. The shaded core is that region itself, derived from
    # the circles rather than approximated by a dot placed in the middle: what
    # the page claims ("where all three agree") is then literally what is drawn.
    # An uneven triangle shrinks the region until nothing fits inside it, which
    # is what an earlier version of this did.
    W, r = 120, 22
    side = 27.0
    R = side / math.sqrt(3)              # circumradius, 15.59
    cx = W / 2
    cy = R + r                           # top circle just touches y = 0

    pts = [
        (cx, cy - R),                                        # Astro, apex
        (cx - R * math.cos(math.radians(30)), cy + R / 2),   # BaZi, lower left
        (cx + R * math.cos(math.radians(30)), cy + R / 2),   # HD, lower right
    ]
    labels = ["Astro", "BaZi", "HD"]
    circs = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="none" stroke="{color}" stroke-width="0.8" opacity="0.8"/>' for x, y in pts)
    # start-anchored with manual centering (weasyprint miscentres text-anchor=middle)
    labs = "".join(
        f'<text x="{x - len(labels[i])*1.55:.1f}" y="{y-(r+5) if i==0 else y+(r+9):.1f}" '
        f'font-family="DeFonte,Montserrat" font-size="5" fill="{color}" opacity="0.7">{labels[i].upper()}</text>'
        for i, (x, y) in enumerate(pts))

    def _corner(c1, c2, toward):
        """The intersection of circles c1 and c2 that lies inside the third one."""
        (x1, y1), (x2, y2) = c1, c2
        d = math.dist(c1, c2)
        h = math.sqrt(r * r - (d / 2) ** 2)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        cands = [(mx - uy * h, my + ux * h), (mx + uy * h, my - ux * h)]
        return min(cands, key=lambda p: math.dist(p, toward))

    core = ""
    if agree:
        # Each edge of the region is an arc of the circle that owns both of its
        # endpoints, so the path is three arcs of radius r, swept the short way.
        v_top = _corner(pts[1], pts[2], pts[0])   # on BaZi and HD
        v_right = _corner(pts[0], pts[1], pts[2])  # on Astro and BaZi
        v_left = _corner(pts[0], pts[2], pts[1])   # on Astro and HD
        d = (f'M {v_top[0]:.2f} {v_top[1]:.2f} '
             f'A {r} {r} 0 0 1 {v_right[0]:.2f} {v_right[1]:.2f} '
             f'A {r} {r} 0 0 1 {v_left[0]:.2f} {v_left[1]:.2f} '
             f'A {r} {r} 0 0 1 {v_top[0]:.2f} {v_top[1]:.2f} Z')
        core = f'<path d="{d}" fill="{color}" opacity="0.85"/>'
    # viewBox padded top and bottom so the three labels (above top circle, below the
    # lower circles) are never clipped.
    return (f'<svg viewBox="0 -11 {W} 92" width="100%" xmlns="http://www.w3.org/2000/svg">{circs}{core}{labs}</svg>')


# ===================================================================
# Life arc
# ===================================================================
# One SVG that has to survive two very different renderers: a browser and
# WeasyPrint. WeasyPrint miscentres text-anchor="middle" on multi character
# strings, which silently eats letters, so every label here is start anchored
# and centred by hand through _tx(). Do not "simplify" that back to middle.

ACCENT = "#D6B982"
MUTED = "#B7B2A8"
BORDER = "#393833"

_CHAR_W = 0.56          # mean glyph width as a fraction of font size


def _tx(x, s, size, anchor="middle"):
    """x for a start-anchored <text> that looks anchored the way you asked."""
    w = len(s) * _CHAR_W * size
    if anchor == "middle":
        return x - w / 2
    if anchor == "end":
        return x - w
    return x


def _txt(x, y, s, size, fill, anchor="middle", weight=400, opacity=1,
         family="Montserrat,DeFonte", extra=""):
    from html import escape
    return (f'<text x="{_tx(x, s, size, anchor):.1f}" y="{y:.1f}" '
            f'font-family="{family}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" opacity="{opacity}" {extra}>{escape(s)}</text>')


def _band_row(x0, x1, y, h, stages, span, color, accent, age, label):
    """One horizontal framework band, with the segment holding `age` lit up."""
    out = [_txt(x0, y - 7, label.upper(), 9, MUTED, anchor="start",
                extra='letter-spacing="1.6"')]
    for lo, hi, name in stages:
        if lo >= span:
            break
        hi = min(hi, span)
        bx = x0 + (x1 - x0) * lo / span
        bw = (x1 - x0) * (hi - lo) / span
        live = lo <= age < hi
        out.append(f'<rect x="{bx:.1f}" y="{y}" width="{max(bw - 2, 1):.1f}" '
                   f'height="{h}" fill="{accent if live else color}" '
                   f'opacity="{0.22 if live else 0.07}"/>')
        # only label a segment wide enough to hold text, else it turns to mush
        if bw > 34:
            short = name
            for cand in (name, name.split(",")[0].split(":")[0], name.split(" ")[0]):
                short = cand
                if len(cand) * _CHAR_W * 9 < bw - 10:
                    break
            if len(short) * _CHAR_W * 9 < bw - 8:
                out.append(_txt(bx + 6, y + h / 2 + 3.2, short, 9,
                                accent if live else MUTED, anchor="start",
                                weight=500 if live else 400))
    return "".join(out)


def life_arc(tl, width=1000, color="#F2EFE6", accent=ACCENT, bg="#0B0B0B",
             share=False):
    """The whole computed life timeline as a single SVG.

    tl is the dict from timeline.build(). Nothing is invented here: every band,
    marker and date comes straight from that dict.

    share=True is the version that leaves the device and gets posted in public.
    It carries no birth date and no calendar years on the axis, only ages, so
    a story post cannot be turned back into someone's birth data. The privacy
    page promises that and this flag is where the promise is kept.
    """
    span = tl["span_years"]
    age = tl["age"]
    birth_year = int(tl["birth"][:4])
    x0, x1 = 66, width - 22

    def X(a):
        return x0 + (x1 - x0) * a / span

    now_x = X(age)
    s = [f'<svg viewBox="0 0 {width} 700" width="100%" '
         f'xmlns="http://www.w3.org/2000/svg" font-family="Montserrat,DeFonte">']

    # ---- solar arc -------------------------------------------------
    base_y, peak = 214, 52
    pts = []
    for i in range(0, 121):
        a = span * i / 120
        y = base_y - (base_y - peak) * math.sin(math.pi * (a / span))
        pts.append((X(a), y))
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    s.append(f'<path d="M {pts[0][0]:.1f},{base_y} L {line} L {pts[-1][0]:.1f},{base_y} Z" '
             f'fill="{accent}" opacity="0.07"/>')
    s.append(f'<polyline points="{line}" fill="none" stroke="{accent}" '
             f'stroke-width="1.6" opacity="0.85"/>')

    # noon band, Jung's midpoint of life
    nx0, nx1 = X(tl["arc"]["noon_from"]), X(tl["arc"]["noon_to"])
    s.append(f'<rect x="{nx0:.1f}" y="{peak - 14}" width="{nx1 - nx0:.1f}" '
             f'height="{base_y - peak + 14}" fill="{accent}" opacity="0.06"/>')
    s.append(_txt((nx0 + nx1) / 2, peak - 20,
                  f'NOON · {tl["arc"]["noon_from"]}-{tl["arc"]["noon_to"]}', 9,
                  accent, extra='letter-spacing="1.4"'))
    s.append(_txt(X(span * 0.22), 150, "morning, turned outward", 12, MUTED,
                  extra='font-style="italic"'))
    s.append(_txt(X(span * 0.80), 150, "afternoon, turned inward", 12, MUTED,
                  extra='font-style="italic"'))

    # ---- you are here ----------------------------------------------
    now_y = base_y - (base_y - peak) * math.sin(math.pi * (age / span))
    s.append(f'<line x1="{now_x:.1f}" y1="{now_y:.1f}" x2="{now_x:.1f}" y2="644" '
             f'stroke="{accent}" stroke-width="1.2" stroke-dasharray="3 4" opacity="0.75"/>')
    s.append(f'<circle cx="{now_x:.1f}" cy="{now_y:.1f}" r="6" fill="{accent}"/>')
    here = f'you · {age}' if share else f'you · {age} · {tl["today"][:7]}'
    s.append(_txt(now_x, now_y - 14, here, 11, accent, weight=500))

    # ---- axis -------------------------------------------------------
    s.append(f'<line x1="{x0}" y1="232" x2="{x1}" y2="232" stroke="{color}" '
             f'stroke-width="0.6" opacity="0.25"/>')
    for a in range(0, span + 1, 5):
        tx = X(a)
        s.append(f'<line x1="{tx:.1f}" y1="232" x2="{tx:.1f}" y2="237" '
                 f'stroke="{color}" stroke-width="0.6" opacity="0.3"/>')
        s.append(_txt(tx, 250, f"{a}" if share else f"{a} · {birth_year + a}",
                      9, MUTED))

    # ---- framework bands --------------------------------------------
    y = 282
    bands = [("Jung · stages of life", tl["bands"]["jung"]),
             ("Levinson · seasons of a life", tl["bands"]["levinson"]),
             ("Erikson · the central conflict", tl["bands"]["erikson"])]
    for label, stages in bands:
        s.append(_band_row(x0, x1, y, 22, stages, span, color, accent, age, label))
        y += 46

    # ---- BaZi luck pillars -------------------------------------------
    lp = tl.get("luck_pillars")
    if lp:
        s.append(_txt(x0, y - 7, "BAZI · TEN YEAR LUCK PILLARS", 9, MUTED,
                      anchor="start", extra='letter-spacing="1.6"'))
        for p in lp["pillars"]:
            if p["start_age"] >= span:
                break
            bx, bw = X(p["start_age"]), X(min(p["end_age"], span)) - X(p["start_age"])
            live = p["start_age"] <= age < p["end_age"]
            s.append(f'<rect x="{bx:.1f}" y="{y}" width="{max(bw - 2, 1):.1f}" '
                     f'height="22" fill="{accent if live else color}" '
                     f'opacity="{0.22 if live else 0.07}"/>')
            name = f'{p["gan"]} {p["zhi"]}'
            if bw > 58:
                s.append(_txt(bx + 6, y + 15.2, name, 9,
                              accent if live else MUTED, anchor="start",
                              weight=500 if live else 400))
        y += 46
    else:
        s.append(_txt(x0, y + 8, "BaZi luck pillars need a birth sex to set their "
                                 "direction, so they are left out here.", 9, MUTED,
                      anchor="start", opacity=0.8))
        y += 30

    # ---- transit markers ---------------------------------------------
    s.append(_txt(x0, y - 7, "PLANETARY CYCLES · DATED", 9, MUTED,
                  anchor="start", extra='letter-spacing="1.6"'))
    ty = y + 42
    s.append(f'<line x1="{x0}" y1="{ty}" x2="{x1}" y2="{ty}" stroke="{color}" '
             f'stroke-width="0.6" opacity="0.25"/>')
    short = {"Saturn return": "Saturn return", "Saturn square Saturn": "Saturn sq",
             "Saturn opposition Saturn": "Saturn opp",
             "Uranus opposition Uranus": "Uranus opp",
             "Neptune square Neptune": "Neptune sq", "Pluto square Pluto": "Pluto sq"}
    # Markers cluster badly in the forties, where four different cycles land
    # within a few years. Labels are assigned to lanes above and below the line,
    # and a lane is only taken if the text actually clears what is already in it.
    lanes = [(-1, 11, 22), (1, 16, 27), (-1, 33, 44), (1, 38, 49)]
    lane_end = [-1e9] * len(lanes)
    drawn = []
    for e in sorted(tl["transits"], key=lambda e: e["age"]):
        if e["age"] > span:
            continue
        ex = X(e["age"])
        big = e["weight"] >= 2
        lab = short.get(e["label"], e["label"])
        w = max(len(lab), 4) * _CHAR_W * 9 + 8
        slot = None
        for i in range(len(lanes)):
            if ex - w / 2 > lane_end[i]:
                slot = i
                break
        s.append(f'<circle cx="{ex:.1f}" cy="{ty}" r="{4.5 if big else 3}" '
                 f'fill="{accent if big else color}" opacity="{1 if big else 0.55}"/>')
        if slot is None:                       # no room anywhere: dot only
            continue
        lane_end[slot] = ex + w / 2
        sign, d_lab, d_year = lanes[slot]
        yl = ty + sign * d_lab if sign > 0 else ty - d_lab
        yy = ty + sign * d_year if sign > 0 else ty - d_year
        s.append(_txt(ex, yl, lab, 9, color if big else MUTED,
                      weight=500 if big else 400))
        s.append(_txt(ex, yy, f'age {e["age"]}' if share else f'{e["year"]}',
                      8.5, MUTED))
        drawn.append(lab)

    # ---- the one row a birth chart cannot fill --------------------------
    ly = y + 118
    s.append(_txt(x0, ly - 7, "YOUR ACTUAL LIFE", 9, MUTED, anchor="start",
                  extra='letter-spacing="1.6"'))
    s.append(f'<rect x="{x0}" y="{ly}" width="{x1 - x0:.1f}" height="26" fill="none" '
             f'stroke="{color}" stroke-width="0.8" stroke-dasharray="5 5" opacity="0.4"/>')
    s.append(_txt((x0 + x1) / 2, ly + 17,
                  "no data yet · a birth chart cannot know what you have lived",
                  10, MUTED, extra='font-style="italic"'))
    s.append(f'<circle cx="{x0}" cy="{ly + 13}" r="3.5" fill="{color}" opacity="0.7"/>')
    s.append(_txt(x0 + 2, ly + 42, "birth", 9, MUTED, anchor="start"))

    s.append("</svg>")
    return "".join(s)
