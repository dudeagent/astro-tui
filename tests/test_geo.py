"""unit tests for the geo helper (no network — search_cities is patched out)."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from astro_tui import geo  # noqa: E402


def test_lat_lon_formatting():
    assert geo.to_astrolog_lat(30.5318) == "30N32"
    assert geo.to_astrolog_lat(-33.87) == "33S52"
    assert geo.to_astrolog_lat(0.0) == "0N00"
    assert geo.to_astrolog_lon(-97.6261) == "97W38"
    assert geo.to_astrolog_lon(151.2093) == "151E13"


def test_format_zone():
    assert geo.format_zone(-6) == "6W"
    assert geo.format_zone(-5) == "5W"
    assert geo.format_zone(0) == "0E"
    assert geo.format_zone(1) == "1E"
    assert geo.format_zone(5.5) == "5E30"      # india
    assert geo.format_zone(-5.5) == "5W30"


def test_parse_time():
    assert geo.parse_time("7:00AM") == (7, 0)
    assert geo.parse_time("12:30PM") == (12, 30)
    assert geo.parse_time("12:00AM") == (0, 0)
    assert geo.parse_time("7PM") == (19, 0)
    assert geo.parse_time("19:30") == (19, 30)
    with pytest.raises(ValueError):
        geo.parse_time("whenever")
    with pytest.raises(ValueError):
        geo.parse_time("25:00")


def test_tz_to_astrolog_chicago_summer_is_dst():
    # austin, 1990-05-15 12:30pm CDT -> UTC-5, dst=1
    assert geo.tz_to_astrolog("America/Chicago", 1990, 5, 15, "12:30PM") == (1, "5W")


def test_tz_to_astrolog_chicago_winter_no_dst():
    # 1990-01-15 12:30pm CST -> UTC-6, dst=0
    assert geo.tz_to_astrolog("America/Chicago", 1990, 1, 15, "12:30PM") == (0, "6W")


def test_tz_to_astrolog_london_winter_and_summer():
    assert geo.tz_to_astrolog("Europe/London", 1990, 1, 15, "12:30PM") == (0, "0E")
    assert geo.tz_to_astrolog("Europe/London", 1990, 7, 15, "12:30PM") == (1, "1E")  # BST = UTC+1


def test_tz_to_astrolog_bad_inputs():
    with pytest.raises(ValueError):
        geo.tz_to_astrolog("Mars/Olympus_Mons", 1990, 5, 15, "12:00PM")
    with pytest.raises(ValueError):
        geo.tz_to_astrolog("America/Chicago", 1990, 5, 15, "whenever")


def test_search_cities_parses_and_sorts(monkeypatch):
    payload = {"results": [
        {"name": "springfield", "admin1": "Missouri", "country": "United States",
         "latitude": 37.2, "longitude": -93.3, "timezone": "America/Chicago",
         "population": 169000},
        {"name": "springfield", "admin1": "Illinois", "country": "United States",
         "latitude": 39.8, "longitude": -89.65, "timezone": "America/Chicago",
         "population": 111000},
    ]}

    import io
    import json as _json

    import astro_tui.geo as g

    monkeypatch.setattr(g.urllib.request, "urlopen", lambda *a, **k:
        io.TextIOWrapper(io.BytesIO(_json.dumps(payload).encode())))
    results = g.search_cities("springfield")
    assert [c.admin1 for c in results] == ["Missouri", "Illinois"]  # sorted by population
    assert results[0].timezone == "America/Chicago"
    assert "springfield, Missouri, United States" in results[0].label


def test_search_cities_offline_returns_empty(monkeypatch):
    import astro_tui.geo as g

    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(g.urllib.request, "urlopen", boom)
    assert g.search_cities("austin") == []
    assert g.search_cities("") == []
