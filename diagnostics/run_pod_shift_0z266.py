#!/usr/bin/env python3
"""Item 53's rebuild: what §0z266's pod changed in each deck's games (§0z279).

    python -m diagnostics.run_pod_shift_0z266 1500 tivit karlov lorehold rendmaw shilgengar

Every numeric output key, the pod at the rebuild (`DEFAULT_CFG`) against
`experiment.POD_PRE_0Z266`, paired on seeds 5000.., on `build_pending()`'s
list; prints the keys whose paired difference has |z| >= 3.
"""
import sys
from multiprocessing import Pool
import numpy as np
N = int(sys.argv[1]); DECKS_ = sys.argv[2:]
def play(job):
    deck_name, seeds = job
    from edhmc.experiment import DEFAULT_CFG, POD_PRE_0Z266
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending(deck_name); sim = DECKS[deck_name].sim
    out = []
    for s in seeds:
        pair = []
        for extra in ({}, POD_PRE_0Z266):
            r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=frozenset(), **extra), 5000 + s)
            nums = {k: float(v) for k, v in r.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
            nums["won T10"] = float(r["at_rounds"][10]["won"]); nums["won T20"] = float(r["won"])
            pair.append(nums)
        out.append(pair)
    return out
if __name__ == "__main__":
    with Pool(4) as p:
        for d in DECKS_:
            chunks = [(d, range(i, N, 16)) for i in range(16)]
            rows = [x for part in p.map(play, chunks) for x in part]
            keys = sorted(set(rows[0][0]) & set(rows[0][1]))
            print(f"== {d}  N={N}  (new pod minus pre-0z266)")
            for k in keys:
                a = np.array([r[0].get(k, 0) for r in rows]); b = np.array([r[1].get(k, 0) for r in rows])
                dd = a - b
                if dd.any():
                    se = dd.std(ddof=1) / np.sqrt(len(dd))
                    z = dd.mean() / se if se else 0
                    if abs(z) >= 3:
                        print(f"  {k:40} new {a.mean():9.4f}  old {b.mean():9.4f}  diff {dd.mean():+9.4f}  z {z:+6.1f}")
            sys.stdout.flush()
