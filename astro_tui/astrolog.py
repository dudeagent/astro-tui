"""wrapper around the astrolog cli: run it, write chart files, parse output."""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ASTROLOG = os.environ.get("ASTROLOG_BIN", "astrolog")

# a transit is "powerful" when our estimated power score (0..1, see
# TransitEvent.power) clears this bar. sane default: Saturn conj (~0.7),
# Pluto square (~0.7) and Uranus trine (~0.64) flag; Moon trine (~0.24) doesn't.
POWERFUL_THRESHOLD = float(os.environ.get("ASTRO_TUI_POWERFUL_THRESHOLD", "0.5"))

# person metadata lives next to the .chart file as json so the tui
# can rebuild forms without re-parsing astrolog's file format
import json

SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
         "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn",
              "Aquarius", "Pisces"]


class AstrologError(RuntimeError):
    pass


def run(args: list[str]) -> str:
    proc = subprocess.run(
        [ASTROLOG] + args, capture_output=True, text=True, timeout=120
    )
    if proc.returncode != 0:
        raise AstrologError(
            f"astrolog failed ({proc.returncode}): {proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout


@dataclass
class Person:
    name: str
    city: str
    year: int
    month: int
    day: int
    time: str          # "7:00AM"
    dst: int           # 0 or 1
    zone: str          # "6W" / "6E" style
    lon: str           # "97W37"
    lat: str           # "30N28"
    path: Path = None  # type: ignore[assignment]

    @property
    def summary(self) -> str:
        return f"{self.name} — {self.month}/{self.day}/{self.year} {self.time}, {self.city}"


def create_chart(p: Person, out_path: Path) -> Path:
    """write a chart file via astrolog -qb (explicit dst + zone, no tz db surprises)."""
    run([
        "-qb", str(p.month), str(p.day), str(p.year), p.time,
        str(p.dst), p.zone, p.lon, p.lat,
        "-zi", p.name, p.city,
        "-o", str(out_path),
    ])
    return out_path


def _norm_lonlat(tok: str) -> str:
    """normalize astrolog's '97:37W' back to the compact '97W37' form."""
    m = re.match(r"(\d+):(\d+)([NSEW])", tok)
    if m:
        return f"{m.group(1)}{m.group(3)}{m.group(2)}"
    return tok


def parse_chart_header(path: Path) -> Person:
    """recover Person metadata from a chart file's first lines."""
    meta = path.with_suffix(".json")
    if meta.exists():
        d = json.loads(meta.read_text())
        # BUGFIX: was `Person(path=d, **d)` — the json dict itself was
        # passed as path, so every form-saved person loaded with a dict
        # as .path, the table row key was str(dict), and selection
        # silently did nothing (john's "clicking does nothing" bug).
        return Person(**d, path=path)
    text = path.read_text()
    m = re.search(r"-qb\s+(\w{3})\s+(\d+)\s+(\d+)\s+(\d+:\d+\w*)\s+(\w+)\s+(\S+)\s+(\S+)\s+(\S+)", text)
    name = city = ""
    nm = re.search(r'-zi\s+"([^"]*)"\s+"?([^"\n]*)"?', text)
    if nm:
        name, city = nm.group(1), nm.group(2)
    if not m:
        raise AstrologError(f"can't parse chart file {path}")
    month = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
             "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}[m.group(1)]
    return Person(
        name=name or path.stem, city=city, month=month,
        day=int(m.group(2)), year=int(m.group(3)),
        time=m.group(4), dst=1 if m.group(5).startswith("DT") else 0,
        zone=m.group(6), lon=_norm_lonlat(m.group(7)), lat=_norm_lonlat(m.group(8)), path=path,
    )


def load_people(data_dir: Path) -> list[Person]:
    return sorted(
        (parse_chart_header(f) for f in data_dir.glob("*.chart")),
        key=lambda p: p.name.lower(),
    )


@dataclass
class Position:
    body: str
    deg: int
    sign: str
    house: int
    retro: bool


@dataclass
class Aspect:
    n: int
    body1: str
    sign1: str
    kind: str
    sign2: str
    body2: str
    orb: str
    power: float


@dataclass
class Transit(Aspect):
    pass


@dataclass
class TransitEvent:
    """an exact-time transit hit from astrolog -t <month> <year> output."""

    date: str
    time: str
    body: str
    body_sign: str
    kind: str
    natal_sign: str
    natal_body: str

    # astrolog doesn't emit a power value with -t output, so we estimate one
    # using the same ingredients its -a power model uses: aspect kind (conj
    # and opposition are strongest, trine/square next, minor aspects weak)
    # times the transiting body's "weight" (outer planets > sun/moon).
    _ASPECT_WEIGHT = {"Con": 1.0, "Opp": 0.9, "Tri": 0.8, "Squ": 0.7,
                      "Sex": 0.4, "Ses": 0.3, "Sem": 0.3, "Qui": 0.2,
                      "Inc": 0.2, "Qun": 0.2, "Qin": 0.2, "Ntv": 0.1,
                      "Wax": 0.3, "Wan": 0.3}
    _BODY_WEIGHT = {"Plu": 1.0, "Nep": 0.9, "Ura": 0.8, "Sat": 0.7,
                    "Jup": 0.6, "Mar": 0.4, "Sun": 0.5, "Moo": 0.3,
                    "Nor": 0.2, "Chi": 0.2}

    @property
    def power(self) -> float:
        """rough 0..1 power score for this transit hit (higher = stronger)."""
        kind = self.kind[:3].capitalize()
        body = self.body[:3].capitalize()
        return self._BODY_WEIGHT.get(body, 0.1) * self._ASPECT_WEIGHT.get(kind, 0.1)

    @property
    def powerful(self) -> bool:
        """true if this transit scores above the POWERFUL_THRESHOLD."""
        return self.power >= POWERFUL_THRESHOLD

    @property
    def label(self) -> str:
        return f"{self.body} {self.kind} natal {self.natal_body}"

    @property
    def sort_key(self) -> tuple:
        m, d, y = (int(x) for x in self.date.split("/"))
        # time is "H:MMam"/"H:MMpm" — split on the colon, not fixed-width slicing
        hh_str, mm_str = self.time[:-2].split(":")
        hh, mm = int(hh_str), int(mm_str)
        if self.time.lower().endswith("pm") and hh != 12:
            hh += 12
        if self.time.lower().endswith("am") and hh == 12:
            hh = 0
        return (y, m, d, hh, mm)


_RE_TRANSIT_EVENT = re.compile(
    r"^(\d{1,2})/\s*(\d{1,2})/\s*(\d{4})\s+(\d{1,2}:\d{2}[ap]m)\s+trans\s+"
    r"(\w+)\s+[\[(]?(\w{3})[\])]\s+(\w{3})\s+natal\s+[\[(]?(\w{3})[\])]\s+(.+)$")


def parse_transit_events(text: str) -> list[TransitEvent]:
    """parse the 'MM/DD/YYYY  h:mmam trans Body (Sig) Kind natal (Sig) Body' lines."""
    out = []
    for line in text.splitlines():
        m = _RE_TRANSIT_EVENT.match(line)
        if m:
            out.append(TransitEvent(
                date=f"{m.group(1)}/{m.group(2)}/{m.group(3)}",
                time=m.group(4), body=m.group(5), body_sign=m.group(6),
                kind=m.group(7), natal_sign=m.group(8), natal_body=m.group(9).strip()))
    return sorted(out, key=lambda e: e.sort_key)


_RE_POS = re.compile(
    r"^(\w{3,4})\s*:\s*(\d{1,2})([A-Za-z]{3})(\d{1,2})(\s+R)?.*?\[ *(\d+)(?:st|nd|rd|th) house\]")
# unified aspect parser: handles natal (-a), transit (-Tn), and
# synastry (-r0 -a) lines. bodies may be multi-word ("North Node"),
# signs appear in parens or brackets, "with"/"natal" markers optional.
_KINDS = r"Con|Squ|Opp|Tri|Sex|Ses|Sem|Qui|Inc|Qun|Qin|Ntv|Wax|Wan"
_RE_ASP = re.compile(
    r"^\s*(\d+):\s*(?:trans\s+)?(.*?)\s*[\[(](\w*)[\])]\s+"
    r"(" + _KINDS + r")\s+"
    r"(?:(?:with|natal)\s+)?[\[(](\w*)[\])]\s+(.+?)\s*"
    r"-\s+(?:orb|pos|neg):?\s+([+-]?[\d:']+)\s+-\s+power:\s+([\d.]+)")

_RE_HEADER = re.compile(r"Astrolog [\d.]+ chart for (.*)")


def chart_title(text: str) -> str:
    m = _RE_HEADER.search(text)
    return m.group(1).strip() if m else "chart"


def parse_positions(text: str) -> list[Position]:
    out = []
    for line in text.splitlines():
        m = _RE_POS.match(line)
        if m:
            body = {"Nort": "North Node", "Asce": "Ascendant", "Midh": "Midheaven"}.get(m.group(1), m.group(1))
            out.append(Position(body, int(m.group(2)), m.group(3).capitalize(),
                                int(m.group(6)), bool(m.group(5))))
    return out


def parse_aspects(text: str) -> list[Aspect]:
    """parse natal (-a), synastry (-r0 -a), or transit (-T) aspect lines."""
    # astrolog truncates some body names in aspect listings ("North N")
    fix = {"North N": "North Node", "Midheav": "Midheaven", "Ascenda": "Ascendant"}
    out = []
    for line in text.splitlines():
        m = _RE_ASP.match(line)
        if m:
            out.append(Aspect(int(m.group(1)), fix.get(m.group(2).strip(), m.group(2).strip()),
                              m.group(3), m.group(4), m.group(5),
                              fix.get(m.group(6).strip(), m.group(6).strip()), m.group(7),
                              float(m.group(8))))
    return out


def natal_positions(chart: Path) -> str:
    return run(["-i", str(chart), "-v"])


def natal_aspects(chart: Path) -> str:
    return run(["-i", str(chart), "-a"])


def wheel(chart: Path) -> str:
    return run(["-i", str(chart), "-w"])


def transits_today(chart: Path) -> str:
    """transits to natal, ordered by influence, for right now."""
    return run(["-i", str(chart), "-Tn"])


def transits_month(chart: Path, month: int, year: int) -> str:
    return run(["-i", str(chart), "-t", str(month), str(year)])


def transits_events_month(chart: Path, month: int, year: int) -> list[TransitEvent]:
    """exact-time transit hits for a month, parsed and sorted chronologically."""
    return parse_transit_events(transits_month(chart, month, year))


def transits_events_next_months(chart: Path, month: int, year: int,
                                months: int = 3) -> list[TransitEvent]:
    """exact-time transit hits for the next `months` months starting at
    (month, year), collected and sorted chronologically. used by the
    transits tab so powerful upcoming transits are visible ahead of time."""
    out: list[TransitEvent] = []
    m, y = month, year
    for _ in range(months):
        out.extend(transits_events_month(chart, m, y))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return sorted(out, key=lambda e: e.sort_key)


def synastry_grid(c1: Path, c2: Path) -> str:
    return run(["-r0", str(c1), str(c2), "-g"])


def synastry_aspects(c1: Path, c2: Path) -> str:
    return run(["-r0", str(c1), str(c2), "-a"])


def interpretations() -> str:
    """sign/house/planet/aspect meanings (-HI)."""
    return run(["-HI"])


def full_output(chart: Path) -> str:
    return run(["-i", str(chart), "-e"])
