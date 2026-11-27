#!/usr/bin/env python3
"""§0z274: Havengul Laboratory's transform and Havengul Mystery (tivit,
§0z207 item 11).

    python -m tests.test_havengul_mystery
    python -m tests.test_havengul_mystery --mutate   # 5 mutations, exact

    Havengul Laboratory: "{T}: Add {C}. {4}, {T}: Investigate. At the
    beginning of your end step, if you sacrificed three or more Clues this
    turn, transform Havengul Laboratory."
    Havengul Mystery: "When this land transforms into Havengul Mystery,
    return target creature card from your graveyard to the battlefield.
    When the creature put onto the battlefield with Havengul Mystery leaves
    the battlefield, transform Havengul Mystery. {T}, Pay 1 life: Add {B}."
                                                    (Scryfall 2026-11-27)

CASES (tivit, the Laboratory on the battlefield)
  A  three Clues sacrificed this turn: at the end step it transforms and
     the graveyard's best creature card comes back
  B  two Clues sacrificed: nothing
  C  the Mystery taps for {B} and costs 1 life
  D  the returned creature dies: it transforms back, {C} again
  E  NEIGHBOUR: havengul_transform=False -- the reach counted, nothing
  F  the Journal's three Clues, sacrificed IN the end step, do not count:
     the condition is read as the step begins
  G  no creature card in the graveyard: it transforms, returns nothing
  H  the Mystery has no investigate

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the condition read after the step's own sacrifices   -> F
  the Mystery's {B} costs no life                      -> C
  it never transforms back                             -> D
  the target is the worst creature card                -> A
  the Mystery taps for {C}                             -> C

UNMUTATED (§0z15): B and E are the off sides; G and H hold under all.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as TI
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
LAB = "Havengul Laboratory // Havengul Mystery"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def creature(name, prio):
    return EN.Card(name=name, types=frozenset({"Creature"}), cost={"gen": 2},
                   power=2, toughness=2, priority=prio)


def game(sacrificed, grave=("Best", "Worst"), extra=(), **cfg):
    board = [B.card("tivit", LAB)] + [B.card("tivit", n) for n in extra]
    g = B.fresh("tivit", board=board, **{**EXTRA_CFG, **cfg})
    for k in g.tokens:
        g.tokens[k] = 0
    g.graveyard = [creature(n, 9 if n == "Best" else 1) for n in grave]
    g.clues_sacrificed_turn = sacrificed
    g.havengul_mystery = g.havengul_creature = None
    lab = next(p for p in g.board if p.card.name == LAB)
    return g, lab


def names(perms):
    return sorted(p.card.name for p in perms)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, lab = game(3)
    TI.end_step(g)
    check("A three sacrificed: it transforms, the best comes back",
          (TI.havengul_sync(g) is lab, g.havengul_creature.card.name,
           [c.name for c in g.graveyard]), (True, "Best", ["Worst"]))

    g, lab = game(2)
    TI.end_step(g)
    check("B two sacrificed: nothing", TI.havengul_sync(g), None)

    g, lab = game(3)
    TI.end_step(g)
    lab.tapped = False
    paid = TI.pay(g, {"B": 1})
    check("C the Mystery's {B}: tapped, 1 life",
          (paid, lab.tapped, g.your_life), (True, True, 39.0))

    g, lab = game(3)
    TI.end_step(g)
    OPP.destroy(g, g.havengul_creature, destroys=True)
    lab.tapped = False
    check("D the creature dies: it transforms back, {C}",
          (TI.havengul_sync(g), frozenset({"C"}) in TI.mana_units(g)),
          (None, True))

    g, lab = game(3, havengul_transform=False)
    TI.end_step(g)
    check("E havengul_transform=False: the reach counted, nothing",
          (TI.havengul_sync(g), g.m["havengul_transform_due"]), (None, 1))

    g, lab = game(0, extra=["Tamiyo's Journal"])
    g.tokens["Clue"] = 3
    TI.end_step(g)
    check("F the Journal's Clues in the end step do not count",
          (g.m["journal_tutors"], TI.havengul_sync(g)), (1, None))

    g, lab = game(3, grave=())
    TI.end_step(g)
    check("G no creature card: it transforms, returns nothing",
          (TI.havengul_sync(g) is lab, g.havengul_creature), (True, None))

    g, lab = game(3, grave=())
    TI.end_step(g)
    lab.tapped = False
    g.tokens["Treasure"] = 6
    TI.havengul_end_step(g, False)
    check("H the Mystery has no investigate", g.m["havengul_clues"], 0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z274: Havengul Laboratory // Havengul Mystery\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(TI, n) for n in ("havengul_end_step", "pay",
                                        "havengul_sync", "havengul_transform",
                                        "MYSTERY_MANA")}

    def read_late(g, due=False):
        return real["havengul_end_step"](g, g.clues_sacrificed_turn >= 3)

    def free_b(g, cost, powerstones=False):
        life = g.your_life
        out = real["pay"](g, cost, powerstones)
        g.your_life = life
        return out

    def never_back(g):
        m = g.havengul_mystery
        if m is None or not TI.on_board(g, m):
            return None
        return m

    def worst(g, lab):
        pool = [c for c in g.graveyard if c.is_creature]
        for c in pool:
            c.priority = -c.priority
        try:
            real["havengul_transform"](g, lab)
        finally:
            for c in pool:
                c.priority = -c.priority

    muts = {
        "the condition read after the step's own sacrifices": (
            {"F"}, "havengul_end_step", read_late),
        "the Mystery's {B} costs no life": ({"C"}, "pay", free_b),
        "it never transforms back": ({"D"}, "havengul_sync", never_back),
        "the target is the worst creature card": (
            {"A"}, "havengul_transform", worst),
        "the Mystery taps for {C}": ({"C"}, "MYSTERY_MANA",
                                     frozenset({"C"})),
    }
    bad = 0
    for label, (want, name, value) in muts.items():
        print(f"-- {label}")
        setattr(TI, name, value)
        try:
            broke = run_cases()
        finally:
            setattr(TI, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
