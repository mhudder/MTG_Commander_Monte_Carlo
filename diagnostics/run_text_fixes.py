#!/usr/bin/env python3
"""The 2026-09-25 text fixes and Goldspan's head-to-heads (§0z49-§0z51, §0z53).

    python -m diagnostics.run_text_fixes 15000 > results/text_fixes.txt

N paired games per arm, seeds 5000.., T10 and T20, on build_pending(). Every
comparison is paired on the same seeds:

  Storm Herd     X = life vs the old constant (storm_herd_x=40), and its row
                 against the ablation blank at both settings -- the X = 40
                 row is the check that this reproduces the committed table.
  Scrollwielder  in Caldera Pyremaw's slot, lifelink on vs off (the clause
                 patched out in each worker), and against Caldera itself.
  Goldspan       in Caldera's slot, and for the two cuts §0c named.
  Ranger of Eos  the tutor vs its old `draw2`, and its row both ways.

Lurrus's hybrid pips (§0z52) are diagnostics/run_lurrus_hybrid.py.
"""
import sys, dataclasses, numpy as np
from multiprocessing import Pool
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
MET = ("won", "damage", "storm_herd_pegasi", "lifelink_gained",
       "ranger_tutored", "cards_drawn")

def build(spec):
    from edhmc.pending import build_pending
    from edhmc.experiment import repl_priority, _swap_many
    from tools.ablation import blank_like
    from edhmc.decks import lorehold_v16 as LM
    deck, cmd = build_pending(spec["deck"])
    if "blank" in spec:
        i = next(i for i, c in enumerate(deck) if c.name == spec["blank"])
        deck = list(deck)
        deck[i] = blank_like(deck[i], repl_priority(deck))
    if "swap" in spec:
        out, new = spec["swap"]
        deck = _swap_many(deck, [out], [getattr(LM, new)])
    if spec.get("ranger_draw2"):
        deck = [dataclasses.replace(c, script="draw2")
                if c.name == "Ranger of Eos" else c for c in deck]
    return deck, cmd

def job(a):
    spec, turns, lo, hi = a
    import edhmc.lorehold as L
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    if spec.get("no_lifelink"):
        L.scrollwielder_lifelink = lambda g, d: None
    deck, cmd = build(spec)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **spec.get("cfg", {}))
    out = {m: [] for m in MET}
    for s in range(lo, hi):
        r = R[spec["deck"]].sim(deck, cmd, cfg, 5000 + s)
        for m in MET:
            out[m].append(float(r.get(m, 0)))
    return out

ARMS = {
    "L":          {"deck": "lorehold"},
    "L_x40":      {"deck": "lorehold", "cfg": {"storm_herd_x": 40}},
    "L_noherd":   {"deck": "lorehold", "blank": "Storm Herd"},
    "L_scroll":   {"deck": "lorehold", "swap": ("Caldera Pyremaw", "RADIANT_SCROLLWIELDER")},
    "L_scroll_noll": {"deck": "lorehold", "swap": ("Caldera Pyremaw", "RADIANT_SCROLLWIELDER"),
                      "no_lifelink": True},
    "L_gold_slot":  {"deck": "lorehold", "swap": ("Caldera Pyremaw", "GOLDSPAN_DRAGON")},
    "L_gold_act":   {"deck": "lorehold", "swap": ("Blasphemous Act", "GOLDSPAN_DRAGON")},
    "L_gold_grv":   {"deck": "lorehold", "swap": ("Lightning Greaves", "GOLDSPAN_DRAGON")},
    "K":          {"deck": "karlov"},
    "K_draw2":    {"deck": "karlov", "ranger_draw2": True},
    "K_noranger": {"deck": "karlov", "blank": "Ranger of Eos"},
}
PAIRS = (
    ("L", "L_x40", "Storm Herd: X = life  minus  X = 40"),
    ("L", "L_noherd", "Storm Herd row (card - blank), new"),
    ("L_x40", "L_noherd", "Storm Herd row at X = 40 (same blank)"),
    ("L_scroll", "L_scroll_noll", "Scrollwielder lifelink (on - off)"),
    ("L_scroll", "L", "Scrollwielder minus Caldera, same slot"),
    ("L_gold_slot", "L", "Goldspan minus Caldera, same slot"),
    ("L_gold_act", "L", "-Blasphemous Act +Goldspan"),
    ("L_gold_grv", "L", "-Lightning Greaves +Goldspan"),
    ("K", "K_draw2", "Ranger of Eos: tutor minus draw2"),
    ("K", "K_noranger", "Ranger of Eos row (card - blank), new"),
    ("K_draw2", "K_noranger", "Ranger of Eos row as draw2 (same blank)"),
)
if __name__ == "__main__":
    CH = 8; tasks = []; keys = []
    for name, spec in ARMS.items():
        for t in (10, 20):
            for k in range(CH):
                tasks.append((spec, t, k*N//CH, (k+1)*N//CH)); keys.append((name, t))
    with Pool(4, maxtasksperchild=1) as p:
        res = p.map(job, tasks, chunksize=1)
    cols = {}
    for k, r in zip(keys, res):
        d = cols.setdefault(k, {m: [] for m in MET})
        for m in MET: d[m] += r[m]
    for a, b, lab in PAIRS:
        for t in (10, 20):
            s = ""
            for m in ("won", "damage"):
                x = np.array(cols[(a, t)][m]) - np.array(cols[(b, t)][m])
                s += f"  {m} {x.mean():+.4f} +-{1.96*x.std(ddof=1)/np.sqrt(len(x)):.4f}"
            print(f"{lab:42s} T{t}{s}")
    for name in ARMS:
        print(name, {m: round(float(np.mean(cols[(name, 20)][m])), 4) for m in MET})
