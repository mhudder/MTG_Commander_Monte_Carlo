#!/usr/bin/env python3
"""The ledger's SIMULATED/STAGED split and the PREPARED flag (§0z79).

    python -m tests.test_ledger_states
    python -m tests.test_ledger_states --mutate   # 3 mutations, exact sets

docs/LEDGER_STATES.md designed both and the owner confirmed the split on
2026-09-22: a head-to-head against a named cut is EVIDENCE (SIMULATED), and
putting the swap in is a DECISION (STAGED). A staged Change's head-to-head is
its `evidence`, derived as `Change.simulated`; SIMULATED holds the rest.

CASES
  A  the real ledger passes `check_simulated`
  B  a SIMULATED record that is also staged is refused
  C  a staged Change with no evidence is refused
  D  a SIMULATED record with no result is refused
  E  PREPARED naming a test on disk passes
  F  PREPARED naming a file that does not exist is refused
  G  `Change.simulated` carries the Change's evidence as its result
  H  check_docs derives SIMULATED and PREPARED from pending.py

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the "not both SIMULATED and staged" rule is off    -> B
  the "staged needs evidence" rule is off            -> C
  PREPARED is never checked                          -> F

THE FIRST RUN FAILED E, AND THE CODE WAS WRONG, NOT THE EXPECTATION.
`check_prepared` split the note on whitespace, so "tests/x.py, 2026-09-29"
became "tests/x.py," -- which does not end in ".py" -- and a real test was
refused. It matches the path now. (The two mutation sets that also broke E
on that run were right about everything else.)

UNMUTATED (§0z15): A is the real data; D, G and H are neighbours -- the
completeness rule, the derivation, and the doc check's input.
"""
import sys

import edhmc.pending as P
import tools.check_docs as CD

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def refused(fn, *a) -> bool:
    try:
        fn(*a)
    except AssertionError:
        return True
    return False


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A the real ledger passes", refused(P.check_simulated), False)
    ch = P.Change(deck="karlov", remove="X", add="Y", staged="2026-09-29",
                  rationale="r", evidence="+0.01 +-0.002 at T10 and T20")
    dup = P.Simulated(deck="karlov", remove="X", add="Y",
                      measured="2026-09-29", result="+0.01 at T20")
    check("B simulated AND staged is refused",
          refused(P.check_simulated, [dup], [ch]), True)
    bare = P.Change(deck="karlov", remove="X", add="Y", staged="2026-09-29",
                    rationale="r")
    check("C staged with no evidence is refused",
          refused(P.check_simulated, [], [bare]), True)
    empty = P.Simulated(deck="karlov", remove="X", add="Z",
                        measured="2026-09-29", result="")
    check("D a SIMULATED record with no result is refused",
          refused(P.check_simulated, [empty], [ch]), True)
    base = dict(deck="karlov", card="Test Card", cost="{1}", identity="",
                type_line="Artifact", oracle="text", verified="2026-09-29",
                rationale="r", implement="i")
    ok = P.Proposal(**base, prepared="tests/test_ledger_states.py, 2026-09-29")
    check("E PREPARED naming a test on disk passes",
          refused(P.check_prepared, ok), False)
    bad = P.Proposal(**base, prepared="tests/test_no_such_file.py")
    check("F PREPARED naming a missing test is refused",
          refused(P.check_prepared, bad), True)
    check("G Change.simulated carries the evidence",
          (ch.simulated.result, ch.simulated.remove), (ch.evidence, "X"))
    check("H check_docs derives SIMULATED and PREPARED",
          {"SIMULATED", "PREPARED"} <= CD.ledger_states(), True)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Ledger states: SIMULATED / STAGED, and PREPARED\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "the not-both rule is off":
            ({"B"}, "_not_simulated_and_staged", lambda sim, st: None),
        "the staged-needs-evidence rule is off":
            ({"C"}, "_staged_have_evidence", lambda st: None),
        "PREPARED is never checked":
            ({"F"}, "check_prepared", lambda pr: None),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(P, name)
        setattr(P, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(P, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
