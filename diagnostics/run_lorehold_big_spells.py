#!/usr/bin/env python3
"""The owner's second lorehold batch: seven big instants and sorceries.

    python -m diagnostics.run_lorehold_big_spells [N] [--procs=4]

Lorehold's STAGED list (`build_pending`), every leg played to T20 with a T10
snapshot (§0z93), so one run reports both horizons. All legs share seeds
80000.. -- candidates.py's -- so every difference below is PAIRED.

  PART 1  THE CANDIDATE ROWS: each card in Pinnacle Monk's slot against a
          blank of ITS cost (`candidates.blank_like`). The T20 rows ARE
          `python -m tools.candidates lorehold4 --n=15000`, printed beside it
          as a check on this script (§0z35).

  PART 2  THE KNOB, said out loud: Immolating Gyre at `gyre_full_x` 3 and 12
          against the default 6 -- how much of the row is the judgement.

  PART 3  THE OWNER'S COMPARISONS, measured rather than argued. Two cards in
          the SAME slot on the SAME seeds are a paired head-to-head (§0c,
          §0z35): Explosive Welcome minus Searing Wind ("a weaker Searing
          Wind"), Gideon's Phalanx minus Furygale Flocking ("weaker than
          Flocking usually"). And `-Reforge the Soul +Raphael's Technique`
          ("a weaker Reforge the Soul") as a real swap against the list.
          Profound Journey is NOT compared with Restoration Seminar: Seminar
          is KNOWN_BLIND here -- unimplemented -- so that difference would be
          Journey against a dead card.

  --h2h="A;B;C"  INSTEAD of the three parts above: REAL SWAPS on the
          tables' seeds (5000..), every contender the owner kept (Furygale
          Flocking, Profound Journey, Raphael's Technique, Immolating Gyre)
          in place of each named cut, against the staged list. The cuts the
          owner named on 2026-10-10: Verge Rangers, Lightning Greaves, Boros
          Charm. `--package="cut>add;cut>add"` adds one leg with ALL those
          swaps applied together, against the same base (§0p: staged changes
          can interact, and a set is measured as a set). `--package` alone
          runs the base and that one leg.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import lorehold_v17 as MOD
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.lorehold import simulate as sim
from edhmc.pending import build_pending
from tools.candidates import blank_like

MET = ("won", "damage", "mv_cheated", "cast_test_card", "miracles_cast",
       "spell_damage", "combat_damage", "cards_drawn",
       "furygale_tokens", "searing_wind_resolved", "welcome_resolved",
       "welcome_mana_added", "phalanx_knights", "phalanx_mastery",
       "wheel_casts", "gyre_resolved", "gyre_x", "gyre_pod_killed",
       "journey_returns", "rebound_casts", "turns_played")
CARDS = MOD.BATCH_2026_10_09_SPELLS
DECK, CMD = build_pending("lorehold")
for c in CARDS:
    if any(x.name == c.name for x in DECK):
        raise SystemExit(f"{c.name!r} is in lorehold's list (staged or "
                         f"committed); this script would measure a second copy. "
                         f"Furygale Flocking, Profound Journey and Immolating "
                         f"Gyre were staged 2026-10-10 after every run here: "
                         f"results/lorehold_big_spells_*.txt (§0z124). A "
                         f"re-measure is a run_ab against the list WITHOUT "
                         f"those Changes.")
VICTIM = "Pinnacle Monk"
SEED = 80000

LEGS = [("base", DECK, {}, frozenset())]
_blanks = {}
for c in CARDS:
    key = tuple(sorted(c.cost.items()))
    if key not in _blanks:
        _blanks[key] = f"blank {c.mv} {key}"
        LEGS.append((_blanks[key],
                     _swap_many(DECK, [VICTIM],
                                [blank_like(c, repl_priority(DECK), DECK)]),
                     {}, frozenset({c.name})))
    LEGS.append((c.name, _swap_many(DECK, [VICTIM], [c]), {},
                 frozenset({c.name})))
GYRE = MOD.IMMOLATING_GYRE
for x in (3, 12):
    LEGS.append((f"Gyre x{x}", _swap_many(DECK, [VICTIM], [GYRE]),
                 {"gyre_full_x": x}, frozenset({GYRE.name})))
RAPH = MOD.RAPHAELS_TECHNIQUE
LEGS.append(("-Reforge +Raphael", _swap_many(DECK, ["Reforge the Soul"], [RAPH]),
             {}, frozenset({RAPH.name})))


H2H = next((tuple(a.split("=", 1)[1].split(";")) for a in sys.argv[1:]
            if a.startswith("--h2h=")), ())
PACKAGE = next((tuple(tuple(x.split(">")) for x in a.split("=", 1)[1].split(";"))
                for a in sys.argv[1:] if a.startswith("--package=")), ())
if H2H or PACKAGE:
    KEPT = (MOD.FURYGALE_FLOCKING, MOD.PROFOUND_JOURNEY,
            MOD.RAPHAELS_TECHNIQUE, MOD.IMMOLATING_GYRE)
    SEED = 5000
    LEGS = [("base", DECK, {}, frozenset())]
    COMPARE_H2H = []
    for cut in H2H:
        for c in KEPT:
            leg = f"-{cut} +{c.name}"
            LEGS.append((leg, _swap_many(DECK, [cut], [c]), {},
                         frozenset({c.name})))
            COMPARE_H2H.append((f"H2H  {leg}", leg, "base"))
    if PACKAGE:
        by = {c.name: c for c in MOD.BATCH_2026_10_09_SPELLS}
        leg = "PACKAGE " + ", ".join(f"-{c} +{a}" for c, a in PACKAGE)
        LEGS.append((leg, _swap_many(DECK, [c for c, _ in PACKAGE],
                                     [by[a] for _, a in PACKAGE]),
                     {}, frozenset(a for _, a in PACKAGE)))
        COMPARE_H2H.append((leg, leg, "base"))


def blank_of(card):
    return _blanks[tuple(sorted(card.cost.items()))]


COMPARE = [] if (H2H or PACKAGE) else [
    (f"PART 1  {c.name} (vs blank, Monk's slot)", c.name, blank_of(c))
    for c in CARDS]
COMPARE += COMPARE_H2H if (H2H or PACKAGE) else [
    ("PART 2  Gyre, gyre_full_x 3  (vs blank)", "Gyre x3", blank_of(GYRE)),
    ("PART 2  Gyre, gyre_full_x 12 (vs blank)", "Gyre x12", blank_of(GYRE)),
    ("PART 3  Explosive Welcome - Searing Wind (same slot)",
     "Explosive Welcome", "Searing Wind"),
    ("PART 3  Gideon's Phalanx - Furygale Flocking (same slot)",
     "Gideon's Phalanx", "Furygale Flocking"),
    ("PART 3  -Reforge the Soul +Raphael's Technique (real swap)",
     "-Reforge +Raphael", "base"),
]


def job(j):
    out = []
    for _leg, deck, over, watch in LEGS:
        cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), watch=watch,
                   **over)
        r = sim(list(deck), CMD, cfg, SEED + j)
        t10 = r["at_rounds"][10]
        out.append([[float(t10.get(m, 0) or 0) for m in MET],
                    [float(r.get(m, 0) or 0) for m in MET]])
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 15000
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), 4)
    with Pool(procs) as p:
        rows = np.array(p.map(job, range(n), chunksize=50), float)
    # rows: (n, legs, horizon, metric)
    idx = {leg[0]: i for i, leg in enumerate(LEGS)}
    if H2H or PACKAGE:
        print("REAL SWAPS against the staged list, the tables' seeds.")
    print(f"Lorehold's second 2026-10-09 batch, staged list, N = {n:,} paired "
          f"games per comparison, seeds {SEED}.., 95% CIs. '*' = outside its "
          f"bar.\n")
    for label, b, a in COMPARE:
        print(label)
        for h, t in ((0, 10), (1, 20)):
            d = rows[:, idx[b], h, :] - rows[:, idx[a], h, :]
            cells = []
            for k, m in enumerate(MET):
                if m == "cast_test_card":
                    continue
                x = d[:, k]
                mu, hw = x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(n)
                if m != "won" and abs(mu) < 5e-4 and hw < 5e-4:
                    continue                      # a counter nobody moved
                w = 4 if m == "won" else 2
                cells.append(f"{m} {mu:+.{w}f}+-{hw:.{w}f}"
                             f"{'*' if abs(mu) > hw else ''}")
            print(f"  T{t}: " + "  ".join(cells[:4]))
            for i in range(4, len(cells), 4):
                print("        " + "  ".join(cells[i:i + 4]))
        legs_b = rows[:, idx[b], 1, :]
        print(f"  P(cast) {legs_b[:, MET.index('cast_test_card')].mean():.3f}"
              f"   leg won at T20 {legs_b[:, 0].mean():.4f}\n")


if __name__ == "__main__":
    main()
