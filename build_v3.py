# -*- coding: utf-8 -*-
"""Decoda · Self v3 renderer (2026-09-28).

Same content schema and same visual identity as build_v2 (DeFonte + Montserrat,
ink #0B0B0B, paper #F2EFE6, gold #8C6A2E, paper grain, thin rules, spaced
upper-case labels). What changed is the page system:

- Text sections FLOW. A block may continue on the next page, so there are no
  half-empty pages and no word budget to calibrate. Sections still open on a
  fresh page, except the short ones that follow a related section
  (07 after 06, 08 after 07, 10 after 09).
- Real page numbers, a running section header, a linked table of contents on
  "Before you begin", and PDF bookmarks.
- Computed cards that need no writing: a portrait-at-a-glance page, a profile
  card at the head of each lens, a larger element chart with the four pillars,
  a landscape timeline, the seven-year table grouped lived / now / ahead.
- Presentation-only upgrades of written content: divergence titles of the form
  "X versus Y" set as two poles, protocols as a numbered reference list,
  two-clocks mechanics replaced by the named source when the writer gave none.

Nothing on these pages is invented: every card reads the computed chart or
repeats a title the writer already produced.

Usage is unchanged:  build_v3.generate(order, content, "out.pdf")
"""
import os, html, re, datetime
from weasyprint import HTML
import engine, viz, timeline

HERE = os.path.dirname(os.path.abspath(__file__))
PRODUCT = "Decoda · Self"
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
INK, PAPER, GOLD = "#0B0B0B", "#F2EFE6", "#8C6A2E"

# ------------------------------------------------------------------ fonts
_LOCAL = os.environ.get("DECODA_FONT_DIR")            # dev: folder of .woff2 files
_DESK = os.path.join(HERE, "..", "font")               # desktop build: .ttf files
if _LOCAL and os.path.isdir(_LOCAL):
    _F = lambda n: "file://" + os.path.join(_LOCAL, n + ".woff2")
    _MONT = "".join(
        f"@font-face{{font-family:'Montserrat';font-weight:{w};src:url('file://{_LOCAL}/montserrat-latin-{w}-normal.woff2')}}"
        f"@font-face{{font-family:'Montserrat';font-weight:{w};src:url('file://{_LOCAL}/montserrat-latin-ext-{w}-normal.woff2');unicode-range:U+0100-024F,U+1E00-1EFF}}"
        for w in (300, 400, 500, 600))
elif os.path.isdir(_DESK):
    _F = lambda n: "file://" + os.path.join(_DESK, n + ".ttf")
    _MONT = "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap');"
else:
    _F = lambda n: "https://trydecoda.com/font/" + n + ".woff2"
    _MONT = "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap');"


# ------------------------------------------------------------------ paper
def _tiles():
    """Pre-blend the grain onto paper and ink so @page backgrounds need no opacity."""
    out = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "decoda-tiles")
    os.makedirs(out, exist_ok=True)
    paths = {k: os.path.join(out, k + ".jpg") for k in ("paper", "ink")}
    if all(os.path.exists(p) for p in paths.values()):
        return paths
    from PIL import Image
    g = Image.open(os.path.join(HERE, "grain.png")).convert("L")
    for key, base, alpha in (("paper", (242, 239, 230), 0.13), ("ink", (11, 11, 11), 0.08)):
        bg = Image.new("RGB", g.size, base)
        grain = Image.merge("RGB", (g, g, g))
        Image.blend(bg, grain, alpha).save(paths[key], quality=78, optimize=True)
    return paths


_T = _tiles()
_PAPER_BG = f"{PAPER} url('file://{_T['paper']}')"
_INK_BG = f"{INK} url('file://{_T['ink']}')"

