#!/usr/bin/env python3
"""§0z221 (queue item 45, §0z197 A3): how each deck LOSES on today's pod.

    python -m diagnostics.run_loss_census [N]      # default 3000, T20

Per deck: the share of losses to an opponent's clock (`loss_route` 2) and to
life (1); for the clock kills, the route that carried each (`Opponent.route`,
§0z140), your life when it came, and your creature count. A spy wraps
`opponents._clock_seat` ONCE per worker process (a wrapper installed per game
re-wraps itself, and recursed on the first try). Seeds 5000.. .
"""
import collections, sys
from multiprocessing import Pool
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
INFO = {}
def play(args):
    deck, s = args
    import edhmc.opponents as OPP
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    info = INFO; info.clear()
    if getattr(OPP._clock_seat, "_spy", False):
        return _run(deck, s, info)
    real = OPP._clock_seat
    def spy(g, i, rolls_t):
        life, opp = g.your_life, g.opponents[i]
        bodies = len([p for p in g.board if OPP.is_creature_now(g, p)]) if hasattr(g, "board") else -1
        killed = real(g, i, rolls_t)
        if killed:
            info.update(life=life, route=getattr(opp, "route", "?"), bodies=bodies)
        return killed
    spy._spy = True
    OPP._clock_seat = spy
    return _run(deck, s, info)
def _run(deck, s, info):
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    d, c = build_pending(deck)
    r = DECKS[deck].sim(d, c, dict(DEFAULT_CFG, turns=20, watch=frozenset()), 5000 + s)
    return deck, r["won"], r.get("loss_route", 0), dict(info)
if __name__ == "__main__":
    decks = ["rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa"]
    with Pool(4) as p:
        rows = p.map(play, [(d, s) for d in decks for s in range(N)], chunksize=50)
    for d in decks:
        rs = [r for r in rows if r[0] == d]
        lost = [r for r in rs if not r[1]]
        clock = [r for r in lost if r[2] == 2]; life = [r for r in lost if r[2] == 1]
        routes = collections.Counter(r[3].get("route") for r in clock)
        lives = sorted(r[3]["life"] for r in clock)
        med = lives[len(lives) // 2] if lives else 0
        hi = sum(1 for x in lives if x >= 30) / max(1, len(lives))
        bod = sorted(r[3]["bodies"] for r in clock); mb = bod[len(bod)//2] if bod else 0
        print(f"{d:<11} won {sum(r[1] for r in rs)/N:.3f}  losses: clock {len(clock)/max(1,len(lost)):.0%}, life {len(life)/max(1,len(lost)):.0%}, other {(len(lost)-len(clock)-len(life))/max(1,len(lost)):.0%}"
              f" | clock routes {dict(routes)} | your life at the kill: median {med:.0f}, >=30 in {hi:.0%} | your creatures median {mb}")
