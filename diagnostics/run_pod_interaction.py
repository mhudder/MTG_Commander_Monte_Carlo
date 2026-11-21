#!/usr/bin/env python3
"""How much of the pod's interaction reaches the table, per game (§0z242).

    python -m diagnostics.run_pod_interaction [--n=2000] [--out=PATH]

For queue item 50's flip (decision 5, §0z234): the pod's spot removal, A/E
removal, wipes and counterspells CAST, whole pod, per game -- in all and on
pod turns 3-10, the window `BRACKETS`' header states its target in ("roughly
4 spot removal spells and ~1 board wipe reaching the table per game") --
under two pods, each deck's staged list, seeds 5000..:

  today    `pod_mana` alone: every cast is charged and nothing is gated, so
           the counts are the pod every table runs (§0z237: bit-identical)
  mana     every item-50 switch on: the pod the flip would run, before the
           rates are scaled back

A cast is a call to `opponents.pod_spend` for that kind, counted by a spy
installed in each worker (§0u: a monkeypatch in the parent does not reach a
fresh worker); a removal the gates stop is never charged, so is not
counted. Each kind's charge is one cast whatever it costs.
"""
import sys
from collections import defaultdict
from multiprocessing import Pool

KINDS = ("spot", "ae", "wipe", "counter")
PODS = {
    "today": dict(pod_mana=True),
    "mana": dict(pod_mana=True, pod_answer_mana=True, pod_tax_mana=True,
                 pod_removal_mana=True, pod_gifts=True),
}
WINDOW = range(3, 11)
TALLY = None


def _init():
    global TALLY
    import edhmc.opponents as O
    real = O.pod_spend
    TALLY = defaultdict(float)

    def spy(g, o, amount, what, floor=0.0):
        if what in KINDS and o is not None and amount > 0 \
                and O.pod_mana_on(g):
            t = O.pod_turn(g)
            TALLY[(what, "all")] += 1
            if t in WINDOW:
                TALLY[(what, "3-10")] += 1
            TALLY[(what, t)] += 1
        return real(g, o, amount, what, floor)
    O.pod_spend = spy


def _play(job):
    deck_name, pod, seeds = job
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    deck, cmd = build_pending(deck_name)
    sim = DECKS[deck_name].sim
    TALLY.clear()
    turns = 0.0
    for s in seeds:
        r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                                watch=frozenset(), **PODS[pod]), 5000 + s)
        turns += r["turns_played"]
    return dict(TALLY), turns


def main() -> int:
    opts = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[1:]
            if "=" in a}
    n = int(opts.get("--n", 2000))
    out_path = opts.get("--out", "results/pod_interaction.txt")
    from edhmc.registry import ACTIVE
    lines = [f"the pod's interaction CAST per game, whole pod, N={n} a deck "
             f"and pod, seeds 5000..{5000 + n - 1}; 'today' is pod_mana "
             "alone (the pod every table runs), 'mana' every item-50 switch",
             "", f"{'deck':<11} {'pod':<6} {'turns':>5}  "
             + "  ".join(f"{k + ' all':>9} {k + ' 3-10':>9}" for k in KINDS)]
    grand = {p: defaultdict(float) for p in PODS}
    with Pool(4, initializer=_init) as pool:
        for deck in ACTIVE:
            for pod in PODS:
                parts = pool.map(_play, [(deck, pod, list(range(i, n, 16)))
                                         for i in range(16)])
                tally, turns = defaultdict(float), 0.0
                for t, tp in parts:
                    turns += tp
                    for k, v in t.items():
                        tally[k] += v
                for k, v in tally.items():
                    grand[pod][k] += v
                lines.append(
                    f"{deck:<11} {pod:<6} {turns / n:5.2f}  "
                    + "  ".join(f"{tally[(k, 'all')] / n:9.2f} "
                                f"{tally[(k, '3-10')] / n:9.2f}"
                                for k in KINDS))
                print(lines[-1], flush=True)
    d = len(ACTIVE) * n
    lines += ["", "every deck together, per game:"]
    for pod in PODS:
        lines.append(f"  {pod:<6} " + "  ".join(
            f"{k} {grand[pod][(k, 'all')] / d:.2f} "
            f"({grand[pod][(k, '3-10')] / d:.2f} in 3-10)" for k in KINDS))
    lines += ["", "by pod turn, every deck together (cast per game):"]
    for pod in PODS:
        for k in KINDS:
            lines.append(f"  {pod:<6} {k:<8}" + " ".join(
                f"{grand[pod][(k, t)] / d:5.2f}" for t in range(1, 15)))
    lines.append("           (pod turns 1..14)")
    text = "\n".join(lines)
    print(text)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
