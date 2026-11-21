#!/usr/bin/env python3
"""§0z242 (queue item 50, decision 5): the pod's rates scaled under the
mana model, `opponents.pod_rate`.

    python -m tests.test_pod_rate
    python -m tests.test_pod_rate --mutate   # 1 mutation, exact set

Each case reads `pod_rate` for opponent 0 of a rendmaw game.

CASES
  A  `pod_rate_scale` {spot: 1.15} with `pod_mana` on: spot is its bracket
     rate times 1.15; a kind the scale does not name (wipe) is unchanged
  B  the same scale with `pod_mana` OFF: unchanged -- the scale is the mana
     model's, and the pod every table runs never reads it
  C  no scale (the default): unchanged

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the scale read without the mana model   -> B

UNMUTATED (§0z15): A and C hold under the one rule mutated.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**cfg):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd, {**DEFAULT_CFG, **cfg}, random.Random(1),
                seed_for_pod=1)
    return g, g.opponents[0]


def run_cases():
    PASS.clear()
    FAIL.clear()
    g, o = game(pod_mana=True, pod_rate_scale={"spot": 1.15})
    check("A scaled under the mana model; an unnamed kind unchanged",
          (O.pod_rate(g, o, "spot"), O.pod_rate(g, o, "wipe")),
          (o.p["spot"] * 1.15, o.p["wipe"]))
    g, o = game(pod_mana=False, pod_rate_scale={"spot": 1.15})
    check("B pod_mana off: unchanged", O.pod_rate(g, o, "spot"), o.p["spot"])
    # "no scale" named: the default is POD_RATE_SCALE since §0z243 (set
    # after the flip, no expectation changed)
    g, o = game(pod_mana=True, pod_rate_scale=None)
    check("C no scale: unchanged", O.pod_rate(g, o, "spot"), o.p["spot"])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z242: the pod's rates under the mana model\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    muts = {"the scale read without the mana model": (
        {"B"}, [("pod_mana_on", lambda g: True)])}
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        saved = [(name, getattr(O, name)) for name, _ in patches]
        for name, val in patches:
            setattr(O, name, val)
        try:
            broke = run_cases()
        finally:
            for name, val in saved:
                setattr(O, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
