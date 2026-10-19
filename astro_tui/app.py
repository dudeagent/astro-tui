"""terminal UI for astrolog: natal charts, transits, synastry, lore."""

import datetime
import json
import os
import shutil
import tempfile
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, ListView, ListItem, Static
from textual.widgets import DataTable, TabbedContent, TabPane

from . import astrolog, geo, lore

DATA_DIR = Path(os.environ.get("ASTRO_TUI_DATA", Path.home() / ".astro-tui"))


def people_dir() -> Path:
    d = DATA_DIR / "people"
    d.mkdir(parents=True, exist_ok=True)
    return d


def render_positions(text: str) -> str:
    """-v output -> compact table with sign names spelled out."""
    lines = []
    for pos in astrolog.parse_positions(text):
        retro = " R" if pos.retro else ""
        lines.append(f"{pos.body:<10} {pos.deg:>2}° {astrolog.SIGN_NAMES[astrolog.SIGNS.index(pos.sign[:3])]:<11} house {pos.house:>2}{retro}")
    return "\n".join(lines) or text


def render_aspects(text: str) -> str:
    lines = []
    for a in astrolog.parse_aspects(text):
        lines.append(f"{a.n:>3}. {a.body1:<8} ({a.sign1}) {a.kind:<4} ({a.sign2}) {a.body2:<8}  orb {a.orb:<8} power {a.power}")
    return "\n".join(lines) or text


class PersonForm(Static):
    """modal form to add a person (writes an astrolog chart file)."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def compose(self) -> ComposeResult:
        self.fields = {}
        self.picked_city: geo.City | None = None
        yield Input(placeholder="city search — type name, press enter", id="field-search")
        yield ListView(id="city-results")
        defaults = [
            ("name", "name"), ("city", "city"),
            ("month", "month (1-12)"), ("day", "day"), ("year", "year"),
            ("time", "time e.g. 7:00AM"), ("dst", "dst (0/1)"),
            ("zone", "zone e.g. 6W"), ("lon", "lon e.g. 97W37"),
            ("lat", "lat e.g. 30N28"),
        ]
        for key, label in defaults:
            inp = Input(placeholder=label, id=f"field-{key}")
            self.fields[key] = inp
            yield inp
        yield Button("save", id="btn-save", variant="primary")
        yield Button("cancel", id="btn-cancel")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "field-search":
            self._run_search(event.input.value)

    @work(thread=True, exclusive=True)
    def _run_search(self, query: str) -> None:
        results = geo.search_cities(query)
        self.app.call_from_thread(self._show_results, results)

    def _show_results(self, results: list[geo.City]) -> None:
        lv = self.query_one("#city-results", ListView)
        lv.clear()
        if not results:
            lv.append(ListItem(Label(f"no matches (offline? type coords manually)")))
        for city in results:
            item = ListItem(Label(city.label))
            item.data = city
            lv.append(item)
        lv.display = True
        lv.index = 0  # highlighted_child is None otherwise -> enter selects nothing
        lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        city = getattr(event.item, "data", None)
        if city is None:
            return
        self._apply_city(city)

    def _apply_city(self, city: geo.City) -> None:
        """autofill city/lon/lat + tz-derived zone/dst for the current date/time."""
        self.picked_city = city
        self.fields["city"].value = f"{city.name}, {city.admin1}".strip(", ") if city.admin1 else city.name
        self.fields["lon"].value = geo.to_astrolog_lon(city.lon)
        self.fields["lat"].value = geo.to_astrolog_lat(city.lat)
        try:
            self._apply_zone_dst()
        except ValueError:
            pass  # date/time not filled in yet; recomputed at save
        lv = self.query_one("#city-results", ListView)
        lv.display = False
        lv.blur()
        self.fields["name"].focus()
        self.app.notify(f"picked {city.label} ({city.timezone})")

    def _apply_zone_dst(self) -> None:
        """recompute dst+zone from picked city's tz and current date/time fields."""
        if not self.picked_city:
            return
        dst, zone = geo.tz_to_astrolog(
            self.picked_city.timezone,
            int(self.fields["year"].value or 2000),
            int(self.fields["month"].value or 1),
            int(self.fields["day"].value or 1),
            self.fields["time"].value or "12:00PM")
        self.fields["dst"].value = str(dst)
        self.fields["zone"].value = zone

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self._hide()

    def _save(self) -> None:
        # tz-derived dst/zone from the picked city win over stale form values
        try:
            self._apply_zone_dst()
        except ValueError:
            pass  # manual-entry path (no picked city) keeps whatever user typed
        data = {k: v.value.strip() for k, v in self.fields.items()}
        try:
            person = astrolog.Person(
                name=data["name"], city=data["city"],
                year=int(data["year"]), month=int(data["month"]), day=int(data["day"]),
                time=data["time"], dst=int(data["dst"]), zone=data["zone"],
                lon=data["lon"], lat=data["lat"])
        except (ValueError, KeyError) as e:
            self.app.notify(f"bad input: {e}", severity="error")
            return
        slug = person.name.lower().replace(" ", "-") or "person"
        out = people_dir() / f"{slug}.chart"
        if out.exists():
            self.app.notify(f"{slug} already exists", severity="warning")
            return
        try:
            astrolog.create_chart(person, out)
        except astrolog.AstrologError as e:
            self.app.notify(f"astrolog rejected it: {e}", severity="error")
            return
        (out.with_suffix(".json")).write_text(json.dumps({
            k: getattr(person, k) for k in
            ("name", "city", "year", "month", "day", "time", "dst", "zone", "lon", "lat")
        }))
        self.app.notify(f"saved {slug}")
        self.app.load_people()
        self._hide()

    def _hide(self) -> None:
        self.picked_city = None
        self.query_one("#city-results", ListView).display = False
        self.remove_class("shown")
        self.app.query_one("#people-table").focus()

    def action_cancel(self) -> None:
        self._hide()