CSS = _MONT + f"""
@font-face{{font-family:'DeFonte';src:url('{_F("DeFontePlus-Leger")}');font-weight:300}}
@font-face{{font-family:'DeFonte';src:url('{_F("DeFontePlus-Normale")}');font-weight:400}}
@font-face{{font-family:'DeFonte';src:url('{_F("DeFontePlus-DemiGras")}');font-weight:600}}

@page{{size:A4;margin:24mm 22mm 25mm 22mm;background:{_PAPER_BG};background-size:95mm;
  @top-left{{content:string(sec, first-except);font-family:'Montserrat';font-weight:500;font-size:7pt;
    letter-spacing:.3em;text-transform:uppercase;color:rgba(11,11,11,.42);vertical-align:bottom;padding-bottom:7mm}}
  @bottom-left{{content:"{PRODUCT}";font-family:'Montserrat';font-size:7pt;letter-spacing:.22em;
    text-transform:uppercase;color:rgba(11,11,11,.45);vertical-align:top;padding-top:9mm}}
  @bottom-right{{content:counter(page);font-family:'Montserrat';font-size:7.5pt;letter-spacing:.1em;
    color:rgba(11,11,11,.55);vertical-align:top;padding-top:9mm}}}}
@page dark{{background:{_INK_BG};background-size:95mm;
  @top-left{{content:none}}
  @bottom-left{{color:rgba(242,239,230,.42)}} @bottom-right{{color:rgba(242,239,230,.5)}}}}
@page cover{{background:{_INK_BG};background-size:95mm;
  @top-left{{content:none}} @bottom-left{{content:none}} @bottom-right{{content:none}}}}
@page land{{size:A4 landscape;margin:15mm 22mm 17mm 22mm;@top-left{{content:none}}}}
.land .viz svg{{height:136mm;width:auto;max-width:100%;margin:0 auto}}

*{{margin:0;padding:0;box-sizing:border-box}}
body{{color:{INK};font-family:'Montserrat'}}
h1,h2,h3,h4{{bookmark-level:none}}
.sheet{{height:247mm;display:flex;flex-direction:column;break-after:page;color:{PAPER}}}
.sheet.cover{{page:cover}} .sheet.dark{{page:dark}}
.sec{{break-before:page}} .sec.cont{{break-before:auto;margin-top:12mm}}
.land{{page:land;break-before:page}}
.lab{{font-family:'Montserrat';font-size:8pt;letter-spacing:.34em;text-transform:uppercase;font-weight:500;opacity:.55}}
.secl{{string-set:sec content();bookmark-level:1;bookmark-label:content()}}
.rule{{height:1px;background:currentColor;opacity:.2;margin:5mm 0}}
.big{{font-family:'DeFonte';font-weight:600;line-height:1.04;letter-spacing:-.02em}}
.ins{{font-family:'DeFonte';font-weight:600;font-size:20pt;line-height:1.1;letter-spacing:-.01em;margin-bottom:4mm;break-after:avoid}}
h1{{font-family:'DeFonte';font-weight:600;font-size:40pt;line-height:1.0;letter-spacing:-.015em}}
p{{font-weight:400;font-size:11.5pt;line-height:1.66;margin-bottom:3.6mm;max-width:158mm;orphans:3;widows:3}}
p.lead{{font-size:13pt;line-height:1.56}}
.dim{{opacity:.55}}
.block{{margin-bottom:7mm}} .tail{{break-inside:avoid}} .keep{{break-inside:avoid}}
.mech{{font-size:8.2pt;letter-spacing:.12em;text-transform:uppercase;color:{GOLD};font-weight:500;
  margin:0 0 0 0;padding-top:2mm;border-top:1px solid rgba(140,106,46,.35);display:inline-block;break-before:avoid;line-height:1.5}}
.mech b{{font-weight:600;opacity:.8}}
.center{{flex:1;display:flex;flex-direction:column}} .push{{flex:1}}
.kv{{font-size:9.3pt;line-height:1.95;font-weight:300}} .kv b{{font-weight:500}}
.two{{display:flex;gap:12mm}} .two>div{{flex:1}}
.viz svg{{display:block;width:100%;height:auto}}
.cap{{font-size:8.6pt;line-height:1.5;opacity:.65;margin-top:3mm}}
.trust{{border:1px solid currentColor;border-radius:4mm;padding:6mm 7mm;margin-top:8mm}}
.trust p{{margin-bottom:0;font-size:9.8pt}}

/* table of contents */
#begin.tight h1{{font-size:30pt!important}} #begin.tight p{{font-size:10.4pt;line-height:1.55}} #begin.tight p.lead{{font-size:11.5pt}}
#begin.tight .toc a{{font-size:9.4pt;line-height:1.6}} #begin.tight .toc .part{{padding:2.4mm 0}} #begin.tight .trust{{margin-top:5mm;padding:4mm 6mm}}
.toc{{margin-top:8mm;display:flex;gap:10mm}} .toc>div{{flex:1}}
.toc .part{{display:flex;gap:6mm;padding:3.2mm 0;border-top:1px solid rgba(11,11,11,.14)}}
.toc .pn{{font-family:'DeFonte';font-weight:600;font-size:15pt;width:9mm;color:{GOLD}}}
.toc .pt{{font-size:7.6pt;letter-spacing:.26em;text-transform:uppercase;font-weight:500;opacity:.6;margin-bottom:1.4mm}}
.toc a{{display:block;color:inherit;text-decoration:none;font-size:10pt;line-height:1.75}}
.toc a::after{{content:target-counter(attr(href), page);float:right;opacity:.55;font-size:9pt}}

/* cards */
.card{{border-top:none;border-bottom:1px solid rgba(11,11,11,.18);padding:5mm 0 5mm 0;margin:1mm 0 9mm 0;break-inside:avoid}}
.cols{{display:flex;gap:7mm}} .cols>div{{flex:1}}
.k{{font-size:7.4pt;letter-spacing:.24em;text-transform:uppercase;font-weight:500;opacity:.55;margin-bottom:1.6mm}}
.v{{font-family:'DeFonte';font-weight:600;font-size:21pt;line-height:1.05;letter-spacing:-.01em}}
.v.sm{{font-size:14pt;line-height:1.15}}
.small{{font-size:9.4pt;line-height:1.6}}
.chip{{display:inline-block;font-size:8.8pt;line-height:1.3;border:1px solid rgba(11,11,11,.28);border-radius:10mm;padding:1mm 3mm;margin:0 1.6mm 1.8mm 0}}
.hr{{height:1px;background:rgba(11,11,11,.14);margin:4.5mm 0}}
table.pil{{width:100%;border-collapse:collapse;margin-top:2mm}}
table.pil th{{font-size:7.2pt;letter-spacing:.22em;text-transform:uppercase;font-weight:500;opacity:.55;text-align:left;padding:0 2mm 2mm 0}}
table.pil td{{font-size:10pt;line-height:1.45;padding:2mm 2mm 2mm 0;border-top:1px solid rgba(11,11,11,.12);vertical-align:top}}
table.pil td.dm{{color:{GOLD};font-weight:500}}

.els{{margin-top:3.5mm}}
.el{{display:flex;align-items:center;gap:3mm;margin-bottom:2.2mm}}
.el .n{{width:15mm;font-size:7.6pt;letter-spacing:.2em;text-transform:uppercase;font-weight:500;opacity:.75}}
.el .t{{flex:1;height:2.6mm;background:rgba(11,11,11,.07);position:relative}}
.el .t b{{position:absolute;left:0;top:0;bottom:0;background:{INK}}}
.el.dm .t b{{background:{GOLD}}}
.el .c{{width:6mm;text-align:right;font-size:9pt;font-weight:600}}
/* at a glance */
.glance.tight ul li,.glance.tight ol li{{font-size:10pt;margin-bottom:1.8mm}} .glance.tight .cols{{margin-top:7mm!important}}
.glance.tight .v.sm{{font-size:14pt}} .glance.tight .note{{margin-top:4mm}}
.glance .big{{font-size:28pt;margin:2mm 0 10mm 0}} .glance .v.sm{{font-size:16pt;line-height:1.2}} .glance .cols{{gap:8mm}}
.glance .sys{{border-top:1px solid rgba(11,11,11,.55);padding-top:3mm}}
.glance ol{{list-style:none;counter-reset:n}}
.glance ol li{{counter-increment:n;font-size:11pt;line-height:1.5;margin-bottom:2.6mm;padding-left:7mm;position:relative}}
.glance ol li::before{{content:counter(n);position:absolute;left:0;color:{GOLD};font-weight:600}}
.glance ul{{list-style:none}}
.glance ul li{{font-size:11pt;line-height:1.5;margin-bottom:2.6mm}} .glance .sys .k{{margin-bottom:2.6mm}}
.note{{font-size:9.4pt;line-height:1.55;margin-top:6mm;padding:4mm 5mm;background:rgba(140,106,46,.08);border-left:2px solid {GOLD}}}
.note a{{color:inherit}}
.note a::after{{content:" (page " target-counter(attr(href), page) ")"}}

/* divergence poles */
.poles{{display:flex;align-items:center;gap:4mm;margin-bottom:4mm;break-after:avoid}}
.poles .pole{{font-family:'DeFonte';font-weight:600;font-size:19pt;line-height:1.1;flex:0 1 auto}}
.poles .mid{{flex:1;min-width:18mm;border-top:1px solid rgba(140,106,46,.6);text-align:center;margin-top:1mm}}
.poles .mid span{{display:inline-block;font-size:6.8pt;letter-spacing:.24em;text-transform:uppercase;color:{GOLD};margin-top:1.2mm}}

/* protocols */
.proto{{display:flex;gap:6mm;padding:3.2mm 0 1.4mm 0;border-top:1px solid rgba(11,11,11,.16)}}
.proto .n{{font-family:'DeFonte';font-weight:600;font-size:28pt;line-height:.9;color:{GOLD};width:12mm;flex:none}}
.proto .ins{{font-size:14pt;margin-bottom:1.4mm}}
.proto p{{font-size:10.2pt;line-height:1.5;margin-bottom:1.8mm}} .proto .block{{margin:0}}

/* strengths */
ul.st{{list-style:none;margin-top:5mm}}
ul.st li{{font-size:11.2pt;line-height:1.6;margin-bottom:3.6mm;padding-left:7mm;position:relative;break-inside:avoid}}
ul.st li::before{{content:'·';position:absolute;left:0;color:{GOLD};font-weight:600}}

/* two clocks */
.steps{{display:flex;align-items:stretch;margin:2mm 0 7mm 0;break-inside:avoid}}
.steps .st{{flex:1;border-top:2px solid {GOLD};padding:2.4mm 3mm 0 0;font-size:9.4pt;line-height:1.35;font-weight:500}}
.steps .st small{{display:block;font-size:6.8pt;letter-spacing:.2em;text-transform:uppercase;opacity:.5;font-weight:500;margin-bottom:1mm}}
.steps .gap{{width:3mm;flex:none}}

/* seven years */
table.yr{{width:100%;border-collapse:collapse;font-size:8.6pt;line-height:1.32}}
table.yr th{{text-align:left;font-weight:500;font-size:7pt;letter-spacing:.2em;text-transform:uppercase;opacity:.55;padding:0 3mm 2.5mm 0;border-bottom:1px solid rgba(11,11,11,.25)}}
table.yr td{{vertical-align:top;padding:1.6mm 3mm 1.6mm 0;border-bottom:1px solid rgba(11,11,11,.12)}}
table.yr tr{{break-inside:avoid}}
table.yr tr.grp td{{font-size:7.4pt;letter-spacing:.24em;text-transform:uppercase;font-weight:600;color:{GOLD};padding:3mm 0 1.2mm 0;border-bottom:1px solid rgba(140,106,46,.5)}}
table.yr tr.now td{{background:rgba(140,106,46,.09)}}
table.yr .hl{{font-family:'DeFonte';font-weight:600;font-size:10.5pt;line-height:1.12;display:block;margin-top:.8mm}}
table.yr .yy{{font-family:'DeFonte';font-weight:600;font-size:13pt}}
"""


