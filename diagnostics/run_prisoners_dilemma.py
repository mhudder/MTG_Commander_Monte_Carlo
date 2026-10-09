#!/usr/bin/env python3
"""Prisoner's Dilemma in lorehold, and the flashback rule it brought with it.

    python -m diagnostics.run_prisoners_dilemma [N] [--procs=4] [--cuts="A;B"]

Lorehold's STAGED list (`build_pending`), every leg played to T20 with a T10
snapshot (§0z93), so one run reports both horizons. Three questions:

  PART 1  FAITHLESS LOOTING'S FLASHBACK. Native flashback is new to this
          engine (2026-10-09), and the generator that reads it from Scryfall
          found that Faithless Looting -- in the list, and SCRIPTED -- has
          Flashback {2}{R} that was never cast. `native_flashback` on against
          off, on the staged list: what that gap was worth, and so how far the
          baseline every other row is measured on just moved.

  PART 2  THE CANDIDATE ROW, in Pinnacle Monk's slot against a blank of the
          card's cost, on candidates.py's seeds (80000..) -- so the `snitch`
          arm IS `python -m tools.candidates lorehold3` at T20, and is printed
          beside it as a check on this script (§0z35). The `silence` arm is
          the knob said out loud: `dilemma_choice`, the opponents' choice.

  PART 3  HEAD-TO-HEADS on the tables' seeds (5000..): the card in place of
          a MODEL-EVALUATED cut whose row is evidence. Soulfire Eruption is
          the like-for-like (a red damage sorcery, +0.0041); Enlightened Tutor
          is the lowest win-rate row in that section (-0.0025). Both choices.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import lorehold_v16 as MOD
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.lorehold import simulate as sim
from edhmc.pending import build_pending
from tools.candidates import blank_like

MET = ("won", "damage", "spell_damage", "dilemma_resolved",
       "native_flashback_casts", "test_card_flashbacks", "cast_test_card",
       "miracles_cast", "mv_cheated", "turns_played")
CARD = MOD.PRISONERS_DILEMMA
DECK, CMD = build_pending("lorehold")
VICTIM = "Pinnacle Monk"
BLANK = blank_like(CARD, repl_priority(DECK), DECK)
WATCH = frozenset({CARD.name})

# (leg, list, cfg overrides, seed base)
LEGS = [
    ("fb_off", DECK, {"native_flashback": False}, 5000),
    ("fb_on", DECK, {}, 5000),
    ("blank", _swap_many(DECK, [VICTIM], [BLANK]), {}, 80000),
    ("snitch", _swap_many(DECK, [VICTIM], [CARD]), {}, 80000),
    ("silence", _swap_many(DECK, [VICTIM], [CARD]),
     {"dilemma_choice": "silence"}, 80000),
]
# `--cuts=A;B` replaces the two cuts of the first run (2026-10-09) -- the
# second run, against Ruby Medallion, is `--cuts="Ruby Medallion"` (§0z123).
CUTS = next((tuple(a.split("=", 1)[1].split(";")) for a in sys.argv[1:]
             if a.startswith("--cuts=")),
            ("Soulfire Eruption", "Enlightened Tutor"))
for cut in CUTS:
    swapped = _swap_many(DECK, [cut], [CARD])
    LEGS.append((f"-{cut}/snitch", swapped, {}, 5000))
    LEGS.append((f"-{cut}/silence", swapped, {"dilemma_choice": "silence"},
                 5000))

COMPARE = [
    ("PART 1  Faithless Looting's flashback (on - off)", "fb_on", "fb_off"),
    ("PART 2  candidate, snitch  (vs blank, Monk's slot)", "snitch", "blank"),
    ("PART 2  candidate, silence (vs blank, Monk's slot)", "silence", "blank"),
]
for cut in CUTS:
    for ch in ("snitch", "silence"):
        COMPARE.append((f"PART 3  -{cut} +Dilemma, {ch}",
                        f"-{cut}/{ch}", "fb_on"))


def job(j):
    out = []
    for _leg, deck, over, base in LEGS:
        cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=WATCH,
                   **over)
        r = sim(list(deck), CMD, cfg, base + j)
        t10 = r["at_rounds"][10]
        out.append([[float(t10.get(m, 0) or 0) for m in MET],
                    [float(r.get(m, 0) or 0) for m in MET]])
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 15000
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    with Pool(procs) as p:
        rows = np.array(p.map(job, range(n), chunksize=50), float)
    # rows: (n, legs, horizon, metric)
    idx = {leg[0]: i for i, leg in enumerate(LEGS)}
    print(f"Prisoner's Dilemma, lorehold staged list, N = {n:,} paired games "
          f"per comparison, 95% CIs. '*' = outside its bar.\n")
    for label, b, a in COMPARE:
        print(label)
        for h, t in ((0, 10), (1, 20)):
            d = rows[:, idx[b], h, :] - rows[:, idx[a], h, :]
            cells = []
            for k, m in enumerate(MET):
                if m in ("cast_test_card",):
                    continue
                x = d[:, k]
                mu, hw = x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(n)
                w = 4 if m == "won" else 2
                cells.append(f"{m} {mu:+.{w}f}+-{hw:.{w}f}"
                             f"{'*' if abs(mu) > hw else ''}")
            print(f"  T{t}: " + "  ".join(cells[:3]))
            print(f"        " + "  ".join(cells[3:]))
        legs_b = rows[:, idx[b], 1, :]
        print(f"  P(cast) {legs_b[:, MET.index('cast_test_card')].mean():.3f}"
              f"   leg won at T20 {legs_b[:, 0].mean():.4f}\n")


if __name__ == "__main__":
    main()
