"""golden dawn correspondences, sephiroth, and house meanings."""

# planet -> sephirah on the tree of life (classic golden dawn attribution)
PLANET_SEPHIROTH = {
    "Saturn": "Binah", "Jupiter": "Chesed", "Mars": "Geburah",
    "Sun": "Tiphareth", "Venus": "Netzach", "Mercury": "Hod",
    "Moon": "Yesod", "Pluto": "Kether (modern attribution)",
    "Uranus": "Chokmah (modern attribution)",
    "Neptune": "Da'ath (modern attribution)",
}

# zodiac sign -> (element, modality, ruler, hebrew letter, tarot major, king-scale color)
SIGNS_GD = [
    ("Aries", "Fire", "Cardinal", "Mars", "Heh", "The Emperor (4)", "Red"),
    ("Taurus", "Earth", "Fixed", "Venus", "Vav", "The Hierophant (5)", "Red-orange"),
    ("Gemini", "Air", "Mutable", "Mercury", "Zayin", "The Lovers (6)", "Orange"),
    ("Cancer", "Water", "Cardinal", "Moon", "Cheth", "The Chariot (7)", "Amber"),
    ("Leo", "Fire", "Fixed", "Sun", "Teth", "Strength (8)", "Yellow (greenish)"),
    ("Virgo", "Earth", "Mutable", "Mercury", "Yod", "The Hermit (9)", "Yellow-green"),
    ("Libra", "Air", "Cardinal", "Venus", "Lamed", "Justice (11)", "Emerald green"),
    ("Scorpio", "Water", "Fixed", "Mars/Pluto", "Nun", "Death (13)", "Blue-green"),
    ("Sagittarius", "Fire", "Mutable", "Jupiter", "Samekh", "Temperance (14)", "Blue"),
    ("Capricorn", "Earth", "Cardinal", "Saturn", "Ayin", "The Devil (15)", "Indigo"),
    ("Aquarius", "Air", "Fixed", "Saturn/Uranus", "Tzaddi", "The Star (17)", "Violet"),
    ("Pisces", "Water", "Mutable", "Jupiter/Neptune", "Qoph", "The Moon (18)", "Crimson"),
]

# planets -> hebrew paths via the signs they rule (dupes ok; order = path on tree)
PLANET_PATHS = {
    "Mars": ["Heh (Aries)", "Nun (Scorpio)"],
    "Venus": ["Vav (Taurus)", "Lamed (Libra)"],
    "Mercury": ["Zayin (Gemini)", "Yod (Virgo)"],
    "Moon": ["Cheth (Cancer)"],
    "Sun": ["Teth (Leo)"],
    "Jupiter": ["Samekh (Sagittarius)", "Qoph (Pisces)"],
    "Saturn": ["Ayin (Capricorn)", "Tzaddi (Aquarius)"],
}

# the sephiroth, top to bottom, with the corresponding divine name + planet
SEPHIROTH = [
    ("Kether", "the Crown", "Eheieh", "-"),
    ("Chokmah", "Wisdom", "Yah", "Uranus / zodiac"),
    ("Binah", "Understanding", "YHVH Elohim", "Saturn"),
    ("Da'ath", "Knowledge (abyss)", "-", "Neptune (modern)"),
    ("Chesed", "Mercy", "El", "Jupiter"),
    ("Geburah", "Severity", "Elohim Gibor", "Mars"),
    ("Tiphareth", "Beauty", "YHVH Eloah ve-Daath", "Sun"),
    ("Netzach", "Victory", "YHVH Tzabaoth", "Venus"),
    ("Hod", "Splendour", "Elohim Tzabaoth", "Mercury"),
    ("Yesod", "Foundation", "Shaddai El Chai", "Moon"),
    ("Malkuth", "Kingdom", "Adonai ha-Aretz", "Earth"),
]

# short house meanings (astrolog -HI has longer text; these are the quick refs)
HOUSES = [
    (1, "self, body, appearance, the raw approach to life"),
    (2, "money, possessions, values, self-worth"),
    (3, "communication, siblings, short trips, learning"),
    (4, "home, family, roots, the private base"),
    (5, "creativity, romance, children, play"),
    (6, "work, health, service, daily routine"),
    (7, "partnership, marriage, open enemies, the other"),
    (8, "death, sex, transformation, shared resources"),
    (9, "philosophy, travel, higher education, belief"),
    (10, "career, reputation, public standing, the parent-as-authority"),
    (11, "friends, groups, hopes, the collective future"),
    (12, "the unconscious, solitude, hidden enemies, dissolution"),
]

