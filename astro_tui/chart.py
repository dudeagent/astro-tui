"""custom terminal astrology chart renderer.

draws a full chart wheel — zodiac sign ring, house cusps + numbers,
planet glyphs and aspect lines — as colored rich text that scales to
whatever grid size the terminal gives it. this replaces the BMP image
wheel (astrolog -Xb), which rendered at a fixed pixel scale, couldn't
grow with the pane, and showed no labels.

layout: longitude 0 (aries) sits at 9 o'clock, longitude increases
counterclockwise (taurus below-left, cancer at the bottom, capricorn at
the top) — the standard chart orientation with the ascendant on the left.
"""
import math

from rich.text import Text
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widget import Widget

from . import astrolog

CELL_ASPECT = 2.0  # a terminal cell is ~1 col wide x ~2 rows tall


# sign glyphs colored by element
_ELEMENTS = ("fire", "earth", "air", "water")
ELEMENT_STYLE = {"fire": "red", "earth": "green",
                 "air": "yellow", "water": "blue"}


def sign_element_style(sign_index: int) -> str:
    return ELEMENT_STYLE[_ELEMENTS[sign_index % 4]]


def _band_char(t: float) -> str:
    """line character for a direction angle t (degrees, mod 180)."""
    if t < 22.5 or t >= 157.5:
        return "─"
    if t < 67.5:
        return "╲"
    if t < 112.5:
        return "│"
    return "╱"


def _dir_char(dx: float, dy: float) -> str:
    """character for a line heading dx (cols) x dy (rows)."""
    return _band_char(math.degrees(math.atan2(dy * CELL_ASPECT, dx)) % 180)


def _ring_char(x: float, y: float, cx: float, cy: float) -> str:
    """character for a point on a circle: the tangent direction there."""
    ux, uy = x - cx, (y - cy) * CELL_ASPECT
    if ux == 0 and uy == 0:
        return "─"
    return _band_char((math.degrees(math.atan2(uy, ux)) + 90) % 180)


def _pt(lon: float, r: float, cx: float, cy: float) -> tuple[float, float]:
    """polar -> grid coords (r in unit space, 1 unit = 1 column)."""
    t = math.radians(lon)
    return cx - r * math.cos(t), cy + r * math.sin(t) / CELL_ASPECT


def _ang_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def _body_key(name: str) -> str:
    """normalize a body name so position lines ('Merc', 'Nort', 'Asce',
    'Midh') match aspect lines ('Mercury', 'North Node', ...)."""
    n = "".join(c for c in name.lower() if c.isalpha())
    for k in ("north", "south", "ascendant", "midheaven", "chiron"):
        if n.startswith(k[:4]):
            return k
    return n[:4]


class _Grid:
    """a w x h cell grid; the last (char, style) written to a cell wins."""

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.cells: list[list[tuple[str, str] | None]] = \
            [[None] * w for _ in range(h)]

    def put(self, x: float, y: float, ch: str, style: str) -> None:
        xi, yi = round(x), round(y)
        if 0 <= xi < self.w and 0 <= yi < self.h:
            self.cells[yi][xi] = (ch, style)

    def put_label(self, lon: float, r: float, cx: float, cy: float,
                  label: str, style: str) -> None:
        """center a 1-2 char label at (lon, r)."""
        x, y = _pt(lon, r, cx, cy)
        if len(label) == 1:
            self.put(x, y, label, style)
        else:
            self.put(x - 0.5, y, label[0], style)
            self.put(x + 0.5, y, label[1], style)

    def seg(self, x0: float, y0: float, x1: float, y1: float,
            style: str, skip_ends: float = 0.0) -> None:
        """draw a line segment (character chosen by its slope)."""
        dx, dy = x1 - x0, y1 - y0
        n = max(2, int(max(abs(dx), abs(dy)) * 2))
        for i in range(n + 1):
            t = i / n
            if skip_ends and (t < skip_ends or t > 1 - skip_ends):
                continue
            self.put(x0 + t * dx, y0 + t * dy, _dir_char(dx, dy), style)

    def radial(self, lon: float, r0: float, r1: float, cx: float,
               cy: float, style: str, skip_ends: float = 0.0) -> None:
        x0, y0 = _pt(lon, r0, cx, cy)
        x1, y1 = _pt(lon, r1, cx, cy)
        self.seg(x0, y0, x1, y1, style, skip_ends)

    def circle(self, r: float, cx: float, cy: float, style: str) -> None:
        """a ring: solve for x per row and y per col so both shallow and
        steep parts render without gaps."""
        for y in range(self.h):
            uy = (y - cy) * CELL_ASPECT
            disc = r * r - uy * uy
            if disc < 0:
                continue
            sx = math.sqrt(disc)
            for x in (cx - sx, cx + sx):
                self.put(x, y, _ring_char(x, y, cx, cy), style)
        for x in range(self.w):
            ux = x - cx
            disc = r * r - ux * ux
            if disc < 0:
                continue
            sy = math.sqrt(disc) / CELL_ASPECT
            for y in (cy - sy, cy + sy):
                self.put(x, y, _ring_char(x, y, cx, cy), style)

    def text(self) -> Text:
        out = Text()
        for row in self.cells:
            for cell in row:
                if cell is None:
                    out.append(" ")
                else:
                    out.append(cell[0], style=cell[1])
            out.append("\n")
        return out


