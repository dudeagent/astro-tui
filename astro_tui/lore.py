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


# --- liber 777 searchable correspondence table ---
# crowley's liber 777 condensed to terminal-friendly columns. one row per
# entity (sephira/planet/sign/path/decan); empty string = not applicable.
# sephiroth/planets/signs reuse the golden dawn tables above; paths and
# decans are new. search_liber777() renders matches as readable blocks.
LIBER777_COLUMNS = [
    "name", "type", "sephira", "path", "element", "modality",
    "ruler", "hebrew", "tarot", "kingcolor", "divinename", "sign",
    "meaning"]

# pretty labels for the columns (shown in the UI / output blocks)
LIBER777_LABELS = {
    "name": "name", "type": "type", "sephira": "sephira",
    "path": "path", "element": "element", "modality": "modality",
    "ruler": "ruler", "hebrew": "hebrew", "tarot": "tarot",
    "kingcolor": "king color", "divinename": "divine name",
    "sign": "sign", "meaning": "meaning"}


def _777row(**kw):
    row = {c: "" for c in LIBER777_COLUMNS}
    row.update(kw)
    return row


def _777_sign_sephira(ruler: str) -> str:
    return PLANET_SEPHIROTH.get(ruler.split("/")[0], "-")


_SEPHIRA_MEANINGS = {
    "Kether": "unity, the point, pure being",
    "Chokmah": "wisdom, the flash of intuition",
    "Binah": "understanding, the great mother, form",
    "Da'ath": "knowledge, the abyss, the gate",
    "Chesed": "mercy, expansion, order",
    "Geburah": "severity, strength, discipline",
    "Tiphareth": "beauty, sacrifice, the heart of the tree",
    "Netzach": "victory, endurance, desire",
    "Hod": "splendour, intellect, communication",
    "Yesod": "foundation, dreams, the unconscious",
    "Malkuth": "kingdom, the manifest world",
}

_PLANET_MEANINGS = {
    "Saturn": "structure, time, restriction",
    "Jupiter": "expansion, fortune, mercy",
    "Mars": "force, energy, conflict",
    "Sun": "vitality, identity, the heart",
    "Venus": "love, desire, beauty",
    "Mercury": "intellect, communication, magic",
    "Moon": "instinct, dreams, the subconscious",
    "Pluto": "transformation, the underworld",
    "Uranus": "disruption, invention",
    "Neptune": "dissolution, mysticism",
}

_SIGN_MEANINGS = {
    "Aries": "initiative, fire, the pioneer",
    "Taurus": "stability, possessions, the builder",
    "Gemini": "duality, communication, curiosity",
    "Cancer": "nurture, home, memory",
    "Leo": "radiance, creativity, the sovereign",
    "Virgo": "discernment, service, craft",
    "Libra": "balance, partnership, justice",
    "Scorpio": "intensity, transformation, depth",
    "Sagittarius": "exploration, philosophy, the arrow",
    "Capricorn": "ambition, structure, the mountain",
    "Aquarius": "invention, humanity, the waterbearer",
    "Pisces": "dissolution, empathy, the ocean",
}

# golden dawn hebrew path attributions: (letter, path number, connects, tarot)
_PATHS = [
    ("Aleph", 11, "Kether–Chokmah", "The Fool (0)"),
    ("Beth", 12, "Kether–Binah", "The Magician (1)"),
    ("Gimel", 13, "Kether–Tiphareth", "The High Priestess (2)"),
    ("Daleth", 14, "Chokmah–Binah", "The Empress (3)"),
    ("Heh", 15, "Chokmah–Tiphareth", "The Emperor (4)"),
    ("Vav", 16, "Chokmah–Chesed", "The Hierophant (5)"),
    ("Zayin", 17, "Binah–Tiphareth", "The Lovers (6)"),
    ("Cheth", 18, "Binah–Geburah", "The Chariot (7)"),
    ("Teth", 19, "Chesed–Geburah", "Strength (8)"),
    ("Yod", 20, "Chesed–Tiphareth", "The Hermit (9)"),
    ("Kaph", 21, "Chesed–Netzach", "The Wheel of Fortune (10)"),
    ("Lamed", 22, "Geburah–Tiphareth", "Justice (11)"),
    ("Mem", 23, "Geburah–Hod", "The Hanged Man (12)"),
    ("Nun", 24, "Tiphareth–Netzach", "Death (13)"),
    ("Samekh", 25, "Tiphareth–Yesod", "Temperance (14)"),
    ("Ayin", 26, "Tiphareth–Hod", "The Devil (15)"),
    ("Pe", 27, "Netzach–Hod", "The Tower (16)"),
    ("Tzaddi", 28, "Netzach–Yesod", "The Star (17)"),
    ("Qoph", 29, "Netzach–Malkuth", "The Moon (18)"),
    ("Resh", 30, "Hod–Tiphareth", "The Sun (19)"),
    ("Shin", 31, "Hod–Malkuth", "Judgement (20)"),
    ("Tav", 32, "Yesod–Malkuth", "The Universe (21)"),
]

_PATH_ELEMENTS = {"Aleph": "Air", "Mem": "Water", "Shin": "Fire"}

