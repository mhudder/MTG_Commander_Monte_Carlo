#!/usr/bin/env python3
"""§0z241 (queue item 50, step 6): your removal that hands the pod mana;
§0z245: your permanents that hand each opponent who takes it a Treasure.

    python -m tests.test_pod_gifts
    python -m tests.test_pod_gifts --mutate   # 4 mutations, exact sets

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
  H  Tempting Contract in your upkeep, every living opponent taking it
     (`tempting_offer_rate` 1.0), opponent 1 dead: opponents 0 and 2 each a
     Treasure and a mana, 1 nothing; you two Treasures (§0z245)
  I  Master of Ceremonies, opponent 1 dead, the two living choices fixed
     at money (seat 0) and secrets (seat 2): seat 0 a Treasure, the others
     none; you one Treasure
  J  `pod_gifts_symmetric` off: H's upkeep, your Treasures, none of theirs

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Path's land read untapped (GIFT_LAND_TAPPED_READ False)  -> A
  an unspent Treasure is lost (TREASURE_KEPT False)        -> D
  no gift is ever given (GIFTS_GIVEN False)               -> A, B, C, G, H, I
  Tempting Contract's takers read as nobody                -> H, J
  (the takers are both counts: your Treasures fall to 0 with theirs)

THE LAST MUTATION WAS CORRECTED AFTER ITS FIRST RUN, said so: it replaced
`pod_gift` with a no-op, which also removed the "due" count E reads, so E
broke too -- a different rule from "no gift is given". It is the seam
`GIFTS_GIVEN` False now, after the count; the expected set is unchanged.

SO WAS THE TAKERS MUTATION (§0z245), said so: written as H alone, it broke
H and J -- J reads your own Treasures, which are the takers' count too, as
the note under it already said of H. The rule was right and the expected
set was not; it is H, J now.

UNMUTATED (§0z15): E, F and J give nothing under every rule here; I's
choices are fixed by the case, so no mutation reaches them.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
import edhmc.tivit as TI
import edhmc.voting as V
from edhmc.decks import tivit_v1 as TV
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(on=True, seat=0, **cfg):
    deck, cmd = TV.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": True, "pod_gifts": on, **cfg},
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

    def upkeep_with(name, **cfg):
        deck, cmd = TV.build()
        g = TI.TivitGame(list(deck), cmd,
                         {**DEFAULT_CFG, "pod_mana": True, "pod_gifts": True,
                          "tempting_offer_rate": 1.0, **cfg}, 1)
        g.board = EN.Board()
        g.hand, g.graveyard = [], []
        g.turn = 6
        g.pod_seat = None
        for o in g.opponents:
            o.mana_left, o.gift_lands, o.treasures = 2.0, 0.0, 0.0
        g.opponents[1].alive = False
        card = next(c for c in TV.build()[0] if c.name == name)
        g.board.append(EN.Permanent(card, sick=False))
        before = g.tokens["Treasure"]
        TI.upkeep(g)
        return g, g.tokens["Treasure"] - before

    g, mine = upkeep_with("Tempting Contract")
    check("H Tempting Contract: each living taker a Treasure, you two",
          [(x.treasures, x.mana_left) for x in g.opponents] + [mine],
          [(1.0, 3.0), (0.0, 2.0), (1.0, 3.0), 2])

    picks = {"ceremonies0": 0, "ceremonies1": 2}   # the LIVING: seats 0, 2
    saved = TI.crn_randrange
    TI.crn_randrange = lambda g, name, n: picks[name]
    try:
        g, mine = upkeep_with("Master of Ceremonies")
    finally:
        TI.crn_randrange = saved
    check("I Master of Ceremonies: the money chooser a Treasure, you one",
          [x.treasures for x in g.opponents] + [mine], [1.0, 0.0, 0.0, 1])

    g, mine = upkeep_with("Tempting Contract", pod_gifts_symmetric=False)
    check("J symmetric gifts off: your Treasures, none of theirs",
          [x.treasures for x in g.opponents] + [mine], [0.0, 0.0, 0.0, 2])
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
            {"A", "B", "C", "G", "H", "I"}, [("GIFTS_GIVEN", False)]),
        "Tempting Contract's takers read as nobody": (
            {"H", "J"}, [("V.tempting_takers", lambda g: [])]),
    }
    mods = {"V": V}
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")

        def where(name):
            mod, _, attr = name.rpartition(".")
            return (mods[mod] if mod else O), attr
        saved = [(name, getattr(*where(name))) for name, _ in patches]
        for name, val in patches:
            setattr(*where(name), val)
        try:
            broke = run_cases()
        finally:
            for name, val in saved:
                setattr(*where(name), val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
