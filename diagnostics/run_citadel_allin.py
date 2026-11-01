#!/usr/bin/env python3
"""Bolas's Citadel's dig (§0z160): what each part of it is worth, and the
owner's question -- AT WHAT LIFE IS DIGGING TO 1 FOR THE WIN WORTH IT?

    python -m diagnostics.run_citadel_allin policies N OUT.txt [ARM ...]
    python -m diagnostics.run_citadel_allin forks N OUT.txt

`policies`: every arm is `build_pending("karlov")` (Citadel staged) with
some knobs set, N paired games at T10 and T20 on seeds 5000.., and every
row is that arm minus "new" (today's defaults) on the same seeds. Three rows
answer other questions: "new" - "old" (the §0z160 dig against the one
before it), and the CARD under each dig, "new" - "noCit" and "old" - "noCit"
(the staged -Swamp +Citadel; a Citadel-less game is bit-identical under
both digs, so one noCit arm serves both).

`forks`: THE DECISION ITSELF, asked where it is made. Each seed is played
once on today's policy (the value dig, floor 10), and every turn whose dig
found the Citadel on the battlefield is logged with the life the turn BEGAN
at and the outs the library held (`karlov.citadel_outs`). Then the same seed
is replayed with `citadel_allin_turn` set to that turn: identical up to it,
all-in on it, today's policy after it. The paired difference is what going
to 1 on THAT turn, at THAT life, is worth to the game -- binned by life and
by outs. No deepcopy: the engines key state on `id()`, so a copied game
does not reproduce (checked: 57 of 200 diverged); a replay does, exactly.

Win rate is the objective (CLAUDE.md); `won` at T20 for the forks, because
the cost of going to 1 lands on the pod's NEXT turns.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

OLD = {"citadel_x0": False, "citadel_skip": False, "citadel_spin": False,
       "citadel_damn_single": False, "citadel_main_loop": False,
       "citadel_main2": False, "citadel_pod_instants": False,
       "citadel_decking_guard": False}

ARMS = {
    "new": {},
    "old": OLD,
    "noCit": "noCit",
    # what each part of the new dig is worth: new with that one part off
    "-x0": {"citadel_x0": False},
    "-skip": {"citadel_skip": False},
    "-spin": {"citadel_spin": False},
    "-damn": {"citadel_damn_single": False},
    "-loop": {"citadel_main_loop": False},
    "-main2": {"citadel_main2": False},
    "-pod": {"citadel_pod_instants": False},
    "-guard": {"citadel_decking_guard": False},
    # condition 4: the floor and the all-in policies
    "floor5": {"citadel_life_floor": 5.0},
    "floor15": {"citadel_life_floor": 15.0},
    "floor20": {"citadel_life_floor": 20.0},
    "always": {"citadel_allin": "always"},
    "always_wipes": {"citadel_allin": "always", "citadel_allin_wipes": True},
    "life20": {"citadel_allin": "life", "citadel_allin_life": 20.0},
    "life30": {"citadel_allin": "life", "citadel_allin_life": 30.0},
    "life40": {"citadel_allin": "life", "citadel_allin_life": 40.0},
    "life60": {"citadel_allin": "life", "citadel_allin_life": 60.0},
    "outs1": {"citadel_allin": "outs", "citadel_allin_outs": 1},
    "outs2": {"citadel_allin": "outs", "citadel_allin_outs": 2},
    "outs1_life20": {"citadel_allin": "outs", "citadel_allin_outs": 1,
                     "citadel_allin_life": 20.0},
}
MET = ("won", "damage", "citadel_casts", "citadel_life_spent", "final_life")
SEED0 = 5000
CHUNK = 500

_DECKS = {}


def _init():
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS as R
    staged, cmd = build_pending("karlov")
    module, _ = R["karlov"].build()
    used = {id(c) for c in staged}
    swamp = next(c for c in module if c.name == "Swamp" and id(c) not in used)
    nocit = [swamp if c.name == "Bolas's Citadel" else c for c in staged]
    _DECKS["staged"], _DECKS["noCit"], _DECKS["cmd"] = staged, nocit, cmd


def _cfg(extra, turns):
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=turns, **extra)


def _policy_job(args):
    arm, turns, lo, hi = args
    from edhmc.karlov import simulate
    spec = ARMS[arm]
    deck = _DECKS["noCit"] if spec == "noCit" else _DECKS["staged"]
    cfg = _cfg({} if spec == "noCit" else spec, turns)
    out = np.zeros((hi - lo, len(MET)))
    for i, s in enumerate(range(lo, hi)):
        r = simulate(deck, _DECKS["cmd"], cfg, s)
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

    def diff(a, b, t, m):
        d = cols[(a, t)][:, MET.index(m)] - cols[(b, t)][:, MET.index(m)]
        return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))

    lines = [f"Bolas's Citadel's dig (§0z160): N={n:,} paired, seeds "
             f"{SEED0}.., karlov as staged, python {sys.version.split()[0]}",
             "row = arm minus 'new' unless named; * = 95% CI excludes 0", ""]
    rows = [("new - old  (the §0z160 dig vs the one before)", "new", "old"),
            ("new - noCit  (-Swamp +Citadel, the new dig)", "new", "noCit"),
            ("old - noCit  (-Swamp +Citadel, the old dig)", "old", "noCit")]
    rows += [(f"{a} - new", a, "new") for a in arms
             if a not in ("new", "old", "noCit")]
    for label, a, b in rows:
        if (a, 10) not in cols or (b, 10) not in cols:
            continue
        cells = []
        for t in (10, 20):
            mu, ci = diff(a, b, t, "won")
            cells.append(f"T{t} {mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}")
        dm, dci = diff(a, b, 20, "damage")
        ls, lci = diff(a, b, 20, "citadel_life_spent")
        lines.append(f"{label:<50}" + "  ".join(cells)
                     + f"  dmgT20 {dm:+.2f} +-{dci:.2f}"
                     + f"  lifeSpentT20 {ls:+.2f}")
    lines.append("")
    lines.append("absolute, T20: arm  won  citadel_casts  citadel_life_spent")
    for a in arms:
        c = cols[(a, 20)]
        lines.append(f"  {a:<14}{c[:, 0].mean():.4f}  {c[:, 2].mean():.3f}"
                     f"  {c[:, 3].mean():.2f}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


# ---------------------------------------------------------------------------
# forks
# ---------------------------------------------------------------------------

def _fork_job(args):
    lo, hi = args
    from edhmc import karlov as K
    real = K.citadel_step
    log = []

    def spy(g):
        if g.has(K.CITADEL) and (not log or log[-1][0] != g.turn):
            log.append((g.turn, g.turn_life, g.your_life, K.citadel_outs(g)))
        return real(g)
    deck, cmd = _DECKS["staged"], _DECKS["cmd"]
    cfg = _cfg({}, 20)
    rows = []
    for s in range(lo, hi):
        log.clear()
        K.citadel_step = spy
        try:
            base = K.simulate(deck, cmd, cfg, s)
        finally:
            K.citadel_step = real
        for turn, turn_life, life, outs in list(log):
            alt = K.simulate(deck, cmd, dict(cfg, citadel_allin_turn=turn), s)
            rows.append((s, turn, turn_life, life, outs, base["won"],
                         alt["won"], base["citadel_life_spent"],
                         alt["citadel_life_spent"],
                         float(base["won"] and base["turn_won"] == turn),
                         float(alt["won"] and alt["turn_won"] == turn)))
    return rows


def forks(n, out):
    jobs = [(lo, min(lo + CHUNK, SEED0 + n))
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    rows = []
    with Pool(initializer=_init) as pool:
        for r in pool.imap_unordered(_fork_job, jobs):
            rows.extend(r)
    a = np.array(rows, dtype=float)
    # columns: seed turn turn_life life_at_dig outs won_base won_allin
    #          spent_base spent_allin won_this_turn_base won_this_turn_allin
    moved = a[:, 8] != a[:, 7]
    lines = [f"Bolas's Citadel, all-in on ONE turn vs today's value dig "
             f"(floor 10), {n:,} seeds from {SEED0}, T20, python "
             f"{sys.version.split()[0]}",
             f"{len(a):,} dig turns with the Citadel out; the all-in dig "
             f"spent different life on {int(moved.sum()):,} of them",
             "diff = P(win | all-in this turn) - P(win | value dig), paired "
             "by seed and turn; * = 95% CI excludes 0",
             "won THIS turn = the game was won on the turn the policy "
             "differed: the 'win outright' rate of each dig", ""]

    def block(title, masks):
        lines.append(title)
        lines.append(f"  {'bin':<22}{'turns':>7}{'moved':>7}{'P(win) value':>14}"
                     f"{'diff':>10}{'+-':>9}   diff | moved"
                     f"   won THIS turn: value  all-in")
        for label, m in masks:
            if m.sum() < 2:
                continue
            d = a[m, 6] - a[m, 5]
            ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            mm = m & moved
            dm = (a[mm, 6] - a[mm, 5]).mean() if mm.sum() else 0.0
            star = "*" if abs(d.mean()) > ci else " "
            lines.append(f"  {label:<22}{int(m.sum()):>7}{int(mm.sum()):>7}"
                         f"{a[m, 5].mean():>14.3f}{d.mean():>+10.4f}"
                         f"{ci:>9.4f}{star}  {dm:+.4f}"
                         f"{a[m, 9].mean():>22.3f}{a[m, 10].mean():>8.3f}")
        lines.append("")

    edges = [0, 10, 15, 20, 25, 30, 40, 50, 70, 1e9]
    life = a[:, 2]
    bins = [(f"turn life {lo:g}-{hi - 1:g}" if hi < 1e9 else f"turn life {lo:g}+",
             (life >= lo) & (life < hi)) for lo, hi in zip(edges, edges[1:])]
    block("BY THE LIFE THE TURN BEGAN AT", [("all", life >= -1e9)] + bins)
    outs = a[:, 4]
    block("BY OUTS (one-card wins in the library, karlov.citadel_outs)",
          [("outs 0", outs == 0), ("outs 1", outs == 1),
           ("outs 2", outs == 2), ("outs 3+", outs >= 3)])
    block("OUTS >= 1, BY LIFE",
          [(lab, m & (outs >= 1)) for lab, m in bins])
    block("OUTS 0, BY LIFE",
          [(lab, m & (outs == 0)) for lab, m in bins])
    text = "\n".join(lines)
    print(text)
    with open(out, "w") as f:
        f.write(text + "\n")


def main():
    mode, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    if mode == "policies":
        arms = sys.argv[4:] or list(ARMS)
        for a in ("new",):
            if a not in arms:
                arms.insert(0, a)
        policies(n, out, arms)
    elif mode == "forks":
        forks(n, out)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
