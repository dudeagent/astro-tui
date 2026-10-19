"""acceptance tests: drive the real TUI the way a user does.

uses textual's run_test() pilot — no mocks for the app layer. these
tests ARE the spec for the main journeys; when features change, update
these tests rather than writing new ones (see AGENTS.md).
journeys covered: launch+lore, add person, select person (natal/aspects/
transits), delete person, bad-input rejection, quit.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from astro_tui import app as app_module  # noqa: E402
from astro_tui import astrolog  # noqa: E402

HAS_ASTROLOG = shutil.which(astrolog.ASTROLOG) is not None


@pytest.fixture()
def app():
    """a real AstroApp with a temp data dir, driven via run_test()."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    app_module.DATA_DIR = tmp  # people_dir() reads the module global
    a = app_module.AstroApp()
    yield a
    shutil.rmtree(tmp, ignore_errors=True)


async def seed_person(app, name="Test", city="Nowhere"):
    """create a chart file through astrolog, reload the people table."""
    person = astrolog.Person(name=name, city=city, year=1990, month=5,
                             day=15, time="12:30PM", dst=0, zone="6W",
                             lon="97W37", lat="30N28")
    out = app_module.people_dir() / f"{name.lower()}.chart"
    astrolog.create_chart(person, out)
    person.path = out  # create_chart writes the file but doesn't set .path
    app.load_people()
    return person


def form_visible(app):
    return "shown" in app.query_one("#form").classes


def set_field(app, key, value):
    from textual.widgets import Input
    inp = app.query_one(f"#field-{key}", Input)
    inp.value = value


async def test_launch_renders_people_table_and_lore(app):
    async with app.run_test(size=(120, 40)) as pilot:
        table = app.query_one("#people-table")
        assert table.row_count == 0
        lore = app.query_one("#lore-out").content
        assert "sephiroth" in lore and "lunar mansions" in lore
        # main tabs all exist
        for tab in ("tab-natal", "tab-aspects", "tab-transits",
                    "tab-synastry", "tab-lore", "tab-hi"):
            app.query_one(f"#{tab}")
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_add_person_via_form(app):
    """press n -> form opens -> fill fields -> save -> person in table + file on disk."""
    async with app.run_test(size=(120, 40)) as pilot:
        assert not form_visible(app)
        await pilot.press("n")            # add-person binding
        assert form_visible(app)
        fields = {"name": "John Doe", "city": "Austin",
                  "month": "5", "day": "15", "year": "1990",
                  "time": "7:00AM", "dst": "0", "zone": "6W",
                  "lon": "97W37", "lat": "30N28"}
        for k, v in fields.items():
            set_field(app, k, v)
        await pilot.click("#btn-save")
        await pilot.pause()
        # form closed, file written, table repopulated
        assert not form_visible(app)
        saved = app_module.people_dir() / "john-doe.chart"
        assert saved.exists() and saved.with_suffix(".json").exists()
        table = app.query_one("#people-table")
        assert table.row_count == 1
        assert "John Doe" in str(table.get_row_at(0))
        # the chart on disk must round-trip back to the same metadata
        back = astrolog.parse_chart_header(saved)
        assert back.name == "John Doe" and back.year == 1990
        # regression (the bug john kept hitting): a form-saved person has a
        # json sidecar, so parse_chart_header takes the json branch. it used
        # to return the dict as .path -> selection silently did nothing.
        assert isinstance(back.path, Path), "json path must be the chart file"
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_select_form_saved_person_with_json_sidecar(app):
    """regression: people saved via the add form get a .json sidecar, and the
    json branch of parse_chart_header returned the dict as .path — so the row
    key was str(dict), no handler ever matched, and click/enter both did
    nothing. this is the journey john actually uses; the seeded-person tests
    above skipped it because seed_person doesn't write a sidecar."""
    async with app.run_test(size=(120, 40)) as pilot:
        person = astrolog.Person(name="Form John", city="Austin",
                                 year=1990, month=5, day=15, time="7:00AM",
                                 dst=0, zone="6W", lon="97W37", lat="30N28")
        out = app_module.people_dir() / "form-john.chart"
        astrolog.create_chart(person, out)
        out.with_suffix(".json").write_text(json.dumps({
            k: getattr(person, k) for k in
            ("name", "city", "year", "month", "day", "time",
             "dst", "zone", "lon", "lat")}))
        app.load_people()
        assert isinstance(app.people[0].path, Path)
        # enter selects
        table = app.query_one("#people-table")
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.selected is not None, "enter did not select json-sidecar person"
        assert "Form John" in str(app.query_one("#natal-out").content)
        assert "orb" in str(app.query_one("#aspects-out").content)
        # and a fresh app instance selects the same person by mouse click
        import tempfile
        a2 = app_module.AstroApp()
        async with a2.run_test(size=(120, 40)) as pilot2:
            await pilot2.click("#people-table", offset=(4, 1))
            await pilot2.pause()
            assert a2.selected is not None, "click did not select json-sidecar person"
            assert "Form John" in str(a2.query_one("#natal-out").content)
            await pilot2.press("q")
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_cancel_add_person(app):
    """open form, change mind, escape -> nothing written."""
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("n")
        set_field(app, "name", "Ghost")
        await pilot.press("escape")
        assert not form_visible(app)
        assert list(app_module.people_dir().glob("*.chart")) == []
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_bad_input_rejected(app):
    """garbage numbers -> error notify, form stays open, no file."""
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("n")
        set_field(app, "name", "Bad")
        set_field(app, "month", "notanumber")
        await pilot.click("#btn-save")
        await pilot.pause()
        assert not list(app_module.people_dir().glob("*.chart"))
        await pilot.press("escape")
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_duplicate_name_rejected(app):
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app, name="Dup")
        await pilot.press("n")
        set_field(app, "name", "Dup")
        set_field(app, "month", "1")
        set_field(app, "day", "1")
        set_field(app, "year", "1990")
        await pilot.click("#btn-save")
        await pilot.pause()
        # original untouched, no second chart
        charts = list(app_module.people_dir().glob("*.chart"))
        assert [c.name for c in charts] == ["dup.chart"]
        await pilot.press("escape")
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_select_person_shows_natal_aspects_transits(app):
    """click a person row -> natal/aspects/transits tabs populate."""
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app)
        table = app.query_one("#people-table")
        key = app.people[0].path
        # real user flow: focus the table, press enter to select the row
        # (direct action_select_cursor() calls don't fire RowSelected reliably)
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        natal = app.query_one("#natal-out").content
        assert "Test" in str(natal) and "5/15/1990" in str(natal) and "Nowhere" in str(natal)
        assert "Sun" in str(natal) and "house" in str(natal)
        aspects = app.query_one("#aspects-out").content
        assert "orb" in str(aspects) and "power" in str(aspects)
        transit_table = app.query_one("#transit-table")
        assert transit_table.row_count > 0
        assert app.selected is not None
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_mouse_click_selects_person(app):
    """the real bug john hit: clicking a row posts CellSelected, not
    RowSelected — without that handler nothing ever displayed."""
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app)
        # click inside the table widget near the top (row 0; y=0 is the header)
        await pilot.click("#people-table", offset=(4, 1))
        await pilot.pause()
        assert app.selected is not None, "click did not select the person"
        natal = app.query_one("#natal-out").content
        assert "Test" in str(natal)
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_synastry_partner(app):
    """select A, arrow to B, press s -> synastry pane fills with A <-> B."""
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app, name="Alpha")
        await seed_person(app, name="Beta")
        table = app.query_one("#people-table")
        table.focus()
        await pilot.press("enter")        # select Alpha (row 0)
        await pilot.pause()
        assert app.selected.name == "Alpha"
        await pilot.press("down")         # cursor to Beta (row 1)
        await pilot.press("s")            # synastry Alpha <-> Beta
        await pilot.pause()
        syn = app.query_one("#synastry-out").content
        assert "Alpha <-> Beta" in str(syn)
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_synastry_needs_two_people(app):
    """synastry of a person with themselves warns instead of crashing."""
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app, name="Solo")
        table = app.query_one("#people-table")
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("s")            # cursor still on Solo -> warning
        await pilot.pause()
        # no crash, synastry pane untouched
        assert str(app.query_one("#synastry-out").content) == ""
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_delete_person(app):
    """select a person, press d -> files gone, table empty."""
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app)
        table = app.query_one("#people-table")
        # select via real key flow, then delete with 'd'
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert list(app_module.people_dir().glob("*.chart")) == []
        assert app.query_one("#people-table").row_count == 0
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_refresh_reloads_current_person(app):
    async with app.run_test(size=(120, 40)) as pilot:
        await seed_person(app)
        table = app.query_one("#people-table")
        # select via real key flow
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        natal_before = app.query_one("#natal-out").content
        await pilot.press("r")
        await pilot.pause()
        assert app.query_one("#natal-out").content == natal_before
        await pilot.press("q")


