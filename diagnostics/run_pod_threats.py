#!/usr/bin/env python3
"""Item 24, change 2: what `pod_threats` is worth to each deck, and how much
of it is the one number nobody has data for (§0z131).

    python -m diagnostics.run_pod_threats                # N=3000, default arms
    python -m diagnostics.run_pod_threats --n=1000 --decks=rendmaw,tivit
    python -m diagnostics.run_pod_threats --out=results/x.txt

Every arm is the STAGED list (`build_pending`) against itself with the pod
model switched off, seed for seed (5000 + s), so each difference is paired
and its interval honest. One T20 run reports T10 too (`snapshot_rounds`).
The arms:

    on         pod_threats=True: the routes, the answers, the hold
    naive      ... threat_hold=False: answers fire on priority (§0z42's rule:
               a model change that makes a new outcome possible is measured
               with the naive pilot as well as the rule)
    rebuild1   ... threat_rebuild_max=1: a removed piece is back next round
    rebuild5   ... threat_rebuild_max=5: the rebuild delay, swept

Reported per arm: win rate, opponents killed, the share of games lost to
an opponent's CLOCK (`loss_route` 2) and to life (1), and the mechanism
counters -- answers cast, answers that found nothing, pieces removed,
rounds the kills moved, pieces your sweepers took.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY

N = 3000
HORIZONS = (10, 20)
ARMS = {
    "on": dict(pod_threats=True),
    "naive": dict(pod_threats=True, threat_hold=False),
    "rebuild1": dict(pod_threats=True, threat_rebuild_max=1),
    "rebuild5": dict(pod_threats=True, threat_rebuild_max=5),
}
COUNTERS = ("threat_answers_cast", "threat_answers_whiffed",
            "threat_pieces_removed", "threat_rounds_delayed",
            "threat_wipe_pieces")


def row(r):
    route = r.get("loss_route", 0)
    out = {"won": float(r.get("won", 0)),
           "opponents_killed": float(r.get("opponents_killed", 0)),
           "lost_to_clock": float(route == 2),
           "lost_on_life": float(route == 1)}
    for k in COUNTERS:
        out[k] = float(r.get(k, 0))
    return out


def measure(args):
    deck, arm, extra, n = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG
    deck_list, cmd = build_pending(deck)
    sim = REGISTRY[deck].sim
    rows = {t: [] for t in HORIZONS}
    for s in range(n):
        r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=max(HORIZONS),
                                     snapshot_rounds=HORIZONS[:-1],
                                     watch=frozenset(), **extra), 5000 + s)
        for t in HORIZONS[:-1]:
            rows[t].append(row(r["at_rounds"][t]))
        rows[HORIZONS[-1]].append(row(r))
    return (deck, arm), rows


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")),
                 [d for d in REGISTRY])
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    arms = dict(off={}, **ARMS)
    jobs = [(d, a, x, n) for d in decks for a, x in arms.items()]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    lines = [f"pod_threats (item 24, change 2), STAGED lists, N={n} paired "
             f"against off, seeds 5000..{5000 + n - 1}", ""]
    keys = ["won", "opponents_killed", "lost_to_clock", "lost_on_life"]
    for d in decks:
        for t in HORIZONS:
            base = res[(d, "off")][t]
            lines.append(f"{d} T{t}   off: won {np.mean([r['won'] for r in base]):.4f}"
                         f"  lost_to_clock {np.mean([r['lost_to_clock'] for r in base]):.4f}")
            for arm in ARMS:
                cur = res[(d, arm)][t]
                cells = []
                for k in keys:
                    dd = (np.array([r[k] for r in cur])
                          - np.array([r[k] for r in base]))
                    hw = 1.96 * dd.std(ddof=1) / np.sqrt(len(dd))
                    star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
                    cells.append(f"{k} {dd.mean():+.4f} ±{hw:.4f}{star}")
                mech = "  ".join(
                    f"{k.replace('threat_', '')} "
                    f"{np.mean([r[k] for r in cur]):.2f}" for k in COUNTERS)
                lines.append(f"   {arm:<9}" + "  ".join(cells))
                lines.append(f"   {'':<9}{mech}")
            lines.append("")
    text = "\n".join(lines)
    print(text)
    if out:
        open(out, "w").write(text + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
