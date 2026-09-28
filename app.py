# -*- coding: utf-8 -*-
"""Decoda · The Glimpse — backend API.
POST /glimpse  { name, date:'YYYY-MM-DD', time:'HH:MM', city }  ->  teaser JSON
Run locally:  uvicorn app:app --reload
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse
import os, time as _time, re as _re
import portrait
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import requests
import engine
import teaser
import timeline
import viz

app = FastAPI(title="Decoda Glimpse")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trydecoda.com", "https://www.trydecoda.com"],
    allow_methods=["*"], allow_headers=["*"],
)


class GlimpseReq(BaseModel):
    name: str
    date: str       # YYYY-MM-DD
    time: str       # HH:MM (24h)
    city: str
    email: str | None = None
    # Only used to set the direction of the BaZi luck pillars, which is the one
    # calculation in the whole engine that needs it. Leave it out and that band
    # is omitted; every other part of the timeline still runs.
    sex: str | None = None


class CityNotFound(Exception):
    """The geocoder answered, but knows no such place."""


class GeocoderUnavailable(Exception):
    """The geocoder could not be reached or refused the request."""


# Vietnamese buyers often give a province, not a city (26/09: "An Giang,
# Vietnam" matched a hamlet called An Giang in Gia Lai, 500 km away). Map the
# 63 pre-2025 provinces to their capital so the chart uses the right place.
VN_PROVINCE_CAPITAL = {
    "an giang": "Long Xuyen", "ba ria vung tau": "Vung Tau", "ba ria - vung tau": "Vung Tau", "bac giang": "Bac Giang",
    "bac kan": "Bac Kan", "bac lieu": "Bac Lieu", "bac ninh": "Bac Ninh", "ben tre": "Ben Tre", "binh dinh": "Quy Nhon",
    "binh duong": "Thu Dau Mot", "binh phuoc": "Dong Xoai", "binh thuan": "Phan Thiet", "ca mau": "Ca Mau",
    "can tho": "Can Tho", "cao bang": "Cao Bang", "da nang": "Da Nang", "dak lak": "Buon Ma Thuot",
    "dak nong": "Gia Nghia", "dien bien": "Dien Bien Phu", "dong nai": "Bien Hoa", "dong thap": "Cao Lanh",
    "gia lai": "Pleiku", "ha giang": "Ha Giang", "ha nam": "Phu Ly", "ha noi": "Hanoi", "ha tinh": "Ha Tinh",
    "hai duong": "Hai Duong", "hai phong": "Haiphong", "hau giang": "Vi Thanh", "hoa binh": "Hoa Binh",
    "hung yen": "Hung Yen", "khanh hoa": "Nha Trang", "kien giang": "Rach Gia", "kon tum": "Kon Tum",
    "lai chau": "Lai Chau", "lam dong": "Da Lat", "lang son": "Lang Son", "lao cai": "Lao Cai",
    "long an": "Tan An", "nam dinh": "Nam Dinh", "nghe an": "Vinh", "ninh binh": "Ninh Binh",
    "ninh thuan": "Phan Rang-Thap Cham", "phu tho": "Viet Tri", "phu yen": "Tuy Hoa", "quang binh": "Dong Hoi",
    "quang nam": "Tam Ky", "quang ngai": "Quang Ngai", "quang ninh": "Ha Long", "quang tri": "Dong Ha",
    "soc trang": "Soc Trang", "son la": "Son La", "tay ninh": "Tay Ninh", "thai binh": "Thai Binh",
    "thai nguyen": "Thai Nguyen", "thanh hoa": "Thanh Hoa", "thua thien hue": "Hue", "hue": "Hue",
    "tien giang": "My Tho", "tra vinh": "Tra Vinh", "tuyen quang": "Tuyen Quang", "vinh long": "Vinh Long",
    "vinh phuc": "Vinh Yen", "yen bai": "Yen Bai", "sai gon": "Ho Chi Minh City", "saigon": "Ho Chi Minh City",
    "tp hcm": "Ho Chi Minh City", "tphcm": "Ho Chi Minh City", "hcm": "Ho Chi Minh City", "hcmc": "Ho Chi Minh City",
}
_RANK = {"PPLC": 4, "PPLA": 3, "PPLA2": 2, "PPLA3": 1}


def _plain(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").replace("đ", "d").replace("Đ", "D")
    s = s.encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^(tinh|thanh pho|tp\.?|province|city of)\s+", "", s.strip())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 -]", " ", s)).strip()


def geocode(city: str, detail: bool = False):
    """Geocode a "City, Country" string. Returns (lat, lon, display_name), or
    with detail=True also a confidence flag ("ok" or a warning string).

    Uses Open-Meteo's geocoding API: free, no API key, and explicitly usable
    from a server. Nominatim was used before and silently failed for every
    request, because it blocks generic user agents and cloud provider IPs.
    """
    q = (city or "").strip()
    if not q:
        raise CityNotFound("empty city")

    # Open-Meteo matches on the place name only, so send the first segment as
    # the name and keep the remaining segments to pick the right match.
    parts = [p.strip() for p in q.split(",") if p.strip()]
    name = parts[0]
    hints = [_plain(p) for p in parts[1:]]
    note = "ok"
    vn = any(h in ("vietnam", "viet nam", "vn") for h in hints) or not hints
    cap = VN_PROVINCE_CAPITAL.get(_plain(name)) if vn else None
    if cap and _plain(cap) != _plain(name):
        note = f"'{name}' read as {cap} (province or alias)"
        name, hints = cap, ["vietnam"]

    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 10, "language": "en", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:                      # network, 4xx/5xx, bad JSON
        raise GeocoderUnavailable(str(exc)) from exc

    results = data.get("results") or []
    if not results:
        raise CityNotFound(q)

    def score(item):
        hay = _plain(" ".join(str(item.get(k, "")) for k in ("country", "country_code", "admin1", "admin2")))
        hit = sum(1 for h in hints if h and h in hay)
        pop = item.get("population") or 0
        return (hit, _RANK.get(item.get("feature_code"), 0) + (1 if pop > 5000 else 0), pop)

    best = max(results, key=score)
    if hints and score(best)[0] == 0:
        note = f"no match for '{', '.join(parts[1:])}'; took the most prominent '{name}'"
    elif not (best.get("population") or 0) and best.get("feature_code") == "PPL" and note == "ok":
        note = f"matched a small locality ({best.get('admin1')}); check this is the right place"

    label = ", ".join(
        x for x in (best.get("name"), best.get("admin1"), best.get("country")) if x
    )
    if detail:
        return float(best["latitude"]), float(best["longitude"]), label, note
    return float(best["latitude"]), float(best["longitude"]), label


# Built ONCE at startup. Constructing TimezoneFinder loads its whole polygon
# dataset, which cost about 0.7 s on a laptop and several seconds on the free
# host, and it used to happen on every single request.
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
_TF = TimezoneFinder()


def tz_offset(lat, lon, dt):
    """Historical UTC offset (hours) at the birth datetime, DST-aware."""
    tzname = _TF.timezone_at(lat=lat, lng=lon)
    if not tzname:
        return round(lon / 15.0)  # crude fallback
    off = dt.replace(tzinfo=ZoneInfo(tzname)).utcoffset()
    return off.total_seconds() / 3600.0


@app.get("/")
def health():
    return {"ok": True, "service": "decoda-glimpse"}


@app.post("/glimpse")
def glimpse(req: GlimpseReq):
    try:
        d = datetime.strptime(req.date, "%Y-%m-%d")
        t = datetime.strptime(req.time, "%H:%M")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD and time HH:MM")
    try:
        lat, lon, place = geocode(req.city)
    except CityNotFound:
        # The user can fix this one.
        raise HTTPException(
            400,
            "We could not find that birth city. Try \"City, Country\", for example \"Lyon, France\".",
        )
    except GeocoderUnavailable:
        # Not the user's fault: never report a service outage as a bad city.
        raise HTTPException(
            503,
            "The location service is temporarily unavailable. Please try again in a moment.",
        )
    dt = datetime(d.year, d.month, d.day, t.hour, t.minute)
    tz = tz_offset(lat, lon, dt)
    chart = engine.compute(d.year, d.month, d.day, t.hour, t.minute, lat, lon, tz)
    out = teaser.make_teaser(chart)
    out["name"] = req.name
    out["place"] = place

    # The computed life timeline. Everything below is derived from the birth
    # data alone, which is why it is free: it costs nothing to produce and
    # every line of it can be checked by the reader against their own past.
    try:
        sex = req.sex if req.sex in ("male", "female") else None
        tl = timeline.build(chart, d.date(), gender=sex)
        out["timeline"] = {
            "age": tl["age"],
            "now": tl["bands"]["now"],
            "years": tl["years"],
            "next_transits": tl["next_transits"],
            "luck_pillars": tl["luck_pillars"],
        }
        out["timeline_svg"] = viz.life_arc(tl)
        # The version that gets posted in public: ages only, no birth date,
        # no calendar years. See viz.life_arc(share=True).
        out["timeline_share_svg"] = viz.life_arc(tl, share=True)
    except Exception as exc:
        # A timeline failure must never take the reading down with it. Say so
        # rather than returning a half page that looks like nothing went wrong.
        out["timeline"] = None
        out["timeline_error"] = str(exc)

    # (email capture: store req.email to your list here)
    return out


# ================================================================ portrait (Self)
# Paid full portrait (Gumroad, 19 USD since 2026-09-27), written by the Claude
# API, QC'd by code, approved by a human with one click, then emailed.
# See portrait.py.
#
# Two ways in:
#   POST /gumroad?k=GUMROAD_KEY   Gumroad Ping after a sale (the normal path)
#   POST /portrait?k=...          manual: JSON body, key = GUMROAD_KEY or
#                                 APPROVE_SECRET. Open to the public only if
#                                 PORTRAIT_OPEN=1 (the old free intake).

class PortraitReq(BaseModel):
    name: str
    email: str
    date: str
    time: str
    city: str
    sex: str | None = None
    life_events: str | None = None
    website: str | None = None        # honeypot: humans never fill it
    source: str | None = None         # ops page: etsy / gumroad / gift / correction / other
    order_ref: str | None = None      # ops page: Etsy or Gumroad order number


_HITS: dict = {}
DAILY_CAP = int(os.environ.get("PORTRAIT_DAILY_CAP", "25"))   # guards API spend


def _limited(ip):
    now = _time.time()
    day = [t for t in _HITS.get("_all", []) if now - t < 86400]
    mine = [t for t in _HITS.get(ip, []) if now - t < 3600]
    if len(day) >= DAILY_CAP or len(mine) >= 3:
        return True
    _HITS["_all"] = day + [now]
    _HITS[ip] = mine + [now]
    return False


def _key_ok(k):
    import hmac as _hmac
    for name in ("GUMROAD_KEY", "APPROVE_SECRET"):
        v = os.environ.get(name)
        if v and k and _hmac.compare_digest(v, k):
            return True
    return False


def _compute_ctx(r):
    y, mo, dd = [int(x) for x in r["date"].split("-")]
    hh, mm = [int(x) for x in r["time"].split(":")]
    return engine.compute(y, mo, dd, hh, mm, r["_lat"], r["_lon"], r["_tz"]), r["_place"], r["_tz"]


@app.post("/portrait")
def portrait_request(req: PortraitReq, bg: BackgroundTasks, request: Request, k: str = ""):
    if req.website:
        return {"ok": True}
    if os.environ.get("PORTRAIT_OPEN") != "1" and not _key_ok(k):
        raise HTTPException(403, "The portrait is ordered at https://decoda.gumroad.com/l/gzcbtz")
    if not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", req.email.strip()):
        raise HTTPException(400, "Please check your email address.")
    try:
        d = datetime.strptime(req.date, "%Y-%m-%d")
        t = datetime.strptime(req.time, "%H:%M")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD and time HH:MM")
    if _limited(request.client.host if request.client else "?"):
        raise HTTPException(429, "Too many requests right now. Please try again later.")
    try:
        lat, lon, place, geo_note = geocode(req.city, detail=True)
    except CityNotFound:
        raise HTTPException(400, "We could not find that birth city. Try \"City, Country\", for example \"Lyon, France\".")
    except GeocoderUnavailable:
        raise HTTPException(503, "The location service is temporarily unavailable. Please try again in a moment.")
    tz = tz_offset(lat, lon, datetime(d.year, d.month, d.day, t.hour, t.minute))
    data = req.model_dump(exclude={"website", "source", "order_ref"})
    if geo_note != "ok":
        data["_flags"] = [f"birth place: {geo_note} -> {place}"]
    data.update(name=req.name.strip()[:80], email=req.email.strip(),
                life_events=(req.life_events or "")[:1500],
                _lat=lat, _lon=lon, _place=place, _tz=tz)
    if _key_ok(k):
        src = _re.sub(r"[^a-z]", "", (req.source or "").lower())[:20]
        data["_source"] = "manual" + (":" + src if src else "")
        if req.order_ref:
            data["_sale_id"] = _re.sub(r"[^A-Za-z0-9#_-]", "", req.order_ref)[:40]
    oid = portrait.new_order(data)
    bg.add_task(portrait.run, oid, _compute_ctx)
    return {"ok": True, "place": place, "id": oid, "place_note": geo_note}


@app.get("/geocode")
def geocode_preview(city: str, request: Request):
    """Read-only place check for the ops page: what would this city resolve to?"""
    ip = request.client.host if request.client else "?"
    now = _time.time()
    hits = [t for t in _HITS.get("geo:" + ip, []) if now - t < 60]
    if len(hits) >= 20:
        raise HTTPException(429, "slow down")
    _HITS["geo:" + ip] = hits + [now]
    try:
        lat, lon, place, note = geocode(city, detail=True)
    except CityNotFound:
        raise HTTPException(404, "not found")
    except GeocoderUnavailable:
        raise HTTPException(503, "geocoder unavailable")
    return {"place": place, "lat": round(lat, 3), "lon": round(lon, 3), "note": note}


# ================================================================ Gumroad Ping
# Gumroad POSTs application/x-www-form-urlencoded after every sale to the Ping
# URL set in Gumroad Settings > Advanced:
#     https://decoda-glimpse.onrender.com/gumroad?k=<GUMROAD_KEY>
# Gumroad does not sign pings, so the key in the URL is the only guard.
# Birth details come from the checkout custom fields. Their labels are matched
# loosely (Gumroad sends them either top level or as custom_fields[Label]).
# Anything that cannot be read safely is mailed to REVIEW_TO instead of guessed.
# The endpoint always answers 200 to a valid key, so Gumroad never retries a
# sale we already hold.

import re
import hmac as _hmac_g
import calendar as _cal
from datetime import date

GUMROAD_SELF = [x.strip() for x in os.environ.get("GUMROAD_SELF_PERMALINKS", "gzcbtz").split(",") if x.strip()]

_GR_STD = {
    "seller_id", "product_id", "product_name", "permalink", "product_permalink", "short_product_id",
    "email", "price", "gumroad_fee", "currency", "quantity", "discover_fee_charged", "can_contact",
    "referrer", "order_number", "sale_id", "sale_timestamp", "purchaser_id", "subscription_id",
    "variants", "offer_code", "test", "ip_country", "is_gift_receiver_purchase", "refunded",
    "disputed", "dispute_won", "resource_name", "full_name", "license_key", "is_recurring_charge",
    "is_preorder_authorization", "shipping_information", "affiliate", "affiliate_credit_amount_cents",
    "gift_price", "recurrence", "url_params", "card", "k",
}

_MONTHS = {m.lower(): i for i, m in enumerate(_cal.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(_cal.month_abbr) if m})
_MONTHS["sept"] = 9


def _gr_fields(f: dict) -> dict:
    """label (lowercased) -> value, for checkout custom fields only."""
    out = {}
    for key, val in f.items():
        val = (val or "").strip()
        if not val:
            continue
        m = re.match(r"custom_fields\[(.+)\]$", key)
        if m:
            out[m.group(1).strip().lower()] = val
        elif key not in _GR_STD and not key.startswith(("variants[", "url_params[", "card[", "shipping_information[")):
            out[key.strip().lower()] = val
    return out


def _gr_pick(fields, want, avoid=()):
    for label, val in fields.items():
        if re.search(want, label) and not (avoid and re.search(avoid, label)):
            return label, val
    return None, None


def _year(y):
    y = int(y)
    if y < 100:
        y += 1900 if y > datetime.utcnow().year % 100 else 2000
    return y


def _parse_birth_date(raw: str, label: str = ""):
    """-> ('YYYY-MM-DD', flag or None). Raises ValueError if unreadable.
    Day/month order: DD/MM unless the label says MM/DD or a part is > 12."""
    s = raw.strip().lower()
    flag = None
    m = re.fullmatch(r"(\d{4})[-/. ](\d{1,2})[-/. ](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(\d{1,2})\s*[-/. ]\s*(\d{1,2})\s*[-/. ]\s*(\d{2,4})", s)
        if m:
            a, b, y = int(m.group(1)), int(m.group(2)), _year(m.group(3))
            us = bool(re.search(r"mm\s*/\s*dd", label.lower()))
            if a > 12:
                d, mo = a, b
            elif b > 12:
                mo, d = a, b
                if not us:
                    flag = f"birth date '{raw}' read as month/day because {b} > 12"
            elif us:
                mo, d = a, b
            else:
                d, mo = a, b
                if a != b and not re.search(r"dd\s*/\s*mm", label.lower()):
                    flag = f"birth date '{raw}' is ambiguous, read as DAY/MONTH = {d:02d}/{mo:02d}. Confirm with the buyer if unsure."
        else:
            words = re.findall(r"[a-z]+", s)
            nums = [int(x) for x in re.findall(r"\d+", s)]
            mo = next((_MONTHS[w] for w in words if w in _MONTHS), None)
            yrs = [n for n in nums if n > 31]
            days = [n for n in nums if 1 <= n <= 31]
            if not (mo and yrs and days):
                raise ValueError(f"cannot read birth date '{raw}'")
            y, d = _year(yrs[0]), days[0]
    dt = date(y, mo, d)                       # raises on 31/02 etc.
    if not (1900 <= dt.year and dt <= datetime.utcnow().date()):
        raise ValueError(f"birth date '{raw}' out of range")
    return dt.isoformat(), flag


def _parse_birth_time(raw: str, label: str = ""):
    """-> ('HH:MM', flag or None). Raises ValueError if unreadable or unknown."""
    s = raw.strip().lower().replace(" ", "")
    if re.search(r"unknown|dontknow|don'tknow|notsure|\?|khongbiet|n/a", s):
        raise ValueError(f"birth time not known ('{raw}')")
    ampm = None
    m = re.search(r"(a\.?m\.?|p\.?m\.?|sa|sáng|chiều|chieu|tối|toi)$", s)
    if m:
        tag = m.group(1)
        ampm = "am" if tag.startswith(("a", "s")) else "pm"
        s = s[:m.start()]
    m = re.fullmatch(r"(\d{1,2})[:.h](\d{2})(?::\d{2})?", s) or re.fullmatch(r"(\d{2})(\d{2})", s) or re.fullmatch(r"(\d{1,2})()", s)
    if not m:
        raise ValueError(f"cannot read birth time '{raw}'")
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if ampm:
        if not 1 <= h <= 12:
            raise ValueError(f"birth time '{raw}' is not a valid 12-hour time")
        h = (h % 12) + (12 if ampm == "pm" else 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError(f"birth time '{raw}' out of range")
    flag = None
    if not ampm and 1 <= h <= 11 and "24" not in label and len(m.group(1)) == 1:
        flag = f"birth time '{raw}' read as 24-hour ({h:02d}:{mi:02d}, morning). Check it is not PM."
    return f"{h:02d}:{mi:02d}", flag


def _gr_action_mail(subject, why, f, fields):
    body = f"""A Gumroad sale needs a hand. Nothing was started automatically.

