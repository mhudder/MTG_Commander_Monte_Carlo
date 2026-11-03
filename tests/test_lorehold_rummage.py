#!/usr/bin/env python3
"""Pin lorehold's rummage pick (`rummage_pick`, §0z166-§0z167).

    python -m tests.test_lorehold_rummage
    python -m tests.test_lorehold_rummage --mutate   # 3 mutations, exact sets

`rummage_discard_choice` is the card both rummages give up -- Lorehold's on
each opponent's upkeep, Artist's Talent's on each noncreature spell. The
hand is the list's own cards: Arcane Bombardment (an enchantment, priority
9.2, no miracle: miracle value -1), Path to Exile (an instant of mana value
1: its miracle saves nothing, value -1 too) and Approach of the Second Sun
(mana value 7, value 5).

CASES
  A "miracle" (the default): the lowest miracle value, a tie to HAND ORDER
    -- Bombardment first, it goes; Path first, Path goes
  B "priority": Path (priority 2), wherever it sits
  C "mv": Path (mana value 1)
  D "guard": the default's pick, but never the 8.5+ Bombardment: Path
  E "guard" with only Bombardment to give up: Bombardment
  F `turn_cfg` sets the rule on its one turn: "priority" on turn 6, the
    default on turn 7
  G the land rule is every rule's: under `land_floor` (8) lands "mv" spares
    the land (mana value 0) for Path; at 8 lands the land goes
  H an unknown rule raises rather than falling through to the default

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the rule is never read (turn_knob gives the default)  -> B, C, D, F, H
  rummage_guard 0 (guard keeps only the miracles)       -> D
  land_floor 0 (lands are never spared)                 -> G

UNMUTATED (§0z15): nothing here asks whether a rule is GOOD -- that is the
forks' question (`diagnostics/run_lorehold_rummage.py forks`).
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
BOMB, PATH = CARD["Arcane Bombardment"], CARD["Path to Exile"]
APPROACH = CARD["Approach of the Second Sun"]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def land(i):
    return EN.Card(name=f"Land {i}", types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({"R"}))


def fresh(hand, lands=4, turn=6, **kw):
    cfg = dict(DEFAULT_CFG, turns=20, **{**kw, **CFG})
    g = LH.LoreholdGame(list(DECK), CMD, cfg, 1)
    g.board = EN.Board()
    for i in range(lands):
        g.board.append(EN.Permanent(card=land(i), sick=False))
    g.hand = list(hand)
    g.commander_cast = True
    g.turn = turn
    return g


def pick(hand, **kw):
    return LH.rummage_discard_choice(fresh(hand, **kw)).name


def run_cases():
    PASS.clear()
    FAIL.clear()
    check("A miracle: the lowest value, a tie to hand order",
          (pick([BOMB, PATH, APPROACH]), pick([PATH, BOMB, APPROACH])),
          ("Arcane Bombardment", "Path to Exile"))
    check("B priority: the lowest cast priority",
          pick([BOMB, PATH, APPROACH], rummage_pick="priority"),
          "Path to Exile")
    check("C mv: the lowest mana value",
          pick([BOMB, APPROACH, PATH], rummage_pick="mv"), "Path to Exile")
    check("D guard: never the 8.5+ permanent while another can go",
          pick([BOMB, PATH, APPROACH], rummage_pick="guard"),
          "Path to Exile")
    check("E guard with nothing else: it goes",
          pick([BOMB], rummage_pick="guard"), "Arcane Bombardment")
    over = {"turn_cfg": (6, {"rummage_pick": "priority"})}
    check("F turn_cfg sets the rule on its one turn",
          (pick([BOMB, PATH, APPROACH], turn=6, **over),
           pick([BOMB, PATH, APPROACH], turn=7, **over)),
          ("Path to Exile", "Arcane Bombardment"))
    check("G the land rule is every rule's",
          (pick([land(9), PATH], lands=4, rummage_pick="mv"),
           pick([land(9), PATH], lands=8, rummage_pick="mv")),
          ("Path to Exile", "Land 9"))
    try:
        pick([BOMB, PATH], rummage_pick="best")
        raised = False
    except ValueError:
        raised = True
    check("H an unknown rule raises", raised, True)
    return set(FAIL)


def main():
    if not MUTATE:
        print("lorehold rummage_pick\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_knob = LH.turn_knob

    def never_read(g, name, default):
        if name == "rummage_pick":
            return default
        return real_knob(g, name, default)

    muts = [
        ("the rule is never read", {"B", "C", "D", "F", "H"},
         ("turn_knob", never_read), {}),
        ("rummage_guard 0", {"D"}, None, {"rummage_guard": 0}),
        ("land_floor 0", {"G"}, None, {"land_floor": 0}),
    ]
    bad = 0
    for label, want, patch, cfg in muts:
        print(f"-- {label}")
        CFG.clear()
        CFG.update(cfg)
        if patch:
            setattr(LH, patch[0], patch[1])
        try:
            broke = run_cases()
        finally:
            LH.turn_knob = real_knob
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
