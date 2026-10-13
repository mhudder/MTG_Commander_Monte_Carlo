#!/usr/bin/env python3
"""What each deck's answers are worth, on today's pod and on POD_V4 (§0z132).

    python -m diagnostics.run_answer_worth                 # N=2000
    python -m diagnostics.run_answer_worth --n=500 --decks=shilgengar

The owner's requirement for the retune: once kills can be delayed, a card
that delays one should be worth having. This measures it the way the tables
do -- the deck against itself with cards blanked (`tools.ablation`'s
`blank_like`, cast at the deck's median priority) -- but blanks EVERY answer
in the deck at once (`opponents.ANSWERS`, the spot answers `pod_threats`
reads), because leave-one-out is blind to redundancy (CLAUDE.md, §0z27):
one Swords in a deck with four more answers is nearly free to lose.

Each cell is keep minus blank, paired on seeds 5000.., at T10 and T20, on
the default pod and on `experiment.POD_V4`.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import ACTIVE, DECKS as REGISTRY

N = 2000
PODS = ("today", "POD_V4")


def answers_in(deck):
    from edhmc import opponents as OPP
    return [c.name for c in deck if c.name in OPP.ANSWERS
            and "wipe" not in c.tags]


def measure(args):
    deck_name, pod, blank, n = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG, POD_V4, repl_priority
    from tools.ablation import blank_like
    deck, cmd = build_pending(deck_name)
    if blank:
        pri = repl_priority(deck)
        names = set(answers_in(deck))
        deck = [blank_like(c, pri) if c.name in names else c for c in deck]
    extra = POD_V4 if pod == "POD_V4" else {}
    sim = REGISTRY[deck_name].sim
    w10, w20 = [], []
    for s in range(n):
        r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                                watch=frozenset(), **extra), 5000 + s)
        w10.append(float(r["at_rounds"][10]["won"]))
        w20.append(float(r["won"]))
    return (deck_name, pod, blank), (np.array(w10), np.array(w20))


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(ACTIVE))
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    jobs = [(d, p, b, n) for d in decks for p in PODS for b in (False, True)]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    from edhmc.pending import build_pending
    lines = [f"Every spot answer blanked together, keep minus blank, N={n} "
             f"paired, staged lists", ""]
    for d in decks:
        names = answers_in(build_pending(d)[0])
        lines.append(f"{d}: {len(names)} answers -- {', '.join(names)}")
        for p in PODS:
            cells = []
            for k, t in ((0, 10), (1, 20)):
                dd = res[(d, p, False)][k] - res[(d, p, True)][k]
                hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
                star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
                cells.append(f"T{t} {dd.mean():+.4f} ±{hw:.4f}{star}")
            lines.append(f"   {p:<7} " + "   ".join(cells))
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if out:
        open(out, "w").write(text + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