_PATH_MEANINGS = {
    "Aleph": "pure potential, the fool's leap",
    "Beth": "will, communication, focus",
    "Gimel": "the unseen, lunar mystery",
    "Daleth": "love, fertility, the mother",
    "Heh": "sight, authority, the window",
    "Vav": "faith, obedience, the nail",
    "Zayin": "choice, the sword, division",
    "Cheth": "enclosure, the vessel",
    "Teth": "serpent power, hidden strength",
    "Yod": "the hand, inner work",
    "Kaph": "rotation, fortune, the palm",
    "Lamed": "teaching, equilibrium, the ox-goad",
    "Mem": "water, suspended awareness",
    "Nun": "death, movement, the fish",
    "Samekh": "prophecy, the bow, circulation",
    "Ayin": "the eye, material temptation",
    "Pe": "the mouth, awakening by force",
    "Tzaddi": "the fishhook, trust, meditation",
    "Qoph": "the back of the head, sleep, the transition",
    "Resh": "the head, solar consciousness",
    "Shin": "fire, judgement, transformation",
    "Tav": "the mark, the cosmic plan",
}

# golden dawn decan rulers (3 per sign) and minor-arcana cards.
# minors run 2-10 of the suit following fire, earth, air, water (Aries = 2/Wands).
_DECAN_RULERS = {
    "Aries": ["Mars", "Sun", "Venus"],
    "Taurus": ["Mercury", "Moon", "Saturn"],
    "Gemini": ["Jupiter", "Mars", "Sun"],
    "Cancer": ["Venus", "Mercury", "Moon"],
    "Leo": ["Saturn", "Jupiter", "Mars"],
    "Virgo": ["Sun", "Venus", "Mercury"],
    "Libra": ["Moon", "Saturn", "Jupiter"],
    "Scorpio": ["Mars", "Sun", "Venus"],
    "Sagittarius": ["Mercury", "Moon", "Saturn"],
    "Capricorn": ["Jupiter", "Mars", "Sun"],
    "Aquarius": ["Venus", "Mercury", "Moon"],
    "Pisces": ["Saturn", "Jupiter", "Mars"],
}

_SIGN_ELEMENT_SUIT = {
    "Aries": ("Fire", "Wands"), "Leo": ("Fire", "Wands"),
    "Sagittarius": ("Fire", "Wands"),
    "Taurus": ("Earth", "Disks"), "Virgo": ("Earth", "Disks"),
    "Capricorn": ("Earth", "Disks"),
    "Gemini": ("Air", "Swords"), "Libra": ("Air", "Swords"),
    "Aquarius": ("Air", "Swords"),
    "Cancer": ("Water", "Cups"), "Scorpio": ("Water", "Cups"),
    "Pisces": ("Water", "Cups"),
}

_DECAN_NUMBERS = {"Aries": 2, "Taurus": 5, "Gemini": 8,
                  "Cancer": 2, "Leo": 5, "Virgo": 8,
                  "Libra": 2, "Scorpio": 5, "Sagittarius": 8,
                  "Capricorn": 2, "Aquarius": 5, "Pisces": 8}


LIBER777_ROWS = []
# build the table programmatically so the golden dawn data above stays the
# single source of truth.
for _name, _meaning, _divine, _planet in SEPHIROTH:
    LIBER777_ROWS.append(_777row(
        name=_name, type="sephira", divinename=_divine,
        meaning=_SEPHIRA_MEANINGS.get(_name, "")))
for _planet, _seph in PLANET_SEPHIROTH.items():
    LIBER777_ROWS.append(_777row(
        name=_planet, type="planet", sephira=_seph,
        meaning=_PLANET_MEANINGS.get(_planet, "")))
for (_name, _elem, _mod, _ruler, _heb, _tarot, _color) in SIGNS_GD:
    LIBER777_ROWS.append(_777row(
        name=_name, type="sign", element=_elem, modality=_mod,
        ruler=_ruler, hebrew=_heb, tarot=_tarot, kingcolor=_color,
        sephira=_777_sign_sephira(_ruler),
        meaning=_SIGN_MEANINGS.get(_name, "")))
for (_letter, _num, _connects, _tarot) in _PATHS:
    LIBER777_ROWS.append(_777row(
        name=_letter, type="path", path=_num, sephira=_connects,
        tarot=_tarot, element=_PATH_ELEMENTS.get(_letter, ""),
        meaning=_PATH_MEANINGS.get(_letter, "")))
for _sign, (_elem, _suit) in _SIGN_ELEMENT_SUIT.items():
    _start = _DECAN_NUMBERS[_sign]
    for _i, _ruler in enumerate(_DECAN_RULERS[_sign]):
        LIBER777_ROWS.append(_777row(
            name=f"{_sign} {_i + 1} ({_i * 10}-{(_i + 1) * 10}\u00b0)",
            type="decan", sign=_sign, element=_elem, ruler=_ruler,
            tarot=f"{_start + _i} of {_suit}",
            meaning=f"{(_i * 10)}-{(_i + 1) * 10}\u00b0 of {_sign}"))


def search_liber777(query: str, display_column: str = "all") -> str:
    """search the liber 777 table. substring match, case-insensitive, over
    all columns. display_column "all" renders full blocks per match; any
    other column name renders just that column (name/type header kept)."""
    q = (query or "").strip().lower()
    if not q:
        return ""
    matches = [r for r in LIBER777_ROWS
               if any(q in str(v).lower() for v in r.values())]
    if not matches:
        return f"no matches for {query!r} in the liber 777 table"
    out = []
    shown = matches[:40]  # keep the pane sane
    if display_column == "all":
        for row in shown:
            body = [f"  {LIBER777_LABELS[c]}: {row[c]}" for c in LIBER777_COLUMNS
                    if c not in ("name", "type") and row[c]]
            out.append(f"— {row['name']} ({row['type']})\n" + "\n".join(body))
    else:
        for row in shown:
            if row.get(display_column):
                out.append(f"{row['name']} ({row['type']}): {row[display_column]}")
    result = "\n\n".join(out)
    if len(matches) > 40:
        result += f"\n\n(+{len(matches) - 40} more — refine the search)"
    return result
