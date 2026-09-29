#!/usr/bin/env python3
"""Shilgengar's trigger lifegain reaches the lifegain payoffs, and finality
creatures are exiled instead of dying (§0z75).

    python -m tests.test_shilgengar_life_finality
    python -m tests.test_shilgengar_life_finality --mutate   # 3 mutations

    Blood Artist        Whenever this creature or another creature dies,
                        target player loses 1 life and you gain 1 life.
    Zulaport Cutthroat  Whenever this creature or another creature you
                        control dies, each opponent loses 1 life and you gain
                        1 life.
    Vampiric Rites      {1}{B}, Sacrifice a creature: You gain 1 life and draw
                        a card.                (Scryfall, verified 2026-09-29)
    Finality counter    If a creature with a finality counter on it would
                        die, exile it instead.

§0z74 found both gaps and left them: the three cards above wrote `your_life`
directly, so Archangel of Thune, Lyra and Selenia never saw those gains; and a
creature carrying a finality counter still fired every death trigger except
Selenia's and went to the graveyard. `ShilgengarGame.trigger_gain` and the
optional protocol hook `exiled_instead_of_dying` (asked by `sacrifice` and by
the shared `opponents.destroy`) close them.

CASES
  A  Blood Artist + Archangel of Thune: a death puts a counter on each creature
  B  Zulaport Cutthroat + Lyra, Archangel of Dawn: a death puts a counter on
     each Angel
  C  Vampiric Rites' activation is a lifegain event (lifegain_triggers +1)
  D  Selenia doubles Blood Artist's gain: +2 life on one death
  E  `gain_life_routed=False`: Thune sees nothing (the old engine)
  F  a finality creature destroyed by the pod: no Blood Artist drain, not in
     the graveyard, counted as exiled
  G  a finality creature sacrificed to Shilgengar: its Blood is still made,
     no death trigger, not in the graveyard
  H  NEIGHBOUR: a creature WITHOUT the counter destroyed: Blood Artist drains,
     the card reaches the graveyard
  I  `finality_exiles=False`: the finality creature dies as before

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  trigger gains write your_life directly     -> A, B, C, D
  the finality hook never fires              -> F, G
  the finality hook fires for every card     -> A, B, D, H

  ONE EXPECTATION WAS WRONG, AND IT IS KEPT HERE. The last set was written
  as "-> H". A hook that fires for every nontoken card also exiles the
  ordinary creature dying in A, B and D, so their death triggers never fire
  -- which is what the mutation means. Its first version also ignored the
  `finality_exiles` knob and broke I; a mutation removes ONE rule, so it
  keeps the knob now (the same mistake as test_commander_aim's, §0z67).

UNMUTATED (§0z15): E and I are the knobs reproducing the old engine.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = SM.build()
POOL = list(DECK) + [v for v in vars(SM).values() if isinstance(v, EN.Card)]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return next(c for c in POOL if c.name == name)


def perm(c):
    return EN.Permanent(card=c, sick=False, base_p=c.power, base_t=c.toughness)


def body(name="Bear", p=2, t=2):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=t)


def game(*cards, **cfg):
    g = SH.ShilgengarGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **cfg), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(20)]
    g.turn = 5
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(perm(c))
    return g


def dies(g, c):
    """Destroy a creature through the pod's shared path."""
    p = perm(c)
    g.board.append(p)
    OPP.destroy(g, p, destroys=True)
    return p


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g = game(card("Blood Artist"), card("Archangel of Thune"))
    dies(g, body())
    check("A Blood Artist + Thune: a counter on each creature",
          [p.counters for p in g.board], [1, 1])
    lyra = card("Lyra, Archangel of Dawn")
    g = game(card("Zulaport Cutthroat"), lyra)
    dies(g, body())
    check("B Zulaport + Lyra: a counter on the Angel",
          next(p.counters for p in g.board if p.card is lyra), 1)
    # A payoff that gains no life, so `aristocrats_step` runs and the only
    # lifegain event is Rites' own. (It returns early with NO payoff and no
    # commander, although its comment says Rites is worth using alone -- a
    # pre-existing inconsistency, named in §0z75 and not changed here.)
    g = game(card("Vampiric Rites"), card("Pitiless Plunderer"))
    tok = EN.Permanent(card=body("Spirit token", 1, 1), sick=False,
                       is_token=True)
    g.board.append(tok)
    g.board += [perm(EN.Card(name=f"Swamp{i}", types=frozenset({"Land"}),
                             is_land=True, produces=frozenset({"B"})))
                for i in range(2)]
    g.aristocrats_step()
    check("C Vampiric Rites is a lifegain event",
          g.m["lifegain_triggers"], 1)
    g = game(card("Blood Artist"), card("Selenia, the Cursed Heart"))
    life = g.your_life
    dies(g, body())
    check("D Selenia doubles Blood Artist: +2", g.your_life - life, 2)
    g = game(card("Blood Artist"), card("Archangel of Thune"),
             gain_life_routed=False)
    dies(g, body())
    check("E routing off: Thune sees nothing",
          [p.counters for p in g.board], [0, 0])
    g = game(card("Blood Artist"))
    fin = body("Returned")
    g.finality.add(id(fin))
    dies(g, fin)
    check("F finality, destroyed: no drain, not in graveyard, exiled",
          (g.m["drain_damage"], fin in g.graveyard, g.m["finality_exiled"]),
          (0, False, 1))
    g = game(card("Blood Artist"))
    g.commander_cast = True
    fin = body("Returned")
    g.finality.add(id(fin))
    p = perm(fin)
    g.board.append(p)
    g.sacrifice(p, to_shilgengar=True)
    check("G finality, sacrificed: Blood made, no trigger, not in graveyard",
          (g.m["blood_made"], g.m["drain_damage"], fin in g.graveyard),
          (1, 0, False))
    g = game(card("Blood Artist"))
    plain = body("Plain")
    dies(g, plain)
    check("H no counter: Blood Artist drains, card in graveyard",
          (g.m["drain_damage"], plain in g.graveyard), (1.0, True))
    g = game(card("Blood Artist"), finality_exiles=False)
    fin = body("Returned")
    g.finality.add(id(fin))
    dies(g, fin)
    check("I finality_exiles off: it dies as before",
          (g.m["drain_damage"], fin in g.graveyard), (1.0, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Shilgengar: trigger lifegain, and finality\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    G = SH.ShilgengarGame
    real = {n: getattr(G, n) for n in ("trigger_gain", "exiled_instead_of_dying")}

    def direct(self, amount):
        self.your_life += amount

    muts = {
        "trigger gains write your_life directly":
            ({"A", "B", "C", "D"}, "trigger_gain", direct),
        "the finality hook never fires":
            ({"F", "G"}, "exiled_instead_of_dying", lambda self, p: False),
        "the finality hook fires for every card":
            ({"A", "B", "D", "H"}, "exiled_instead_of_dying",
             lambda self, p: (self.cfg.get("finality_exiles", True)
                              and not p.is_token)),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(G, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(G, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
