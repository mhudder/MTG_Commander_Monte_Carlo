#!/usr/bin/env python3
"""§0z225 (queue item 49): rendmaw's goaded Birds attack a rival as a
combat of bodies (`goad_body_blocks`), the rule every rival-on-rival attack
has followed since A4 (§0z200), not `goad_block_share`'s count.

    python -m tests.test_goad_bodies
    python -m tests.test_goad_bodies --mutate   # 2 mutations, exact sets

Each case: a rendmaw game; opponent 0 holds three goaded Birds (2/2
fliers); opponent 1, at 40 life, is the lowest and so the victim; opponent
2 at 50. Opponent 1's bodies are set by hand.

CASES
  A  no blockers: three Birds connect, 6 life
  B  two 4/4 bodies WITHOUT reach: neither can block a flier (702.9b) -- 6
     life (the count share blocked 0.6 of a Bird here: 4.8)
  C  one 3/3 body WITH reach: it blocks a Bird and kills it -- 4 life, and
     opponent 0 has two Birds left
  D  NEIGHBOUR: `goad_body_blocks` False, B's board: the count share, 4.8

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  goad_body_blocks=False                   -> B, C
  any body can block a flier               -> B

UNMUTATED (§0z15): A reads the same under both rules (nothing blocks); D
is the old rule.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(bodies=(), **cfg):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd, dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}),
                random.Random(1), seed_for_pod=1)
    a, v, other = g.opponents
    for o, life in ((a, 40.0), (v, 40.0), (other, 50.0)):
        o.life, o.alive, o.goaded_birds = life, True, 0.0
        o.bodies, o.body_tapped, o.next_body = [], [], 0
        o.creatures, o.body_pool = 0.0, ()
    a.goaded_birds = 3.0
    v.body_pool = tuple(bodies)
    v.creatures = float(len(bodies))
    return g, a, v


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, a, v = game()
    OPP.goaded_combat(g, seat=0)
    check("A no blockers: 6 life", v.life, 34.0)

    no_reach = [OPP.PodBody(4, 3, False, 4, False, False)] * 2
    g, a, v = game(no_reach)
    OPP.goaded_combat(g, seat=0)
    check("B two 4/4s without reach cannot block a flier: 6 life",
          round(v.life, 4), 34.0)

    g, a, v = game([OPP.PodBody(3, 3, False, 3, False, True)])
    OPP.goaded_combat(g, seat=0)
    check("C a 3/3 with reach blocks and kills a Bird: 4 life, 2 Birds left",
          (v.life, a.goaded_birds), (36.0, 2.0))

    g, a, v = game(no_reach, goad_body_blocks=False)
    OPP.goaded_combat(g, seat=0)
    check("D NEIGHBOUR: the count share: 4.8 life", round(v.life, 4), 35.2)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z225: goaded Birds attack as bodies\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.available_blockers

    def reach_for_all(g, defender):
        out, cap = real(g, defender)
        return [b._replace(reach=True) for b in out], cap

    muts = {
        "goad_body_blocks=False": ({"B", "C"}, {"goad_body_blocks": False},
                                   []),
        "any body can block a flier": ({"B"}, {}, [
            (OPP, "available_blockers", reach_for_all)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
