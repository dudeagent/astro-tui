"""terminal UI for astrolog: natal charts, transits, synastry, lore."""

import datetime
import json
import os
import shutil
import tempfile
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, ListView, ListItem, Select, Static
from textual.widgets import DataTable, TabbedContent, TabPane
from textual.screen import ModalScreen
from textual_image.widget import AutoRenderable as AutoImageRenderable

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


def _sparkline(values: list[int | None]) -> str:
    """render a -V power row (values 0-9 or None) as unicode blocks."""
    blocks = " ▁▂▃▄▅▆▇█"
    return "".join("·" if v is None else blocks[min(v, 8)] for v in values)


def render_aspect_graph(text: str) -> Text:
    """the aspects listing as a colored glyph graph: planet glyphs + sign
    glyphs + aspect symbols, each colored by its planet/aspect. this is the
    visual view that comes BEFORE the plain text list in the aspects (and
    synastry) panes. returns rich Text so colors survive Static.update."""
    out = Text()
    out.append("☌ conj   △ trine   □ square   ☍ opp   ⚹ sextile\n",
               style="grey50")
    out.append("glyphs colored by planet/aspect — ☉ yellow ☽ white ☿ green "
               "♀ cyan ♂ red ♃ blue ♄ grey ♅ mag ♆ sky ♇ purple\n\n",
               style="grey50")
    for a in astrolog.parse_aspects(text):
        out.append(f"{astrolog.planet_glyph(a.body1):>2} ",
                   style=astrolog.planet_color(a.body1))
        out.append(f"{astrolog.sign_glyph(a.sign1)} ",
                   style="grey58")
        out.append(f"{astrolog.aspect_glyph(a.kind):>2} ",
                   style=astrolog.aspect_color(a.kind))
        out.append(f"{astrolog.sign_glyph(a.sign2)} ",
                   style="grey58")
        out.append(f"{astrolog.planet_glyph(a.body2):<2}",
                   style=astrolog.planet_color(a.body2))
        out.append(f"  orb {a.orb:<7} power {a.power}\n", style="grey50")
    return out if out.plain.strip("\n").count("\n") >= 2 else Text("no aspects found")


class WheelView(Static):
    """a static that holds a PIL wheel image; clicking it maximizes the
    image full-screen (same as the 'm' hotkey)."""

    image = None
    big_image = None

    def on_click(self, event) -> None:
        # the big (high-res) image is the one to maximize
        if self.image is None and self.big_image is None:
            return
        # inside MaximizeScreen a click dismisses it instead of pushing
        # another maximize on top of itself
        if isinstance(self.screen, MaximizeScreen):
            self.screen.dismiss()
        else:
            self.app.action_maximize_wheel(self.big_image or self.image)


class MaximizeScreen(ModalScreen):
    """full-screen modal showing one wheel image bigger. click anywhere or
    press escape/q/m to close."""

    BINDINGS = [Binding("escape", "dismiss", "close"),
                Binding("q", "dismiss", "close"),
                Binding("m", "dismiss", "close")]

    def __init__(self, image) -> None:
        super().__init__()
        self.image = image

    def compose(self) -> ComposeResult:
        # the image must be passed to the Static itself — setting view.image
        # alone leaves the widget's content as "" so the maximize screen
        # renders an empty pane (the bug john hit on 10-19)
        renderable = (AutoImageRenderable(self.image) if self.image is not None
                      else Text("no wheel image"))
        view = WheelView(renderable, id="maximized-wheel")
        view.image = self.image
        view.big_image = self.image
        yield view

