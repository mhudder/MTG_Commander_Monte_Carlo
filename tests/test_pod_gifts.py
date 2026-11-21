#!/usr/bin/env python3
"""§0z241 (queue item 50, step 6): your removal that hands the pod mana.

    python -m tests.test_pod_gifts
    python -m tests.test_pod_gifts --mutate   # 3 mutations, exact sets

Path to Exile and Assassin's Trophy: "Its controller may search their
library for a basic land card, put [it] onto the battlefield [tapped]";
An Offer You Can't Refuse: "Its controller creates two Treasure tokens"
(`_pod_mana.POD_GIFTS`, generated). Each case: a tivit game with `pod_mana`
and `pod_gifts` on (unless it says off), opponent 0 given 2 mana, and
`pod_gift` (or an answer that calls it) applied.

CASES
  A  Path on opponent 0's OWN turn: a land for later (gift_lands 1), no
     mana now -- it enters tapped
  B  Trophy on its own turn: a land AND a mana now (untapped); on YOUR turn:
     the land only, mana from its next untap
  C  An Offer: two Treasures, two mana now
  D  its next untap: spare + its gift land + the Treasures it kept -- of 2
     Treasures, with 1 mana left unspent, it kept 1 (a Treasure goes last)
  E  `pod_gifts` off: counted due, nothing given
  F  a card with no gift (Swords to Plowshares): nothing, not even due
  G  through `answer_pod_threat`: Path cast at a route piece -- the piece's
     controller gets the land, and only that opponent

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Path's land read untapped (GIFT_LAND_TAPPED_READ False)  -> A
  an unspent Treasure is lost (TREASURE_KEPT False)        -> D
  no gift is ever given (GIFTS_GIVEN False)               -> A, B, C, G

THE LAST MUTATION WAS CORRECTED AFTER ITS FIRST RUN, said so: it replaced
`pod_gift` with a no-op, which also removed the "due" count E reads, so E
broke too -- a different rule from "no gift is given". It is the seam
`GIFTS_GIVEN` False now, after the count; the expected set is unchanged.

UNMUTATED (§0z15): E and F give nothing under every rule here.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import tivit_v1 as TV
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(on=True, seat=0):
    deck, cmd = TV.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": True, "pod_gifts": on},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 6
    g.pod_seat = seat
    for o in g.opponents:
        o.mana_left, o.gift_lands, o.treasures = 2.0, 0.0, 0.0
    return g, g.opponents[0]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game()
    O.pod_gift(g, o, "Path to Exile")
    check("A Path on its own turn: a land for later, no mana now",
          (o.gift_lands, o.mana_left), (1.0, 2.0))

    g, o = game()
    O.pod_gift(g, o, "Assassin's Trophy")
    own = (o.gift_lands, o.mana_left)
    g, o = game(seat=None)
    O.pod_gift(g, o, "Assassin's Trophy")
    check("B Trophy: a land and a mana on its turn, the land on yours",
          [own, (o.gift_lands, o.mana_left)], [(1.0, 3.0), (1.0, 2.0)])

    g, o = game(seat=None)
    O.pod_gift(g, o, "An Offer You Can't Refuse")
    check("C An Offer: two Treasures, two mana now",
          (o.treasures, o.mana_left), (2.0, 4.0))

    g, o = game()
    o.gift_lands, o.treasures, o.mana_left = 1.0, 2.0, 1.0
    O.pod_untap(g, 0)
    check("D its untap: spare + the land + the 1 Treasure kept",
          (o.treasures, o.mana_left),
          (1.0, O.pod_mana_row(g, o).spare + 1.0 + 1.0))

    g, o = game(on=False)
    O.pod_gift(g, o, "Path to Exile")
    check("E gifts off: due, nothing given",
          (g.m["pod_gifts_due"], o.gift_lands, o.mana_left), (1, 0.0, 2.0))

    g, o = game()
    O.pod_gift(g, o, "Swords to Plowshares")
    check("F no gift: nothing, not even due",
          (g.m["pod_gifts_due"], o.gift_lands), (0, 0.0))

    g, o = game(seat=None)
    for x in g.opponents:
        x.pieces = (O.ThreatPiece("Creature", 2, 2, 1),)
        x.piece_lands = [99]
    target = g.opponents[1]
    target.piece_lands = [1]
    path = next(c for c in TV.build()[0] if c.name == "Path to Exile")
    O.answer_pod_threat(g, path)
    check("G Path at a route piece: its controller's land, no one else's",
          [x.gift_lands for x in g.opponents], [0.0, 1.0, 0.0])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z241: your removal that hands the pod mana\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "Path's land read untapped": (
            {"A"}, [("GIFT_LAND_TAPPED_READ", False)]),
        "an unspent Treasure is lost": ({"D"}, [("TREASURE_KEPT", False)]),
        "no gift is ever given": (
            {"A", "B", "C", "G"}, [("GIFTS_GIVEN", False)]),
    }
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
