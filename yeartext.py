# -*- coding: utf-8 -*-
"""Decoda · what a year is like, in words a person can check against memory.

Every sentence here is chosen by computed factors, never written per person:
the profection house and the sign it falls in (varies with the Rising sign),
the BaZi year stem read against the day master (ten gods, varies by day
master), the year branch against the day branch, the numerology personal year
(varies by birth day and month), and the dated transits inside the year.

Tone rules, same as the report spec: tendencies, not events. No clinical
language. No em dashes. For years that have not happened yet the same text is
framed as themes, never as predictions.
"""

HOUSES = {
    1: dict(head="you, your body and how you show up", tags={"self", "body", "change"},
            feel="The year turns the attention back onto you: how you look, how you come across, what your body is telling you. People often start something under their own name, change how they present themselves, or feel unusually visible.",
            signs=["a change in how you look or present yourself", "starting something that is clearly yours",
                   "your body asking for attention", "feeling more noticed than usual"]),
    2: dict(head="money, what you own and what you are worth", tags={"money", "worth"},
            feel="Money and self-worth move into the foreground. The practical question of earning and the quieter question of what you are worth tend to arrive together.",
            signs=["a change in income or in how you earn it", "a purchase or a loss that mattered more than its price",
                   "renegotiating your rate, salary or value", "sorting out what you actually own and need"]),
    3: dict(head="daily talk, learning, siblings and short trips", tags={"learning", "talk", "near"},
            feel="Life speeds up at the local scale: messages, errands, short trips, a course, a lot of talking and writing. Siblings, neighbours or close peers often play a bigger part than usual.",
            signs=["a course, a new skill or a lot of reading", "a sibling or close peer needing or giving more",
                   "many short trips or a new daily route", "writing, messaging or speaking more than usual"]),
    4: dict(head="home, family and the private base", tags={"home", "inner"},
            feel="The centre of gravity moves home. Where you live, who you live with and the family you come from all ask for attention, sometimes quietly, sometimes through a move.",
            signs=["moving, renovating or rethinking where you live", "a parent or family matter taking real time",
                   "wanting more privacy and a smaller circle", "old family patterns becoming clearer"]),
    5: dict(head="play, creating, romance and children", tags={"expression", "joy"},
            feel="The year leans towards pleasure and making things for their own sake. Romance, creative work, children and anything done for joy rather than duty tend to take up more room.",
            signs=["a new romance, or an old one rekindled", "a creative project done for its own sake",
                   "children, yours or other people's, more present", "more going out, play or risk-taking"]),
    6: dict(head="the body, daily work and routine", tags={"body", "work", "routine"},
            feel="The unglamorous machinery of life comes up for review: health, habits, workload, the daily grind. It is often a year of fixing systems, and sometimes of the body insisting on it.",
            signs=["a health issue, a check-up or a new habit", "a heavier workload or a new daily routine at work",
                   "reorganising how your days actually run", "looking after someone or something that needs care"]),
    7: dict(head="other people: partners, rivals and contracts", tags={"others", "partnership"},
            feel="Other people become the main event. Partnerships form, change or are tested, and the qualities you notice most in others often turn out to be your own.",
            signs=["a relationship starting, deepening or ending", "a business partner, client or contract taking centre stage",
                   "a conflict or rivalry you could not avoid", "seeing yourself more clearly through someone else"]),
    8: dict(head="shared money, fear and deep change", tags={"change", "shared", "depth"},
            feel="The year goes below the surface. Shared money, debt, inheritance, intimacy and the things people usually avoid talking about come up, and something often has to end so something else can start.",
            signs=["debt, shared money, tax or inheritance matters", "an intense closeness, or a trust tested",
                   "facing a fear you usually avoid", "something ending that made room for change"]),
    9: dict(head="meaning, belief, study and distance", tags={"meaning", "learning", "far"},
            feel="The horizon widens. Travel, study, publishing, belief and the search for meaning pull you beyond the familiar, and your view of how the world works tends to shift.",
            signs=["a long trip or time abroad", "serious study, a qualification or teaching",
                   "a change in belief or worldview", "dealing with law, publishing or people from far away"]),
    10: dict(head="career, reputation and public role", tags={"work", "status", "visibility"},
             feel="Work and public standing move to the front. New roles, visibility and the question of what you are known for tend to define the year, along with more responsibility.",
             signs=["a promotion, a new title or a clear career step", "more visibility than you are used to",
                    "a boss or an institution shaping your year", "deciding what you want to be known for"]),
    11: dict(head="friends, networks and the future you aim at", tags={"others", "network", "future"},
             feel="The year runs through people in the plural: friends, communities, collaborators. Long-range plans get clearer, and so does who you actually want around you.",
             signs=["a new circle, community or team", "a friendship growing, or quietly ending",
                    "a long-term goal becoming clearer", "help arriving through someone you know"]),
    12: dict(head="solitude, rest and what runs underneath", tags={"inner", "endings", "rest"},
             feel="A quieter, more inward year. Things wind down, you need more rest and time alone, and what has been running under the surface becomes easier to see. It often reads as the end of a cycle.",
             signs=["needing more sleep, solitude or retreat", "a cycle quietly ending",
                    "work behind the scenes that nobody sees", "old feelings or patterns surfacing"]),
}

