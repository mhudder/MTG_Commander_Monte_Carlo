#!/usr/bin/env python3
"""`check_unchanged_decks` says which trees it compared, and refuses a stale
one (§0z137).

    python -m tests.test_check_unchanged
    python -m tests.test_check_unchanged --mutate   # 5 mutations, exact sets

The recipe is a worktree at the old commit, a measurement in each tree and a
diff. `git worktree add` fails when the directory is already there, and the
old side is then measured in whatever commit an earlier session left it at;
on 2026-10-14 that read as six decks MOVED, about a change nobody made. Each
`--out` now records its tree, and `--diff --old-at=<ref>` refuses a pair
whose old side is not that commit, clean, at the new side's N and turns.

CASES
  A  `provenance` records this tree's HEAD, a dirty flag, N, turns and cfg
  B  a matching pair passes, `--cfg` differing included
  C  an old side at another commit is refused under --old-at
  D  an old side with no provenance is refused under --old-at, and passes
     without it (the files written before this check still diff)
  E  different N on the two sides is refused, --old-at or not
  F  an old side with uncommitted changes is refused under --old-at
  G  end to end: `diff` on two files returns the refusal, and nothing for
     a valid pair

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  --old-at is ignored                                  -> C, D, F, G
  N and turns are not compared                         -> E
  a dirty old tree is accepted                         -> F
  provenance records no commit                         -> A
  check_sides finds nothing                            -> C, D, E, F, G
"""
import json
import os
import subprocess
import sys
import tempfile

import tools.check_unchanged_decks as CU

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def side(commit, dirty=False, n=400, turns=20, cfg=None):
    return {"commit": commit, "dirty": dirty, "n": n, "turns": turns,
            "cfg": cfg or {}}


OLD, OTHER = "a" * 40, "b" * 40


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    p = CU.provenance(7, 10, {"rearm_rule": "reland"})
    check("A provenance: HEAD, dirty flag, N, turns, cfg",
          (p["commit"], isinstance(p["dirty"], bool), p["n"], p["turns"],
           p["cfg"]),
          (head, True, 7, 10, {"rearm_rule": "'reland'"}))

    check("B a matching pair passes, a differing cfg included",
          CU.check_sides(side(OLD), side(OTHER, dirty=True,
                                         cfg={"x": "1"}), OLD), [])

    check("C an old side at another commit is refused",
          len(CU.check_sides(side(OTHER), side(OTHER), OLD)), 1)

    check("D no provenance: refused under --old-at, passes without",
          (len(CU.check_sides(None, side(OTHER), OLD)),
           CU.check_sides(None, side(OTHER), None)),
          (1, []))

    check("E different N is refused, with or without --old-at",
          (len(CU.check_sides(side(OLD, n=400), side(OTHER, n=2000), OLD)),
           len(CU.check_sides(side(OLD, n=400), side(OTHER, n=2000)))),
          (1, 1))

    check("F a dirty old tree is refused under --old-at",
          len(CU.check_sides(side(OLD, dirty=True), side(OTHER), OLD)), 1)

    deck = CU.DECKS[0]
    row = {m: 1.0 for m in CU.METRICS}
    out = []
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, commit in (("old", OTHER), ("new", OTHER)):
            path = os.path.join(d, f"{name}.json")
            json.dump({deck: row, CU.PROVENANCE: side(commit)},
                      open(path, "w"))
            paths.append(path)
        devnull = open(os.devnull, "w")
        real, sys.stdout = sys.stdout, devnull
        try:
            out.append(len(CU.diff(*paths, old_at=OLD)))
            out.append(len(CU.diff(*paths, old_at=OTHER)))
        finally:
            sys.stdout = real
            devnull.close()
    check("G diff returns the refusal for a stale old side, none when valid",
          out, [1, 0])

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("check_unchanged_decks says which trees it compared (§0z137)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_sides, real_prov = CU.check_sides, CU.provenance

    def no_size(old_p, new_p, old_at=None):
        if old_p and new_p:
            old_p = dict(old_p, n=None, turns=None)
            new_p = dict(new_p, n=None, turns=None)
        return real_sides(old_p, new_p, old_at)

    def clean(old_p, new_p, old_at=None):
        return real_sides(old_p and dict(old_p, dirty=False), new_p, old_at)

    muts = {
        "--old-at is ignored":
            ({"C", "D", "F", "G"}, CU, "check_sides",
             lambda o, n, old_at=None: real_sides(o, n, None)),
        "N and turns are not compared":
            ({"E"}, CU, "check_sides", no_size),
        "a dirty old tree is accepted":
            ({"F"}, CU, "check_sides", clean),
        "provenance records no commit":
            ({"A"}, CU, "provenance",
             lambda n, t, e: dict(real_prov(n, t, e), commit=None)),
        "check_sides finds nothing":
            ({"C", "D", "E", "F", "G"}, CU, "check_sides",
             lambda o, n, old_at=None: []),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
