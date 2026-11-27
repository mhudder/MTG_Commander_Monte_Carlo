#!/usr/bin/env python3
"""§0z268: Elesh Norn, Grand Cenobite's -2/-2 on the pod's survivors.

    python -m tests.test_norn_shrink
    python -m tests.test_norn_shrink --mutate   # 5 mutations, exact sets

    "Vigilance. Other creatures you control get +2/+2. Creatures your
    opponents control get -2/-2."   ({5}{W}{W}; Scryfall 2026-11-27)

The kill of toughness 2 or less was modelled (§0z151); the survivors kept
their power and toughness. Since §0z268 every pod body is read under the
game's static shift (`opponents.pod_pt_shift`, shilgengar's
`pod_static_pt`): applied in `pod_bodies`, where every body enters and is
read, and undone when Norn leaves.

CASES (shilgengar; opponent 0's bodies (power, toughness) as built)
  A  Norn enters over (3,1), (4,3), (6,5): the 1 dies; the rest read (2,1),
     (4,3)
  B  Norn leaves: over (4,5), (6,6), the survivors read (4,5), (6,6) again
  C  a body that enters while she is out is shifted: (5,4) reads (3,2)
  D  your upkeep's static kill: a (2,2) that entered under her dies, a
     (4,3) does not
  E  NEIGHBOUR: norn_shrink=False -- the 1 dies, the rest keep (4,3), (6,5)
  F  power floors at 0: a (1,5) reads (0,3)
  G  Massacre Wurm under Norn kills what reads 2 or less: bases 3 and 4 die,
     a base 5 lives, reading (1,3)
  H  a combat kill's force under Norn: base toughness 2 or less skipped,
     each power 2 less
  I  the tapped flags stay with their bodies through the shift and back
  J  outside shilgengar there is no shift (rendmaw)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the shift never read (pod_pt_shift always none)  -> A, C, D, F, G, H
  the originals forgotten (no restore)             -> B
  power not floored at 0                           -> F
  the static kill ignores the shift (limit 2)      -> A, D
  kill_force ignores the shift                     -> H

UNMUTATED (§0z15): E is the switch's neighbour; I and J hold under all.

BEFORE THE FIRST RUN (§0z11) the sets were re-read against the cases and
four slips fixed: B continued A's game (its own game now, toughness 5+ so
the fourth mutation's kill does not reach it); G's survivor is (1,3), not
(1,1); I read the sizes after the restore (now the flags only); and D
breaks under the first mutation (its survivor reads (2,1) only shifted).
"""
import sys

import edhmc.opponents as OPP
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
NORN = "Elesh Norn, Grand Cenobite"
WURM = "Massacre Wurm"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def body(p, t, utility=False):
    return OPP.PodBody(t, 2, False, p, utility, False, False)


def game(pts, deck="shilgengar", **cfg):
    g = B.fresh(deck, **{**EXTRA_CFG, **cfg})
    g.turn = 4
    for i, o in enumerate(g.opponents):
        o.body_pool = tuple(body(p, t) for p, t in pts) if i == 0 else ()
        o.bodies, o.body_tapped, o.next_body = [], [], 0
        o.creatures = float(len(pts)) if i == 0 else 0.0
        o.pt_shift, o.pt_base = OPP.NO_SHIFT, {}
    o = g.opponents[0]
    OPP.pod_bodies(g, o)
    return g, o


def pt(g, o):
    return [(b.power, b.toughness) for b in OPP.pod_bodies(g, o)]


