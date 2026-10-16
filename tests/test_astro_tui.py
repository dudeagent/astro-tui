"""tests for the astrolog output parsers and lore lookups (no binary needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from astro_tui import astrolog, lore  # noqa: E402

# real astrolog 7.70 output samples
NATAL_V = """Astrolog 7.70 chart for Tue May 15, 1990 12:30pm (ST Zone 6W)  97:37W  0:00N
Body  Locat. Ret. Lati. Rul.      House  Rul. Veloc.    Placidus Houses

Sun : 24Tau39   - 0:00' (-) [ 9th house] [-] +0.964  -  House cusp  1: 20Leo42
Merc:  7Tau58 R - 2:34' (-) [ 9th house] [d] -0.099  -  House cusp  3: 24Lib56
Nort: 11Aqu19 R + 0:00' (R) [ 6th house] [-] -0.052  -  House cusp 11: 23Gem40
Asce: 20Leo42   + 0:00'     [ 1st house]     +368.4  -  House cusp 12: 21Can22
Midh: 25Tau26   + 0:00'     [10th house]     +351.2
"""

NATAL_A = """Astrolog 7.70 chart for Tue May 15, 1990 12:30pm (ST Zone 6W)  97:37W  0:00N

  1:     Sun (Tau) Con (Tau) Midheaven  - orb: +0:47' - power: 20.28
  2:     Sun (Tau) Squ (Leo) Ascendant  - orb: +3:31' - power: 11.17
  3:     Sun (Tau) Tri (Cap) Saturn     - orb: -0:35' - power: 11.12
  4: Ascenda (Leo) Squ (Tau) Midheaven  - orb: +2:44' - power:  8.52
 18:  North N [Aqu] Sex (Can) Ascendant  - orb: -1:43' - power:  1.02
"""

TRANSIT_A = """  1: trans   Pluto (Aqu) Con natal [Aqu] Moon     - orb: 1:30' - power: 253.28
  2: trans  Neptune (Ari) Sex natal [Aqu] Moon     - orb: 0:53' - power: 147.17
  5: trans   Venus [Sco] Sex natal [Vir] North Node - orb: 0:12' - power:  6.05
"""

SYNASTRY_A = """  1:     Sun (Tau) Con with (Tau) Sun       - orb: +0:00' - power: 30.00
  2: Midheav (Tau) Con with (Tau) Sun        - orb: +0:47' - power: 20.28
"""


def test_parse_positions():
    pos = astrolog.parse_positions(NATAL_V)
    assert len(pos) == 5
    sun = pos[0]
    assert sun.body == "Sun" and sun.deg == 24 and sun.sign == "Tau"
    assert sun.house == 9 and sun.retro is False
    merc = pos[1]
    assert merc.body == "Merc" and merc.retro is True and merc.house == 9
    nort = pos[2]
    assert nort.body == "North Node" and nort.retro is True
    assert pos[4].body == "Midheaven" and pos[4].house == 10


def test_parse_natal_aspects():
    aspects = astrolog.parse_aspects(NATAL_A)
    assert len(aspects) == 5
    a1 = aspects[0]
    assert (a1.body1, a1.kind, a1.body2, a1.power) == ("Sun", "Con", "Midheaven", 20.28)
    a4 = aspects[3]
    assert a4.body1 == "Ascendant" and a4.kind == "Squ" and a4.body2 == "Midheaven"
    a18 = aspects[4]
    assert a18.body1 == "North Node" and a18.kind == "Sex"


def test_parse_transit_aspects():
    aspects = astrolog.parse_aspects(TRANSIT_A)
    assert len(aspects) == 3
    a1 = aspects[0]
    assert a1.body1 == "Pluto" and a1.sign1 == "Aqu"
    assert a1.kind == "Con" and a1.body2 == "Moon"
    assert a1.orb == "1:30'" and a1.power == 253.28
    a5 = aspects[2]
    assert a5.body1 == "Venus" and a5.body2 == "North Node"


def test_parse_synastry_aspects():
    aspects = astrolog.parse_aspects(SYNASTRY_A)
    assert len(aspects) == 2
    assert aspects[0].body1 == "Sun" and aspects[0].kind == "Con"
    assert aspects[0].power == 30.0
    assert aspects[1].body1 == "Midheaven"


def test_moon_mansions():
    assert "mansion 1" in lore.moon_mansion(5, "Ari")
    assert "mansion 18" in lore.moon_mansion(15, "Sco")
    assert "mansion 28" in lore.moon_mansion(25, "Pis")
    assert "mansion 11" in lore.moon_mansion(10, "Leo")


def test_sign_lore():
    text = lore.sign_lore("Sco")
    assert "Water" in text and "Geburah" in text
    assert "Nun" in text and "Death" in text
    text = lore.sign_lore("Leo")
    assert "Tiphareth" in text


def test_planet_lore():
    assert "Tiphareth" in lore.planet_lore("Sun")
    assert "Binah" in lore.planet_lore("Saturn")
    assert "YHVH Elohim" in lore.planet_lore("Saturn")


def test_person_round_trip_requires_astrolog():
    """if the binary is present, exercise create_chart -> parse_chart_header."""
    import shutil
    if not shutil.which(astrolog.ASTROLOG):
        return
    import tempfile
    person = astrolog.Person(name="Test", city="Nowhere", year=1990, month=5,
                             day=15, time="12:30PM", dst=0, zone="6W",
                             lon="97W37", lat="30N28")
    with tempfile.TemporaryDirectory() as d:
        out = astrolog.create_chart(person, Path(d) / "test.chart")
        back = astrolog.parse_chart_header(out)
        assert back.name == "Test"
        assert (back.year, back.month, back.day) == (1990, 5, 15)
        assert back.zone == "6W" and back.dst == 0
        assert back.lon == "97W37" and back.lat == "30N28"