MOON_MANSIONS = [
    (1, "Al-Sharatain 0Ari00-12Ari51", "beginnings, body, medicine"),
    (2, "Al-Butain 12Ari52-25Ari43", "discovery, hidden things, digging"),
    (3, "Al-Thurayya 25Ari43-8Tau17", "abundance, gatherings"),
    (4, "Al-Dabaran 8Tau17-21Tau10", "conflict, confrontation, courage"),
    (5, "Al-Haqa 21Tau10-4Gem03", "seclusion, rest, retreat"),
    (6, "Al-Hanaya 4Gem03-16Gem57", "favor, loyalty, love"),
    (7, "Al-Dhira 16Gem57-29Gem51", "weapons, defense, sharp action"),
    (8, "Al-Nathla 29Gem51-12Can45", "movement, journeys, escape"),
    (9, "Al-Tarf 12Can45-25Can38", "discord, boundaries, eyes"),
    (10, "Al-Jabha 25Can38-8Leo31", "friendship, beauty, adornment"),
    (11, "Al-Zubra 8Leo31-21Leo24", "generosity, royalty"),
    (12, "Al-Sarfa 21Leo24-4Vir17", "departure, movement, change"),
    (13, "Al-Awwa 4Vir17-17Vir10", "love, healing, divination"),
    (14, "Al-Simak 17Vir10-30Vir03", "harvest, protection, cutting ties"),
    (15, "Al-Ghafr 30Vir03-12Lib57", "commerce, writing, craft"),
    (16, "Al-Zubana 12Lib57-25Lib50", "justice, judgment, society"),
    (17, "Al-Iklil 25Lib50-8Sco43", "protection, defense, circles"),
    (18, "Al-Qalb 8Sco43-21Sco36", "the heart, danger, passion"),
    (19, "Al-Shaula 21Sco36-4Sag29", "stings, binding, mischief"),
    (20, "Al-Naaim 4Sag29-17Sag22", "comfort, ease, hospitality"),
    (21, "Al-Baldah 17Sag22-0Cap15", "strength, vulnerability in war"),
    (22, "Al-Saad al-Dhabih 0Cap15-13Cap08", "sacrifice, banishing"),
    (23, "Al-Saad al-Bula 13Cap08-26Cap01", "dissolution, endings"),
    (24, "Al-Saad al-Suud 26Cap01-8Aqr55", "gaining, ambition"),
    (25, "Al-Saad al-Ahbiyah 8Aqr55-21Aqr48", "isolation, secrets"),
    (26, "Al-Fargh al-Mukdim 21Aqr48-4Pis41", "gatherings, unions"),
    (27, "Al-Fargh al-Thani 4Pis41-17Pis34", "completion, baths, vows"),
    (28, "Al-Risha/Batn al-Hut 17Pis34-0Ari00", "deep water, endings, the veil"),
]


def sign_lore(sign: str) -> str:
    for row in SIGNS_GD:
        if row[0].lower() == sign.lower() or row[0][:3].lower() == sign.lower():
            (name, elem, mod, ruler, heb, tarot, color) = row
            seph = PLANET_SEPHIROTH.get(ruler.split("/")[0], "-")
            return (f"{name} — {elem} {mod}, ruled by {ruler}\n"
                    f"golden dawn: hebrew letter {heb}, tarot {tarot}, "
                    f"king-scale color {color}\n"
                    f"ruler's sephirah: {seph}")
    return f"no golden dawn data for {sign!r}"


def planet_lore(planet: str) -> str:
    for row in SEPHIROTH:
        if row[3].lower().startswith(planet.lower()):
            return f"{planet} -> sephirah {row[0]} ({row[1]}), divine name {row[2]}"
    if planet.lower() in [p.lower() for p in PLANET_SEPHIROTH]:
        return f"{planet} -> {PLANET_SEPHIROTH[planet.capitalize()]}"
    return f"no sephirah attribution for {planet!r}"


def moon_mansion(deg: int, sign: str) -> str:
    """which lunar mansion the moon sits in, given sign + degree."""
    import re

    idx = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
           "Lib", "Sco", "Sag", "Cap", "Aqr", "Pis"].index(sign[:3])
    absolute = idx * 30 + deg
    for n, span, meaning in MOON_MANSIONS:
        # spans hold "name degSignMM-degSignMM"; extract degree-sign pairs
        pairs = re.findall(r"(\d+)([A-Za-z]{3})", span)
        if len(pairs) < 2:
            continue
        start = 30 * _SIGN_IDX[pairs[0][1]] + int(pairs[0][0])
        end = 30 * _SIGN_IDX[pairs[-1][1]] + int(pairs[-1][0])
        if start <= absolute < end or (end < start and (absolute >= start or absolute < end)):
            return f"mansion {n} {span}: {meaning}"
    return "mansion lookup failed"


_SIGN_IDX = {s: i for i, s in enumerate(
    ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
     "Lib", "Sco", "Sag", "Cap", "Aqr", "Pis"])}
