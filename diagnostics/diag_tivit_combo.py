#!/usr/bin/env python3
"""Is Academy Manufactor really what makes the Deadeye loop go infinite?

The engine is WRITTEN as though it is, and a claim built into a model is
exactly the kind of thing that has to be measured rather than assumed -- this
project has been wrong about a card's mechanism more than once, and every time
the engine was the first suspect.

THE CLAIM. Deadeye Navigator soulbound to Tivit is "{1}{U}: exile and return",
so each activation costs two mana and yields one council's dilemma. In a
four-player pod that dilemma is five votes. Under the adversarial default your
two votes buy Treasures and their three buy Clues, so:

    without Academy Manufactor   2 Treasures for 2 mana  -> break even
    with Academy Manufactor      every vote makes a Clue AND a Food AND a
                                 Treasure, so 5 Treasures for 2 mana -> the
                                 loop pays for itself and does not stop

If that is right, ablating Manufactor should collapse `combo_iterations`
CONDITIONAL ON THE LOOP BEING ASSEMBLED, and not merely reduce it.

    python diag_tivit_combo.py [--n 4000]
"""
import sys

import numpy as np

from edhmc.decks import tivit_v1
from edhmc.tivit import simulate
from edhmc.experiment import DEFAULT_CFG, _swap_many, analyse
from edhmc.engine import Card

METRICS = ("won", "damage", "artifacts_made", "treasures_made", "clues_made",
           "tivit_triggers", "deadeye_activations", "combo_iterations",
           "extra_turns", "final_treasures")


def blank(mv):
    """A do-nothing card of the same cost, the same blank ablation.py uses."""
    return Card(name="Blank", types=frozenset({"Artifact"}),
                cost={"gen": mv}, priority=0.0)


def main():
    argv = sys.argv[1:]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 4000
    deck, cmd = tivit_v1.build()

    print(f"n={n:,} paired games, T20, pod v3, opp_vote_policy=adversarial.\n")

    for turns in (20,):
        cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
        a = [simulate(deck, cmd, cfg, 5000 + i) for i in range(n)]
        deck_b = _swap_many(deck, ["Academy Manufactor"], [blank(3)])
        b = [simulate(deck_b, cmd, cfg, 5000 + i) for i in range(n)]

        print(f"=== ablating Academy Manufactor  (T{turns})")
        print(f"    {'metric':<22}{'with':>10}{'blank':>10}{'diff':>10}"
              f"   95% CI")
        for r in analyse(a, b, metrics=METRICS):
            star = " *" if r.significant else ""
            print(f"    {r.metric:<22}{r.mean_a:>10.3f}{r.mean_b:>10.3f}"
                  f"{r.mean_diff:>+10.4f}   [{r.ci_low:+.4f}, "
                  f"{r.ci_high:+.4f}]{star}")

        # THE CONDITIONAL VIEW, which is the one that answers the question.
        # Unconditionally, Manufactor and Deadeye are each drawn in a minority
        # of games, so the mean is dominated by games where the loop never
        # existed and both branches are identical.
        keep = [i for i in range(n) if a[i]["deadeye_activations"] > 0
                or b[i]["deadeye_activations"] > 0]
        print(f"\n    Restricted to the {len(keep):,} games "
              f"({len(keep)/n:.1%}) where the loop was ASSEMBLED at all:")
        for m in ("combo_iterations", "treasures_made", "artifacts_made",
                  "extra_turns", "won"):
            av = np.array([a[i][m] for i in keep], dtype=float)
            bv = np.array([b[i][m] for i in keep], dtype=float)
            print(f"      {m:<22}{av.mean():>10.3f}{bv.mean():>10.3f}"
                  f"{av.mean() - bv.mean():>+10.3f}")

        deep = [i for i in keep if max(a[i]["combo_iterations"],
                                       b[i]["combo_iterations"]) >= 10]
        print(f"\n    Games where the loop ran 10+ times: "
              f"with Manufactor {sum(1 for i in keep if a[i]['combo_iterations'] >= 10)}, "
              f"without {sum(1 for i in keep if b[i]['combo_iterations'] >= 10)}"
              f"  (union {len(deep)})")


if __name__ == "__main__":
    main()
