#!/usr/bin/env python3
"""One run, every horizon: a T10 game IS the first ten rounds of the T20 game
on the same seed (§0z93).

    python -m tests.test_horizon_prefix
    python -m tests.test_horizon_prefix --mutate   # 3 mutations, exact sets

`ablation.py` plays each game once, to the longest horizon, and reads the
shorter horizons off `engine.Snapshots`. That is a speed change ONLY if the
numbers are identical to running each horizon separately -- so this checks
identity, on every output key, not closeness.

CASES
  A-F  rendmaw, lorehold, karlov, tivit, shilgengar, azusa: over 60 seeds,
       the standalone T10 game's output equals the T20 game's round-10
       snapshot, key for key
  G    taking a snapshot does not perturb the game: a T20 game with
       `snapshot_rounds=(10,)` returns what one without it returns, all six
  H    ablation's `columns_all` equals `columns` run per horizon (rendmaw,
       the unmodified deck, 60 seeds)
  I    a round neither snapshotted nor reached by a game that ENDED raises
  J    the pod's grid has the same number of rows at T10 and T20

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the grid is sized by the horizon again (pod_grid_rounds=0)
                                                 -> A, B, C, D, E, F, H, J
  a snapshot keeps live references (no deep copy) -> A, B, C, D, E, F
  attach ignores the snapshots (final for all)    -> A, B, C, D, E, F, H, I

UNMUTATED (§0z15): G is the neighbour -- the snapshot must change nothing.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
SEEDS = range(5000, 5060)
ORDER = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
LISTS = {d: build_pending(d) for d in ORDER}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return {**DEFAULT_CFG, **EXTRA_CFG, **kw}


def run_cases():
    PASS.clear()
    FAIL.clear()
    perturbed = []
    for letter, deck in zip("ABCDEF", ORDER):
        cards, cmd = LISTS[deck]
        sim = DECKS[deck].sim
        bad = 0
        for s in SEEDS:
            t10 = dict(sim(list(cards), cmd, cfg(turns=10), s))
            t20 = sim(list(cards), cmd, cfg(turns=20, snapshot_rounds=(10,)), s)
            bad += t10 != t20["at_rounds"][10]
            if s < 5015:
                plain = dict(sim(list(cards), cmd, cfg(turns=20), s))
                if {k: v for k, v in t20.items() if k != "at_rounds"} != plain:
                    perturbed.append((deck, s))
        check(f"{letter} {deck}: T10 equals the T20 game at round 10", bad, 0)
    check("G a snapshot perturbs no game", perturbed, [])

    run = AB.Run("rendmaw", 60, (10, 20), False, True)
    cards, cmd = LISTS["rendmaw"]
    saved = dict(DEFAULT_CFG)
    DEFAULT_CFG.update(EXTRA_CFG)          # `columns` reads DEFAULT_CFG
    try:
        both = AB.columns_all(run, cards, cmd, 0, 60)
        each = {t: AB.columns(run, cards, cmd, t, 0, 60) for t in (10, 20)}
    finally:
        DEFAULT_CFG.clear()
        DEFAULT_CFG.update(saved)
    same = all((both[t][m] == each[t][m]).all() for t in (10, 20)
               for m in run.metrics)
    check("H columns_all equals columns per horizon", same, True)

    snaps = EN.Snapshots({"snapshot_rounds": (10,)})
    fake = type("G", (), {"result": None})()
    try:
        snaps.attach(fake, {})
        raised = False
    except ValueError:
        raised = True
    check("I a round never reached raises", raised, True)

    rows = [len(OPP.make_pod(cfg(turns=t), 5000)[1]) for t in (10, 20)]
    check("J the grid's size does not depend on the horizon",
          rows[0] == rows[1], True)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("One run, every horizon (§0z93)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    import copy as _copy

    def shallow(self, g, rounds, outputs):
        if rounds in self.want and g.result is None:
            self.taken[rounds] = dict(outputs(g))

    def final_only(self, g, out):
        if not self.want:
            return out
        out["at_rounds"] = {k: _copy.deepcopy(dict(out)) for k in self.want}
        return out

    six = {"A", "B", "C", "D", "E", "F"}
    muts = {
        "the grid is sized by the horizon again":
            (six | {"H", "J"}, None, {"pod_grid_rounds": 0}),
        "a snapshot keeps live references":
            (six, (EN.Snapshots, "after_round", shallow), {}),
        "attach ignores the snapshots":
            (six | {"H", "I"}, (EN.Snapshots, "attach", final_only), {}),
    }
    bad = 0
    for label, (want, patch, extra) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = extra
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
