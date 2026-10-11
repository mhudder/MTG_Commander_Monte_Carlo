"""The ledger's DATA: one module per deck, gathered by `edhmc/pending.py`.

    edhmc/ledger/records.py    Change, Candidate, Simulated, Proposal
    edhmc/ledger/<deck>.py     that deck's COMMITTED, MEASURED, CHANGES,
                               WITHDRAWN, SIMULATED and PROPOSED lists, and
                               its swap-in CATALOG

WHY IT IS SPLIT (2026-10-11). `pending.py` was 394 KB, nine tenths of it
entries, and every session that staged a swap or recorded a number paged
through all seven decks' evidence to edit one. The logic and the checks stay
in `pending.py`, which rebuilds the same six module-level lists from here, so
nothing that imports the ledger changed.

ORDER. A gathered list holds the decks in `edhmc/registry.py`'s order, each
deck's entries in its own file's order. Only the order WITHIN a deck carries
meaning -- `build_pending` applies that deck's CHANGES in it, `up_to=n` slices
it, and the cache fingerprint hashes it -- and it is exactly what it was. The
interleaving ACROSS decks, which nothing read, is now grouped by deck.

FILING IS CHECKED, not trusted (§0q). Every registered deck must have a module
here and every module here a registered deck, and an entry must name the deck
whose file it is in: an entry filed in the wrong file would still be applied
to the deck it names, but in an order no one chose.
"""

from __future__ import annotations

import importlib
import os

from edhmc.registry import DECKS as REGISTRY

LISTS = ("COMMITTED", "MEASURED", "CHANGES", "WITHDRAWN", "SIMULATED",
         "PROPOSED")
HERE = os.path.dirname(os.path.abspath(__file__))
NOT_DECKS = {"__init__", "records"}


def check_filing(modules: dict, on_disk: set[str]) -> None:
    """Raise unless the deck modules and the registry match, and every entry
    is in the file of the deck it names. Takes its inputs as arguments so a
    test can hand it a mis-filed copy."""
    missing = sorted(set(REGISTRY) - on_disk)
    extra = sorted(on_disk - set(REGISTRY))
    if missing or extra:
        raise ImportError(f"edhmc/ledger/ does not match edhmc/registry.py: "
                          f"no module for {missing}, no deck for {extra}")
    wrong = [f"{name}.{lst}: {x.deck!r}"
             for name, mod in modules.items() for lst in LISTS
             for x in getattr(mod, lst) if x.deck != name]
    if wrong:
        raise ValueError("ledger entries filed under the wrong deck: "
                         + "; ".join(wrong))


def deck_modules() -> dict:
    """{deck: its ledger module}, in the registry's order, checked."""
    on_disk = {f[:-3] for f in os.listdir(HERE)
               if f.endswith(".py") and f[:-3] not in NOT_DECKS}
    mods = {d: importlib.import_module(f"edhmc.ledger.{d}")
            for d in REGISTRY if d in on_disk}
    check_filing(mods, on_disk)
    return mods


def gather(name: str) -> list:
    """One ledger list across every deck: registry order, file order."""
    return [x for mod in deck_modules().values() for x in getattr(mod, name)]


def catalogs() -> dict:
    """{deck: (deck module, {card name: Card})}, pending.DECKS' shape."""
    return {d: mod.CATALOG for d, mod in deck_modules().items()}
