#!/usr/bin/env python3
"""Holding mana up through the pod's turn (item 24, change 3, §0z134;
`pod_responses`, OFF by default).

    python -m tests.test_pod_responses
    python -m tests.test_pod_responses --mutate   # 9 mutations, exact sets

Texts as the census and `PROTECTION` quote them: Counterspell ("counter
target spell"), Dovin's Veto ("counter target noncreature spell"), Muddle
the Mixture ("counter target instant or sorcery spell"), Heroic
Intervention ("hexproof and indestructible"), Swords to Plowshares ("exile
target creature"), Path to Exile ("exile target creature").

CASES
  A  pure responses: Counterspell and Heroic Intervention are; Boros Charm
     (4 damage) and Swords to Plowshares are not
  B  the main phase holds a pure response under `pod_responses`, not off it
  C  Heroic Intervention against a wrath is cast from UNTAPPED mana: with
     two Forests up it grants indestructible; with them tapped, nothing --
     no roll, no four-land rule
  D  Counterspell against the pod's spot removal: countered when the target
     is worth it (threat >= 4), held when it is not
  E  a countered wrath never resolves: your creature and the pod's survive
  F  a route piece being cast: Swords exiles a creature piece before the
     kill; Dovin's Veto counters an artifact piece and not a creature one;
     Muddle the Mixture counters neither
  G  the end of the pod's round: Path to Exile at a creature piece that is
     out, with the mana left
  H  `response_reserve="hold"`: with four Islands, a three-drop is held so
     Counterspell stays castable; with five it is not; "leftover" never holds
  I  OFF: `try_protect` is the old rule -- the roll and four lands, mana
     untouched
  J  a removal once the pod's round is open counts from the NEXT round: the
     same piece, removed with the same delay, comes back one round later
     than when it is removed in your turn (`next_pod_round`)
  K  a piece landing for an opponent who is NOT going off this round is left
     alone (Swords stays in hand); `response_pieces="all"` answers it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  nothing is a pure response                        -> A, B, H *
  held mana is free (response_pay always pays)      -> C
  counters ignore the target's worth                -> D
  a countered wrath resolves like phasing out       -> D, E *
  counters counter anything                         -> F
  the end of the round answers nothing              -> G
  the reserve never holds                           -> H
  (added with J, before its run)
  the pod's round is never open                     -> J
  (added with K, before its run)
  every landing piece is answered                   -> K
  * TWO SETS WERE WRITTEN TOO NARROW and are corrected after the first run,
    a transcript and not a prediction (§0z14). The first was A, B: the
    reserve keeps mana for a held PURE response, so with none it holds
    nothing and H breaks too. The second was E: the mutation rewrites every
    "countered" to "blank", so D's countered spot removal reads "blank" too.

UNMUTATED (§0z15): I is the OFF path, pinned by the plain run and by the
bit-identity check in §0z134.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as T
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v17 as LM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
P = OPP.ThreatPiece


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def find(module, name):
    deck, cmd = module.build()
    pool = list(deck) + [cmd] + [v for v in vars(module).values()
                                 if isinstance(v, EN.Card)]
    return next(c for c in pool if c.name == name)


def ready(g):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    for o in g.opponents:
        o.life, o.creatures, o.alive, o.counters_left = 40.0, 3.0, True, 0
        o.route, o.pieces, o.piece_lands = "combat", (), []
        o.rebuild_pool, o.next_rebuild, o.kill_turn = (2,), 0, 30
    return g


def rgame(**cfg):
    deck, cmd = RM.build()
    return ready(EN.Game(list(deck), cmd,
                         dict(DEFAULT_CFG, **dict(dict(pod_responses=True),
                                                  **cfg)),
                         random.Random(1), seed_for_pod=1))


def tgame(**cfg):
    deck, cmd = TM.build()
    return ready(T.TivitGame(list(deck), cmd,
                             dict(DEFAULT_CFG, **dict(dict(pod_responses=True),
                                                      **cfg)), 1))


def lands(g, module, name, n, tapped=False):
    for _ in range(n):
        g.board.append(EN.Permanent(card=find(module, name), sick=False,
                                    tapped=tapped))


def body(g, threat, power=3):
    c = EN.Card(name=f"Body{threat}", types=frozenset({"Creature"}),
                power=power, toughness=power, threat=threat)
    p = EN.Permanent(card=c, sick=False, base_p=power, base_t=power)
    g.board.append(p)
    return p


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g = rgame()
    counter = find(TM, "Counterspell")
    heroic = find(RM, "Heroic Intervention")
    check("A pure responses: Counterspell, Heroic; not Boros Charm, Swords",
          [OPP.pure_response(g, c) for c in
           (counter, heroic, find(LM, "Boros Charm"),
            find(KM, "Swords to Plowshares"))],
          [True, True, False, False])

    check("B the main phase holds a pure response only under pod_responses",
          (OPP.hold_answer(rgame(), heroic),
           OPP.hold_answer(rgame(pod_responses=False), heroic)),
          (True, False))

    out = []
    for tapped in (False, True):
        g = rgame()
        lands(g, RM, "Forest", 2, tapped=tapped)
        g.hand = [heroic]
        out.append((OPP.try_protect(g, 0.99, "wipe"), heroic in g.hand))
    check("C Heroic from untapped mana only: no roll, no four-land rule",
          out, [("indestructible", False), (None, True)])

    out = []
    for threat in (6.0, 2.0):
        g = tgame()
        lands(g, TM, "Island", 2)
        victim = body(g, threat)
        g.hand = [counter]
        out.append((OPP.try_protect(g, 0.0, "spot", victim),
                    counter in g.hand))
    check("D Counterspell on removal worth it; held when it is not",
          out, [("countered", False), (None, True)])

    g = tgame()
    lands(g, TM, "Island", 2)
    mine = body(g, 5.0)
    g.hand = [counter]
    g.opp_rolls = [[[0.0] * OPP.N_SLOTS for _ in g.opponents]
                   for _ in range(30)]
    OPP.board_wipe(g, g.opponents[0], g.opp_rolls[6][0])
    check("E a countered wrath never resolves: nobody's creatures die",
          (mine in g.board, [o.creatures for o in g.opponents],
           g.m["wipes_countered"]),
          (True, [3.0, 3.0, 3.0], 1))

    swords = find(KM, "Swords to Plowshares")
    veto = find(TM, "Dovin's Veto")
    muddle = find(TM, "Muddle the Mixture")
    out = []
    for card, land, piece in ((swords, "Plains", "Creature"),
                              (veto, "Hallowed Fountain", "Artifact"),
                              (veto, "Hallowed Fountain", "Creature"),
                              (muddle, "Island", "Artifact")):
        g = tgame(pod_threats=True)
        lands(g, TM, land, 2)
        o = g.opponents[1]
        o.pieces = (P(piece, 3, 3, 0),)
        o.piece_lands, o.kill_turn = [6], 6     # lands and wins THIS round
        g.hand = [card]
        OPP.respond_to_pieces(g)
        out.append(o.kill_turn > 6)
    check("F a piece being cast: Swords, Veto on noncreature, never Muddle",
          out, [True, True, False, False])

    path = find(KM, "Path to Exile")
    g = tgame(pod_threats=True)
    lands(g, TM, "Plains", 1)
    o = g.opponents[2]
    o.pieces, o.piece_lands, o.kill_turn = (P("Creature", 3, 3, 2),), [4], 7
    g.hand = [path]
    OPP.end_step_answers(g)
    check("G the end of the round: Path at a piece that is out",
          (path in g.hand, o.kill_turn > 7), (False, True))

    three = EN.Card(name="Three", types=frozenset({"Creature"}),
                    cost={"gen": 3}, power=3, toughness=3)
    out = []
    for n, policy in ((4, "hold"), (5, "hold"), (4, "leftover")):
        g = tgame(response_reserve=policy)
        lands(g, TM, "Island", n)
        g.hand = [counter, three]
        out.append(OPP.reserve_holds(g, three))
    check("H the reserve: hold at four Islands, not five; leftover never",
          out, [True, False, False])

    g = rgame(pod_responses=False)
    lands(g, RM, "Forest", 4, tapped=True)
    g.hand = [heroic]
    check("I OFF: the old roll and four lands, tapped or not",
          OPP.try_protect(g, 0.1, "wipe"), "indestructible")

    out = []
    for opened in (False, True):
        g = tgame(pod_threats=True)
        o = g.opponents[0]
        o.pieces, o.piece_lands, o.kill_turn = (P("Creature", 3, 3, 1),), [5], 7
        o.rebuild_pool = (2,)
        if opened:
            g.pod_round_of = g.turn
        OPP.remove_threat_piece(g, o, 0)
        out.append((o.piece_lands[0], o.kill_turn))
    check("J the pod's round open: the rebuild counts from the next round",
          out, [(7, 8), (8, 9)])

    out = []
    for policy in ("going_off", "all"):
        g = tgame(pod_threats=True, response_pieces=policy)
        lands(g, TM, "Plains", 1)
        o = g.opponents[1]
        o.pieces, o.piece_lands, o.kill_turn = (P("Creature", 3, 3, 3),), [6], 9
        g.hand = [swords]
        OPP.respond_to_pieces(g)
        out.append(swords in g.hand)
    check("K a piece from an opponent not going off: held; 'all' answers it",
          out, [True, False])

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Holding mana up through the pod's turn (item 24, change 3)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_cast = OPP._cast_response
    real_event = OPP.respond_to_event

    real_pieces = OPP.respond_to_pieces

    def greedy_pieces(g):
        cfg = g.cfg
        g.cfg = dict(cfg, response_pieces="all")
        try:
            return real_pieces(g)
        finally:
            g.cfg = cfg

    def free_cast(g, card, kind):
        g.hand.remove(card)
        g.graveyard.append(card)
        g.m["responses_cast"] += 1
        return True

    def worthless_target(g, event, victim, how):
        return real_event(g, event, None, how)

    def wipe_as_phasing(g, event, victim, how):
        r = real_event(g, event, victim, how)
        return "blank" if r == "countered" else r

    muts = {
        "nothing is a pure response":
            ({"A", "B", "H"}, OPP, "pure_response", lambda g, c: False),
        "held mana is free":
            ({"C"}, OPP, "_cast_response", free_cast),
        "counters ignore the target's worth":
            ({"D"}, OPP, "respond_to_event", worthless_target),
        "a countered wrath resolves like phasing out":
            ({"D", "E"}, OPP, "respond_to_event", wipe_as_phasing),
        "counters counter anything":
            ({"F"}, OPP, "counter_hits", lambda name, spell:
             name in OPP._removal.COUNTERS),
        "the end of the round answers nothing":
            ({"G"}, OPP, "end_step_answers", lambda g: 0),
        "the reserve never holds":
            ({"H"}, OPP, "reserve_holds", lambda g, c: False),
        "the pod's round is never open":
            ({"J"}, OPP, "next_pod_round", lambda g: OPP.pod_turn(g)),
        "every landing piece is answered":
            ({"K"}, OPP, "respond_to_pieces", greedy_pieces),
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
