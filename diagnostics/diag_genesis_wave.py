#!/usr/bin/env python3
"""§0z210: why Genesis Wave by its text wins LESS than the old tutor.

    python -m diagnostics.diag_genesis_wave [--n=6000]

Three legs on the same seeds (5000.., the tables' block), azusa's staged list:

  tutor   `genesis_wave_reveal=False`: the old rule -- the three highest-mv
          permanents of mv <= 6 from anywhere in the library, nothing milled
  text    the default: the top six revealed, every permanent of mv <= 6 put
          in, the rest MILLED
  bottom  a DIAGNOSTIC leg, not a rule anyone proposes: the text, except the
          cards not put in go to the library's BOTTOM instead of the
          graveyard, so the mill's share of text - tutor can be read apart
          from the reveal's

and a census of every Wave the text leg resolves: what it revealed, put and
milled, and how often the mill took one of the deck's permanents of mana
value above six (the finishers the fixed X=6 can reveal and never keep).

The `bottom` leg patches `AzusaGame.wave` in each worker (§0u: installed in
the worker, not the parent). Its legs are paired per seed; a game where no
Wave resolves is identical in all three, so the deltas are carried by the
games that cast one.
"""
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

FINISHER_MV = 6          # the fixed X: a permanent above it is never kept


_REAL = {}


def _install(leg):
    """Wrap the ORIGINAL `wave`, never the one installed last: a worker runs
    several jobs, and wrapping the live attribute stacked one leg's patch
    on the next (caught in the first smoke run: every Wave logged twice)."""
    from edhmc.azusa import AzusaGame
    real = _REAL.setdefault("wave", AzusaGame.wave)

    def wave(self, x, count=None, lands_only=False):
        if lands_only:
            return real(self, x, count, lands_only)
        top = {id(c) for c in self.library[-x:]}
        names = [c.name for c in reversed(self.library[-x:])]
        before = {id(p.card) for p in self.board}
        real(self, x, count, lands_only)
        put = [p.card for p in self.board
               if id(p.card) not in before and not p.is_token]
        milled = [c for c in self.graveyard if id(c) in top]
        if leg == "bottom":
            for c in milled:
                self.graveyard.remove(c)
                self.library.insert(0, c)
        self._wave_log.append((names, [c.name for c in put],
                               [c.name for c in milled]))
    AzusaGame.wave = wave


def _play(job):
    leg, seeds = job
    _install(leg)
    from edhmc.azusa import AzusaGame
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending("azusa")
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=frozenset())
    if leg == "tutor":
        cfg["genesis_wave_reveal"] = False
    init = AzusaGame.__init__

    def logged(self, *a, **k):
        init(self, *a, **k)
        self._wave_log = []
        logs.append(self._wave_log)
    AzusaGame.__init__ = logged
    out = []
    for s in seeds:
        logs = []
        r = DECKS["azusa"].sim(deck, cmd, cfg, 5000 + s)
        out.append((s, float(r["at_rounds"][10]["won"]), float(r["won"]),
                    float(r["drew_from_empty"]), logs[-1] if logs else []))
    AzusaGame.__init__ = init
    return out


def main():
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), 6000)
    from edhmc.pending import build_pending
    deck, _ = build_pending("azusa")
    finishers = sorted({c.name for c in deck
                        if c.is_permanent and c.mv > FINISHER_MV})
    legs = ("tutor", "text", "bottom")
    jobs = [(leg, list(range(i, n, 8))) for leg in legs for i in range(8)]
    with Pool(4) as pool:
        parts = pool.map(_play, jobs)
    res = {leg: {} for leg in legs}
    for (leg, _), part in zip(jobs, parts):
        for s, t10, t20, dfe, log in part:
            res[leg][s] = (t10, t20, dfe, log)
    seeds = sorted(res["tutor"])
    reached = [s for s in seeds if any(res[l][s][3] for l in legs)]

    def delta(a, b, subset, i):
        d = np.array([res[a][s][i] - res[b][s][i] for s in subset])
        return d.mean(), d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else 0

    print(f"azusa, staged list, N={n} paired, seeds 5000..{5000 + n - 1}")
    print(f"games where a Wave resolved in any leg: {len(reached)} "
          f"({len(reached) / n:.1%})\n")
    for a, b in (("text", "tutor"), ("bottom", "tutor"), ("text", "bottom")):
        for name, sub in (("all", seeds), ("reached", reached)):
            t10 = delta(a, b, sub, 0)
            t20 = delta(a, b, sub, 1)
            print(f"  {a:>6} - {b:<6} {name:<8} T10 {t10[0]:+.4f} "
                  f"±{1.96 * t10[1]:.4f}   T20 {t20[0]:+.4f} "
                  f"±{1.96 * t20[1]:.4f}")
    for leg in legs:
        dfe = np.mean([res[leg][s][2] for s in seeds])
        print(f"  drew_from_empty, {leg}: {dfe:.4f} a game")

    casts = [w for s in seeds for w in res["text"][s][3]]
    print(f"\ntext leg: {len(casts)} Waves resolved")
    if casts:
        rev = np.mean([len(w[0]) for w in casts])
        put = np.mean([len(w[1]) for w in casts])
        mil = np.mean([len(w[2]) for w in casts])
        hit = np.mean([any(m in finishers for m in w[2]) for w in casts])
        print(f"  per Wave: revealed {rev:.2f}, put {put:.2f}, "
              f"milled {mil:.2f}")
        print(f"  share of Waves that milled a permanent of mv > "
              f"{FINISHER_MV} ({', '.join(finishers)}): {hit:.1%}")
        mc = Counter(m for w in casts for m in w[2])
        print("  most milled: " + ", ".join(f"{k} {v}"
                                           for k, v in mc.most_common(8)))
    tut = [w for s in seeds for w in res["tutor"][s][3]]
    if tut:
        pc = Counter(p for w in tut for p in w[1])
        print(f"\ntutor leg: {len(tut)} Waves; what it took: "
              + ", ".join(f"{k} {v}" for k, v in pc.most_common(8)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
