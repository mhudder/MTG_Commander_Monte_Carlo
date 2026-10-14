#!/usr/bin/env python3
"""What a re-armed clock's route is (§0z136, §0z137; `rearm_rule`, "keep").

    python -m tests.test_rearm_rule
    python -m tests.test_rearm_rule --mutate   # 5 mutations, exact sets

When an opponent's clock eliminates another opponent, `resolve_clocks`
re-arms it `clock_rearm` rounds on. Under `pod_threats` the rule for its
route is a knob: "keep" leaves its pieces out where they were (the original
reading), "reland" rebuilds it on a pre-rolled route of the same kind whose
pieces land `lead` before the new kill, and "prefer_unfired" keeps the
pieces and aims your answers at an unfired clock first.

CASES
  A  the re-arm routes: `REARM_ROUTES` per opponent, the kind's leads, a
     combat route's first piece a creature; the rule never enters
     `make_pod`; OFF rolls none
  B  "keep": the re-arm counts, and the pieces and landings stay
  C  "reland": the pieces become the next pre-rolled route, each landing
     `lead` before the new kill, none of them out yet; the second re-arm
     takes the second route
  D  what the first answer after the re-arm buys: on a kept route it is
     taken at once and fits inside the re-arm (0 rounds); on a relanded one
     it waits for a piece to land and moves the kill as a fresh route's
     removal does
  E  "prefer_unfired": your answer goes to the unfired clock with fewer
     pieces out (keep: the re-armed one with more), and to the re-armed one
     when only it has a piece the answer can hit
  F  the end of the pod's round aims the same way (Path to Exile)
  G  an unknown rule raises
  H  end to end: `resolve_clocks` eliminates another opponent and the
     clock's route is relanded under "reland", kept under "keep"

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the re-arm only counts (never relands)              -> C, D, H *
  every clock reads unfired                           -> E, F
  reland swaps the pieces, keeps the old landings     -> C, D, H *
  any rule is accepted                                -> G
  resolve_clocks rebuilds nothing, counts nothing     -> B, C, D, H *

  * A TRANSCRIPT, NOT A PREDICTION (§0z14). Rows 1 and 5 are as written
    before the first run; they broke C, H and B, C, H, because the first D
    was wrong: it moved the reland leg to turn 9 by hand, where a KEPT
    route's answer buys 2 as well. D now answers at the first turn a piece
    is out under each rule, which is the comparison the rule is about. Row 3
    was written C, H; the rewritten D reaches it too, correctly -- new
    pieces on the old landings are out at once, and an answer to them fits
    inside the re-arm as a kept route's does.

UNMUTATED (§0z15): A is a property of `roll_threat_routes`, read by the plain
run, and is not mutated.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as T
from edhmc.decks import karlov_v2 as KM
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


def route(o, pieces, lands, kill, pool=(2,), rearms=0, rearm_routes=()):
    o.route = "combat"
    o.pieces = tuple(pieces)
    o.piece_lands = list(lands)
    o.kill_turn = kill
    o.rebuild_pool, o.next_rebuild = tuple(pool), 0
    o.clock_fired = False
    o.rearms, o.rearm_routes = rearms, tuple(rearm_routes)


def tgame(**cfg):
    deck, cmd = TM.build()
    g = T.TivitGame(list(deck), cmd,
                    dict(DEFAULT_CFG, **dict(dict(pod_threats=True), **cfg)),
                    1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 6
    g.your_life = 40.0
    for o in g.opponents:
        o.life, o.creatures, o.alive, o.counters_left = 40.0, 3.0, True, 0
        route(o, (), (), 99)
    return g


NEW = ((P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)),
       (P("Enchantment", 2, 4, 3),))


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    cfg = dict(DEFAULT_CFG, pod_threats=True)

    ok_a = True
    for seed in range(40):
        for o in OPP.make_pod(cfg, seed)[0]:
            slots, (lo, hi) = OPP.ROUTE_PIECES[o.route]
            ok_a &= len(o.rearm_routes) == OPP.REARM_ROUTES
            for rt in o.rearm_routes:
                ok_a &= len(rt) == len(slots)
                ok_a &= all(lo <= p.lead <= hi for p in rt)
                ok_a &= o.route != "combat" or rt[0].type == "Creature"
    pods = [[(o.kill_turn, o.pieces, o.piece_lands, o.rearm_routes)
             for o in OPP.make_pod(dict(cfg, rearm_rule=rule), 9)[0]]
            for rule in OPP.REARM_RULES]
    off = OPP.make_pod(dict(DEFAULT_CFG), 9)[0]
    check("A re-arm routes: count, leads, kinds; the rule never rolls",
          (ok_a, pods[0] == pods[1] == pods[2],
           all(o.rearm_routes == () for o in off)),
          (True, True, True))

    g = tgame()
    o = g.opponents[0]
    route(o, (P("Creature", 3, 3, 2),), (3,), 10, rearm_routes=NEW)
    OPP.rearm_route(g, o)
    check("B keep: counted; pieces and landings stay",
          (o.rearms, o.pieces, o.piece_lands, OPP.present_pieces(g, o)),
          (1, (P("Creature", 3, 3, 2),), [3], [0]))

    g = tgame(rearm_rule="reland")
    o = g.opponents[0]
    route(o, (P("Creature", 3, 3, 2),), (3,), 10, rearm_routes=NEW)
    OPP.rearm_route(g, o)
    first = (o.pieces, o.piece_lands, OPP.present_pieces(g, o))
    o.kill_turn = 14
    OPP.rearm_route(g, o)
    check("C reland: the next route, landing lead before the kill, not out",
          (first, o.pieces, o.piece_lands, o.rearms),
          ((NEW[0], [8, 9], []), NEW[1], [11], 2))

    moved = []
    for rule in ("keep", "reland"):
        g = tgame(rearm_rule=rule)
        o = g.opponents[0]
        # Its pieces out since turns 3 and 4; it has just won, and re-arms
        # for turn 6 + 4 = 10.
        route(o, (P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)), (3, 4),
              10, rearm_routes=NEW)
        OPP.rearm_route(g, o)
        while not OPP.present_pieces(g, o):  # the first answer it can take:
            g.turn += 1                      # kept, now; relanded, from 9
        k = OPP.present_pieces(g, o)[0]
        moved.append(OPP.remove_threat_piece(g, o, k))
    # keep: on turn 6, back on 6+2-1=7, ready 9 < 10.  reland: on turn 9,
    # back on 9+2-1=10, ready 12, two rounds past 10 -- what a fresh route's
    # removal buys.
    check("D the first answer after the re-arm: kept buys 0, relanded 2",
          moved, [0, 2])

    swords = find(KM, "Swords to Plowshares")
    reach = OPP.ANSWERS[swords.name]
    aim = []
    for rule, unfired_piece in (("keep", "Creature"),
                                ("prefer_unfired", "Creature"),
                                ("prefer_unfired", "Artifact")):
        g = tgame(rearm_rule=rule)
        fired, fresh = g.opponents[0], g.opponents[1]
        route(fired, (P("Creature", 3, 3, 2), P("Creature", 2, 2, 1)),
              (3, 4), 10, rearms=1)
        route(fresh, (P(unfired_piece, 3, 3, 2),), (4,), 11)
        pick = OPP.answer_target(g, reach)
        aim.append(g.opponents.index(pick[0]))
    check("E prefer_unfired: aims at the unfired clock it can hit",
          aim, [0, 1, 0])

    path = find(KM, "Path to Exile")
    hit = []
    for rule in ("keep", "prefer_unfired"):
        g = tgame(rearm_rule=rule, pod_responses=True)
        g.board.append(EN.Permanent(card=find(TM, "Plains"), sick=False))
        fired, fresh = g.opponents[0], g.opponents[1]
        route(fired, (P("Creature", 3, 3, 2), P("Creature", 2, 2, 1)),
              (3, 4), 10, rearms=1)
        route(fresh, (P("Creature", 3, 3, 2),), (4,), 11)
        g.hand = [path]
        OPP.end_step_answers(g)
        # Read which piece went back, not the kill: both clocks have room
        # for a rebuild here, which is the slack D is about.
        hit.append((fired.piece_lands != [3, 4], fresh.piece_lands != [4]))
    check("F the end of the round: kept aims at the fired, else the unfired",
          hit, [(True, False), (False, True)])

    try:
        OPP.rearm_rule(tgame(rearm_rule="relaand"))
        raised = False
    except ValueError:
        raised = True
    check("G an unknown rule raises", raised, True)

    out = []
    for rule in ("keep", "reland"):
        g = tgame(rearm_rule=rule)
        o = g.opponents[0]
        route(o, (P("Creature", 3, 3, 2),), (3,), 6, rearm_routes=NEW)
        for x in g.opponents[1:]:
            route(x, (), (), 99)
        g.opp_rolls[OPP.pod_turn(g)][0][6] = 0.9999   # it picks a rival
        OPP.resolve_clocks(g)
        out.append((g.result, sum(x.alive for x in g.opponents),
                    o.kill_turn, o.pieces, o.piece_lands))
    check("H end to end: the winner's route is kept, or relanded",
          out, [(None, 2, 10, (P("Creature", 3, 3, 2),), [3]),
                (None, 2, 10, NEW[0], [8, 9])])

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("What a re-armed clock's route is (§0z137)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_rule = OPP.rearm_rule

    def count_only(g, o):
        o.rearms += 1

    def stale_lands(g, o):
        o.rearms += 1
        if OPP.pod_threats_on(g) and real_rule(g) == "reland":
            o.pieces = o.rearm_routes[(o.rearms - 1) % len(o.rearm_routes)]

    muts = {
        "the re-arm only counts":
            ({"C", "D", "H"}, OPP, "rearm_route", count_only),
        "every clock reads unfired":
            ({"E", "F"}, OPP, "unfired_first", lambda g, o: True),
        "reland keeps the old landings":
            ({"C", "D", "H"}, OPP, "rearm_route", stale_lands),
        "any rule is accepted":
            ({"G"}, OPP, "rearm_rule",
             lambda g: g.cfg.get("rearm_rule", "keep")),
        "resolve_clocks rebuilds nothing":
            ({"B", "C", "D", "H"}, OPP, "rearm_route", lambda g, o: None),
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
