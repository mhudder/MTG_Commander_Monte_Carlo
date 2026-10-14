"""Item 24 / POD_V4: how many of your answers land on a clock that has
already fired and been RE-ARMED, and what they buy (§0z136).

    python -m diagnostics.run_rearm_answers               # N=3000, POD_V4
    python -m diagnostics.run_rearm_answers --n=600 --decks=rendmaw,tivit
    python -m diagnostics.run_rearm_answers --out=results/x.txt
    python -m diagnostics.run_rearm_answers --cfg=rearm_rule=reland   (§0z137)

When an opponent's clock eliminates ANOTHER opponent, `resolve_clocks`
re-arms it `clock_rearm` (4) rounds on -- and leaves its route's pieces
where they were, all of them out. `answer_target` aims at the opponent with
the most pieces out, so a re-armed route draws answers, and a removal there
only moves the kill when the rebuild plus the piece's lead reaches past the
re-armed kill turn. This counts, per deck: re-arms a game, piece removals
on FRESH routes and on RE-ARMED ones, the rounds each moved the kill, and
the share that moved it not at all.

Every removal is counted, whatever made it (a spot answer, a sweeper, a
response), by wrapping `opponents.remove_threat_piece`; a route is re-armed
from the `resolve_clocks` call that moved its kill turn after it was due.
The STAGED lists (`build_pending`), POD_V4, T20, seeds 5000 + s. A count,
not a paired comparison: nothing here is switched.
"""
import sys
from collections import Counter
from multiprocessing import Pool

from edhmc.registry import ACTIVE

N = 3000


def measure(args):
    deck, n, extra = args
    from edhmc import opponents as O
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG, POD_V4
    from edhmc.registry import DECKS
    c = Counter()
    real_remove, real_clocks = O.remove_threat_piece, O.resolve_clocks

    # Installed in the worker, so it holds under a spawning Pool too (§0u).
    def remove(g, o, k):
        moved = real_remove(g, o, k)
        tag = "rearmed" if getattr(o, "_rearmed", False) else "fresh"
        c[f"{tag}_removals"] += 1
        c[f"{tag}_moved"] += moved
        c[f"{tag}_zero"] += (moved == 0)
        return moved

    def clocks(g):
        before = {id(o): o.kill_turn for o in g.opponents}
        real_clocks(g)
        for o in g.opponents:
            due = before[id(o)]
            if (o.alive and not o.clock_fired and o.kill_turn != due
                    and O.pod_turn(g) >= due):
                o._rearmed = True
                c["rearms"] += 1

    O.remove_threat_piece, O.resolve_clocks = remove, clocks
    deck_list, cmd = build_pending(deck)
    sim = DECKS[deck].sim
    for s in range(n):
        sim(deck_list, cmd, dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                                 **dict(POD_V4, **extra)), 5000 + s)
    return deck, c


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(ACTIVE))
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    from diagnostics.run_shared_code_shift import parse_cfg
    extra = next((parse_cfg(a.split("=", 1)[1]) for a in args
                  if a.startswith("--cfg=")), {})
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure,
                                       [(d, n, extra) for d in decks]))
    lines = [f"Answers on re-armed clocks (§0z136), POD_V4 {extra or ''}, "
             f"STAGED lists, "
             f"T20, N={n}, seeds 5000..{5000 + n - 1}", "",
             f"{'deck':11s} {'rearms':>7s} {'fresh':>7s} {'rd/rm':>6s} "
             f"{'moved0':>7s} {'rearmed':>8s} {'rd/rm':>6s} {'moved0':>7s} "
             f"{'share':>6s}",
             f"{'':11s} {'/game':>7s} {'/game':>7s} {'':>6s} {'':>7s} "
             f"{'/game':>8s} {'':>6s} {'':>7s} {'rearmd':>6s}"]
    for d in decks:
        c = res[d]
        f, r = c["fresh_removals"], c["rearmed_removals"]
        lines.append(
            f"{d:11s} {c['rearms'] / n:7.2f} {f / n:7.2f} "
            f"{c['fresh_moved'] / max(f, 1):6.2f} "
            f"{c['fresh_zero'] / max(f, 1):7.0%} {r / n:8.2f} "
            f"{c['rearmed_moved'] / max(r, 1):6.2f} "
            f"{c['rearmed_zero'] / max(r, 1):7.0%} "
            f"{r / max(f + r, 1):6.0%}")
    lines += ["", "rd/rm: rounds the kill moved per removal; moved0: the "
              "share of removals that moved it not at all; share rearmd: "
              "the removals that went to a re-armed route."]
    text = "\n".join(lines) + "\n"
    print(text)
    if out:
        with open(out, "w") as fh:
            fh.write(text)


if __name__ == "__main__":
    main()
