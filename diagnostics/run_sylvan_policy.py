#!/usr/bin/env python3
"""Sylvan Library's policy in azusa (§0z163): how much life to pay, 4 a
card -- the §0z160-§0z162 method on the third card that pays life down to
a floor.

    python -m diagnostics.run_sylvan_policy forks N OUT.txt
    python -m diagnostics.run_sylvan_policy policies N OUT.txt [ARM ...]

"At the beginning of your draw step, you may draw two additional cards. If
you do, choose two cards in your hand drawn this turn. For each of those
cards, pay 4 life or put the card on top of your library."
`engine.sylvan_library`: the two least wanted are chosen, the better of them
is kept first while life stays at or above the floor (`library_floor`: 20
fixed, or the pod's clock), at most `library_pay_max` (2) of them, and the
rest go back on top -- drawn again over the next turns, so paying buys a
card NOW, not a card at all.

`forks`: each seed is played once on today's policy, every draw step that
reaches the choice with Sylvan Library out is logged (life, the chip on the
table, hand size), and the seed is replayed under every arm in `FORK_ARMS`
on THAT turn only (`turn_cfg`). `BASE_ARM` is today's policy replayed and
must reproduce the baseline on every turn (§0z35). Paired differences at
T20; "best by bin" is picked on even seeds and reported on odd ones.
`policies`: the knobs on every turn, N paired games at T10 and T20.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 500
DECK = "azusa"

FORK_ARMS = (
    [(f"L{f:g}", {"library_floor_mode": "fixed", "library_life_floor": f})
     for f in (4, 8, 12, 16, 20, 24, 30)]
    + [("never", {"library_pay_max": 0}), ("cap1", {"library_pay_max": 1})]
    + [(f"clk+{p:g}", {"library_floor_mode": "clock", "library_clock_pad": float(p)})
       for p in (1, 4, 8)]
    + [(f"clk{r}r+1", {"library_floor_mode": "clock", "library_clock_rounds": r,
                       "library_clock_pad": 1.0}) for r in (2, 3, 6, 8)]
    + [("clkx2+1", {"library_floor_mode": "clock", "library_clock_mult": 2.0,
                    "library_clock_pad": 1.0})])
BASE_ARM = "L20"       # today's default: fixed 20, pay for up to two

ARMS = {
    "base": {},
    "floor8": {"library_life_floor": 8}, "floor12": {"library_life_floor": 12},
    "floor16": {"library_life_floor": 16}, "floor24": {"library_life_floor": 24},
    "never": {"library_pay_max": 0}, "cap1": {"library_pay_max": 1},
    "clock1": {"library_floor_mode": "clock", "library_clock_pad": 1.0},
    "clock4": {"library_floor_mode": "clock", "library_clock_pad": 4.0},
    "clock8": {"library_floor_mode": "clock", "library_clock_pad": 8.0},
    "clock2r1": {"library_floor_mode": "clock", "library_clock_rounds": 2,
                 "library_clock_pad": 1.0},
    "clock3r1": {"library_floor_mode": "clock", "library_clock_rounds": 3,
                 "library_clock_pad": 1.0},
    "clock6r1": {"library_floor_mode": "clock", "library_clock_rounds": 6,
                 "library_clock_pad": 1.0},
    "clock8r1": {"library_floor_mode": "clock", "library_clock_rounds": 8,
                 "library_clock_pad": 1.0},
    "clockx2": {"library_floor_mode": "clock", "library_clock_mult": 2.0,
                "library_clock_pad": 1.0},
}
MET = ("won", "damage", "library_kept", "library_life_paid", "final_life")

_D = {}


def _init(arms=None):
    from edhmc.pending import build_pending
    _D["deck"], _D["cmd"] = build_pending(DECK)
    _D["arms"] = [(nm, k) for nm, k in FORK_ARMS
                  if arms is None or nm in arms or nm == BASE_ARM]


def _cfg(extra, turns):
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=turns, **extra)


def _fork_job(args):
    lo, hi = args
    from edhmc import azusa as A
    from edhmc import engine as EN
    from edhmc import opponents as OPP
    real = A.sylvan_library
    log = []

    def spy(g, since):
        if (g.has("Sylvan Library") and g.result is None
                and EN.draw_is_safe(g, 2)):
            log.append((g.turn, g.your_life, OPP.predicted_chip(g, 1),
                        len(g.hand)))
        return real(g, since)
    cfg = _cfg({}, 20)
    rows = []
    for s in range(lo, hi):
        log.clear()
        A.sylvan_library = spy
        try:
            base = A.simulate(_D["deck"], _D["cmd"], cfg, s)
        finally:
            A.sylvan_library = real
        for turn, life, chip, hand in list(log):
            row = [s, turn, life, chip, hand, base["won"]]
            for _, knobs in _D["arms"]:
                alt = A.simulate(_D["deck"], _D["cmd"],
                                 dict(cfg, turn_cfg=(turn, knobs)), s)
                row.append(alt["won"])
            rows.append(row)
    return rows


def forks(n, out, arms=None):
    jobs = [(lo, min(lo + CHUNK, SEED0 + n))
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    rows = []
    with Pool(initializer=_init, initargs=(arms,)) as pool:
        for r in pool.imap_unordered(_fork_job, jobs):
            rows.extend(r)
    a = np.array(rows, dtype=float)
    if os.environ.get("SYLVAN_RAW"):
        np.save(os.environ["SYLVAN_RAW"], a)
    names = [nm for nm, _ in FORK_ARMS
             if arms is None or nm in arms or nm == BASE_ARM]
    won = {nm: a[:, 6 + k] for k, nm in enumerate(names)}
    base = a[:, 5]
    same = bool((won[BASE_ARM] == base).all())

    def cell(m, nm):
        if m.sum() < 2:
            return 0.0, 0.0
        d = won[nm][m] - base[m]
        return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(m.sum())

    lines = [f"Sylvan Library ({DECK}), the policy on ONE turn (turn_cfg), "
             f"{n:,} seeds from {SEED0}, T20, python {sys.version.split()[0]}",
             f"{len(a):,} Sylvan Library draw steps. {BASE_ARM} (today's "
             f"policy, replayed) reproduces the baseline on every turn: "
             f"{'YES' if same else 'NO -- the comparison is broken'}",
             f"life at the choice median {np.median(a[:, 2]):.1f}; chip on the "
             f"table median {np.median(a[:, 3]):.2f}",
             f"cells: P(win) minus {BASE_ARM}, paired by seed and turn; "
             "* = 95% CI excludes 0", "", "OVERALL"]
    allm = np.ones(len(a), bool)
    for nm in names:
        mu, ci = cell(allm, nm)
        lines.append(f"  {nm:<9}{mu:>+9.4f}{ci:>8.4f}"
                     f"{'*' if abs(mu) > ci else ' '}")
    lines.append("")

    def grid(title, col, edges):
        lines.append(title + "  (x1000; [best] by point estimate)")
        lines.append(f"  {'bin':<10}{'turns':>6}{'P(win)':>7} "
                     + "".join(f"{nm:>8}" for nm in names))
        for lo, hi in zip(edges, edges[1:]):
            m = (a[:, col] >= lo) & (a[:, col] < hi)
            if m.sum() < 30:
                continue
            cells = [cell(m, nm) for nm in names]
            best = max(range(len(names)), key=lambda k: cells[k][0])
            txt = "".join(
                (f"[{1000 * mu:>+5.1f}]" if k == best else f"{1000 * mu:>+7.1f}")
                + ("*" if abs(mu) > ci else " ")
                for k, (mu, ci) in enumerate(cells))
            lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
            lines.append(f"  {lab:<10}{int(m.sum()):>6}{base[m].mean():>7.3f} "
                         + txt)
        lines.append("")

    grid("BY LIFE AT THE CHOICE", 2, [0, 10, 15, 20, 25, 30, 40, 1e9])
    grid("BY THE CHIP ON THE TABLE", 3, [0, 1, 2, 3, 4, 6, 1e9])
    lines.append("BEST BY LIFE BIN, CHOSEN ON EVEN SEEDS, MEASURED ON ODD "
                 f"(minus {BASE_ARM})")
    even, odd = a[:, 0] % 2 == 0, a[:, 0] % 2 == 1
    edges = [0, 10, 15, 20, 25, 30, 40, 1e9]
    for lo, hi in zip(edges, edges[1:]):
        m = (a[:, 2] >= lo) & (a[:, 2] < hi)
        pick = max(names, key=lambda nm: cell(m & even, nm)[0])
        mu, ci = cell(m & odd, pick)
        lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
        lines.append(f"  {lab:<10} picked {pick:<8} on odd seeds "
                     f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ''}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def _policy_job(args):
    arm, turns, lo, hi = args
    from edhmc.azusa import simulate
    cfg = _cfg(ARMS[arm], turns)
    out = np.zeros((hi - lo, len(MET)))
    for i, s in enumerate(range(lo, hi)):
        r = simulate(_D["deck"], _D["cmd"], cfg, s)
        out[i] = [r[m] for m in MET]
    return arm, turns, lo, out


def policies(n, out, arms):
    jobs = [(a, t, lo, min(lo + CHUNK, SEED0 + n)) for a in arms
            for t in (10, 20) for lo in range(SEED0, SEED0 + n, CHUNK)]
    res = {}
    with Pool(initializer=_init) as pool:
        for arm, t, lo, block in pool.imap_unordered(_policy_job, jobs):
            res.setdefault((arm, t), {})[lo] = block
    cols = {k: np.vstack([v[lo] for lo in sorted(v)]) for k, v in res.items()}
    lines = [f"Sylvan Library's policy ({DECK}, §0z163): N={n:,} paired, seeds "
             f"{SEED0}.., the staged list, python {sys.version.split()[0]}",
             "row = arm minus 'base' (today's defaults); * = 95% CI excludes 0",
             ""]
    for a in arms:
        if a == "base":
            continue
        cells = []
        for t in (10, 20):
            d = cols[(a, t)][:, 0] - cols[("base", t)][:, 0]
            mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            cells.append(f"T{t} {mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        kept = cols[(a, 20)][:, 2].mean() - cols[("base", 20)][:, 2].mean()
        lines.append(f"{a:<10}" + "  ".join(cells)
                     + f"  library_kept T20 {kept:+.3f}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def main():
    mode, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    if mode == "forks":
        forks(n, out, sys.argv[4:] or None)
    elif mode == "policies":
        arms = sys.argv[4:] or list(ARMS)
        if "base" not in arms:
            arms.insert(0, "base")
        policies(n, out, arms)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
