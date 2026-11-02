#!/usr/bin/env python3
"""`tools.deferrals` finds every main-phase veto and reserve, and every one
is classified.

    python -m tests.test_deferrals
    python -m tests.test_deferrals --mutate   # 6 mutations, exact sets

The inventory is the first half of the deferral protocol (the owner,
2026-11-02): WHERE a pilot declines a spell it holds. It is only worth
anything if a new veto cannot arrive unclassified, a removed one cannot
linger, and the lines the census traces are the lines that fire.

CASES
  A the engines' sites and `CLASSES` agree: `check()` is empty
  B a planted veto is found -- a bare `continue`, and one that counts before
    it continues (Proft's shape) -- and a branch that APPENDS an option and
    continues (trostani's Chord dispatch) is not
  C a planted reserve compare in an `if` test is a reserve site, and one
    outside an `if` test is refused
  D a one-line `if X: continue` is refused (the trace could not see it fire)
  E `check()` reports an unclassified site AND a classification naming no
    site: dropping one key and adding a fake one is exactly two problems
  F every veto's fire line is a `continue` in the source TEXT, and every
    reserve's is a line beginning `if` -- the lines the census traces

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  a veto body must be exactly `continue`     -> A, B  (Proft is lost)
  a branch that builds an option is a veto   -> A, B  (Chord is found)
  reserves are not scanned                   -> A, C
  the one-line guard is off                  -> D
  check() ignores stale classifications      -> E
  a veto fires at its `if`, not its continue -> F

UNMUTATED (§0z15): nothing here checks that a category is RIGHT -- that is
the reading recorded in each reason -- or the census's own counting, whose
check is its traced-equals-untraced comparison on every game it plays.
"""
import os
import sys

import tools.deferrals as D

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

PLANT = '''
def main_phase(g):
    while True:
        options = []
        for c in g.hand:
            if c.is_land:
                continue
            if c.name == "X":
                g.m["x"] += 1
                continue
            if c.name == "Chord":
                options.append(c)
                continue
        pick = lookahead_pick(g, options)
'''
RESERVE_IN_IF = '''
def f(g, reserve=0):
    if len(g.units) >= reserve:
        return 1
'''
RESERVE_OUTSIDE = '''
def f(g, reserve=0):
    ok = len(g.units) >= reserve
'''
ONE_LINE = '''
def main_phase(g):
    for c in g.hand:
        if c.is_land: continue
    lookahead_pick(g, [])
'''


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def raises(src):
    try:
        D.scan_source("plant", src)
    except ValueError:
        return True
    return False


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    sites = D.scan()
    check("A the engines' sites and CLASSES agree", D.check(sites), [])

    planted = sorted(s.cond for s in D.scan_source("plant", PLANT))
    check("B a planted veto is found, an option-builder is not", planted,
          sorted(["c.is_land", "c.name == 'X'"]))

    got = [s.kind for s in D.scan_source("plant", RESERVE_IN_IF)]
    check("C a reserve in an if is a site; outside one is refused",
          (got, raises(RESERVE_OUTSIDE)), (["reserve"], True))

    check("D a one-line if/continue is refused", raises(ONE_LINE), True)

    two = [D.Site("veto", "m", "f", cond, 1, 2, "c")
           for cond in ("c.is_land", "c.name == 'X'")]
    classes = {two[0].key: ("NOT_A_CHOICE", "kept"),
               "nowhere.f | False": ("JUDGEMENT", "fake")}
    check("E check() reports unclassified and stale",
          sorted(p.split()[0] for p in D.check(two, classes)),
          ["NAMES", "UNCLASSIFIED"])

    bad = []
    for s in sites:
        with open(os.path.join(D.ROOT, "edhmc", f"{s.module}.py"),
                  encoding="utf-8") as fh:
            text = fh.read().split("\n")[s.fire_line - 1]
        text = text.split("#")[0].strip()
        if s.kind == "veto" and text != "continue":
            bad.append(s.where)
        if s.kind == "reserve" and not text.startswith("if"):
            bad.append(s.where)
    check("F every fire line is the line the census traces", bad[:3], [])
    return set(FAIL)


def main():
    if not MUTATE:
        print("tools.deferrals\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {k: getattr(D, k) for k in
            ("_touches_options", "_names_reserve", "ONE_LINE_GUARD",
             "CHECK_STALE", "scan_source")}

    def fire_at_if(module, src):
        return [D.Site(s.kind, s.module, s.qualname, s.cond, s.line,
                       s.line, s.loop_var)
                for s in real["scan_source"](module, src)]

    muts = {
        "a veto body must be exactly `continue`":
            ({"A", "B"}, "_touches_options", lambda body: len(body) != 1),
        "a branch that builds an option is a veto":
            ({"A", "B"}, "_touches_options", lambda body: False),
        "reserves are not scanned":
            ({"A", "C"}, "_names_reserve", lambda test: False),
        "the one-line guard is off": ({"D"}, "ONE_LINE_GUARD", False),
        "check() ignores stale classifications":
            ({"E"}, "CHECK_STALE", False),
        "a veto fires at its `if`, not its continue":
            ({"F"}, "scan_source", fire_at_if),
    }
    bad = 0
    for label, (want, name, val) in muts.items():
        print(f"-- {label}")
        setattr(D, name, val)
        try:
            broke = run_cases()
        finally:
            setattr(D, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
