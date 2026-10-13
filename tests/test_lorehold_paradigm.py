#!/usr/bin/env python3
"""Restoration Seminar and Improvisation Capstone in lorehold (item 24,
change 0): two Lessons that were KNOWN_BLIND -- a vanilla seven-mana sorcery
each -- for want of code.

    python -m tests.test_lorehold_paradigm
    python -m tests.test_lorehold_paradigm --mutate   # 6 mutations

    Restoration Seminar {5}{W}{W} Sorcery -- Lesson  (Scryfall, 2026-10-13)
    Return target nonland permanent card from your graveyard to the
    battlefield. / Paradigm (Then exile this spell. After you first resolve a
    spell with this name, you may cast a copy of it from exile without paying
    its mana cost at the beginning of each of your first main phases.)
    Improvisation Capstone {5}{R}{R} Sorcery -- Lesson
    Exile cards from the top of your library until you exile cards with total
    mana value 4 or greater. You may cast any number of spells from among
    them without paying their mana costs. / Paradigm (as above)

CASES
  A  Seminar resolves: the highest-priority nonland permanent card returns;
     the Seminar is exiled, not in the graveyard
  B  ... a land is not a legal target: nothing returns, and the pilot does
     not cast a Seminar with only a land in the graveyard
  C  paradigm: at the next main phase a copy is CAST (spells_cast +1) and
     returns another card; nothing reaches the graveyard
  D  ... with no legal target the copy is declined
  E  Capstone: exiles 3-drop, land, 2-drop (total 5) and casts both spells;
     the land is lost; the Capstone is exiled
  F  the Capstone's copy is declined with 15 cards or fewer in the library

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  restoration_seminar does nothing             -> A, C
  seminar_target falls back to a land          -> B
  PARADIGM is empty (the card goes to the yard) -> A, C, E
  paradigm_step does nothing                   -> C, D
  paradigm_step ignores the Capstone's floor   -> F
  improvisation_capstone does nothing          -> E

UNMUTATED (§0z15): the Capstone's mana-value stop is read only by E's plain
run.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
from edhmc.decks import lorehold_v17 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
LDECK, LCMD = LM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return next(c for c in LDECK if c.name == name)


def filler(n):
    return [EN.Card(name=f"F{i}", types=frozenset({"Creature"}), cost={"gen": 9},
                    power=1, toughness=1) for i in range(n)]


def thing(name, cost, priority, types=("Artifact",)):
    return EN.Card(name=name, types=frozenset(types), cost=cost,
                   priority=priority)


def lgame(library=30, **cfg):
    g = L.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard = [], []
    g.library = filler(library)
    g.treasures = 0
    g.turn = 6
    return g


def on_board(g, c):
    return any(p.card is c for p in g.board)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    seminar = card("Restoration Seminar")
    capstone = card("Improvisation Capstone")
    rock = thing("Rock", {"gen": 2}, priority=9)
    trinket = thing("Trinket", {"gen": 1}, priority=2)
    mountain = card("Mountain")

    g = lgame()
    g.graveyard = [trinket, rock]
    L.resolve_spell(g, seminar, 7)
    check("A Seminar returns the best permanent and exiles itself",
          (on_board(g, rock), on_board(g, trinket), seminar in g.graveyard,
           "Restoration Seminar" in g.paradigm),
          (True, False, False, True))

    g = lgame()
    g.graveyard = [mountain]
    may = L.pilot_may_cast(g, seminar)
    L.resolve_spell(g, seminar, 7)
    check("B a land is no target",
          (may, on_board(g, mountain), g.m["seminar_returns"]),
          (False, False, 0))

    g = lgame()
    g.graveyard = [trinket, rock]
    L.resolve_spell(g, seminar, 7)
    cast0 = g.m["spells_cast"]
    L.paradigm_step(g)
    check("C the paradigm copy is cast and returns another card",
          (g.m["spells_cast"] - cast0, on_board(g, trinket),
           seminar in g.graveyard, g.m["paradigm_copies"]),
          (1, True, False, 1))

    g = lgame()
    g.paradigm["Restoration Seminar"] = seminar
    L.paradigm_step(g)
    check("D no target: the copy is declined",
          (g.m["paradigm_copies"], g.m["paradigm_declined"]), (0, 1))

    g = lgame()
    two = thing("Two", {"gen": 2}, priority=5, types=("Sorcery",))
    three = thing("Three", {"gen": 3}, priority=6, types=("Sorcery",))
    g.library += [two, mountain, three]          # the top is the END
    L.resolve_spell(g, capstone, 7)
    check("E Capstone exiles to 5, casts both spells, loses the land",
          (g.m["capstone_exiled"], g.m["capstone_casts"],
           two in g.graveyard, three in g.graveyard,
           mountain in g.graveyard or mountain in g.library,
           capstone in g.graveyard),
          (3, 2, True, True, False, False))

    g = lgame(library=15)
    g.paradigm["Improvisation Capstone"] = capstone
    L.paradigm_step(g)
    check("F the Capstone copy is declined at 15 cards",
          (g.m["paradigm_copies"], g.m["capstone_exiled"]), (0, 0))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Restoration Seminar, Improvisation Capstone (lorehold, item 24)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_step = L.paradigm_step

    def target_with_land(g):
        pool = [c for c in g.graveyard if c.is_permanent]
        return max(pool, key=lambda c: (c.priority, c.mv), default=None)

    def step_no_floor(g):
        g.cfg = dict(g.cfg, capstone_min_library=-1)
        real_step(g)

    muts = {
        "restoration_seminar does nothing":
            ({"A", "C"}, L, "restoration_seminar", lambda g: None),
        "seminar_target falls back to a land":
            ({"B"}, L, "seminar_target", target_with_land),
        "PARADIGM is empty":
            ({"A", "C", "E"}, L, "PARADIGM", set()),
        "paradigm_step does nothing":
            ({"C", "D"}, L, "paradigm_step", lambda g: None),
        "paradigm_step ignores the Capstone's floor":
            ({"F"}, L, "paradigm_step", step_no_floor),
        "improvisation_capstone does nothing":
            ({"E"}, L, "improvisation_capstone", lambda g: None),
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
