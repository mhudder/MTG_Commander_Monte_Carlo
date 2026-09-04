#!/usr/bin/env python3
"""
Evaluate candidate ADDITIONS without committing to a cut.

Method: replace one existing slot with a neutral blank of the candidate's cost
(deck A), then with the candidate itself (deck B), and take the paired
difference under common random numbers. That isolates "what does this card add
over a replacement-level slot", which is directly comparable to the numbers
`ablation.py` produces for cards already in the deck.

So the cut decision is: is the candidate's score higher than the ablation score
of your weakest card? If yes, the swap is justified whatever that card is.
"""
import numpy as np

from edhmc.engine import Card, simulate as rendmaw_sim
from edhmc.lorehold import simulate as lorehold_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.decks.rendmaw_v12 import (NOXIOUS_GEARHULK, BABA_LYSAGA,
                                     EZURIS_PREDATION)
from edhmc.decks.lorehold_v16 import (GALVANOTH, RADIANT_SCROLLWIELDER,
                                      GOLDSPAN_DRAGON)

N = 6000


def blank_like(card):
    return Card(name="(blank)", types=card.types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0, priority=0.5)


def add_value(deck_name, sim, turns, cand, victim, n=N):
    deck, cmd = build_pending(deck_name)
    a = _swap_many(deck, [victim], [blank_like(cand)])
    b = _swap_many(deck, [victim], [cand])
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({cand.name}))
    ra = [sim(a, cmd, cfg, 80000 + j) for j in range(n)]
    rb = [sim(b, cmd, cfg, 80000 + j) for j in range(n)]
    out = {}
    for m in ("damage", "won"):
        x = (np.array([r[m] for r in rb], float)
             - np.array([r[m] for r in ra], float))
        out[m] = (x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)))
    out["deploy"] = np.mean([r["cast_test_card"] for r in rb])
    return out


if __name__ == "__main__":
    for label, name, sim, turns, victim, cands in (
        ("RENDMAW", "rendmaw", rendmaw_sim, 10, "Pygmy Kavu",
         (NOXIOUS_GEARHULK, BABA_LYSAGA, EZURIS_PREDATION)),
        ("LOREHOLD", "lorehold", lorehold_sim, 14, "Pinnacle Monk",
         (GALVANOTH, RADIANT_SCROLLWIELDER, GOLDSPAN_DRAGON)),
    ):
        print(f"\n{label} candidates — value over a blank of the same cost "
              f"({turns} turns)")
        print(f"  {'card':<28}{'MV':>4}{'damage':>16}{'win rate':>18}"
              f"{'P(deploy)':>11}")
        for cand in cands:
            r = add_value(name, sim, turns, cand, victim)
            print(f"  {cand.name:<28}{cand.mv:>4}"
                  f"{r['damage'][0]:>+10.2f}+-{r['damage'][1]:<5.2f}"
                  f"{r['won'][0]:>+11.4f}+-{r['won'][1]:<5.4f}"
                  f"{r['deploy']:>11.3f}")
