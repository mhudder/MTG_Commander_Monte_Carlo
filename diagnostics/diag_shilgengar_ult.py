#!/usr/bin/env python3
"""Shilgengar's own ability has never fired. Why, and what it is worth.

THE CLAIM UNDER TEST, which is a fact about the card and not about this model:

    Shilgengar, Sire of Famine  {3}{B}{B}  6/6 flying
      Sacrifice another creature: Create a Blood token. If you sacrificed an
      ANGEL this way, create a number of Blood tokens equal to ITS TOUGHNESS
      instead.
      {W/B}{W/B}{W/B}, Sacrifice six Blood tokens: Return each creature card
      from your graveyard to the battlefield with a finality counter on it.

The deck is half Angels. A 6-toughness Angel is the entire ultimate on its
own, and the ultimate RETURNS THE ANGEL YOU JUST SACRIFICED -- so the payment
is a loan, not a cost. `ablation_shilgengar.txt` was measured on an engine
where `blood_made` averaged 0.10 a game and the ultimate fired ZERO times in
3,000 games, because the sacrifice policy would only ever eat 1/1 Spirit
tokens and Spirits only exist once an Angel has already died. The namesake
ability was untested, not tested and found wanting.

This is the "when a result is surprising, the engine is the first suspect"
check for that row.

    python diag_shilgengar_ult.py [--n=4000] [--procs=N]

PART A  forced boards -- does the line fire, and does it correctly REFUSE?
PART B  real games: how often the ability assembles, and what it produces.
PART C  the policy and the mana reserve as separate paired CFG flips.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import shilgengar_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc import shilgengar as S

DECK, CMD = shilgengar_v1.build()
BY_NAME = {c.name: c for c in DECK}

OLD = {"shilgengar_sac_policy": "tokens"}
NEW = {"shilgengar_sac_policy": "ultimate"}


# ---------------------------------------------------------------------------
# PART A -- forced boards
# ---------------------------------------------------------------------------

def forced(creatures=(), yard=(), lands=4, blood=0, tokens=0,
           commander=True, flags=NEW, turns=20):
    """A hand-built battlefield, then ONE call to the real `activations()`.

    Drives the engine's own entry point rather than reimplementing the policy,
    so this diagnostic cannot drift from the code it is diagnosing -- the same
    rule `diag_time_sieve.py` follows.
    """
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)
    g = S.ShilgengarGame(DECK, CMD, cfg, 1)
    g.opening_hand()
    if commander:
        g.board.append(Permanent(card=CMD, sick=False,
                                 base_p=CMD.power, base_t=CMD.toughness))
        g.commander_cast = True
    for name in creatures:
        c = BY_NAME[name]
        g.make_permanent(c, sick=False)
    for _ in range(tokens):
        g.make_spirit_tokens(1)
    for p in g.board:
        p.sick = False
    for name in yard:
        g.graveyard.append(BY_NAME[name])
    for c in [x for x in DECK if x.is_land][:lands]:
        g.board.append(Permanent(card=c, sick=False))
    g.blood = blood
    g.activations()
    return g


CASES = [
    # label, kwargs, expected ults
    ("one 7-toughness Angel, a creature in the yard",
     dict(creatures=("Serra's Emissary",), yard=("Lyra Dawnbringer",)), 1),
    ("SAME BOARD, EMPTY GRAVEYARD -- must refuse, it is a pure shuffle",
     dict(creatures=("Serra's Emissary",), yard=()), 0),
    ("SAME BOARD, NO MANA -- must refuse BEFORE anything dies",
     dict(creatures=("Serra's Emissary",), yard=("Lyra Dawnbringer",),
          lands=0), 0),
    ("a 5-toughness Angel alone -- five Blood is not six",
     dict(creatures=("Lyra Dawnbringer",), yard=("Angel of Serenity",)), 0),
    ("the same Angel plus one Spirit token to top it up",
     dict(creatures=("Lyra Dawnbringer",), tokens=1,
          yard=("Angel of Serenity",)), 1),
    ("six non-Angels, one Blood each",
     dict(creatures=("Blood Artist", "Zulaport Cutthroat", "Viscera Seer",
                     "Grim Haruspex", "Midnight Reaper", "Cartel Aristocrat"),
          yard=("Lyra Dawnbringer",)), 1),
    ("Blood already banked, nothing needs to die",
     dict(creatures=(), yard=("Lyra Dawnbringer",), blood=6), 1),
    ("OLD POLICY, the board that fires under the new one",
     dict(creatures=("Serra's Emissary",), yard=("Lyra Dawnbringer",),
          flags=OLD), 0),
]


def part_a():
    print("=" * 78)
    print("PART A -- forced boards, one call to activations().")
    print("=" * 78)
    print("  Shilgengar and four lands on the battlefield unless stated.")
    print("  A check that cannot fail is worse than no check, so half of")
    print("  these cases assert the line REFUSES.\n")
    print(f"  {'':<58}{'ults':>6}{'fed':>5}{'blood':>7}{'back':>6}  ok")
    bad = 0
    for label, kw, want in CASES:
        g = forced(**kw)
        got = g.m["shilgengar_ults"]
        ok = got == want
        bad += not ok
        print(f"  {label:<58}{got:>6}{g.m['creatures_sacrificed']:>5}"
              f"{g.m['blood_made']:>7}{g.m['shilgengar_reanimated']:>6}"
              f"  {'.' if ok else 'FAIL'}")

    # The refusal that matters most is the mana one: `shilgengar_ultimate`
    # checks the mana too and returns early, so a plan that sacrifices first
    # and pays second would eat the Angels for none of the effect.
    g = forced(creatures=("Serra's Emissary",), yard=("Lyra Dawnbringer",),
               lands=0)
    if g.m["creatures_sacrificed"]:
        print("\n  FAIL: creatures died for an ultimate that was never cast")
        bad += 1

    # FINALITY COUNTERS, which is the check this whole line stands on. Without
    # them the engine plays a card the game does not print: sacrifice the
    # Angel, return it, sacrifice it again next turn, return it again, forever.
    #
    # Note what does NOT test this. Casting the ultimate twice in a row proves
    # nothing -- the creatures it returned are on the BATTLEFIELD and the
    # graveyard is empty, so the second cast has nothing to return whether
    # finality works or not. The loop has to be closed by FEEDING THE RETURNED
    # CARD BACK to Shilgengar, which is exactly what a pilot would do.
    g = forced(creatures=("Serra's Emissary",), yard=("Lyra Dawnbringer",))
    first = g.m["shilgengar_reanimated"]
    again = [p for p in g.board
             if p.card.name in ("Serra's Emissary", "Lyra Dawnbringer")]
    for p in again:
        g.sacrifice(p, to_shilgengar=True)      # straight back to the yard
    # Untap, or the second cast fails on the {3} and this reads as a passing
    # finality check when it is really a mana check -- which is exactly what
    # the first version of this test did.
    for p in g.board:
        p.tapped = False
    g.blood = 12
    g.shilgengar_ultimate()
    looped = g.m["shilgengar_reanimated"] - first
    if looped:
        print(f"\n  FAIL: finality counters ignored -- {first} creature(s) "
              f"returned, fed back to Shilgengar, and {looped} of them "
              f"returned a SECOND time. The line loops.")
        bad += 1
    else:
        print(f"\n  finality: {first} creature(s) returned once; fed back to "
              f"Shilgengar and with 12 Blood banked, none of them returns "
              f"again.")
    print(f"\n  {len(CASES)} cases, {bad} failing.\n")
    return bad


# ---------------------------------------------------------------------------
# PART B / C -- real games
# ---------------------------------------------------------------------------

_W = {}
OBS = ("won", "damage", "blood_made", "blood_spent", "creatures_sacrificed",
       "angels_fed", "cards_fed", "shilgengar_ults", "shilgengar_reanimated",
       "mana_floated", "stranded_mv", "final_board_power")


def _init(flags, turns):
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    r = S.simulate(DECK, CMD, _W["cfg"], seed)
    return [r[m] for m in OBS]


def observe(flags, n, turns, procs):
    with Pool(procs, initializer=_init, initargs=(flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def part_b(n, procs, turns=20):
    print("=" * 78)
    print(f"PART B -- real games, N = {n:,}, T{turns}, default pod.")
    print("=" * 78)
    print("  Per-game means. `ults` is the six-Blood mass reanimation.\n")
    print(f"  {'policy':<10}{'blood':>8}{'sacs':>7}{'angels fed':>12}"
          f"{'ults':>7}{'returned':>10}{'damage':>9}{'win':>8}")
    out = {}
    for label, flags in (("tokens", OLD), ("ultimate", NEW)):
        a = observe(flags, n, turns, procs)
        col = {m: a[:, i] for i, m in enumerate(OBS)}
        out[label] = col
        print(f"  {label:<10}{col['blood_made'].mean():>8.2f}"
              f"{col['creatures_sacrificed'].mean():>7.2f}"
              f"{col['angels_fed'].mean():>12.2f}"
              f"{col['shilgengar_ults'].mean():>7.2f}"
              f"{col['shilgengar_reanimated'].mean():>10.2f}"
              f"{col['damage'].mean():>9.1f}{col['won'].mean():>8.3f}")
    print()
    for label in ("tokens", "ultimate"):
        col = out[label]
        got = col["shilgengar_ults"] > 0
        if not got.sum():
            print(f"  {label}: the ultimate fires in 0 of {n:,} games.")
            continue
        print(f"  {label}: the ultimate fires in {int(got.sum()):,} of "
              f"{n:,} games ({got.mean():.1%}) -- "
              f"{col['shilgengar_reanimated'][got].mean():.2f} creatures "
              f"returned, win rate {col['won'][got].mean():.3f} vs "
              f"{col['won'][~got].mean():.3f} when it does not")
    print("\n  THAT LAST SPLIT IS SELECTION, NOT AN EFFECT SIZE. Firing the")
    print("  ultimate needs the commander alive, six Blood of fodder and {3}")
    print("  to spare, which are all things that are true in games you were")
    print("  already winning. PART C is the causal number.\n")


FLIPS = [
    ("the FODDER POLICY alone, with no mana held back for it",
     dict(OLD, shilgengar_ult_reserve=0),
     dict(NEW, shilgengar_ult_reserve=0)),
    ("the MANA RESERVE on top of it ({3} held through the main phase)",
     dict(NEW, shilgengar_ult_reserve=0), dict(NEW)),
    ("BOTH", dict(OLD), dict(NEW)),
]


def part_c(n, procs, turns=20):
    print("=" * 78)
    print(f"PART C -- policy and reserve as separate flips, N = {n:,}, T{turns}.")
    print("=" * 78)
    print("  Same deck, same seeds, flag off vs on, so common random numbers")
    print("  are intact and nothing but the flag differs. Applied")
    print("  CUMULATIVELY, so the two deltas add up to BOTH.\n")
    for label, off, on in FLIPS:
        a = observe(off, n, turns, procs)
        b = observe(on, n, turns, procs)
        print(f"  {label}")
        for i, m in enumerate(OBS):
            d = b[:, i] - a[:, i]
            hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
            if abs(d.mean()) < 1e-9 and hw < 1e-9:
                continue
            star = " *" if abs(d.mean()) > hw else "  "
            print(f"      {m:<22}{a[:, i].mean():>9.3f} ->"
                  f"{b[:, i].mean():>9.3f}   {d.mean():>+9.4f} "
                  f"+-{hw:<8.4f}{star}")
        print()


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 4000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    bad = part_a()
    part_b(n, procs)
    part_c(n, procs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
