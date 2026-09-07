"""edhmc.decks — one module per commander, named "<name>_v<N>.py".

`discover_current_decks()` is the registry. It walks this package, keeps only
modules that match the version-suffix convention and expose `build()`, and
resolves each NAME to its highest-numbered version — so `karlov_v1.py` (kept
for history) is automatically shadowed by `karlov_v2.py` with no list to edit.

WHY THIS EXISTS. This project has been burned twice by exactly this class of
bug: `tag_flying.py` used to walk a hand-written `decks = {...}` dict and
missed module-level candidates until a card was silently measured as a ground
creature (2026-09-05), and `ablation.py`'s `SCRIPTED_*` sets have twice gone
stale when a card was added and the set was not. CLAUDE.md's "Hazard: adding a
card to a deck is TWO edits, not one" is that same failure at the card level.
This is the deck-level fix: `audit_cards.py` and `tag_flying.py` both call
`discover_current_decks()` instead of naming decks by hand, so dropping in a
new `<name>_v1.py` with a `build()` gets it Scryfall-checked and evasion-tagged
the next time either script runs, with no registry to remember.

NOT auto-discovered, and this is deliberate rather than an oversight:
`ablation.py` (SCRIPTED_*/KNOWN_BLIND sets are a claim about the ENGINE, which
nothing can verify by import alone), `validate.py`'s A/A control (one hand-
picked real swap per engine), `pending.py`'s per-deck candidate catalog, and
`cache_manifest.py`'s source fingerprints (which files an engine's cache
depends on). Each of those needs a genuine decision a script cannot make for
itself; see HANDOFF.md's "adding a fifth deck" checklist.
"""
import importlib
import pkgutil
import re

_VERSIONED = re.compile(r"^(?P<name>[a-z0-9]+)_v(?P<ver>\d+)$")


def discover_current_decks():
    """{name: module} for the highest-numbered "<name>_v<N>" module in this
    package that exposes build(). Skips private modules (_evasion)."""
    best = {}   # name -> (ver, module)
    for info in pkgutil.iter_modules(__path__):
        m = _VERSIONED.match(info.name)
        if not m:
            continue
        mod = importlib.import_module(f"edhmc.decks.{info.name}")
        if not hasattr(mod, "build"):
            continue
        name, ver = m.group("name"), int(m.group("ver"))
        if name not in best or ver > best[name][0]:
            best[name] = (ver, mod)
    return {name: mod for name, (ver, mod) in best.items()}
