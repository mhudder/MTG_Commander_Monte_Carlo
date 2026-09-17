#!/usr/bin/env python3
"""§0z31 — a staged or proposed cut is a card whose ablation row was evidence.

    python -m tests.test_pending_cuts
    python -m tests.test_pending_cuts --mutate   # 4 mutations, exact sets

WHAT IS BEING PINNED. `pending.check_cuts_are_measured` classifies every
STAGED cut and every PROPOSED cut with `tools/ablation.py`'s sets, in the
deck's MODULE list (a staged cut has already left the staged list, which is
why `check_scripted_coverage` never saw one). A MODEL-BLIND or PARTLY
MODELLED cut is refused unless `cut_unmeasured` says why it is cut anyway;
a cut in no category is refused outright; a land cut passes with a note.
This is the trap behind the two withdrawn swaps (§0z, §0z2), made a check
the day `ablation.py` became importable (M4, §0z31).

CASES
  A  the live ledger passes, and every line names a classification
  B  a blind cut with no acknowledgement is refused
  C  the same cut, acknowledged, passes and prints the acknowledgement
  D  a cut in no category is refused
  E  a basic-land cut passes with the land note

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets. Each drops one branch of the
check and must break exactly the cases that branch decides:
  the blind branch never refuses       -> B and C
  the acknowledgement is ignored       -> A and C
  unclassified is treated as evaluated -> D only
  a land is treated as unclassified    -> A and E

THE FIRST EXPECTATION WAS WRONG (B only, C only, E only) and the way it was
wrong is worth keeping: case A runs the LIVE ledger, and the live ledger
contains an acknowledged blind cut (Soulmender) and two land cuts (Plains,
Swamp), so ignoring the acknowledgement or misreading a land refuses the
real ledger too; and C asserts the acknowledgement is PRINTED, which needs
the blind branch that the first mutation removes. Corrected before the
second run; a set edited to match the output would be a transcript.
"""
import sys

import edhmc.pending as P
from edhmc.pending import Change, Candidate

MUTATE = "--mutate" in sys.argv
passed = failed = 0
FAILED = []


def check(name, got, want=True):
    global passed, failed
    ok = got == want
    passed += ok
    failed += (not ok)
    if not ok:
        FAILED.append(name)
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + ("" if ok else f"  got {got!r}"))


def outcome(changes, candidates=()):
    try:
        return "ok", P.check_cuts_are_measured(changes, list(candidates))
    except AssertionError as exc:
        return "refused", str(exc)


def a_blind_karlov_card():
    """A KNOWN_BLIND karlov card that is in the module list and not staged."""
    import tools.ablation as AB
    module, _ = P.DECKS["karlov"]
    deck, _ = module.build()
    staged_out = {c.remove for c in P.CHANGES if c.deck == "karlov"}
    for c in deck:
        if (c.name in AB.KNOWN_BLIND["karlov"] and not c.is_land
                and c.name not in staged_out):
            return c.name
    raise SystemExit("no unstaged KNOWN_BLIND karlov card to test with")


def run_cases(classify):
    global FAILED
    FAILED = []
    saved = P.classify_cut
    P.classify_cut = classify
    try:
        # A: the live ledger
        status, lines = outcome(P.CHANGES, P.MEASURED)
        check("A the live ledger passes and every line is classified",
              status == "ok" and all(
                  any(k in ln for k in ("MODEL-EVALUATED", "MODEL-BLIND",
                                        "PARTLY MODELLED", "LAND"))
                  for ln in lines))
        blind = a_blind_karlov_card()
        fake = Change(deck="karlov", remove=blind, add="X", staged="today",
                      rationale="test")
        status, text = outcome([fake])
        check("B a blind cut with no acknowledgement is refused",
              status == "refused" and "MODEL-BLIND" in text)
        acked = Change(deck="karlov", remove=blind, add="X", staged="today",
                       rationale="test", cut_unmeasured="because reasons")
        status, lines = outcome([acked])
        check("C the same cut, acknowledged, passes and prints why",
              status == "ok" and any("because reasons" in ln for ln in lines))
        status, text = outcome([Change(deck="karlov", remove="Not A Card",
                                       add="X", staged="today", rationale="t")])
        check("D a cut in no category is refused",
              status == "refused")
        status, lines = outcome([Change(deck="karlov", remove="Swamp", add="X",
                                        staged="today", rationale="t")])
        check("E a basic-land cut passes with the land note",
              status == "ok" and any("LAND" in ln for ln in lines))
    finally:
        P.classify_cut = saved
    return {n.split(" ")[0] for n in FAILED}


# --- mutations of classify_cut: each disables one branch of the decision
def blind_never_refuses(deck, card):
    r = _REAL(deck, card)
    return "evaluated" if r == "blind" else r


def unclassified_as_evaluated(deck, card):
    r = _REAL(deck, card)
    return "evaluated" if r in ("unclassified", "absent") else r


def land_as_unclassified(deck, card):
    r = _REAL(deck, card)
    return "unclassified" if r == "land" else r


_REAL = P.classify_cut


def main() -> int:
    if not MUTATE:
        print("§0z31 -- staged and proposed cuts are classified\n")
        run_cases(_REAL)
        print(f"\n{passed} passed, {failed} failed")
        return 1 if failed else 0

    print("MUTATION RUN -- exact sets\n")
    # "the acknowledgement is ignored" mutates the CHECK, not the classifier:
    # wrap check_cuts_are_measured so every item reads as unacknowledged.
    def ignore_ack(changes=None, candidates=None):
        import dataclasses
        ch = [dataclasses.replace(c, cut_unmeasured="") for c in
              (P.CHANGES if changes is None else changes)]
        return _REAL_CHECK(ch, candidates)
    _REAL_CHECK = P.check_cuts_are_measured
    mutations = {
        "the blind branch never refuses": (blind_never_refuses, None),
        "the acknowledgement is ignored": (_REAL, ignore_ack),
        "unclassified is treated as evaluated": (unclassified_as_evaluated, None),
        "a land is treated as unclassified": (land_as_unclassified, None),
    }
    expected = {
        "the blind branch never refuses": {"B", "C"},
        "the acknowledgement is ignored": {"A", "C"},
        "unclassified is treated as evaluated": {"D"},
        "a land is treated as unclassified": {"A", "E"},
    }
    bad = 0
    for label, (classify, check_fn) in mutations.items():
        print(f"-- {label}")
        if check_fn is not None:
            P.check_cuts_are_measured = check_fn
        try:
            broke = run_cases(classify)
        finally:
            P.check_cuts_are_measured = _REAL_CHECK
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed  "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
