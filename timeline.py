# -*- coding: utf-8 -*-
"""Decoda · life timeline layer.

Everything here is COMPUTED from birth data alone. Nothing in this module makes
a judgement about the person, which is exactly why all of it can be given away
free: the marginal cost is zero and every line is falsifiable.

The judgement layers (Herman's phases, Jung's stages of the work, where the
person actually stands) deliberately live outside this file. They cannot be
derived from a birth chart and must not be faked here.

Outputs are English, because the product is English.
"""
from datetime import date, timedelta
import swisseph as swe
import sxtwl

import engine

# ---------------------------------------------------------------- constants

# Same naming engine.py emits, so a pillar read back from a chart matches.
GAN = ["Yang Wood", "Yin Wood", "Yang Fire", "Yin Fire", "Yang Earth",
       "Yin Earth", "Yang Metal", "Yin Metal", "Yang Water", "Yin Water"]
ZHI = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei",
       "Shen", "You", "Xu", "Hai"]
ZHI_ANIMAL = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
              "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
GAN_EL = ["Wood", "Wood", "Fire", "Fire", "Earth",
          "Earth", "Metal", "Metal", "Water", "Water"]
ZHI_EL = ["Water", "Earth", "Wood", "Wood", "Earth", "Fire",
          "Fire", "Earth", "Metal", "Metal", "Earth", "Water"]

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# What each house is about, kept to one plain noun phrase. Whole sign houses.
HOUSE_TOPIC = {
    1: "you, your body, how you show up",
    2: "what you own and what you are worth",
    3: "daily talk, learning, siblings, short trips",
    4: "home, family, the private base",
    5: "play, creation, children, what you make for joy",
    6: "the body, daily work, service, routine",
    7: "other people: partners, opponents, contracts",
    8: "fear, what is hidden, other people's resources, change",
    9: "meaning, belief, distance, study",
    10: "public role, career, being seen",
    11: "friends, networks, the future you are aiming at",
    12: "what is undone, solitude, what runs underneath",
}

# Age-based frameworks. These are published models, not chart output, so they
# are the same for everyone. They are on the chart to give the reader a frame,
# not to tell them who they are.
JUNG_STAGES = [
    (0, 18, "Childhood"),
    (18, 35, "Youth, the morning: build an ego, find a place"),
    (35, 60, "Middle life, the afternoon: turn inward"),
    (60, 71, "Old age"),
]
LEVINSON_STAGES = [
    (0, 17, "Pre-adulthood"), (17, 22, "Early adult transition"),
    (22, 28, "Entering the adult world"), (28, 33, "Age 30 transition"),
    (33, 40, "Settling down"), (40, 45, "Mid-life transition"),
    (45, 50, "Entering middle adulthood"), (50, 55, "Age 50 transition"),
    (55, 60, "Culmination of middle adulthood"),
    (60, 65, "Late adult transition"), (65, 71, "Late adulthood"),
]
ERIKSON_STAGES = [
    (0, 12, "Childhood stages"),
    (12, 18, "Identity vs role confusion"),
    (18, 40, "Intimacy vs isolation"),
    (40, 65, "Generativity vs stagnation"),
    (65, 71, "Integrity vs despair"),
]

# Transit cycles worth naming. (body, aspect degrees, label, weight)
# Weight drives how loudly the marker is drawn: 2 = once in a lifetime.
CYCLES = [
    (swe.SATURN,  0,   "Saturn return", 2),
    (swe.SATURN,  90,  "Saturn square Saturn", 1),
    (swe.SATURN,  180, "Saturn opposition Saturn", 1),
    (swe.SATURN,  270, "Saturn square Saturn", 1),
    (swe.URANUS,  180, "Uranus opposition Uranus", 2),
    (swe.NEPTUNE, 90,  "Neptune square Neptune", 2),
    (swe.PLUTO,   90,  "Pluto square Pluto", 2),
]
NATAL_KEY = {swe.SATURN: "Saturn", swe.URANUS: "Uranus",
             swe.NEPTUNE: "Neptune", swe.PLUTO: "Pluto",
             swe.JUPITER: "Jupiter"}


# ---------------------------------------------------------------- helpers

def _reduce(n):
    """Digit sum down to 1..9. Master numbers are reduced too, which is what
    the reference table does."""
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def _age_on(birth, when):
    """Whole years completed, by birthday."""
    return when.year - birth.year - ((when.month, when.day) < (birth.month, birth.day))


def _band(stages, age):
    for lo, hi, name in stages:
        if lo <= age < hi:
            return name
    return stages[-1][2]


