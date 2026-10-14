#!/usr/bin/env python3
"""One card (or several, blanked together) against ablation's blank, paired.

    python -m diagnostics.run_card_vs_blank azusa "Storm Cauldron"
    python -m diagnostics.run_card_vs_blank shilgengar "Angel of Suffering" --n=3000 --pod=POD_V4
    python -m diagnostics.run_card_vs_blank karlov "Swords to Plowshares,Path to Exile"

The ablation table's question for cards already in the list, at a chosen N
and pod, without a full table: the STAGED list against itself with the
named cards replaced by `tools.ablation.blank_like` at the deck's median
priority (§0j), seeds 5000.. both legs. Several names are blanked TOGETHER
(leave-one-out is blind to redundancy, §0z27). `--pod=POD_V4` plays
`experiment.POD_V4`. Prints keep minus blank for win rate at T10 and T20,
and every numeric output that moved, so a card's mechanism counter shows.
"""
import sys

import numpy as np


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[1:]
            if a.startswith("--") and "=" in a}
    deck_name, names = args[0], [n.strip() for n in args[1].split(",")]
    n = int(opts.get("--n", 2000))
    from edhmc.experiment import DEFAULT_CFG, POD_V4, repl_priority
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    from tools.ablation import blank_like
    extra = dict(POD_V4) if opts.get("--pod") == "POD_V4" else {}
    deck, cmd = build_pending(deck_name)
    missing = [x for x in names if x not in {c.name for c in deck}]
    if missing:
        raise SystemExit(f"not in {deck_name}'s staged list: {missing}")
    pri = repl_priority(deck)
    blank = [blank_like(c, pri) if c.name in names else c for c in deck]
    sim = DECKS[deck_name].sim
    rows = {"keep": [], "blank": []}
    for s in range(n):
        for leg, d in (("keep", deck), ("blank", blank)):
            r = sim(d, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                                 watch=frozenset(), **extra), 5000 + s)
            rows[leg].append((float(r["at_rounds"][10]["won"]), r))
    print(f"{deck_name}: {', '.join(names)} vs blank, N={n} paired, "
          f"{opts.get('--pod', 'today')}'s pod")
    for label, get in (("won T10", lambda x: x[0]),
                       ("won T20", lambda x: float(x[1]["won"]))):
        dd = (np.array([get(x) for x in rows["keep"]])
              - np.array([get(x) for x in rows["blank"]]))
        hw = 1.96 * dd.std(ddof=1) / np.sqrt(n)
        star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
        print(f"   {label}  {dd.mean():+.4f} ±{hw:.4f}{star}")
    keys = sorted({k for _, r in rows["keep"] + rows["blank"] for k, v in r.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)})
    for k in keys:
        a = np.mean([float(r.get(k, 0)) for _, r in rows["keep"]])
        b = np.mean([float(r.get(k, 0)) for _, r in rows["blank"]])
        if abs(a - b) > 1e-9 and k not in ("won",):
            print(f"   {k:<28} keep {a:9.3f}  blank {b:9.3f}  {a - b:+.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
