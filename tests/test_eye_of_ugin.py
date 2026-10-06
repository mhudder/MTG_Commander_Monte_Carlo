#!/usr/bin/env python3
"""Pin Eye of Ugin's tutor and Kozilek's cast draw (§0z114, azusa).

    python -m tests.test_eye_of_ugin
    python -m tests.test_eye_of_ugin --mutate   # 2 mutations, exact sets

Eye of Ugin: "Colorless Eldrazi spells you cast cost {2} less to cast. {7},
{T}: Search your library for a colorless creature card, reveal it, put it into
your hand, then shuffle." Only the first sentence was modelled.
Kozilek, Butcher of Truth: "When you cast this spell, draw four cards." --
not modelled, while the card was listed as SCRIPTED.

CASES
  A  the Eye with seven spare mana puts Kozilek (the cheaper Eldrazi) into
     hand, taps itself and seven lands
  B  ... not with six
  C  ... not while a colourless creature is already in hand
  D  Dryad Arbor is not a colourless creature (a land, and green)
  E  casting Kozilek draws four
  F  the pilot reads those four before casting (`draws_on_resolve`)
  G  `activations` runs the Eye step

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  eye_tutor = "off"            -> A, G
  kozilek_cast_draw = False    -> E, F

UNMUTATED (§0z15): B, C and D are the policy's own guards, inside the step;
no seam separates them from the step the first mutation switches off.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.decks import azusa_v1 as AM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = AM.build()
BY = {c.name: c for c in DECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def forest():
    return EN.Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({"G"}))


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def game(lands, library, hand=()):
    g = AZ.AzusaGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **CFG), 99)
    g.board, g.graveyard = EN.Board(), []
    g.hand = list(hand)
    g.library = list(library)
    g.board.append(EN.Permanent(card=BY["Eye of Ugin"], sick=False))
    for _ in range(lands):
        g.board.append(EN.Permanent(card=forest(), sick=False))
    g.clues = 0
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()
    koz, ula = BY["Kozilek, Butcher of Truth"], BY["Ulamog, the Infinite Gyre"]
    lib = [filler(i) for i in range(10)] + [ula, koz]

    g = game(7, lib)
    g.eye_of_ugin_step()
    check("A seven spare mana: Kozilek to hand, the Eye and seven lands tapped",
          ([c.name for c in g.hand], sum(p.tapped for p in g.board),
           g.m["eye_tutors"]), (["Kozilek, Butcher of Truth"], 8, 1))

    g = game(6, lib)
    g.eye_of_ugin_step()
    check("B ... not with six", (g.hand, g.m["eye_tutors"]), ([], 0))

    g = game(7, lib[:-1], hand=[koz])
    g.eye_of_ugin_step()
    check("C ... not while one is already in hand",
          (len(g.hand), g.m["eye_tutors"]), (1, 0))

    g = game(7, [filler(i) for i in range(5)] + [BY["Dryad Arbor"]])
    g.eye_of_ugin_step()
    check("D Dryad Arbor is not a colourless creature", g.m["eye_tutors"], 0)

    g = game(0, [filler(i) for i in range(10)])
    g.creature_spell_cast(koz)
    check("E casting Kozilek draws four",
          (len(g.hand), len(g.library), g.m["kozilek_draws"]), (4, 6, 4))

    check("F the pilot reads the four before casting",
          game(0, lib).draws_on_resolve(koz), 4)

    g = game(7, lib)
    g.activations()
    check("G activations runs the Eye step", g.m["eye_tutors"], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Eye of Ugin and Kozilek (§0z114)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ('eye_tutor = "off"', {"eye_tutor": "off"}, {"A", "G"}),
        ("kozilek_cast_draw = False", {"kozilek_cast_draw": False},
         {"E", "F"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for label, cfg, want in mutations:
        CFG.update(cfg)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {label}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
