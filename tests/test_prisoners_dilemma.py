#!/usr/bin/env python3
"""Prisoner's Dilemma, and a card's own flashback, in lorehold (2026-10-09).

    python -m tests.test_prisoners_dilemma
    python -m tests.test_prisoners_dilemma --mutate   # 4 mutations, exact sets

Prisoner's Dilemma {3}{R}{R}, Scryfall 2026-10-09: "Each opponent secretly
chooses silence or snitch ... If each opponent chose silence, 4 damage to each
of them. If each opponent chose snitch, 8 damage to each of them. Otherwise,
12 damage to each opponent who chose silence. Flashback {5}{R}{R}."

CASES
  A  snitch (the default): each of three opponents takes 8
  B  silence (`dilemma_choice`): each takes 4
  C  one opponent dead: the two living take 8 each, the dead one nothing
  D  Artist's Talent level 3, one opponent dead: each survivor takes 8 + 2
  E  FLASHBACK: in the graveyard with seven Mountains, the main phase casts
     it for {5}{R}{R}, the opponents take 8, and it is EXILED (702.34a)
  F  six Mountains: the flashback cost is seven, so it stays in the graveyard
  G  `native_flashback=False`: seven Mountains and it is not cast
  H  Faithless Looting's own Flashback {2}{R}, three Mountains: cast, exiled
  K  Faithless Looting, ONE Mountain: its printed {R} is not its flashback cost
  N  NEIGHBOUR: from HAND with five Mountains it is cast and goes to the
     GRAVEYARD, and no flashback is counted

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  snitch deals 4, as silence does                  -> A, C, D, E, N
  exile_flashback does nothing                     -> E, H
  the flashback cost is the PRINTED cost           -> F, K
  `native_flashback` is ignored                    -> G

THE FIRST SET WAS WRONG, and is kept as written: it read A, C, D, E. N checks
the damage of a cast FROM HAND as well as where the card goes, so the damage
mutation reaches it -- the neighbour shares the resolution and differs only in
the zone, which is the point of it.

UNMUTATED (§0z15): D also pins `hits` = the full pod, which has no seam of its
own -- `hits=alive` gives each survivor 9.33 rather than 10 with one opponent
dead, and D reads 30.67 instead of 30. B is the knob's other setting, and
N's ZONE half is reached by no mutation.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
from edhmc.decks import lorehold_v16 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

DECK, CMD = LM.build()
DILEMMA = LM.PRISONERS_DILEMMA
LOOTING = next(c for c in DECK if c.name == "Faithless Looting")
TALENT = next(c for c in DECK if c.name == "Artist's Talent")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def mountains(n):
    return [EN.Card(name="Mountain", types=frozenset({"Land"}), is_land=True,
                    produces=frozenset({"R"})) for _ in range(n)]


def filler(n):
    return [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                    cost={"gen": 9}) for i in range(n)]


def game(lands=0, **cfg):
    g = L.LoreholdGame(list(DECK), CMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard, g.dream_exile = [], [], []
    g.library = filler(20)
    g.turn = 1                      # before the pod's counterspells start
    g.treasures = 0
    for o in g.opponents:
        o.life, o.alive = 40.0, True
    for c in mountains(lands):
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def lives(g):
    return tuple(round(o.life, 2) for o in g.opponents)


def kill_one(g):
    g.opponents[0].life, g.opponents[0].alive = 0.0, False


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    L.apply_spell_effects(g, DILEMMA)
    check("A snitch: each opponent takes 8",
          (lives(g), g.m["dilemma_resolved"]), ((32.0, 32.0, 32.0), 1))

    g = game(dilemma_choice="silence")
    L.apply_spell_effects(g, DILEMMA)
    check("B silence: each opponent takes 4", lives(g), (36.0, 36.0, 36.0))

    g = game()
    kill_one(g)
    L.apply_spell_effects(g, DILEMMA)
    check("C one dead: the two living take 8 each", lives(g),
          (0.0, 32.0, 32.0))

    g = game()
    kill_one(g)
    g.board.append(EN.Permanent(card=TALENT, sick=False))
    g.board[-1].level = 3
    L.apply_spell_effects(g, DILEMMA)
    check("D Artist's Talent level 3, one dead: 10 each to the living",
          lives(g), (0.0, 30.0, 30.0))

    g = game(lands=7)
    g.graveyard.append(DILEMMA)
    L.main_phase(g, reserve=0)
    check("E flashback for seven: cast, 8 each, exiled",
          (g.m["native_flashback_casts"], lives(g), DILEMMA in g.graveyard),
          (1, (32.0, 32.0, 32.0), False))

    g = game(lands=6)
    g.graveyard.append(DILEMMA)
    L.main_phase(g, reserve=0)
    check("F six Mountains: not cast, still in the graveyard",
          (g.m["native_flashback_casts"], DILEMMA in g.graveyard), (0, True))

    g = game(lands=7, native_flashback=False)
    g.graveyard.append(DILEMMA)
    L.main_phase(g, reserve=0)
    check("G native_flashback=False: not cast",
          g.m["native_flashback_casts"], 0)

    g = game(lands=3)
    g.graveyard.append(LOOTING)
    L.main_phase(g, reserve=0)
    check("H Faithless Looting's flashback for three: cast, exiled",
          (g.m["native_flashback_casts"], LOOTING in g.graveyard), (1, False))

    g = game(lands=1)
    g.graveyard.append(LOOTING)
    L.main_phase(g, reserve=0)
    check("K Faithless Looting on one Mountain: not cast",
          g.m["native_flashback_casts"], 0)

    g = game(lands=5)
    g.hand.append(DILEMMA)
    L.main_phase(g, reserve=0)
    check("N NEIGHBOUR: from hand, to the graveyard, no flashback",
          (lives(g), DILEMMA in g.graveyard, g.m["native_flashback_casts"]),
          ((32.0, 32.0, 32.0), True, 0))
    return set(FAIL)


def _printed_costs():
    return {n: dict(c.cost) for n, c in
            (("Prisoner's Dilemma", DILEMMA), ("Faithless Looting", LOOTING))}


def _ignore_knob(orig):
    def wrapped(g, units, reserve):
        g.cfg["native_flashback"] = True
        return orig(g, units, reserve)
    return wrapped


MUTATIONS = [
    ("snitch deals 4, as silence does", "DILEMMA_DAMAGE",
     lambda _o: {"snitch": 4.0, "silence": 4.0}, {"A", "C", "D", "E", "N"}),
    ("exile_flashback does nothing", "exile_flashback",
     lambda _o: (lambda g, card: None), {"E", "H"}),
    ("the flashback cost is the printed cost", "FLASHBACK",
     lambda _o: _printed_costs(), {"F", "K"}),
    ("`native_flashback` is ignored", "flashback_options",
     _ignore_knob, {"G"}),
]


def main() -> int:
    if not MUTATE:
        print("Prisoner's Dilemma and native flashback (2026-10-09)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    print("MUTATION RUN -- exact sets\n")
    good = 0
    for label, attr, make, want in MUTATIONS:
        saved = getattr(L, attr)
        setattr(L, attr, make(saved))
        try:
            broke = run_cases()
        finally:
            setattr(L, attr, saved)
        ok = broke == want
        good += ok
        print(f"   {label}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    bad = len(MUTATIONS) - good
    print(f"{good} passed, {bad} failed ({len(MUTATIONS)} mutations, "
          f"exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
