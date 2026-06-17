# -*- coding: utf-8 -*-
"""Decoda compute engine: Western astrology + BaZi + Human Design.
Deterministic. Verified against a known chart (Virgo/Gemini/Cancer, Yi Wood, MG 2/4 Sacral)."""
import swisseph as swe
import sxtwl
from datetime import datetime, timedelta

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio",
         "Sagittarius","Capricorn","Aquarius","Pisces"]

def _sign(L): return SIGNS[int(L // 30)]

# --- Human Design gate wheel (Gate 41 starts at 302 deg) ---
RING = [41,19,13,49,30,55,37,63,22,36,25,17,21,51,42,3,27,24,2,23,8,20,16,35,45,12,15,52,
        39,53,62,56,31,33,7,4,29,59,40,64,47,6,46,18,48,57,32,50,28,44,1,43,14,34,9,5,26,
        11,10,58,38,54,61,60]

def _gate_line(L):
    o = (L - 302) % 360
    i = int(o // 5.625)
    return RING[i], int((o - i * 5.625) // 0.9375) + 1

CENTER = {}
for g in [64,61,63]: CENTER[g] = "Head"
for g in [47,24,4,17,43,11]: CENTER[g] = "Ajna"
for g in [62,23,56,35,12,45,33,8,31,20,16]: CENTER[g] = "Throat"
for g in [1,13,25,46,2,15,10,7]: CENTER[g] = "G"
for g in [21,40,26,51]: CENTER[g] = "Heart"
for g in [5,14,29,59,9,3,42,27,34]: CENTER[g] = "Sacral"
for g in [48,57,44,50,32,28,18]: CENTER[g] = "Spleen"
for g in [6,37,30,55,49,22,36]: CENTER[g] = "SolarPlexus"
for g in [53,60,52,19,39,41,58,38,54]: CENTER[g] = "Root"

CHANNELS = [(1,8),(2,14),(3,60),(4,63),(5,15),(6,59),(7,31),(9,52),(10,20),(10,34),(10,57),
    (11,56),(12,22),(13,33),(16,48),(17,62),(18,58),(19,49),(20,34),(20,57),(21,45),(23,43),
    (24,61),(25,51),(26,44),(27,50),(28,38),(29,46),(30,41),(32,54),(34,57),(35,36),(37,40),
    (39,55),(42,53),(47,64)]

_PL = {"Sun":swe.SUN,"Earth":"E","Moon":swe.MOON,"NorthNode":swe.MEAN_NODE,"SouthNode":"S",
       "Mercury":swe.MERCURY,"Venus":swe.VENUS,"Mars":swe.MARS,"Jupiter":swe.JUPITER,
       "Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}

_GAN = ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"]
_GAN_EL = ["Wood","Wood","Fire","Fire","Earth","Earth","Metal","Metal","Water","Water"]
_GAN_YIN = ["Yang Wood","Yin Wood","Yang Fire","Yin Fire","Yang Earth","Yin Earth",
            "Yang Metal","Yin Metal","Yang Water","Yin Water"]
_ZHI_EL = ["Water","Earth","Wood","Wood","Earth","Fire","Fire","Earth","Metal","Metal","Earth","Water"]


def _activations(jd):
    out = {}
    for name, p in _PL.items():
        if p == "E":
            L = (swe.calc_ut(jd, swe.SUN)[0][0] + 180) % 360
        elif p == "S":
            L = (swe.calc_ut(jd, swe.MEAN_NODE)[0][0] + 180) % 360
        else:
            L = swe.calc_ut(jd, p)[0][0]
        out[name] = _gate_line(L)
    return out


def compute(year, month, day, hour, minute, lat, lon, tz):
    """tz = hours offset from UTC at birth (e.g. 7 for Vietnam)."""
    ut = datetime(year, month, day, hour, minute) - timedelta(hours=tz)
    jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60.0)

    # Western astrology
    sun = swe.calc_ut(jd, swe.SUN)[0][0]
    moon = swe.calc_ut(jd, swe.MOON)[0][0]
    merc = swe.calc_ut(jd, swe.MERCURY)[0][0]
    venus = swe.calc_ut(jd, swe.VENUS)[0][0]
    mars = swe.calc_ut(jd, swe.MARS)[0][0]
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc = ascmc[0]
    astro = {"sun": _sign(sun), "moon": _sign(moon), "rising": _sign(asc),
             "mercury": _sign(merc), "venus": _sign(venus), "mars": _sign(mars)}

    # BaZi
    d = sxtwl.fromSolar(year, month, day)
    yp, mp, dp = d.getYearGZ(), d.getMonthGZ(), d.getDayGZ()
    hz = (hour + 1) // 2 % 12
    ht = (dp.tg * 2 + hz) % 10
    elems = {"Wood":0,"Fire":0,"Earth":0,"Metal":0,"Water":0}
    for t, z in [(yp.tg,yp.dz),(mp.tg,mp.dz),(dp.tg,dp.dz),(ht,hz)]:
        elems[_GAN_EL[t]] += 1
        elems[_ZHI_EL[z]] += 1
    dominant = max(elems, key=elems.get)
    bazi = {"day_master": _GAN_YIN[dp.tg], "day_master_element": _GAN_EL[dp.tg],
            "elements": elems, "dominant": dominant}

    # Human Design
    tgt = (sun - 88) % 360
    lo, hi = jd - 100, jd - 80
    for _ in range(60):
        m = (lo + hi) / 2
        s = swe.calc_ut(m, swe.SUN)[0][0]
        diff = (s - tgt + 180) % 360 - 180
        lo, hi = (m, hi) if diff > 0 else (lo, m)
    djd = (lo + hi) / 2
    pers, des = _activations(jd), _activations(djd)
    active = set(v[0] for v in pers.values()) | set(v[0] for v in des.values())
    defined, ach = set(), []
    for a, b in CHANNELS:
        if a in active and b in active:
            ach.append((a, b)); defined.add(CENTER[a]); defined.add(CENTER[b])
    sacral = "Sacral" in defined
    throat = "Throat" in defined
    motors = {"Sacral","Heart","SolarPlexus","Root"}
    m2t = any((CENTER[a]=="Throat" and CENTER[b] in motors) or
              (CENTER[b]=="Throat" and CENTER[a] in motors) for a, b in ach)
    if not defined:
        htype = "Reflector"
    elif sacral:
        htype = "Manifesting Generator" if m2t else "Generator"
    elif throat and m2t:
        htype = "Manifestor"
    else:
        htype = "Projector"
    if "SolarPlexus" in defined:
        authority = "Emotional"
    elif sacral:
        authority = "Sacral"
    elif "Spleen" in defined:
        authority = "Splenic"
    else:
        authority = "Other"
    all_centers = {"Head","Ajna","Throat","G","Heart","Sacral","Spleen","SolarPlexus","Root"}
    hd = {"type": htype, "authority": authority,
          "profile": f"{pers['Sun'][1]}/{des['Sun'][1]}",
          "defined": sorted(defined), "open": sorted(all_centers - defined)}

    return {"astro": astro, "bazi": bazi, "hd": hd}
