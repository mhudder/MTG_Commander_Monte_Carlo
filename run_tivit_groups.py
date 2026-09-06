#!/usr/bin/env python3
"""Group ablations for Tivit, plus a direct estimate of the table's noise floor.

WHY. `ablation_tivit.txt` is leave-one-out, and this project's own rule is that
leave-one-out is blind to redundancy: removing one card of an interchangeable
set understates all of them because the others cover. Karlov's three Exquisite
Blood partners scored +0.02 each and +0.0513 as a group. Tivit has at least
three sets with that shape, so the individual rows cannot be read as a ranking
without this.

THE NOISE FLOOR IS MEASURED, NOT ASSERTED. The deck runs four mana rocks that
are close to functionally identical -- Arcane, Azorius, Dimir and Orzhov Signet
-- and in the N=2000 table they scored +0.0080, +0.0050, +0.0100 and +0.0200 on
win rate. Four near-identical cards spread over 0.015 IS the noise floor, read
straight off the table, and it is larger than most of the differences anyone
would want to rank. That comparison is run here explicitly rather than left as
an observation.

    python run_tivit_groups.py [--n 4000]
"""
import sys

import numpy as np

from edhmc.decks import tivit_v1
from edhmc.engine import Card
from edhmc.experiment import DEFAULT_CFG, _swap_many, analyse
from edhmc.tivit import simulate

METRICS = ("won", "damage", "artifacts_made", "treasures_made",
           "tivit_triggers", "combo_iterations", "extra_turns")

GROUPS = {
    # "Whenever you create / whenever a token leaves, each opponent loses 1."
    # Three cards doing one job. Individually +0.0325, +0.0295, +0.0215 --
    # already the top of the table, and leave-one-out understates all three.
    "token drains": ["Mirkwood Bats", "Kambal, Profiteering Mayor",
                     "Nadier's Nightblade"],
    # The same job read off ARTIFACTS leaving rather than tokens.
    "artifact drains": ["Disciple of the Vault", "Marionette Master"],
    # All five together: the deck's actual damage plan.
    "every drain": ["Mirkwood Bats", "Kambal, Profiteering Mayor",
                    "Nadier's Nightblade", "Disciple of the Vault",
                    "Marionette Master"],
    # The vote threshold. Tivit alone is 2 votes against 3, which LOSES every
    # will-of-the-council card; one extra ties, two wins outright. So each is
    # weak alone and the pair is the thing that works -- the clearest
    # redundancy trap in the deck.
    "extra votes": ["Ballot Broker", "Brago's Representative"],
    # Six ways to re-trigger the commander. Any one covers for any other.
    "blink package": ["Ephemerate", "Soulherder", "Displacer Kitten",
                      "Teleportation Circle", "Conjurer's Closet",
                      "Deadeye Navigator"],
    # The "win with artifacts" plan. Every member scored at or below zero
    # individually; the question is whether the PACKAGE does anything.
    "alternate wins": ["Revel in Riches", "Mechanized Production",
                       "Time Sieve"],
    # Four near-identical two-mana rocks. Not a deckbuilding question -- this
    # is the NOISE FLOOR, and the answer says how much of the table is
    # rankable at all.
    "the four signets": ["Arcane Signet", "Azorius Signet", "Dimir Signet",
                         "Orzhov Signet"],
}


def blank_like(card):
    """A do-nothing card of the same mana value, matching ablation.py's blank
    for a single type line (BLANK_KEEPS_TYPES=0, the default)."""
    return Card(name=f"Blank ({card.name})",
                types=frozenset({"Artifact"}),
                cost=dict(card.cost), priority=0.0)


def main():
    argv = sys.argv[1:]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 4000
    wanted = [a for a in argv if not a.startswith("--")]
    deck, cmd = tivit_v1.build()
    by_name = {c.name: c for c in deck}

    print(f"n={n:,} paired games, common random numbers, pod v3, "
          f"opp_vote_policy=adversarial.")
    print("Each group is replaced by blanks of the SAME mana values, all at "
          "once.\n")

    for label, names in GROUPS.items():
        if wanted and label not in wanted:
            continue
        missing = [x for x in names if x not in by_name]
        if missing:
            raise SystemExit(f"{label}: not in the deck: {missing}")
        blanks = [blank_like(by_name[x]) for x in names]
        deck_b = _swap_many(deck, names, blanks)
        for turns in (10, 20):
            cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
            a = [simulate(deck, cmd, cfg, 5000 + i) for i in range(n)]
            b = [simulate(deck_b, cmd, cfg, 5000 + i) for i in range(n)]
            res = analyse(a, b, metrics=METRICS)
            if turns == 10:
                print(f"=== {label}  ({len(names)} cards: "
                      f"{', '.join(names)})")
            for r in res:
                if r.metric != "won" and turns == 10:
                    continue
                star = " *" if r.significant else "  "
                print(f"    T{turns} {r.metric:<18}{r.mean_diff:>+9.4f}"
                      f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
