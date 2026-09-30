#!/usr/bin/env python3
"""What the census's destroy shares do to indestructible (queued item 7,
§0z87).

    python -m diagnostics.run_destroy_share 15000 OUTDIR [JOB ...]
    python -m diagnostics.run_destroy_share --report OUTDIR

`opponents.destroy` prices indestructible against the pod's anonymous answers
with a DESTROY SHARE. It was a flat assumed 0.60; `tools.removal_census`
measured it from the six lists as spot 0.45, wipe 0.54 (ae takes spot). Both
are lower, so indestructible should be worth LESS than every table so far has
credited it.

Two questions, on each deck's STAGED list, N games at T10 and T20, seeds
5000..:

  1. BASELINE: how far does each deck move, split against flat? Lorehold and
     tivit hold no indestructible permanent, so they must come back
     bit-identical: that is the check that the change touches nothing else.
  2. PER CARD: what is the indestructibility itself worth, flat and split?
     The same list with the card made MORTAL (`indestructible_of` false for
     it, and Avacyn's grant switched off with it), paired. The difference of
     the two differences is how much of the card's row rested on 0.60.

     Erebos, Bleak-Hearted    rendmaw     (indestructible; a creature only at
                                           devotion five)
     Voice of the Blessed     karlov      (at ten +1/+1 counters, §0z46)
     Avacyn, Angel of Hope    shilgengar  (and every permanent you control)
     Ulamog, the Infinite Gyre azusa
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
MET = ("won", "damage", "removal_eaten", "ae_removal_eaten")
DECKS = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
CARDS = {"rendmaw": "Erebos, Bleak-Hearted", "karlov": "Voice of the Blessed",
         "shilgengar": "Avacyn, Angel of Hope",
         "azusa": "Ulamog, the Infinite Gyre"}
CFG = {"flat": {"destroy_share_split": False}, "split": {}}
# job = (deck, "live" | "mortal", "flat" | "split")
JOBS = [(d, "live", c) for d in DECKS for c in CFG] + \
       [(d, "mortal", c) for d in CARDS for c in CFG]


def key(job):
    return "_".join(job)


def run(a):
    job, turns, lo, hi = a
    deck_name, arm, cfgname = job
    import edhmc.opponents as OPP
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    if arm == "mortal":
        name = CARDS[deck_name]
        real = OPP.indestructible_of
        OPP.indestructible_of = (lambda g, p: False if p.card.name == name
                                 else real(g, p))
        OPP.GRANTS_INDESTRUCTIBLE = {n for n in OPP.GRANTS_INDESTRUCTIBLE
                                     if n != name}
    deck, cmd = build_pending(deck_name)
    cfg = dict(DEFAULT_CFG, turns=turns, **CFG[cfgname])
    return [[float(R[deck_name].sim(list(deck), cmd, cfg, 5000 + s).get(m, 0)
                   or 0) for m in MET] for s in range(lo, hi)]


def col(outdir, job, t, m="won"):
    return np.load(os.path.join(outdir, f"{key(job)}_T{t}.npy"))[:, MET.index(m)]


def cell(d):
    mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
    exact = " (bit-identical)" if not d.any() else ""
    return f"{mu:+.4f} ±{ci:.4f}{'*' if abs(mu) > ci else ' '}{exact}"


def report(outdir):
    print("1. BASELINE, split - flat (win rate, paired, 95% CI)")
    for d in DECKS:
        print(f"  {d:<11}" + "   ".join(
            f"T{t} " + cell(col(outdir, (d, 'live', 'split'), t)
                            - col(outdir, (d, 'live', 'flat'), t))
            for t in (10, 20)))
    print("\n2. INDESTRUCTIBILITY'S WORTH, live - mortal")
    for d, name in CARDS.items():
        print(f"  {name} ({d})")
        for c in CFG:
            print(f"    {c:<6}" + "   ".join(
                f"T{t} " + cell(col(outdir, (d, 'live', c), t)
                                - col(outdir, (d, 'mortal', c), t))
                for t in (10, 20)))
        print("    split - flat, of the worth" + "   ".join(
            f"  T{t} " + cell((col(outdir, (d, 'live', 'split'), t)
                               - col(outdir, (d, 'mortal', 'split'), t))
                              - (col(outdir, (d, 'live', 'flat'), t)
                                 - col(outdir, (d, 'mortal', 'flat'), t)))
            for t in (10, 20)))
        for c in CFG:
            eaten = [col(outdir, (d, 'live', c), 20, m).mean()
                     for m in ("removal_eaten", "ae_removal_eaten")]
            print(f"    T20 {c}: removal eaten {eaten[0]:.3f}, "
                  f"ae removal eaten {eaten[1]:.3f} a game")


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
        sys.exit(0)
    n, outdir = int(sys.argv[1]), sys.argv[2]
    jobs = [j for j in JOBS if not sys.argv[3:] or key(j) in sys.argv[3:]]
    os.makedirs(outdir, exist_ok=True)
    CH = 4
    tasks = [(j, t, k * n // CH, (k + 1) * n // CH)
             for j in jobs for t in (10, 20) for k in range(CH)]
    with Pool(4, maxtasksperchild=1) as p:
        res = p.map(run, tasks, chunksize=1)
    cols = {}
    for (j, t, _, _), r in zip(tasks, res):
        cols.setdefault((j, t), []).extend(r)
    for (j, t), rows in cols.items():
        np.save(os.path.join(outdir, f"{key(j)}_T{t}.npy"), np.array(rows, float))
    print("saved", len(cols), "columns to", outdir)