def render_wheel(positions: list, cusps: dict, aspects: list,
                 width: int, height: int, partner: list | None = None) -> Text:
    """draw the chart wheel for `positions` (natal or synastry bi-wheel when
    `partner` is given) at width x height terminal cells.

    positions: astrolog.Position list; cusps: {house: (deg, sign, minute)};
    aspects: astrolog.Aspect list; partner: second chart's positions
    (bi-wheel: partner planets on the outer ring, inter-chart aspect lines
    connecting the two rings).
    """
    w, h = width, height
    if w < 20 or h < 9:
        return Text("wheel needs a bigger pane", style="grey50")
    g = _Grid(w, h)
    cx, cy = (w - 1) / 2, (h - 1) / 2
    r_max = min((w - 3) / 2, (h - 3) / 2 * CELL_ASPECT)
    ring_w = max(2.0, r_max * 0.14)
    r_out, r_in = r_max, r_max - ring_w
    r_hnum = r_in - ring_w * 0.9
    if partner:
        # bi-wheel: partner planets on the outer ring (closer to the
        # zodiac), natal planets further in; aspect lines connect the two
        r_partner = r_hnum - ring_w * 1.6
        r_planet = r_hnum - ring_w * 3.4
        r_aspect = None  # aspect endpoints sit on each body's own ring
    else:
        r_planet = r_hnum - ring_w * 2.4
        r_aspect = r_in * 0.4
        r_partner = None

    by_key = {_body_key(p.body): p for p in positions}
    partner_by_key = {_body_key(p.body): p for p in (partner or [])}

    # house cusp spokes (grey, from the inner area out to the zodiac ring)
    if cusps:
        cusp_lons = {}
        for n, (deg, sign, minute) in cusps.items():
            cusp_lons[n] = astrolog.SIGNS.index(sign[:3]) * 30 + deg + minute / 60.0
        r_from = r_planet if partner else r_aspect
        for lon in cusp_lons.values():
            g.radial(lon, r_from, r_in, cx, cy, "grey42")

    # aspect lines (colored by aspect). single chart: both ends on the
    # aspect circle inside the planet ring. bi-wheel: natal end on the
    # natal ring, partner end on the partner ring.
    for a in aspects:
        style = astrolog.aspect_color(a.kind)
        p1, p2 = by_key.get(_body_key(a.body1)), by_key.get(_body_key(a.body2))
        if p1 is None or p2 is None:
            continue
        if partner:
            q1, q2 = partner_by_key.get(_body_key(a.body1)), \
                partner_by_key.get(_body_key(a.body2))
            if q1 is None or q2 is None:
                continue
            x0, y0 = _pt(p1.lon, r_planet, cx, cy)
            x1, y1 = _pt(q2.lon, r_partner, cx, cy)
        else:
            x0, y0 = _pt(p1.lon, r_aspect, cx, cy)
            x1, y1 = _pt(p2.lon, r_aspect, cx, cy)
        g.seg(x0, y0, x1, y1, style)

    # planet pointer lines: from each planet's ring slot outward to the
    # house-number band, showing the exact degree it points to (single
    # chart only — bi-wheels are too busy for them)
    if not partner:
        placed: list[tuple[float, float]] = []
        for pos in sorted(positions, key=lambda p: p.lon):
            r_here = r_planet
            for other_lon, other_r in placed:
                if _ang_diff(pos.lon, other_lon) < 8 and \
                        abs(r_here - other_r) < 1:
                    r_here = r_planet - ring_w
            placed.append((pos.lon, r_here))
            g.radial(pos.lon, r_here + 1.3, r_hnum, cx, cy,
                     f"dim {astrolog.planet_color(pos.body)}")

    # zodiac ring + sign glyphs + sign boundary ticks
    g.circle(r_out, cx, cy, "grey58")
    g.circle(r_in, cx, cy, "grey58")
    for k, sign in enumerate(astrolog.SIGNS):
        g.put_label(k * 30 + 15, (r_in + r_out) / 2, cx, cy,
                    astrolog.SIGN_GLYPHS[sign], sign_element_style(k))
        g.radial(k * 30, r_in, r_out, cx, cy, "grey42")

    # house numbers between adjacent cusps (natal chart only)
    if cusps:
        nums = sorted(cusp_lons)
        for i, n in enumerate(nums):
            lon0, lon1 = cusp_lons[n], cusp_lons[nums[(i + 1) % len(nums)]]
            mid = (lon0 + _ang_diff(lon0, lon1) * (1 if lon1 > lon0 else -1)) % 360
            g.put_label(mid, (r_hnum + r_in) / 2, cx, cy,
                        str(n), "grey50")

    # planet glyphs (staggered inward when crowded), retro marker
    def _planets(plist, r0, style_mod: str = "") -> None:
        placed: list[tuple[float, float]] = []
        for pos in sorted(plist, key=lambda p: p.lon):
            r_here = r0
            for other_lon, other_r in placed:
                if _ang_diff(pos.lon, other_lon) < 8 and \
                        abs(r_here - other_r) < 1:
                    r_here = r0 - ring_w
            placed.append((pos.lon, r_here))
            style = f"{style_mod}{astrolog.planet_color(pos.body)}"
            g.put_label(pos.lon, r_here, cx, cy,
                        astrolog.planet_glyph(pos.body), style)
            if pos.retro:
                g.put_label(pos.lon, r_here - 1.1, cx, cy, "R", "grey50")

    _planets(positions, r_planet)
    if partner:
        _planets(partner, r_partner, "bold ")
    return g.text()


