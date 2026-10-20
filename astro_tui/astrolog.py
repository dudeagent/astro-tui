"""wrapper around the astrolog cli: run it, write chart files, parse output."""

import json
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

ASTROLOG = os.environ.get("ASTROLOG_BIN", "astrolog")

# a transit is "powerful" when our estimated power score (0..1, see
# TransitEvent.power) clears this bar. sane default: Saturn conj (~0.7),
# Pluto square (~0.7) and Uranus trine (~0.64) flag; Moon trine (~0.24) doesn't.
POWERFUL_THRESHOLD = float(os.environ.get("ASTRO_TUI_POWERFUL_THRESHOLD", "0.5"))

SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
         "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn",
              "Aquarius", "Pisces"]

# unicode glyphs + rich color styles for the graphical aspect view.
# john's ask: symbols for the signs/planets and use colors.
PLANET_GLYPHS = {"Sun": "☉", "Moon": "☽", "Mercury": "☿",
                 "Venus": "♀", "Mars": "♂", "Jupiter": "♃",
                 "Saturn": "♄", "Uranus": "♅", "Neptune": "♆",
                 "Pluto": "♇", "North Node": "☊", "South Node": "☋",
                 "Chiron": "⚷", "Ascendant": "AC", "Midheaven": "MC"}
SIGN_GLYPHS = dict(zip(SIGNS, "♈♉♊♋♌♍♎♏♐♑♒♓"))
ASPECT_GLYPHS = {"Con": "☌", "Opp": "☍", "Tri": "△",
                 "Squ": "□", "Sex": "⚹", "Ses": "⚻",
                 "Sem": "⚼", "Qui": "⚺"}
PLANET_COLORS = {"Sun": "yellow", "Moon": "white", "Mercury": "green",
                 "Venus": "cyan", "Mars": "red", "Jupiter": "blue",
                 "Saturn": "grey70", "Uranus": "magenta",
                 "Neptune": "sky_blue1", "Pluto": "purple",
                 "North Node": "orange1", "South Node": "orange1",
                 "Chiron": "grey50", "Ascendant": "bright_white",
                 "Midheaven": "bright_white"}
ASPECT_COLORS = {"Con": "bold red", "Opp": "red", "Tri": "green",
                 "Squ": "orange1", "Sex": "magenta", "Ses": "grey50",
                 "Sem": "grey50", "Qui": "grey50"}


def planet_glyph(name: str) -> str:
    return PLANET_GLYPHS.get(name, name[:2])


def sign_glyph(abbr: str) -> str:
    """'Tau'/'tau'/'taurus' -> ♉; unknown abbrs pass through."""
    key = abbr[:3].capitalize()
    return SIGN_GLYPHS.get(key, key)


def aspect_glyph(kind: str) -> str:
    return ASPECT_GLYPHS.get(kind[:3].capitalize(), kind)


def planet_color(name: str) -> str:
    return PLANET_COLORS.get(name, "white")


def aspect_color(kind: str) -> str:
    return ASPECT_COLORS.get(kind[:3].capitalize(), "grey50")


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
        d.pop("path", None)  # a stray "path" key in json would collide with path=path below
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


def wheel_bitmap(chart: Path, partner: Path | None = None,
                 tmp_dir: Path | None = None, width: int = 2048) -> bytes:
    """astrolog's graphic wheel as BMP bytes. with a partner chart it
    draws the synastry overlay (-r0 file1 file2 -w).

    arg order matters: -r0 <f1> <f2> must come before -Xb0/-Xo, or astrolog
    tries to open the switches as chart files.

    'width' is the horizontal pixel size of the rendered graphic (-Xw);
    default 2048 so the wheel is high-resolution and can be maximized
    full-screen without being a tiny upscaled blob.
    """
    if tmp_dir is None:
        tmp_dir = Path(tempfile.mkdtemp(prefix="astro-tui-"))
    out = tmp_dir / "wheel.bmp"
    args = (["-r0", str(chart), str(partner)] if partner
            else ["-i", str(chart)])
    run(args + [f"-Xw", str(width), "-Xb0", "-Xo", str(out), "-w"])
    data = out.read_bytes()
    out.unlink(missing_ok=True)
    return data


