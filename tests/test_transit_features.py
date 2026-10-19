"""tests for the new wheel + selectable-transits features (feature/wheel-and-transits)."""

import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))
from astro_tui import astrolog

SAMPLE_MONTH = """Astrolog 7.70 chart for Test Person
Mon Jan  1, 1990 12:00pm (ST Zone 6W) Nowhere  97:37W 30:28N

10/ 2/2026  2:47pm trans Mercury (Sco) Sex natal (Cap) Midheaven
10/ 3/2026  1:02am trans     Sun (Lib) Sex natal (Sag) Mars
10/ 3/2026 10:48pm trans     Sun (Lib) Squ natal (Cap) Sun
10/11/2026  9:35am trans     Sun (Lib) Tri natal [Aqu] North Node
"""

VALID_KINDS = ("Con", "Squ", "Opp", "Tri", "Sex")


class TestTransitEventParser(unittest.TestCase):
    def test_parses_all_events(self):
        events = astrolog.parse_transit_events(SAMPLE_MONTH)
        self.assertEqual(len(events), 4)

    def test_field_extraction(self):
        ev = astrolog.parse_transit_events(SAMPLE_MONTH)[0]
        self.assertEqual(ev.date, "10/2/2026")
        self.assertEqual(ev.time, "2:47pm")
        self.assertEqual(ev.body, "Mercury")
        self.assertEqual(ev.body_sign, "Sco")
        self.assertEqual(ev.kind, "Sex")
        self.assertEqual(ev.natal_body, "Midheaven")
        self.assertEqual(ev.label, "Mercury Sex natal Midheaven")

    def test_chronological_sort_across_day_boundary(self):
        events = astrolog.parse_transit_events(SAMPLE_MONTH)
        keys = [e.sort_key for e in events]
        self.assertEqual(keys, sorted(keys))
        # 1:02am on 10/3 sorts before 10:48pm on 10/3
        self.assertEqual(events[1].time, "1:02am")
        self.assertEqual(events[2].time, "10:48pm")

    def test_pm_time_conversion_in_sort_key(self):
        ev = astrolog.parse_transit_events(SAMPLE_MONTH)[2]  # 10:48pm
        self.assertEqual(ev.sort_key[-2:], (22, 48))

    def test_bracketed_signs_parse(self):
        # "[Aqu]" bracket form from -t output must parse the same as parens
        ev = astrolog.parse_transit_events(SAMPLE_MONTH)[3]
        self.assertEqual(ev.natal_sign, "Aqu")
        self.assertEqual(ev.natal_body, "North Node")

    def test_no_events_returns_empty(self):
        self.assertEqual(astrolog.parse_transit_events("garbage"), [])


class TestAppTransitTab(unittest.TestCase):
    """the app's transit-tab population + selection logic, exercised directly."""

    @classmethod
    def setUpClass(cls):
        if not _try_import("textual"):
            raise unittest.SkipTest("textual not installed")
        from astro_tui import app as app_module
        cls.app_module = app_module

    def _make_events(self):
        return self.app_module.astrolog.parse_transit_events(SAMPLE_MONTH)

    def test_load_transit_events_populates_table(self):
        events = self._make_events()
        app = self.app_module.AstroApp()
        table = mock.MagicMock()
        app.query_one = mock.MagicMock(return_value=table)
        with mock.patch.object(self.app_module.astrolog, "transits_events_month",
                               return_value=events):
            app.load_transit_events(mock.Mock())
        self.assertEqual(table.add_row.call_count, len(events))
        # first row: date, time, label, key
        first = table.add_row.call_args_list[0][0]
        self.assertEqual(first[0], "10/2/2026")
        self.assertEqual(first[1], "2:47pm")
        self.assertEqual(first[2], "Mercury Sex natal Midheaven")
        # key is passed as a keyword arg to DataTable.add_row
        self.assertEqual(table.add_row.call_args_list[0].kwargs["key"], "0")

    def test_show_transit_detail_renders_exact_hit(self):
        events = self._make_events()
        app = self.app_module.AstroApp()
        app.transit_events = events
        detail = mock.MagicMock()
        app.query_one = mock.MagicMock(return_value=detail)
        app.show_transit_detail(mock.Mock(value="1"))
        text = detail.update.call_args[0][0]
        self.assertIn("Sun (Lib) Sex natal Mars", text)
        self.assertIn("exact: 10/3/2026 at 1:02am", text)

    def test_show_transit_detail_bad_key_notifies(self):
        app = self.app_module.AstroApp()
        app.transit_events = self._make_events()
        app.query_one = mock.MagicMock()
        app.notify = mock.MagicMock()
        app.show_transit_detail(mock.Mock(value="999"))
        self.assertTrue(app.notify.called)
        self.assertFalse(app.query_one().update.called)


class TestLiveAstrologMonthRoundTrip(unittest.TestCase):
    @unittest.skipIf(not shutil.which(astrolog.ASTROLOG),
                     "astrolog binary not on PATH")
    def test_real_month_output_parses(self):
        tmp = Path(__import__("tempfile").mkdtemp())
        chart = tmp / "t.chart"
        astrolog.create_chart(astrolog.Person(
            name="Test", city="Nowhere", year=1990, month=1, day=1,
            time="12:00PM", dst=0, zone="6W", lon="97W37", lat="30N28"),
            chart)
        events = astrolog.transits_events_month(chart, 10, 2026)
        self.assertGreater(len(events), 0)
        for ev in events:
            self.assertIn(ev.kind, VALID_KINDS)
            self.assertTrue(ev.body and ev.natal_body)


def _try_import(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    unittest.main()