class ChartWheel(Widget):
    """a scalable terminal chart wheel (sign ring + houses + planets +
    aspects). renders at whatever size its container gives it, so it fills
    the pane instead of sitting at a fixed image scale. click it (or 'm')
    to maximize full-screen."""

    DEFAULT_CSS = """
    ChartWheel { height: 50%; }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.positions: list = []
        self.cusps: dict = {}
        self.aspects: list = []
        self.partner_positions: list = []

    def render(self) -> Text:
        if not self.positions:
            return Text("pick a person (enter or click)", style="grey50")
        w, h = self.size.width or 40, self.size.height or 20
        return render_wheel(self.positions, self.cusps, self.aspects,
                            w, h, partner=self.partner_positions or None)

    def on_click(self, event) -> None:
        if not self.positions:
            return
        # inside MaximizeScreen a click dismisses it instead of stacking
        if type(self.screen).__name__ == "MaximizeScreen":
            self.screen.dismiss()
        else:
            self.app.push_screen(MaximizeScreen(self))


class MaximizeScreen(ModalScreen):
    """full-screen modal showing one chart wheel at full terminal size.
    click anywhere or press escape/q/m to close."""

    BINDINGS = [Binding("escape", "dismiss", "close"),
                Binding("q", "dismiss", "close"),
                Binding("m", "dismiss", "close")]

    def __init__(self, source: ChartWheel) -> None:
        super().__init__()
        self.source = source

    def compose(self):
        view = ChartWheel(id="maximized-wheel")
        view.positions = self.source.positions
        view.cusps = self.source.cusps
        view.aspects = self.source.aspects
        view.partner_positions = self.source.partner_positions
        yield view
