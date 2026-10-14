#!/usr/bin/env python3
"""What a re-armed clock's route should be, measured (§0z137).

    python -m diagnostics.run_rearm_rule                    # N=15000, POD_V4
    python -m diagnostics.run_rearm_rule --n=2000 --decks=rendmaw
    python -m diagnostics.run_rearm_rule --cfg=threat_clock_shift=2.5
    python -m diagnostics.run_rearm_rule --out=results/x.txt

§0z136 found that a clock which eliminates another opponent re-arms with its
pieces all out, so a fifth to a quarter of your answers land there and buy
about half as much. `opponents.rearm_rule` is the choice: "keep" (as it was),
"reland" (the route is rebuilt and lands as a fresh one does) or
"prefer_unfired" (the pilot aims at an unfired clock first). For each deck
and rule this plays the STAGED list, and the same list with every spot
answer blanked together (`run_answer_worth`'s blank, at the deck's median
priority), on `experiment.POD_V4` at T20 with a T10 snapshot, seeds 5000 + s.
It prints, paired on the seeds:

  win    each rule's win rate, and its difference from "keep"
  worth  the answers' worth under each rule (full minus blank), and its
         difference from "keep"'s worth -- the number §0z136 is about

`--cfg=k=v,...` sets knobs on every arm (`threat_clock_shift`, say).
"""
import sys
from multiprocessing import Pool

import numpy as np

from diagnostics.run_answer_worth import answers_in
from diagnostics.run_shared_code_shift import parse_cfg
from edhmc.registry import ACTIVE, DECKS as REGISTRY

N = 15000
RULES = ("keep", "reland", "prefer_unfired")


def measure(args):
    deck_name, rule, blank, n, extra = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG, POD_V4, repl_priority
    from tools.ablation import blank_like
    deck, cmd = build_pending(deck_name)
    if blank:
        pri = repl_priority(deck)
        names = set(answers_in(deck))
        deck = [blank_like(c, pri) if c.name in names else c for c in deck]
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               watch=frozenset(), **dict(POD_V4, rearm_rule=rule, **extra))
    sim = REGISTRY[deck_name].sim
    w10, w20 = np.empty(n), np.empty(n)
    for s in range(n):
        r = sim(deck, cmd, cfg, 5000 + s)
        w10[s] = float(r["at_rounds"][10]["won"])
        w20[s] = float(r["won"])
    return (deck_name, rule, blank), (w10, w20)


def cell(d, n):
    hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
    star = "*" if hw > 0 and abs(d.mean()) > hw else " "
    return f"{d.mean():+.4f} ±{hw:.4f}{star}"


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(ACTIVE))
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    extra = next((parse_cfg(a.split("=", 1)[1]) for a in args
                  if a.startswith("--cfg=")), {})
    jobs = [(d, r, b, n, extra) for d in decks for r in RULES
            for b in (False, True)]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    lines = [f"rearm_rule (§0z137): POD_V4 {extra or ''}, STAGED lists, "
             f"N={n} paired, seeds 5000..{5000 + n - 1}", "",
             "win: the rule's win rate (its difference from keep); worth: "
             "every spot answer blanked together, full minus blank (its "
             "difference from keep's worth). * = outside its 95% interval.",
             ""]
    for d in decks:
        lines.append(d)
        for r in RULES:
            for k, t in ((0, 10), (1, 20)):
                full, blank = res[(d, r, False)][k], res[(d, r, True)][k]
                kfull, kblank = res[(d, "keep", False)][k], \
                    res[(d, "keep", True)][k]
                worth = full - blank
                row = (f"   {r:<15} T{t}  win {full.mean():.4f}"
                       f"   worth {cell(worth, n)}")
                if r != "keep":
                    row += (f"   | vs keep: win {cell(full - kfull, n)}"
                            f"   worth {cell(worth - (kfull - kblank), n)}")
                lines.append(row)
        lines.append("")
    for r in RULES:
        m20 = np.mean([res[(d, r, False)][1].mean() for d in decks])
        lines.append(f"mean T20 win, {r:<15} {m20:.4f}")
    text = "\n".join(lines) + "\n"
    print(text)
    if out:
        with open(out, "w") as fh:
            fh.write(text)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