Why: {why}

Buyer: {f.get('full_name') or '-'} <{f.get('email')}>
Product: {f.get('product_name')} ({f.get('permalink') or f.get('product_permalink')})
Sale: {f.get('sale_id')} · {f.get('price')} {f.get('currency')} · test={f.get('test', 'false')}

Custom fields as received:
""" + "\n".join(f"  {k}: {v}" for k, v in fields.items()) + """

Once the details are clear, start it by hand at https://trydecoda.com/ops"""
    try:
        portrait.send_mail(portrait.REVIEW_TO, subject, body, reply_to=f.get("email") or None)
    except Exception:
        pass


@app.post("/gumroad")
async def gumroad_ping(request: Request, bg: BackgroundTasks, k: str = "", run: str = ""):
    key = os.environ.get("GUMROAD_KEY")
    if not key or not k or not _hmac_g.compare_digest(key, k):
        raise HTTPException(403, "bad key")
    form = await request.form()
    f = {name: str(v) for name, v in form.multi_items()}
    fields = _gr_fields(f)
    sale = (f.get("sale_id") or f.get("order_number") or "").strip()
    who = f.get("full_name") or f.get("email") or "?"

    if f.get("refunded") == "true":
        return {"ok": True, "skipped": "refund"}

    prod = " ".join([f.get("permalink", ""), f.get("product_permalink", ""), f.get("short_product_id", "")])
    if not any(p in prod for p in GUMROAD_SELF):
        _gr_action_mail(f"[Decoda sale] {f.get('product_name')} · {who}",
                        "Not a Self order (e.g. Two). Fulfil it the usual way.", f, fields)
        return {"ok": True, "skipped": "not self"}

    is_test = f.get("test") == "true"
    if is_test and run != "1":
        _gr_action_mail(f"[Decoda ping test] {who}",
                        "Test ping from Gumroad. Shown so the field labels can be checked. Add &run=1 to the Ping URL to run a test sale end to end.",
                        f, fields)
        return {"ok": True, "skipped": "test"}

    marker = os.path.join(portrait.DATA_DIR, f"sale-{re.sub(r'[^A-Za-z0-9_=-]', '', sale)}") if sale else None
    if marker and os.path.exists(marker):
        return {"ok": True, "skipped": "duplicate"}

    flags = ["TEST sale from Gumroad"] if is_test else []
    try:
        dl, dv = _gr_pick(fields, r"date|dob|birthday|ngày", r"time|giờ")
        tl_, tv = _gr_pick(fields, r"time|giờ|hour", r"date|ngày")
        if not dv:                              # one field holding both
            dl, dv = _gr_pick(fields, r"birth|sinh")
            if dv and re.search(r"\d{1,2}[:h]\d{2}", dv) and not tv:
                tv = re.search(r"\d{1,2}[:h]\d{2}\s*(?:am|pm)?", dv, re.I).group(0)
                dv = dv.replace(tv, "").strip(" ,@")
                tl_ = dl
        cl, cv = _gr_pick(fields, r"city|place|location|where|born in|nơi", r"date|time")
        nl, nv = _gr_pick(fields, r"name|tên", r"city|place|user")
        _, sv = _gr_pick(fields, r"sex|gender|giới")
        _, lv = _gr_pick(fields, r"moment|event|life|changed")
        if not dv or not tv or not cv:
            raise ValueError("missing " + ", ".join(n for n, v in (("birth date", dv), ("birth time", tv), ("birth city", cv)) if not v))
        bdate, fl = _parse_birth_date(dv, dl or "")
        if fl: flags.append(fl)
        btime, fl = _parse_birth_time(tv, tl_ or "")
        if fl: flags.append(fl)
        email = (f.get("email") or "").strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("no valid buyer email")
        name = (nv or f.get("full_name") or email.split("@")[0]).strip()[:80]
        sx = (sv or "").strip().lower()
        sex = "female" if sx.startswith(("f", "w", "nữ", "nu ")) or sx == "nu" else ("male" if sx.startswith(("m", "nam")) else None)
        try:
            lat, lon, place, geo_note = geocode(cv, detail=True)
            if geo_note != "ok":
                flags.append(f"birth place: {geo_note} -> {place}")
        except CityNotFound:
            raise ValueError(f"birth city '{cv}' not found by the geocoder")
        except GeocoderUnavailable:
            raise ValueError("geocoder unavailable right now; retry by hand")
        d = datetime.strptime(bdate, "%Y-%m-%d"); t = datetime.strptime(btime, "%H:%M")
        tz = tz_offset(lat, lon, datetime(d.year, d.month, d.day, t.hour, t.minute))
    except Exception as e:
        _gr_action_mail(f"[Decoda ACTION] Gumroad sale needs details · {who}", str(e), f, fields)
        if marker:
            open(marker, "w").write("action")
        return {"ok": True, "queued": False}

    data = dict(name=name, email=email, date=bdate, time=btime, city=cv, sex=sex,
                life_events=(lv or "")[:1500], _lat=lat, _lon=lon, _place=place, _tz=tz,
                _source="gumroad", _sale_id=sale, _flags=flags,
                _gumroad={k2: v2 for k2, v2 in fields.items()})
    oid = portrait.new_order(data)
    if marker:
        open(marker, "w").write(oid)
    bg.add_task(portrait.run, oid, _compute_ctx)
    return {"ok": True, "queued": True}


_PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Decoda review</title><body style="font-family:system-ui;background:#0B0B0B;color:#F2EFE6;max-width:520px;margin:12vh auto;padding:0 24px">{}</body>"""


@app.get("/approve/{oid}", response_class=HTMLResponse)
def approve_page(oid: str, sig: str = ""):
    # GET never sends: mail scanners open links. Sending needs the button (POST).
    if not portrait.check_sig(oid, sig):
        raise HTTPException(403, "bad link")
    try:
        rec = portrait.load(oid)
    except FileNotFoundError:
        return _PAGE.format("<h2>Not found</h2><p>This order is no longer on the server (it restarts). Send the PDF from the review email by hand.</p>")
    r = rec["req"]
    flags = "".join(f"<li>{i}</li>" for i in rec.get("issues", []))
    flags = f"<p style='color:#e8a33d'>QC flags:</p><ul>{flags}</ul>" if flags else "<p>QC: clean.</p>"
    return _PAGE.format(f"""<h2>Send to {r['name']}?</h2><p>{r['email']} · status: {rec.get('status')}</p>{flags}
<form method=post><input type=hidden name=sig value="{sig}"><button style="font-size:18px;padding:12px 28px;margin-top:16px">Approve and send</button></form>""")


@app.post("/approve/{oid}", response_class=HTMLResponse)
def approve_send(oid: str, sig: str = Form("")):
    if not portrait.check_sig(oid, sig):
        raise HTTPException(403, "bad link")
    try:
        result = portrait.approve(oid)
    except FileNotFoundError:
        result = "order no longer on the server; send the PDF by hand"
    except Exception as e:
        result = f"error: {e}"
    return _PAGE.format(f"<h2>{result}</h2>")


@app.get("/health/portrait")
def health_portrait():
    """Can this host render PDFs and is the pipeline configured? No secrets shown."""
    out = {k: bool(os.environ.get(k)) for k in ("ANTHROPIC_API_KEY", "RESEND_API_KEY", "APPROVE_SECRET", "GUMROAD_KEY")}
    out["portrait_open"] = os.environ.get("PORTRAIT_OPEN") == "1"
    try:
        from weasyprint import HTML
        HTML(string="<p>ok</p>").write_pdf()
        out["weasyprint"] = True
    except Exception as e:
        out["weasyprint"] = f"no: {str(e)[:200]}"
    out["model"] = portrait.MODEL
    return out
