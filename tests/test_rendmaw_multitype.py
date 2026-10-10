#!/usr/bin/env python3
"""The owner's multi-type batch for rendmaw (§0z125).

    python -m tests.test_rendmaw_multitype
    python -m tests.test_rendmaw_multitype --mutate   # 10 mutations, exact sets

Five candidates, every one two card types (so every cast is a Rendmaw
trigger). Oracle text verbatim on each Proposal in edhmc/pending.py:

  H.E.R.B.I.E., Lovable Robot {2} 1/1 flying; at the beginning of combat on
      your turn, if you've cast a noncreature spell this turn, surveil 1;
      {T}: Add {C}; {1}, {T}: Add one mana of any color.
  The Swarmweaver {2}{B}{G} 2/3: enters -> two 1/1 flying Insects; delirium
      -> Insects and Spiders you control get +1/+1 and deathtouch.
  Wickerfolk Indomitable {3}{B} 4/3: may be cast from the graveyard for
      2 life and the sacrifice of an artifact or creature, on top of its cost.
  Fire Navy Trebuchet {2}{B} 0/4 defender, reach: whenever you attack, a
      2/1 flying artifact Construct named Ballistic Boulder, tapped and
      attacking, sacrificed at the beginning of the next end step.
  Dalek Squadron {2}{B} 3/3 menace, myriad.

CASES
  A  H.E.R.B.I.E. is a flier and taps for {C}
  B  surveil: a noncreature spell cast, a land on top, six lands out: binned
  C  no noncreature spell this turn: no surveil
  D  a noncreature spell, a NONLAND on top: surveilled, kept on top
  E  main_phase sets the noncreature flag for an enchantment, not a creature
  F  The Swarmweaver enters: two Insect tokens, both FLYING
  G  NEIGHBOUR: Grist's Insects (make_tokens with no override) do not fly
  H  delirium with The Swarmweaver: an Insect token 2/2, Haywire Mite 2, a
     Bird token 2 (no bonus)
  I  no delirium: the Insect token is 1
  J  delirium without The Swarmweaver: the Insect token is 1
  K  Wickerfolk cast from the graveyard: on the battlefield, 2 life paid, a
     token sacrificed, one Rendmaw trigger
  L  no creature token to sacrifice: not cast
  M  life 11 (9 after paying, under the floor of 10): not cast
  N  its sacrifice is a death: Blood Artist drains 1
  O  Fire Navy Trebuchet has defender: it does not attack, the Bear does
  P  an attack makes one Ballistic Boulder: tapped, flying, an artifact
  Q  the end step sacrifices it -- a death, Blood Artist drains 1
  R  no attack (the Trebuchet alone): no Boulder
  S  Dalek Squadron attacks with three opponents alive: two copies, and none
     left on the battlefield after combat; the Squadron itself stays
  T  with Primal Vigor: four copies
  U  the copies are EXILED: no creature died this turn
  V  `enters_attacking` makes them attackers, 3/3 tokens, with menace
  W  PROPERTY: no card in the committed list has defender, so the new
     attacker filter is the identity there

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  make_tokens ignores the flying override        -> F, P
  no delirium pump (swarmweaver_bonus 0)          -> H
  the pump ignores delirium                       -> I
  H.E.R.B.I.E.'s surveil never fires              -> B, D
  the graveyard cast is never offered             -> K, N
  the graveyard cast pays no life                 -> K
  defender is ignored (DEFENDER empty)            -> O, R
  the Boulder is never sacrificed                 -> Q
  the myriad copies are never exiled              -> S, U
  token doubling ignored                          -> T

UNMUTATED, and written down (§0z15): A and W are static facts (the generated
FLYING and DEFENDER sets); C, E, L and M are gates with no seam of their own
(C's flag is E's, L and M sit inside `wickerfolk_option`); G is the default
path every other token takes; J is `has` and V's menace is the generated
MENACE, both pinned elsewhere.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = RM.build()
HERBIE = RM.HERBIE_LOVABLE_ROBOT
SWARM = RM.THE_SWARMWEAVER
WICKER = RM.WICKERFOLK_INDOMITABLE
TREB = RM.FIRE_NAVY_TREBUCHET
DALEK = RM.DALEK_SQUADRON
BEAR = EN.Card(name="Test Bear", types=frozenset({"Creature"}),
               cost={"gen": 1}, power=2, toughness=2, priority=5)
CHARM = EN.Card(name="Test Charm", types=frozenset({"Enchantment"}),
                cost={"gen": 1}, priority=5)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(name, colour):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({colour}))


def card(name):
    return next(c for c in DECK if c.name == name)


def game(*cards, life=40.0):
    g = EN.Game(list(DECK), CMD, dict(DEFAULT_CFG, turns=20),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"F{i}", types=frozenset({"Sorcery"}),
                         cost={"gen": 9}) for i in range(20)]
    g.commander_cast = True
    g.turn = 6
    g.your_life = life
    for o in g.opponents:
        o.counters_left = 0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def token(g, subtype, p=1, t=1):
    return g.make_tokens(1, p, t, subtype)[0]


def pod_life(g):
    return sum(o.life for o in g.opponents)


def surveil(flag, top):
    g = game(*[land("Swamp", "B") for _ in range(6)], HERBIE)
    g.noncreature_cast_this_turn = flag
    g.library.append(top)
    EN.herbie_surveil(g)
    return (g.m["herbie_surveils"], g.m["herbie_binned"],
            g.library[-1] is top)


def delirium(g, on):
    kinds = ("Land", "Creature", "Artifact", "Sorcery") if on else ("Land",)
    g.graveyard = [EN.Card(name=f"G{k}", types=frozenset({k})) for k in kinds]


def wicker(*cards, life=40.0, bird=True):
    g = game(*[land("Swamp", "B") for _ in range(4)], *cards, life=life)
    if bird:
        token(g, "Bird", 2, 2)
    g.graveyard = [WICKER]
    return g


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A H.E.R.B.I.E. flies and taps for {C}",
          (HERBIE.flying, HERBIE.mana_ability), (True, (1, frozenset("C"))))
    check("B surveil: a land on top with six lands out is binned",
          surveil(True, land("Forest", "G")), (1, 1, False))
    check("C no noncreature spell: no surveil",
          surveil(False, land("Forest", "G")), (0, 0, True))
    check("D a nonland on top: surveilled, kept",
          surveil(True, BEAR), (1, 0, True))
    flags = []
    for c in (CHARM, BEAR):
        g = game(land("Swamp", "B"))
        g.hand = [c]
        EN.main_phase(g)
        flags.append(g.noncreature_cast_this_turn)
    check("E the noncreature flag: an enchantment yes, a creature no",
          tuple(flags), (True, False))
    g = game()
    perm = EN.Permanent(card=SWARM, sick=True)
    g.board.append(perm)
    EN.run_etb(g, perm)
    ins = [p for p in g.board if p.card.name == "Insect token"]
    check("F The Swarmweaver enters: two flying Insects",
          (len(ins), all(p.card.flying for p in ins)), (2, True))
    g = game()
    check("G NEIGHBOUR: Grist's Insects do not fly",
          token(g, "Insect").card.flying, False)
    g = game(SWARM, card("Haywire Mite"))
    delirium(g, True)
    ins, bird = token(g, "Insect"), token(g, "Bird", 2, 2)
    mite = next(p for p in g.board if p.card.name == "Haywire Mite")
    check("H delirium: Insect 2/2, Haywire Mite 2, Bird 2",
          (g.power_of(ins), g.toughness_of(ins), g.power_of(mite),
           g.power_of(bird)), (2, 2, 2, 2))
    g = game(SWARM)
    delirium(g, False)
    check("I no delirium: the Insect is 1", g.power_of(token(g, "Insect")), 1)
    g = game()
    delirium(g, True)
    check("J delirium, no Swarmweaver: the Insect is 1",
          g.power_of(token(g, "Insect")), 1)
    g = wicker()
    EN.main_phase(g)
    check("K Wickerfolk from the graveyard: cast, 2 life, a token, a trigger",
          (any(p.card is WICKER for p in g.board), WICKER in g.graveyard,
           g.your_life, g.m["wickerfolk_gy_casts"], g.m["rendmaw_triggers"]),
          (True, False, 38.0, 1, 1))
    g = wicker(bird=False)
    EN.main_phase(g)
    check("L no token to sacrifice: not cast", WICKER in g.graveyard, True)
    g = wicker(life=11.0)
    EN.main_phase(g)
    check("M life 11: under the floor, not cast", WICKER in g.graveyard, True)
    g = wicker(card("Blood Artist"))
    before = pod_life(g)
    EN.main_phase(g)
    check("N the sacrifice is a death: Blood Artist drains 1",
          before - pod_life(g), 1.0)
    g = game(TREB, BEAR)
    EN.combat(g)
    t = next(p for p in g.board if p.card is TREB)
    b = next(p for p in g.board if p.card is BEAR)
    check("O defender: the Trebuchet stays home, the Bear attacks",
          (t.tapped, b.tapped), (False, True))
    boulders = [p for p in g.board if p.card.name == "Ballistic Boulder"]
    check("P one Ballistic Boulder: tapped, flying, an artifact",
          (g.m["boulders_made"], len(boulders),
           all(p.tapped and p.card.flying and "Artifact" in p.card.types
               for p in boulders)), (1, 1, True))
    g = game(TREB, BEAR, card("Blood Artist"))
    EN.combat(g)
    before = pod_life(g)
    EN.boulder_end_step(g)
    check("Q the end step sacrifices it: a death, Blood Artist drains 1",
          (g.m["boulders_sacrificed"],
           any(p.card.name == "Ballistic Boulder" for p in g.board),
           before - pod_life(g)), (1, False, 1.0))
    g = game(TREB)
    EN.combat(g)
    check("R no attack: no Boulder", g.m["boulders_made"], 0)
    g = game(DALEK)
    EN.combat(g)
    check("S myriad, three alive: two copies, none left, the Squadron stays",
          (g.m["myriad_copies"],
           sum(1 for p in g.board if p.card.name == "Dalek Squadron")),
          (2, 1))
    g = game(DALEK, card("Primal Vigor"))
    EN.combat(g)
    check("T Primal Vigor: four copies", g.m["myriad_copies"], 4)
    g = game(DALEK)
    EN.combat(g)
    check("U the copies are exiled: nothing died, none on the battlefield",
          (g.creature_died_this_turn,
           sum(1 for p in g.board if p.is_token)), (False, 0))
    g = game(DALEK)
    att = [next(p for p in g.board if p.card is DALEK)]
    EN.enters_attacking(g, att)
    check("V copies are attackers: 3/3 menace tokens",
          (len(att), all(p.is_token and g.power_of(p) == 3
                         and OPP.menace_of(g, p) for p in att[1:])),
          (3, True))
    check("W PROPERTY: no committed card has defender",
          sorted({c.name for c in DECK} & EN.DEFENDER), [])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Rendmaw: the owner's multi-type batch (§0z125)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_make = EN.Game.make_tokens

    def no_flying_override(self, n, p, t, subtype="", tapped=False,
                           flying=None, artifact=False, name=None):
        return real_make(self, n, p, t, subtype, tapped, None, artifact, name)

    def always_pumped(g, perm):
        return int(g.has("The Swarmweaver")
                   and (perm.card.name in EN.INSECT_SPIDER
                        or perm.card.name in EN.INSECT_SPIDER_TOKENS))

    real_costs = EN.wickerfolk_additional_costs

    def no_life(g, c):
        life = g.your_life
        real_costs(g, c)
        g.your_life = life

    muts = {
        "make_tokens ignores the flying override":
            ({"F", "P"}, EN.Game, "make_tokens", no_flying_override),
        "no delirium pump":
            ({"H"}, EN, "swarmweaver_bonus", lambda g, perm: 0),
        "the pump ignores delirium":
            ({"I"}, EN, "swarmweaver_bonus", always_pumped),
        "H.E.R.B.I.E.'s surveil never fires":
            ({"B", "D"}, EN, "herbie_surveil", lambda g: None),
        "the graveyard cast is never offered":
            ({"K", "N"}, EN, "wickerfolk_option", lambda g, units: None),
        "the graveyard cast pays no life":
            ({"K"}, EN, "wickerfolk_additional_costs", no_life),
        "defender is ignored":
            ({"O", "R"}, EN, "DEFENDER", frozenset()),
        "the Boulder is never sacrificed":
            ({"Q"}, EN, "boulder_end_step", lambda g: None),
        "the myriad copies are never exiled":
            ({"S", "U"}, EN, "myriad_exile", lambda g: None),
        "token doubling ignored":
            ({"T"}, EN, "token_doublings", lambda g: 1),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        real = (mod.__dict__[name] if isinstance(mod, type)
                else getattr(mod, name))
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    assert EN.Game.make_tokens is real_make
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
