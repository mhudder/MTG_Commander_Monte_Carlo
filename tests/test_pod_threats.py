#!/usr/bin/env python3
"""Opponent threats as objects that carry the clock (item 24, change 2;
`pod_threats`, OFF by default).

    python -m tests.test_pod_threats
    python -m tests.test_pod_threats --mutate   # 9 mutations, exact sets

Each opponent's `kill_turn` stays the roll it always was; under
`pod_threats` it is also a ROUTE of pre-rolled pieces (type, toughness,
mana value, lead), and removing a piece sends it back to be rebuilt, which
pushes the kill. Your spot answers' reach is DERIVED from the census clause
(`edhmc/decks/_removal.py`, generated from Scryfall). Texts as the census
quotes them: Swords to Plowshares ("exile target creature"), Beast Within
("destroy target permanent"), Despark ("target permanent with mana value 4
or greater"), Nameless Inversion ("target creature gets +3/-3"), Terastodon
("up to three target noncreature permanents"), Angel of the Ruins ("up to
two target artifacts and/or enchantments"), Massacre Wurm ("-2/-2"), Ondu
Inversion ("destroy all nonland permanents"), Coercive Portal ("destroy
all nonland permanents").

CASES
  A  OFF changes nothing in `make_pod`; ON adds routes and draws nothing
     from the pod's stream (same kill turns, same grid)
  B  routes: a combat route's first piece is a creature, leads lie in the
     kind's range, every piece lands `lead` before the kill, delays lie in
     1..`threat_rebuild_max`, and the roll repeats per seed
  C  a piece is out from the pod turn AFTER it lands; a dead opponent has
     none
  D  removing a piece: it comes back `d` rounds on (pre-rolled), the kill
     moves to its return plus its lead; a far-out clock does not move
  E  `answer_reach` reads the census clauses -- types, "up to", mana value
     and +X/-N conditions -- and raises on a clause naming no type
  F  the pilot aims at the opponent with the most pieces OUT, then the
     higher bracket; a creature answer passes over a route of artifacts
  G  a spell that resolves through `countered` answers (Beast Within); a
     countered one does not
  H  the hold: Swords waits while no creature piece is out and fires when
     one is; a creature that answers is never held; threat_hold=False and
     OFF never hold
  I  your sweepers: Damnation takes creature pieces only, Massacre Wurm
     toughness 2 or less, Ondu Inversion everything
  J  OFF: `countered` and `resolve_own_wipe` leave pieces and clocks alone
  K  tivit's Coercive Portal (carnage) takes noncreature pieces too
  L  rendmaw's main phase holds Beast Within with nothing out and casts it
     at a piece once one is out (the end-to-end hold and answer)
  M  the retune (§0z132): `threat_clock_shift` 2 brings every kill two
     rounds earlier and its pieces with it; 0.5 brings some one earlier and
     none more; routes and delays do not move

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  a removed piece does not push the kill            -> D, G, L *
  the pilot aims at the fewest pieces out           -> F
  answer_reach ignores conditions (mv, toughness)   -> E
  countered no longer answers                       -> G, L
  never hold                                        -> H, L
  every sweeper takes every piece                   -> I
  the Portal takes creature pieces only             -> K
  a piece is out on the turn it lands               -> C, L *
  the hold ignores what is out (always holds)       -> H, L
  (§0z132, written before its run)
  the clock shift is ignored                        -> M
  * TWO PREDICTIONS WERE WRONG, corrected after the first run and recorded
    here as a transcript, not a prediction (§0z14). The first was written
    as D, G, I, K, L: I and K read which pieces are OUT, not the clock, so a
    mutation that only freezes `kill_turn` cannot reach them -- the sweeper
    cases pin reach, D pins the push. The second was written as C alone: L's
    first step holds Beast Within BECAUSE a piece landing this pod turn is
    not out yet, so it reads the same rule C does.

UNMUTATED (§0z15): A and B are properties of `roll_threat_routes`, read by
the plain run; J is the OFF path.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as T
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import tivit_v1 as TM
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v17 as LM
from edhmc.experiment import DEFAULT_CFG, POD_PRE_V4

# Written on the pod before §0z140 and pinning that pod's mechanism: the
# old pod named, so POD_V4 becoming the default does not move it.
DEFAULT_CFG = dict(DEFAULT_CFG, **POD_PRE_V4)

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


def route(o, pieces, lands, kill, pool=(2,)):
    o.route = "combat"
    o.pieces = tuple(pieces)
    o.piece_lands = list(lands)
    o.kill_turn = kill
    o.rebuild_pool, o.next_rebuild = tuple(pool), 0
    o.clock_fired = False


def ready(g):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    for o in g.opponents:
        o.life, o.creatures, o.alive, o.counters_left = 40.0, 0.0, True, 0
        route(o, (), (), 99)
    return g


def rgame(**cfg):
    deck, cmd = RM.build()
    return ready(EN.Game(list(deck), cmd,
                         dict(DEFAULT_CFG, **dict(dict(pod_threats=True),
                                                  **cfg)),
                         random.Random(1), seed_for_pod=1))


def tgame(**cfg):
    deck, cmd = TM.build()
    return ready(T.TivitGame(list(deck), cmd,
                             dict(DEFAULT_CFG, **dict(dict(pod_threats=True),
                                                      **cfg)),
                             1))


def land(name):
    return EN.Permanent(card=find(RM, name), sick=False)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    cfg = dict(DEFAULT_CFG)

    off = OPP.make_pod(dict(cfg, pod_threats=False), 77)
    on = OPP.make_pod(dict(cfg, pod_threats=True), 77)
    same = (off[1] == on[1] and off[2] == on[2]
            and [(o.kill_turn, o.has_blue, o.archetype) for o in off[0]]
            == [(o.kill_turn, o.has_blue, o.archetype) for o in on[0]])
    check("A OFF changes nothing; ON adds routes and nothing else",
          (same, all(not o.pieces for o in off[0]),
           all(len(o.pieces) == 2 for o in on[0])),
          (True, True, True))

    ok_b = True
    for seed in range(40):
        for o in OPP.make_pod(dict(cfg, pod_threats=True), seed)[0]:
            slots, (lo, hi) = OPP.ROUTE_PIECES[o.route]
            ok_b &= all(lo <= p.lead <= hi for p in o.pieces)
            ok_b &= o.piece_lands == [o.kill_turn - p.lead for p in o.pieces]
            ok_b &= o.route != "combat" or o.pieces[0].type == "Creature"
            ok_b &= all(1 <= d <= 3 for d in o.rebuild_pool)
    a = [(o.route, o.pieces, o.rebuild_pool)
         for o in OPP.make_pod(dict(cfg, pod_threats=True), 5)[0]]
    b = [(o.route, o.pieces, o.rebuild_pool)
         for o in OPP.make_pod(dict(cfg, pod_threats=True), 5)[0]]
    wide = OPP.make_pod(dict(cfg, pod_threats=True, threat_rebuild_max=6),
                        5)[0]
    check("B routes: kinds, leads, landings, delays; per-seed repeat",
          (ok_b, a == b, max(d for o in wide for d in o.rebuild_pool) > 3),
          (True, True, True))

    g = rgame()
    o, dead = g.opponents[0], g.opponents[1]
    route(o, (P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)), (5, 6), 8)
    route(dead, (P("Creature", 3, 3, 2),), (2,), 8)
    dead.alive = False
    check("C out from the pod turn after landing; the dead have none",
          (OPP.present_pieces(g, o), OPP.present_pieces(g, dead)),
          ([0], []))

    g = rgame()
    o, far = g.opponents[0], g.opponents[1]
    route(o, (P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)), (4, 5), 7,
          pool=(2, 3))
    route(far, (P("Creature", 3, 3, 1),), (4,), 15, pool=(1,))
    m1 = OPP.remove_threat_piece(g, o, 0)       # back on 6+2-1=7, ready 9
    m2 = OPP.remove_threat_piece(g, far, 0)     # back on 6, ready 7 < 15
    check("D a removal pushes the kill to return + lead; a far clock holds",
          (m1, o.kill_turn, o.piece_lands, o.next_rebuild, m2, far.kill_turn,
           g.m["threat_rounds_delayed"]),
          (2, 9, [7, 5], 1, 0, 15, 2))

    R = OPP.answer_reach
    try:
        R("you gain 3 life and target player draws a card.")
        raised = False
    except ValueError:
        raised = True
    check("E answer_reach: types, up to, conditions; raises on no type",
          (sorted(R("exile target creature.").types),
           R("exile target permanent with mana value 4 or greater.").min_mv,
           R("target creature gets +3/-3 and loses all creature types "
             "until end of turn.").max_toughness,
           sorted(R("when this creature enters, you may destroy up to three "
                    "target noncreature permanents.").types),
           R("when this creature enters, you may destroy up to three "
             "target noncreature permanents.").n,
           R("exile up to two target artifacts and/or enchantments.").n,
           raised),
          (["Creature"], 4, 3, ["Artifact", "Enchantment", "Planeswalker"], 3,
           2, True))

    g = rgame()
    o0, o1, o2 = g.opponents
    route(o0, (P("Creature", 3, 3, 2), P("Creature", 2, 2, 2)), (3, 9), 11)
    route(o1, (P("Creature", 3, 3, 2), P("Enchantment", 2, 2, 2)), (3, 4), 11)
    route(o2, (P("Artifact", 3, 3, 2), P("Artifact", 2, 2, 2)), (3, 4), 11)
    swords = OPP.ANSWERS["Swords to Plowshares"]
    beast = OPP.ANSWERS["Beast Within"]
    t_sw = OPP.answer_target(g, swords)
    t_bw = OPP.answer_target(g, beast)
    check("F aim: most pieces out, then bracket; reach decides",
          ((g.opponents.index(t_sw[0]), t_sw[1]),
           (g.opponents.index(t_bw[0]), t_bw[1])),
          ((1, 0), (2, 0)))

    bw = find(RM, "Beast Within")
    g = rgame()
    o = g.opponents[2]
    route(o, (P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)), (4, 5), 7)
    got = OPP.countered(g, bw, 0)
    kill_after = o.kill_turn
    g2 = rgame()
    o2 = g2.opponents[2]
    route(o2, (P("Creature", 3, 3, 2), P("Artifact", 1, 2, 1)), (4, 5), 7)
    for opp in g2.opponents:
        opp.counters_left = 5
    g2.counter_rolls = [[[0.0] * 3 for _ in range(OPP.N_COUNTER_SLOTS)]
                        for _ in range(40)]
    hard = EN.Card(name=bw.name, types=bw.types, cost=bw.cost, threat=9.0)
    got2 = OPP.countered(g2, hard, 0)
    check("G a resolving answer removes a piece; a countered one does not",
          (got, kill_after > 7, g.m["threat_pieces_removed"],
           got2, o2.kill_turn, g2.m["threat_pieces_removed"]),
          (False, True, 1, True, 7, 0))

    sw = find(KM, "Swords to Plowshares")
    angel = EN.Card(name="Angel of Despair", types=frozenset({"Creature"}))
    g = rgame()
    o = g.opponents[0]
    route(o, (P("Artifact", 3, 3, 2),), (4,), 9)
    held_none = OPP.hold_answer(g, sw)
    held_angel = OPP.hold_answer(g, angel)
    route(o, (P("Creature", 3, 3, 2),), (4,), 9)
    held_out = OPP.hold_answer(g, sw)
    route(o, (P("Artifact", 3, 3, 2),), (4,), 9)
    naive = OPP.hold_answer(rgame(threat_hold=False), sw)
    off_hold = OPP.hold_answer(rgame(pod_threats=False), sw)
    check("H hold while nothing it hits is out; bodies, naive, OFF never",
          (held_none, held_angel, held_out, naive, off_hold),
          (True, False, False, False, False))

    damnation = find(KM, "Damnation")
    wurm = find(RM, "Massacre Wurm")
    ondu = find(LM, "Ondu Inversion")
    lands = (3, 3, 3)
    pcs = (P("Creature", 2, 2, 2), P("Creature", 5, 5, 2),
           P("Enchantment", 1, 1, 2))
    out = []
    for card in (damnation, wurm, ondu):
        g = rgame()
        o = g.opponents[0]
        route(o, pcs, lands, 20)
        OPP.resolve_own_wipe(g, spare_own=True, card=card)
        out.append(OPP.present_pieces(g, o))
    check("I Damnation creatures, Massacre Wurm t<=2, Ondu everything",
          out, [[2], [1, 2], []])

    g = rgame(pod_threats=False)
    o = g.opponents[2]
    route(o, pcs, lands, 8)
    OPP.countered(g, bw, 0)
    OPP.resolve_own_wipe(g, spare_own=True, card=damnation)
    check("J OFF: no answer, no sweep reaches a piece",
          (o.piece_lands, o.kill_turn), ([3, 3, 3], 8))

    g = tgame()
    o = g.opponents[0]
    route(o, pcs, lands, 20)
    T.coercive_carnage(g)
    check("K Coercive Portal's carnage takes noncreature pieces too",
          OPP.present_pieces(g, o), [])

    g = rgame()
    g.board = EN.Board([land("Forest") for _ in range(3)])
    g.commander_cast = True
    g.hand = [bw]
    o = g.opponents[0]
    route(o, (P("Creature", 3, 3, 2),), (6,), 8)     # lands on THIS pod turn
    EN.main_phase(g)
    held = bw in g.hand
    g.turn = 7
    for p in g.board:
        p.tapped = False
    EN.main_phase(g)
    check("L rendmaw holds Beast Within, then casts it at the piece",
          (held, bw in g.hand, o.kill_turn > 8),
          (True, False, True))

    base = OPP.make_pod(dict(cfg, pod_threats=True), 11)[0]
    two = OPP.make_pod(dict(cfg, pod_threats=True, threat_clock_shift=2.0),
                       11)[0]
    half = [o.kill_turn for seed in range(30) for o in OPP.make_pod(
        dict(cfg, pod_threats=True, threat_clock_shift=0.5), seed)[0]]
    flat = [o.kill_turn for seed in range(30) for o in OPP.make_pod(
        dict(cfg, pod_threats=True), seed)[0]]
    steps = {a - b for a, b in zip(flat, half)}
    check("M the clock shift: 2 rounds earlier, pieces too; 0.5 some by 1",
          ([a.kill_turn - b.kill_turn for a, b in zip(base, two)],
           all(b.piece_lands == [b.kill_turn - p.lead for p in b.pieces]
               for b in two),
           [(a.route, a.pieces, a.rebuild_pool) for a in base]
           == [(b.route, b.pieces, b.rebuild_pool) for b in two],
           steps),
          ([2, 2, 2], True, True, {0, 1}))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Opponent threats that carry the clock (item 24, change 2)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_remove = OPP.remove_threat_piece
    real_roll = OPP.roll_threat_routes
    real_reach = OPP.answer_reach
    real_wipe = OPP.wipe_threat_pieces

    def no_push(g, o, k):
        kill = o.kill_turn
        real_remove(g, o, k)
        o.kill_turn = kill
        return 0

    def fewest(g, reach):
        best, key = None, None
        for i, o in enumerate(g.opponents):
            present = OPP.present_pieces(g, o)
            ok = [k for k in present if OPP.hits(reach, o.pieces[k])]
            if ok and (key is None or len(present) < key):
                best, key = (o, ok[0]), len(present)
        return best

    def no_conditions(clause):
        r = real_reach(clause)
        return r._replace(max_toughness=99, min_mv=0)

    def all_pieces(g, card, scope=None):
        return real_wipe(g, card, scope="nonland")

    def portal_creatures(g, card, scope=None):
        return real_wipe(g, card, scope=None if scope == "nonland" else scope)

    def same_turn(g, o):
        if not o.alive:
            return []
        t = OPP.pod_turn(g)
        return [k for k, lands in enumerate(o.piece_lands) if lands <= t]

    def always_hold(g, card):
        if not OPP.pod_threats_on(g) or not g.cfg.get("threat_hold", True):
            return False
        if "wipe" in card.tags or not ({"Instant", "Sorcery"} & card.types):
            return False
        return card.name in OPP.ANSWERS

    muts = {
        "a removed piece does not push the kill":
            ({"D", "G", "L"}, OPP, "remove_threat_piece", no_push),
        "the pilot aims at the fewest pieces out":
            ({"F"}, OPP, "answer_target", fewest),
        "answer_reach ignores conditions":
            ({"E"}, OPP, "answer_reach", no_conditions),
        "countered no longer answers":
            ({"G", "L"}, OPP, "answer_pod_threat", lambda g, card: 0),
        "never hold":
            ({"H", "L"}, OPP, "hold_answer", lambda g, card: False),
        "every sweeper takes every piece":
            ({"I"}, OPP, "wipe_threat_pieces", all_pieces),
        "the Portal takes creature pieces only":
            ({"K"}, OPP, "wipe_threat_pieces", portal_creatures),
        "a piece is out on the turn it lands":
            ({"C", "L"}, OPP, "present_pieces", same_turn),
        "the hold ignores what is out":
            ({"H", "L"}, OPP, "hold_answer", always_hold),
        "the clock shift is ignored":
            ({"M"}, OPP, "roll_threat_routes",
             lambda cfg, seed, opps: real_roll(
                 dict(cfg, threat_clock_shift=0.0), seed, opps)),
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
