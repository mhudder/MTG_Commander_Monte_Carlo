#!/usr/bin/env python3
"""Azusa batch 6: seven landfall payoffs, each as the REAL SWAP against
Wayward Swordtooth (§0z101).

    python -m diagnostics.run_azusa_batch6 15000 > results/azusa_batch6_h2h.txt
    python -m diagnostics.run_azusa_batch6 15000 --cut="Life from the Loam" \
        --cards="Mossborn Hydra"        # any cut, any subset of CARDS

THE QUESTION is §0z100's. The landfall group's returns diminish by about 0.8
a copy, and the curve's extrapolated fifth copy is +0.029 at T20 for an
AVERAGE member. Is a further payoff still worth a slot -- and which?

THE CUT IS THE OWNER'S (2026-10-03): Wayward Swordtooth, a MODEL-EVALUATED
row (+0.0032 +-0.0030 at T20) whose job -- an extra land drop -- §0z99 found
the deck does not lack: Exploration + Swordtooth together are +0.0065 against
+0.0571 for the three cards that play lands from the top. Every swap below
cuts the same card, so the seven rows share a baseline and §0c forbids
ranking them against each other by their bars; they are seven decisions, each
against the same named cut.

ONE RUN PER SWAP, BOTH HORIZONS: each game is played to 20 rounds and its
round-10 output is read off the same game (`snapshot_rounds`, §0z93), which
is exact. Base list is `build_pending("azusa")`, seeds 5000.. (the tables').
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import run_ab
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

CUT = "Wayward Swordtooth"
CARDS = ("Elfsworn Giant", "Chocobo Racetrack", "Dancing from Dark to Dawn",
         "Mole Man, Moloid Master", "Mossborn Hydra",
         "Bristly Bill, Spine Sower", "Glacier Godmaw")
# Each card's own mechanism counters, read on the B leg at T20 -- the check
# that a number traces to the card's text (CLAUDE.md, "MECHANISM COUNTERS").
OWN = {
    "Elfsworn Giant": ("elfsworn_tokens",),
    "Chocobo Racetrack": ("racetrack_birds", "racetrack_pumps"),
    "Dancing from Dark to Dawn": ("dancing_bears", "dancing_counters"),
    "Mole Man, Moloid Master": ("moloids_made", "moloid_mills",
                                "lands_from_graveyard"),
    "Mossborn Hydra": ("mossborn_doublings",),
    "Bristly Bill, Spine Sower": ("bristly_counters", "bristly_activations"),
    "Glacier Godmaw": ("godmaw_pumps", "godmaw_hasted", "landers_cracked"),
}
SHARED = ("damage", "landfall_triggers", "lands_played", "cards_drawn",
          "final_life")
CHUNKS = 4
SEED0 = 5000


def job(a):
    add, lo, hi, cut = a
    base, cmd = build_pending("azusa")
    assert any(c.name == cut for c in base), f"{cut!r} is not in the list"
    card = CATALOG["azusa"][1][add]
    ra, rb, _ = run_ab(base, cmd, cut, card, n=hi - lo,
                       cfg={"snapshot_rounds": (10,)}, base_seed=SEED0 + lo,
                       turns=20, sim=REGISTRY["azusa"].sim)
    keys = SHARED + OWN[add]
    out = []
    for x, y in zip(ra, rb):
        out.append((float(x["at_rounds"][10]["won"]),
                    float(y["at_rounds"][10]["won"]),
                    float(x["won"]), float(y["won"]),
                    float(y["cast_test_card"]),
                    tuple(float(y[k]) - float(x[k]) for k in SHARED),
                    tuple(float(y[k]) for k in OWN[add])))
    return out


def ci(d):
    d = np.asarray(d, dtype=float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    opt = dict(a[2:].split("=", 1) for a in sys.argv[2:] if a.startswith("--"))
    cut = opt.get("cut", CUT)
    cards = tuple(opt["cards"].split(",")) if "cards" in opt else CARDS
    assert set(cards) <= set(CARDS), "only batch-6 cards have OWN counters"
    tasks = [(c, k * n // CHUNKS, (k + 1) * n // CHUNKS, cut)
             for c in cards for k in range(CHUNKS)]
    with Pool(4) as p:
        res = p.map(job, tasks, chunksize=1)
    rows = {}
    for (c, _lo, _hi, _cut), r in zip(tasks, res):
        rows.setdefault(c, []).extend(r)

    print(f"azusa batch 6: -{cut} +X, the real swap. N={n:,} paired per "
          f"card, seeds {SEED0}.., base = build_pending('azusa'), one T20 run "
          "per swap with T10 read off the same game (§0z93).\n"
          "POSITIVE = the swap gains. * = the 95% CI excludes zero.\n")
    print(f"  {'card':<28}{'win T10':>18}{'win T20':>18}"
          f"{'damage T20':>16}{'P(cast)':>9}")
    for c in cards:
        r = rows[c]
        cells = []
        for ia, ib in ((0, 1), (2, 3)):
            m, h = ci([x[ib] - x[ia] for x in r])
            cells.append(f"{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ' '}")
        dm, dh = ci([x[5][0] for x in r])
        pc = np.mean([x[4] for x in r])
        print(f"  {c:<28}{cells[0]:>18}{cells[1]:>18}"
              f"{dm:>+9.2f} ±{dh:<5.2f}{pc:>9.3f}")
    print("\nmechanism, T20 (B minus A for the shared counters; the card's own "
          "counters are B-leg means per game):")
    for c in cards:
        r = rows[c]
        parts = []
        for i, k in enumerate(SHARED[1:], start=1):
            m, h = ci([x[5][i] for x in r])
            parts.append(f"{k} {m:+.2f}±{h:.2f}")
        own = [f"{k} {np.mean([x[6][i] for x in r]):.2f}"
               for i, k in enumerate(OWN[c])]
        print(f"  {c}\n      " + "  ".join(parts) + "\n      own: "
              + "  ".join(own))


if __name__ == "__main__":
    main()
