"""regression: transit display double-parse bug.

show_person() was passing parse_aspects() output (a list) back into
render_aspects(), which calls parse_aspects() again — a list has no
.splitlines(). 2026-10-18, found by the acceptance suite (john's add-person
crash was unrelated but the same review prompted this deep pass).
"""
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from astro_tui import app as app_module  # noqa: E402
from astro_tui import astrolog  # noqa: E402

from tests.test_acceptance import HAS_ASTROLOG, app, seed_person  # noqa: E402,F401


def test_transits_are_parsed_once_not_twice(app):
    """feed a raw string through show_person and assert the transit pane
    gets rendered text, and that render_aspects never receives a list."""
    if not HAS_ASTROLOG:
        return
    fake_transits = (
        "  1: trans   Pluto (Aqu) Con natal [Aqu] Moon     - orb: 1:30' - power: 253.28\n"
        "  2: trans  Neptune (Ari) Sex natal [Aqu] Moon     - orb: 0:53' - power: 147.17\n"
    )
    calls = []

    real_parse = astrolog.parse_aspects

    def spy_parse(text):
        if isinstance(text, list):
            raise AssertionError(
                "render_aspects received a list — the double-parse bug is back")
        calls.append(text)
        return real_parse(text)

    with patch.object(astrolog, "transits_today", return_value=fake_transits), \
         patch.object(astrolog, "parse_aspects", side_effect=spy_parse):
        import asyncio

        async def run():
            async with app.run_test(size=(120, 40)) as pilot:
                person = await seed_person(app)
                table = app.query_one("#people-table")
                table.focus()
                await pilot.press("enter")
                await pilot.pause()
                pane = app.query_one("#transits-out").content
                return person, pane

        person, pane = asyncio.run(run())

    assert "253.28" in str(pane)
    assert "sorted by influence" in str(pane)
    # one parse per render_aspects call, all with strings
    assert all(isinstance(t, str) for t in calls)
    assert person.path.exists()
