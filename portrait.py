# -*- coding: utf-8 -*-
"""Decoda · Self, automated fulfilment.

    request -> chart (engine) -> content (Claude API, REPORT-SPEC prompt)
            -> automatic QC (+ one repair round) -> PDF (build_v2)
            -> review email to Decoda with a one-click approve link
            -> on approve: delivery email to the reader with the PDF

A human still presses "approve" for every portrait. The QC here catches what
code can catch (invented placements, forbidden words, em dashes, the Herman
guardrails, overflow). Taste is still checked by eye, for now.

Env:
  ANTHROPIC_API_KEY   required
  RESEND_API_KEY      required for email
  APPROVE_SECRET      required, any long random string
  DECODA_MODEL        default claude-sonnet-5
  REVIEW_TO           default trydecoda@gmail.com
  MAIL_FROM           default "Decoda <portrait@trydecoda.com>"
  PUBLIC_BASE         default https://decoda-glimpse.onrender.com
  DATA_DIR            default /tmp/decoda-orders
"""
import os, re, json, hmac, hashlib, secrets, base64, time, traceback
from datetime import datetime, date
import requests

import engine, timeline

MODEL = os.environ.get("DECODA_MODEL", "claude-sonnet-5")
REVIEW_TO = os.environ.get("REVIEW_TO", "trydecoda@gmail.com")
MAIL_FROM = os.environ.get("MAIL_FROM", "Decoda <portrait@trydecoda.com>")
PUBLIC_BASE = os.environ.get("PUBLIC_BASE", "https://decoda-glimpse.onrender.com")
DATA_DIR = os.environ.get("DATA_DIR", "/tmp/decoda-orders")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------- prompt

SYSTEM = """You are the writer for Decoda, a premium self-knowledge instrument.
You are given a computed chart (JSON). It is the ONLY source of truth.

HARD RULES
1. GROUNDING: every claim must be traceable to at least one field in the JSON. Never invent gates, channels, placements, pillars or aspects that are not in the JSON. Every block has a "mech" line listing the exact factors used, written like "Virgo Sun · Sacral authority · scarce Water".
2. SWAP TEST: before keeping any sentence, ask: would this sentence survive being pasted into a different chart's report? If yes, delete or sharpen it.
3. CROSS-SYSTEM DEPTH: prefer interaction between systems ("your Virgo Mercury sharpens your Sacral yes/no into words") over three parallel one-system readings.
4. DIVERGENCE HONESTY: find the real tensions in THIS chart. Never manufacture fake conflict, never smooth over real conflict. If there are fewer than 2 real tensions, say plainly where the chart runs in one direction.
5. VOICE: a sharp, warm observer speaking plainly. Second person. No fortune-teller voice, no "the universe", no predictions of events, no flattery padding. Confident sentences, varied length. British-neutral English. Smart adult reading level, no unexplained jargon.
6. FORBIDDEN: em dashes and en dashes (use . , : ( ) or a hyphen). The words journey, unlock, embrace, vibration, energy field. Any sentence that is a compliment without information.
7. If birth_time_confidence is not "exact": fill trust_block, naming rising, the Human Design chart and the hour pillar as less reliable. Otherwise trust_block is null.
8. The shadow is the dark side of the reader's own strengths, written to be seen, never to frighten.
9. No clinical diagnosis. No medical, legal or financial advice.

WORD BUDGET (body words): core_body 400-550, each lens 450-600, convergence 300-400, divergence 450-600, shadow 400-550, strengths 250-350, connect + work 500-650 together, protocols 350-450 (4-6 rules, at least 2 crossing systems), closing 40-80.

TWO CLOCKS (two_clocks, 450-600 words): describe Judith Herman's three phases of recovery (safety, remembrance and mourning, reconnection) and Jung's four stages (confession, elucidation, education, transformation), each with signs by which a reader could recognise it. You may use real chart factors ONLY to say which phase tends to be hard for this structure. NEVER say or imply which phase or stage the reader is in. NEVER tie a phase or stage to a year or date. Do not write numbers of years anywhere in this section.

ACTUAL LIFE (actual_life): only if the request includes life events. Place each event the reader gave at its age, and relate it only to cycles that had ALREADY happened by then (from the timeline JSON). Do not project forward. If there are no life events, actual_life is null.

OUTPUT: a single JSON object, no prose before or after, with exactly these keys:
archetype (2-4 words), essence (1-2 sentences), trust_block (string or null), core_statement (one sentence, max 22 words),
core_body, lens_astro, lens_bazi, lens_hd, connect, work, protocols: arrays of {"title","body","mech"},
convergence, divergence, shadow, two_clocks: {"lead": string, "items": [{"title","body","mech"}]},
strengths: {"lead": string, "items": [string]},
actual_life: null or {"lead": string, "items": [{"title","body","mech"}]},
closing: string.
Paragraphs inside a body are separated by \\n\\n. Plain text, no markdown."""


