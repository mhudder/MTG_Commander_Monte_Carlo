#!/usr/bin/env python3
"""§0z31 — the metrics dict cannot KeyError, and a table re-renders from its cache.

    python -m tests.test_metrics_and_render
    python -m tests.test_metrics_and_render --mutate   # 2 mutations, exact sets

WHAT IS BEING PINNED. M3 and M4 of the 2026-09-17 review, both zero-behaviour
refactors, each with the one property that makes it worth having:

  M3  `engine.Metrics` reads 0 for a key nothing has written, so
      `g.m["x"] += 1` on a metric missing from an engine's literal is a
      count and not a KeyError in a worker twenty minutes into a run. Every
      engine's `simulate()` returns one, so `experiment.analyse` finds a
      metric on both branches even when only one branch's games touched it.
      A missing key is not inserted on read: `dict(m)` is what the game
      recorded.

  M4  `tools/ablation.py` is importable with no argv and its table is a pure
      function of a cache and the classification sets (`render_table`). So
      the §0z4 check -- re-render the committed table from the committed
      cache and diff -- is a test now, over every deck with a cache: the
      table on disk IS the cache on disk, byte for byte. This fails when a
      cache is regenerated and the table is not, when a classification
      moves a row between sections and nobody re-renders, and when the
      renderer changes what it prints.

CASES
  A  Metrics: a missing key reads 0, is not inserted, and += works on it
  B  every engine's simulate() returns a Metrics
  C  every committed table re-renders byte-identical from its cache

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  a plain dict in place of Metrics        -> A only (B is only checked on the
                                             live engines, which are not mutated)
  one card moved to KNOWN_BLIND (rendmaw) -> C only, and only for rendmaw
"""
import os
import sys

import edhmc.engine as ENG
import edhmc.lorehold as LH
import edhmc.karlov as KV
import edhmc.tivit as TV
import edhmc.shilgengar as SH
import edhmc.azusa as AZ
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS as REGISTRY
import tools.ablation as AB

MUTATE = "--mutate" in sys.argv
ENGINES = {name: spec.engine_module for name, spec in REGISTRY.items()}
N, HORIZONS = 15000, (10, 20)     # the committed tables' identity

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


def case_a(cls):
    m = cls({"seeded": 3})
    try:
        read = m["never_written"]           # a plain dict raises HERE --
    except KeyError:                        # the failure this class removes
        read = "KeyError"
    inserted = "never_written" in m
    try:
        m["also_never"] += 2
        plus = m["also_never"]
    except KeyError:
        plus = "KeyError"
    check("A a missing metric reads 0, is not inserted by the read, and += works",
          (read, inserted, plus, dict(m)),
          (0, False, 2, {"seeded": 3, "also_never": 2}))


def case_b():
    kinds = {}
    for name, mod in ENGINES.items():
        deck, cmd = build_pending(name)
        out = mod.simulate(deck, cmd, dict(DEFAULT_CFG, turns=3,
                                           watch=frozenset()), 1)
        kinds[name] = type(out).__name__
    check("B every engine's simulate() returns a Metrics",
          kinds, {k: "Metrics" for k in ENGINES})


def case_c(scripted_by_deck):
    """Re-render each committed table from its committed cache."""
    import json
    saved = AB.SCRIPTED_BY_DECK
    AB.SCRIPTED_BY_DECK = scripted_by_deck
    try:
        for name in ENGINES:
            run = AB.Run(name, N, HORIZONS)
            table = os.path.join("results", f"ablation_{name}.txt")
            if not (os.path.exists(run.cache) and os.path.exists(table)):
                check(f"C {name}: cache and table both on disk", False)
                continue
            deck, cmd = build_pending(name)
            partly = AB.partly_for(name, deck)
            nonlands = [c.name for c in deck if not c.is_land]
            results = json.load(open(run.cache))
            if any(n not in results for n in nonlands):
                check(f"C {name}: the cache covers the deck", False)
                continue
            rendered = AB.render_table(run, results, nonlands, partly)
            with open(table, "r", encoding="utf-8", newline="") as fh:
                on_disk = fh.read()
            check(f"C {name}: the committed table re-renders byte-identical "
                  f"from its cache", rendered == on_disk)
    finally:
        AB.SCRIPTED_BY_DECK = saved


def run_cases(metrics_cls, scripted_by_deck):
    global FAILED
    FAILED = []
    case_a(metrics_cls)
    if not MUTATE:
        case_b()
    case_c(scripted_by_deck)
    return {n.split(" ")[0] + ("" if not n.startswith("C") else " " + n.split(" ")[1])
            for n in FAILED}


def main() -> int:
    if not MUTATE:
        print("§0z31 -- Metrics reads 0; tables re-render from their caches\n")
        run_cases(ENG.Metrics, AB.SCRIPTED_BY_DECK)
        print(f"\n{passed} passed, {failed} failed")
        return 1 if failed else 0

    print("MUTATION RUN -- exact sets\n")
    # One rendmaw card moved out of SCRIPTED: it prints under MODEL-BLIND
    # instead of MODEL-EVALUATED, and only rendmaw's table changes.
    victim = sorted(AB.SCRIPTED_RENDMAW)[0]
    moved = dict(AB.SCRIPTED_BY_DECK)
    moved["rendmaw"] = AB.SCRIPTED_RENDMAW - {victim}
    mutations = {
        "a plain dict in place of Metrics": (dict, AB.SCRIPTED_BY_DECK),
        f"one card moved to KNOWN_BLIND (rendmaw: {victim})":
            (ENG.Metrics, moved),
    }
    expected = {
        "a plain dict in place of Metrics": {"A"},
        f"one card moved to KNOWN_BLIND (rendmaw: {victim})": {"C rendmaw:"},
    }
    bad = 0
    for label, (cls, sets) in mutations.items():
        print(f"-- {label}")
        broke = run_cases(cls, sets)
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed  "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
