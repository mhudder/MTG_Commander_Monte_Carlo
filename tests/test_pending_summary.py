#!/usr/bin/env python3
"""The ledger's default view is short, and loses no check (2026-10-10/11).

    python -m tests.test_pending_summary
    python -m tests.test_pending_summary --mutate   # 5 mutations, exact sets

`python -m edhmc.pending` printed the whole ledger, evidence and all: 165 KB,
about forty thousand tokens, for a command CLAUDE.md sends every session to
for three lines of legality. On 2026-10-10 it printed `summary()`, one line
per entry, 19 KB; on 2026-10-11 the default became `check_view()`, the checks,
legality and staged cuts with every other state as a count, under 2 KB, and
the one-line-per-entry view moved behind `--summary`. What must not move with
either is any CHECK: legality on every deck, every staged change named.

CASES (A-C run the default, `main([])`; G-H run `main(["--summary"])`)
  A the default prints a legality line for EVERY deck, including the decks
    with nothing staged (the full ledger only printed decks with something
    staged)
  B the default names every staged change as `-OUT +IN`
  C the default is under a quarter the size of `--summary`
  D `--card conqueror` keeps karlov's Conqueror swap and drops azusa's Forest
  E `--deck karlov` keeps a karlov entry and drops an azusa one
  F an unknown `--deck` is refused, not silently empty
  G `--summary` names every MEASURED card
  H `--summary` is under a quarter the size of the full ledger

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the default goes back to --summary           -> C
  the default goes back to the full ledger     -> A, C
  --summary goes back to the full ledger       -> H
  --card is ignored                            -> D
  --deck is ignored                            -> E, F (nothing left to refuse)

UNMUTATED (§0z15): B holds under every view, and G under the full ledger
too, so no mutation here can break them alone.
"""
import contextlib
import io
import sys

import edhmc.pending as P

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def captured(fn, *args, **kw) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kw)
    return buf.getvalue()


def full() -> str:
    return captured(P.ledger) + captured(P.print_proposals)


FULL = None


def run_cases():
    global PASS, FAIL, FULL
    PASS, FAIL = [], []
    FULL = FULL or full()
    out = captured(P.main, [])
    summ = captured(P.main, ["--summary"])
    legal = {d for d in P.DECKS
             if f"  {d:<10} -> 100 cards, singleton-legal" in out}
    check("A a legality line for every deck", sorted(legal), sorted(P.DECKS))
    missing = [f"-{c.remove} +{c.add}" for c in P.CHANGES
               if f"-{c.remove} +{c.add}" not in out]
    check("B every staged change named", missing, [])
    check("C the default under a quarter of --summary",
          len(out) * 4 < len(summ), True)
    keep = P._filter(["--card", "conqueror"])
    check("D --card keeps the Conqueror, drops a Forest",
          (keep("karlov", "Soulmender", "Bloodthirsty Conqueror"),
           keep("azusa", "Forest", "Fabled Passage")), (True, False))
    keep = P._filter(["--deck", "karlov"])
    check("E --deck keeps karlov, drops azusa",
          (keep("karlov", "Soulmender", "Bloodthirsty Conqueror"),
           keep("azusa", "Forest", "Fabled Passage")), (True, False))
    try:
        P._filter(["--deck", "nope"])
        refused = False
    except SystemExit:
        refused = True
    check("F an unknown deck is refused", refused, True)
    absent = [c.card for c in P.MEASURED if c.card not in summ]
    check("G --summary names every measured card", absent, [])
    check("H --summary under a quarter of the full ledger",
          len(summ) * 4 < len(FULL), True)
    return set(FAIL)


def main():
    if not MUTATE:
        print("The ledger's default view\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {"summary": P.summary, "check_view": P.check_view,
            "_filter": P._filter}

    def without(flag):
        """`_filter` as if `flag` and its value had never been passed."""
        def f(args):
            if flag not in args:
                return real["_filter"](args)
            i = args.index(flag)
            return real["_filter"](args[:i] + args[i + 2:])
        return f

    muts = {
        "the default goes back to --summary":
            ({"C"}, "check_view", real["summary"]),
        "the default goes back to the full ledger":
            ({"A", "C"}, "check_view",
             lambda: (P.ledger(), P.print_proposals())),
        "--summary goes back to the full ledger":
            ({"H"}, "summary",
             lambda: (P.ledger(), P.print_proposals())),
        "--card is ignored": ({"D"}, "_filter", without("--card")),
        "--deck is ignored": ({"E", "F"}, "_filter", without("--deck")),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(P, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(P, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
