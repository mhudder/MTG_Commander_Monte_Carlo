#!/usr/bin/env python3
"""Two candidates for ONE azusa slot, ranked by a paired run (§0c, §0z35).

    python -m diagnostics.run_slot_pair 15000 "Life from the Loam" \\
        "Mossborn Hydra" "Nissa, Resurgent Animist" \\
        > results/azusa_slot_loam_20261003.txt

Three lists on the same seeds (5000..): the staged list, the list with card
A in the cut's EXACT position, and the list with card B there. So each
swap's number is the real swap, and B minus A is measured directly rather
than inferred from two rows that share a baseline -- the comparison §0c
forbids and this run makes. One T20 game per list per seed, T10 read off it
(§0z93). The cards' own mechanism counters print beside the objective.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG, _swap_many
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.registry import DECKS as REGISTRY

SHARED = ("won", "damage", "landfall_triggers", "lands_played",
          "cards_drawn", "stranded_mv")
OWN = {
    "Mossborn Hydra": ("mossborn_doublings",),
    "Nissa, Resurgent Animist": ("animist_mana", "animist_cards",
                                 "animist_whiffs"),
}
CHUNKS = 4


def legs(cut, a, b):
    base, cmd = build_pending("azusa")
    assert any(c.name == cut for c in base), f"{cut!r} is not in the list"
    cat = CATALOG["azusa"][1]
    return {"base": base, "A": _swap_many(base, [cut], [cat[a]]),
            "B": _swap_many(base, [cut], [cat[b]])}, cmd


def job(task):
    cut, a, b, lo, hi = task
    decks, cmd = legs(cut, a, b)
    keys = SHARED + OWN.get(a, ()) + OWN.get(b, ())
    sim = REGISTRY["azusa"].sim
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=frozenset())
    out = {k: [] for k in decks}
    for s in range(lo, hi):
        for leg, deck in decks.items():
            r = sim(list(deck), cmd, cfg, 5000 + s)
            row = {f"{m}20": float(r.get(m, 0) or 0) for m in keys}
            row["won10"] = float(r["at_rounds"][10]["won"])
            out[leg].append(row)
    return out


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    n = int(sys.argv[1])
    cut, a, b = sys.argv[2], sys.argv[3], sys.argv[4]
    tasks = [(cut, a, b, k * n // CHUNKS, (k + 1) * n // CHUNKS)
             for k in range(CHUNKS)]
    with Pool(CHUNKS) as p:
        parts = p.map(job, tasks)
    rows = {leg: sum((part[leg] for part in parts), []) for leg in parts[0]}

    def col(leg, key):
        return np.array([r[key] for r in rows[leg]])

    print(f"azusa, ONE SLOT: {cut!r}. N={n:,} paired, seeds 5000.., base = "
          f"build_pending('azusa'), each card in the cut's exact position.\n"
          f"  A = {a}\n  B = {b}\n* = the 95% CI excludes zero.\n")
    for label, x, y in ((f"-{cut} +A (A minus base)", "base", "A"),
                        (f"-{cut} +B (B minus base)", "base", "B"),
                        ("B minus A, SAME SLOT (positive = B is better)",
                         "A", "B")):
        print(f"  {label}")
        for key in ("won10", "won20", "damage20", "landfall_triggers20",
                    "lands_played20", "cards_drawn20", "stranded_mv20"):
            m, h = ci(col(y, key) - col(x, key))
            print(f"      {key:<22}{m:+.4f} ±{h:.4f}{'*' if abs(m) > h else ''}")
    print("\n  own counters, T20, means per game:")
    for leg, card in (("A", a), ("B", b)):
        own = "  ".join(f"{k} {col(leg, k + '20').mean():.2f}"
                        for k in OWN.get(card, ()))
        print(f"      {card}: {own}")
    print(f"\n  base win rate: T10 {col('base', 'won10').mean():.4f}, "
          f"T20 {col('base', 'won20').mean():.4f}")


if __name__ == "__main__":
    main()
