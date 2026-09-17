"""ONE registry of the decks this project simulates (§0z32, M6).

`DECKS` maps a deck's short name to a `DeckSpec`: which engine simulates it,
its colour identity, the metric columns its ablation table prints, and the
engine files its cache fingerprint depends on. Everything that used to keep
its own per-deck dict -- `tools/ablation.py`'s SIMS and METRIC_SETS,
`tools/cache_manifest.py`'s PER_DECK, `tools/check_unchanged_decks.py`,
`tools/status.py`, `edhmc/pending.py`'s DECK_IDENTITY, the tests' ENGINES
maps -- reads this instead. Adding a seventh deck is one `DeckSpec` here
plus the things that are GENUINELY per-deck decisions and cannot be derived:
`ablation.py`'s SCRIPTED/PARTLY/KNOWN_BLIND classification (a claim about
the engine), `pending.py`'s candidate catalog, and a `validate.py` A/A case.

The deck MODULE is not named here: `edhmc.decks.discover_current_decks()`
finds the highest-numbered `<name>_v<N>.py`, and this registry is checked
against it at import -- a deck module with no spec, or a spec with no
module, raises. That is the §0q rule (a hand-maintained name set gets a
derivation check in the same file), applied to the registry itself.

Engine modules are imported lazily, on first use of `.sim`, so importing
this module costs nothing and creates no cycle: `pending.py` imports it for
the identities, and the engines never import `pending.py`.
"""
from __future__ import annotations

import importlib
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DeckSpec:
    name: str
    engine: str                 # module under edhmc/ whose simulate() runs it
    identity: frozenset         # colour identity, for check_proposals()
    metrics: tuple              # the ablation table's metric columns
    extra_files: tuple = ()     # engine files beyond edhmc/<engine>.py

    @property
    def engine_module(self):
        return importlib.import_module(f"edhmc.{self.engine}")

    @property
    def sim(self):
        return self.engine_module.simulate

    @property
    def module(self):
        """The current deck module (`edhmc.decks.<name>_v<N>`)."""
        from edhmc.decks import discover_current_decks
        return discover_current_decks()[self.name]

    def build(self):
        return self.module.build()

    @property
    def fingerprint_files(self) -> list[str]:
        """The per-deck half of the cache fingerprint: the engine file (unless
        it is engine.py, which is SHARED), any extra engine files, and the
        deck module. Paths are repo-relative with forward slashes, exactly as
        `cache_manifest.PER_DECK` spelt them, so no fingerprint moved when
        the lists were derived instead of typed."""
        files = []
        if self.engine != "engine":
            files.append(f"edhmc/{self.engine}.py")
        files.extend(self.extra_files)
        rel = os.path.relpath(self.module.__file__, os.getcwd())
        files.append(rel.replace(os.sep, "/"))
        return files


DECKS: dict[str, DeckSpec] = {
    "rendmaw": DeckSpec(
        "rendmaw", "engine", frozenset("BG"),
        ("damage", "cards_drawn", "tokens_made", "rendmaw_triggers", "won")),
    "lorehold": DeckSpec(
        "lorehold", "lorehold", frozenset("RW"),
        ("mv_cheated", "damage", "miracles_cast", "total_mv_cast", "won")),
    "karlov": DeckSpec(
        "karlov", "karlov", frozenset("BW"),
        ("damage", "lifegain_triggers", "final_life", "cards_drawn", "won")),
    # artifacts_made is this deck's mv_cheated: the proxy the engine is built
    # around. It is NOT the objective -- follow win rate where they disagree.
    "tivit": DeckSpec(
        "tivit", "tivit", frozenset("BUW"),
        ("damage", "artifacts_made", "tivit_triggers", "votes_cast", "won"),
        extra_files=("edhmc/voting.py",)),
    "shilgengar": DeckSpec(
        "shilgengar", "shilgengar", frozenset("BW"),
        ("damage", "blood_made", "creatures_sacrificed",
         "single_reanimations", "won")),
    "azusa": DeckSpec(
        "azusa", "azusa", frozenset("G"),
        ("damage", "landfall_triggers", "lands_played", "tokens_made", "won")),
}


def check_registry_matches_disk() -> None:
    """Raise if the registry and the deck modules on disk disagree."""
    from edhmc.decks import discover_current_decks
    on_disk = set(discover_current_decks())
    here = set(DECKS)
    if on_disk != here:
        raise ImportError(
            f"edhmc/registry.py disagrees with edhmc/decks/: "
            f"modules with no DeckSpec {sorted(on_disk - here)}, "
            f"specs with no module {sorted(here - on_disk)}. "
            f"Add the DeckSpec (or delete the stale one) -- §0q.")


check_registry_matches_disk()
