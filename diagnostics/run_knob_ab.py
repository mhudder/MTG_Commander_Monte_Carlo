#!/usr/bin/env python3
"""One knob, ON against OFF, on one deck's staged list -- with the identity
check that says the knob moves only the games it claims to.

    python -m diagnostics.run_knob_ab DECK KNOB REACH [--n=15000] [--out=PATH]
                                      [--cfg=k=v,k=v] [--no-identity]

e.g. `python -m diagnostics.run_knob_ab azusa azusa_pool_empties
floating_mana_lost` (§0z177). Both legs are `build_pending(DECK)`, seeds
5000.. (the tables' block), T20 with T10 read off the same game; A is
`KNOB=True`, B is `KNOB=False`. It prints A minus B for win rate at both
horizons and every numeric output that moved -- the whole output, not the
table metrics (§0z32).

THE IDENTITY CHECK. `REACH` names an output counter that is nonzero in a
game exactly when the rule the knob adds did something there (for §0z177,
the floating mana it emptied; for §0z176, `extra_turns_taken`). A game where
REACH is 0 in BOTH legs must be bit-identical on every output key, and the
script prints how many are not; that number must be 0. The proof is the
rule's, not the script's: write it down beside the call (§0z177 does).

`--no-identity` says the identity is NOT claimed for this knob -- one that
changes a game without touching REACH, such as §0z177's payment order, which
taps different lands in a game that loses no mana. The count is still
printed, labelled as not claimed, and the exit status ignores it.

KNOB and REACH may each be a comma-separated list: every knob is True in A
and False in B, and a game is reached if ANY of the counters is above 0 --
for two fixes measured together (§0z178).

`--cfg=k=v,...` sets knobs on BOTH legs (values parsed as Python literals,
else kept as strings): §0z177's rule measured with the old payment order is
`--cfg=azusa_floating_first=False`.

`diagnostics/run_tivit_extra_order.py` is the same measurement for §0z176,
written first; its output is cited there and it is kept as it ran.
"""
import ast
import sys
from multiprocessing import Pool

import numpy as np


def _play(job):
    deck_name, knob, base, seeds = job
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending(deck_name)
    sim = DECKS[deck_name].sim
    out = []
    for s in seeds:
        pair = []
        for on in (True, False):
            r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20,
                                    snapshot_rounds=(10,), watch=frozenset(),
                                    **{**base, **{k: on for k in
                                                  knob.split(",")}}),
                    5000 + s)
            nums = {k: float(v) for k, v in r.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)}
            nums["won T10"] = float(r["at_rounds"][10]["won"])
            nums["won T20"] = float(r["won"])
            pair.append(nums)
        out.append(pair)
    return out


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[1:]
            if a.startswith("--") and "=" in a}
    if len(pos) != 3:
        print(__doc__)
        return 2
    deck_name, knob, reach = pos
    n = int(opts.get("--n", 15000))
    claimed = "--no-identity" not in sys.argv[1:]
    base = {}
    for kv in filter(None, opts.get("--cfg", "").split(",")):
        k, v = kv.split("=", 1)
        try:
            base[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            base[k] = v
    out_path = opts.get("--out", f"results/knob_ab_{deck_name}_{knob}.txt")
    with Pool(4) as pool:
        chunks = [(deck_name, knob, base, list(range(i, n, 16)))
                  for i in range(16)]
        pairs = [p for part in pool.map(_play, chunks) for p in part]

    py = sys.version.split()[0]
    lines = [f"{deck_name}: {knob}=True (A) minus False (B), the staged list "
             f"both legs, N={n} paired, seeds 5000..{5000 + n - 1}, today's "
             f"pod, python {py} / numpy {np.__version__}"
             + (f", both legs {base}" if base else ""), ""]
    for k in ("won T10", "won T20"):
        dd = np.array([a[k] - b[k] for a, b in pairs])
        hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
        star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
        lines.append(f"   {k}  {dd.mean():+.4f} ±{hw:.4f}{star}")

    reaches = reach.split(",")
    hit = [any(a.get(r, 0) > 0 or b.get(r, 0) > 0 for r in reaches)
           for a, b in pairs]
    none = [p for p, h in zip(pairs, hit) if not h]
    broken = sum(1 for a, b in none if a != b)
    lines += ["",
              f"   games where {reach} > 0 in either leg: {sum(hit)} of {n}"
              f" ({sum(hit) / n:.1%})",
              f"   IDENTITY: of the {len(none)} games with {reach} = 0 in "
              f"both legs, {broken} differ "
              + ("(must be 0)" if claimed
                 else "(NOT CLAIMED for this knob -- see the section citing "
                      "this file)")]
    sub = [p for p, h in zip(pairs, hit) if h]
    if len(sub) > 1:
        for k in ("won T10", "won T20"):
            dd = np.array([a[k] - b[k] for a, b in sub])
            hw = 1.96 * dd.std(ddof=1) / np.sqrt(len(sub))
            lines.append(f"   in those games, {k}  {dd.mean():+.4f} ±{hw:.4f}")

    lines += ["", "   every numeric output that moved (mean A, mean B, A - B):"]
    keys = sorted({k for a, b in pairs for k in list(a) + list(b)}
                  - {"won T10", "won T20"})
    for k in keys:
        a = np.mean([p[0].get(k, 0.0) for p in pairs])
        b = np.mean([p[1].get(k, 0.0) for p in pairs])
        if abs(a - b) > 1e-9:
            lines.append(f"   {k:<30} {a:10.4f} {b:10.4f}  {a - b:+.4f}")
    text = "\n".join(lines)
    print(text)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwrote {out_path}")
    return 1 if broken and claimed else 0


if __name__ == "__main__":
    sys.exit(main())
