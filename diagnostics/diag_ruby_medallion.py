#!/usr/bin/env python3
"""Ruby Medallion in lorehold: is the miracle discount modelled, and used?

    python -m diagnostics.diag_ruby_medallion [N]

The owner, 2026-10-09: "In theory, the ruby should allow twice as many
lorehold spell activations, as it reduces the cost of red 'miracle' cards."
Lorehold's miracle is {2}; "red spells you cast cost {1} less" makes a red
one {1}, so the two mana the pilot holds back can pay for two miracles
instead of one. The engine applies the discount in `miracle_reduction`,
which every miracle decision and payment reads. This asks whether it MATTERS.

Two parts, the staged list, T20, seeds 5000.. (the tables'):

  PART 1  Ruby against the table's blank, paired, with counters added by
          wrapping `miracle_window` in each worker (§0u: a patch made in the
          parent does not reach a spawned worker): red miracles cast while
          Ruby is out, and how many of those full price could NOT have paid
          for (`ruby_enabled`). The `won` row reproduces the table's row.
  PART 2  When Ruby arrives: P(cast), the turn, removal, and how long the
          game runs after it.
"""
import sys
from multiprocessing import Pool

import numpy as np

import edhmc.lorehold as L
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.pending import build_pending
from tools.ablation import blank_like

DECK, CMD = build_pending("lorehold")
RUBY = next(c for c in DECK if c.name == "Ruby Medallion")
LEGS = {"ruby": DECK,
        "blank": _swap_many(DECK, ["Ruby Medallion"],
                            [blank_like(RUBY, repl_priority(DECK))])}
MET = ("won", "miracles_cast", "miracle_no_mana", "mv_cheated",
       "ruby_miracles", "ruby_enabled", "ruby_windows")
DEPLOY = ("cast_test_card", "test_card_turn", "test_card_removed",
          "turns_played")


def _counting_window():
    """`miracle_window`, counting what Ruby's discount bought."""
    orig = L.miracle_window

    def window(g, off_turn=False):
        avail = ((g.float_mana + g.treasures) if off_turn
                 else len(L.mana_units(g)))
        card, cast = orig(g, off_turn=off_turn)
        if g.has("Ruby Medallion"):
            g.m["ruby_windows"] += 1
            if (cast and card.cost.get("R", 0) > 0
                    and ("Instant" in card.types or "Sorcery" in card.types)):
                g.m["ruby_miracles"] += 1
                if avail < g.last_paid + 1:     # full price was unaffordable
                    g.m["ruby_enabled"] += 1
        return card, cast
    return window


def _init():
    L.miracle_window = _counting_window()


def job(s):
    out = []
    for leg in ("ruby", "blank"):
        r = L.simulate(list(LEGS[leg]), CMD, dict(DEFAULT_CFG, turns=20),
                       5000 + s)
        out.append([float(r.get(m, 0) or 0) for m in MET])
    w = L.simulate(list(DECK), CMD,
                   dict(DEFAULT_CFG, turns=20,
                        watch=frozenset({"Ruby Medallion"})), 5000 + s)
    out.append([float(w.get(m, 0) or 0) for m in DEPLOY]
               + [0.0] * (len(MET) - len(DEPLOY)))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    with Pool(4, initializer=_init) as p:
        a = np.array(p.map(job, range(n), chunksize=50))
    ruby, blank, dep = a[:, 0, :], a[:, 1, :], a[:, 2, :]
    print(f"Ruby Medallion, lorehold staged list, T20, N = {n:,} paired\n")
    print("PART 1  Ruby against the table's blank")
    for i, m in enumerate(MET):
        d = ruby[:, i] - blank[:, i]
        hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
        print(f"  {m:16} ruby {ruby[:, i].mean():8.4f}  blank "
              f"{blank[:, i].mean():8.4f}  diff {d.mean():+.4f} +-{hw:.4f}"
              f"{'*' if abs(d.mean()) > hw else ''}")
    cast = dep[:, 0] == 1
    left = dep[cast, 3] - dep[cast, 1]
    print("\nPART 2  when it arrives")
    print(f"  cast in {cast.mean():.3f} of games; median turn "
          f"{np.median(dep[cast, 1]):.0f}; removed in {dep[cast, 2].mean():.3f}"
          f" of those; {left.mean():.2f} turns of game left after the cast")


if __name__ == "__main__":
    main()
