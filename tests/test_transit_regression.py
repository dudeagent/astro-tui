"""regression: transit display must parse astrolog output exactly once.

The original bug: show_person() passed parse_aspects() output (a list) back
into render_aspects(), which re-parses it — a list has no .splitlines() and
the whole transit tab crashed. The transit tab has since been rebuilt around
parse_transit_events() + a DataTable, so the modern equivalent regression is:
selecting a person must call parse_transit_events() exactly once and
populate the transit table. 2026-10-18.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from astro_tui import app as app_module  # noqa: E402
from astro_tui import astrolog  # noqa: E402

from tests.test_acceptance import HAS_ASTROLOG, app, seed_person  # noqa: E402,F401


def test_transits_are_parsed_once_not_twice(app):
    """selecting a person parses each month's transit output exactly once and
    populates the transit DataTable. the transit tab scans a window of
    months (transits_events_next_months), so that's one parse call per
    month in the window — 3 by default. the original regression (parsed
    data being fed back into a parser) would double this to 6+ calls."""
    if not HAS_ASTROLOG:
        return
    calls = []

    real_parse = astrolog.parse_transit_events

    def spy_parse(text):
        calls.append(text)
        return real_parse(text)

    with patch.object(astrolog, "parse_transit_events", side_effect=spy_parse):
        import asyncio

        async def run():
            async with app.run_test(size=(120, 40)) as pilot:
                person = await seed_person(app)
                table = app.query_one("#people-table")
                table.focus()
                await pilot.press("enter")
                await pilot.pause()
                transit_table = app.query_one("#transit-table")
                return person, transit_table

        person, transit_table = asyncio.run(run())

    assert transit_table.row_count > 0
    # one parse per month in the scan window (3 = transits_events_next_months
    # default); the old double-parse bug would show up as 6+ calls
    assert len(calls) == 3, (
        f"expected exactly one parse_transit_events call per month (3), "
        f"got {len(calls)}")
    assert all(isinstance(t, str) for t in calls)
    assert person.path.exists()
