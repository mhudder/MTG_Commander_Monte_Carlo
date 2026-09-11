#!/usr/bin/env python3
"""The two staged Lorehold changes, measured TOGETHER. Closes queued item 0b.

    -Penance     +Caldera Pyremaw      staged 2026-09-05, +0.0202 win at T20
    -Scroll Rack +Sunbird's Invocation  staged 2026-09-04, +0.0215 win at T20

WHY THIS IS NOT JUST "RUN BOTH AND SEE". Each was measured against the v16 list,
never against the other, and the reason to doubt that they add is mechanical
rather than statistical:

  * Both are ADDITIONS TO THE SAME CURVE. Sunbird's Invocation is MV 6 and
    Caldera Pyremaw MV 5, replacing a two-drop and a free spell. Sunbird's alone
    already costs +4.28 stranded MV -- mana value sitting uncastable in hand --
    and stranding is exactly the cost that compounds when you do it twice.
  * Both are CAST TRIGGERS competing for the same spells. Sunbird's fires on
    each spell you cast from hand; Caldera pings an opponent on each instant or
    sorcery you cast. Neither consumes the other's trigger, but they are paid for
    out of one mana pool and one draw step.
  * BOTH CUTS ARE TOP-SETTERS. Penance and Scroll Rack both put a card on top of
    your library to miracle, and the standing finding is that the top-setter
    package raises `mv_cheated` and LOSES GAMES. Cutting two of them at once
    could easily be worth more than the sum, in the other direction.

So the question is the INTERACTION, and a difference of two differences needs its
own design. This is a 2x2 factorial on common random numbers -- all four legs
shuffled on the same seed -- which makes the interaction a paired quantity too:

    A   = v16 as printed              (neither change)
    C   = -Penance +Caldera Pyremaw   (Caldera only)
    S   = -Scroll Rack +Sunbird's     (Sunbird's only)
    CS  = both

    main effects        C-A, S-A, CS-A
    INTERACTION         CS - C - S + A     <- zero means they add
    marginal value      CS-S  (Caldera, given Sunbird's is already in)
                        CS-C  (Sunbird's, given Caldera is already in)

The marginal pair is what the decision actually rests on: if you are going to
make one of them, is the second still worth a slot?

N DEFAULTS TO 30,000, twice the tables. An interaction is a difference of
differences, so its variance is roughly twice a main effect's, and the effects
being argued about here are 0.003-0.02. 15,000 would resolve the main effects
(median lorehold bar 0.0034) and leave the interaction ambiguous, which is the
one number this script exists to produce.

PART 2 asks a follow-up the factorial raises: what are the two CUT TARGETS worth
on today's engine? Both Penance and Scroll Rack are in `lorehold.TOP_SETTERS`,
and the 2026-09-05 top-setter POLICY fixes made top-setters materially better
(Library of Leng: miracled 43% -> 80%, deck win 0.205 -> 0.219). If a staged swap
that CUTS one has decayed since it was measured, that is the obvious mechanism --
and it is measurable rather than a story, so it is measured.

    python run_lorehold_pair.py [--n 30000] [--procs 16]
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import lorehold_v16 as MOD
from edhmc.engine import Card
from edhmc.lorehold import simulate as lh_sim
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority

BASE_SEED = 5000            # the ablation tables' seed base
CHANGES = {
    "C": ("Penance", "CALDERA_PYREMAW"),
    "S": ("Scroll Rack", "SUNBIRDS_INVOCATION"),
}
LEGS = ("A", "C", "S", "CS")
METRICS = ("won", "damage", "mv_cheated", "stranded_mv", "miracles_cast",
           "cards_drawn", "sunbird_casts", "sunbird_mv", "pyremaw_damage",
           "turns_played")

_W = {}


def build_leg(leg):
    deck, cmd = MOD.build()
    outs, ins = [], []
    for key in ("C", "S"):
        if key in leg:
            out, const = CHANGES[key]
            outs.append(out)
            ins.append(getattr(MOD, const))
    if outs:
        deck = _swap_many(deck, outs, ins)
    assert len(deck) + 1 == 100, f"{leg}: {len(deck) + 1} cards"
    names = [c.name for c in deck] + [cmd.name]
    dups = {n for n in names if n not in
            ("Mountain", "Plains", "Forest", "Swamp", "Island", "Wastes")
            and names.count(n) > 1}
    assert not dups, f"{leg}: singleton violation {dups}"
    return deck, cmd


def _init(turns):
    _W["legs"] = {leg: build_leg(leg) for leg in LEGS}
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns,
                     watch=frozenset({"Caldera Pyremaw",
                                      "Sunbird's Invocation"}))


def _one(seed):
    """All four legs on ONE seed. That is what makes the interaction paired."""
    out = []
    for leg in LEGS:
        deck, cmd = _W["legs"][leg]
        r = lh_sim(deck, cmd, _W["cfg"], seed)
        out.append([r[m] for m in METRICS])
    return out


def measure(turns, n, procs):
    with Pool(procs, initializer=_init, initargs=(turns,)) as pool:
        rows = pool.map(_one, range(BASE_SEED, BASE_SEED + n), chunksize=64)
    a = np.array(rows, float)          # (n, 4 legs, len(METRICS))
    return {leg: a[:, i, :] for i, leg in enumerate(LEGS)}


def ci(d):
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def row(label, d, i, width=6):
    m, hw = ci(d[:, i])
    star = " *" if abs(m) > hw else "  "
    return f"    {label:<34}{m:>+11.{width}f} +-{hw:<10.{width}f}{star}"


# ---------------------------------------------------------------------------
# PART 2 -- what are the CUT TARGETS worth on today's engine?
# ---------------------------------------------------------------------------

CUTS = ("Scroll Rack", "Penance")
CUT_M = ("won", "damage", "settop_placed", "settop_miracled", "miracles_cast")


def blank_like(card, priority):
    """ablation.py's blank, so this lands on the tables' scale (KNOWN_ISSUES 0j)."""
    if card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0, priority=priority)


def _init_cut(name, turns):
    deck, cmd = MOD.build()            # v16 AS PRINTED: both cut targets present
    card = next(c for c in deck if c.name == name)
    _W["a"] = deck
    _W["b"] = _swap_many(deck, [name], [blank_like(card, repl_priority(deck))])
    _W["cmd"] = cmd
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset({name}))


def _cut_pair(seed):
    ra = lh_sim(_W["a"], _W["cmd"], _W["cfg"], seed)
    rb = lh_sim(_W["b"], _W["cmd"], _W["cfg"], seed)
    return [ra[m] for m in CUT_M] + [rb[m] for m in CUT_M]


def part2(n, procs):
    print("=" * 78)
    print(f"PART 2 -- what the CUT TARGETS are worth, v16 as printed, N = {n:,}")
    print("=" * 78)
    print("  Real minus blank, so POSITIVE means the card is worth that much and")
    print("  cutting it costs that much. Same blank as ablation.py, so this is on")
    print("  the tables' scale.")
    print("  For reference, the 2026-09-04 table had Scroll Rack at -0.0100 win /")
    print("  -1.78 damage, which is what made it 'the deck's worst")
    print("  model-evaluated non-wipe card' and therefore the cut.\n")
    print(f"  {'card':<16}{'T':>4}{'win rate':>21}{'damage':>17}"
          f"{'settop placed':>17}{'settop miracled':>18}")
    for name in CUTS:
        for turns in (10, 20):
            with Pool(procs, initializer=_init_cut,
                      initargs=(name, turns)) as pool:
                rows = np.array(pool.map(_cut_pair,
                                         range(BASE_SEED, BASE_SEED + n),
                                         chunksize=64), float)
            k = len(CUT_M)
            d = rows[:, :k] - rows[:, k:]
            cells = []
            for m in ("won", "damage", "settop_placed", "settop_miracled"):
                j = CUT_M.index(m)
                mean, hw = ci(d[:, j])
                w = 4 if m == "won" else 2
                cells.append(f"{mean:+.{w}f}+-{hw:.{w}f}"
                             f"{'*' if abs(mean) > hw else ' '}")
            print(f"  {name:<16}{turns:>4}{cells[0]:>21}{cells[1]:>17}"
                  f"{cells[2]:>17}{cells[3]:>18}")
    print()


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 30000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)

    print(f"Two staged Lorehold changes, 2x2 factorial on common random "
          f"numbers.")
    print(f"N = {n:,} paired games per cell, seeds {BASE_SEED}.."
          f"{BASE_SEED + n - 1}, all four legs on the same seed.")
    print(f"Baseline A is lorehold_v16 AS PRINTED -- neither staged change.\n")
    print("  C  = -Penance +Caldera Pyremaw        (staged 2026-09-05)")
    print("  S  = -Scroll Rack +Sunbird's Invocation (staged 2026-09-04)\n")

    for turns in (10, 20):
        L = measure(turns, n, procs)
        A, C, S, CS = L["A"], L["C"], L["S"], L["CS"]
        print("=" * 78)
        print(f"T{turns}")
        print("=" * 78)
        for i, m in enumerate(METRICS):
            w = 6 if m == "won" else 3
            print(f"  {m}   (baseline A = {A[:, i].mean():.{w}f})")
            print(row("C alone", C - A, i, w))
            print(row("S alone", S - A, i, w))
            print(row("BOTH (CS - A)", CS - A, i, w))
            print(row("INTERACTION  CS-C-S+A", CS - C - S + A, i, w))
            print(row("Caldera GIVEN Sunbird's  CS-S", CS - S, i, w))
            print(row("Sunbird's GIVEN Caldera  CS-C", CS - C, i, w))
        print()
    print("* = 95% CI excludes zero. Win rate is the objective; damage and "
          "mv_cheated are proxies,")
    print("and this deck's own standing finding is that mv_cheated and win rate "
          "have pointed in")
    print("opposite directions for the top-setter cards THAT THESE TWO CHANGES "
          "CUT. Follow win rate.")
    print()
    part2(min(n, 15000), procs)


if __name__ == "__main__":
    main()
