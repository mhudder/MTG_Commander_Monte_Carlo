#!/usr/bin/env python3
"""WHY THE POD'S BOARDS OUTRUN ITS MANA (queue item 53, the owner's
2026-11-26 question before item 52's re-fit; §0z264).

    python -m diagnostics.diag_pod_mana_budget [DECK] [--n=600] [--gated]

Measures a MECHANISM, changes nothing: it wraps `opponents.pod_untap`,
`pod_spend` and `charge_growth` and tabulates, per opponent per pod turn
(1..12), averaged over every living opponent-turn:

  supply   the mana at its untap step (its row's `spare` plus gifts,
           Treasures and mana creatures)
  demand   what it spends, by kind: route pieces, removal (spot, A/E,
           wipe, ward), bodies -- and the overspend `pod_spend` clamps
  bodies   how many arrive, their mean mana value, and the share whose
           mana value exceeds that turn's mana sources (lands, rocks and
           mana creatures -- what it could ever tap)

With `--gated` (`pod_develop_gated=True`) it also splits each body the gate
holds back by WHY: the mana was not there at all ("no mana"), only the
answer reserve stood in the way ("reserve"), or it was affordable and
waited behind an unaffordable one in front of it ("blocked behind").

Both legs default to the staged list and today's pod; seeds 5000.. .
"""
import sys
from collections import defaultdict

import edhmc.opponents as OPP
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS

TURNS = 12


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    deck_name = args[0] if args else "tivit"
    n = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--n=")),
             600)
    gated = "--gated" in sys.argv
    acc = defaultdict(float)        # (turn, key) -> sum
    cnt = defaultdict(int)          # turn -> opponent-turns seen

    real_untap, real_spend, real_growth = (OPP.pod_untap, OPP.pod_spend,
                                           OPP.charge_growth)

    def turn_of(g):
        return min(OPP.pod_turn(g), TURNS)

    def untap(g, i):
        real_untap(g, i)
        o = g.opponents[i]
        if not o.alive or not OPP.pod_mana_on(g):
            return
        t = turn_of(g)
        row = OPP.pod_mana_row(g, o)
        cnt[t] += 1
        acc[t, "supply"] += o.mana_left
        acc[t, "sources"] += (row.sources if row is not None else 0.0) \
            + OPP.mana_creature_mana(g, o)
        acc[t, "lands"] += row.lands if row is not None else 0.0

    def spend(g, o, amount, what, floor=0.0):
        if o is not None and amount > 0 and OPP.pod_mana_on(g):
            t = turn_of(g)
            kind = what if what in ("body", "piece") else "removal"
            acc[t, f"demand_{kind}"] += amount
            before = g.m["pod_overspent"]
            real_spend(g, o, amount, what, floor)
            acc[t, f"over_{kind}"] += g.m["pod_overspent"] - before
            return
        real_spend(g, o, amount, what, floor)

    def growth(g, o, before):
        t = turn_of(g)
        arrivals = OPP._arrival_mvs(g, o, before)
        row = OPP.pod_mana_row(g, o)
        sources = ((row.sources if row is not None else 0.0)
                   + OPP.mana_creature_mana(g, o))
        acc[t, "arrivals"] += len(arrivals)
        acc[t, "arrival_mv"] += sum(arrivals)
        acc[t, "over_sources"] += sum(1 for mv in arrivals if mv > sources)
        if gated and OPP.pod_mana_on(g) and OPP.pod_knob(
                g.cfg, "pod_develop_gated"):
            keep = OPP.answer_reserve(g, o)
            left = o.mana_left
            blocked = False
            for mv in arrivals:
                if blocked:
                    why = ("blocked" if left - keep >= mv - 1e-9
                           else "no_mana" if left < mv - 1e-9 else "reserve")
                    acc[t, f"held_{why}"] += 1
                    continue
                if left - keep < mv - 1e-9:
                    blocked = True
                    acc[t, "held_no_mana" if left < mv - 1e-9
                        else "held_reserve"] += 1
                    continue
                left -= mv
        real_growth(g, o, before)

    OPP.pod_untap, OPP.pod_spend, OPP.charge_growth = untap, spend, growth
    deck, cmd = build_pending(deck_name)
    sim = DECKS[deck_name].sim
    cfg = dict(DEFAULT_CFG, turns=20)
    if gated:
        cfg["pod_develop_gated"] = True
    for s in range(5000, 5000 + n):
        sim(deck, cmd, cfg, s)

    print(f"{deck_name}, {n} games, seeds 5000.., "
          f"{'GATED (pod_develop_gated)' if gated else 'today: charged, not gated'}"
          " -- per living opponent-turn\n")
    head = ("turn  lands sources supply | pieces removal bodies | over:pc  rm  "
            "body | arr  mv>src  meanmv")
    if gated:
        head += " | held: nomana reserve blocked"
    print(head)
    for t in range(1, TURNS + 1):
        c = cnt[t] or 1
        a = acc[t, "arrivals"]
        row = (f"{t:>4} {acc[t,'lands']/c:6.2f} {acc[t,'sources']/c:7.2f} "
               f"{acc[t,'supply']/c:6.2f} | {acc[t,'demand_piece']/c:6.2f} "
               f"{acc[t,'demand_removal']/c:7.2f} {acc[t,'demand_body']/c:6.2f} | "
               f"{acc[t,'over_piece']/c:6.2f} {acc[t,'over_removal']/c:4.2f} "
               f"{acc[t,'over_body']/c:5.2f} | {a/c:4.2f} "
               f"{(acc[t,'over_sources']/a if a else 0):6.0%} "
               f"{(acc[t,'arrival_mv']/a if a else 0):6.2f}")
        if gated:
            row += (f" | {acc[t,'held_no_mana']/c:6.2f} "
                    f"{acc[t,'held_reserve']/c:7.2f} {acc[t,'held_blocked']/c:7.2f}")
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
