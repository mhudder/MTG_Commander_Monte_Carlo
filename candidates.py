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
from edhmc.karlov import simulate as karlov_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.decks.rendmaw_v12 import (NOXIOUS_GEARHULK, BABA_LYSAGA,
                                     EZURIS_PREDATION,
                                     CAULDRON_OF_ESSENCE, REVITALIZING_REPAST,
                                     WURMCOIL_ENGINE)
from edhmc.decks.lorehold_v16 import (GALVANOTH, RADIANT_SCROLLWIELDER,
                                      GOLDSPAN_DRAGON,
                                      SUNBIRDS_INVOCATION, BRASSS_BOUNTY,
                                      UNDERWORLD_BREACH,
                                      CALDERA_PYREMAW, INVINCIBLE_HYMN,
                                      REVERSE_THE_SANDS)
from edhmc.decks.karlov_v2 import (HELIOD_SUN_CROWNED, EXEMPLAR_OF_LIGHT,
                                   GUIDE_OF_SOULS, ENDURING_TENACITY,
                                   STARSCAPE_CLERIC, THE_WIND_CRYSTAL,
                                   ENLIGHTENED_CONFIDANT, CRYPT_GHAST,
                                   DARK_CONFIDANT)

N = 6000


def blank_like(card):
    """A do-nothing replacement-level card of the same cost.

    This MUST match `ablation.py`'s blank, or the two tables are not on the same
    scale and the cut decision above is meaningless. It previously copied the
    candidate's whole type line, which silently cancelled the type line's own
    payoff: for Rendmaw an Artifact Creature blank triggers the commander, so
    Wurmcoil Engine was being scored against a blank that also made a Bird, and
    every card in `ablation_rendmaw.txt` was not. Single-type blank, same as
    ablation.py with BLANK_KEEPS_TYPES=0 — a card's type line is part of what
    it does.
    """
    if card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0, priority=0.5)


def add_value(deck_name, sim, turns, cand, victim, n=N, extra=()):
    deck, cmd = build_pending(deck_name)
    a = _swap_many(deck, [victim], [blank_like(cand)])
    b = _swap_many(deck, [victim], [cand])
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({cand.name}))
    ra = [sim(a, cmd, cfg, 80000 + j) for j in range(n)]
    rb = [sim(b, cmd, cfg, 80000 + j) for j in range(n)]
    out = {}
    for m in ("damage", "won") + tuple(extra):
        x = (np.array([r[m] for r in rb], float)
             - np.array([r[m] for r in ra], float))
        out[m] = (x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)))
    out["deploy"] = np.mean([r["cast_test_card"] for r in rb])
    return out


import sys

# The victim slot is removed in BOTH legs, so its identity does not bias the
# comparison — it only decides which 98 cards the candidate is measured
# alongside. Each is a card the ablation table scores near zero.
DECKS = {
    "rendmaw": ("RENDMAW", "rendmaw", rendmaw_sim, 10, "Pygmy Kavu",
                (CAULDRON_OF_ESSENCE, REVITALIZING_REPAST, WURMCOIL_ENGINE)),
    "lorehold": ("LOREHOLD", "lorehold", lorehold_sim, 14, "Pinnacle Monk",
                 (CALDERA_PYREMAW, GOLDSPAN_DRAGON, INVINCIBLE_HYMN,
                  REVERSE_THE_SANDS)),
    "karlov": ("KARLOV", "karlov", karlov_sim, 10, "Soulmender",
               (ENLIGHTENED_CONFIDANT, CRYPT_GHAST, DARK_CONFIDANT)),
    # 2026-09-04 first batch, kept so the runs are reproducible
    "lorehold1": ("LOREHOLD", "lorehold", lorehold_sim, 14, "Pinnacle Monk",
                  (SUNBIRDS_INVOCATION, BRASSS_BOUNTY, UNDERWORLD_BREACH)),
    "karlov1": ("KARLOV", "karlov", karlov_sim, 10, "Soulmender",
                (HELIOD_SUN_CROWNED, EXEMPLAR_OF_LIGHT, GUIDE_OF_SOULS,
                 ENDURING_TENACITY, STARSCAPE_CLERIC, THE_WIND_CRYSTAL)),
}

OLD = {
    "rendmaw": (NOXIOUS_GEARHULK, BABA_LYSAGA, EZURIS_PREDATION),
    "lorehold": (GALVANOTH, RADIANT_SCROLLWIELDER, GOLDSPAN_DRAGON),
}

if __name__ == "__main__":
    args = sys.argv[1:]
    override = next((int(a.split("=")[1]) for a in args
                     if a.startswith("--turns=")), None)
    want = [a for a in args if not a.startswith("--")] or list(DECKS)
    for label, name, sim, turns, victim, cands in (DECKS[w] for w in want):
        turns = override or turns
        print(f"\n{label} candidates — value over a blank of the same cost "
              f"({turns} turns)")
        # Lorehold's primary metric is mana cheated, not damage; the deck is
        # not built to put power on the board, so damage is the proxy there and
        # mv_cheated is the objective-adjacent number.
        extra = ("mv_cheated",) if name == "lorehold" else ()
        head = f"  {'card':<28}{'MV':>4}{'damage':>16}{'win rate':>18}"
        for e in extra:
            head += f"{e:>16}"
        print(head + f"{'P(deploy)':>11}")
        for cand in cands:
            r = add_value(name, sim, turns, cand, victim, extra=extra)
            line = (f"  {cand.name:<28}{cand.mv:>4}"
                    f"{r['damage'][0]:>+10.2f}+-{r['damage'][1]:<5.2f}"
                    f"{r['won'][0]:>+11.4f}+-{r['won'][1]:<5.4f}")
            for e in extra:
                line += f"{r[e][0]:>+10.2f}+-{r[e][1]:<5.2f}"
            print(line + f"{r['deploy']:>11.3f}")
