#!/usr/bin/env python3
"""§0z213: does Chord of Calling's TARGET RANKING cost azusa games?

    python -m diagnostics.diag_chord_rank [--n=15000]

`engine.x_plan` -- the shared rule, trostani's -- ranks the library's
creatures by CAST priority, then mana value, and plans the first one the
pool affords at or above `tutor_floor` (6). Cast priority is the order the
pilot casts from hand, so in azusa's list Lotus Cobra (9, mana value 2)
outranks Avenger of Zendikar, Ancient Greenwarden and Rampaging Baloths
whenever Craterhoof (9, mana value 8) is out of reach.

Legs on the same seeds (5000.., the tables' block), azusa's staged list,
paired:

  priority  the shared rule, as it ships
  biggest   a DIAGNOSTIC: among the same creatures (priority >= floor), the
            highest mana value the pool affords, priority breaking ties

Only the ranking moves: the convoke pool, the floor, the cast decision and
the resolution are the shared rule's. The `biggest` leg patches `x_plan` in
each worker (§0u), wrapping the original; a game where no Chord is cast is
identical in both.
"""
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

_REAL = {}


def _install(leg):
    import edhmc.azusa as AZ
    import edhmc.engine as EN
    real = _REAL.setdefault("x_plan", EN.x_plan)
    if leg == "priority":
        AZ.x_plan = real
        return

    def biggest(g, card, units):
        if card.name != "Chord of Calling":
            return real(g, card, units)
        floor = g.cfg.get("tutor_floor", 6)
        pool = sorted((c for c in g.library
                       if c.is_creature and c.priority >= floor),
                      key=lambda c: (c.free_mv, c.priority), reverse=True)
        for c in pool:
            cost = {"G": 3}
            x = int(c.free_mv)
            if x:
                cost["gen"] = x
            pay = EN.can_pay(cost, units)
            if pay is not None:
                return c, cost, pay
        return None
    AZ.x_plan = biggest


def _play(job):
    leg, seeds = job
    _install(leg)
    import edhmc.azusa as AZ
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending("azusa")
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               watch=frozenset())
    picks = Counter()
    real_resolve = AZ.AzusaGame.chord_resolve

    def logged(self, plan):
        picks[plan[0].name] += 1
        return real_resolve(self, plan)
    AZ.AzusaGame.chord_resolve = logged
    out = []
    for s in seeds:
        r = DECKS["azusa"].sim(deck, cmd, cfg, 5000 + s)
        out.append((s, float(r["at_rounds"][10]["won"]), float(r["won"]),
                    r.get("chord_casts", 0)))
    AZ.AzusaGame.chord_resolve = real_resolve
    return out, picks


def main():
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), 15000)
    legs = ("priority", "biggest")
    jobs = [(leg, list(range(i, n, 8))) for leg in legs for i in range(8)]
    with Pool(4) as pool:
        parts = pool.map(_play, jobs)
    res = {leg: {} for leg in legs}
    picks = {leg: Counter() for leg in legs}
    for (leg, _), (part, pk) in zip(jobs, parts):
        picks[leg] += pk
        for s, t10, t20, casts in part:
            res[leg][s] = (t10, t20, casts)
    seeds = sorted(res["priority"])
    reached = [s for s in seeds if any(res[l][s][2] for l in legs)]
    print(f"azusa, staged list, N={n} paired, seeds 5000..{5000 + n - 1}")
    print(f"games where a Chord resolved in either leg: {len(reached)} "
          f"({len(reached) / n:.1%})\n")
    for name, sub in (("all", seeds), ("reached", reached)):
        row = []
        for i, h in ((0, "T10"), (1, "T20")):
            d = np.array([res["biggest"][s][i] - res["priority"][s][i]
                          for s in sub])
            hw = 1.96 * d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else 0
            row.append(f"{h} {d.mean():+.4f} ±{hw:.4f}")
        print(f"  biggest - priority  {name:<8} " + "   ".join(row))
    for leg in legs:
        tot = sum(picks[leg].values())
        print(f"\n{leg}: {tot} Chords resolved; what they found:")
        for k, v in picks[leg].most_common(10):
            print(f"  {v:>5}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
