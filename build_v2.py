# -*- coding: utf-8 -*-
"""Decoda · Self v2 renderer.
Takes (order dict, content dict per REPORT-SPEC.md) and renders the 18-24 page PDF.
Content is written per order by the LLM pipeline (see REPORT-SPEC.md prompt system),
QC'd via QC-CHECKLIST.md, then rendered here. Design language unchanged from v1.

Usage:
    import build_v2
    build_v2.generate(order, content, "out.pdf")
order   = {"name","date":"YYYY-MM-DD","time":"HH:MM","lat","lon","tz","place",
           "birth_time_confidence": "exact"|"approx"|"unknown"}
content = dict, keys below (see CONTENT SCHEMA).

CONTENT SCHEMA (all text plain, paragraphs split by \\n\\n, no em dashes):
  archetype: str            essence: str
  trust_block: str|None     core_statement: str
  core_body:   [ {title, body, mech} ]
  lens_astro:  [ {title, body, mech} ]      lens_bazi: [...]   lens_hd: [...]
  convergence: {lead: str, items: [{title, body, mech}]}
  divergence:  {lead: str, items: [{title, body, mech}]}
  shadow:      {lead: str, items: [{title, body, mech}]}
  strengths:   {lead: str, items: [str]}
  connect:     [ {title, body, mech} ]      work: [ {title, body, mech} ]
  protocols:   [ {title, body, mech} ]      closing: str
  two_clocks:  {lead?, items:[{title, body, mech}]}   optional, QC-guarded (REPORT-SPEC 5b)
  actual_life: {lead?, items:[{title, body, mech}]}   optional, only if intake had life_events
  order["sex"] optional ("male"/"female"), needed only for luck pillar direction
"""
import os, html
from weasyprint import HTML
import re, datetime
import engine, viz, timeline

HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FONT = os.path.join(HERE, "..", "font")
# Local TTFs when building on the desktop; on the server (public repo, no font
# files committed) the same faces are loaded from the live site.
if os.path.isdir(_LOCAL_FONT):
    FONT_URL = lambda n: "file://" + os.path.join(_LOCAL_FONT, n + ".ttf")
else:
    FONT_URL = lambda n: "https://trydecoda.com/font/" + n + ".woff2"