def norn(g):
    g.make_permanent(B.card("shilgengar", NORN), sick=False)
    return next(p for p in g.board if p.card.name == NORN)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game([(3, 1), (4, 3), (6, 5)])
    norn(g)
    check("A Norn enters: the 1 dies, the rest shrink", pt(g, o),
          [(2, 1), (4, 3)])

    g, o = game([(4, 5), (6, 6)])
    perm = norn(g)
    OPP.pod_bodies(g, o)
    g.board.remove(perm)
    check("B Norn leaves: the survivors back", pt(g, o), [(4, 5), (6, 6)])

    g, o = game([(4, 3)])
    norn(g)
    o.body_pool = o.body_pool + (body(5, 4),)
    o.creatures += 1.0
    check("C an entering body is shifted", pt(g, o)[-1], (3, 2))

    g, o = game([(4, 3)])
    norn(g)
    o.body_pool = o.body_pool + (body(2, 2),)
    o.creatures += 1.0
    OPP.pod_bodies(g, o)
    g.m["norn_kills"] = 0
    g.upkeep() if hasattr(g, "upkeep") else None
    check("D the upkeep's static kill: the 2 dies, the 3 lives",
          pt(g, o), [(2, 1)])

    g, o = game([(3, 1), (4, 3), (6, 5)], norn_shrink=False)
    norn(g)
    check("E norn_shrink=False: survivors keep their size", pt(g, o),
          [(4, 3), (6, 5)])

    g, o = game([(1, 5)])
    norn(g)
    check("F power floors at 0", pt(g, o), [(0, 3)])

    g, o = game([(3, 3), (3, 4), (3, 5)])
    norn(g)
    OPP.minus_two_pod(g, B.card("shilgengar", WURM))
    check("G Massacre Wurm under Norn: bases 3 and 4 die", pt(g, o),
          [(1, 3)])

    g, o = game([])
    o.body_pool = (body(5, 2), body(4, 4), body(6, 6))
    norn(g)
    force = OPP.kill_force(g, o, 4)
    check("H the kill force under Norn",
          [(b.power, b.toughness) for b in force], [(2, 2), (4, 4)])

    g, o = game([(4, 5), (6, 6)])
    o.body_tapped = [True, False]
    perm = norn(g)
    OPP.pod_bodies(g, o)
    g.board.remove(perm)
    OPP.pod_bodies(g, o)
    check("I the tapped flags stay with their bodies",
          (list(o.body_tapped), len(o.bodies)), ([True, False], 2))

    g, o = game([(4, 3)], deck="rendmaw")
    check("J no shift outside shilgengar",
          (OPP.pod_pt_shift(g), pt(g, o)), (OPP.NO_SHIFT, [(4, 3)]))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z268: Elesh Norn's -2/-2 on the pod's survivors\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(OPP, n) for n in
            ("pod_pt_shift", "_reshift", "_shift_body", "minus_two_pod",
             "kill_force")}

    def no_restore(o, shift):
        if not hasattr(o, "pt_base"):
            o.pt_base = {}
        for i, b in enumerate(o.bodies):
            o.bodies[i] = (b if shift == OPP.NO_SHIFT
                           else OPP._shift_body(o, b, shift))
        o.pt_shift = shift

    def no_floor(o, base, shift):
        dp, dt = shift
        b = base._replace(power=base.power + dp, toughness=base.toughness + dt)
        o.pt_base[id(b)] = (b, base)
        return b

    def limit_two(g, card, static=False):
        return real["minus_two_pod"](g, card, static=False)

    def force_unshifted(g, opp, size):
        hook = g.pod_static_pt if hasattr(g, "pod_static_pt") else None
        try:
            if hook is not None:
                g.pod_static_pt = lambda: OPP.NO_SHIFT
            return real["kill_force"](g, opp, size)
        finally:
            if hook is not None:
                del g.pod_static_pt

    muts = {
        "the shift never read": (
            {"A", "C", "D", "F", "G", "H"}, "pod_pt_shift",
            lambda g: OPP.NO_SHIFT),
        "the originals forgotten": ({"B"}, "_reshift", no_restore),
        "power not floored at 0": ({"F"}, "_shift_body", no_floor),
        "the static kill ignores the shift": ({"A", "D"}, "minus_two_pod",
                                              limit_two),
        "kill_force ignores the shift": ({"H"}, "kill_force",
                                         force_unshifted),
    }
    bad = 0
    for label, (want, name, value) in muts.items():
        print(f"-- {label}")
        setattr(OPP, name, value)
        try:
            broke = run_cases()
        finally:
            setattr(OPP, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
