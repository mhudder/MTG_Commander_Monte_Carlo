#!/usr/bin/env python3
"""Item 24, change 3: what holding mana up through the pod's turn is worth
(§0z134), and what the cards that use it are now worth.

    python -m diagnostics.run_pod_responses                 # N=2000
    python -m diagnostics.run_pod_responses --n=500 --decks=tivit

Per deck, on today's pod and on `experiment.POD_V4`, the staged list paired
on seeds 5000.. against the same pod without responses:

    leftover   pod_responses=True: held cards cast from what the main phase
               left untapped (the default reserve)
    hold       ... response_reserve="hold": the main phase keeps the
               cheapest held response castable (§0t is why both are run)
    blanked    ... leftover, with every RESPONSE CARD blanked together: the
               pure responses (counterspells, protection spells) and the
               instant answers. `leftover - blanked` is what those cards are
               worth with responses on -- leave-one-out is blind to
               redundancy (§0z27), so they go together

Reported: win rate at T10 and T20, and the response counters (`responses_*`).
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import ACTIVE, DECKS as REGISTRY

N = 2000
ARMS = ("off", "leftover", "hold", "blanked")
COUNTERS = ("responses_protect", "responses_counter_removal",
            "responses_counter_piece", "responses_answer_piece",
            "responses_end_step")


def response_cards(deck):
    """The cards change 3 casts on the pod's turn: counterspells, protection
    spells with nothing else modelled, and instant answers -- read off the
    card, not an engine's `protection_cards` (every protection card in the
    lists is in its engine's list, or none is in the deck)."""
    from edhmc import opponents as OPP
    from edhmc.decks import _removal

    def pure(c):
        return (c.name in _removal.COUNTERS
                or (c.name in OPP.PROTECTION
                    and all(not getattr(c, f, None)
                            for f in OPP._PURE_FIELDS)))
    return {c.name for c in deck
            if pure(c) or ("Instant" in c.types and c.name in OPP.ANSWERS
                           and "wipe" not in c.tags)}


def measure(args):
    deck_name, pod, arm, n = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG, POD_V4, repl_priority
    from tools.ablation import blank_like
    deck, cmd = build_pending(deck_name)
    sim = REGISTRY[deck_name].sim
    extra = dict(POD_V4) if pod == "POD_V4" else {}
    if arm != "off":
        extra["pod_responses"] = True
    if arm == "hold":
        extra["response_reserve"] = "hold"
    if arm == "blanked":
        sim_cfg_names = response_cards(deck)
        pri = repl_priority(deck)
        deck = [blank_like(c, pri) if c.name in sim_cfg_names else c
                for c in deck]
    w10, w20, cnt = [], [], {k: 0.0 for k in COUNTERS}
    for s in range(n):
        r = sim(deck, cmd, dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
                                watch=frozenset(), **extra), 5000 + s)
        w10.append(float(r["at_rounds"][10]["won"]))
        w20.append(float(r["won"]))
        for k in COUNTERS:
            cnt[k] += float(r.get(k, 0)) / n
    return (deck_name, pod, arm), (np.array(w10), np.array(w20), cnt)


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(ACTIVE))
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    pods = ("today", "POD_V4")
    jobs = [(d, p, a, n) for d in decks for p in pods for a in ARMS]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    lines = [f"pod_responses (item 24, change 3), STAGED lists, N={n} paired, "
             f"seeds 5000..{5000 + n - 1}", ""]
    for d in decks:
        for p in pods:
            base = res[(d, p, "off")]
            lines.append(f"{d} on {p}: off won T10 {base[0].mean():.4f} "
                         f"T20 {base[1].mean():.4f}")
            for arm, ref, label in (("leftover", "off", "responses, leftover"),
                                    ("hold", "off", "responses, hold"),
                                    ("leftover", "blanked",
                                     "response cards worth")):
                a, b = res[(d, p, arm)], res[(d, p, ref)]
                cells = []
                for k, t in ((0, 10), (1, 20)):
                    dd = a[k] - b[k]
                    hw = 1.96 * dd.std(ddof=1) / np.sqrt(len(dd))
                    star = "*" if hw > 0 and abs(dd.mean()) > hw else " "
                    cells.append(f"T{t} {dd.mean():+.4f} ±{hw:.4f}{star}")
                lines.append(f"   {label:<22}" + "   ".join(cells))
            mech = "  ".join(f"{k.replace('responses_', '')} {v:.2f}"
                             for k, v in res[(d, p, "leftover")][2].items())
            lines.append(f"   {'per game (leftover)':<22}{mech}")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if out:
        open(out, "w").write(text + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
