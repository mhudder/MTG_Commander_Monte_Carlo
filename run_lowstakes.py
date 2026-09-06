#!/usr/bin/env python3
"""Measure the four low-stakes oracle fixes of 2026-09-05.

Each is a CFG FLIP, not a card swap: the same deck, the same seeds, the flag
off vs on. That isolates the fix from everything else and keeps common random
numbers intact.

  attack_triggers            Grave Titan and Overlord of the Hauntwoods both
                             read "whenever this ... ENTERS OR ATTACKS" and
                             only the ETB half was modelled.
  everywhere_enters_tapped   Overlord's Everywhere token is created TAPPED;
                             the engine gave it to you untapped, a turn early.
  another_creature_clause    Suture Priest, Daxos and Elas il-Kor all read
                             "whenever ANOTHER creature you control enters"
                             and each gained a phantom life off its own
                             arrival.

All three are expected to be SMALL. The point of measuring them is to know
whether they are small, not to assume it — "correcting Karlov made the deck
look worse" is the standing reminder that a correction's sign is not
predictable from its description.

    python run_lowstakes.py [--n 6000]
"""
import sys

import numpy as np

from edhmc.engine import simulate as rendmaw_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.decks import rendmaw_v12, karlov_v2
from edhmc.experiment import DEFAULT_CFG, analyse

CASES = [
    ("rendmaw", rendmaw_v12, rendmaw_sim,
     "attack_triggers  (Grave Titan + Overlord 'or attacks')",
     {"attack_triggers": False, "everywhere_enters_tapped": False},
     {"attack_triggers": True, "everywhere_enters_tapped": False},
     ("won", "damage", "tokens_made", "attack_triggers", "rendmaw_triggers",
      "final_board_power", "cards_drawn")),
    ("rendmaw", rendmaw_v12, rendmaw_sim,
     "everywhere_enters_tapped  (Overlord's land token)",
     {"attack_triggers": True, "everywhere_enters_tapped": False},
     {"attack_triggers": True, "everywhere_enters_tapped": True},
     ("won", "damage", "tokens_made", "mana_floated", "stranded_mv",
      "cards_drawn")),
    ("karlov", karlov_v2, karlov_sim,
     "another_creature_clause  (Suture Priest / Daxos / Elas il-Kor)",
     {"another_creature_clause": False},
     {"another_creature_clause": True},
     ("won", "damage", "lifegain_triggers", "karlov_counters", "final_life",
      "cards_drawn")),
]


def main():
    argv = sys.argv[1:]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 6000

    print(f"CFG flips, {n:,} paired games each, common random numbers, "
          f"pod v3.\nA = flag OFF (the old, wrong behaviour)   "
          f"B = flag ON (oracle-correct)\n")

    for deck_name, mod, sim, label, cfg_a, cfg_b, metrics in CASES:
        deck, cmd = mod.build()
        print(f"=== {deck_name}: {label}")
        for turns in (10, 20):
            a = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **cfg_a)
            b = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **cfg_b)
            ra = [sim(deck, cmd, a, 5000 + i) for i in range(n)]
            rb = [sim(deck, cmd, b, 5000 + i) for i in range(n)]
            for r in analyse(ra, rb, metrics=metrics):
                star = " *" if r.significant else "  "
                print(f"   T{turns} {r.metric:<20}{r.mean_a:>9.3f} ->"
                      f"{r.mean_b:>9.3f}  {r.mean_diff:>+9.4f}"
                      f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
