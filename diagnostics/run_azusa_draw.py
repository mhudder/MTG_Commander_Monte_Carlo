#!/usr/bin/env python3
"""Two card-draw candidates for Azusa, against the STAGED list.

    python -m diagnostics.run_azusa_draw [--n=15000] [--procs=16]

THE BASELINE IS `build_pending("azusa")`, NOT the printed v1 list. The three
2026-09-10 swaps are staged, so the question "what should the deck add next"
is a question about the deck as it will be, and measuring against the old list
would score these cards alongside two cards that are on their way out. This is
the same reason `run_swaps_0904.py` passes `apply_pending=False` for the
opposite case -- the baseline has to be the list the change will actually be
made to.

THE WEAKNESS BEING ADDRESSED, stated so the result can be read against it.
The corrected table's finding is that this deck is CARD-limited and not
drop-limited: 2.77 land drops granted a turn against 1.33 used (48%), and
57.9% of turns end with an unused drop and NO land anywhere to play. The cards
that score are the ones turning drops back into cards -- Horn of Greed
+0.0419, Seer's Sundial +0.0293, Tireless Tracker +0.0281 -- and the ones
adding a fourth drop are near-blanks (Exploration +0.0079, Wayward Swordtooth
+0.0061).

    CRYPTIC CAVES   "{1}, {T}, Sacrifice this land: Draw a card. Activate
                    only if you control five or more lands."
                    A land that eats itself for a card is one-shot in most
                    decks. Here Crucible of Worlds and Ramunap Excavator are
                    already in the list and Ancient Greenwarden is staged, so
                    it comes BACK, and replaying it is a landfall trigger on a
                    drop that was going begging. It converts the deck's most
                    abundant resource into its scarcest. Cut: a Forest, of
                    which there are 21, so the swap costs almost nothing.

    KA-ZAR OF THE   "You may look at the top card of your library any time.
      SAVAGE LAND   You may play lands from the top of your library. When
                    Ka-Zar enters, create Zabu, a legendary 2/2 with landfall
                    +1/+1."
                    The FOURTH top-of-library enabler. Courser (+0.0172),
                    Augur (+0.0208) and Oracle (+0.0211) are the shape that
                    roughly doubled once land sequencing was fixed. EXPECT
                    REDUNDANCY -- `top_access()` is a boolean and three of
                    these are already in the list, which is exactly the shape
                    that made Conduit of Worlds the weak leg of the staged
                    package. Measuring it is the point.

Cut targets for Ka-Zar are the two weakest model-evaluated nonlands in
`results/ablation_azusa.txt`: Bane of Progress (-0.0041, significant and
NEGATIVE) and Perilous Forays (+0.0012, signal `--`). Ashaya is deliberately
not a candidate -- §0z.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.pending import build_pending
from edhmc.decks import azusa_v1 as M
from edhmc.azusa import simulate as az_sim
from edhmc.experiment import DEFAULT_CFG, _swap_many

BASE_SEED = 5000

LEGS = [
    ("A", [], []),
    # The four self-sacrificing draw lands, ALL IN THE SAME SLOT (a Forest),
    # so they are directly rankable against each other rather than each
    # against a different baseline.
    ("Forest->Caves",        ["Forest"],            [M.CRYPTIC_CAVES]),
    ("Forest->Horizon",      ["Forest"],            [M.HORIZON_OF_PROGRESS]),
    ("Forest->Scene",        ["Forest"],            [M.SCENE_OF_THE_CRIME]),
    ("Forest->HunterMaze",   ["Forest"],            [M.THE_HUNTER_MAZE]),
    ("Forays->KaZar",        ["Perilous Forays"],   [M.KA_ZAR]),
    ("Bane->KaZar",          ["Bane of Progress"],  [M.KA_ZAR]),
    ("BOTH (Caves+KaZar)",   ["Forest", "Perilous Forays"],
                             [M.CRYPTIC_CAVES, M.KA_ZAR]),
    # The best pair actually available: Ka-Zar taking the Bane of Progress
    # slot rather than the Perilous Forays one. Bane is the only
    # model-evaluated card in this deck with a SIGNIFICANTLY NEGATIVE win rate
    # (-0.0041), so cutting it is worth more than cutting a card that merely
    # does nothing -- which is why the same card in two different slots
    # differs by a full point of win rate.
    ("BEST (Bane->KaZar + Caves)", ["Bane of Progress", "Forest"],
                                   [M.KA_ZAR, M.CRYPTIC_CAVES]),
]

METRICS = ("won", "damage", "cards_drawn", "landfall_triggers",
           "lands_played", "lands_from_graveyard", "lands_from_library",
           "caves_cracked", "stranded_mv")

_W = {}


# The baseline is the THREE ANIMATION SWAPS ONLY, applied by hand rather than
# taken from build_pending("azusa").
#
# WHY, because this bit once: on 2026-09-10 Ka-Zar and Cryptic Caves were
# themselves staged, so build_pending() started returning a list that ALREADY
# CONTAINED THEM. Every leg below then tried to add a second copy, and the
# workers died on the singleton assertion -- with the Pool hanging rather than
# reporting, so it looked like a slow run rather than a crash. That is §0o
# exactly (candidates.py measuring a second copy of a card already in the
# deck) arriving from the other direction: not a stale hand-written list, but
# a baseline that moved underneath the harness because the harness's own
# results had been staged.
#
# The cards under review must not be in the baseline they are measured
# against, so the baseline is pinned to the three swaps that are NOT under
# review.
BASELINE_SWAPS = (["Sylvan Awakening", "Rude Awakening", "Nissa, Worldwaker"],
                  ["Ancient Greenwarden", "Greensleeves, Maro-Sorcerer",
                   "Springheart Nantuko"])


def build_leg(outs, ins):
    deck, cmd = build_pending("azusa", apply_pending=False)
    base_in = [next(v for a in dir(M) for v in [getattr(M, a)]
                    if type(v).__name__ == "Card" and v.name == n)
               for n in BASELINE_SWAPS[1]]
    deck = _swap_many(deck, BASELINE_SWAPS[0], base_in)
    if outs:
        deck = _swap_many(deck, outs, ins)
    assert len(deck) + 1 == 100, f"{len(deck) + 1} cards"
    names = [c.name for c in deck] + [cmd.name]
    basics = ("Forest", "Mountain", "Plains", "Swamp", "Island", "Wastes")
    dups = {n for n in names if n not in basics and names.count(n) > 1}
    assert not dups, f"singleton violation {dups}"
    return deck, cmd


def _init(turns):
    _W["legs"] = [(lbl, build_leg(o, i)) for lbl, o, i in LEGS]
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns)


def _one(seed):
    return [[az_sim(d, c, _W["cfg"], seed)[m] for m in METRICS]
            for _lbl, (d, c) in _W["legs"]]


def measure(turns, n, procs):
    with Pool(procs, initializer=_init, initargs=(turns,)) as pool:
        rows = pool.map(_one, range(BASE_SEED, BASE_SEED + n), chunksize=64)
    a = np.array(rows, float)
    return {lbl: a[:, i, :] for i, (lbl, _o, _i) in enumerate(LEGS)}


def ci(d):
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)

    print("Azusa card-draw candidates, measured against the STAGED list")
    print(f"N = {n:,} paired games per leg, seeds {BASE_SEED}.."
          f"{BASE_SEED + n - 1}, every leg on the same seed.")
    print("Baseline A = build_pending('azusa'): v1 with the three staged "
          "swaps applied.\n")

    iw = METRICS.index("won")
    for turns in (10, 20):
        legs = measure(turns, n, procs)
        print("=" * 78)
        print(f"T{turns}   baseline win rate {legs['A'][:, iw].mean():.4f}")
        print("=" * 78)
        print(f"  {'swap':<24}{'win rate':>22}{'damage':>16}{'cards drawn':>16}")
        for lbl, _o, _i in LEGS:
            if lbl == "A":
                continue
            d = legs[lbl] - legs["A"]
            m, hw = ci(d[:, iw])
            dm, dh = ci(d[:, METRICS.index("damage")])
            cm, ch = ci(d[:, METRICS.index("cards_drawn")])
            star = " *" if abs(m) > hw else "  "
            print(f"  {lbl:<24}{m:>+11.4f} +-{hw:<8.4f}{star}"
                  f"{dm:>+8.2f}+-{dh:<6.2f}{cm:>+8.2f}+-{ch:<6.2f}")

        got, _ = ci((legs["BOTH (Caves+KaZar)"] - legs["A"])[:, iw])
        summed = (ci((legs["Forest->Caves"] - legs["A"])[:, iw])[0]
                  + ci((legs["Forays->KaZar"] - legs["A"])[:, iw])[0])
        print(f"\n  BOTH: measured {got:+.4f} vs sum of singles {summed:+.4f}"
              f"   ({got - summed:+.4f} interaction)")

        print(f"\n  MECHANISM vs baseline (T{turns}):")
        show = ("cards_drawn", "landfall_triggers", "lands_played",
                "lands_from_graveyard", "lands_from_library", "caves_cracked",
                "stranded_mv")
        print(f"    {'metric':<22}{'Caves':>14}{'Horizon':>14}"
              f"{'Scene':>14}{'HunterMaze':>14}{'Ka-Zar':>14}{'base':>9}")
        for mname in show:
            j = METRICS.index(mname)
            cells = []
            for lbl in ("Forest->Caves", "Forest->Horizon",
                        "Forest->Scene", "Forest->HunterMaze",
                        "Forays->KaZar"):
                m, hw = ci((legs[lbl] - legs["A"])[:, j])
                cells.append(f"{m:>+7.2f}+-{hw:<5.2f}")
            print(f"    {mname:<22}" + "".join(f"{c:>14}" for c in cells)
                  + f"{legs['A'][:, j].mean():>9.2f}")
        print()
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
