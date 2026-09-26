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


def geocode(city: str):
    """Geocode a "City, Country" string. Returns (lat, lon, display_name).

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
    hints = [p.lower() for p in parts[1:]]

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

    best = results[0]
    if hints:
        for item in results:
            haystack = " ".join(
                str(item.get(k, "")) for k in ("country", "country_code", "admin1", "admin2")
            ).lower()
            if any(h in haystack for h in hints):
                best = item
                break

    label = ", ".join(
        x for x in (best.get("name"), best.get("admin1"), best.get("country")) if x
    )
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
# Free full portrait, written by the Claude API, QC'd by code, approved by a
# human with one click, then emailed. See portrait.py.

class PortraitReq(BaseModel):
    name: str
    email: str
    date: str
    time: str
    city: str
    sex: str | None = None
    life_events: str | None = None
    website: str | None = None        # honeypot: humans never fill it


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


@app.post("/portrait")
def portrait_request(req: PortraitReq, bg: BackgroundTasks, request: Request):
    if req.website:
        return {"ok": True}
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
        lat, lon, place = geocode(req.city)
    except CityNotFound:
        raise HTTPException(400, "We could not find that birth city. Try \"City, Country\", for example \"Lyon, France\".")
    except GeocoderUnavailable:
        raise HTTPException(503, "The location service is temporarily unavailable. Please try again in a moment.")
    tz = tz_offset(lat, lon, datetime(d.year, d.month, d.day, t.hour, t.minute))
    data = req.model_dump(exclude={"website"})
    data.update(name=req.name.strip()[:80], email=req.email.strip(),
                life_events=(req.life_events or "")[:1500],
                _lat=lat, _lon=lon, _place=place, _tz=tz)
    oid = portrait.new_order(data)

    def ctx(r):
        y, mo, dd = [int(x) for x in r["date"].split("-")]
        hh, mm = [int(x) for x in r["time"].split(":")]
        return engine.compute(y, mo, dd, hh, mm, r["_lat"], r["_lon"], r["_tz"]), r["_place"], r["_tz"]

    bg.add_task(portrait.run, oid, ctx)
    return {"ok": True, "place": place}


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