# ------------------------------------------------------------------ helpers
def _e(t): return html.escape(str(t or ""))


def _paras(t, cls=""):
    c = f' class="{cls}"' if cls else ""
    return "".join(f"<p{c}>{_e(x.strip())}</p>" for x in str(t or "").split("\n\n") if x.strip())


def _mech(t, label="Mechanics"):
    t = (t or "").strip()
    if not t or t.lower() in ("none", "n/a", "-"):
        return ""
    return f'<div class="mech"><b>{_e(label)}</b> · {_e(t)}</div>'


def _body_mech(body, mech_html):
    """Paragraphs, with the last one glued to its mechanics line so a
    mechanics line never lands alone at the top of a page."""
    ps = [x.strip() for x in str(body or "").split("\n\n") if x.strip()]
    if not ps:
        return mech_html
    head = "".join(f"<p>{_e(x)}</p>" for x in ps[:-1])
    return head + f'<div class="tail"><p>{_e(ps[-1])}</p>{mech_html}</div>'


def _block(b, title_html=None, mech_html=None):
    t = title_html if title_html is not None else f'<div class="ins">{_e(b.get("title", ""))}</div>'
    m = mech_html if mech_html is not None else _mech(b.get("mech"))
    return f'<div class="block">{t}{_body_mech(b.get("body", ""), m)}</div>'


