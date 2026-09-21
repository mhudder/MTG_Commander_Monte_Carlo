#!/usr/bin/env python3
"""Reality Fracture batch 2: one card per remaining deck, against its cut.

PREVIEW TEXT: Reality Fracture releases 2026-10-02 and this was fetched on
2026-09-21, so every number here is a claim with a date on it.

    deck        card                        cut                 why that cut
    rendmaw     Proft, Sinister Mastermind  Ashnod's Altar      worst win-rate
                                                                MODEL-EVALUATED
                                                                row (-0.0012
                                                                ±0.0012)
    lorehold    Stingcaster Mage            Lightning Greaves   worst row
                                                                (-0.0017
                                                                ±0.0028); two
                                                                other shroud
                                                                sources remain
    tivit       Memnarch, the Warden        Tamiyo's Journal    worst row
                                                                (+0.0006
                                                                ±0.0017) --
                                                                INSIDE its bar,
                                                                so this cut is
                                                                "least
                                                                supported", not
                                                                "measured bad"
    shilgengar  Lyra, Archangel of Dawn     Vampiric Rites      -0.0014 ±0.0011,
                                                                signal `both`:
                                                                the only
                                                                genuinely
                                                                negative cut in
                                                                the batch

All four cuts classify MODEL-EVALUATED (§0z31), so none needs a
`cut_unmeasured` acknowledgement, and none is a land -- a land cut is the kind
of change this harness flatters (CLAUDE.md), and avoiding it is why three of
these four rows sit inside their own bars.

NO `ref` LEG HERE, unlike batch 1: none of these four decks has a card already
queued for the slot, so there is nothing to rank against. The swap against the
cut is the whole measurement.

§0z37 DOES NOT TOUCH THESE NUMBERS. That defect is azusa's floating landfall
mana; lorehold deducts its Treasures by index arithmetic, tivit sacrifices them
(`sacrifice_tokens`), shilgengar does `treasures -= used`, and rendmaw spends no
Treasures as mana at all. That is a grep over five engines, not an argument.

    python -m diagnostics.run_fra_batch2 > results/fra_batch2.txt
    python -m diagnostics.run_fra_batch2 --n=40      # smoke test
"""
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.experiment import run_ab, analyse

N = 15000
HORIZONS = (10, 20)
PLAN = {
    "rendmaw": ("Ashnod's Altar", "Proft, Sinister Mastermind",
                ("won", "damage", "cards_drawn", "proft_gated", "spells_cast",
                 "mana_spent", "stranded_mv")),
    "lorehold": ("Lightning Greaves", "Stingcaster Mage",
                 ("won", "damage", "cards_drawn", "stingcaster_casts",
                  "flashback_casts", "flashback_exiled", "mv_cheated",
                  "stranded_mv")),
    "tivit": ("Tamiyo's Journal", "Memnarch, the Warden",
              ("won", "damage", "cards_drawn", "memnarch_draws",
               "artifacts_made", "extra_turns", "stranded_mv")),
    "shilgengar": ("Vampiric Rites", "Lyra, Archangel of Dawn",
                   ("won", "damage", "lyra_counters", "lifegain_triggers",
                    "life_gained", "blood_made", "stranded_mv")),
}


def job(args):
    deck, turns, n = args
    cut, add, metrics = PLAN[deck]
    cards, cmd = build_pending(deck)
    assert any(c.name == cut for c in cards), f"{cut} is not in {deck}'s list"
    _mod, catalog = CATALOG[deck]
    t0 = time.time()
    ra, rb, _cfg = run_ab(cards, cmd, cut, catalog[add], n=n, turns=turns,
                          sim=REGISTRY[deck].sim)
    return (deck, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])),
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in analyse(ra, rb, metrics=metrics)])


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    jobs = [(d, t, n) for d in PLAN for t in HORIZONS]
    print(f"Reality Fracture batch 2. N={n:,} paired, same seeds both legs, "
          f"base = build_pending(<deck>).")
    for deck, (cut, add, _m) in PLAN.items():
        print(f"  {deck:<12}-{cut} +{add}")
    print()
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for deck, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(deck, turns)] = rows
            cut, add, _m = PLAN[deck]
            print(f"  {deck}  -{cut} +{add}  T{turns}  ({secs:.0f}s)   "
                  f"A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 78)
    print("SUMMARY: win rate of the real swap, paired")
    print("=" * 78)
    print(f"{'deck':<12}{'swap':<46}{'win T10':>16}{'win T20':>16}")
    for deck, (cut, add, _m) in PLAN.items():
        cells = []
        for t in HORIZONS:
            rows = done.get((deck, t))
            if rows is None:
                cells.append("     (not run)")
                continue
            _m2, diff, lo, hi, sig = rows[0]
            cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}"
                         f"{' *' if sig else '  '}")
        print(f"{deck:<12}{'-' + cut + ' +' + add:<46}"
              f"{cells[0]:>16}{cells[1]:>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
