#!/usr/bin/env python3
"""Re-measure Goldspan Dragon. Closes queued work item 0c.

WHY IT NEEDED RE-MEASURING. It was passed on 2026-09-04 at +0.0025 +-0.0045 win
rate, and two separate things were wrong with that number:

  1. `tag_flying.py` walked `mod.build()` only, and `flying=name in FLYING` is
     evaluated at import, so module-level CANDIDATES were all constructed as
     ground creatures. Goldspan Dragon is a 4/4 FLIER with haste and was
     measured as a 4/4 ground creature (KNOWN_ISSUES.md 0c). Fixed 2026-09-05.
     The same bug understated Caldera Pyremaw, which then won the five-drop
     slot -- so this is not a hypothetical correction.
  2. The ablation blank was built at `priority=0.5`, below the minimum priority
     of every deck, so it was never cast and the candidate was charged the whole
     tempo difference (KNOWN_ISSUES.md 0j). Fixed 2026-09-06.

And the bar was the real problem: +-0.0045 at N=6000 cannot resolve an effect of
0.0025. This runs N=15,000, whose median bar on the lorehold table is 0.0034,
and reports THREE horizons -- 14 because that is what the original number used,
10 and 20 because that is what `ablation_lorehold.txt` uses and therefore the
only scale on which "is it better than the card you would cut" can be asked.

    python run_goldspan.py [--n 15000] [--procs 16]

Method is `candidates.py`'s exactly: the victim slot is blanked in BOTH legs, so
its identity does not bias the comparison, and the blank comes from
`experiment.repl_priority()` so this lands on the same scale as the tables.
Baseline is `build_pending("lorehold")`, which is what `ablation.py` uses, so it
carries BOTH staged Lorehold changes (-Penance +Caldera Pyremaw, -Scroll Rack
+Sunbird's Invocation). That is a different baseline from the 2026-09-04 run,
which predated the Caldera staging -- said out loud because it is the one thing
here that is not an apples-to-apples improvement on the old number.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.engine import Card
from edhmc.lorehold import simulate as lh_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.decks.lorehold_v16 import GOLDSPAN_DRAGON, CALDERA_PYREMAW

VICTIM = "Pinnacle Monk"          # same slot candidates.py used
BASE_SEED = 80000                 # same seeds candidates.py used
HORIZONS = (10, 14, 20)
METRICS = ("won", "damage", "mv_cheated", "cards_drawn", "treasures_made",
           "final_board_power")

_W = {}


def blank_like(card, priority):
    """Must stay identical to ablation.py / candidates.py -- see KNOWN_ISSUES 0j."""
    if card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0, priority=priority)


def _resolve(cand_name):
    """`Name` or `Name@priority`.

    The priority override exists because Goldspan Dragon and Caldera Pyremaw are
    the same cost ({3}{R}{R}), the same threat (8.5) and the same slot, and
    differ by one hand-set knob: priority 8 against 8.5. `main_phase` is greedy
    on priority, so that knob and not the card could be most of the gap in
    P(deploy). Measuring at matched priority is what separates the two.
    """
    base, _, pri = cand_name.partition("@")
    cand = {"Goldspan Dragon": GOLDSPAN_DRAGON,
            "Caldera Pyremaw": CALDERA_PYREMAW}[base]
    if pri:
        from dataclasses import replace
        cand = replace(cand, priority=float(pri))
    return cand


def _init(cand_name, turns):
    deck, cmd = build_pending("lorehold")
    cand = _resolve(cand_name)
    # See the same guard in candidates.py. Caldera Pyremaw was measured here
    # once as a control and the number was MEANINGLESS: it is already in the
    # staged list, so the run put a second copy in the victim slot and measured
    # a duplicate in a singleton-illegal deck. That row is why this check
    # exists; do not re-add it.
    if any(c.name == cand.name for c in deck):
        raise SystemExit(
            f"{cand.name!r} is already in the staged lorehold list, so it "
            f"cannot be measured as an ADDITION -- the run would put a second "
            f"copy in the victim slot. Measure it as a swap instead.")
    pri = repl_priority(deck)
    _W["a"] = _swap_many(deck, [VICTIM], [blank_like(cand, pri)])
    _W["b"] = _swap_many(deck, [VICTIM], [cand])
    _W["cmd"] = cmd
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns,
                     watch=frozenset({cand.name}))


def _pair(seed):
    ra = lh_sim(_W["a"], _W["cmd"], _W["cfg"], seed)
    rb = lh_sim(_W["b"], _W["cmd"], _W["cfg"], seed)
    return ([ra[m] for m in METRICS] + [ra["cast_test_card"]],
            [rb[m] for m in METRICS] + [rb["cast_test_card"]])


def measure(cand_name, turns, n, procs):
    with Pool(procs, initializer=_init, initargs=(cand_name, turns)) as pool:
        rows = pool.map(_pair, range(BASE_SEED, BASE_SEED + n), chunksize=64)
    a = np.array([r[0] for r in rows], float)
    b = np.array([r[1] for r in rows], float)
    d = b - a
    out = {}
    for i, m in enumerate(METRICS):
        out[m] = (d[:, i].mean(),
                  1.96 * d[:, i].std(ddof=1) / np.sqrt(n))
    out["deploy"] = b[:, len(METRICS)].mean()
    return out


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    cands = [a for a in args if not a.startswith("--")] or ["Goldspan Dragon"]

    print(f"Value over a replacement-level blank of the same cost. "
          f"N = {n:,} paired games, seeds {BASE_SEED}..{BASE_SEED + n - 1}.")
    print(f"Baseline build_pending('lorehold'); victim slot {VICTIM!r} is "
          f"blanked in both legs.\n")
    for cand_name in cands:
        c = _resolve(cand_name)
        print(f"{cand_name}   (MV {c.mv}, priority {c.priority}, "
              f"threat {c.threat}, {c.power}/{c.toughness}"
              f"{', flying' if c.flying else ''})")
        head = f"  {'T':>3}"
        for m in METRICS:
            head += f"{m:>22}"
        print(head + f"{'P(deploy)':>11}")
        for turns in HORIZONS:
            r = measure(cand_name, turns, n, procs)
            line = f"  {turns:>3}"
            for m in METRICS:
                mean, hw = r[m]
                star = "*" if abs(mean) > hw else " "
                fmt = "%+.4f+-%.4f" % (mean, hw) if m == "won" \
                    else "%+.2f+-%.2f" % (mean, hw)
                line += f"{fmt:>21}{star}"
            print(line + f"{r['deploy']:>11.3f}")
        print()
    print("* = 95% CI excludes zero.  Win rate is the objective; damage and "
          "mv_cheated are proxies.")


if __name__ == "__main__":
    main()