def _jd_to_date(jd):
    y, m, d, _ = swe.revjul(jd)
    return date(y, m, d)


# ---------------------------------------------------------------- pieces

def personal_year(birth, year):
    """Numerology personal year: reduce(month+day) + reduce(year), reduced."""
    return _reduce(_reduce(birth.month + birth.day) + _reduce(year))


def profection(chart, birth, year):
    """Annual profection, whole sign. Age 0 sits in the 1st house and it walks
    one house per birthday, so the cycle closes every 12 years."""
    ref = date(year, birth.month, birth.day)
    age = _age_on(birth, ref)
    house = (age % 12) + 1
    rising_idx = SIGNS.index(chart["astro"]["rising"])
    sign = SIGNS[(rising_idx + house - 1) % 12]
    return {"year": year, "age": age, "house": house,
            "sign": sign, "topic": HOUSE_TOPIC[house]}


def bazi_year(chart, year):
    """The year pillar that rules a given solar year, and how it meets the day
    pillar. March 1 is safely past the Feb 4 boundary."""
    gz = sxtwl.fromSolar(year, 3, 1).getYearGZ()
    day = chart["bazi"]["pillars"]["day"]
    day_zhi = ZHI.index(day["zhi"]) if day["zhi"] in ZHI else None
    rel = None
    if day_zhi is not None:
        rel = _zhi_relation(gz.dz, day_zhi)
    same_pillar = (day.get("gan") == GAN[gz.tg] and day.get("zhi") == ZHI[gz.dz])
    return {"year": year, "gan": GAN[gz.tg], "zhi": ZHI[gz.dz],
            "animal": ZHI_ANIMAL[gz.dz], "element": GAN_EL[gz.tg],
            "branch_element": ZHI_EL[gz.dz],
            "relation_to_day": "same pillar as your day" if same_pillar else rel}


_LIUHE = {frozenset(p) for p in [(0, 1), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)]}
_CHONG = {frozenset(p) for p in [(0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11)]}
_HAI = {frozenset(p) for p in [(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)]}
_SANHE = [{8, 0, 4}, {11, 3, 7}, {2, 6, 10}, {5, 9, 1}]


def _zhi_relation(a, b):
    if a == b:
        return "repeats your day branch"
    key = frozenset((a, b))
    if key in _LIUHE:
        return "six harmony with your day branch"
    if any(a in g and b in g for g in _SANHE):
        return "part of a triad with your day branch"
    if key in _CHONG:
        return "clashes with your day branch"
    if key in _HAI:
        return "harm with your day branch"
    return None


# Sampling step per body. A step only has to be fine enough to never skip a
# retrograde loop: Saturn's is about 7 degrees over 140 days, the outer three
# are far slower, so a coarser step there costs nothing and saves most of the
# scan time.
STEP_DAYS = {swe.SATURN: 12, swe.URANUS: 25, swe.NEPTUNE: 30, swe.PLUTO: 30}