SIGN_FLAVOUR = {
    "Aries": "fast and directly, sometimes through conflict",
    "Taurus": "slowly, through money, comfort and the body",
    "Gemini": "through talk, ideas, messages and short moves",
    "Cancer": "through feelings, family and a need for safety",
    "Leo": "visibly, with pride and a wish to be seen",
    "Virgo": "through details, work and practical fixes",
    "Libra": "through other people, balance and agreements",
    "Scorpio": "intensely and privately, with a lot at stake",
    "Sagittarius": "through travel, belief and wanting more room",
    "Capricorn": "through duty, structure and long-term goals",
    "Aquarius": "through groups, ideas and breaking with convention",
    "Pisces": "quietly, through intuition, blurred edges and retreat",
}

# Ten gods, collapsed to their five families. Read the year stem against the
# day master: same element, produces it, it produces, it controls, controls it.
PRODUCES = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
CONTROLS = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}
GODS = {
    "companion": dict(name="Companion", tags={"self", "others"},
                      text="peers, rivals and your own independence are the theme",
                      sign="competing with, or leaning on, people like you"),
    "resource": dict(name="Resource", tags={"learning", "home", "rest"},
                     text="support, learning and being looked after are the theme",
                     sign="being supported, taught or looked after"),
    "output": dict(name="Output", tags={"expression", "joy"},
                   text="expression is the theme, making, speaking and showing what you have",
                   sign="putting more of yourself out: making, speaking, showing"),
    "wealth": dict(name="Wealth", tags={"money", "work"},
                   text="money, effort and results you have to go after are the theme",
                   sign="working harder for money or results"),
    "pressure": dict(name="Pressure", tags={"work", "status"},
                     text="rules, responsibility and being tested are the theme",
                     sign="pressure from rules, a boss or responsibility"),
}

RELATION = {
    "clashes with your day branch": ("a clash with your day branch: movement and disruption, often at home or in close relationships",
                                     "a move, a break, or something shaken loose"),
    "six harmony with your day branch": ("a six harmony with your day branch: an easy alliance, something that fits",
                                         "a person or an opportunity that simply fit"),
    "part of a triad with your day branch": ("part of a triad with your day branch: carried by a current bigger than you",
                                             "momentum you did not have to create yourself"),
    "harm with your day branch": ("a harm with your day branch: friction that is quiet but wearing",
                                  "a low, steady friction that wore you down"),
    "repeats your day branch": ("your own day branch repeated: a mirror year, old patterns show up clearly",
                                "meeting your own habits in someone or something else"),
    "same pillar as your day": ("the year pillar is identical to your day pillar: a mirror year, you meet your own pattern head on",
                                "meeting your own habits in someone or something else"),
}

PERSONAL_YEAR = {
    1: ("beginnings", "a new nine-year cycle starts", {"self", "change"}),
    2: ("patience and partnership", "a slower year of cooperation and waiting", {"others", "partnership"}),
    3: ("expression and people", "a sociable, expressive year", {"expression", "joy"}),
    4: ("building", "a year of hard work and foundations", {"work", "home"}),
    5: ("change and freedom", "a restless year that wants movement", {"change", "far"}),
    6: ("responsibility and care", "a year of home, duty and looking after others", {"home", "others"}),
    7: ("an inward year", "a year for study, solitude and questions", {"inner", "learning"}),
    8: ("power and results", "a year about money, ambition and results", {"money", "work", "status"}),
    9: ("completion", "a year of endings and letting go", {"endings", "change"}),
}

TRANSIT_TEXT = {
    "Saturn return": "Saturn back at its birth position: structures are tested, and what is not really yours gets harder to carry",
    "Saturn square Saturn": "a Saturn checkpoint: effort and limits, a push to adjust what is not working",
    "Saturn opposition Saturn": "Saturn opposite its birth position: outside demands test what you have built",
    "Uranus opposition Uranus": "the classic midlife shake-up: a strong pull towards freedom and change",
    "Neptune square Neptune": "a foggy stretch: old certainties dissolve and ideals get questioned",
    "Pluto square Pluto": "slow, deep change: questions of power and control come to the surface",
}

TAG_WORDS = {
    "self": "you yourself", "body": "the body", "change": "change", "money": "money", "worth": "worth",
    "learning": "learning", "talk": "communication", "near": "your close world", "home": "home and family",
    "inner": "your inner life", "expression": "self-expression", "joy": "pleasure", "work": "work",
    "routine": "routine", "others": "other people", "partnership": "partnership", "shared": "shared resources",
    "depth": "depth", "meaning": "meaning", "far": "distance", "visibility": "visibility", "status": "status",
    "network": "networks", "future": "the future", "endings": "endings", "rest": "rest",
}