class AstroApp(App):
    TITLE = "astro-tui"
    CSS = """
    #sidebar { width: 34; border-right: heavy $primary; padding: 0 1; }
    #content { padding: 0 1; }
    .pre { overflow-y: auto; }
    #form { display: none; border: heavy $accent; padding: 1; max-width: 50; }
    #form.shown { display: block; }
    #city-results { display: none; height: auto; max-height: 10; border-top: solid $primary; }
    DataTable { height: 1fr; }
    """
    BINDINGS = [
        Binding("n", "new_person", "add person"),
        Binding("d", "delete_person", "delete person"),
        Binding("s", "synastry_partner", "synastry partner"),
        Binding("r", "refresh", "refresh"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.people: list[astrolog.Person] = []
        self.selected: astrolog.Person | None = None
        self.transit_events: list[astrolog.TransitEvent] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("people (n=add, d=del)")
                yield DataTable(id="people-table")
            with TabbedContent(id="content", initial="tab-natal"):
                with TabPane("natal", id="tab-natal"):
                    yield Static("pick a person", classes="pre", id="natal-out")
                with TabPane("aspects", id="tab-aspects"):
                    yield Static("", classes="pre", id="aspects-out")
                with TabPane("transits", id="tab-transits"):
                    with Vertical():
                        yield DataTable(id="transit-table")
                        yield Static("", classes="pre", id="transit-detail")
                with TabPane("wheel", id="tab-wheel"):
                    yield Static("", classes="pre", id="wheel-out")
                with TabPane("synastry", id="tab-synastry"):
                    yield Static("", classes="pre", id="synastry-out")
                with TabPane("lore", id="tab-lore"):
                    with VerticalScroll():
                        yield Static(lore_text(), classes="pre", id="lore-out")
                with TabPane("raw -HI", id="tab-hi"):
                    yield Static("", classes="pre", id="hi-out")
        yield PersonForm(id="form")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#people-table", DataTable)
        table.add_columns("name", "birth")
        # people are picked row-by-row; default cursor_type is "cell",
        # which posts CellSelected and never fires on_data_table_row_selected
        table.cursor_type = "row"
        self.load_people()

    def load_people(self) -> None:
        self.people = astrolog.load_people(people_dir())
        table = self.query_one("#people-table", DataTable)
        table.clear()
        for p in self.people:
            table.add_row(p.name, f"{p.month}/{p.day}/{p.year}", key=str(p.path))

    def _select_from_key(self, key) -> None:
        path = Path(key)
        person = next((p for p in self.people if p.path == path), None)
        if person:
            self.selected = person
            self.show_person(person)
        else:
            # never fail silently again
            self.notify(f"no person for row {key!r}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # enter / keyboard selection — only the people table selects people;
        # the transit table posts the same events and is handled separately
        if event.data_table.id != "people-table":
            return
        if event.row_key and event.row_key.value is not None:
            self._select_from_key(event.row_key.value)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        # a mouse click posts CellSelected (even with cursor_type="row"),
        # so without this handler clicking a person row did nothing.
        if event.data_table.id != "people-table":
            return
        if event.row_key and event.row_key.value is not None:
            self._select_from_key(event.row_key.value)

    def show_person(self, person: astrolog.Person) -> None:
        try:
            natal = astrolog.natal_positions(person.path)
            self.query_one("#natal-out", Static).update(
                person.summary + "\n\n" + render_positions(natal))
            self.query_one("#aspects-out", Static).update(
                render_aspects(astrolog.natal_aspects(person.path)))
            self.query_one("#wheel-out", Static).update(astrolog.wheel(person.path))
            self.load_transit_events(person)
            # keep focus on the table so the user can arrow to another row
            # (e.g. to pick a synastry partner with 's') without re-clicking
        except astrolog.AstrologError as e:
            self.notify(str(e), severity="error")

    def load_transit_events(self, person: astrolog.Person) -> None:
        """populate the transits tab: exact-time hits for a window of upcoming
        months. the power column flags transits scoring above
        POWERFUL_THRESHOLD with a 🔺 (see astrolog.py for the scoring)."""
        today = datetime.date.today()
        table = self.query_one("#transit-table", DataTable)
        table.clear(columns=True)
        table.add_columns("date", "time", "transit", "power")
        table.cursor_type = "row"
        self.transit_events = astrolog.transits_events_next_months(
            person.path, today.month, today.year)
        for i, ev in enumerate(self.transit_events):
            flag = "🔺" if ev.powerful else ""
            table.add_row(ev.date, ev.time, ev.label, flag, key=str(i))
        n_flagged = sum(1 for ev in self.transit_events if ev.powerful)
        self.query_one("#transit-detail", Static).update(
            f"upcoming transits — enter/click one for details "
            f"({n_flagged} powerful 🔺)")

    def show_transit_detail(self, key) -> None:
        if key is None or key.value is None:
            return
        try:
            ev = self.transit_events[int(key.value)]
        except (ValueError, IndexError):
            self.notify(f"bad transit row {key.value!r}", severity="error")
            return
        self.query_one("#transit-detail", Static).update(
            f"{ev.body} ({ev.body_sign}) {ev.kind} natal {ev.natal_body} "
            f"({ev.natal_sign})\nexact: {ev.date} at {ev.time}")

    def on_transit_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.show_transit_detail(event.row_key)

    def on_transit_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        self.show_transit_detail(event.row_key)

    def action_synastry_partner(self) -> None:
        """with the cursor on a row: compute synastry selected <-> that person."""
        if not self.selected:
            self.notify("pick a person first (enter or click)", severity="warning")
            return
        table = self.query_one("#people-table", DataTable)
        from textual.coordinate import Coordinate
        key = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0)).row_key
        if not key or key.value is None:
            return
        partner = next((p for p in self.people if p.path == Path(key.value)), None)
        if partner is None:
            return
        if partner.path == self.selected.path:
            self.notify("synastry needs two different people", severity="warning")
            return
        try:
            text = astrolog.synastry_aspects(self.selected.path, partner.path)
            self.query_one("#synastry-out", Static).update(
                f"{self.selected.name} <-> {partner.name} "
                f"(sorted by power):\n" +
                render_aspects(text))
            self.notify(f"synastry: {self.selected.name} x {partner.name}")
        except astrolog.AstrologError as e:
            self.notify(str(e), severity="error")

    def action_new_person(self) -> None:
        form = self.query_one("#form", PersonForm)
        form.add_class("shown")
        # PersonForm is a Static (not focusable itself) — focus the first
        # Input instead so keys (incl. escape -> cancel) reach the form.
        form.query_one("#field-name", Input).focus()

    def action_delete_person(self) -> None:
        if self.selected and self.selected.path:
            self.selected.path.unlink(missing_ok=True)
            self.selected.path.with_suffix(".json").unlink(missing_ok=True)
            self.selected = None
            self.load_people()
            self.notify("deleted")

    def action_refresh(self) -> None:
        if self.selected:
            self.show_person(self.selected)


def lore_text() -> str:
    out = ["=== sephiroth (tree of life) ==="]
    for name, meaning, divine, planet in lore.SEPHIROTH:
        out.append(f"{name:<10} {meaning:<20} {divine:<22} {planet}")
    out.append("\n=== signs: golden dawn correspondences ===")
    for (name, elem, mod, ruler, heb, tarot, color) in lore.SIGNS_GD:
        out.append(f"{name:<12} {elem:<6} {mod:<9} ruler {ruler:<8} {heb:<6} {tarot:<18} {color}")
    out.append("\n=== houses ===")
    for n, meaning in lore.HOUSES:
        out.append(f"{n:>2}. {meaning}")
    out.append("\n=== lunar mansions ===")
    for n, span, meaning in lore.MOON_MANSIONS:
        out.append(f"{n:>2}. {span:<26} {meaning}")
    return "\n".join(out)


def main() -> None:
    if not shutil.which(astrolog.ASTROLOG):
        raise SystemExit(
            "astrolog not found — nix profile install nixpkgs#astrolog "
            "or set ASTROLOG_BIN")
    AstroApp().run()
