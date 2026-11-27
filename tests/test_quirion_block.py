#!/usr/bin/env python3
"""§0z275: Quirion Ranger untaps a blocker on the pod's turn (azusa, the
oracle audit's Tier 4 item 19; the owner, 2026-11-27: "go ahead with this
fix").

    python -m tests.test_quirion_block
    python -m tests.test_quirion_block --mutate   # 4 mutations, exact sets

    "Return a Forest you control to its owner's hand: Untap target
    creature. Activate only once each turn."   (Scryfall 2026-10-13)

`AzusaGame.quirion_block_untap`, at each opponent's upkeep
(`pod_upkeep`): your toughest tapped creature, for a Forest already tapped.

CASES (azusa; the Ranger out; opponent 0 has a 3/3 combat body)
  A  a tapped 2/4 and a tapped Forest: the 2/4 untaps, the Forest goes to
     your hand
  B  only an untapped Forest: nothing
  C  once each turn: a second time on seat 0's turn nothing; on seat 1's
     turn again
  D  NEIGHBOUR: quirion_block=False -- the reach counted, nothing
  E  opponent 0 has only a utility body: nothing
  F  of a tapped 1/1 and a tapped 3/5, the 3/5
  G  your own turn after a pod-turn use: the Ranger is ready again (a
     different turn)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  "once each turn" keyed on your turn number only   -> C, G
  an untapped Forest may be returned                -> B
  the weakest tapped creature is untapped           -> F
  the combat-body check ignored                     -> E

UNMUTATED (§0z15): D is the switch's neighbour; A holds under all.

THE FIRST RUN (§0z11) raised in the setup: the hand was emptied before
the takes, and the Ranger was in the opening hand. Fixed; the sets as
written.
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


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def body(name, p, t):
    return EN.Card(name=name, types=frozenset({"Creature"}), cost={"gen": 2},
                   power=p, toughness=t)


def game(creatures=((2, 4),), forests=(True,), utility=False, **cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.turn = 6
    g.board.append(EN.Permanent(card=take(g, "Quirion Ranger"), sick=False))
    for tapped in forests:
        g.board.append(EN.Permanent(card=take(g, "Forest"), sick=False,
                                    tapped=tapped))
    mine = []
    for k, (p, t) in enumerate(creatures):
        perm = EN.Permanent(card=body(f"C{k} {p}/{t}", p, t), sick=False,
                            tapped=True)
        g.board.append(perm)
        mine.append(perm)
    for i, o in enumerate(g.opponents):
        o.body_pool = (OPP.PodBody(3, 2, False, 0 if utility else 3,
                                   utility, False, False),)
        o.bodies, o.body_tapped, o.next_body = [], [], 0
        o.creatures = 1.0
    g.hand = []                  # after the takes: the opening hand had some
    g.pod_seat = 0
    return g, mine


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, mine = game()
    g.quirion_block_untap(0)
    check("A the 2/4 untaps, the tapped Forest to hand",
          (mine[0].tapped, [c.name for c in g.hand]), (False, ["Forest"]))

    g, mine = game(forests=(False,))
    check("B only an untapped Forest: nothing", g.quirion_block_untap(0),
          False)

    g, mine = game(creatures=((2, 4), (2, 3)), forests=(True, True))
    first = g.quirion_block_untap(0)
    again = g.quirion_block_untap(0)
    g.pod_seat = 1
    seat1 = g.quirion_block_untap(1)
    check("C once on seat 0's turn, again on seat 1's",
          (first, again, seat1), (True, False, True))

    g, mine = game(quirion_block=False)
    check("D quirion_block=False: the reach counted, nothing",
          (g.quirion_block_untap(0), g.m["quirion_block_seen"],
           mine[0].tapped), (False, 1, True))

    g, mine = game(utility=True)
    check("E a utility body only: nothing", g.quirion_block_untap(0), False)

    g, mine = game(creatures=((1, 1), (3, 5)))
    g.quirion_block_untap(0)
    check("F the 3/5 untaps, not the 1/1",
          [p.tapped for p in mine], [True, False])

    g, mine = game(forests=(True, False))
    g.quirion_block_untap(0)
    g.pod_seat = None
    check("G your own turn: the Ranger is ready again",
          g.quirion_turn == g.quirion_key(), False)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z275: Quirion Ranger untaps a blocker\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_key = AzusaGame.quirion_key
    real_untap = AzusaGame.quirion_block_untap
    real_bodies = OPP.combat_bodies

    def untapped_ok(self, i):
        for p in self.board:
            if p.card.name == "Forest":
                p.tapped = True
        return real_untap(self, i)

    def weakest(self, i):
        real_t = AzusaGame.toughness_of
        AzusaGame.toughness_of = lambda s, p: -real_t(s, p)
        try:
            return real_untap(self, i)
        finally:
            AzusaGame.toughness_of = real_t

    def set_key(v):
        AzusaGame.quirion_key = v

    def set_untap(v):
        AzusaGame.quirion_block_untap = v

    def set_bodies(v):
        OPP.combat_bodies = v

    muts = {
        "'once each turn' on your turn number only": (
            {"C", "G"}, set_key, lambda self: self.turn, real_key),
        "an untapped Forest may be returned": ({"B"}, set_untap, untapped_ok,
                                               real_untap),
        "the weakest tapped creature is untapped": ({"F"}, set_untap,
                                                    weakest, real_untap),
        "the combat-body check ignored": ({"E"}, set_bodies,
                                          lambda bodies: [0], real_bodies),
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
