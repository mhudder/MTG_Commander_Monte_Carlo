#!/usr/bin/env python3
"""Item 24's last four route answers (§0z138), all under `pod_threats`:
Damn's single-target mode, the voting answers, the attack taxes, and the
wipe gate reading routes.

    python -m tests.test_route_answers
    python -m tests.test_route_answers --mutate   # 10 mutations, exact sets

Texts (Scryfall, 2026-10-14): Damn "Destroy target creature ... Overload
{2}{W}{W}"; Council's Judgment "each player votes for a nonland permanent you
don't control. Exile each permanent with the most votes or tied for most
votes"; Vault 11, chapters II and III, "Each player secretly votes for up to
one creature ... destroy each creature with the most votes or tied for most
votes"; Ghostly Prison and Propaganda "Creatures can't attack you unless
their controller pays {2} for each creature they control that's attacking
you".

CASES
  A  Damn's single-target reach comes from its census clause (a creature);
     the mode is ready only under `pod_threats`, with the knob on, and with a
     creature piece out
  B  the mode a cast is priced at: single when the gate refuses the wrath,
     single when the gate wants it but the overload cannot be paid, the
     overload when it can; never off `pod_threats`
  C  end to end, tivit's main phase with {B}{B}: Damn is cast at the piece,
     the piece goes back, and the wrath half does not resolve (your
     creature lives)
  D  Council's Judgment: one vote against three loses; Tivit plus Ballot
     Broker ties three-all and the tie exiles the piece
  E  Vault 11: winning takes the piece; losing takes your most-wanted
     creature (not an indestructible one); a tie takes both
  F  the hold: Council's Judgment waits while nothing is out under
     `pod_threats`, and is never held off it
  G  the tax: `ATTACK_TAX` is generated (both cards, {2}); through-share 1
     with none out, 0.5 with one, 0.25 with both, 1 off `pod_threats`
  H  a combat route's kill aimed at you is deflected at `attack_tax_deflect`
     1.0 and never at 0.0; a drain route and a lone opponent never are
  I  end to end, `resolve_clocks`: a combat clock that rolled you kills
     another opponent instead when the tax deflects it (a Prison out in
     both legs; deflect 0 against 1)
  J  the pod's chip damage at you is scaled by the through-share (one
     Prison in both legs; deflect 0 against 0.5)
  K  the wipe gate: a creature piece the sweeper takes opens a gate that
     was shut; `wipe_gate_pieces=False` leaves it shut
  L  `wipe_takes` is the scope rule: Damnation takes the creature piece and
     not the artifact one, Ondu Inversion both; the sweeper removes exactly
     that list

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the single-target mode is never ready              -> A, B, C
  the overload's affordability is ignored            -> B
  a single cast resolves the wrath as well           -> C
  a tied council loses (Judgment)                    -> D
  Vault 11 never takes your creature                 -> E
  the hold ignores the voting answers                -> F
  the taxes let everything through                   -> G, H, I, J
  any route's kill is deflected, not combat only     -> H
  the gate ignores the pieces                        -> K
  every sweeper takes every piece (wipe_takes)       -> L

  A TRANSCRIPT (§0z14): the ten sets above held on the first mutation run.
  Four CASES failed their first plain run, all on setup, none on the code:
  B's "gate refuses" leg had 5 power against six creatures (the gate was
  open); I's empty board has share 0 of the clock, so nothing was ever aimed
  at you; J added the Prison to one leg only, and it carries threat, so it
  moved the share as well as the tax -- the §0z137 shape, both legs now hold
  it; K's seat 0 rolled a 0.69-power archetype. Each comment says why.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as T
import edhmc.voting as V
from edhmc.decks import _evasion
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import shilgengar_v1 as SM
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


def route(o, pieces, lands, kill, kind="combat"):
    o.route = kind
    o.pieces = tuple(pieces)
    o.piece_lands = list(lands)
    o.kill_turn = kill
    o.rebuild_pool, o.next_rebuild = (2,), 0
    o.clock_fired = False


def tgame(**cfg):
    deck, cmd = TM.build()
    g = T.TivitGame(list(deck), cmd,
                    dict(DEFAULT_CFG, **dict(dict(pod_threats=True), **cfg)),
                    1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    g.commander_cast = True
    for o in g.opponents:
        o.life, o.creatures, o.alive, o.counters_left = 40.0, 0.0, True, 0
        route(o, (), (), 99)
    return g


def put(g, module, name, n=1):
    for _ in range(n):
        g.board.append(EN.Permanent(card=find(module, name), sick=False))


def body(g, power, threat=None, name=None):
    c = EN.Card(name=name or f"Body{power}", types=frozenset({"Creature"}),
                power=power, toughness=power, threat=threat)
    p = EN.Permanent(card=c, sick=False, base_p=power, base_t=power)
    g.board.append(p)
    return p


CREATURE = P("Creature", 3, 3, 2)
ARTIFACT = P("Artifact", 1, 2, 1)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    damn = find(TM, "Damn")

    ready = []
    for cfg, piece in (({}, CREATURE), ({"pod_threats": False}, CREATURE),
                       ({"overload_single_target": False}, CREATURE),
                       ({}, ARTIFACT)):
        g = tgame(**cfg)
        route(g.opponents[0], (piece,), (3,), 10)
        ready.append(OPP.single_target_ready(g, damn))
    check("A Damn's reach from its clause; ready only with a creature piece",
          (OPP.SINGLE_TARGET["Damn"], ready),
          (OPP.Reach(frozenset({"Creature"}), 1, 99, 0),
           [True, False, False, False]))

    base, over = {"B": 2}, OPP.OVERLOAD_WIPES["Damn"]
    four = [frozenset({"W"}), frozenset({"W"}), frozenset({"B"}),
            frozenset({"B"})]
    two = [frozenset({"B"}), frozenset({"B"})]
    priced = []
    # 20 power of yours shuts the gate; none with six of theirs opens it.
    for threats, mine, units in ((True, 20, four), (True, 0, two),
                                 (True, 0, four), (False, 20, four)):
        g = tgame(pod_threats=threats)
        route(g.opponents[0], (CREATURE,), (3,), 10)
        g.opponents[1].creatures = 6.0
        if mine:
            body(g, mine)
        priced.append(OPP.wipe_mode_cost(g, damn, dict(base), units) == base)
    check("B single when the gate refuses or the overload is unaffordable",
          priced, [True, True, False, False])

    g = tgame()
    put(g, TM, "Swamp", 2)
    mine = body(g, 5)
    o = g.opponents[0]
    route(o, (CREATURE,), (3,), 8)
    g.hand = [damn]
    T.main_phase(g)
    check("C tivit casts Damn single-target: piece back, your creature lives",
          (damn in g.hand, o.piece_lands != [3], o.kill_turn > 8,
           mine in g.board, g.m["single_target_casts"], g.m["own_wipes_cast"]),
          (False, True, True, True, 1, 0))

    out = []
    for extras in ((), ("Tivit, Seller of Secrets", "Ballot Broker")):
        g = tgame()
        for name in extras:
            put(g, TM, name)
        o = g.opponents[0]
        route(o, (ARTIFACT,), (3,), 10)
        out.append((V.judgment(g), o.piece_lands != [3]))
    check("D Council's Judgment: 1 v 3 loses; a 3-3 tie exiles the piece",
          out, [(False, False), (True, True)])

    out = []
    for extras in (("Tivit, Seller of Secrets", "Ballot Broker",
                    "Brago's Representative"),
                   (),
                   ("Tivit, Seller of Secrets", "Ballot Broker")):
        g = tgame()
        for name in extras:
            put(g, TM, name)
        hardy = body(g, 9, threat=50.0, name="Hardy")
        hardy.card = hardy.card.__class__(**{**vars(hardy.card),
                                            "indestructible": True})
        wanted = body(g, 4, threat=20.0, name="Wanted")
        o = g.opponents[0]
        route(o, (CREATURE,), (3,), 10)
        V.dilemma_vault(g)
        out.append((o.piece_lands != [3], wanted in g.board, hardy in g.board))
    check("E Vault 11: win takes the piece, loss your creature, tie both",
          out, [(True, True, True), (False, False, True),
                (True, False, True)])

    judge = find(TM, "Council's Judgment")
    held = []
    for threats in (True, False):
        g = tgame(pod_threats=threats)
        held.append(OPP.hold_answer(g, judge))
        route(g.opponents[0], (ARTIFACT,), (3,), 10)
        held.append(OPP.hold_answer(g, judge))
    check("F Council's Judgment held while nothing is out, only on the pod",
          held, [True, False, False, False])

    through = []
    for threats, names in ((True, ()), (True, ("Ghostly Prison",)),
                           (True, ("Ghostly Prison", "Propaganda")),
                           (False, ("Ghostly Prison", "Propaganda"))):
        g = tgame(pod_threats=threats)
        for name in names:
            put(g, TM, name)
        through.append(OPP.attack_tax_through(g))
    check("G the tax is generated; through 1, 0.5, 0.25, and 1 off the pod",
          ({k: _evasion.ATTACK_TAX[k] for k in ("Ghostly Prison",
                                                 "Propaganda")}, through),
          ({"Ghostly Prison": 2, "Propaganda": 2}, [1.0, 0.5, 0.25, 1.0]))

    out = []
    for d, kind, alone in ((1.0, "combat", False), (0.0, "combat", False),
                           (1.0, "drain", False), (1.0, "combat", True)):
        g = tgame(attack_tax_deflect=d)
        put(g, TM, "Ghostly Prison")
        o = g.opponents[0]
        route(o, (CREATURE,), (3,), 6, kind=kind)
        others = [] if alone else g.opponents[1:]
        out.append(OPP.tax_deflects(g, 0, o, others))
    check("H deflected at 1.0 only: never at 0.0, a drain route, or alone",
          out, [True, False, False, False])

    out = []
    for d in (0.0, 1.0):
        # Your share of the clock is threat-weighted: a board with a threat
        # draws it (an empty one has share 0 and is never picked).
        g = tgame(attack_tax_deflect=d)
        put(g, TM, "Ghostly Prison")
        body(g, 3, threat=10.0)
        o = g.opponents[0]
        route(o, (CREATURE,), (3,), 6)
        for x in g.opponents[1:]:
            route(x, (), (), 99)
        g.opp_rolls[OPP.pod_turn(g)][0][6] = 0.0        # it picks you
        OPP.resolve_clocks(g)
        out.append((g.result, sum(x.alive for x in g.opponents)))
    check("I a taxed combat kill aimed at you takes another opponent",
          out, [("loss", 3), (None, 2)])

    lost = []
    # The Prison is on the board in both legs: it carries threat, so its
    # presence moves your share of the swing on its own. The legs differ in
    # the tax alone (§0z137: drive both legs through the same steps).
    for d in (0.0, 0.5):
        g = tgame(attack_tax_deflect=d)
        put(g, TM, "Ghostly Prison")
        for x in g.opponents:
            x.creatures = 4.0
        OPP.incidental_damage(g)
        lost.append(40.0 - g.your_life)
    check("J the pod's chip damage at you halves at deflect 0.5, one Prison",
          (lost[0] > 0, abs(lost[1] * 2 - lost[0]) < 1e-9), (True, True))

    wrath = find(SM, "Wrath of God")
    gates = []
    for cfg, pieces in (({}, ()), ({}, (CREATURE, CREATURE)),
                        ({"wipe_gate_pieces": False}, (CREATURE, CREATURE))):
        # Seat 1's creatures are 1.34 power apiece on this seed: two pieces
        # are 2.68 against your 1 * 1.4 + 1.
        g = tgame(**cfg)
        body(g, 1)
        route(g.opponents[1], pieces, [3] * len(pieces), 10)
        gates.append(OPP.should_cast_own_wipe(g, wrath))
    check("K a route's pieces open the wipe gate; off, they do not",
          gates, [False, True, False])

    damnation = find(KM, "Damnation")
    ondu = EN.Card(name="Ondu Inversion", types=frozenset({"Sorcery"}),
                   tags=("wipe",))
    out = []
    for card in (damnation, ondu):
        g = tgame()
        o = g.opponents[0]
        route(o, (CREATURE, ARTIFACT), (3, 3), 10)
        takes = [k for _o, k in OPP.wipe_takes(g, card)]
        OPP.wipe_threat_pieces(g, card)
        out.append((takes, [k for k, ln in enumerate(o.piece_lands)
                            if ln != 3]))
    check("L wipe_takes is the scope; the sweeper removes exactly that",
          out, [([0], [0]), ([0, 1], [0, 1])])

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Item 24's last four route answers (§0z138)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_wmc, real_resolve = OPP.wipe_mode_cost, OPP.resolve_own_wipe
    real_takes = OPP.wipe_takes
    real_destroy = OPP.destroy

    def no_afford(g, card, base, units=None):
        return real_wmc(g, card, base, None)

    def double(g, spare_own=False, card=None):
        g.single_cast = None
        return real_resolve(g, spare_own=spare_own, card=card)

    def judgment_tie_loses(g, name="Council's Judgment"):
        # `voting.judgment` with `won = mine > against`: a tie loses.
        mine, against = V.council_votes(g)
        pick = OPP.answer_target(g, OPP.VOTE_ANSWERS[name])
        if mine > against and pick is not None:
            OPP.remove_threat_piece(g, *pick)
            return True
        return False

    def spare_yours(g, perm, roll=None, destroys=None, kind=None):
        return False

    def vault_spares(g, name="Vault 11: Voter's Dilemma"):
        OPP.destroy = spare_yours
        try:
            return real_vault(g, name)
        finally:
            OPP.destroy = real_destroy

    real_vault = V.dilemma_vault

    def any_route(g, i, opp, others):
        kind = opp.route
        opp.route = "combat"
        try:
            return real_deflects(g, i, opp, others)
        finally:
            opp.route = kind

    real_deflects = OPP.tax_deflects

    muts = {
        "the single-target mode is never ready":
            ({"A", "B", "C"}, OPP, "single_target_ready",
             lambda g, card: False),
        "the overload's affordability is ignored":
            ({"B"}, OPP, "wipe_mode_cost", no_afford),
        "a single cast resolves the wrath as well":
            ({"C"}, OPP, "resolve_own_wipe", double),
        "a tied council loses (Judgment)":
            ({"D"}, V, "judgment", judgment_tie_loses),
        "Vault 11 never takes your creature":
            ({"E"}, V, "dilemma_vault", vault_spares),
        "the hold ignores the voting answers":
            ({"F"}, OPP, "vote_answers_on", lambda g: False),
        "the taxes let everything through":
            ({"G", "H", "I", "J"}, OPP, "attack_tax_through",
             lambda g: 1.0),
        "any route's kill is deflected, not combat only":
            ({"H"}, OPP, "tax_deflects", any_route),
        "the gate ignores the pieces":
            ({"K"}, OPP, "gate_pieces", lambda g, card, measure: 0.0),
        "every sweeper takes every piece":
            ({"L"}, OPP, "wipe_takes",
             lambda g, card, scope=None: real_takes(g, card, "nonland")),
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
