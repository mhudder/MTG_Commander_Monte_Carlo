#!/usr/bin/env python3
"""The ledger's data is one module per deck, and its filing is checked.

    python -m tests.test_ledger_split
    python -m tests.test_ledger_split --mutate   # 2 mutations, exact sets

`edhmc/pending.py` was 394 KB, nine tenths of it entries; since 2026-10-11 the
entries live in `edhmc/ledger/<deck>.py` and `pending.py` gathers them. What
the split must not change is the ORDER within a deck -- `build_pending`
applies a deck's CHANGES in it and the cache fingerprint hashes it -- and what
it adds is a new way to be wrong: an entry filed in another deck's file, which
would still be applied to the deck it names, in an order nobody chose.

CASES
  A deck_modules() has one module per registered deck, in the registry's order
  B an entry filed under the wrong deck is refused (ValueError)
  C a registered deck with no ledger module is refused (ImportError)
  D a ledger module with no registered deck is refused (ImportError)
  E the gathered lists are grouped in registry order, and each deck's CHANGES
    are pending_for's order -- the order build_pending applies
  F pending.DECKS is each ledger module's CATALOG

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  filing is not checked                     -> B, C, D
  the deck modules come back sorted by name -> A, E

UNMUTATED (§0z15): F, because nothing in the package reorders or rebuilds a
catalog -- it is the plain pass-through the mutations do not touch.
"""
import sys
import types

import edhmc.ledger as L
import edhmc.pending as P
from edhmc.registry import DECKS as REGISTRY

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    return False


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    mods = L.deck_modules()
    check("A one module per deck, registry order", list(mods), list(REGISTRY))

    real = dict(mods)
    misfiled = types.SimpleNamespace(**{lst: list(getattr(real["karlov"], lst))
                                        for lst in L.LISTS})
    misfiled.CHANGES = misfiled.CHANGES + [P.Change(
        deck="azusa", remove="Forest", add="Fabled Passage", staged="test",
        rationale="filed in karlov's file on purpose")]
    bad = dict(real, karlov=misfiled)
    check("B a mis-filed entry is refused",
          raises(lambda: L.check_filing(bad, set(REGISTRY)), ValueError), True)
    check("C a deck with no module is refused",
          raises(lambda: L.check_filing(real, set(REGISTRY) - {"azusa"}),
                 ImportError), True)
    check("D a module with no deck is refused",
          raises(lambda: L.check_filing(real, set(REGISTRY) | {"phantom"}),
                 ImportError), True)

    gathered = L.gather("CHANGES")
    groups = []
    for x in gathered:
        if not groups or groups[-1] != x.deck:
            groups.append(x.deck)
    in_order = [d for d in REGISTRY if any(x.deck == d for x in gathered)]
    per_deck = all([c for c in gathered if c.deck == d] == P.pending_for(d)
                   for d in REGISTRY)
    check("E grouped in registry order; each deck's CHANGES in pending_for's order",
          (groups, per_deck), (in_order, True))
    check("F pending.DECKS is each module's CATALOG",
          all(P.DECKS[d] is m.CATALOG for d, m in real.items()), True)
    return set(FAIL)


def main():
    if not MUTATE:
        print("The ledger's per-deck modules\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {"check_filing": L.check_filing, "deck_modules": L.deck_modules}
    real_mods = L.deck_modules()

    muts = {
        "filing is not checked":
            ({"B", "C", "D"}, "check_filing", lambda mods, on_disk: None),
        "the deck modules come back sorted by name":
            ({"A", "E"}, "deck_modules",
             lambda: dict(sorted(real_mods.items()))),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(L, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(L, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