def _sec(sid, label, inner, cont=False, lead=None):
    """inner = html string, or a list of block html strings. With a list, the
    section head (label, rule, lead) is glued to the first block's opening so a
    head never sits alone at the bottom of a page."""
    lead_html = f'<p class="lead" style="margin-bottom:7mm">{_e(lead)}</p>' if lead else ""
    head = f'<div class="lab secl">{_e(label)}</div><div class="rule"></div>{lead_html}'
    if isinstance(inner, list):
        first, rest = (inner[0], inner[1:]) if inner else ("", [])
        inner = f'<div class="keep">{head}{first}</div>' + "".join(rest)
        head = ""
    return f'<section class="sec{" cont" if cont else ""}" id="{sid}">{head}{inner}</section>'


def _sheet(cls, inner):
    return f'<div class="sheet {cls}"><div class="center">{inner}</div></div>'


_CENTRE = {"SolarPlexus": "Solar Plexus", "G": "G (identity)"}
_STRATEGY = {"Generator": "To respond", "Manifesting Generator": "To respond, then inform",
             "Projector": "Wait for the invitation", "Manifestor": "To inform",
             "Reflector": "Wait a lunar cycle"}
_PLANET_SET = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rising", "MC")


def _aspects_named(chart, content):
    """Computed aspects that the written portrait actually names in a mechanics
    line. Falls back to the tightest Sun / Moon / Rising aspects."""
    try:
        import portrait
        asp = portrait.aspects(chart["astro"])
    except Exception:
        return []
    mech = " ".join((b.get("mech") or "") for k in ("core_body", "lens_astro")
                    for b in (content.get(k) or [])).lower()
    named = []
    for x in asp:
        a, b, kind = x["a"].lower(), x["b"].lower(), x["aspect"]
        rx = rf"\b{a}\b(?:\s+\w+){{0,2}}\s+{kind}\w*\s+(?:\w+\s+){{0,2}}{b}\b|\b{b}\b(?:\s+\w+){{0,2}}\s+{kind}\w*\s+(?:\w+\s+){{0,2}}{a}\b"
        if re.search(rx, mech):
            named.append(x)
    if not named:
        core = [x for x in asp if {x["a"], x["b"]} & {"Sun", "Moon", "Rising"}]
        named = sorted(core, key=lambda x: x["orb"])[:3]
    return named[:6]


def _nice(p): return {"MC": "Midheaven"}.get(p, p)


# ------------------------------------------------------------------ cards
def _astro_card(a, chart, content, approx):
    rise = a["rising"] + (" (approx.)" if approx else "")
    aspects = _aspects_named(chart, content)
    chips = "".join(f'<span class="chip">{_nice(x["a"])} {x["aspect"]} {_nice(x["b"])}</span>' for x in aspects)
    return f"""<div class="card"><div class="cols">
      <div><div class="k">Sun · identity</div><div class="v">{_e(a['sun'])}</div></div>
      <div><div class="k">Moon · emotional needs</div><div class="v">{_e(a['moon'])}</div></div>
      <div><div class="k">Rising · how you come across</div><div class="v">{_e(rise)}</div></div></div>
      <div class="hr"></div>
      <div class="cols"><div style="flex:1"><div class="k">Also in your chart</div>
        <div class="small">{" · ".join(f"{p}&nbsp;{_e(a[p.lower()])}" for p in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"))}</div></div>
      <div style="flex:1.3"><div class="k">Aspects read in this portrait</div>{chips or '<span class="small dim">none named</span>'}</div></div></div>"""


def _bazi_card(b):
    pl = b["pillars"]
    cols = [("Year", "year"), ("Month", "month"), ("Day", "day"), ("Hour", "hour")]
    head = "".join(f"<th{' style=color:' + GOLD if k == 'day' else ''}>{n}</th>" for n, k in cols)
    stem = "".join(f"<td class=\"{'dm' if k == 'day' else ''}\">{_e(pl[k]['gan'])}</td>" for _, k in cols)
    br = "".join(f"<td>{_e(pl[k]['zhi'])} · {_e(pl[k]['animal'])}<br><span class='dim'>{_e(pl[k]['zhi_element'])}</span></td>" for _, k in cols)
    try:
        import portrait
        rel = portrait.branch_relations(b)
    except Exception:
        rel = []
    rel_html = "".join(f'<span class="chip">{_e(r)}</span>' for r in rel)
    bars = _element_bars(b["elements"], b.get("day_master_element"))
    return f"""<div class="card"><div class="cols">
      <div style="flex:1.05"><div class="k">Five elements · count of 8 positions</div>{bars}
        <div class="cap">A count across the eight stems and branches of your four pillars, not a score. Gold marks your day master element. Dominant {_e(b['dominant'])} · scarce {_e(b['scarce'])}.</div></div>
      <div><div class="k">Day master</div><div class="v">{_e(b['day_master'])}</div>
        <table class="pil"><tr><th></th>{head}</tr><tr><td class="dim small">Stem</td>{stem}</tr><tr><td class="dim small">Branch</td>{br}</tr></table></div></div>
      {'<div class="hr"></div><div class="k">Relations between your branches</div>' + rel_html if rel_html else ''}</div>"""


