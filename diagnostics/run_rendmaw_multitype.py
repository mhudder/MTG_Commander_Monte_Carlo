#!/usr/bin/env python3
"""The owner's multi-type batch for rendmaw (§0z125).

    python -m diagnostics.run_rendmaw_multitype [N] [--procs=4]

Rendmaw's STAGED list (`build_pending`), every leg played to T20 with a T10
snapshot (§0z93), so one run reports both horizons. All legs share seeds
80000.. -- candidates.py's -- so every difference below is PAIRED.

  PART 1  THE CANDIDATE ROWS: each card in Pygmy Kavu's slot against a blank
          of ITS cost (`candidates.blank_like`, a SINGLE-type blank). The T20
          rows ARE `python -m tools.candidates rendmaw3 --n=15000`, as a check
          on this script (§0z35).

  PART 2  WHAT THE TYPE LINE IS WORTH. Each card against ITSELF with its type
          line cut to "Creature", same slot, same seeds: the difference is
          everything two card types buy here -- the Rendmaw trigger on every
          cast, and the artifact half (Foundry Inspector's discount, Steel
          Overseer's counters, Junk Diver / Myr Retriever / Scrap Trawler).
          It is the question the owner's search was built on, measured.

  PART 3  WICKERFOLK'S CLAUSE, and its knob said out loud: the card with its
          graveyard cast off (`wickerfolk_gy=False`), and with the life floor
          at 6 and 14 against the default 10.
"""
import sys
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

from edhmc.decks import rendmaw_v12 as MOD
from edhmc.engine import simulate as sim
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.pending import build_pending
from tools.candidates import blank_like

MET = ("won", "damage", "cast_test_card", "rendmaw_triggers", "tokens_made",
       "cards_drawn", "drain_damage", "herbie_surveils", "herbie_binned",
       "swarmweaver_insects", "swarmweaver_pumped", "wickerfolk_gy_casts",
       "wickerfolk_life_paid", "boulders_made", "boulders_sacrificed",
       "myriad_copies", "final_life", "turns_played")
CARDS = MOD.BATCH_2026_10_10
DECK, CMD = build_pending("rendmaw")
for c in CARDS:
    if any(x.name == c.name for x in DECK):
        raise SystemExit(f"{c.name!r} is in rendmaw's list (staged or "
                         f"committed); this script would measure a second copy.")
VICTIM = "Pygmy Kavu"
SEED = 80000

LEGS = []
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
    # The same card, one card type. `replace` builds a NEW Card (a fresh
    # object, §0z112) with every other field -- cost, body, priority, threat,
    # script, mana -- the card's own.
    single = replace(c, types=frozenset({"Creature"}))
    LEGS.append((f"{c.name} [Creature only]", _swap_many(DECK, [VICTIM], [single]),
                 {}, frozenset({c.name})))
WICK = MOD.WICKERFOLK_INDOMITABLE
LEGS.append(("Wickerfolk, no graveyard cast", _swap_many(DECK, [VICTIM], [WICK]),
             {"wickerfolk_gy": False}, frozenset({WICK.name})))
for floor in (6, 14):
    LEGS.append((f"Wickerfolk, floor {floor}", _swap_many(DECK, [VICTIM], [WICK]),
                 {"wickerfolk_life_floor": floor}, frozenset({WICK.name})))


def blank_of(card):
    return _blanks[tuple(sorted(card.cost.items()))]


COMPARE = [(f"PART 1  {c.name} (vs blank, Kavu's slot)", c.name, blank_of(c))
           for c in CARDS]
COMPARE += [(f"PART 2  {c.name}: its type line (vs itself as a Creature)",
             c.name, f"{c.name} [Creature only]") for c in CARDS]
COMPARE += [
    ("PART 3  Wickerfolk: the graveyard cast (vs the card without it)",
     WICK.name, "Wickerfolk, no graveyard cast"),
    ("PART 3  Wickerfolk, life floor 6 (vs blank)", "Wickerfolk, floor 6",
     blank_of(WICK)),
    ("PART 3  Wickerfolk, life floor 14 (vs blank)", "Wickerfolk, floor 14",
     blank_of(WICK)),
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
    print(f"Rendmaw's multi-type batch (§0z125), staged list, N = {n:,} paired "
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