class PersonForm(Static):
    """modal form to add a person (writes an astrolog chart file)."""

    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def compose(self) -> ComposeResult:
        self.fields = {}
        self.picked_city: geo.City | None = None
        self.person: astrolog.Person | None = None
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
        # editing mode: overwriting the person's own file is fine, but a
        # collision with a *different* person still gets blocked
        is_edit = self.person is not None
        if out.exists():
            if is_edit and self.person.path.resolve() == out.resolve():
                pass  # same person, allow save
            else:
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
        # if the name changed during an edit the slug changed too — clean up
        # the old chart + json files so the person doesn't exist twice
        if is_edit and self.person.path.resolve() != out.resolve():
            self.person.path.unlink(missing_ok=True)
            self.person.path.with_suffix(".json").unlink(missing_ok=True)
        self.app.notify(f"saved {slug}")
        self.app.load_people()
        self._hide()

    def _hide(self) -> None:
        self.picked_city = None
        self.person = None
        self.query_one("#city-results", ListView).display = False
        self.remove_class("shown")
        self.app.query_one("#people-table").focus()

    def action_cancel(self) -> None:
        self._hide()

    def populate(self, person: astrolog.Person) -> None:
        """pre-fill the form fields for editing an existing person."""
        self.person = person
        data = {
            "name": person.name, "city": person.city,
            "month": str(person.month), "day": str(person.day),
            "year": str(person.year), "time": person.time,
            "dst": str(person.dst), "zone": person.zone,
            "lon": person.lon, "lat": person.lat,
        }
        for key, value in data.items():
            if key in self.fields:
                self.fields[key].value = value

    def start_edit(self, person: astrolog.Person) -> None:
        """open the form in edit mode, pre-filled with the person's data."""
        self.populate(person)
        self.add_class("shown")
        self.fields["name"].focus()


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
    MaximizeScreen { background: $surface; align: center middle; }
    # maximized wheel: 80% of the screen, centered (john: "make the larger
    # one 80% screen size and centered")
    MaximizeScreen WheelView { width: 80%; height: 80%; }
    """
    BINDINGS = [
        Binding("n", "new_person", "add person"),
        Binding("d", "delete_person", "delete person"),
        Binding("e", "edit_person", "edit person"),
        Binding("s", "synastry_partner", "synastry partner"),
        Binding("r", "refresh", "refresh"),
        Binding("m", "maximize_wheel", "maximize wheel"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.people: list[astrolog.Person] = []
        self.selected: astrolog.Person | None = None
        self.transit_events: list[astrolog.TransitEvent] = []
        self.transit_graphs: dict[str, list[int | None]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("people (n=add, d=del)")
                yield DataTable(id="people-table")
            with TabbedContent(id="content", initial="tab-natal"):
                with TabPane("natal", id="tab-natal"):
                    with VerticalScroll():
                        yield Static("pick a person", classes="pre", id="natal-out")
                        yield WheelView("", classes="pre", id="natal-wheel")
                with TabPane("aspects", id="tab-aspects"):
                    with VerticalScroll():
                        # colored glyph graph FIRST, then the plain text list
                        # (john: "make it come before the text list of them")
                        yield Static("", classes="pre", id="aspects-graph")
                        yield Static("", classes="pre", id="aspects-out")
                        yield Static("", classes="pre", id="aspects-grid")
                        yield WheelView("", classes="pre", id="aspects-wheel")
                with TabPane("transits", id="tab-transits"):
                    with VerticalScroll():
                        yield DataTable(id="transit-table")
                        yield Static("", classes="pre", id="transit-detail")
                        yield WheelView("", classes="pre", id="transit-wheel")
                with TabPane("wheel", id="tab-wheel"):
                    # the graphic wheel image, not the ascii one (john: "make
                    # it the img pls")
                    yield WheelView("", classes="pre", id="big-wheel")
                with TabPane("synastry", id="tab-synastry"):
                    with VerticalScroll():
                        yield Select([("choose partner...", None)], id="synastry-partner", allow_blank=True)
                        # graph before the text list here too
                        yield Static("", classes="pre", id="synastry-graph")
                        yield Static("", classes="pre", id="synastry-out")
                        yield WheelView("", classes="pre", id="synastry-wheel")
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
        # enter / keyboard selection — dispatch by table id (textual dispatches
        # these messages by widget class, so both tables land here)
        if event.data_table.id == "people-table":
            if event.row_key and event.row_key.value is not None:
                self._select_from_key(event.row_key.value)
        elif event.data_table.id == "transit-table":
            self.show_transit_detail(event.row_key)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        # a mouse click posts CellSelected (even with cursor_type="row") —
        # dispatch by table id the same way as RowSelected.
        if event.data_table.id == "people-table":
            if event.row_key and event.row_key.value is not None:
                self._select_from_key(event.row_key.value)
        elif event.data_table.id == "transit-table":
            self.show_transit_detail(event.row_key)

    def _wheel_image(self, person: astrolog.Person,
                     partner: astrolog.Person | None = None,
                     width: int = astrolog.WHEEL_SMALL_SIZE):
        """astrolog's graphic wheel as a raw PIL image. two sizes are
        generated per chart (john: "generate two sizes and make the larger
        one 80% screen size and centered"): astrolog.WHEEL_SMALL_SIZE for the in-tab
        wheel views, astrolog.WHEEL_LARGE_SIZE when a wheel is maximized.
        `width` passes through to astrolog's -Xw; the wheel view widgets wrap
        the image in a renderable themselves."""
        try:
            return astrolog.wheel_image(person.path,
                                        partner.path if partner else None,
                                        width=width)
        except Exception:
            return None

    def _set_wheel(self, selector: str, img, big_img=None) -> None:
        """update a WheelView widget: render the (small) image for the tab
        and keep both sizes on the widget — `image` is what's displayed,
        `big_image` is the high-res version used when the wheel is
        maximized (falls back to `image` if no big one was generated)."""
        w = self.query_one(selector, WheelView)
        w.image = img
        w.big_image = big_img if big_img is not None else img
        w.update(AutoImageRenderable(img) if img is not None
                 else Text("wheel render failed"))

    def action_maximize_wheel(self, image=None) -> None:
        """maximize the wheel image full-screen. 'image' is passed directly by
        WheelView clicks; the 'm' hotkey grabs the image from the wheel view
        in the currently active tab."""
        if image is None:
            tab = self.query_one("#content", TabbedContent).active
            wid = {"tab-natal": "#natal-wheel",
                   "tab-aspects": "#aspects-wheel",
                   "tab-transits": "#transit-wheel",
                   "tab-wheel": "#big-wheel",
                   "tab-synastry": "#synastry-wheel"}.get(tab)
            if wid is None:
                self.notify("no wheel on this tab", severity="warning")
                return
            view = self.query_one(wid, WheelView)
            # the big (high-res) image is what gets maximized
            image = view.big_image
        if image is None:
            self.notify("no wheel image to maximize", severity="warning")
            return
        self.push_screen(MaximizeScreen(image))

    def show_person(self, person: astrolog.Person) -> None:
        try:
            natal = astrolog.natal_positions(person.path)
            self.query_one("#natal-out", Static).update(
                person.summary + "\n\n" + render_positions(natal))
            aspects_text = astrolog.natal_aspects(person.path)
            # colored glyph graph first, plain text list after it
            self.query_one("#aspects-graph", Static).update(
                render_aspect_graph(aspects_text))
            self.query_one("#aspects-out", Static).update(
                render_aspects(aspects_text))
            # astrolog's own matrix view of every body pair (-g) — the
            # "better table of aspects" john asked for
            self.query_one("#aspects-grid", Static).update(
                astrolog.natal_grid(person.path))
            # graphic wheel on every chart screen (natal/aspects/transits),
            # the dedicated wheel tab, and synastry gets the overlay image
            # once a partner is picked
            # two sizes: small for the in-tab wheels, large for maximize
            img = self._wheel_image(person)
            big = self._wheel_image(person, width=astrolog.WHEEL_LARGE_SIZE)
            for wid in ("natal-wheel", "aspects-wheel", "transit-wheel",
                        "big-wheel"):
                self._set_wheel(f"#{wid}", img, big)
            self.load_transit_events(person)
            self.refresh_synastry_options(person)
            # keep focus on the table so the user can arrow to another row
            # (e.g. to pick a synastry partner with 's') without re-clicking
        except astrolog.AstrologError as e:
            self.notify(str(e), severity="error")

    def refresh_synastry_options(self, person: astrolog.Person) -> None:
        """(re)populate the synastry partner dropdown for the selected person."""
        sel = self.query_one("#synastry-partner", Select)
        sel.set_options(
            [("choose partner...", None)] +
            [(p.name, str(p.path)) for p in self.people
             if p.path != person.path])
        sel.value = None
        self.query_one("#synastry-graph", Static).update("")
        self.query_one("#synastry-out", Static).update("")
        self._set_wheel("#synastry-wheel", None)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "synastry-partner" or event.value is None:
            return
        partner = next((p for p in self.people
                        if str(p.path) == event.value), None)
        if partner is None or self.selected is None:
            return
        self.show_synastry(self.selected, partner)

    def show_synastry(self, person: astrolog.Person,
                      partner: astrolog.Person) -> None:
        try:
            text = astrolog.synastry_aspects(person.path, partner.path)
            # colored glyph graph before the text list (same as natal)
            self.query_one("#synastry-graph", Static).update(
                render_aspect_graph(text))
            self.query_one("#synastry-out", Static).update(
                f"{person.name} <-> {partner.name} "
                f"(sorted by power):\n" + render_aspects(text))
            self._set_wheel("#synastry-wheel",
                            self._wheel_image(person, partner),
                            self._wheel_image(person, partner,
                                              width=astrolog.WHEEL_LARGE_SIZE))
            self.notify(f"synastry: {person.name} x {partner.name}")
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
        # grab astrolog's monthly power graphs (-V) for every month in the
        # transit window so details can show the day-by-day power curve for
        # events in future months too, without re-running on every select
        self.transit_graphs = {}
        m, y = today.month, today.year
        for _ in range(3):
            self.transit_graphs[f"{y}-{m:02d}"] = astrolog.transits_graph(
                person.path, m, y)
            m += 1
            if m > 12:
                m, y = 1, y + 1
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
        lines = [f"{ev.body} ({ev.body_sign}) {ev.kind} natal {ev.natal_body} "
                 f"({ev.natal_sign})",
                 # be explicit about what the -t timestamp actually is:
                 # astrolog emits the exact moment the aspect perfects (is
                 # exact), NOT the start or end of the orb window.
                 f"exact hit (peak): {ev.date} at {ev.time} — this is when the "
                 f"aspect is exact, not the orb start/end",
                 f"power score: {ev.power:.2f}"
                 + ("  🔺 POWERFUL" if ev.powerful else "")]
        # look up the -V power graph for the event's month
        month, _, year = ev.date.split("/")
        graph = self.transit_graphs.get(f"{int(year)}-{int(month):02d}")
        row = astrolog.find_graph_row(graph, ev) if graph else None
        if row:
            lines.append("power graph (this month): " + _sparkline(row))
            peak = max((i for i, v in enumerate(row) if v is not None),
                       default=None)
            if peak is not None:
                lines.append(f"peaks day {peak + 1} at strength "
                             f"{row[peak]}/9")
        else:
            lines.append("(no monthly power graph row for this transit)")
        self.query_one("#transit-detail", Static).update("\n".join(lines))

    def action_synastry_partner(self) -> None:
        """jump to the synastry partner dropdown ('s' binding)."""
        if not self.selected:
            self.notify("pick a person first (enter or click)", severity="warning")
            return
        self.query_one("#synastry-partner", Select).focus()

    def action_new_person(self) -> None:
        form = self.query_one("#form", PersonForm)
        form.add_class("shown")
        # PersonForm is a Static (not focusable itself) — focus the first
        # Input instead so keys (incl. escape -> cancel) reach the form.
        form.query_one("#field-name", Input).focus()

    def action_edit_person(self) -> None:
        """edit the selected person's birth data (rewrites the chart file)."""
        if not self.selected:
            self.notify("pick a person first (enter or click)", severity="warning")
            return
        self.query_one("#form", PersonForm).start_edit(self.selected)

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
