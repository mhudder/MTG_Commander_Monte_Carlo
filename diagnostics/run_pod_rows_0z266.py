#!/usr/bin/env python3
"""Item 53's rebuild: did a mover move because of §0z266's pod? (§0z279)

    python -m diagnostics.run_pod_rows_0z266 DECK "CARD" [DECK "CARD" ...]
    python -m diagnostics.run_pod_rows_0z266 --seed0=20000 DECK "CARD"   # fresh seeds

A card's ablation row under the pod at the rebuild (`DEFAULT_CFG`) and under
`experiment.POD_PRE_0Z266`, same code, same seeds, N=15,000, T10/T20 -- and
the per-game difference of the two rows, with its own bar. On the tables'
seeds (the default, 5000..) the NEW arm must reproduce the committed cache
exactly, and the last line says whether it did. Also: how often THE CARD
ITSELF is countered (`opponents._countered`, wrapped in each worker, §0u),
and the keep-minus-drop shift of a few mechanism keys between the pods.
Run it on the interpreter that built the caches (§0z119).
"""
import json, sys
from collections import Counter
from multiprocessing import Pool
import numpy as np

N = 15000
SEED0 = 5000
KEYS = ("countered", "turns_played", "mana_spent", "cards_drawn", "damage",
        "pod_spent_body", "approach_casts", "approach_wins")
_S = {}

def _init(deck_name, card, seed0=5000):
    import tools.ablation as AB
    import edhmc.opponents as OPP
    from edhmc.experiment import POD_PRE_0Z266
    from edhmc.pending import build_pending
    run = AB.Run(deck_name, N, (10, 20))
    deck, cmd = build_pending(deck_name)
    _S.update(AB=AB, run=run, cmd=cmd, keep=deck, drop=AB.blanked(run, deck, card),
              arms={"new": {}, "old": dict(POD_PRE_0Z266)}, card=card, hits=Counter(), seed0=seed0)
    orig = OPP._countered
    def counted(g, c, i):
        r = orig(g, c, i)
        if r:
            _S["hits"][(_S["cur"], c.name == card)] += 1
        return r
    OPP._countered = counted          # installed in each worker (§0u)

def _part(args):
    arm, leg, lo, hi = args
    AB, run = _S["AB"], _S["run"]
    cfg = dict(AB.DEFAULT_CFG, turns=20, watch=frozenset(), snapshot_rounds=(10,),
               **_S["arms"][arm])
    _S["cur"] = (arm, leg); _S["hits"].clear()
    rows = [run.sim(_S[leg], _S["cmd"], cfg, _S["seed0"] + i) for i in range(lo, hi)]
    out = {"w20": np.array([r["won"] for r in rows], float),
           "w10": np.array([r["at_rounds"][10]["won"] for r in rows], float)}
    for k in KEYS:
        out[k] = np.array([float(r.get(k, 0) or 0) for r in rows])
    return args, out, dict(_S["hits"])

def main(argv):
    global SEED0
    SEED0 = next((int(a.split("=")[1]) for a in argv if a.startswith("--seed0=")), 5000)
    argv = [a for a in argv if not a.startswith("--")]
    pairs = list(zip(argv[0::2], argv[1::2]))
    for deck_name, card in pairs:
        import tools.ablation as AB
        run = AB.Run(deck_name, N, (10, 20))
        cached = json.load(open(run.cache))[card]
        parts = AB._chunks(N, 4)
        jobs = [(a, l, lo, hi) for a in ("new", "old") for l in ("keep", "drop") for lo, hi in parts]
        with Pool(4, initializer=_init, initargs=(deck_name, card, SEED0)) as p:
            res = p.map(_part, jobs)
        col = {}; hits = Counter()
        for (a, l, lo, hi), out, h in res:
            col.setdefault((a, l), []).append((lo, out))
            for k, v in h.items(): hits[k] += v
        C = {k: {m: np.concatenate([o[m] for _, o in sorted(v, key=lambda x: x[0])]) for m in v[0][1]}
             for k, v in col.items()}
        print(f"=== {deck_name} / {card}   seeds {SEED0}..{SEED0+N-1}   (python {sys.version.split()[0]}, numpy {np.__version__})")
        ok = True
        for t, m in ((10, "w10"), (20, "w20")):
            dn = C[("new", "keep")][m] - C[("new", "drop")][m]
            do = C[("old", "keep")][m] - C[("old", "drop")][m]
            ci = lambda d: 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            same = SEED0 == 5000 and float(dn.mean()) == cached[str(t)]["won"][0] and float(ci(dn)) == cached[str(t)]["won"][1]
            ok &= same
            dd = dn - do
            print(f"  T{t}: row NEW pod {dn.mean():+.4f}+-{ci(dn):.4f} ({'= cache' if same else ('CACHE MISMATCH' if SEED0 == 5000 else 'fresh seeds')})"
                  f"   row OLD pod {do.mean():+.4f}+-{ci(do):.4f}   NEW-OLD {dd.mean():+.4f}+-{ci(dd):.4f}")
        for a in ("new", "old"):
            tot = C[(a, "keep")]["countered"].mean()
            mine = hits.get(((a, "keep"), True), 0) / N
            allc = (hits.get(((a, "keep"), True), 0) + hits.get(((a, "keep"), False), 0)) / N
            print(f"  {a} pod, keep leg: countered/game {tot:.4f} (tally {allc:.4f}); THIS CARD countered/game {mine:.4f}")
        for k in KEYS:
            sn = C[("new", "keep")][k] - C[("new", "drop")][k]
            so = C[("old", "keep")][k] - C[("old", "drop")][k]
            if not (sn.any() or so.any()):
                continue
            d = sn - so
            se = d.std(ddof=1) / np.sqrt(N)
            print(f"  keep-drop {k:16} new {sn.mean():+8.4f}  old {so.mean():+8.4f}  shift {d.mean():+8.4f} (z {d.mean()/se if se else 0:+5.1f})")
        print("  reproduces cache:", "n/a (fresh seeds)" if SEED0 != 5000 else ("YES" if ok else "NO -- do not trust this card's numbers"))
        sys.stdout.flush()

if __name__ == "__main__":
    main(sys.argv[1:])
