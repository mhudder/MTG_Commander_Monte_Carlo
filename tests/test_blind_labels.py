#!/usr/bin/env python3
"""A KNOWN_BLIND card the engine acts on must say so (§0z78).

    python -m tests.test_blind_labels
    python -m tests.test_blind_labels --mutate   # 3 mutations, exact sets

`KNOWN_BLIND` is a hand-maintained name set, and §0q says those rot: the
triage back-test (§0z66) found 33 of its cards playing differently from a
blank matched on cost, types, body, priority and threat. 27 were relabelled;
six stay blind with a written reason in `BLIND_BUT_LIVE`. This test is the
back-test's label half made permanent, and it asks the question exactly:
under common random numbers a card the engine cannot see plays IDENTICALLY,
seed for seed, to its matched blank (`tools.triage.plays_identically`).

ONE CASE PER KNOWN_BLIND CARD IN A LIST (`build_pending`, lands skipped),
named "deck card". It FAILS when
  - the engine acts on the card and `BLIND_BUT_LIVE` has no reason for it
    (the label rotted: relabel it, or write down why it stays blind), or
  - `BLIND_BUT_LIVE` has a reason for a card the engine no longer acts on
    (the reason rotted).

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Rhystic Study's reason is deleted              -> tivit Rhystic Study
  Village Rites is put back in KNOWN_BLIND       -> rendmaw Village Rites
  Propaganda (inert: a tag nothing reads, §0z12)
    is given a BLIND_BUT_LIVE reason             -> tivit Propaganda

What this cannot see: a KNOWN_BLIND card the engine acts on only past the
40 seeds, or only at another horizon. The back-test used the same 40.
"""
import sys

import tools.ablation as AB
from edhmc.pending import build_pending
from tools.triage import plays_identically

MUTATE = "--mutate" in sys.argv
SEEDS = range(5000, 5040)
_SAME = {}


def identical(deck_name, card):
    key = (deck_name, card.name)
    if key not in _SAME:
        _SAME[key] = plays_identically(deck_name, card, SEEDS)
    return _SAME[key]


def run_cases(verbose=True):
    fail, n = set(), 0
    for deck_name in AB.SCRIPTED_BY_DECK:
        deck, _ = build_pending(deck_name)
        live_ok = AB.BLIND_BUT_LIVE.get(deck_name, {})
        for c in deck:
            if c.is_land or c.name not in AB.KNOWN_BLIND[deck_name]:
                continue
            n += 1
            same, why = identical(deck_name, c)
            label = f"{deck_name} {c.name}"
            if not same and c.name not in live_ok:
                fail.add(label)
                if verbose:
                    print(f"  FAIL  {label}: the engine acts on it ({why}) "
                          f"and BLIND_BUT_LIVE has no reason")
            elif same and c.name in live_ok:
                fail.add(label)
                if verbose:
                    print(f"  FAIL  {label}: BLIND_BUT_LIVE has a reason, and "
                          f"it plays identically to its matched blank")
    if verbose:
        print(f"\n{n - len(fail)} passed, {len(fail)} failed "
              f"({n} KNOWN_BLIND cards across {len(AB.SCRIPTED_BY_DECK)} decks)")
    return fail


def main() -> int:
    if not MUTATE:
        print("KNOWN_BLIND cards against their matched blanks\n")
        return 1 if run_cases() else 0

    print("MUTATION RUN -- exact sets\n")
    live, blind = AB.BLIND_BUT_LIVE, AB.KNOWN_BLIND

    def drop_rhystic():
        del live["tivit"]["Rhystic Study"]

    def rites_back():
        blind["rendmaw"].add("Village Rites")

    def propaganda_live():
        live["tivit"]["Propaganda"] = "a reason for a card nothing reads"

    muts = {
        "Rhystic Study's reason is deleted":
            ({"tivit Rhystic Study"}, drop_rhystic),
        "Village Rites is put back in KNOWN_BLIND":
            ({"rendmaw Village Rites"}, rites_back),
        "Propaganda is given a BLIND_BUT_LIVE reason":
            ({"tivit Propaganda"}, propaganda_live),
    }
    bad = 0
    for label, (want, apply) in muts.items():
        print(f"-- {label}")
        saved = ({k: dict(v) for k, v in live.items()},
                 {k: set(v) for k, v in blind.items()})
        apply()
        try:
            broke = run_cases(verbose=False)
        finally:
            live.clear(); live.update(saved[0])
            blind.clear(); blind.update(saved[1])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