def _element_bars(el, dm=None):
    rows = []
    for k in ("Wood", "Fire", "Earth", "Metal", "Water"):
        v = int(el.get(k, 0))
        rows.append(f'<div class="el{" dm" if k == dm else ""}"><div class="n">{k}</div><div class="t"><b style="width:{v / 8 * 100:.1f}%"></b></div><div class="c">{v}</div></div>')
    return '<div class="els">' + "".join(rows) + "</div>"


def _hd_card(h):
    cen = lambda xs: " · ".join(_CENTRE.get(x, x) for x in xs) or "none"
    ch = "".join(f'<span class="chip">{_e(c)}</span>' for c in h.get("channels", [])) or '<span class="small dim">none</span>'
    return f"""<div class="card"><div class="cols">
      <div style="flex:1.4"><div class="k">Type</div><div class="v">{_e(h['type'])}</div></div>
      <div><div class="k">Authority</div><div class="v">{_e(h['authority'])}</div></div>
      <div><div class="k">Profile</div><div class="v">{_e(h['profile'])}</div></div></div>
      <div class="hr"></div>
      <div class="cols"><div><div class="k">Strategy</div><div class="small">{_e(_STRATEGY.get(h['type'], ''))}</div>
        <div class="k" style="margin-top:3.5mm">Channels</div>{ch}</div>
      <div><div class="k">Defined centres</div><div class="small">{_e(cen(h['defined']))}</div>
        <div class="k" style="margin-top:3.5mm">Open centres</div><div class="small">{_e(cen(h['open']))}</div></div></div></div>"""


# ------------------------------------------------------------------ pages
_PARTS = [
    ("1", "See yourself", [("glance", "Your portrait at a glance"), ("s-core", "The core pattern")]),
    ("2", "Three lenses", [("s-astro", "Western astrology"), ("s-bazi", "BaZi"), ("s-hd", "Human Design")]),
    ("3", "Connect the lenses", [("s-conv", "Where they agree"), ("s-div", "Where they pull apart"),
                                 ("s-shadow", "The shadow"), ("s-str", "Your strengths")]),
    ("4", "Use it", [("s-conn", "How you connect"), ("s-work", "Work and output"), ("s-proto", "Protocols")]),
    ("5", "Look back, look up", [("s-tl", "Your timeline"), ("s-seven", "Seven years"),
                                 ("s-clocks", "Two clocks"), ("s-life", "Your actual life"), ("s-raw", "The raw chart")]),
]


def _toc(present):
    rows = []
    for n, name, items in _PARTS:
        links = "".join(f'<a href="#{i}">{_e(t)}</a>' for i, t in items if i in present)
        if links:
            rows.append(f'<div class="part"><div class="pn">{n}</div><div style="flex:1"><div class="pt">{_e(name)}</div>{links}</div></div>')
    return ('<div class="lab" style="margin-top:9mm">Inside</div><div class="toc"><div>' + "".join(rows[:3]) +
            '</div><div>' + "".join(rows[3:]) + "</div></div>")


def _glance(order, chart, c, approx):
    a, b, h = chart["astro"], chart["bazi"], chart["hd"]
    rise = a["rising"] + (" (approx.)" if approx else "")
    agree = "".join(f"<li>{_e(i['title'])}</li>" for i in c["convergence"]["items"])
    apart = "".join(f"<li>{_e(i['title'])}</li>" for i in c["divergence"]["items"])
    rules = "".join(f"<li>{_e(i['title'])}</li>" for i in c["protocols"])
    n = len(c["core_statement"])
    big = 28 if n <= 120 else 24 if n <= 170 else 20 if n <= 240 else 17
    items = len(c["convergence"]["items"]) + len(c["divergence"]["items"])
    tight = " tight" if items > 5 or n > 170 else ""
    seven = '<div class="note">Start with the three lived years on the <a href="#s-seven">seven-year page</a>. If they do not sound like your life, trust the rest less.</div>' if order.get("_timeline") else ""
    return f"""<section class="sec glance{tight}" id="glance"><div class="lab secl">Your portrait at a glance</div><div class="rule"></div>
      <div class="k">The core pattern</div><div class="big" style="font-size:{big}pt">{_e(c['core_statement'])}</div>
      <div class="cols">
        <div class="sys"><div class="k">Western astrology</div><div class="v sm">{_e(a['sun'])} Sun<br>{_e(a['moon'])} Moon<br>{_e(rise)} Rising</div></div>
        <div class="sys"><div class="k">BaZi</div><div class="v sm">{_e(b['day_master'])}<br>{_e(b['dominant'])} dominant<br>{_e(b['scarce'])} scarce</div></div>
        <div class="sys"><div class="k">Human Design</div><div class="v sm">{_e(h['type'])}<br>{_e(h['authority'])} authority<br>{_e(h['profile'])} profile</div></div></div>
      <div class="cols" style="margin-top:11mm">
        <div class="sys"><div class="k">Where the systems agree</div><ul>{agree}</ul></div>
        <div class="sys"><div class="k">Where they pull apart</div><ul>{apart}</ul></div></div>
      <div class="sys" style="margin-top:9mm"><div class="k">Your protocols</div><ol>{rules}</ol></div>
      {seven}</section>"""


