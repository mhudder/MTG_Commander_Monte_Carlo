#!/usr/bin/env python3
"""Necropotence's policy (§0z162): how much life to pay, and how many cards
to buy -- the §0z160/§0z161 method, applied to the Citadel's neighbour.

    python -m diagnostics.run_necro_policy forks N OUT.txt [ARM ...]
    python -m diagnostics.run_necro_policy policies N OUT.txt [ARM ...]

"Pay 1 life: Exile the top card of your library face down. Put that card
into your hand at the beginning of your next end step." The pilot pays after
the last main phase (`karlov.necropotence_step`), for `necropotence_cards`:
up to the hand target (`necro_target`, 7 -- the maximum hand size the cards
meet at cleanup, CR 514.1; Reliquary Tower lifts it), never below the floor
(`necro_floor`, 10 -- or the pod's clock, `necro_floor_mode="clock"`).

`forks`: each seed is played once on today's policy, and every turn that
reaches `necropotence_step` with Necropotence on the battlefield is logged:
the life, the hand, the chip damage on the table (`opponents.predicted_chip`)
and whether Reliquary Tower is out. Then the seed is replayed under every arm
in `FORK_ARMS`, set on THAT turn only (`turn_cfg`): identical up to it,
today's policy after it. `BASE_ARM` is today's policy replayed and must
reproduce the baseline on every turn (§0z35). Cells are paired differences
against it, at T20. "Best by bin" is picked on even seeds and reported on
odd ones. `T0` buys nothing that turn: what one turn of the card is worth.
The Tower targets (`TT9`..) differ from the base only while the Tower is out,
so they are read on those turns.

`policies`: every arm is `build_pending("karlov")` with knobs set on every
turn, N paired games at T10 and T20 on seeds 5000.., minus "base".
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 500

FORK_ARMS = (
    [(f"N{f:g}", {"necro_floor_mode": "fixed", "necro_life_floor": f})
     for f in (1, 3, 5, 7, 10, 13, 16, 20, 25)]
    + [(f"clk+{p:g}", {"necro_floor_mode": "clock", "necro_clock_pad": float(p)})
       for p in (1, 2, 4)]
    + [(f"T{t}", {"necro_hand_target": t}) for t in (0, 3, 5, 6)]
    + [(f"TT{t}", {"necro_tower_target": t}) for t in (9, 11, 14, 20, 30, 99)])
BASE_ARM = "N10"       # today's default: fixed 10, target 7

ARMS = {
    "base": {},
    "floor1": {"necro_life_floor": 1}, "floor5": {"necro_life_floor": 5},
    "floor7": {"necro_life_floor": 7}, "floor13": {"necro_life_floor": 13},
    "floor20": {"necro_life_floor": 20},
    "clock1": {"necro_floor_mode": "clock", "necro_clock_pad": 1.0},
    "clock2": {"necro_floor_mode": "clock", "necro_clock_pad": 2.0},
    "clock4": {"necro_floor_mode": "clock", "necro_clock_pad": 4.0},
    "target5": {"necro_hand_target": 5}, "target6": {"necro_hand_target": 6},
    "tower9": {"necro_tower_target": 9}, "tower11": {"necro_tower_target": 11},
    "tower14": {"necro_tower_target": 14},
    "tower20": {"necro_tower_target": 20},
    "tower30": {"necro_tower_target": 30},
    "tower99": {"necro_tower_target": 99},   # no target: the floor decides
    "tower20_clock1": {"necro_tower_target": 20, "necro_floor_mode": "clock",
                       "necro_clock_pad": 1.0},
    "tower99_clock1": {"necro_tower_target": 99, "necro_floor_mode": "clock",
                       "necro_clock_pad": 1.0},
}
MET = ("won", "damage", "necro_cards", "necro_life_paid", "final_life")

_D = {}


def _init(arms=None):
    from edhmc.pending import build_pending
    _D["deck"], _D["cmd"] = build_pending("karlov")
    _D["arms"] = [(nm, k) for nm, k in FORK_ARMS
                  if arms is None or nm in arms or nm == BASE_ARM]


def _cfg(extra, turns):
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=turns, **extra)


def _fork_job(args):
    lo, hi = args
    from edhmc import karlov as K
    from edhmc import opponents as OPP
    real = K.necropotence_step
    log = []

    def spy(g):
        if g.has("Necropotence") and g.result is None:
            log.append((g.turn, g.your_life, len(g.hand),
                        OPP.predicted_chip(g, 1),
                        float(g.has("Reliquary Tower")),
                        K.necropotence_cards(g)))
        return real(g)
    cfg = _cfg({}, 20)
    rows = []
    for s in range(lo, hi):
        log.clear()
        K.necropotence_step = spy
        try:
            base = K.simulate(_D["deck"], _D["cmd"], cfg, s)
        finally:
            K.necropotence_step = real
        for turn, life, hand, chip, tower, buy in list(log):
            row = [s, turn, life, hand, chip, tower, buy, base["won"]]
            for _, knobs in _D["arms"]:
                alt = K.simulate(_D["deck"], _D["cmd"],
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
    if os.environ.get("NECRO_RAW"):
        np.save(os.environ["NECRO_RAW"], a)
    names = [nm for nm, _ in FORK_ARMS
             if arms is None or nm in arms or nm == BASE_ARM]
    won = {nm: a[:, 8 + k] for k, nm in enumerate(names)}
    base = a[:, 7]
    same = bool((won[BASE_ARM] == base).all())
    tower = a[:, 5] == 1

    def cell(m, nm):
        d = won[nm][m] - base[m]
        if m.sum() < 2:
            return 0.0, 0.0
        return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(m.sum())

    lines = [f"Necropotence, the policy on ONE turn (turn_cfg), {n:,} seeds "
             f"from {SEED0}, T20, python {sys.version.split()[0]}",
             f"{len(a):,} Necropotence turns ({int(tower.sum()):,} with "
             f"Reliquary Tower out). {BASE_ARM} (today's policy, replayed) "
             f"reproduces the baseline on every turn: "
             f"{'YES' if same else 'NO -- the comparison is broken'}",
             f"bought on the base: mean {a[:, 6].mean():.2f} cards; hand "
             f"before the buy median {np.median(a[:, 3]):g}; life median "
             f"{np.median(a[:, 2]):.1f}; chip on the table median "
             f"{np.median(a[:, 4]):.1f}",
             f"cells: P(win) minus {BASE_ARM}, paired by seed and turn; "
             "* = 95% CI excludes 0", ""]
    lines.append("OVERALL (the Tower targets on Tower turns only)")
    allm = np.ones(len(a), bool)
    for nm in names:
        m = tower if nm.startswith("TT") else allm
        mu, ci = cell(m, nm)
        lines.append(f"  {nm:<8}{mu:>+9.4f}{ci:>8.4f}"
                     f"{'*' if abs(mu) > ci else ' '}  (n={int(m.sum()):,})")
    lines.append("")

    def grid(title, col, edges, arms, only=None):
        lines.append(title + "  (x1000; [best] by point estimate)")
        lines.append(f"  {'bin':<10}{'turns':>6}{'P(win)':>7} "
                     + "".join(f"{nm:>8}" for nm in arms))
        for lo, hi in zip(edges, edges[1:]):
            m = (a[:, col] >= lo) & (a[:, col] < hi)
            if only is not None:
                m &= only
            if m.sum() < 30:
                continue
            cells = [cell(m, nm) for nm in arms]
            best = max(range(len(arms)), key=lambda k: cells[k][0])
            txt = "".join(
                (f"[{1000 * mu:>+5.1f}]" if k == best else f"{1000 * mu:>+7.1f}")
                + ("*" if abs(mu) > ci else " ")
                for k, (mu, ci) in enumerate(cells))
            lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
            lines.append(f"  {lab:<10}{int(m.sum()):>6}{base[m].mean():>7.3f} "
                         + txt)
        lines.append("")

    no_tt = [nm for nm in names if not nm.startswith("TT")]
    grid("BY LIFE AT THE BUY", 2, [0, 15, 20, 25, 30, 40, 60, 1e9], no_tt)
    grid("BY THE CHIP ON THE TABLE", 4, [0, 1, 2, 4, 6, 1e9], no_tt)
    grid("BY HAND SIZE BEFORE THE BUY", 3, [0, 3, 4, 5, 6, 7, 1e9], no_tt)
    tt = [nm for nm in names if nm.startswith("TT")]
    if tt:
        grid("RELIQUARY TOWER OUT: THE TARGET, BY LIFE AT THE BUY", 2,
             [0, 15, 20, 25, 30, 40, 60, 1e9], [BASE_ARM] + tt, only=tower)
        grid("RELIQUARY TOWER OUT: THE TARGET, BY THE CHIP ON THE TABLE", 4,
             [0, 1, 2, 4, 6, 1e9], [BASE_ARM] + tt, only=tower)

    lines.append("BEST BY LIFE BIN, CHOSEN ON EVEN SEEDS, MEASURED ON ODD "
                 f"(minus {BASE_ARM})")
    even, odd = a[:, 0] % 2 == 0, a[:, 0] % 2 == 1
    edges = [0, 15, 20, 25, 30, 40, 60, 1e9]
    for lo, hi in zip(edges, edges[1:]):
        m = (a[:, 2] >= lo) & (a[:, 2] < hi)
        pick = max(no_tt, key=lambda nm: cell(m & even, nm)[0])
        mu, ci = cell(m & odd, pick)
        lab = f"{lo:g}-{hi:g}" if hi < 1e9 else f"{lo:g}+"
        lines.append(f"  {lab:<10} picked {pick:<7} on odd seeds "
                     f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ''}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def _policy_job(args):
    arm, turns, lo, hi = args
    from edhmc.karlov import simulate
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
    lines = [f"Necropotence's policy (§0z162): N={n:,} paired, seeds "
             f"{SEED0}.., karlov as staged, python {sys.version.split()[0]}",
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
        nc = cols[(a, 20)][:, 2].mean() - cols[("base", 20)][:, 2].mean()
        lines.append(f"{a:<12}" + "  ".join(cells)
                     + f"  necro_cards T20 {nc:+.3f}")
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
