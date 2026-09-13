#!/usr/bin/env python3
"""Bolas's Citadel in Karlov: -Swamp +Bolas's Citadel, and the life it spends.

The cut is a SWAMP, which is the same shape as the committed v2 change
(-Swamp +Starscape Cleric, 37 lands -> 36) and takes the list to 35. That
makes the swap a real test of the trade this card asks for: a land for an
engine that turns life into cards, in the deck that has the most life to
spend.

Run at the project's swap convention -- N=6,000 paired games, default seeds,
both horizons -- so the number is comparable to every other staged swap.

    python -m diagnostics.run_citadel
    python -m diagnostics.run_citadel --floor=20,10,5,1

THE LIFE FLOOR IS A KNOB AND IT IS THE WHOLE CARD (CLAUDE.md: "say the knob
out loud"). `citadel_life_floor` is what the Citadel is LEFT with, not what it
pays, and the sweep exists because a conservative floor would quietly assert
this is a value engine rather than the dig it actually is.
"""
import sys

from edhmc.decks.karlov_v2 import BOLASS_CITADEL
from edhmc.karlov import simulate as karlov_sim
from edhmc.pending import build_pending
from edhmc.experiment import run_ab, analyse

N = 6000
METRICS = ("won", "damage", "lifegain_triggers", "final_life", "cards_drawn",
           "stranded_mv", "citadel_casts", "citadel_life_spent",
           "citadel_lands", "combo_assembled", "turns_played",
           "cast_test_card")


def main():
    floors = [10.0]
    for a in sys.argv[1:]:
        if a.startswith("--floor="):
            floors = [float(x) for x in a.split("=")[1].split(",")]
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)

    deck, cmd = build_pending("karlov")
    for floor in floors:
        for turns in (10, 20):
            ra, rb, _ = run_ab(deck, cmd, ["Swamp"], [BOLASS_CITADEL], n=n,
                               cfg={"citadel_life_floor": floor},
                               turns=turns, sim=karlov_sim)
            res = analyse(ra, rb, metrics=METRICS)
            print(f"\n=== -Swamp +Bolas's Citadel  "
                  f"(life floor {floor:g}, {turns} turns, n={n:,} paired)")
            for r in res:
                star = " *" if r.significant else "  "
                print(f"      {r.metric:<22}{r.mean_diff:>+10.4f}"
                      f"  [{r.ci_low:>+9.4f}, {r.ci_high:>+9.4f}]{star}"
                      f"   B={r.mean_b:>9.3f}")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
