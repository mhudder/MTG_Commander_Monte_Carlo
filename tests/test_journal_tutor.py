#!/usr/bin/env python3
"""§0z272: Tamiyo's Journal's tutor (tivit, §0z207 item 10).

    python -m tests.test_journal_tutor
    python -m tests.test_journal_tutor --mutate   # 4 mutations, exact sets

    "At the beginning of your upkeep, investigate. {T}, Sacrifice three
    Clues: Search your library for a card, put that card into your hand,
    then shuffle."                    ({5}; Scryfall 2026-11-27)

`tivit.journal_tutor`, at your end step, by the policy in its docstring:
three idle Clues, the Journal untapped, not while Mechanized Production
enchants a Clue.

CASES (tivit, Tamiyo's Journal on the battlefield untapped)
  A  4 Clues: one tutor -- 1 Clue left, the Journal tapped, the library's
     best card in hand
  B  2 Clues: nothing
  C  the Journal tapped: nothing
  D  Mechanized Production enchanting a Clue, 4 Clues: nothing, no reach
  E  NEIGHBOUR: journal_tutor=False -- the reach counted, nothing done
  F  the sacrifice is a leave: Mirkwood Bats drains for the three
  G  twice in a turn, 6 Clues: one tutor (the {T})

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the Journal never taps                 -> A, G
  the three Clues are not sacrificed     -> A, F
  the Mechanized guard ignored           -> D
  the tutor takes the worst card         -> A

UNMUTATED (§0z15): B, C and E are the off sides.
"""
import sys

import edhmc.engine as EN
import edhmc.tivit as TI
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
JOURNAL = "Tamiyo's Journal"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(clues, extra=(), tapped=False, **cfg):
    board = [B.card("tivit", JOURNAL)] + [B.card("tivit", n) for n in extra]
    g = B.fresh("tivit", board=board, **{**EXTRA_CFG, **cfg})
    for k in g.tokens:
        g.tokens[k] = 0
    g.tokens["Clue"] = clues
    g.library.insert(5, EN.Card(name="Best", types=frozenset({"Sorcery"}),
                                cost={"gen": 1}, priority=50))
    j = next(p for p in g.board if p.card.name == JOURNAL)
    j.tapped = tapped
    return g, j


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, j = game(4)
    TI.journal_tutor(g)
    check("A one tutor: 1 Clue, tapped, the best card in hand",
          (g.tokens["Clue"], j.tapped, [c.name for c in g.hand]),
          (1, True, ["Best"]))

    g, j = game(2)
    check("B 2 Clues: nothing", (TI.journal_tutor(g), g.hand), (False, []))

    g, j = game(4, tapped=True)
    check("C the Journal tapped: nothing", TI.journal_tutor(g), False)

    g, j = game(4, extra=["Mechanized Production"])
    g.mech_target = "Clue"
    check("D Mechanized on a Clue: nothing, no reach",
          (TI.journal_tutor(g), g.m["journal_tutor_ready"]), (False, 0))

    g, j = game(4, journal_tutor=False)
    check("E journal_tutor=False: the reach counted, nothing",
          (TI.journal_tutor(g), g.m["journal_tutor_ready"],
           g.tokens["Clue"]), (False, 1, 4))

    g, j = game(4, extra=["Mirkwood Bats"])
    before = g.m["token_drain"]
    TI.journal_tutor(g)
    check("F the three Clues leave: Mirkwood Bats drains",
          g.m["token_drain"] > before, True)

    g, j = game(6)
    TI.journal_tutor(g)
    TI.journal_tutor(g)
    check("G twice in a turn: one tutor", g.m["journal_tutors"], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z272: Tamiyo's Journal's tutor\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_tutor, real_sac, real_jt = TI._tutor, TI.sacrifice_tokens, \
        TI.journal_tutor

    def untapping(g):
        out = real_jt(g)
        for p in g.board:
            if p.card.name == JOURNAL:
                p.tapped = False
        return out

    def no_clue_sac(g, kind, n, tapped_first=True):
        if kind == "Clue" and n == 3:
            return 0
        return real_sac(g, kind, n, tapped_first)

    def worst(g, pred):
        pool = [c for c in g.library if pred(c) and not c.is_land]
        if pool:
            w = min(pool, key=lambda c: c.priority)
            TI.remove_card(g.library, w)
            g.hand.append(w)

    def set_jt(v):
        TI.journal_tutor = v

    def set_sac(v):
        TI.sacrifice_tokens = v

    def set_tutor(v):
        TI._tutor = v

    def set_mech(v):
        TI.mech_text = v

    real_mech = TI.mech_text
    muts = {
        "the Journal never taps": ({"A", "G"}, set_jt, untapping, real_jt),
        "the three Clues are not sacrificed": ({"A", "F"}, set_sac,
                                               no_clue_sac, real_sac),
        "the Mechanized guard ignored": ({"D"}, set_mech, lambda g: False,
                                         real_mech),
        "the tutor takes the worst card": ({"A"}, set_tutor, worst,
                                           real_tutor),
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
