#!/usr/bin/env python3
"""Pin lorehold's adopted miracle policy and off-turn float (§0z168).

    python -m tests.test_lorehold_float
    python -m tests.test_lorehold_float --mutate   # 3 mutations, exact sets

ADOPTED BY THE OWNER 2026-11-03: no miracle reserve, never decline a
hardcast to wait for a miracle (§0z164), and the float the pod's windows pay
from is the board's untapped mana (§0z166). Two untapped one-mana lands, one
Treasure, Lorehold cast.

CASES
  A the float is the two lands, not three: the Treasure stays in
    `g.treasures`, so the pod's pool is 2 + 1, not 3 + 1
  B Apex of Power's unspent mana does not float (CR 106.4)
  C `float_board_only=False` restores the old float: 2 + 1 Treasure + 3 Apex
  D `reserve_for` holds nothing by default
  E `hold_for_miracle` holds nothing by default, with Library of Leng out
    and Approach of the Second Sun (miracle value 5) in hand
  F the old pilot is one knob away: `miracle_reserve` 2 holds 2, and
    `hold_min_value` 3 holds Approach

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  float_board_only False      -> A, B
  miracle_reserve 2 (cfg)     -> D
  hold_min_value 3.0 (cfg)    -> E

UNMUTATED (§0z15): C and F are the switches themselves; the pod's windows'
payment (`miracle_window`'s off-turn branch) is pinned by test_lorehold_top.
"""
import sys

import edhmc.engine as EN
import edhmc.lorehold as LH
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECK, CMD = build_pending("lorehold")
CARD = {c.name: c for c in DECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(i):
    return EN.Card(name=f"Land {i}", types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({"R"}))


def fresh(apex=0, extra=(), **kw):
    cfg = dict(DEFAULT_CFG, turns=20, **{**kw, **CFG})
    g = LH.LoreholdGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    for i in range(2):
        g.board.append(EN.Permanent(card=land(i), sick=False))
    for card in extra:
        g.board.append(EN.Permanent(card=card, sick=False))
    g.treasures, g.apex_mana, g.apex_color = 1, apex, "R"
    g.hand = []
    g.commander_cast = True
    g.turn = 6
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = fresh()
    check("A the float is the lands; the Treasure stays a Treasure",
          (LH.end_of_turn_float(g), g.treasures), (2, 1))
    check("B unspent Apex mana does not float",
          LH.end_of_turn_float(fresh(apex=3)), 2)
    check("C float_board_only=False restores the old float",
          LH.end_of_turn_float(fresh(apex=3, float_board_only=False)), 6)
    check("D no miracle reserve by default", LH.reserve_for(fresh()), 0)
    leng = CARD["Library of Leng"]
    g = fresh(extra=[leng])
    g.hand = [CARD["Approach of the Second Sun"]]
    check("E never hold for a miracle by default",
          LH.hold_for_miracle(g, g.hand[0]), False)
    g2 = fresh(extra=[leng], hold_min_value=3.0)
    g2.hand = [CARD["Approach of the Second Sun"]]
    check("F the old pilot is one knob away",
          (LH.reserve_for(fresh(miracle_reserve=2)),
           LH.hold_for_miracle(g2, g2.hand[0])), (2, True))
    return set(FAIL)


def main():
    if not MUTATE:
        print("lorehold's adopted miracle policy and float\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = [("float_board_only False", {"A", "B"}, {"float_board_only": False}),
            ("miracle_reserve 2", {"D"}, {"miracle_reserve": 2}),
            ("hold_min_value 3.0", {"E"}, {"hold_min_value": 3.0})]
    bad = 0
    for label, want, cfg in muts:
        print(f"-- {label}")
        CFG.clear()
        CFG.update(cfg)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
