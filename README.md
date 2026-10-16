# astro-tui

terminal astrology UI wrapping the [`astrolog`](https://www.astrolog.org/) cli (v7.70).

tabs: people, natal chart (positions + aspects + ascii wheel), transits to natal
(sorted by power), synastry/compatibility grid, and lore (golden dawn
correspondences, sephiroth, lunar mansions).

## run

needs the `astrolog` binary on `PATH` (override with `ASTROLOG_BIN`).
people are stored as astrolog `.chart` files in `~/.astro-tui/people`
(override with `ASTRO_TUI_DATA`).

```sh
# pip path
pip install .
astro-tui

# nix path
nix run github:dudeagent/astro-tui

# dev shell (astrolog + pytest included)
nix develop -c python -m pytest tests/
```

astrolog has no timezone database, so birth times are stored with an explicit
utc offset (e.g. `-6`) and dst flag — add-person prompts for both. note the
zone string format is `6W` style (west positive) per astrolog convention.

## structure

- `astro_tui/astrolog.py` — subprocess wrapper + parsers for `-v` positions, `-a` aspects, `-Tn` transits, synastry grids, chart-file create/parse round-trip
- `astro_tui/lore.py` — golden dawn sign/planet correspondences (sephiroth, divine names), 28 lunar mansions with degree-span lookup
- `astro_tui/app.py` — textual TUI

## roadmap

- map ui for birth location picking
- decan rulerships for ritual timing
- graphic chart rendering for a second screen