GRAIN = "file://" + os.path.join(HERE, "grain.png")

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600&display=swap');
@font-face{{font-family:'DeFonte';src:url('{FONT_URL("DeFontePlus-Leger")}');font-weight:300}}
@font-face{{font-family:'DeFonte';src:url('{FONT_URL("DeFontePlus-Normale")}');font-weight:400}}
@font-face{{font-family:'DeFonte';src:url('{FONT_URL("DeFontePlus-DemiGras")}');font-weight:600}}
@page{{size:A4;margin:0}}
@page land{{size:A4 landscape;margin:0}}
.p.land{{page:land;width:297mm;height:210mm;padding:14mm 20mm}}
.land .viz svg{{height:138mm;width:auto;max-width:100%;margin:0 auto}}
table.yr{{width:100%;border-collapse:collapse;font-family:'Montserrat';font-size:8.6pt;line-height:1.45}}
table.yr th{{text-align:left;font-weight:500;font-size:7pt;letter-spacing:.2em;text-transform:uppercase;opacity:.55;padding:0 3mm 2.5mm 0;border-bottom:1px solid rgba(11,11,11,.25)}}
table.yr td{{vertical-align:top;padding:3mm 3mm 3mm 0;border-bottom:1px solid rgba(11,11,11,.12)}}
table.yr tr.now td{{background:rgba(11,11,11,.05)}}
table.yr .hl{{font-family:'DeFonte';font-weight:600;font-size:11pt;line-height:1.15;display:block;margin-top:1mm}}
*{{margin:0;padding:0;box-sizing:border-box}}
.p{{position:relative;width:210mm;height:297mm;overflow:hidden;padding:26mm 22mm;page-break-after:always}}
.p:last-child{{page-break-after:auto}}
.dark{{background:#0B0B0B;color:#F2EFE6}} .light{{background:#F2EFE6;color:#0B0B0B}}
.grain{{position:absolute;inset:0;background:url('{GRAIN}');background-size:360px;opacity:.08}}
.light .grain{{opacity:.13}}
.z{{position:relative;z-index:2;height:100%}}
.big{{font-family:'DeFonte';font-weight:600;line-height:1.02;letter-spacing:-.02em}}
.lab{{font-family:'Montserrat';font-size:8pt;letter-spacing:.34em;text-transform:uppercase;font-weight:500}}
.dim{{opacity:.5}}
h1{{font-family:'DeFonte';font-weight:600;font-size:40pt;line-height:1.0;letter-spacing:-.015em}}
.ins{{font-family:'DeFonte';font-weight:600;font-size:20pt;line-height:1.08;letter-spacing:-.01em;margin-bottom:4mm}}
p{{font-family:'Montserrat';font-weight:400;font-size:11.5pt;line-height:1.68;margin-bottom:3.6mm;max-width:158mm}}
p.lead{{font-size:13pt;line-height:1.58;font-weight:400}}
.mech{{font-family:'Montserrat';font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;opacity:.55;margin:1mm 0 8mm 0}}
.rule{{height:1px;background:currentColor;opacity:.2;margin:5mm 0}}
.center{{display:flex;flex-direction:column;justify-content:center;height:100%}}
.push{{margin-top:auto}}
.foot{{position:absolute;left:22mm;right:22mm;bottom:13mm;z-index:2;display:flex;justify-content:space-between;font-family:'Montserrat';font-size:7.5pt;letter-spacing:.22em;text-transform:uppercase;opacity:.45}}
.two{{display:flex;gap:13mm}} .two>div{{flex:1}}
.kv{{font-family:'Montserrat';font-size:9.3pt;line-height:1.95;font-weight:300}} .kv b{{font-weight:500}}
.block{{margin-bottom:6mm}}
.src{{font-family:'Montserrat';font-size:7.8pt;letter-spacing:.16em;text-transform:uppercase;opacity:.42;margin-top:1mm}}
.trust{{border:1px solid currentColor;border-radius:4mm;padding:6mm 7mm;margin-top:8mm;opacity:.85}}
.trust p{{margin-bottom:0;font-size:9.5pt}}
ul.st{{list-style:none;margin-top:6mm}}
ul.st li{{font-family:'Montserrat';font-weight:400;font-size:11.5pt;line-height:1.62;margin-bottom:4.5mm;padding-left:7mm;position:relative}}
ul.st li:before{{content:'·';position:absolute;left:0;opacity:.5}}
.viz{{margin:6mm 0 3mm 0}}
.viz svg{{display:block;width:100%;height:auto}}
.viz.sm{{max-width:118mm;margin-left:auto;margin-right:auto}}
.viz-cap{{font-family:'Montserrat';font-size:7.8pt;opacity:.6;margin-top:3mm;margin-bottom:2mm}}
"""

MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
WORDS_PER_PAGE = 285   # body-word budget per light page. Re-calibrated 07/2026 after the mobile
                       # readability bump (body 11.5pt / weight 400): 300 words = 85.3% of page
                       # height, 270 = 80.6%, footer sits ~95%. 285 is safe and keeps the airy
                       # look. Always run check_render.py after generating; re-calibrate via the
                       # ink test if type size ever changes.

PRODUCT = "Decoda · Self"   # footer product label; build_two overrides to "Decoda · Two"

def _e(t): return html.escape(str(t or ""))
def _paras(t):
    return "".join(f"<p>{_e(x.strip())}</p>" for x in str(t or "").split("\n\n") if x.strip())
def _P(cls, inner, foot=""):
    return f'<div class="p {cls}"><div class="grain"></div><div class="z">{inner}</div>{foot}</div>'
def _ft(label, n):
    return f'<div class="foot"><span>{PRODUCT}</span><span>{_e(label)}{(" · " + n) if n else ""}</span></div>'
def _mech(t):
    return f'<div class="mech">Mechanics · {_e(t)}</div>' if t else ""
def _block(b):
    return f'<div class="block"><div class="ins">{_e(b.get("title",""))}</div>{_paras(b.get("body",""))}{_mech(b.get("mech"))}</div>'

def _wc(b): return len(str(b.get("body","")).split()) + 18

def _paginate(blocks, budget=WORDS_PER_PAGE, first_budget=None):
    pages, cur, used = [], [], 0
    limit = first_budget if first_budget is not None else budget
    for b in blocks:
        w = _wc(b)
        if cur and used + w > limit:
            pages.append(cur); cur, used = [], 0
            limit = budget
        cur.append(b); used += w
    if cur: pages.append(cur)
    return pages

def _section_pages(lab, blocks, lead=None, foot_lab=""):
    """Light pages for one section; lead paragraph on first page only."""
    out = []
    # a lead paragraph costs vertical space on the first page: shrink its budget
    first = WORDS_PER_PAGE - (len(str(lead).split()) + 40 if lead else 0)
    pages = _paginate(blocks, first_budget=first)
    for i, pg in enumerate(pages):
        head = f'<div class="lab dim">{_e(lab)}</div><div class="rule"></div>'
        if i == 0 and lead:
            head += f'<p class="lead" style="margin-bottom:7mm">{_e(lead)}</p>'
        out.append(_P("light", head + "".join(_block(b) for b in pg), _ft(foot_lab or lab, "")))
    return out

def _statement_page(lab, statement, size="40pt", sub=None):
    sub_html = f'<p class="lead dim" style="margin-top:9mm">{_e(sub)}</p>' if sub else ""
    return _P("dark", f"""<div class="center"><div class="lab dim">{_e(lab)}</div><div class="rule"></div>
      <div class="push"></div><div class="big" style="font-size:{size}">{_e(statement)}</div>{sub_html}<div class="push"></div></div>""", _ft(lab, ""))

# ---------------------------------------------------------------- time sections

CLOCKS_LEAD = ("Two maps of inner change, neither tied to a date. The first comes from trauma treatment "
               "(Judith Herman, Trauma and Recovery): if you recognise yourself in its second phase, walk it "
               "with a professional, not alone. The second is Jung's four stages of therapy (Problems of "
               "Modern Psychotherapy, 1929). Only you can say where you stand.")

_BAD_CLOCK = [
    re.compile(r"\byou are (now |currently )?in (the )?(phase|stage)\b", re.I),
    re.compile(r"\byou('re| are) (now |currently )?(at|in) (the )?(first|second|third|fourth) (phase|stage)\b", re.I),
    re.compile(r"\b(19|20)\d\d\b[^.]{0,80}\b(phase|stage|shadow|confession|elucidation|education|transformation|remembrance|mourning|reconnection)\b", re.I),
    re.compile(r"\b(phase|stage|shadow|confession|elucidation|education|transformation|remembrance|mourning|reconnection)\b[^.]{0,80}\b(19|20)\d\d\b", re.I),
]

def _qc_clocks(block):
    """REPORT-SPEC 5b guardrails 1-2, enforced in code: never place the reader in
    a phase, never tie a phase to a calendar year. Fails the build, not a warning."""
    txt = " ".join([block.get("lead") or ""] + [f"{i.get('title','')} {i.get('body','')}" for i in block["items"]])
    for rx in _BAD_CLOCK:
        m = rx.search(txt)
        if m:
            raise ValueError(f"QC fail, section 13 (two clocks): '{m.group(0)}'")

def _timeline_pages(tl):
    # Light portrait page, ink on paper: the same page the homepage shows.
    GOLD = "#8C6A2E"
    arc = viz.life_arc(tl, width=1000, color=viz.INK, accent=GOLD, bg=viz.PAPER)
    arc = arc.replace("#B7B2A8", "#5B5851").replace("#D6B982", GOLD)
    out = [_P("light", f"""<div class="lab dim">12 · Your timeline</div><div class="rule"></div>
      <div class="ins">Your life as one arc, every date calculated.</div>
      <div class="viz" style="margin-top:4mm">{arc}</div>
      <div class="viz-cap">Bands: Jung, Levinson, Erikson. Markers: dated returns and oppositions from Swiss Ephemeris. Luck pillars from your BaZi. Nothing on this page is written, only calculated.</div>
      <div class="rule"></div>
      <p style="font-size:10pt">Read it from the left. The years behind the dotted line are ones you can check against memory; the markers ahead are dates, not events. The next page lists seven years, three of them already lived.</p>""",
      _ft("12", ""))]
    rows = []
    for y in tl["years"]:
        bz = y["bazi"]; d = y.get("detail") or {}
        rel = f" · {_e(bz['relation_to_day'])}" if bz.get("relation_to_day") else ""
        god = (d.get("bazi") or {}).get("god")
        god = f"<br>{_e(god)}" if god else ""
        tr = "<br>".join(f"{_e(t['label'])}, {_e(t['date'][:7])}" for t in y["transits"]) or "<span class='dim'>none</span>"
        state = {"past": "lived", "now": "now", "ahead": "ahead"}[y["state"]]
        rows.append(f"""<tr class="{'now' if y['state']=='now' else ''}">
          <td><b>{y['year']}</b><br><span class="dim">{state} · age {y['age']}</span></td>
          <td>House {y['house']} · {_e(y['sign'])}<br><span class="dim">{_e(y['topic'])}</span><span class="hl">{_e(d.get('headline',''))}</span></td>
          <td>{y['personal_year']}</td>
          <td>{_e(bz['gan'])} {_e(bz['zhi'])} ({_e(bz['animal'])}){rel}{god}</td>
          <td>{tr}</td></tr>""")
    out.append(_P("light", f"""<div class="lab dim">12 · Seven years, three already lived</div><div class="rule"></div>
      <p class="lead" style="margin-bottom:6mm">Check the three lived years first. If they do not sound like your life, trust the rest less.</p>
      <table class="yr"><tr><th>Year</th><th>Year of the house</th><th>No.</th><th>BaZi year</th><th>Dated cycles</th></tr>{''.join(rows)}</table>""",
      _ft("12", "")))
    return out

def build_html(order, chart, c):
    a, b, h = chart["astro"], chart["bazi"], chart["hd"]
    pg = []

    # 0 · cover
    pg.append(_P("dark", f"""
      <div class="center"><div class="lab dim">Decoda® · Self</div>
      <div class="lab dim" style="margin-top:2mm">A portrait in three lenses</div>
      <div class="push"></div>
      <div class="big" style="font-size:60pt">{_e(c['archetype'])}</div>
      <div style="height:9mm"></div><p class="lead dim">{_e(c['essence'])}</p>
      <div class="push"></div><div class="rule"></div>
      <div class="two"><div class="kv"><b>For</b><br>{_e(order['name'])}</div>
      <div class="kv"><b>Born</b><br>{_e(order['birth_str'])}</div>
      <div class="kv"><b>Place</b><br>{_e(order['place'])}</div></div></div>"""))

    # 1 · how to read
    trust = ""
    if c.get("trust_block"):
        trust = f'<div class="trust"><div class="lab dim" style="margin-bottom:3mm">What to trust less</div>{_paras(c["trust_block"])}</div>'
    pg.append(_P("light", f"""
      <div class="lab dim">Before you begin</div><div class="rule"></div>
      <h1 style="font-size:46pt">A mirror,<br>not a prediction.</h1><div style="height:9mm"></div>
      <p class="lead">Decoda reads three systems for understanding people: Western astrology, the Chinese system of BaZi, and Human Design, and translates them into plain language.</p>
      <p>You don't need to know any of them. Under each statement you'll see the machinery it's built from, drawn from your specific chart. This portrait was written for your chart alone and checked against it, line by line. Where the three systems agree, the signal is strong. Where they disagree, we say so. Nothing here is fate. You decide what's true.</p>{trust}""", _ft("Before you begin","")))

    # 2 · core pattern
    pg.append(_statement_page("01 · The core pattern", c["core_statement"], "40pt"))
    pg += _section_pages("01 · The core pattern", c["core_body"], foot_lab="01")

    # 3-5 · lenses
    pg += _section_pages("02 · Lens one · Western astrology", c["lens_astro"], foot_lab="02")
    # BaZi at a glance: element-balance infographic before the written lens
    _bars = viz.element_bars(b["elements"], color=viz.INK, title="Five-element balance")
    pg.append(_P("light", f"""<div class="lab dim">03 · Lens two · BaZi</div><div class="rule"></div>
      <div class="ins">Your balance of the five elements.</div>
      <div class="viz sm">{_bars}</div>
      <div class="viz-cap">Day master {_e(b['day_master'])} · dominant {_e(b['dominant'])} · scarce {_e(b['scarce'])}. The reading that follows is built from this distribution.</div>""", _ft("03", "")))
    pg += _section_pages("03 · Lens two · BaZi", c["lens_bazi"], foot_lab="03")
    pg += _section_pages("04 · Lens three · Human Design", c["lens_hd"], foot_lab="04")

    # 6 · convergence (opener with three-systems diagram; normal flow so the SVG keeps its height)
    _conv = viz.convergence_diagram(color=viz.PAPER, agree=True)
    pg.append(_P("dark", f"""<div class="lab dim" style="margin-top:14mm">05 · Convergence</div><div class="rule"></div>
      <div class="big" style="font-size:40pt;margin-top:10mm">What all three keep pointing at.</div>
      <div class="viz sm" style="margin-top:16mm">{_conv}</div>""", _ft("05", "")))
    pg += _section_pages("05 · Convergence", c["convergence"]["items"], lead=c["convergence"].get("lead"), foot_lab="05")

    # 7 · divergence
    pg += _section_pages("06 · Divergence", c["divergence"]["items"],
                         lead=c["divergence"].get("lead") or "A reading that pretends everything lines up is lying to you. Here is where your own systems pull apart.",
                         foot_lab="06")

    # 8 · shadow
    pg += _section_pages("07 · The shadow", c["shadow"]["items"],
                         lead=c["shadow"].get("lead") or "Not flaws to delete. The shadow cast by the exact things that make you good.",
                         foot_lab="07")

    # 9 · strengths
    st = "".join(f"<li>{_e(s)}</li>" for s in c["strengths"]["items"])
    lead = c["strengths"].get("lead")
    lead_html = f'<p class="lead" style="margin-bottom:5mm">{_e(lead)}</p>' if lead else ""
    pg.append(_P("light", f"""<div class="lab dim">08 · Your strengths</div><div class="rule"></div>
      <h1 style="font-size:32pt">What you're built to do well.</h1><div style="height:7mm"></div>{lead_html}<ul class="st">{st}</ul>""", _ft("08","")))

    # 10 · connect + work
    pg += _section_pages("09 · How you connect", c["connect"], foot_lab="09")
    pg += _section_pages("10 · Work & output", c["work"], foot_lab="10")

    # 11 · protocols
    pg += _section_pages("11 · Protocols", c["protocols"],
                         lead="Rules you can actually run. Each one is built from your chart, not from general advice.",
                         foot_lab="11")

    # 12-14 · time (REPORT-SPEC 5b). 12 is computed only; 13-14 come from content.
    if order.get("_timeline"):
        pg += _timeline_pages(order["_timeline"])
    if c.get("two_clocks"):
        _qc_clocks(c["two_clocks"])
        pg += _section_pages("13 · Two clocks the calendar does not move", c["two_clocks"]["items"],
                             lead=CLOCKS_LEAD + (" " + c["two_clocks"]["lead"] if c["two_clocks"].get("lead") else ""),
                             foot_lab="13")
    if c.get("actual_life") and c["actual_life"].get("items"):
        pg += _section_pages("14 · Your actual life", c["actual_life"]["items"],
                             lead=c["actual_life"].get("lead"), foot_lab="14")

    # closing + appendix
    pg.append(_statement_page("Closing", c["closing"], "36pt",
                              sub="A language for reflection, not a forecast. You decide what's true."))
    el = b["elements"]; pl = b["pillars"]
    def _pill(k): return f"{pl[k]['gan']} over {pl[k]['zhi']} ({pl[k]['zhi_element']})"
    ch = " · ".join(h.get("channels", [])) or "-"
    pg.append(_P("light", f"""<div class="lab dim">Appendix · the raw chart</div><div class="rule"></div>
      <h1 style="font-size:28pt">The data behind the reading.</h1>
      <p class="dim" style="font-size:9.5pt;margin-top:4mm">Swiss Ephemeris positions; Chinese lunisolar pillars. Every statement in this portrait is built from these. Check us.</p><div class="rule"></div>
      <div class="two"><div>
        <div class="lab">Western astrology</div><div class="kv" style="margin-top:3mm"><b>Sun</b> {a['sun']} · <b>Moon</b> {a['moon']}<br><b>Rising</b> {a['rising']}<br><b>Mercury</b> {a['mercury']} · <b>Venus</b> {a['venus']}<br><b>Mars</b> {a['mars']}</div>
        <div class="lab" style="margin-top:6mm">BaZi · four pillars</div><div class="kv" style="margin-top:3mm"><b>Day Master</b> {b['day_master']}<br><b>Year</b> {_pill('year')}<br><b>Month</b> {_pill('month')}<br><b>Day</b> {_pill('day')}<br><b>Hour</b> {_pill('hour')}<br>Wood {el['Wood']} · Fire {el['Fire']} · Earth {el['Earth']} · Metal {el['Metal']} · Water {el['Water']}<br>Dominant {b['dominant']} · Scarce {b['scarce']}</div>
        <div class="viz" style="margin-top:5mm">{viz.element_bars(el, color=viz.INK)}</div>
      </div><div>
        <div class="lab">Human Design</div><div class="kv" style="margin-top:3mm"><b>Type</b> {h['type']}<br><b>Authority</b> {h['authority']} · <b>Profile</b> {h['profile']}<br><b>Defined</b> {' · '.join(h['defined']) or '-'}<br><b>Open</b> {' · '.join(h['open']) or '-'}<br><b>Channels</b> {ch}</div>
      </div></div>""", _ft("Appendix","")))

    return "<html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>" + "".join(pg) + "</body></html>"

def generate(order, content, out_path):
    """order may carry display overrides for privacy (e.g. public samples):
    'name_display', 'birth_display', 'place_display' replace what is PRINTED
    while the chart is still computed from the real data."""
    y, mo, d = [int(x) for x in order["date"].split("-")]
    hh, mm = [int(x) for x in order["time"].split(":")]
    chart = engine.compute(y, mo, d, hh, mm, order["lat"], order["lon"], order["tz"])
    order = dict(order)
    order["birth_str"] = order.get("birth_display") or f"{d:02d} {MON[mo-1]} {y}, {order['time']}"
    order["name"] = order.get("name_display") or order["name"]
    order["place"] = order.get("place_display") or order["place"]
    try:
        order["_timeline"] = timeline.build(chart, datetime.date(y, mo, d), gender=order.get("sex"))
    except Exception as ex:          # a missing timeline must never block a delivery
        print("timeline skipped:", ex)
        order["_timeline"] = None
    HTML(string=build_html(order, chart, content)).write_pdf(out_path)
    return chart