def transits(chart, birth, span_years=70, step_days=None):
    """Dates when a slow planet meets its own natal position at a given angle.

    Outer planets go retrograde, so one contact usually happens two or three
    times across a year. They are grouped and reported as one event with its
    exact passes kept, because that is what a person actually lives through.
    """
    lon = chart["astro"]["lon"]
    jd0 = chart["astro"]["jd"]
    jd1 = jd0 + span_years * 365.25
    out = []

    for body, angle, label, weight in CYCLES:
        step = step_days or STEP_DAYS.get(body, 12)
        natal = lon[NATAL_KEY[body]]
        target = (natal + angle) % 360
        hits, prev = [], None
        jd = jd0
        while jd < jd1:
            p = swe.calc_ut(jd, body)[0][0]
            d = ((p - target + 180) % 360) - 180
            if prev is not None and prev[1] * d < 0 and abs(d - prev[1]) < 180:
                a, b = prev[0], jd
                for _ in range(40):                     # bisect to the day
                    m = (a + b) / 2
                    pm = swe.calc_ut(m, body)[0][0]
                    dm = ((pm - target + 180) % 360) - 180
                    a, b = (m, b) if dm * prev[1] > 0 else (a, m)
                hits.append((a + b) / 2)
            prev = (jd, d)
            jd += step

        for group in _group(hits, 500):                 # retrograde passes
            mid = group[len(group) // 2]
            when = _jd_to_date(mid)
            if _age_on(birth, when) < 1:      # planet has not left its natal
                continue                      # degree yet, not a life event
            out.append({
                "label": label, "body": NATAL_KEY[body], "angle": angle,
                "date": when.isoformat(), "year": when.year,
                "month": when.month,
                "age": _age_on(birth, when), "weight": weight,
                "passes": [_jd_to_date(h).isoformat() for h in group],
            })

    out.sort(key=lambda e: e["date"])
    return out


def _group(values, max_gap):
    groups, cur = [], []
    for v in sorted(values):
        if cur and v - cur[-1] > max_gap:
            groups.append(cur)
            cur = []
        cur.append(v)
    if cur:
        groups.append(cur)
    return groups


def luck_pillars(chart, birth, gender, count=8):
    """BaZi 10 year luck pillars (da yun).

    Direction depends on the polarity of the year stem combined with gender,
    so without gender this cannot be computed and returns None rather than
    guessing. The start age is the distance to the bounding solar term, three
    days to a year, which is the classical rule.
    """
    if gender not in ("male", "female"):
        return None

    y_gan = chart["bazi"]["pillars"]["year"]["gan"]
    m_gan = chart["bazi"]["pillars"]["month"]["gan"]
    m_zhi = chart["bazi"]["pillars"]["month"]["zhi"]
    if y_gan not in GAN or m_gan not in GAN or m_zhi not in ZHI:
        return None

    yang_year = GAN.index(y_gan) % 2 == 0
    forward = (yang_year and gender == "male") or (not yang_year and gender == "female")

    jie = _nearest_jie(birth, forward)
    if jie is None:
        return None
    days = abs((jie - birth).days)
    start_age = days / 3.0

    gi, zi = GAN.index(m_gan), ZHI.index(m_zhi)
    step = 1 if forward else -1
    pillars = []
    for k in range(1, count + 1):
        g, z = (gi + step * k) % 10, (zi + step * k) % 12
        pillars.append({
            "gan": GAN[g], "zhi": ZHI[z], "animal": ZHI_ANIMAL[z],
            "element": GAN_EL[g], "branch_element": ZHI_EL[z],
            "start_age": round(start_age + (k - 1) * 10, 2),
            "end_age": round(start_age + k * 10, 2),
            "start_year": birth.year + int(start_age + (k - 1) * 10),
        })
    return {"direction": "forward" if forward else "backward",
            "start_age": round(start_age, 2), "pillars": pillars}


def _nearest_jie(birth, forward):
    """The month-starting solar terms are the odd indices in sxtwl's 24."""
    for off in range(1, 33):
        d = birth + timedelta(days=off if forward else -off)
        day = sxtwl.fromSolar(d.year, d.month, d.day)
        if day.hasJieQi() and day.getJieQi() % 2 == 1:
            return d
    return None


# ---------------------------------------------------------------- assembly

def build(chart, birth, gender=None, today=None, span_years=70,
          past_years=3, future_years=3):
    """The whole computed timeline. Free tier shows all of it."""
    today = today or date.today()
    age = _age_on(birth, today)
    this_year = today.year

    ev = transits(chart, birth, span_years=span_years)

    years = []
    for y in range(this_year - past_years, this_year + future_years + 1):
        p = profection(chart, birth, y)
        years.append({
            **p,
            "personal_year": personal_year(birth, y),
            "bazi": bazi_year(chart, y),
            # the dated cycles that land inside this calendar year, so a past
            # year can be checked against them too, not only the house topic
            "transits": [{"label": e["label"], "date": e["date"]}
                         for e in ev if e["year"] == y],
            "state": "past" if y < this_year else ("now" if y == this_year else "ahead"),
        })
    return {
        "age": age,
        "today": today.isoformat(),
        "birth": birth.isoformat(),
        "span_years": span_years,
        "arc": {                      # Jung's solar metaphor, noon at 35 to 40
            "noon_from": 35, "noon_to": 40,
            "position": round(age / span_years, 4),
        },
        "bands": {
            "jung": JUNG_STAGES, "levinson": LEVINSON_STAGES,
            "erikson": ERIKSON_STAGES,
            "now": {"jung": _band(JUNG_STAGES, age),
                    "levinson": _band(LEVINSON_STAGES, age),
                    "erikson": _band(ERIKSON_STAGES, age)},
        },
        "luck_pillars": luck_pillars(chart, birth, gender),
        "transits": ev,
        "next_transits": [e for e in ev if e["date"] >= today.isoformat()][:5],
        "years": years,
        # Deliberately empty. The reader's own life is the one row a birth
        # chart cannot fill, and that gap is the honest reason to go further.
        "life_events": [],
    }