@pytest.mark.skipif(not HAS_ASTROLOG, reason="astrolog binary not on PATH")
async def test_journey_city_search_autofills(app, monkeypatch):
    """type in the search bar -> pick a result -> city/lon/lat/zone/dst autofill."""
    import asyncio

    from textual.widgets import Input

    from astro_tui.geo import City

    fake = City(name="Austin", admin1="Texas", country="United States",
                lat=30.2672, lon=-97.7431, timezone="America/Chicago",
                population=965000)
    monkeypatch.setattr(app_module.geo, "search_cities", lambda q, **kw: [fake])

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("n")
        form = app.query_one("#form")
        # type into the search input and hit enter
        search = form.query_one("#field-search", Input)
        search.value = "austin"
        search.focus()  # real user flow: click/tab into the search bar
        await pilot.press("enter")
        await pilot.pause()
        # search runs in a worker thread — poll until results land
        for _ in range(50):
            lv = form.query_one("#city-results")
            if lv.display and lv.children:
                break
            await asyncio.sleep(0.05)
        lv = form.query_one("#city-results")
        assert lv.display, "results list never appeared"
        assert "Austin" in str(lv.children[0].children[0].content)
        # user picks the first result (enter on the list view)
        await pilot.press("enter")
        await pilot.pause()
        assert form.fields["city"].value == "Austin, Texas"
        assert form.fields["lon"].value == "97W45"
        assert form.fields["lat"].value == "30N16"
        # fill birth date/time -> save -> zone/dst recomputed from the city tz
        for k, v in {"name": "Geo Kid", "month": "5", "day": "15",
                     "year": "1990", "time": "12:30PM"}.items():
            set_field(app, k, v)
        await pilot.click("#btn-save")
        await pilot.pause()
        saved = app_module.people_dir() / "geo-kid.json"
        meta = json.loads(saved.read_text())
        assert meta["zone"] == "5W" and meta["dst"] == 1  # CDT, not manual 6W
        await pilot.press("q")
