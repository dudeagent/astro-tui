"""tests for the new wheel + selectable-transits features (feature/wheel-and-transits)."""

import datetime
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


class TestTransitEventPower(unittest.TestCase):
    """the estimated power scoring + powerful threshold behavior."""

    def _make_event(self, body: str, kind: str):
        return astrolog.TransitEvent(
            date="10/1/2026", time="1:00pm", body=body, body_sign="Cap",
            kind=kind, natal_sign="Can", natal_body="Sun")

    def test_power_ranks_major_aspects_higher(self):
        # conj/opposition weigh more than sextile for the same planet
        self.assertGreater(self._make_event("Pluto", "Con").power,
                           self._make_event("Pluto", "Sex").power)
        self.assertGreater(self._make_event("Saturn", "Opp").power,
                           self._make_event("Saturn", "Ses").power)

    def test_power_ranks_outer_planets_higher(self):
        # outer planets beat personal points for the same aspect kind
        self.assertGreater(self._make_event("Pluto", "Tri").power,
                           self._make_event("Moon", "Tri").power)
        self.assertGreater(self._make_event("Saturn", "Squ").power,
                           self._make_event("Mercury", "Squ").power)

    def test_powerful_threshold_boundary(self):
        # pluto conj (1.0) and saturn conj (0.7) clear the 0.5 threshold
        self.assertTrue(self._make_event("Pluto", "Con").powerful)
        self.assertTrue(self._make_event("Saturn", "Con").powerful)
        # saturn sextile (0.7 * 0.4 = 0.28) doesn't
        self.assertFalse(self._make_event("Saturn", "Sex").powerful)
        # uranus trine (0.8 * 0.8 = 0.64) does; moon trine (0.24) doesn't
        self.assertTrue(self._make_event("Uranus", "Tri").powerful)
        self.assertFalse(self._make_event("Moon", "Tri").powerful)

    def test_unknown_bodies_score_low(self):
        # bodies without a weight entry (asteroids etc) get the floor
        self.assertEqual(self._make_event("Vesta", "Con").power, 0.1)
        self.assertFalse(self._make_event("Vesta", "Con").powerful)


