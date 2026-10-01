"""Regression checks for the compute engine. Run: python3 test_engine.py

References are public charts with published results, not charts produced by
this code, so a pass means agreement with an independent source.
"""
import random
from datetime import date
import swisseph as swe
import engine
import timeline


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("ok ", msg)


# 1. Design = exactly 88 degrees of solar arc before birth, for any birth.
random.seed(1)
for _ in range(300):
    jd = swe.julday(random.randint(1900, 2030), random.randint(1, 12), random.randint(1, 28), random.random() * 24)
    sun = swe.calc_ut(jd, swe.SUN)[0][0]
    djd = engine.design_jd(jd, sun)
    arc = (sun - swe.calc_ut(djd, swe.SUN)[0][0]) % 360
    assert abs(arc - 88) < 1e-6, (jd, arc)
    assert 85 < jd - djd < 95, (jd, jd - djd)
check(True, "design sun sits 88.000000 deg before birth sun on 300 random births")

# 2. Published reference charts (type, authority, profile, incarnation cross gates).
REF = [
    # Ra Uru Hu, 1948-04-09 00:14 Montreal (EST): Manifestor 5/1 Splenic, cross 51/57 | 61/62
    ((1948, 4, 9, 0, 14, 45.5, -73.57, -5), "Manifestor", "Splenic", "5/1", ("51", "57", "61", "62")),
    # Steve Jobs, 1955-02-24 19:15 San Francisco (PST): Generator 6/3 Emotional, cross 55/59 | 9/16
    ((1955, 2, 24, 19, 15, 37.77, -122.42, -8), "Generator", "Emotional", "6/3", ("55", "59", "9", "16")),
    # 1996-09-05 14:45 Long Xuyen (UTC+7), checked on Jovian Archive 01/10/2026: Generator 2/4 Sacral,
    # cross 64/63 | 35/5. Design nodes 57.1/51.1 only with the TRUE node (mean node gives 48/21 -> Manifestor).
    ((1996, 9, 5, 14, 45, 10.386, 105.435, 7), "Generator", "Sacral", "2/4", ("64", "63", "35", "5")),
]
for args, typ, auth, prof, cross in REF:
    h = engine.compute(*args)["hd"]
    got = (h["gates_personality"]["Sun"].split(".")[0], h["gates_personality"]["Earth"].split(".")[0],
           h["gates_design"]["Sun"].split(".")[0], h["gates_design"]["Earth"].split(".")[0])
    check((h["type"], h["authority"], h["profile"], got) == (typ, auth, prof, cross),
          f"reference chart {args[:3]} -> {h['type']} {h['authority']} {h['profile']} cross {got}")

# 3. Motor to Throat through the G center (Heart-G-Throat) makes a Manifestor.
defined = {"Heart", "G", "Throat"}
check(engine.hd_type_authority(defined, [(25, 51), (10, 20)]) == ("Manifestor", "Ego Manifested"),
      "Heart-G-Throat chain is Manifestor, not Projector")
check(engine.hd_type_authority({"G", "Throat"}, [(10, 20)]) == ("Projector", "Self-Projected"),
      "G-Throat only is Self-Projected Projector")
check(engine.hd_type_authority({"Head", "Ajna", "Throat"}, [(64, 47), (17, 62)]) == ("Projector", "Mental"),
      "Head-Ajna-Throat only is Mental Projector")
check(engine.hd_type_authority(set(), []) == ("Reflector", "Lunar"), "no definition is Lunar Reflector")
check(engine.hd_type_authority({"Sacral", "G", "Throat"}, [(2, 14), (10, 20)])[0] == "Manifesting Generator",
      "Sacral-G-Throat chain is Manifesting Generator")

# 4. No authority is ever left unnamed.
random.seed(2)
for _ in range(300):
    c = engine.compute(random.randint(1940, 2010), random.randint(1, 12), random.randint(1, 28),
                       random.randint(0, 23), random.randint(0, 59), 10, 106, 7)
    assert c["hd"]["authority"] != "Other"
check(True, "no 'Other' authority across 300 random charts")

# 5. 29 February birthdays in common years.
c = engine.compute(2000, 2, 29, 12, 0, 40.7, -74.0, -5)
houses = [timeline.profection(c, date(2000, 2, 29), y)["house"] for y in (2025, 2026, 2027, 2028)]
check(houses == [2, 3, 4, 5], f"leap-day profection walks one house a year {houses}")
tl = timeline.build(c, date(2000, 2, 29), gender="female", today=date(2026, 9, 30))
check(len(tl["years"]) == 7, "leap-day timeline builds without error")
print("all checks passed")