ZHI = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
# Three harmonies (san he) and directional assemblies (san hui), with the
# element each one produces. A year branch that completes one of these with
# branches already in the chart is the strongest thing BaZi says about a year.
TRIADS = [({8, 0, 4}, "Water", 0), ({11, 3, 7}, "Wood", 3), ({2, 6, 10}, "Fire", 6), ({5, 9, 1}, "Metal", 9)]
ASSEMBLIES = [({2, 3, 4}, "Wood"), ({5, 6, 7}, "Fire"), ({8, 9, 10}, "Metal"), ({11, 0, 1}, "Water")]
COMBO_TEXT = {
    "resource": ("a strong current of support: being fed, taught and looked after", "being fed, taught or given a foundation"),
    "output": ("a strong current of expression: the year burns hot and you put out a lot", "burning a lot of energy on what you make or say"),
    "wealth": ("a strong current of effort and money", "chasing money, results or a big practical goal"),
    "pressure": ("a strong current of pressure: status, responsibility, being tested", "a role, a title or a responsibility weighing on you"),
    "companion": ("a strong current of your own element: independence, peers and competition", "standing on your own, or against people like you"),
}


def combo(year_zhi, natal_zhis):
    """Full triad or assembly completed by the year branch, else a half triad
    that includes the centre branch. Returns (kind, element) or None."""
    y = ZHI.index(year_zhi)
    natal = {ZHI.index(z) for z in natal_zhis if z in ZHI}
    for group, el, centre in TRIADS:
        if y in group and (group - {y}) <= natal:
            return "full triad", el
    for group, el in ASSEMBLIES:
        if y in group and (group - {y}) <= natal:
            return "full assembly", el
    for group, el, centre in TRIADS:
        if y in group and any(n in group and n != y for n in natal) and (y == centre or centre in natal):
            return "half triad", el
    return None


def ten_god(year_element, dm_element):
    if year_element == dm_element:
        return "companion"
    if PRODUCES[year_element] == dm_element:
        return "resource"
    if PRODUCES[dm_element] == year_element:
        return "output"
    if CONTROLS[dm_element] == year_element:
        return "wealth"
    return "pressure"


def describe(row, chart):
    """Turn one computed year row into prose a person can check."""
    h = HOUSES[row["house"]]
    dm, dm_el = chart["bazi"]["day_master"], chart["bazi"]["day_master_element"]
    god_key = ten_god(row["bazi"]["element"], dm_el)
    god = GODS[god_key]
    rel = RELATION.get(row["bazi"]["relation_to_day"] or "")
    py_label, py_text, py_tags = PERSONAL_YEAR[row["personal_year"]]

    natal_zhis = [chart["bazi"]["pillars"][k]["zhi"] for k in ("year", "month", "day", "hour")]
    cmb = combo(row["bazi"]["zhi"], natal_zhis)
    cmb_line, cmb_sign, bazi_tags, cg = None, None, set(god["tags"]), None
    if cmb:
        kind, el = cmb
        cg = ten_god(el, dm_el)
        strength = "completes a" if kind.startswith("full") else "forms a half"
        what = "triad" if "triad" in kind else "directional assembly"
        cmb_line = (f"The year branch {strength} {el} {what} with branches already in your chart. "
                    f"For a {dm} day master {el} is {GODS[cg]['name'].lower()}, so this is "
                    f"{COMBO_TEXT[cg][0]}.")
        cmb_sign = COMBO_TEXT[cg][1]
        bazi_tags |= GODS[cg]["tags"]

    signs = h["signs"][:2] + [cmb_sign or god["sign"]]
    # fourth sign: the branch relation if there is one, else the stem reading
    # unless the combination already said the same thing, else the house again
    if rel:
        signs.append(rel[1])
    elif cmb_sign and cg != god_key:
        signs.append(god["sign"])
    else:
        signs.append(h["signs"][2])

    layers = {"astrology": h["tags"], "bazi": bazi_tags, "numerology": py_tags}
    counts = {}
    for tags in layers.values():
        for t in tags:
            counts[t] = counts.get(t, 0) + 1
    agree_tag, agree_n = max(counts.items(), key=lambda kv: (kv[1], kv[0] in h["tags"]))
    agreement = None
    if agree_n >= 2:
        who = "All three layers" if agree_n == 3 else "Two of the three layers"
        agreement = f"{who} point at the same thing this year: {TAG_WORDS[agree_tag]}."

    return {
        "headline": f"A year about {h['head']}.",
        "feel": h["feel"],
        "flavour": f"In your chart this falls in {row['sign']}, so it tends to play out {SIGN_FLAVOUR[row['sign']]}.",
        "signs": signs,
        "bazi": {"god": god["name"],
                 "text": f"{god['name']} year for a {dm} day master: {god['text']}.",
                 "relation": (rel[0][0].upper() + rel[0][1:] + ".") if rel else None,
                 "combo": cmb_line},
        "numerology": f"Personal year {row['personal_year']}, {py_label}: {py_text}.",
        "transits": [{"label": t["label"], "date": t["date"],
                      "text": TRANSIT_TEXT.get(t["label"], "")} for t in row.get("transits", [])],
        "agreement": agreement,
    }