_VS = re.compile(r"^\s*(.+?)\s+(?:versus|vs\.?)\s+(.+?)\s*$", re.I)


def _div_block(b):
    m = _VS.match(b.get("title", ""))
    if not m:
        return _block(b)
    l, r = m.group(1), m.group(2)
    r = r[:1].upper() + r[1:]
    t = f'<div class="poles"><div class="pole">{_e(l)}</div><div class="mid"><span>versus</span></div><div class="pole">{_e(r)}</div></div>'
    return _block(b, t)


def _protocols(items):
    out = []
    for n, b in enumerate(items, 1):
        out.append(f'<div class="proto" style="break-inside:avoid"><div class="n">{n}</div><div style="flex:1">'
                   f'<div class="ins">{_e(b.get("title", ""))}</div>{_body_mech(b.get("body", ""), _mech(b.get("mech")))}</div></div>')
    return "".join(out)


CLOCKS_LEAD = ("Two maps of inner change, neither tied to a date. The first comes from trauma treatment "
               "(Judith Herman, Trauma and Recovery): if you recognise yourself in its second phase, walk it "
               "with a professional, not alone. The second is Jung's four stages of therapy (Problems of "
               "Modern Psychotherapy, 1929). Only you can say where you stand.")
_HERMAN = ("safety", "remembrance", "mourning", "reconnection")
_JUNG = ("confession", "elucidation", "education", "transformation")
SRC_HERMAN = "Judith Herman, Trauma and Recovery (1992)"
SRC_JUNG = "C. G. Jung, Problems of Modern Psychotherapy (1929)"


def _clocks(block):
    steps = lambda name, xs: ('<div class="steps">' + '<div class="gap"></div>'.join(
        f'<div class="st"><small>{name} · {i + 1}</small>{_e(x)}</div>' for i, x in enumerate(xs)) + "</div>")
    head = (steps("Herman", ["Safety", "Remembrance and mourning", "Reconnection"]) +
            steps("Jung", ["Confession", "Elucidation", "Education", "Transformation"]))
    out = []
    for b in block["items"]:
        t = (b.get("title") or "").lower()
        mech = (b.get("mech") or "").strip()
        if not mech or mech.lower() in ("none", "n/a", "-"):
            src = SRC_HERMAN if any(w in t for w in _HERMAN) else SRC_JUNG if any(w in t for w in _JUNG) else ""
            out.append(_block(b, mech_html=_mech(src, "Source") if src else ""))
        else:
            out.append(_block(b))
    return head + "".join(out)


def _timeline_page(tl):
    arc = viz.life_arc(tl, width=1000, color=viz.INK, accent=GOLD, bg=viz.PAPER)
    arc = arc.replace("#B7B2A8", "#5B5851").replace("#D6B982", GOLD)
    return f"""<section class="land" id="s-tl"><div class="two" style="align-items:flex-end;gap:8mm"><div style="flex:1.3"><div class="lab secl">12 · Your timeline</div>
      <div class="ins" style="margin:2.5mm 0 0 0">Your life as one arc, every date calculated.</div></div>
      <div><p class="small" style="margin:0">Read it from the left. The years behind the dotted line are ones you can check against memory; the markers ahead are dates, not events.</p></div></div>
      <div class="viz" style="margin-top:3mm">{arc}</div>
      <div class="cap" style="margin-top:1mm">Bands: Jung, Levinson, Erikson. Markers: dated returns and oppositions from Swiss Ephemeris. Luck pillars from your BaZi. Nothing on this page is written, only calculated.</div></section>"""


def _seven_page(tl):
    groups = {"past": [], "now": [], "ahead": []}
    for y in tl["years"]:
        bz = y["bazi"]; d = y.get("detail") or {}
        rel = f" · {_e(bz['relation_to_day'])}" if bz.get("relation_to_day") else ""
        god = (d.get("bazi") or {}).get("god")
        god = f"<br><span class='dim'>{_e(god)}</span>" if god else ""
        tr = "<br>".join(f"{_e(t['label'])}, {_e(t['date'][:7])}" for t in y["transits"]) or "<span class='dim'>none</span>"
        groups[y["state"]].append(f"""<tr class="{'now' if y['state'] == 'now' else ''}">
          <td><span class="yy">{y['year']}</span><br><span class="dim">age {y['age']}</span></td>
          <td>House {y['house']} · {_e(y['sign'])}<br><span class="dim">{_e(y['topic'])}</span><span class="hl">{_e(d.get('headline', ''))}</span></td>
          <td>{y['personal_year']}</td>
          <td>{_e(bz['gan'])} {_e(bz['zhi'])} ({_e(bz['animal'])}){rel}{god}</td>
          <td>{tr}</td></tr>""")
    names = {"past": "Already lived · check these against memory", "now": "This year",
             "ahead": "Ahead · dates, not events"}
    rows = "".join(f'<tr class="grp"><td colspan="5">{names[k]}</td></tr>' + "".join(v)
                   for k, v in groups.items() if v)
    return _sec("s-seven", "12 · Seven years, three already lived",
                f'<table class="yr"><tr><th>Year</th><th>Year of the house</th><th>No.</th><th>BaZi year</th><th>Dated cycles</th></tr>{rows}</table>'
                '<p class="cap" style="margin-top:4mm">Year of the house: the annual profection from your Rising sign. No.: numerology personal year. BaZi year: the year pillar and how it meets your day branch.</p>',
                lead="Check the three lived years first. If they do not sound like your life, trust the rest less.")