class TestTransitsNextMonths(unittest.TestCase):
    """transits_events_next_months collects a window of months, sorted."""

    def test_collects_and_sorts_across_months(self):
        oct_ev = astrolog.TransitEvent(
            date="10/15/2026", time="5:00pm", body="Mars",
            body_sign="Sco", kind="Tri", natal_sign="Pis", natal_body="Sun")
        nov_ev = astrolog.TransitEvent(
            date="11/2/2026", time="9:00am", body="Jupiter",
            body_sign="Can", kind="Opp", natal_sign="Cap", natal_body="MC")
        by_month = {(10, 2026): [oct_ev], (11, 2026): [nov_ev]}
        with mock.patch.object(
                astrolog, "transits_events_month",
                side_effect=lambda chart, m, y: by_month.get((m, y), [])):
            got = astrolog.transits_events_next_months(
                mock.Mock(), 10, 2026, months=2)
        # chronological across the month boundary
        self.assertEqual(got, [oct_ev, nov_ev])

    def test_rolls_over_the_year(self):
        called = []

        def fake_month(chart, m, y):
            called.append((m, y))
            return []

        with mock.patch.object(astrolog, "transits_events_month",
                               side_effect=fake_month):
            astrolog.transits_events_next_months(
                mock.Mock(), 11, 2026, months=3)
        self.assertEqual(called, [(11, 2026), (12, 2026), (1, 2027)])


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
        # the app asks for a window of upcoming months (not just the current
        # one) so powerful upcoming transits are visible ahead of time
        events = self._make_events()
        # synthetic high-power event to verify the 🔺 flag lands on it
        powerful = self.app_module.astrolog.TransitEvent(
            date="11/1/2026", time="8:00am", body="Pluto", body_sign="Cap",
            kind="Squ", natal_sign="Can", natal_body="Sun")
        all_events = events + [powerful]
        app = self.app_module.AstroApp()
        table = mock.MagicMock()
        app.query_one = mock.MagicMock(return_value=table)
        with mock.patch.object(self.app_module.astrolog,
                               "transits_events_next_months",
                               return_value=all_events), \
                mock.patch.object(self.app_module.astrolog,
                                  "transits_graph", return_value={}):
            app.load_transit_events(mock.Mock())
        self.assertEqual(table.add_row.call_count, len(all_events))
        # the new power column sits alongside the existing ones
        # (DataTable.add_columns(*cols) receives them as positional args)
        self.assertEqual(table.add_columns.call_args_list[0][0],
                         ("date", "time", "transit", "power"))
        # first row: date, time, label, power flag (no flag for weak transits)
        first = table.add_row.call_args_list[0][0]
        self.assertEqual(first[0], "10/2/2026")
        self.assertEqual(first[1], "2:47pm")
        self.assertEqual(first[2], "Mercury Sex natal Midheaven")
        self.assertEqual(first[3], "")
        # key is passed as a keyword arg to DataTable.add_row
        self.assertEqual(table.add_row.call_args_list[0].kwargs["key"], "0")
        # the high-power event gets the 🔺 flag in its power column
        last = table.add_row.call_args_list[-1][0]
        self.assertEqual(last[0], "11/1/2026")
        self.assertEqual(last[3], "🔺")

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

    def test_load_transit_events_loads_graphs_for_full_window(self):
        # the app must fetch a -V power graph for every month in the
        # transit window (current + 2), not just the current month,
        # so events in future months get their graph in the detail view
        app = self.app_module.AstroApp()
        app.query_one = mock.MagicMock()
        fake_graph = {"Sun Con Sun": [9] * 31}
        called = []

        def fake_graph_call(chart, m, y):
            called.append((m, y))
            return fake_graph

        # create the real date object BEFORE the mock (patching datetime.date
        # on the app module patches the shared datetime module, so a real
        # date must be built outside the with block)
        today = datetime.date(2026, 11, 18)
        with mock.patch.object(self.app_module.datetime, "date") as d, \
                mock.patch.object(self.app_module.astrolog,
                                  "transits_events_next_months",
                                  return_value=[]), \
                mock.patch.object(self.app_module.astrolog,
                                  "transits_graph",
                                  side_effect=fake_graph_call):
            d.today.return_value = today
            app.load_transit_events(mock.Mock())
        # window: current month + next two, with year rollover
        self.assertEqual(called, [(11, 2026), (12, 2026), (1, 2027)])
        self.assertEqual(app.transit_graphs["2026-11"], fake_graph)
        self.assertEqual(app.transit_graphs["2026-12"], fake_graph)
        self.assertEqual(app.transit_graphs["2027-01"], fake_graph)

    def test_show_transit_detail_uses_event_month_graph(self):
        # the detail view must look up the -V graph by the event's month,
        # not always the current month (events span the 3-month window)
        app = self.app_module.AstroApp()
        app.transit_events = self._make_events()  # all events dated 10/2026
        app.query_one = mock.MagicMock()
        fake_graph = {"Sun Sex Mar": [None, None, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, None, None]}
        app.transit_graphs = {"2026-10": fake_graph,
                              "2026-11": {"Sun Sex Mar": [None] * 31}}
        # select the third event: Sun (Lib) Sex natal (Sag) Mars, day 3
        app.show_transit_detail(mock.Mock(value="1"))
        text = app.query_one().update.call_args[0][0]
        self.assertIn("power score", text)
        self.assertIn("power graph (this month):", text)
        # the sparkline renders a block at the exact-hit day (day 3)
        sparkline_line = next(l for l in text.split("\n")
                              if "power graph" in l)
        self.assertIn("█", sparkline_line)  # peak value 9 (day 3) -> full block
        self.assertIn("▂", sparkline_line)  # mid values render too

    def test_show_transit_detail_missing_graph_row(self):
        app = self.app_module.AstroApp()
        app.transit_events = self._make_events()
        app.query_one = mock.MagicMock()
        # graph exists but has no row matching this transit
        app.transit_graphs = {"2026-10": {"Unrelated Row": [None] * 31}}
        app.show_transit_detail(mock.Mock(value="0"))
        text = app.query_one().update.call_args[0][0]
        self.assertIn("(no monthly power graph row for this transit)", text)


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