def parse_bmp(data: bytes) -> tuple[list[list[tuple[int, int, int]]], int, int]:
    """parse a 24-bit uncompressed Windows BMP into RGB rows + width/height.
    BMP rows are bottom-up and padded to 4-byte boundaries."""
    if data[:2] != b"BM":
        raise ValueError("not a BMP file")
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp != 24:
        raise ValueError(f"only 24-bit BMPs supported, got {bpp}bpp")
    row_size = ((width * 3 + 3) // 4) * 4
    rows: list[list[tuple[int, int, int]]] = []
    for y in range(abs(height)):
        start = offset + y * row_size
        row = [tuple(data[start + x * 3:start + x * 3 + 3][::-1])
               for x in range(width)]
        rows.append(row)  # bottom-up; caller indexes by source row
    if height > 0:
        rows.reverse()  # top-down
    return rows, width, abs(height)


def render_bmp_ansi(data: bytes, cols: int = 44, rows: int = 24) -> str:
    """render a 24-bit BMP as an ANSI-colored unicode-halfblock string.

    nearest-neighbor downsample to cols x 2*rows pixels, then each output
    row emits one '▀' char whose fg = top pixel and bg = bottom pixel —
    double vertical resolution without any image dependency.
    """
    px, w, h = parse_bmp(data)
    out = []
    for r in range(rows):
        sy0 = min(h - 1, r * h // rows)
        sy1 = min(h - 1, (2 * r + 1) * h // (2 * rows))
        line = []
        for c in range(cols):
            sx = min(w - 1, c * w // cols)
            top = px[sy0][sx]
            bot = px[sy1][sx]
            line.append(f"\x1b[38;2;{top[0]};{top[1]};{top[2]};48;2;"
                        f"{bot[0]};{bot[1]};{bot[2]}m▀")
        out.append("".join(line) + "\x1b[0m")
    return "\n".join(out)


# two wheel sizes are generated per chart (john: "generate two sizes and
# make the larger one 80% screen size and centered"): a small one for the
# in-tab wheel views and a large high-res one for the full-screen maximize.
WHEEL_SMALL_SIZE = 760
WHEEL_LARGE_SIZE = 2048


def wheel_image(chart: Path, partner: Path | None = None,
                width: int = WHEEL_LARGE_SIZE):
    """astrolog's graphic wheel as a PIL image (for textual-image display).
    same -Xb0/-Xo/-w invocation as wheel_bitmap; returns a Pillow Image.

    'width' passes through to wheel_bitmap (astrolog -Xw). use the large
    size when a wheel is about to be maximized full-screen, the small one
    for the in-tab wheel views.
    """
    from PIL import Image
    import io
    data = wheel_bitmap(chart, partner, width=width)
    return Image.open(io.BytesIO(data))


def natal_grid(chart: Path) -> str:
    """astrolog's aspect grid (-g): the matrix view of every body pair with
    its exact aspect glyph, orb degrees and declination info.
    """
    return run(["-i", str(chart), "-g"])


def transits_graph(chart: Path, month: int, year: int) -> dict[str, list[int | None]]:
    """parse astrolog's -V <month> <year> monthly transit-power graph.

    each row is 'T.Body Kind N.Body' followed by 2 chars per day of the
    month (a digit pair like '55' = power 5 for that day; '|' and spaces
    mean the transit is out of orb that day -> None). returns a dict of
    label -> per-day values, e.g. {"Sun Opp Moo": [None, ...]}.
    """
    text = run(["-i", str(chart), "-V", str(month), str(year)])
    out: dict[str, list[int | None]] = {}
    for line in text.splitlines():
        m = re.match(r"^T\.(\w+)\s+(\w+)\s+N\.(\w+)\s*(.*)$", line)
        if not m:
            continue
        label = f"{m.group(1)} {m.group(2)} {m.group(3)}"
        raw = m.group(4)
        values: list[int | None] = []
        i = 0
        while i < len(raw):
            chunk = raw[i:i + 2]
            if chunk[0].isdigit():
                values.append(int(chunk[0]))
            elif chunk[0] == "|":
                values.append(None)
                i += 2
                # resync: skip whitespace pairs after the divider
                while i + 1 < len(raw) and raw[i:i + 2].isspace():
                    values.append(None)
                    i += 2
                continue
            else:
                values.append(None)
            i += 2
        out[label] = values
    return out


def find_graph_row(graph: dict[str, list[int | None]],
                   ev: "TransitEvent") -> list[int | None] | None:
    """locate the -V graph row matching a transit event (T-body kind
    natal-body, abbreviated to 3 letters like astrolog does)."""
    key = f"{ev.body[:3]} {ev.kind[:3]} {ev.natal_body[:3]}"
    return graph.get(key)


def interpretations() -> str:
    """sign/house/planet/aspect meanings (-HI)."""
    return run(["-HI"])


def full_output(chart: Path) -> str:
    return run(["-i", str(chart), "-e"])
