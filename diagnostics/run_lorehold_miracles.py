#!/usr/bin/env python3
"""Lorehold's miracles and Sensei's Divining Top (§0z164): the §0z160-§0z163
method on the deck whose engine is the top of its library.

    python -m diagnostics.run_lorehold_miracles forks top N OUT.txt
    python -m diagnostics.run_lorehold_miracles forks reserve N OUT.txt
    python -m diagnostics.run_lorehold_miracles policies N OUT.txt [ARM ...] [--base=ARM]

The pilot's decisions, each a knob read through `engine.turn_knob`:
  `lorehold_top_spin`   when Top's {1} spin is used: "every" window, "own"
                        draw step only, "pod" windows only, "never"
  `lorehold_top_order`  "value" (the best miracle on top, payable or not) or
                        "afford" (the best one THIS window can pay for; none
                        payable -> the least wanted on top, the best second)
  `miracle_reserve`     mana the main phase leaves for the pod's windows (2;
                        "need" holds exactly the miracle's cost) -- §0t
  `hold_min_value`      decline to hardcast a spell worth this much as a
                        miracle (3; 99 = never hold)

`forks top`: every turn that BEGINS with Top on the battlefield; `forks
reserve`: every turn that begins with Lorehold on the battlefield. Each is
replayed under every arm of its family with the knobs set on THAT turn only
(`turn_cfg`: your turn and the pod's round after it). `base` is today's
policy replayed and must reproduce the baseline on every turn (§0z35).
Paired differences at T20; "best by bin" picked on even seeds, reported on
odd. `policies`: knobs on every turn, N paired games at T10 and T20.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 500
DECK = "lorehold"

FAMILIES = {
    "top": [("base", {}),
            ("own", {"lorehold_top_spin": "own"}),
            ("pod", {"lorehold_top_spin": "pod"}),
            ("never", {"lorehold_top_spin": "never"}),
            ("afford", {"lorehold_top_order": "afford"}),
            ("afford_own", {"lorehold_top_order": "afford",
                            "lorehold_top_spin": "own"}),
            ("afford_pod", {"lorehold_top_order": "afford",
                            "lorehold_top_spin": "pod"})],
    "reserve": [("base", {})]
               + [(f"R{r}", {"miracle_reserve": r}) for r in (0, 1, 3, 4)]
               + [("Rneed", {"miracle_reserve": "need"})]
               + [(f"H{h:g}", {"hold_min_value": float(h)}) for h in (1, 5, 99)],
}
BASE_ARM = "base"

ARMS = {"base": {}}
for fam in FAMILIES.values():
    for nm, knobs in fam:
        if nm != "base":
            ARMS[nm] = knobs
ARMS["R0_H99"] = {"miracle_reserve": 0, "hold_min_value": 99.0}
ARMS["Rknown"] = {"miracle_reserve": "known"}
ARMS["Rknown_H99"] = {"miracle_reserve": "known", "hold_min_value": 99.0}
MET = ("won", "damage", "miracles_cast", "mv_cheated", "top_spins")

_D = {}


def _init(family=None):
    from edhmc.pending import build_pending
    _D["deck"], _D["cmd"] = build_pending(DECK)
    _D["family"] = family


def _cfg(extra, turns):
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=turns, **extra)


def _fork_job(args):
    lo, hi = args
    from edhmc import lorehold as L
    fam = _D["family"]
    arms = FAMILIES[fam]
    real = L.take_turn
    log = []

    def spy(g):
        nxt = g.turn + 1                 # take_turn's turn, before it begins
        want = (g.has("Sensei's Divining Top") if fam == "top"
                else g.commander_cast)
        if want and g.result is None:
            log.append((nxt, sum(1 for p in g.board if p.card.is_land),
                        len(g.hand),
                        g.your_life))
        return real(g)
    cfg = _cfg({}, 20)
    rows = []
    for s in range(lo, hi):
        log.clear()
        L.take_turn = spy
        try:
            base = L.simulate(_D["deck"], _D["cmd"], cfg, s)
        finally:
            L.take_turn = real
        for turn, mana, hand, life in list(log):
            row = [s, turn, mana, hand, life, base["won"]]
            for _, knobs in arms:
                alt = L.simulate(_D["deck"], _D["cmd"],
                                 dict(cfg, turn_cfg=(turn, knobs)), s)
                row.append(alt["won"])
            rows.append(row)
    return rows


def forks(fam, n, out):
    jobs = [(lo, min(lo + CHUNK, SEED0 + n))
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    rows = []
    with Pool(initializer=_init, initargs=(fam,)) as pool:
        for r in pool.imap_unordered(_fork_job, jobs):
            rows.extend(r)
    a = np.array(rows, dtype=float)
    names = [nm for nm, _ in FAMILIES[fam]]
    won = {nm: a[:, 6 + k] for k, nm in enumerate(names)}
    base = a[:, 5]
    same = bool((won[BASE_ARM] == base).all())

    def cell(m, nm):
        if m.sum() < 2:
            return 0.0, 0.0
        d = won[nm][m] - base[m]
        return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(m.sum())

    what = ("Sensei's Divining Top on the battlefield" if fam == "top"
            else "Lorehold on the battlefield")
    lines = [f"Lorehold, the {fam} policy on ONE round (turn_cfg), {n:,} seeds "
             f"from {SEED0}, T20, python {sys.version.split()[0]}",
             f"{len(a):,} turns beginning with {what}. {BASE_ARM} (today's "
             f"policy, replayed) reproduces the baseline on every turn: "
             f"{'YES' if same else 'NO -- the comparison is broken'}",
             f"lands on the battlefield median {np.median(a[:, 2]):g}; hand median "
             f"{np.median(a[:, 3]):g}",
             f"cells: P(win) minus {BASE_ARM}, paired by seed and turn; "
             "* = 95% CI excludes 0", "", "OVERALL"]
    allm = np.ones(len(a), bool)
    for nm in names:
        mu, ci = cell(allm, nm)
        lines.append(f"  {nm:<11}{mu:>+9.4f}{ci:>8.4f}"
                     f"{'*' if abs(mu) > ci else ' '}")
    lines.append("")

    def grid(title, col, edges):
        lines.append(title + "  (x1000; [best] by point estimate)")
        lines.append(f"  {'bin':<10}{'turns':>6}{'P(win)':>7} "
                     + "".join(f"{nm:>11}" for nm in names))
        for lo, hi in zip(edges, edges[1:]):
            m = (a[:, col] >= lo) & (a[:, col] < hi)
            if m.sum() < 30:
                continue
            cells = [cell(m, nm) for nm in names]
            best = max(range(len(names)), key=lambda k: cells[k][0])
            txt = "".join(
                (f"   [{1000 * mu:>+5.1f}]" if k == best
                 else f"{1000 * mu:>+10.1f}") + ("*" if abs(mu) > ci else " ")
                for k, (mu, ci) in enumerate(cells))
            lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
            lines.append(f"  {lab:<10}{int(m.sum()):>6}{base[m].mean():>7.3f} "
                         + txt)
        lines.append("")

    grid("BY LANDS ON THE BATTLEFIELD AT THE TURN'S START", 2,
         [0, 3, 5, 7, 9, 12, 1e9])
    grid("BY THE TURN", 1, [0, 4, 6, 8, 10, 13, 1e9])
    lines.append("BEST BY LANDS BIN, CHOSEN ON EVEN SEEDS, MEASURED ON ODD "
                 f"(minus {BASE_ARM})")
    even, odd = a[:, 0] % 2 == 0, a[:, 0] % 2 == 1
    edges = [0, 3, 5, 7, 9, 12, 1e9]
    for lo, hi in zip(edges, edges[1:]):
        m = (a[:, 2] >= lo) & (a[:, 2] < hi)
        if m.sum() < 30:
            continue
        pick = max(names, key=lambda nm: cell(m & even, nm)[0])
        mu, ci = cell(m & odd, pick)
        lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
        lines.append(f"  {lab:<10} picked {pick:<11} on odd seeds "
                     f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ''}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def _policy_job(args):
    arm, turns, lo, hi = args
    from edhmc.lorehold import simulate
    cfg = _cfg(ARMS[arm], turns)
    out = np.zeros((hi - lo, len(MET)))
    for i, s in enumerate(range(lo, hi)):
        r = simulate(_D["deck"], _D["cmd"], cfg, s)
        out[i] = [r.get(m, 0) for m in MET]
    return arm, turns, lo, out


def policies(n, out, arms, ref="base"):
    jobs = [(a, t, lo, min(lo + CHUNK, SEED0 + n)) for a in arms
            for t in (10, 20) for lo in range(SEED0, SEED0 + n, CHUNK)]
    res = {}
    with Pool(initializer=_init) as pool:
        for arm, t, lo, block in pool.imap_unordered(_policy_job, jobs):
            res.setdefault((arm, t), {})[lo] = block
    cols = {k: np.vstack([v[lo] for lo in sorted(v)]) for k, v in res.items()}
    lines = [f"Lorehold's miracle and Top policy (§0z164): N={n:,} paired, "
             f"seeds {SEED0}.., the staged list, python {sys.version.split()[0]}",
             f"row = arm minus '{ref}'; * = 95% CI excludes 0",
             ""]
    for a in arms:
        if a == ref:
            continue
        cells = []
        for t in (10, 20):
            d = cols[(a, t)][:, 0] - cols[(ref, t)][:, 0]
            mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            cells.append(f"T{t} {mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        mir = cols[(a, 20)][:, 2].mean() - cols[(ref, 20)][:, 2].mean()
        spins = cols[(a, 20)][:, 4].mean() - cols[(ref, 20)][:, 4].mean()
        lines.append(f"{a:<11}" + "  ".join(cells)
                     + f"  miracles T20 {mir:+.3f}  spins {spins:+.3f}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def main():
    if sys.argv[1] == "forks":
        forks(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif sys.argv[1] == "policies":
        n, out = int(sys.argv[2]), sys.argv[3]
        rest = sys.argv[4:]
        ref = next((a.split("=", 1)[1] for a in rest
                    if a.startswith("--base=")), "base")
        arms = [a for a in rest if not a.startswith("--base=")] or list(ARMS)
        if ref not in arms:
            arms.insert(0, ref)
        policies(n, out, arms, ref)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
