#!/usr/bin/env python3
"""What is colour-correct payment worth, and WHERE? (§0z8)

    python -m diagnostics.run_mana_colour [n_games]

Two questions, and the second is the one that motivated the change:

  1. WHAT IS IT WORTH on the six lists as they stand? Expected to be small.
     These decks are built with sane mana bases and a Commander game gives you
     many turns to draw into a colour, so the old rule was wrong far more
     often than it was punished.

  2. WHAT IS IT WORTH WHEN LANDS ARE SCARCE? The prediction is that this is
     where it pays: a greedy build that cuts lands for business spells spends
     more of its turns with exactly enough mana and no spare of a colour, and
     that is precisely the position in which tapping the wrong land costs you
     a whole turn. Modelled by CUTTING LANDS from each list -- 2, 4 and 6 of
     them, replaced by nothing at all, so the deck is simply shorter on mana.

`mana_colour_legacy=True` restores the pre-2026-09-11 rule (tap by count,
cheapest-to-lose first) so both legs run on one build.
"""
import importlib
import sys

import numpy as np

from edhmc.experiment import DEFAULT_CFG, analyse
from edhmc.pending import build_pending

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
TURNS = 20

DECKS = {"rendmaw": "edhmc.engine", "lorehold": "edhmc.lorehold",
         "karlov": "edhmc.karlov", "tivit": "edhmc.tivit",
         "shilgengar": "edhmc.shilgengar", "azusa": "edhmc.azusa"}


def trimmed(deck, n_cut):
    """The list with `n_cut` of its most numerous basic land removed."""
    if not n_cut:
        return list(deck)
    lands = [c for c in deck if c.is_land]
    if not lands:
        return list(deck)
    modal = max({c.name for c in lands},
                key=lambda n: sum(1 for c in lands if c.name == n))
    out, cut = [], 0
    for c in deck:
        if cut < n_cut and c.name == modal:
            cut += 1
            continue
        out.append(c)
    return out


def skewed(deck, n_skew):
    """Replace the `n_skew` most FLEXIBLE lands with the deck's modal basic.

    CUTTING LANDS TESTS THE WRONG VARIABLE, which the first run of this
    harness demonstrated by finding nothing. A deck short of lands fails to
    cast things because it is SHORT -- the colour assignment cannot help with
    that, and the failure population `can_pay` classifies as "not enough mana"
    is exactly the one this fix has no purchase on.

    Colour screw needs the opposite: ENOUGH mana of the WRONG kind. So this
    holds the mana COUNT constant and removes FLEXIBILITY, turning duals and
    any-colour lands into another copy of the commonest basic. That is what a
    greedy build actually does to itself when it trades fixing for speed, and
    it is the condition under which tapping the right land is supposed to
    start mattering.
    """
    if not n_skew:
        return list(deck)
    lands = [c for c in deck if c.is_land]
    if not lands:
        return list(deck)
    modal_name = max({c.name for c in lands},
                     key=lambda n: sum(1 for c in lands if c.name == n))
    modal = next(c for c in lands if c.name == modal_name)
    # Most flexible first; ties by name so the choice is deterministic.
    order = sorted(lands, key=lambda c: (-len(c.produces), c.name))
    victims = []
    for c in order:
        if len(victims) >= n_skew:
            break
        if c.name != modal_name and len(c.produces) > 1:
            victims.append(id(c))
    out = []
    for c in deck:
        out.append(modal if id(c) in victims else c)
    return out


def run(deck_name, modname, legacy, n, mode):
    sim = importlib.import_module(modname).simulate
    deck, cmd = build_pending(deck_name)
    deck = trimmed(deck, n) if mode == "cut" else skewed(deck, n)
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset(),
               mana_colour_legacy=legacy)
    return [sim(deck, cmd, cfg, 98000 + i) for i in range(N)]


def main():
    print(f"COLOUR-CORRECT PAYMENT — {N:,} paired games, {TURNS} turns, "
          f"same seeds")
    print("tivit is EXCLUDED FROM THE COMPARISON, not merely unaffected: it "
          "has its own\nmana_units/pay and already mapped indices back to "
          "permanents, so both legs\nrun identical code and its rows are "
          "exact zeros.\n")
    for mode, label in (
            ("cut", "LANDS CUT — tests mana QUANTITY"),
            ("skew", "FIXING REPLACED BY A BASIC — tests colour FLEXIBILITY, "
                     "mana count held constant")):
        print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
        print(f"{'deck':<12}{'n':>4}{'legacy':>9}{'fixed':>9}"
              f"{'diff':>10}{'95% CI':>22}")
        totals = {}
        for deck_name, modname in DECKS.items():
            for n in (0, 2, 4, 6):
                a = run(deck_name, modname, True, n, mode)
                b = run(deck_name, modname, False, n, mode)
                r = analyse(a, b, metrics=("won",))[0]
                totals.setdefault(n, []).append(r.mean_diff)
                mark = "  *" if r.significant else ""
                print(f"{deck_name:<12}{n:>4}{r.mean_a:>9.4f}{r.mean_b:>9.4f}"
                      f"{r.mean_diff:>+10.4f}   [{r.ci_low:+.4f}, "
                      f"{r.ci_high:+.4f}]{mark}")
            print()
        print(f"MEAN EFFECT ACROSS THE SIX DECKS ({mode}):")
        for n, diffs in sorted(totals.items()):
            print(f"  n={n}: {np.mean(diffs):+.4f}")
        print("A column that grows with n is the hypothesis confirmed.")


if __name__ == "__main__":
    main()
