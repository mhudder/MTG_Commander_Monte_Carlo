"""trostani's ledger entries and swap-in catalog.

DATA ONLY. `edhmc/pending.py` gathers these lists from every deck's
module (in `edhmc/registry.py`'s order) and holds the logic and the
checks; `docs/LEDGER_STATES.md` defines the states. Split out of
`pending.py` on 2026-10-11 so that editing one deck's entries does not
mean paging through every deck's. ORDER WITHIN A LIST IS MEANINGFUL:
`build_pending` applies CHANGES in this order, and the cache fingerprint
hashes it. Every entry here must name this deck; the package refuses one
that does not (`edhmc/ledger/__init__.py`).
"""

from __future__ import annotations

from edhmc.decks import trostani_v1


COMMITTED: list[Change] = []


MEASURED: list[Candidate] = []


CHANGES: list[Change] = []


WITHDRAWN: list[Change] = []


SIMULATED: list[Simulated] = []


PROPOSED: list[Proposal] = []


# Added 2026-10-01 from the owner's spreadsheet. No candidates yet: the
# catalog is empty, which the registry check above allows.
CATALOG = (trostani_v1, {})
