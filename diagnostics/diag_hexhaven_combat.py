#!/usr/bin/env python3
"""§0z249: how Hexhaven Invigorator is used in combat -- does it attack every
turn, is it kept back, and where its damage triggers come from.

    python -m diagnostics.diag_hexhaven_combat 3000 \\
        > results/diag_hexhaven_combat_20261123.txt

The owner, 2026-11-23: "does the deck attack with the invigorator every turn
since no one will realistically block it, or is it kept back on defense?"
Hexhaven in Ka-Zar's slot (the least costly swap, §0z249), seeds 5000..,
today's defaults. Counted by wrapping, never changing, four functions:
`AzusaGame.combat` (a turn it could attack: on the battlefield, untapped,
not summoning-sick), `opponents.combat_damage` (whether it is among the
attackers sent after `hold_back`), `opponents.resolve_trades` (whether the
pod blocked it) and `opponents._attack_you` (the pod's attacks at you while
it is out, and whether it blocked one and was dealt damage). Each wrapper
copies its function's signature and calls it unchanged, so the games are
the games `run_azusa_hexhaven` played.
"""
import sys
from collections import Counter
from multiprocessing import Pool

ROWS = ("games", "your turns with it out", "turns it could attack",
        "turns it attacked", "turns it was kept back",
        "attacks the pod blocked", "blockers on it",
        "pod attack steps at you, it out", "  ...it untapped",
        "  ...it blocked and was dealt damage", "hexhaven_triggers",
        "hexhaven_damage", "hexhaven_lands")


def job(seeds):
    import edhmc.azusa as AZ
    import edhmc.opponents as OPP
    from edhmc.experiment import DEFAULT_CFG, _swap_many
    from edhmc.pending import DECKS as CATALOG, build_pending
    from edhmc.registry import DECKS

    base, cmd = build_pending("azusa")
    deck = _swap_many(base, ["Ka-Zar of the Savage Land"],
                      [CATALOG["azusa"][1]["Hexhaven Invigorator"]])
    c = Counter()
    real = (AZ.AzusaGame.combat, OPP.combat_damage, OPP.resolve_trades,
            OPP._attack_you)
    turn = {}

    def is_hex(p):
        return p.card.name == "Hexhaven Invigorator"

    def combat(self):
        hx = [p for p in self.board if is_hex(p)]
        if hx:
            c["your turns with it out"] += 1
        turn["eligible"] = any(not p.sick and not p.tapped for p in hx)
        turn["attacked"] = False
        real[0](self)
        if turn["eligible"]:
            c["turns it could attack"] += 1
            c["turns it attacked" if turn["attacked"]
              else "turns it was kept back"] += 1
        turn["eligible"] = False

    def combat_damage(g, attackers, *a, **k):
        if turn.get("eligible") and any(is_hex(p) for p in attackers):
            turn["attacked"] = True
        return real[1](g, attackers, *a, **k)

    def resolve_trades(g, defender, assigned):
        for a, blks in assigned:
            if is_hex(a.perm):
                c["attacks the pod blocked"] += 1
                c["blockers on it"] += len(blks)
        return real[2](g, defender, assigned)

    def attack_you(g, opp, bodies, sent, dead):
        hx = [p for p in g.board if is_hex(p)]
        if hx:
            c["pod attack steps at you, it out"] += 1
            c["  ...it untapped"] += any(not p.tapped for p in hx)
        before = g.m["hexhaven_triggers"]
        real[3](g, opp, bodies, sent, dead)
        if g.m["hexhaven_triggers"] > before:
            c["  ...it blocked and was dealt damage"] += 1

    AZ.AzusaGame.combat = combat
    OPP.combat_damage = combat_damage
    OPP.resolve_trades = resolve_trades
    OPP._attack_you = attack_you
    sim = DECKS["azusa"].sim
    cfg = dict(DEFAULT_CFG, turns=20, watch=frozenset())
    for s in seeds:
        r = sim(list(deck), cmd, cfg, s)
        c["games"] += 1
        for k in ("hexhaven_triggers", "hexhaven_damage", "hexhaven_lands"):
            c[k] += r[k]
    return c


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    chunks = [range(5000 + k * n // 4, 5000 + (k + 1) * n // 4)
              for k in range(4)]
    with Pool(4) as p:
        tot = sum(p.map(job, chunks), Counter())
    print(f"azusa, Hexhaven Invigorator in Ka-Zar's slot, N={n:,} games, "
          f"seeds 5000.., today's defaults.\n")
    for k in ROWS:
        v = tot[k]
        print(f"  {k:<42}{v:g}")


if __name__ == "__main__":
    main()
