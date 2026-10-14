#!/usr/bin/env python3
"""Item 24's change 4 (§0z139): every card it made live, against ablation's
blank, and the two policies said out loud with it.

    python -m diagnostics.run_change4 [--n=3000] [--out=results/change4_20261014.txt]

`diagnostics.run_card_vs_blank`'s question -- the STAGED list against itself
with the card replaced by `tools.ablation.blank_like` at the deck's median
priority (§0j), seeds 5000.. both legs, T20 with T10 read off it -- run in
parallel, on today's pod and on `experiment.POD_V4`. Then:

  * SYLVAN LIBRARY's `library_life_floor` swept (12 / 20 / 40, where 40 never
    pays): the card against its blank at each floor.
  * LOREHOLD'S TOP at {1} against the old free sort (`lorehold_top_cost` 1
    against 0), the staged list both legs: what the owner's cost is worth.

Each row prints keep minus blank for win rate and every numeric output
that moved, so a card's mechanism counter shows.
"""
import sys
from multiprocessing import Pool

import numpy as np

ROWS = [
    ("karlov", ("Sensei's Divining Top",)),
    ("karlov", ("Enlightened Tutor",)),
    ("lorehold", ("Gamble",)),
    ("azusa", ("Sylvan Library",)),
    ("azusa", ("Abundance",)),
    ("azusa", ("Sylvan Scrying",)),
    ("azusa", ("Crop Rotation",)),
]


def _play(job):
    deck_name, names, pod, cfg_a, cfg_b, seeds = job
    from edhmc.experiment import DEFAULT_CFG, POD_V4, repl_priority
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    from tools.ablation import blank_like
    extra = dict(POD_V4) if pod == "POD_V4" else {}
    deck, cmd = build_pending(deck_name)
    if names:
        pri = repl_priority(deck)
        other = [blank_like(c, pri) if c.name in names else c for c in deck]
    else:
        other = deck
    sim = DECKS[deck_name].sim
    out = []
    for s in seeds:
        pair = []
        for d, leg in ((deck, cfg_a), (other, cfg_b)):
            r = sim(d, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                                 watch=frozenset(), **extra, **leg), 5000 + s)
            nums = {k: float(v) for k, v in r.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)}
            nums["won T10"] = float(r["at_rounds"][10]["won"])
            nums["won T20"] = float(r["won"])
            pair.append(nums)
        out.append(pair)
    return out


def measure(pool, label, deck_name, names, pod, n, cfg_a=None, cfg_b=None):
    chunks = [list(range(i, n, 16)) for i in range(16)]
    jobs = [(deck_name, names, pod, cfg_a or {}, cfg_b or {}, c)
            for c in chunks]
    pairs = [p for part in pool.map(_play, jobs) for p in part]
    lines = [f"{label}, N={n} paired, {pod}'s pod"]
    for k in ("won T10", "won T20"):
        dd = np.array([a[k] - b[k] for a, b in pairs])
        hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
        star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
        lines.append(f"   {k}  {dd.mean():+.4f} ±{hw:.4f}{star}")
    keys = sorted({k for a, b in pairs for k in list(a) + list(b)}
                  - {"won T10", "won T20", "won", "lost"})
    for k in keys:
        a = np.mean([p[0].get(k, 0.0) for p in pairs])
        b = np.mean([p[1].get(k, 0.0) for p in pairs])
        if abs(a - b) > 1e-9:
            lines.append(f"   {k:<28} keep {a:9.3f}  blank {b:9.3f}  "
                         f"{a - b:+.3f}")
    text = "\n".join(lines)
    print(text, flush=True)
    return text


def main():
    opts = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[1:]
            if a.startswith("--") and "=" in a}
    n = int(opts.get("--n", 3000))
    out_path = opts.get("--out", "results/change4_20261014.txt")
    blocks = []
    with Pool(4) as pool:
        for pod in ("today", "POD_V4"):
            for deck_name, names in ROWS:
                blocks.append(measure(
                    pool, f"{deck_name}: {', '.join(names)} vs blank",
                    deck_name, names, pod, n))
        for floor in (12, 40):
            cfg = {"library_life_floor": floor}
            blocks.append(measure(
                pool, f"azusa: Sylvan Library vs blank, library_life_floor="
                f"{floor}", "azusa", ("Sylvan Library",), "today", n, cfg, cfg))
        blocks.append(measure(
            pool, "lorehold: Top at {1} (keep) vs the free sort (blank leg = "
            "lorehold_top_cost 0), the staged list", "lorehold", (), "today",
            n, {"lorehold_top_cost": 1}, {"lorehold_top_cost": 0}))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(blocks) + "\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
