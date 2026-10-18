"""city search + timezone/dst + coord helpers.

astrolog has no timezone database, so the form needs an explicit utc
offset ("6W") and dst flag. this module resolves a city name
(open-meteo geocoding api, no key required) into everything astrolog
wants: decimal coords in astrolog string form, the timezone name, and
the correct dst flag + zone string for the given birth date/time.
"""

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


@dataclass
class City:
    name: str
    admin1: str      # state/region, may be ""
    country: str
    lat: float
    lon: float
    timezone: str    # IANA name, e.g. "America/Chicago"
    population: int = 0

    @property
    def label(self) -> str:
        region = f", {self.admin1}" if self.admin1 else ""
        pop = f" · {self.population:,}" if self.population else ""
        return f"{self.name}{region}, {self.country}{pop}"


def search_cities(query: str, count: int = 6, timeout: float = 10.0) -> list[City]:
    """look up cities by name. returns [] on network error (offline-safe)."""
    query = query.strip()
    if len(query) < 2:
        return []
    url = f"{GEOCODE_URL}?{urllib.parse.urlencode({'name': query, 'count': count})}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
    except (OSError, ValueError):
        return []
    results = [
        City(
            name=r.get("name", ""),
            admin1=r.get("admin1", "") or "",
            country=r.get("country", "") or "",
            lat=float(r.get("latitude", 0.0)),
            lon=float(r.get("longitude", 0.0)),
            timezone=r.get("timezone", "") or "",
            population=int(r.get("population", 0) or 0))
        for r in data.get("results", [])
    ]
    results.sort(key=lambda c: -c.population)
    return results


def _dms(value: float, pos_hemi: str, neg_hemi: str) -> str:
    hemi = pos_hemi if value >= 0 else neg_hemi
    value = abs(value)
    deg, minutes = int(value), round((value - int(value)) * 60)
    if minutes == 60:
        deg, minutes = deg + 1, 0
    return f"{deg}{hemi}{minutes:02d}"


def to_astrolog_lat(value: float) -> str:
    """30.532 -> '30N32' (degrees + minutes, N/S)."""
    return _dms(value, "N", "S")


def to_astrolog_lon(value: float) -> str:
    """-97.626 -> '97W38' (degrees + minutes, W/E)."""
    return _dms(value, "E", "W")


def format_zone(offset_hours: float) -> str:
    """utc offset in hours -> astrolog zone string ('6W' west-positive)."""
    offset_hours = round(offset_hours * 2) / 2  # nearest half-hour
    sign = "W" if offset_hours < 0 else "E"
    mag = abs(offset_hours)
    whole = int(mag)
    minutes = round((mag - whole) * 60)
    frac = f"{minutes:02d}" if minutes else ""
    return f"{whole}{sign}{frac}"


_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])?$")


def parse_time(s: str) -> tuple[int, int]:
    """'7:00AM' / '19:30' -> (hour24, minute). raises ValueError."""
    m = _TIME_RE.match(s.strip())
    if not m:
        raise ValueError(f"can't parse time {s!r} (try 7:00AM)")
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm:
        hour = hour % 12 + (12 if ampm == "pm" else 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time out of range: {s!r}")
    return hour, minute


def tz_to_astrolog(tz_name: str, year: int, month: int, day: int,
                   time_str: str) -> tuple[int, str]:
    """figure out (dst flag, zone string) for a birth moment in a tz.

    returns (1, '5W') if daylight saving was in effect at that local
    time (fold=0 for ambiguous fall-back times). raises ValueError for
    unknown timezones or bad time strings.
    """
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        raise ValueError(f"unknown timezone {tz_name!r}") from None
    hour, minute = parse_time(time_str)
    aware = datetime(year, month, day, hour, minute, tzinfo=tz)
    offset_hours = aware.utcoffset().total_seconds() / 3600
    return 1 if aware.dst() else 0, format_zone(offset_hours)
