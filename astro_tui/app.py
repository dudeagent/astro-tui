"""terminal UI for astrolog: natal charts, transits, synastry, lore."""

import json
import os
import shutil
import tempfile
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.widgets import DataTable, TabbedContent, TabPane

from . import astrolog, lore

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        else:
            self._hide()

    def _save(self) -> None:
        from textual.app import App
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
        self.dismiss(None)

    def _hide(self) -> None:
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
    DataTable { height: 1fr; }
    """
    BINDINGS = [
        Binding("n", "new_person", "add person"),
        Binding("d", "delete_person", "delete person"),
        Binding("r", "refresh", "refresh"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.people: list[astrolog.Person] = []
        self.selected: astrolog.Person | None = None

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
                    yield Static("", classes="pre", id="transits-out")
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
        self.load_people()

    def load_people(self) -> None:
        self.people = astrolog.load_people(people_dir())
        table = self.query_one("#people-table", DataTable)
        table.clear()
        for p in self.people:
            table.add_row(p.name, f"{p.month}/{p.day}/{p.year}", key=str(p.path))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not event.row_key or event.row_key.value is None:
            return
        path = Path(event.row_key.value)
        person = next((p for p in self.people if p.path == path), None)
        if person:
            self.selected = person
            self.show_person(person)

    def show_person(self, person: astrolog.Person) -> None:
        try:
            natal = astrolog.natal_positions(person.path)
            self.query_one("#natal-out", Static).update(
                person.summary + "\n\n" + render_positions(natal))
            self.query_one("#aspects-out", Static).update(
                render_aspects(astrolog.natal_aspects(person.path)))
            self.query_one("#transits-out", Static).update(
                "now (sorted by influence):\n" +
                render_aspects(astrolog.parse_aspects(astrolog.transits_today(person.path))))
            self.set_focus(None)
        except astrolog.AstrologError as e:
            self.notify(str(e), severity="error")

    def action_new_person(self) -> None:
        form = self.query_one("#form", PersonForm)
        form.add_class("shown")
        form.set_focus(True)

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
