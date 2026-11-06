#!/usr/bin/env python3
"""§0z176: tivit's extra turns BEFORE the pod's round (CR 500.7), against the
old order, where the pod acted between your turn and the turns it bought.

    python -m diagnostics.run_tivit_extra_order [--n=15000] [--out=PATH]

The staged tivit list on both legs, `extra_turns_before_pod` True (A) against
False (B), seeds 5000.. (the tables' block), T20 with T10 read off the same
game. Prints A minus B for win rate at both horizons and every numeric output
that moved -- the whole output, not the table metrics (§0z32).

THE IDENTITY CHECK. The two orders differ only in a round where an extra turn
is taken, so a seed on which NEITHER leg ever takes one must play
bit-identically. The script counts the seeds where that fails, and the number
it must print is 0; anything else means the knob moves something other than
the order it names.
"""
import sys
from multiprocessing import Pool

import numpy as np

KEY = "extra_turns_before_pod"


def _play(seeds):
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending("tivit")
    sim = DECKS["tivit"].sim
    out = []
    for s in seeds:
        pair = []
        for on in (True, False):
            r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20,
                                    snapshot_rounds=(10,), watch=frozenset(),
                                    **{KEY: on}), 5000 + s)
            nums = {k: float(v) for k, v in r.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)}
            nums["won T10"] = float(r["at_rounds"][10]["won"])
            nums["won T20"] = float(r["won"])
            pair.append(nums)
        out.append(pair)
    return out


def main():
    opts = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[1:]
            if a.startswith("--") and "=" in a}
    n = int(opts.get("--n", 15000))
    out_path = opts.get("--out", "results/tivit_extra_order_20261106.txt")
    with Pool(4) as pool:
        chunks = [list(range(i, n, 16)) for i in range(16)]
        pairs = [p for part in pool.map(_play, chunks) for p in part]

    lines = [f"tivit: {KEY}=True (A) minus False (B), the staged list both "
             f"legs, N={n} paired, seeds 5000..{5000 + n - 1}, today's pod", ""]
    for k in ("won T10", "won T20"):
        dd = np.array([a[k] - b[k] for a, b in pairs])
        hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
        star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
        lines.append(f"   {k}  {dd.mean():+.4f} ±{hw:.4f}{star}")

    extra = [a.get("extra_turns_taken", 0) > 0 or b.get("extra_turns_taken", 0) > 0
             for a, b in pairs]
    none = [p for p, e in zip(pairs, extra) if not e]
    broken = sum(1 for a, b in none if a != b)
    lines += ["",
              f"   games where either leg takes an extra turn: {sum(extra)} of {n}"
              f" ({sum(extra) / n:.1%})",
              f"   IDENTITY: of the {len(none)} games with no extra turn in "
              f"either leg, {broken} differ (must be 0)"]
    if any(extra):
        sub = [p for p, e in zip(pairs, extra) if e]
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
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