# ------------------------------------------------------------------ document
_BAD_CLOCK = [
    re.compile(r"\byou are (now |currently )?in (the )?(phase|stage)\b", re.I),
    re.compile(r"\byou('re| are) (now |currently )?(at|in) (the )?(first|second|third|fourth) (phase|stage)\b", re.I),
    re.compile(r"\b(19|20)\d\d\b[^.]{0,80}\b(phase|stage|shadow|confession|elucidation|education|transformation|remembrance|mourning|reconnection)\b", re.I),
    re.compile(r"\b(phase|stage|shadow|confession|elucidation|education|transformation|remembrance|mourning|reconnection)\b[^.]{0,80}\b(19|20)\d\d\b", re.I),
]


def _qc_clocks(block):
    txt = " ".join([block.get("lead") or ""] + [f"{i.get('title', '')} {i.get('body', '')}" for i in block["items"]])
    for rx in _BAD_CLOCK:
        m = rx.search(txt)
        if m:
            raise ValueError(f"QC fail, section 13 (two clocks): '{m.group(0)}'")


def build_html(order, chart, c):
    a, b, h = chart["astro"], chart["bazi"], chart["hd"]
    approx = order.get("birth_time_confidence") in ("approx", "unknown")
    tl = order.get("_timeline")
    clocks = c.get("two_clocks") if c.get("two_clocks") and c["two_clocks"].get("items") else None
    life = c.get("actual_life") if c.get("actual_life") and c["actual_life"].get("items") else None
    present = {"glance", "s-core", "s-astro", "s-bazi", "s-hd", "s-conv", "s-div", "s-shadow", "s-str",
               "s-conn", "s-work", "s-proto", "s-raw"}
    if tl:
        present |= {"s-tl", "s-seven"}
    if clocks:
        present.add("s-clocks")
    if life:
        present.add("s-life")
    pg = []

    # cover
    pg.append(_sheet("cover", f"""<div class="lab">Decoda® · Self</div>
      <div class="lab" style="margin-top:2mm">A portrait in three lenses</div><div class="push"></div>
      <div class="big" style="font-size:60pt">{_e(c['archetype'])}</div>
      <div style="height:9mm"></div><p class="lead" style="opacity:.6">{_e(c['essence'])}</p>
      <div class="push"></div><div class="rule"></div>
      <div class="two"><div class="kv"><b>For</b><br>{_e(order['name'])}</div>
      <div class="kv"><b>Born</b><br>{_e(order['birth_str'])}</div>
      <div class="kv"><b>Place</b><br>{_e(order['place'])}</div></div>"""))

    # before you begin + contents
    trust = ""
    if c.get("trust_block"):
        trust = f'<div class="trust"><div class="lab" style="margin-bottom:3mm">What to trust less</div>{_paras(c["trust_block"])}</div>'
    pg.append(f"""<section class="sec{' tight' if trust else ''}" id="begin" style="break-before:auto"><div class="lab secl">Before you begin</div><div class="rule"></div>
      <h1 style="font-size:38pt">A mirror,<br>not a prediction.</h1><div style="height:6mm"></div>
      <p class="lead">Decoda reads three systems for understanding people: Western astrology, the Chinese system of BaZi, and Human Design, and translates them into plain language.</p>
      <p>You don't need to know any of them. Under each statement you'll see the machinery it's built from, drawn from your specific chart. Where the three systems agree, the signal is strong. Where they disagree, we say so. Nothing here is fate. You decide what's true.</p>{trust}
      {_toc(present)}</section>""")

    pg.append(_glance(order, chart, c, approx))
    pg.append(_sec("s-core", "01 · The core pattern", [_block(x) for x in c["core_body"]]))
    pg.append(_sec("s-astro", "02 · Lens one · Western astrology",
                   [_astro_card(a, chart, c, approx)] + [_block(x) for x in c["lens_astro"]]))
    pg.append(_sec("s-bazi", "03 · Lens two · BaZi", [_bazi_card(b)] + [_block(x) for x in c["lens_bazi"]]))
    pg.append(_sec("s-hd", "04 · Lens three · Human Design", [_hd_card(h)] + [_block(x) for x in c["lens_hd"]]))
    pg.append(_sec("s-conv", "05 · Convergence", [_block(x) for x in c["convergence"]["items"]],
                   lead=c["convergence"].get("lead")))
    pg.append(_sec("s-div", "06 · Divergence", [_div_block(x) for x in c["divergence"]["items"]],
                   lead=c["divergence"].get("lead") or "A reading that pretends everything lines up is lying to you. Here is where your own systems pull apart."))
    pg.append(_sec("s-shadow", "07 · The shadow", [_block(x) for x in c["shadow"]["items"]], cont=True,
                   lead=c["shadow"].get("lead") or "Not flaws to delete. The shadow cast by the exact things that make you good."))
    st = "".join(f"<li>{_e(s)}</li>" for s in c["strengths"]["items"])
    pg.append(_sec("s-str", "08 · Your strengths",
                   [f'<div class="ins" style="font-size:26pt">What you\'re built to do well.</div><ul class="st">{st}</ul>'],
                   cont=True, lead=c["strengths"].get("lead")))
    pg.append(_sec("s-conn", "09 · How you connect", [_block(x) for x in c["connect"]]))
    pg.append(_sec("s-work", "10 · Work & output", [_block(x) for x in c["work"]], cont=True))
    pg.append(_sec("s-proto", "11 · Protocols", _protocols(c["protocols"]),
                   lead="Rules you can actually run. Each one is built from your chart, not from general advice."))
    if tl:
        pg.append(_timeline_page(tl))
        pg.append(_seven_page(tl))
    if clocks:
        _qc_clocks(clocks)
        pg.append(_sec("s-clocks", "13 · Two clocks the calendar does not move", _clocks(clocks),
                       lead=CLOCKS_LEAD + (" " + clocks["lead"] if clocks.get("lead") else "")))
    if life:
        pg.append(_sec("s-life", "14 · Your actual life", [_block(x) for x in life["items"]], lead=life.get("lead")))

    pg.append(_sheet("dark", f"""<div class="lab">Closing</div><div class="rule"></div><div class="push"></div>
      <div class="big" style="font-size:34pt">{_e(c['closing'])}</div>
      <p class="lead" style="margin-top:9mm;opacity:.55">A language for reflection, not a forecast. You decide what's true.</p><div class="push"></div>"""))

    el = b["elements"]; pl = b["pillars"]
    def _pill(k): return f"{pl[k]['gan']} over {pl[k]['zhi']} ({pl[k]['zhi_element']})"
    ch = " · ".join(h.get("channels", [])) or "-"
    cen = lambda xs: " · ".join(_CENTRE.get(x, x) for x in xs) or "-"
    pg.append(_sec("s-raw", "Appendix · the raw chart", f"""
      <h1 style="font-size:28pt">The data behind the reading.</h1>
      <p class="dim" style="font-size:9.5pt;margin-top:4mm">Swiss Ephemeris positions; Chinese lunisolar pillars. Every statement in this portrait is built from these. Check us.</p><div class="rule"></div>
      <div class="two"><div>
        <div class="lab">Western astrology</div><div class="kv" style="margin-top:3mm"><b>Sun</b> {a['sun']} · <b>Moon</b> {a['moon']}<br><b>Rising</b> {a['rising']} · <b>Midheaven</b> {a['mc']}<br><b>Mercury</b> {a['mercury']} · <b>Venus</b> {a['venus']}<br><b>Mars</b> {a['mars']} · <b>Jupiter</b> {a['jupiter']}<br><b>Saturn</b> {a['saturn']}</div>
        <div class="lab" style="margin-top:6mm">BaZi · four pillars</div><div class="kv" style="margin-top:3mm"><b>Day master</b> {b['day_master']}<br><b>Year</b> {_pill('year')}<br><b>Month</b> {_pill('month')}<br><b>Day</b> {_pill('day')}<br><b>Hour</b> {_pill('hour')}<br>Wood {el['Wood']} · Fire {el['Fire']} · Earth {el['Earth']} · Metal {el['Metal']} · Water {el['Water']}<br>Dominant {b['dominant']} · Scarce {b['scarce']}</div>
      </div><div>
        <div class="lab">Human Design</div><div class="kv" style="margin-top:3mm"><b>Type</b> {h['type']}<br><b>Authority</b> {h['authority']} · <b>Profile</b> {h['profile']}<br><b>Defined</b> {cen(h['defined'])}<br><b>Open</b> {cen(h['open'])}<br><b>Channels</b> {ch}</div>
        <div class="lab" style="margin-top:6mm">Where to read more</div><div class="kv" style="margin-top:3mm">Sun, Moon, Rising: page <a href="#s-astro" class="pgref"></a><br>Pillars and elements: page <a href="#s-bazi" class="pgref"></a><br>Type and authority: page <a href="#s-hd" class="pgref"></a></div>
      </div></div>"""))

    extra = "a.pgref{color:inherit;text-decoration:none} a.pgref::after{content:target-counter(attr(href), page)}"
    return ("<html><head><meta charset='utf-8'><title>Decoda · Self</title><style>" + CSS + extra +
            "</style></head><body>" + "".join(pg) + "</body></html>")


def generate(order, content, out_path):
    """order may carry display overrides for privacy (public samples):
    'name_display', 'birth_display', 'place_display' replace what is PRINTED
    while the chart is still computed from the real data."""
    y, mo, d = [int(x) for x in order["date"].split("-")]
    hh, mm = [int(x) for x in order["time"].split(":")]
    chart = engine.compute(y, mo, d, hh, mm, order["lat"], order["lon"], order["tz"])
    order = dict(order)
    order["birth_str"] = order.get("birth_display") or f"{d:02d} {MON[mo - 1]} {y}, {order['time']}"
    order["name"] = order.get("name_display") or order["name"]
    order["place"] = order.get("place_display") or order["place"]
    try:
        order["_timeline"] = timeline.build(chart, datetime.date(y, mo, d), gender=order.get("sex"))
    except Exception as ex:          # a missing timeline must never block a delivery
        print("timeline skipped:", ex)
        order["_timeline"] = None
    HTML(string=build_html(order, chart, content), base_url=HERE).write_pdf(out_path)
    return chart
