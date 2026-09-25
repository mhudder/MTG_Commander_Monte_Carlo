#!/usr/bin/env python3
"""One path for every free cast (§0z54), and Approach's second cast (§0z55).

    python -m tests.test_free_casts_and_approach
    python -m tests.test_free_casts_and_approach --mutate   # 6 mutations

    The Dawning Archaic  (Scryfall, verified 2026-09-25)
    Whenever The Dawning Archaic attacks, you may cast target instant or
    sorcery card from your graveyard without paying its mana cost. If that
    spell would be put into your graveyard, exile it instead.

    Approach of the Second Sun  {6}{W} Sorcery
    If this spell was cast from your hand and you've cast another spell named
    Approach of the Second Sun this game, you win the game. Otherwise, put
    Approach of the Second Sun into its owner's library seventh from the top
    and you gain 7 life.

WHAT WAS WRONG. The Archaic, Invoke Calamity, Goliath's dream casts and
Galvanoth each wrote out their own subset of `resolve_spell`. A spell the
Archaic cast triggered Guttersnipe and nothing else; a spell Invoke cast from
HAND triggered nothing; Galvanoth counted `mv_cheated` twice; Scrollwielder's
card went back to the graveyard. `cast_free` is the one path now. Approach's
"otherwise" did not exist, so the card could never be cast twice.

CASES
  A1 the Archaic casts Boros Charm from the graveyard with Longshot out:
     4 from the Charm AND 6 from Longshot's cast trigger
  A2 ... and the Charm is exiled, not put back in the graveyard
  B  the Archaic does not cast a wipe off its own attack trigger
  C  Invoke Calamity casting from HAND fires Guttersnipe (4 + 6)
  D  Radiant Scrollwielder's card is exiled after it resolves
  E  a free cast counts `mv_cheated` once, at `free_mv`
  F  a Goliath dream cast goes to the graveyard afterwards
  G  Approach's first resolution: +7 life, the card SEVENTH from the top
  H  a second cast FROM HAND wins
  I  a second cast NOT from hand does not win, and returns it again
  J  a CAST copy (Bombardment) counts as a spell named Approach cast
  K  a copy PUT ON THE STACK (Double Vision) does not
  L  with fewer than seven cards in the library it goes to the bottom

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  cast_free is the old subset (effects, no triggers, no placement) -> A1, A2, C, E, F
  the Archaic's pick allows wipes                  -> B
  Approach wins on any second cast                 -> I
  Approach's "otherwise" does not return it        -> G, I, L
  a cast copy does not count as a cast             -> J
  a stack copy counts as a cast                    -> K

UNMUTATED, and written down (§0z15): D's exile is an argument at its one
call site, with no seam of its own; H is the positive case three Approach
mutations are measured against.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
from edhmc.decks import lorehold_v16 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


DECK, CMD = LM.build()


def card(name):
    return next(c for c in DECK if c.name == name)


BOROS, LONGSHOT = card("Boros Charm"), card("Longshot, Rebel Bowman")
SNIPE, ACT = card("Guttersnipe"), card("Blasphemous Act")
INVOKE = next(c for c in DECK if c.script == "invoke_calamity")
APPROACH = card("Approach of the Second Sun")
FIVE = EN.Card(name="Five Sorcery", types=frozenset({"Sorcery"}),
               cost={"gen": 5})


def filler(n):
    return [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                    cost={"gen": 1}) for i in range(n)]


def land(name, colour):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({colour}))


def game(*cards, lib=20):
    g = L.LoreholdGame(list(DECK), CMD, dict(DEFAULT_CFG), 1)
    g.board = L.Board()
    g.hand, g.graveyard, g.dream_exile = [], [], []
    g.library = filler(lib)
    g.before_draw_step = False
    g.m["approach_casts"] = 0
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def pos_from_top(g):
    """Seventh from the top is 7; None when it is not in the library."""
    if APPROACH not in g.library:
        return None
    return len(g.library) - g.library.index(APPROACH)


def approach_twice(first, second, lib=20):
    """Resolve Approach two ways in a row; return (result, where it is)."""
    g = game(lib=lib)
    first(g)
    second(g)
    return g.result, APPROACH in g.library


def from_hand(g):
    L.resolve_spell(g, APPROACH, 0, from_hand=True)


def not_from_hand(g):
    L.cast_free(g, APPROACH, exile=True)


def bombardment_copy(g):
    L.apply_spell_effects(g, APPROACH, is_copy=True)


def stack_copy(g):
    L.apply_spell_effects(g, APPROACH, is_copy=True, was_cast=False)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    g = game(LONGSHOT)
    g.graveyard = [BOROS]
    L.dawning_archaic_attack(g)
    check("A1 Archaic casts Boros Charm with Longshot out: 4 + 6",
          g.m["spell_damage"], 10.0)
    check("A2 ... and the Charm is exiled",
          (BOROS in g.graveyard, g.m["free_cast_exiled"]), (False, 1))
    g = game()
    g.graveyard = [ACT]
    L.dawning_archaic_attack(g)
    check("B the Archaic does not cast a wipe", g.m["archaic_casts"], 0)
    g = game(SNIPE)
    g.hand = [BOROS]
    L.invoke_calamity(g, self_card=INVOKE)
    check("C Invoke from hand fires Guttersnipe: 4 + 6",
          g.m["spell_damage"], 10.0)
    g = game(LM.RADIANT_SCROLLWIELDER, land("Mountain", "R"),
             land("Plains", "W"))
    g.graveyard = [BOROS]
    L.radiant_scrollwielder(g)
    check("D Scrollwielder's card is exiled after it resolves",
          (g.m["scrollwielder_casts"], BOROS in g.graveyard), (1, False))
    g = game()
    L.cast_free(g, FIVE)
    check("E a free cast counts mv_cheated once", g.m["mv_cheated"], 5.0)
    g = game()
    g.dream_exile = [FIVE]
    L.goliath_attack(g)
    check("F a Goliath dream cast goes to the graveyard",
          FIVE in g.graveyard, True)
    g = game()
    life = g.your_life
    from_hand(g)
    check("G Approach once: +7 life, seventh from the top",
          (g.your_life - life, pos_from_top(g), g.result), (7, 7, None))
    check("H a second cast from hand wins",
          approach_twice(from_hand, from_hand)[0], "win")
    check("I a second cast not from hand: no win, returned again",
          approach_twice(from_hand, not_from_hand), (None, True))
    check("J a cast copy counts as a cast",
          approach_twice(bombardment_copy, from_hand)[0], "win")
    check("K a stack copy does not",
          approach_twice(stack_copy, from_hand)[0], None)
    g = game(lib=3)
    from_hand(g)
    check("L fewer than seven cards: the bottom (4th from top of 4)",
          pos_from_top(g), 4)
    return set(FAIL)


def approach_variant(any_cast_wins=False, no_return=False,
                     copies_uncounted=False, stack_counts=False):
    """`approach_resolves` with one clause changed -- the mutation arms."""
    def fn(g, card, is_copy, was_cast, from_hand):
        prior = g.m["approach_casts"]
        counted = (was_cast or stack_counts) and not (copies_uncounted and is_copy)
        if counted:
            g.m["approach_casts"] += 1
        if not is_copy and (from_hand or any_cast_wins) and prior >= 1:
            g.result = "win"
            return
        g.your_life += 7
        if not is_copy and not no_return:
            g.library.insert(max(0, len(g.library) - 6), card)
    return fn


def main() -> int:
    if not MUTATE:
        print("Free casts through one path; Approach of the Second Sun\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(L, n) for n in
            ("cast_free", "dawning_archaic_pick", "approach_resolves")}

    def old_subset(g, c, exile=False, from_hand=False):
        L.apply_spell_effects(g, c)

    def pick_wipes_too(g):
        pool = [c for c in g.graveyard
                if "Instant" in c.types or "Sorcery" in c.types]
        return max(pool, key=lambda c: c.free_mv, default=None)

    muts = {
        "cast_free is the old subset":
            ({"A1", "A2", "C", "E", "F"}, "cast_free", old_subset),
        "the Archaic's pick allows wipes":
            ({"B"}, "dawning_archaic_pick", pick_wipes_too),
        "Approach wins on any second cast":
            ({"I"}, "approach_resolves", approach_variant(any_cast_wins=True)),
        "Approach's otherwise does not return it":
            ({"G", "I", "L"}, "approach_resolves", approach_variant(no_return=True)),
        "a cast copy does not count as a cast":
            ({"J"}, "approach_resolves", approach_variant(copies_uncounted=True)),
        "a stack copy counts as a cast":
            ({"K"}, "approach_resolves", approach_variant(stack_counts=True)),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(L, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(L, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
