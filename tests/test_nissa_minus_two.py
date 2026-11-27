#!/usr/bin/env python3
"""§0z276: Nissa, Sage Animist's -2 when she is doomed (azusa, the oracle
audit's Tier 4 item 18; the owner, 2026-11-27, rule (a): "use the -2 when
the pod's next round is predicted to kill Nissa anyway").

    python -m tests.test_nissa_minus_two
    python -m tests.test_nissa_minus_two --mutate   # 5 mutations, exact

    "+1: Reveal the top card of your library. If it's a land card, put it
    onto the battlefield. Otherwise, put it into your hand. -2: Create
    Ashaya, the Awoken World, a legendary 4/4 green Elemental creature
    token. -7: Untap up to six target lands. They become 6/6 Elemental
    creatures. They're still lands."           (Scryfall 2026-09-07)

`AzusaGame.nissa_doomed`: the pod's combat power (every living opponent's
combat bodies) reaches her loyalty after a +1.

CASES (azusa; Nissa, Sage Animist on the battlefield; opponent 0's one
combat body, the others none; `pod_attack_rate` 1, so the forecast is a
third of its power -- your share of that opponent's attention)
  A  loyalty 3, a 12-power body (4 expected through): the -2 -- loyalty 1,
     a 4/4 Ashaya token
  B  loyalty 3, a 6-power body (2): the +1 -- loyalty 4
  C  loyalty 7, a 12-power body: the -7 still comes first
  D  NEIGHBOUR: nissa_minus_two=False -- A's setup, the +1, the reach
     counted
  E  loyalty 2, a 12-power body: the -2 takes her to 0 -- she goes to the
     graveyard, Ashaya stays
  F  A5 off (pod_attacks_walkers=False): A's setup, the +1
  G  loyalty 3, an 11-power body (3.67, under 3 + 1): the +1
  H  loyalty 3, a 21-power body and your untapped 5/7: your board moves
     your share to 0.2, so unblocked it is 4.2 expected -- doomed -- and
     the 5/7 blocks it for her: the +1
  I  §0z276's first predictor (nissa_doom_rule="power"): B's setup -- 6
     power against 4 -- is doomed

MUTATIONS, WRITTEN BEFORE THE RUN (§0z278), exact sets:
  she is never doomed                          -> A, D, E, I
  the prediction leaves out her +1             -> G
  a walker at 0 loyalty stays                  -> E
  A5's switch ignored                          -> F
  your blocks ignored by the forecast          -> H

UNMUTATED (§0z15): B and C hold under all; D is the switch's neighbour.

THE FIRST RUN (§0z11): the blocks mutation broke nothing -- H's 5/7 also
moved your share of the opponent's attention (0.333 -> 0.2), which alone
put a 12-power body under 4; H's body is 21 power now. The sets as written.
(§0z276's own first run: one set fixed before it.) §0z276's sets were
rewritten for §0z278's predictor: its powers were the
first predictor's (the pod's summed power); these read the expectation.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")
ASHAYA = "Ashaya, the Awoken World token"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(loyalty, power, blocker=None, **cfg):
    # nissa_minus_two=True (on by default since §0z278; said for the record
    # of §0z276, when it was off); pod_attack_rate=1 makes the forecast a
    # third of the body's power.
    cfg = {"nissa_minus_two": True, "pod_attack_rate": 1.0, **cfg}
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.turn = 6
    nissa = EN.Permanent(card=AZ.NISSA_SAGE_ANIMIST, sick=False,
                         counters=loyalty)
    g.board.append(nissa)
    for i, o in enumerate(g.opponents):
        o.body_pool = ((OPP.PodBody(4, 2, False, power, False, False,
                                    False),) if i == 0 else ())
        o.bodies, o.body_tapped, o.next_body = [], [], 0
        o.creatures = 1.0 if i == 0 else 0.0
    if blocker is not None:
        p, t = blocker
        g.board.append(EN.Permanent(card=EN.Card(
            name="Wall", types=frozenset({"Creature"}), cost={"gen": 2},
            power=p, toughness=t), sick=False))
    return g, nissa


def ashaya(g):
    return [(g.power_of(p), g.toughness_of(p)) for p in g.board
            if p.card.name == ASHAYA]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, n = game(3, 12)
    g._nissa_sage_animist(n)
    check("A doomed: the -2, loyalty 1, a 4/4", (n.counters, ashaya(g)),
          (1, [(4, 4)]))

    g, n = game(3, 6)
    g._nissa_sage_animist(n)
    check("B not doomed: the +1", (n.counters, ashaya(g)), (4, []))

    g, n = game(7, 12)
    g._nissa_sage_animist(n)
    check("C loyalty 7: the -7 first", (n.counters, ashaya(g)), (0, []))

    g, n = game(3, 12, nissa_minus_two=False)
    g._nissa_sage_animist(n)
    check("D nissa_minus_two=False: the +1, the reach counted",
          (n.counters, g.m["nissa_doomed_seen"]), (4, 1))

    g, n = game(2, 12)
    g._nissa_sage_animist(n)
    check("E loyalty 2: she dies, Ashaya stays",
          (any(p is n for p in g.board), ashaya(g),
           AZ.NISSA_SAGE_ANIMIST in g.graveyard), (False, [(4, 4)], True))

    g, n = game(3, 12, pod_attacks_walkers=False)
    g._nissa_sage_animist(n)
    check("F A5 off: the +1", n.counters, 4)

    g, n = game(3, 11)
    g._nissa_sage_animist(n)
    check("G 3.67 expected against 3 + 1: the +1", n.counters, 4)

    g, n = game(3, 21, blocker=(5, 7))
    g._nissa_sage_animist(n)
    check("H your blocker stops it: the +1", n.counters, 4)

    g, n = game(3, 6, nissa_doom_rule="power")
    g._nissa_sage_animist(n)
    check("I the first predictor: 6 power against 4, doomed", n.counters, 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z276: Nissa, Sage Animist's -2 when she is doomed\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_doomed = AzusaGame.nissa_doomed
    real_die = EN.walker_dies_at_zero
    real_knob = OPP.pod_knob

    def no_plus(self, perm):
        perm.counters -= 1
        try:
            return real_doomed(self, perm)
        finally:
            perm.counters += 1

    def knob_on(cfg, name):
        return True if name == "pod_attacks_walkers" else real_knob(cfg, name)

    def set_doomed(v):
        AzusaGame.nissa_doomed = v

    def set_die(v):
        EN.walker_dies_at_zero = v

    def set_knob(v):
        OPP.pod_knob = v

    real_blocks = OPP.plan_blocks

    def set_blocks(v):
        OPP.plan_blocks = v

    muts = {
        "she is never doomed": ({"A", "D", "E", "I"}, set_doomed,
                                lambda self, perm: False, real_doomed),
        "the prediction leaves out her +1": ({"G"}, set_doomed, no_plus,
                                             real_doomed),
        "a walker at 0 loyalty stays": ({"E"}, set_die,
                                        lambda g, perm: None, real_die),
        "A5's switch ignored": ({"F"}, set_knob, knob_on, real_knob),
        "your blocks ignored by the forecast": (
            {"H"}, set_blocks, lambda *a, **k: {}, real_blocks),
    }
    bad = 0
    for label, (want, setter, value, restore) in muts.items():
        print(f"-- {label}")
        setter(value)
        try:
            broke = run_cases()
        finally:
            setter(restore)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
