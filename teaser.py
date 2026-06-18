# -*- coding: utf-8 -*-
"""Templated, instant teaser. Grounded in real computed factors (defeats Barnum by
naming the mechanic). The deep, curated writing lives in the paid report, not here."""

SUN = {
 "Aries":"a drive to start things and move first","Taurus":"a need for steadiness and things that last",
 "Gemini":"a restless, curious mind that needs constant new input","Cancer":"a protective, feeling-led core",
 "Leo":"a need to be seen and to create from the heart","Virgo":"an eye that notices what is wrong and wants to refine it",
 "Libra":"a mind that weighs everything for fairness and balance","Scorpio":"a pull toward depth, intensity and what is hidden",
 "Sagittarius":"a hunger for meaning, freedom and the bigger picture","Capricorn":"a long-game drive to build and achieve",
 "Aquarius":"a need to think independently and break the mold","Pisces":"a porous, imaginative, deeply empathic inner world",
}
ELEM = {
 "Wood":"growth, ideas and reaching outward","Fire":"expression, visibility and creative output",
 "Earth":"stability, care and the practical","Metal":"structure, standards and clarity",
 "Water":"depth, reflection and inner life",
}
TYPE = {
 "Manifesting Generator":"You are built to be busy with what you love, moving fast and on several tracks at once. Your energy is real but conditional: it floods in for what you want and drains on what you force.",
 "Generator":"You are built to respond, not to push. When you do what genuinely lights you up, your energy is deep and renewable; forcing the wrong things quietly burns you out.",
 "Projector":"You are built to guide and see others clearly, not to grind. Your gift lands when you are recognised and invited, and you need more rest than the people around you.",
 "Manifestor":"You are built to initiate and start things others follow. You move in bursts, and you do your best work when you are free to act without waiting for permission.",
 "Reflector":"You are rare: a mirror of the people and places around you. You need the right environment more than almost anyone, and time before any big decision.",
}
AUTH = {
 "Sacral":"Your body knows yes or no faster than your head does. Trust the gut pull in the moment; let analysis check the decision, never make it.",
 "Emotional":"You have no truth in the now. Sleep on anything that matters; your clarity arrives only after the emotional wave has passed.",
 "Splenic":"Your knowing is a quiet, one-time instinct in the moment. It speaks softly and only once, so learn to catch it.",
 "Other":"Your clearest decisions come from the right environment and unhurried time, not from pressure.",
}
OPEN = {
 "SolarPlexus":"you absorb and amplify other people's emotions, often mistaking their mood for your own",
 "Heart":"you can over-promise to prove your worth, when you never needed to prove it",
 "Head":"you take on mental pressure and questions that are not even yours to answer",
 "G":"your sense of direction shifts with your environment, so the wrong room can quietly pull you off course",
}

# what each Moon sign actually needs emotionally
MOON = {
 "Aries":"you need momentum and a clean, direct outlet for feeling",
 "Taurus":"you settle through comfort, touch and a steady, unhurried pace",
 "Gemini":"you process feeling by talking and naming it, not by sitting in it",
 "Cancer":"you feel everything deeply and need a safe base to retreat to",
 "Leo":"you need warmth, recognition and to feel genuinely wanted",
 "Virgo":"you steady yourself by being useful and putting things in order",
 "Libra":"you need harmony and another person to think alongside",
 "Scorpio":"you feel in extremes and need depth, privacy and full honesty",
 "Sagittarius":"you need room, freedom and a sense that more is possible",
 "Capricorn":"you self-soothe through control, competence and quiet achievement",
 "Aquarius":"you need space and tend to observe your own feelings from a step back",
 "Pisces":"you absorb the emotional weather around you and need time alone to clear it",
}
# the pull each dominant element creates
DRIVE = {
 "Wood":"to grow, push outward and keep starting new things",
 "Fire":"to express, be seen and turn energy into something visible",
 "Earth":"to stabilise, take care of people and make things solid and usable",
 "Metal":"to refine, hold a standard and bring order to mess",
 "Water":"to go inward, reflect and understand before you act",
}
_SUN_ELEM = {
 "Aries":"fire","Leo":"fire","Sagittarius":"fire",
 "Gemini":"air","Libra":"air","Aquarius":"air",
 "Taurus":"earth","Virgo":"earth","Capricorn":"earth",
 "Cancer":"water","Scorpio":"water","Pisces":"water",
}
_OUTWARD_WEST = {"fire","air"}
_OUTWARD_EAST = {"Wood","Fire"}

def make_teaser(chart):
    a, b, h = chart["astro"], chart["bazi"], chart["hd"]
    sun_line = SUN.get(a["sun"], "a distinct way of seeing")
    moon_line = MOON.get(a["moon"], "you have your own way of handling feeling")
    elem = b["dominant"]
    elem_line = ELEM.get(elem, "")
    drive = DRIVE.get(elem, "to move in your own direction")

    # honest agreement/tension read between two systems (the brand's moat, in miniature)
    west_out = _SUN_ELEM.get(a["sun"]) in _OUTWARD_WEST
    east_out = elem in _OUTWARD_EAST
    if west_out == east_out:
        bridge = f"These two pull the same way, so the drive {drive} runs strong and is hard to ignore."
    elif west_out:  # Western chart outward, Chinese element inward
        bridge = (f"Here the two disagree: your Western chart pushes you outward and visible, while your "
                  f"{elem} core pulls the other way, {drive}. That split is not a flaw, it is where most of your range lives.")
    else:  # Chinese element outward, Western chart inward
        bridge = (f"Here the two disagree: your {elem} core pushes you {drive}, while your Western chart "
                  f"pulls you toward something quieter and more inward. That split is not a flaw, it is where most of your range lives.")

    core = (f"Your Sun in {a['sun']} gives you {sun_line}, and your {a['moon']} Moon means "
            f"{moon_line}. In the Chinese system your chart leans toward {elem} ({elem_line}), "
            f"built on a {b['day_master']} core, which pulls you {drive}. In Human Design "
            f"you are a {h['type']}. {bridge}")

    strength = TYPE.get(h["type"], "")
    decision = AUTH.get(h["authority"], "")

    # one shadow from an open center if present
    shadow = None
    for c in ["SolarPlexus","Heart","Head","G"]:
        if c in h["open"]:
            shadow = "One thing to watch: " + OPEN[c] + "."
            break
    if not shadow:
        shadow = "One thing to watch: you tend to give out more than you take back in."

    mechanics = f"Sun in {a['sun']} · {a['moon']} Moon · {a['rising']} Rising  ||  {b['day_master']} day master, {elem}-dominant  ||  {h['type']}, {h['authority']} authority, Profile {h['profile']}"

    return {
        "core": core,
        "energy": strength,
        "decision": decision,
        "shadow": shadow,
        "mechanics": mechanics,
        "astro": a, "bazi_dominant": elem, "hd": h,
    }
