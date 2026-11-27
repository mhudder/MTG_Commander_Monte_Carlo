#!/usr/bin/env python3
"""§0z271: the one scry rule (`engine.scry`), and Model of Unity's scry 2
(tivit, §0z207 item 13).

    python -m tests.test_unity_scry
    python -m tests.test_unity_scry --mutate   # 4 mutations, exact sets

    "Whenever players finish voting, you and each opponent who voted for a
    choice you voted for may scry 2."  (Model of Unity; Scryfall 2026-11-27)

`voting._vote_payoffs` counted `unity_scrys` and nothing read it. The scry
rule was written twice (trostani's `scry1`, shilgengar's `seer_scry`); it is
`engine.scry_bottoms` now, and `engine.scry(g, n)` applies it to the top n.

CASES (tivit unless said; the library's top is its last card)
  A  3 lands out, the top two a land and a 6-drop: the 6-drop goes to the
     bottom, the land stays on top
  B  6 lands out, the top two both lands: both go to the bottom, the card
     under them is the new top
  C  two cheap spells on top: nothing moves, the order kept
  D  Model of Unity out, a council vote: the scry 2 runs -- a cheap spell on
     top and a land under it with 6 lands out: the land goes to the bottom
  E  NEIGHBOUR: unity_scry=False -- the vote counts the scry, nothing moves
  F  shilgengar's Viscera Seer scry 1 (now `engine.scry`): a land on top
     with 5 lands out goes to the bottom, as the old method did

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  scry reads only the top card                 -> B, D
  the kept cards come back in reverse order    -> C
  Model of Unity never scries                  -> D
  lands are never bottomed                     -> B, D, F

UNMUTATED (§0z15): E is the switch's neighbour.

THE FIRST RUN (§0z11): B, D and F failed and the sets did not match --
the test's lands were built without `is_land` (a field, not read from
`types`), so no land was ever one. The helper fixed; the sets as written.
"""
import sys

import edhmc.engine as EN
import edhmc.voting as V
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(i):
    return EN.Card(name=f"Land {i}", types=frozenset({"Land"}),
                   is_land=True, produces=frozenset({"C"}))


def spell(name, mv):
    return EN.Card(name=name, types=frozenset({"Sorcery"}), cost={"gen": mv})


def game(deck, n_lands, library, extra=(), **cfg):
    board = [land(i) for i in range(n_lands)] + [B.card(deck, n)
                                                 for n in extra]
    g = B.fresh(deck, board=board, **{**EXTRA_CFG, **cfg})
    g.library = list(library)
    return g


def names(cards):
    return [c.name for c in cards]


def run_cases():
    PASS.clear()
    FAIL.clear()
    under = spell("Under", 1)

    g = game("tivit", 3, [under, land("L"), spell("Six", 6)])
    EN.scry(g, 2)
    check("A the 6-drop to the bottom, the land on top",
          (g.library[-1].name, g.library[0].name), ("Land L", "Six"))

    g = game("tivit", 6, [under, land("X"), land("Y")])
    EN.scry(g, 2)
    check("B both lands to the bottom", g.library[-1].name, "Under")

    g = game("tivit", 3, [under, spell("Two", 2), spell("One", 1)])
    EN.scry(g, 2)
    check("C nothing moves, the order kept", names(g.library),
          ["Under", "Two", "One"])

    g = game("tivit", 6, [under, land("X"), spell("One", 1)],
             extra=["Model of Unity"])
    V._vote_payoffs(g, 0)
    check("D Model of Unity: the land under the top goes to the bottom",
          (names(g.library), g.m["unity_scrys"]),
          (["Land X", "Under", "One"], 1))

    g = game("tivit", 6, [under, land("X"), spell("One", 1)],
             extra=["Model of Unity"], unity_scry=False)
    V._vote_payoffs(g, 0)
    check("E unity_scry=False: counted, nothing moves",
          (names(g.library), g.m["unity_scrys"]),
          (["Under", "Land X", "One"], 1))

    g = game("shilgengar", 5, [under, land("T")], extra=["Viscera Seer"])
    g.commander_cast = False
    g.seer_scry()
    check("F Viscera Seer: the land on top goes to the bottom",
          names(g.library), ["Land T", "Under"])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z271: the one scry rule, and Model of Unity's scry 2\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_scry, real_bottoms = EN.scry, EN.scry_bottoms

    def top_only(g, n):
        return real_scry(g, min(1, n))

    def reversed_keep(g, n):
        n = min(int(n), len(g.library))
        top = g.library[-n:] if n else []
        gone = [c for c in top if EN.scry_bottoms(g, c)]
        del g.library[len(g.library) - n:]
        g.library.extend(reversed([c for c in top
                                   if not any(c is x for x in gone)]))
        g.library[:0] = gone
        return len(gone)

    def no_lands(g, card):
        return (not card.is_land) and real_bottoms(g, card)

    def set_scry(v):
        EN.scry = v

    def set_bottoms(v):
        EN.scry_bottoms = v

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    muts = {
        "scry reads only the top card": ({"B", "D"}, set_scry, top_only,
                                         real_scry),
        "the kept cards come back reversed": ({"C"}, set_scry, reversed_keep,
                                              real_scry),
        "Model of Unity never scries": ({"D"}, set_cfg,
                                        {"unity_scry": False}, {}),
        "lands are never bottomed": ({"B", "D", "F"}, set_bottoms, no_lands,
                                     real_bottoms),
    }
    bad = 0
    for label, (want, setter, value, restore) in muts.items():
        print(f"-- {label}")
        setter(value)
        try:
            broke = run_cases()
        finally:
            setter(restore)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
