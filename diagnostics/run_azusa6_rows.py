#!/usr/bin/env python3
"""The azusa6 candidate rows, run in PARALLEL (§0z101).

    python -m diagnostics.run_azusa6_rows 15000 "Card" ... >> results/...

`python -m tools.candidates azusa6` runs its nine rows one after another,
about five minutes each at N=15,000. This runs the named rows four at a time
through the SAME `candidates.add_value`, same victim slot, same seeds and the
same columns, so a row from here is a row from there. Written on 2026-10-03
when `counter_target` changed default mid-batch: the serial run had already
loaded the old default, so the rows that READ the policy (Bristly Bill,
Dancing from Dark to Dawn) were re-run here, with the rest of the batch.
"""
import sys
from multiprocessing import Pool

import tools.candidates as CA

LABEL, NAME, SIM, TURNS, VICTIM, CANDS = CA.DECKS["azusa6"]
EXTRA = ("landfall_triggers", "lands_played", "cards_drawn")


def row(a):
    name, n = a
    cand = next(c for c in CANDS if c.name == name)
    r = CA.add_value(NAME, SIM, TURNS, cand, VICTIM, n=n, extra=EXTRA)
    line = (f"  {cand.name:<28}{cand.mv:>4}"
            f"{r['damage'][0]:>+10.2f}+-{r['damage'][1]:<5.2f}"
            f"{r['won'][0]:>+11.4f}+-{r['won'][1]:<5.4f}")
    for e in EXTRA:
        line += f"{r[e][0]:>+10.2f}+-{r[e][1]:<5.2f}"
    return line + f"{r['deploy']:>11.3f}"


def main():
    n = int(sys.argv[1])
    names = sys.argv[2:] or [c.name for c in CANDS]
    with Pool(4) as p:
        for line in p.map(row, [(nm, n) for nm in names], chunksize=1):
            print(line, flush=True)


if __name__ == "__main__":
    main()
