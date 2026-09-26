# -*- coding: utf-8 -*-
"""Decoda · The Glimpse — backend API.
POST /glimpse  { name, date:'YYYY-MM-DD', time:'HH:MM', city }  ->  teaser JSON
Run locally:  uvicorn app:app --reload
"""
from fastapi import FastAPI, HTTPException
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


def tz_offset(lat, lon, dt):
    """Historical UTC offset (hours) at the birth datetime, DST-aware."""
    from timezonefinder import TimezoneFinder
    from zoneinfo import ZoneInfo
    tzname = TimezoneFinder().timezone_at(lat=lat, lng=lon)
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
