#!/usr/bin/env python3
"""Is a knob still READ, in effect, by the pod it runs on? (§0z205)

    python -m diagnostics.run_knob_liveness KNOB=V [KNOB=V ...] [--n=300]
                                            [--seed0=5000] [--decks=a,b]
                                            [--pods=new,old]

For each KNOB=V (V read as a Python literal) and each pod -- "new" is
`DEFAULT_CFG`, "old" is `DEFAULT_CFG` + `experiment.POD_PRE_COMBAT` (the pod
before §0z204) -- plays N staged games a deck (`build_pending`, T20, seeds
SEED0..) with the knob at V and with it unset, and counts the games whose
WHOLE output differs (every key, hashed) and the games whose RESULT differs.
A knob at 0 moved games on a pod is DEAD there at this N: perturbing it
changes nothing. That is evidence about these games, not a proof (§0z126):
a knob read one game in 2,000 passes it. Say the N, and say what V was --
a perturbation inside a threshold's dead zone reads dead too.

Why it exists: item 44's flip (§0z204) replaced the pod's combat formula
with bodies, so every knob written for the formula -- `block_share`,
`flier_block_share`, `blocker_toughness` and the rest -- may have stopped
mattering. `KNOBS.md` says where a knob is READ; only playing the games
says whether the read still reaches anything.
"""
import ast
import hashlib
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.getcwd())


def _lit(v):
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return v


def _digests(args):
    deck, pod, extra, n, seed0 = args
    from edhmc import experiment
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    lst, cmd = build_pending(deck)
    base = dict(experiment.DEFAULT_CFG, turns=20, watch=frozenset())
    if pod == "old":
        base.update(experiment.POD_PRE_COMBAT)
    base.update(extra)
    out = []
    for s in range(seed0, seed0 + n):
        r = DECKS[deck].sim(lst, cmd, dict(base), s)
        h = hashlib.sha256(json.dumps(r, sort_keys=True, default=repr)
                           .encode()).hexdigest()[:16]
        out.append((h, r.get("result")))
    return (deck, pod, json.dumps(extra, sort_keys=True)), out


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:]
                if a.startswith("--") and "=" in a)
    if not pos:
        print(__doc__)
        return 2
    knobs = [(k, _lit(v)) for k, v in (a.split("=", 1) for a in pos)]
    n = int(opts.get("--n", 300))
    seed0 = int(opts.get("--seed0", 5000))
    pods = opts.get("--pods", "new,old").split(",")
    from edhmc.registry import ACTIVE
    decks = opts["--decks"].split(",") if "--decks" in opts else list(ACTIVE)
    arms = [{}] + [{k: v} for k, v in knobs]
    jobs = [(d, p, a, n, seed0) for d in decks for p in pods for a in arms]
    with Pool() as pool:
        res = dict(pool.imap_unordered(_digests, jobs))
    py = sys.version.split()[0]
    print(f"knob liveness: N={n} staged games a deck, T20, seeds "
          f"{seed0}..{seed0 + n - 1}, decks {','.join(decks)}, python {py}")
    print("cells: games whose whole output moved / whose result moved, "
          f"of {n * len(decks)}; per-deck output moves in brackets\n")
    head = f"{'knob=value':38s}" + "".join(f" | {p + ' pod':>34s}"
                                           for p in pods)
    print(head)
    for k, v in knobs:
        key = json.dumps({k: v}, sort_keys=True)
        row = f"{(k + '=' + repr(v))[:38]:38s}"
        for p in pods:
            moved = won = 0
            per = []
            for d in decks:
                a = res[(d, p, "{}")]
                b = res[(d, p, key)]
                m = sum(x[0] != y[0] for x, y in zip(a, b))
                moved += m
                won += sum(x[1] != y[1] for x, y in zip(a, b))
                per.append(str(m))
            tag = "DEAD" if moved == 0 else "live"
            cell = f"{tag} {moved:5d} / {won:4d} [{' '.join(per)}]"
            row += f" | {cell:>34s}"
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
