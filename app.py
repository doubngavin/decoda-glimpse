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

app = FastAPI(title="Decoda Glimpse")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to https://trydecoda.com before launch
    allow_methods=["*"], allow_headers=["*"],
)


class GlimpseReq(BaseModel):
    name: str
    date: str       # YYYY-MM-DD
    time: str       # HH:MM (24h)
    city: str
    email: str | None = None


def geocode(city: str):
    """Free OpenStreetMap geocoding. Returns (lat, lon, display_name)."""
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "Decoda/1.0 (decode yourself)"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("city not found")
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]


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
    except Exception:
        raise HTTPException(400, "could not find that birth city, try 'City, Country'")
    dt = datetime(d.year, d.month, d.day, t.hour, t.minute)
    tz = tz_offset(lat, lon, dt)
    chart = engine.compute(d.year, d.month, d.day, t.hour, t.minute, lat, lon, tz)
    out = teaser.make_teaser(chart)
    out["name"] = req.name
    out["place"] = place
    # (email capture: store req.email to your list here)
    return out