def _call(messages, max_tokens=16000):
    key = os.environ["ANTHROPIC_API_KEY"]
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": max_tokens, "system": SYSTEM,
              "messages": messages},
        timeout=900,
    )
    r.raise_for_status()
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []))
    usage = data.get("usage", {})
    return text, usage


def _parse(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    return json.loads(t[a:b + 1])


def _chart_payload(chart, tl, order):
    c = {k: chart[k] for k in ("astro", "bazi", "hd") if k in chart}
    c["meta"] = {"name": order["name"], "birth_time_confidence": order.get("birth_time_confidence", "exact")}
    if tl:
        c["timeline"] = {
            "age_now": tl["age"],
            "luck_pillars": tl["luck_pillars"],
            "past_cycles": [e for e in tl["transits"] if e["date"] <= date.today().isoformat()],
        }
    return c


def write_content(chart, tl, order):
    user = "CHART JSON:\n" + json.dumps(_chart_payload(chart, tl, order), ensure_ascii=False, default=str)
    if order.get("life_events"):
        user += "\n\nLIFE EVENTS the reader gave (their words):\n" + order["life_events"][:1500]
    else:
        user += "\n\nLIFE EVENTS: none given. actual_life must be null."
    msgs = [{"role": "user", "content": user}]
    text, usage = _call(msgs)
    return _parse(text), msgs, text, usage


def repair(msgs, prev_text, issues):
    msgs = msgs + [{"role": "assistant", "content": prev_text},
                   {"role": "user", "content": "Automatic QC found these problems. Fix every one and return the full corrected JSON only:\n- " + "\n- ".join(issues)}]
    text, usage = _call(msgs)
    return _parse(text), text, usage

# ---------------------------------------------------------------- automatic QC

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
BODIES = ["Sun", "Moon", "Rising", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
FORBIDDEN = ["journey", "unlock", "embrace", "vibration", "energy field", "the universe"]
LIST_KEYS = ["core_body", "lens_astro", "lens_bazi", "lens_hd", "connect", "work", "protocols"]
DICT_KEYS = ["convergence", "divergence", "shadow", "strengths"]


def _all_text(c):
    return json.dumps(c, ensure_ascii=False)


def auto_qc(c, chart):
    issues = []
    for k in ["archetype", "essence", "core_statement", "closing"] + LIST_KEYS + DICT_KEYS:
        if not c.get(k):
            issues.append(f"missing or empty key: {k}")
    for k in LIST_KEYS:
        for i, b in enumerate(c.get(k) or []):
            if not isinstance(b, dict) or not b.get("body") or not b.get("mech"):
                issues.append(f"{k}[{i}] needs title, body and mech")
    txt = _all_text(c)
    if "—" in txt or "–" in txt:
        issues.append("contains em or en dashes; replace them")
    low = txt.lower()
    for w in FORBIDDEN:
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            issues.append(f"forbidden phrase: '{w}'")
    # grounding: any "<Sign> <Body>" or "<Body> in <Sign>" must match the chart
    astro = chart["astro"]
    for m in re.finditer(r"\b(" + "|".join(SIGNS) + r")[ -](" + "|".join(BODIES) + r")\b", txt):
        sign, body = m.group(1), m.group(2)
        real = astro.get(body.lower())
        if real and real != sign:
            issues.append(f"'{sign} {body}' is not in this chart ({body} is in {real})")
    for m in re.finditer(r"\b(" + "|".join(BODIES) + r") in (" + "|".join(SIGNS) + r")\b", txt):
        body, sign = m.group(1), m.group(2)
        real = astro.get(body.lower())
        if real and real != sign:
            issues.append(f"'{body} in {sign}' is not in this chart ({body} is in {real})")
    hd = chart["hd"]
    for t in ["Manifesting Generator", "Generator", "Projector", "Manifestor", "Reflector"]:
        if re.search(r"\b(you are|as) an? " + t + r"\b", txt) and t not in hd["type"]:
            issues.append(f"calls the reader a {t}; their type is {hd['type']}")
    # Herman / Jung guardrails live in build_v2._qc_clocks; run them here too
    try:
        import build_v2
        if c.get("two_clocks"):
            build_v2._qc_clocks(c["two_clocks"])
    except ValueError as e:
        issues.append(str(e))
    return sorted(set(issues))


def fix_dashes(c):
    s = json.dumps(c, ensure_ascii=False)
    s = s.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
    return json.loads(s)

# ---------------------------------------------------------------- orders

def _sig(oid):
    return hmac.new(os.environ["APPROVE_SECRET"].encode(), oid.encode(), hashlib.sha256).hexdigest()[:32]


def check_sig(oid, sig):
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{10,40}", oid or "")) and hmac.compare_digest(_sig(oid), sig or "")


def _path(oid, ext):
    return os.path.join(DATA_DIR, f"{oid}.{ext}")


def load(oid):
    with open(_path(oid, "json")) as f:
        return json.load(f)


def save(oid, rec):
    with open(_path(oid, "json"), "w") as f:
        json.dump(rec, f, ensure_ascii=False, default=str)

# ---------------------------------------------------------------- email (Resend)

def send_mail(to, subject, text, pdf_path=None, filename=None, reply_to=None):
    payload = {"from": MAIL_FROM, "to": [to], "subject": subject, "text": text}
    if reply_to:
        payload["reply_to"] = reply_to
    if pdf_path:
        with open(pdf_path, "rb") as f:
            payload["attachments"] = [{"filename": filename or "Decoda.pdf",
                                       "content": base64.b64encode(f.read()).decode()}]
    r = requests.post("https://api.resend.com/emails",
                      headers={"Authorization": "Bearer " + os.environ["RESEND_API_KEY"]},
                      json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def delivery_text(first):
    return f"""Hi {first},

Your portrait is attached.

It was calculated from the birth details you sent and checked against your chart, line by line, before it left. Under each statement you will see the placements it came from, so when a line is wrong you can see exactly why.

One question, and it is the only thing I will ask you:

Which line was wrong, and what should it have said?

Reply to this email with that, even a single sentence. It is the most useful thing anyone can send me right now, and I read every reply myself.

---

If this was useful, there is a version for two.

Decoda · Two reads two charts side by side: a full portrait for each of you, then what actually happens between you. Where you amplify each other, where you grind, and the pattern that keeps repeating. Partners, but also a parent, a sibling, a co-founder.

It is 99 USD, and it is the only thing Decoda sells:
https://decoda.gumroad.com/l/jpwhra

No need to reply to that part. Only to the question above.

Decoda · trydecoda.com
"""

# ---------------------------------------------------------------- pipeline

def new_order(req):
    oid = secrets.token_urlsafe(12)
    rec = {"id": oid, "status": "queued", "created": datetime.utcnow().isoformat(), "req": req}
    save(oid, rec)
    return oid


def run(oid, compute_ctx):
    """compute_ctx(req) -> (chart, lat, lon, tz, place). Supplied by app.py so the
    geocoder and timezone finder are shared with /glimpse."""
    rec = load(oid)
    req = rec["req"]
    t0 = time.time()
    try:
        chart, place, tz = compute_ctx(req)
        y, mo, d = [int(x) for x in req["date"].split("-")]
        sex = req.get("sex") if req.get("sex") in ("male", "female") else None
        try:
            tl = timeline.build(chart, date(y, mo, d), gender=sex)
        except Exception:
            tl = None
        order = {"name": req["name"], "date": req["date"], "time": req["time"],
                 "tz": tz, "lat": req["_lat"], "lon": req["_lon"], "place": place,
                 "sex": sex, "life_events": (req.get("life_events") or "").strip(),
                 "birth_time_confidence": req.get("birth_time_confidence", "exact")}

        content, msgs, raw, u1 = write_content(chart, tl, order)
        content = fix_dashes(content)
        issues = auto_qc(content, chart)
        usage = [u1]
        if issues:
            content, raw, u2 = repair(msgs, raw, issues)
            content = fix_dashes(content)
            usage.append(u2)
            issues = auto_qc(content, chart)

        import build_v2, check_render
        pdf = _path(oid, "pdf")
        try:
            build_v2.generate(order, content, pdf)
        except ValueError as e:                        # _qc_clocks failed after repair
            content["two_clocks"] = None
            issues.append(f"two_clocks dropped: {e}")
            build_v2.generate(order, content, pdf)
        over = check_render.check(pdf)
        if over:
            issues.append("overflow risk on pages " + ", ".join(str(p) for p, _ in over))

        rec.update(status="review", order=order, content=content, issues=issues,
                   usage=usage, seconds=round(time.time() - t0))
        save(oid, rec)

        link = f"{PUBLIC_BASE}/approve/{oid}?sig={_sig(oid)}"
        qc = "QC: clean." if not issues else "QC FLAGS, read before approving:\n- " + "\n- ".join(issues)
        send_mail(REVIEW_TO, f"[Decoda review] {req['name']}" + (" · FLAGS" if issues else ""),
                  f"""Portrait ready for review.

Reader: {req['name']} <{req['email']}>
Born: {req['date']} {req['time']}, {place}
Sex: {sex or 'not given'} · life events: {'yes' if order['life_events'] else 'no'}

{qc}

Approve and send to the reader:
{link}

Do nothing and nothing is sent. The PDF is attached.
Took {rec['seconds']} s.""",
                  pdf_path=pdf, filename=f"Decoda - {req['name']}.pdf")
    except Exception as e:
        rec.update(status="error", error=str(e), trace=traceback.format_exc()[-3000:])
        save(oid, rec)
        try:
            send_mail(REVIEW_TO, f"[Decoda ERROR] {req.get('name')}",
                      f"Automatic portrait failed. Make it by hand.\n\nRequest:\n{json.dumps({k: v for k, v in req.items() if not k.startswith('_')}, ensure_ascii=False, indent=1)}\n\nError: {e}")
        except Exception:
            pass


def approve(oid):
    rec = load(oid)
    if rec.get("status") == "sent":
        return "already sent"
    if rec.get("status") != "review":
        return f"not ready (status {rec.get('status')})"
    req = rec["req"]
    first = req["name"].split()[0]
    send_mail(req["email"], f"Your Decoda portrait, {first}", delivery_text(first),
              pdf_path=_path(oid, "pdf"), filename=f"Decoda - {req['name']}.pdf",
              reply_to=REVIEW_TO)
    rec["status"] = "sent"
    rec["sent"] = datetime.utcnow().isoformat()
    save(oid, rec)
    return "sent"
