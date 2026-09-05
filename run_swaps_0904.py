#!/usr/bin/env python3
"""Measure the four 2026-09-04 swaps as REAL swaps, not as value-over-a-blank.

`candidates.py` answers "is this card better than a replacement-level slot".
That is the right screen, but it is not the change you actually make. This
measures the specific cards in against the specific cards out, which is the
evidence `pending.py` wants.
"""
import sys

from edhmc.engine import simulate as rendmaw_sim
from edhmc.lorehold import simulate as lorehold_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.pending import build_pending
from edhmc.experiment import run_ab, analyse, POD_V2

from edhmc.decks.rendmaw_v12 import CAULDRON_OF_ESSENCE
from edhmc.decks.lorehold_v16 import SUNBIRDS_INVOCATION, GALVANOTH
from edhmc.decks.karlov_v2 import (STARSCAPE_CLERIC, ENDURING_TENACITY,
                                   EXEMPLAR_OF_LIGHT)

N = 6000

METRICS = {
    "rendmaw": ("won", "damage", "cards_drawn", "rendmaw_triggers",
                "tokens_made", "stranded_mv"),
    "lorehold": ("won", "damage", "mv_cheated", "miracles_cast",
                 "cards_drawn", "stranded_mv"),
    "karlov": ("won", "damage", "lifegain_triggers", "final_life",
               "cards_drawn", "stranded_mv"),
}

SWAPS = {
    "karlov2": ("karlov", karlov_sim,
                ["Swamp", "Whispersilk Cloak"],
                [STARSCAPE_CLERIC, ENDURING_TENACITY]),
    "karlov3": ("karlov", karlov_sim,
                ["Swamp", "Whispersilk Cloak", "Lightning Greaves"],
                [STARSCAPE_CLERIC, ENDURING_TENACITY, EXEMPLAR_OF_LIGHT]),
    "rendmaw": ("rendmaw", rendmaw_sim,
                ["Ornithopter of Paradise"], [CAULDRON_OF_ESSENCE]),
    # Does the Rendmaw swap recover if the CUT is a noncreature? Cauldron is
    # not a body; Ornithopter is a 0/2. Under pod v3 a spare blocker has value
    # the old pod priced at zero, so this isolates that.
    "rendmaw_idol": ("rendmaw", rendmaw_sim,
                     ["Idol of Oblivion"], [CAULDRON_OF_ESSENCE]),
    "rendmaw_dockside": ("rendmaw", rendmaw_sim,
                         ["Dockside Chef"], [CAULDRON_OF_ESSENCE]),
    # Queued work item 3: "cut Penance, add Galvanoth - decided, not staged."
    "penance_galvanoth": ("lorehold", lorehold_sim,
                          ["Penance"], [GALVANOTH]),
    "lorehold_scrollrack": ("lorehold", lorehold_sim,
                            ["Scroll Rack"], [SUNBIRDS_INVOCATION]),
    "lorehold_capstone": ("lorehold", lorehold_sim,
                          ["Improvisation Capstone"], [SUNBIRDS_INVOCATION]),
}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pod2 = "--pod2" in sys.argv
    extra = dict(POD_V2) if pod2 else {}
    if pod2:
        print("### POD v2: combat_targeting=open, incidental_rate=1.0, clock_shift=2")
    for key in (args or list(SWAPS)):
        deck_name, sim, outs, ins = SWAPS[key]
        # apply_pending=False: these ARE the staged changes, so they must be
        # measured against the list as it stood BEFORE they were staged.
        # Without this the cut cards are already gone and _swap_many raises.
        deck, cmd = build_pending(deck_name, apply_pending=False)
        for turns in (10, 20):
            ra, rb, cfg = run_ab(deck, cmd, outs, ins, n=N,
                                 cfg=dict(extra, turns=turns), sim=sim)
            res = analyse(ra, rb, metrics=METRICS[deck_name])
            print(f"\n=== {key}  ({turns} turns, n={N:,} paired)")
            print(f"    OUT {', '.join(outs)}")
            print(f"    IN  {', '.join(c.name for c in ins)}")
            for r in res:
                star = " *" if r.significant else "  "
                print(f"      {r.metric:<20}{r.mean_diff:>+9.4f}"
                      f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
            sys.stdout.flush()
