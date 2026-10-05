#!/usr/bin/env python3
"""Did lorehold's rows move because of the CARD swap or because of the BLANK?
(§0z108)

    python -m diagnostics.diag_blank_shift 15000 > results/blank_shift_20261005.txt

Withdrawing -Blasphemous Act +Goldspan Dragon (§0z105) moved twelve cells
of the lorehold table beyond their old bars, nine cards, all but one down --
three of them MODEL-BLIND sorceries the engine plays as dead cards. A blind
card's row is a dead card against the blank (§0z66), so it cannot move
because of what the card does. What moved is the blank: it is cast at the
list's median nonland priority (`experiment.repl_priority`, §0j), and
Goldspan (priority 8) out with the Act (priority 4) in took that median from
6 to 5 -- every row in the table is measured against a different blank.

So each moved card is blanked two ways on TODAY's list, same seeds and N as
the table:
  at 5   the table's own blank -- must REPRODUCE the committed row exactly,
         which is the check on this tool (§0z35)
  at 6   the blank the old table used
If "at 6" lands back near the old row, the move was the blank, not the card.
"""
import json
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.pending import build_pending

DECK = "lorehold"
HORIZONS = (10, 20)
CARDS = ("Apex of Power", "Arcane Bombardment", "Call Forth the Tempest",
         "Farewell", "Guttersnipe", "Improvisation Capstone",
         "Longshot, Rebel Bowman", "Restoration Seminar", "Soulfire Eruption")
OLD_COMMIT = "651817b~1"     # the table before the withdrawal's rebuild
CHUNKS = 4


def job(task):
    card, prio, lo, hi = task
    run = AB.Run(DECK, 1, HORIZONS)
    deck, cmd = build_pending(DECK)
    if card is not None:
        i = next(i for i, c in enumerate(deck) if c.name == card)
        deck = list(deck)
        deck[i] = AB.blank_like(deck[i], prio,
                                keep_types=run.blank_keeps_types)
    cols = AB.columns_all(run, deck, cmd, lo, hi)
    return task, {t: cols[t]["won"] for t in HORIZONS}


def main():
    n = int(sys.argv[1])
    parts = AB._chunks(n, CHUNKS)
    tasks = [(None, None, lo, hi) for lo, hi in parts]
    tasks += [(c, p, lo, hi) for c in CARDS for p in (5.0, 6.0)
              for lo, hi in parts]
    got = {}
    with Pool(CHUNKS) as pool:
        for task, cols in pool.imap_unordered(job, tasks, chunksize=1):
            got[task] = cols

    def col(card, prio, t):
        return np.concatenate([got[(card, prio, lo, hi)][t]
                               for lo, hi in parts])

    path = AB.Run(DECK, 15000, HORIZONS).cache   # the committed table; at 15000
    # the "at 5" column must equal it, at any other N it cannot
    new = json.load(open(path))
    old = json.loads(subprocess.check_output(
        ["git", "show", f"{OLD_COMMIT}:{path}"]))
    print(f"lorehold, N={n:,} paired, seeds 5000.., today's staged list (the "
          f"Act in). Win rate, card minus blank.\n  old    the table with "
          f"Goldspan in, blank at 6 ({OLD_COMMIT})\n  at 5   today's list, "
          f"today's blank -- must equal the committed row\n  at 6   today's "
          f"list, the OLD blank\n")
    ok_all = True
    for t in HORIZONS:
        base = col(None, None, t)
        print(f"T{t}  {'card':<26}{'old':>17}{'at 5':>17}{'at 6':>17}  "
              "reproduces")
        for c in CARDS:
            cells = []
            for p in (5.0, 6.0):
                d = base - col(c, p, t)
                cells.append((d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(n)))
            o = old[c][str(t)]["won"]
            cached = new[c][str(t)]["won"][0]
            ok = abs(cells[0][0] - cached) < 1e-12
            ok_all &= ok
            print(f"     {c:<26}"
                  f"{o[0]:>+9.4f} ±{o[1]:.4f}"
                  f"{cells[0][0]:>+9.4f} ±{cells[0][1]:.4f}"
                  f"{cells[1][0]:>+9.4f} ±{cells[1][1]:.4f}  "
                  f"{'YES' if ok else 'NO'}")
        print()
    print("every 'at 5' reproduces its committed row:",
          "YES" if ok_all else "NO -- the tool is not measuring the table")


if __name__ == "__main__":
    main()
