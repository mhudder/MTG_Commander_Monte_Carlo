#!/usr/bin/env python3
"""Is holding mana back for a later ability worth what it costs?

Two engines decline to spend mana in their main phase so that a LATER ability
is affordable, and both numbers were picked to match a printed cost rather
than measured:

    lorehold    `miracle_reserve` = 2, held through BOTH main phases, for the
                three miracle windows on the opponents' upkeeps.
    shilgengar  `shilgengar_ult_reserve` = 3, held through the one main phase
                before `activations()`, for the six-Blood ultimate.

CLAUDE.md's standing claim is "raising `miracle_reserve` above 2 makes it
worse -- the default is right." That is evidence about RAISING it. Nobody had
lowered it, and nobody had tried holding the amount actually needed rather
than a constant.

THE ASYMMETRY THAT MAKES THIS WORTH ASKING PER ENGINE. Shilgengar's reserve is
spent or released within the same turn -- `activations()` runs before the
postcombat main phase, which is passed no reserve at all. Lorehold's is held
through the whole turn AND the windows it is held for open only after
`opponents_act`, so a commander answered in between takes them with it. The
held mana is exposed to removal in one engine and not the other.

    python run_reserve_sweep.py [--n=15000] [--procs=N]

PART A  what the reserve actually buys, per turn it is held.
PART B  lorehold: every reserve value against the default, paired.
PART C  shilgengar: the same, plus the gate that decides when to hold at all.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import lorehold_v16, shilgengar_v1
from edhmc.experiment import DEFAULT_CFG
from edhmc import lorehold as L
from edhmc import shilgengar as S

L_DECK, L_CMD = lorehold_v16.build()
S_DECK, S_CMD = shilgengar_v1.build()

L_OBS = ("won", "mv_cheated", "miracles_cast", "damage", "spells_cast",
         "mana_floated", "stranded_mv", "reserve_turns", "reserve_held",
         "reserve_overheld", "reserve_unused_turns", "reserve_wasted",
         "reserve_lost_commander", "turns_played")
S_OBS = ("won", "damage", "shilgengar_ults", "shilgengar_reanimated",
         "blood_made", "blood_spent", "angels_fed", "mana_floated",
         "stranded_mv", "turns_played")

_W = {}


def _init(which, flags, turns):
    _W["which"] = which
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    if _W["which"] == "lorehold":
        r = L.simulate(L_DECK, L_CMD, _W["cfg"], seed)
        return [r[m] for m in L_OBS]
    r = S.simulate(S_DECK, S_CMD, _W["cfg"], seed)
    return [r[m] for m in S_OBS]


def observe(which, flags, n, turns, procs):
    with Pool(procs, initializer=_init,
              initargs=(which, flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def paired(which, base, variant, n, turns, procs, obs):
    a = observe(which, base, n, turns, procs)
    b = observe(which, variant, n, turns, procs)
    out = {}
    for i, m in enumerate(obs):
        d = b[:, i] - a[:, i]
        hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
        out[m] = (a[:, i].mean(), b[:, i].mean(), d.mean(), hw)
    return out


# ---------------------------------------------------------------------------
# PART A -- what the reserve buys
# ---------------------------------------------------------------------------

def part_a(n, procs, turns=20):
    print("=" * 78)
    print(f"PART A -- what the held mana actually buys. N = {n:,}, T{turns}.")
    print("=" * 78)
    a = observe("lorehold", {}, n, turns, procs)
    col = {m: a[:, i] for i, m in enumerate(L_OBS)}
    held_t = col["reserve_turns"].mean()
    held_m = col["reserve_held"].mean()
    unused_t = col["reserve_unused_turns"].mean()
    wasted = col["reserve_wasted"].mean()
    lost = col["reserve_lost_commander"].mean()
    over = col["reserve_overheld"].mean()
    print(f"\n  lorehold, at the default reserve of 2, per game:\n")
    print(f"    turns the reserve was held            {held_t:8.2f}")
    print(f"    mana declined over those turns        {held_m:8.2f}")
    print(f"    turns it bought NO off-turn miracle   {unused_t:8.2f}"
          f"   ({unused_t / held_t:.0%} of them)")
    print(f"    mana declined for nothing             {wasted:8.2f}"
          f"   ({wasted / held_m:.0%} of it)")
    print(f"    ...of which: the commander was GONE   {lost:8.2f} turns")
    print(f"    mana held beyond the miracle's cost   {over:8.2f}"
          f"   ({over / held_m:.0%})")
    print("""
  "Bought nothing" is not the same as "should not have been held" -- a
  reserve is insurance, and insurance that never pays out was still not
  necessarily a mistake. PART B is the test that decides it; this is the
  mechanism it has to explain.""")
    print()


# ---------------------------------------------------------------------------
# PART B / C -- sweeps
# ---------------------------------------------------------------------------

def sweep(which, knob, values, default, n, procs, turns, obs, headline):
    print("=" * 78)
    print(f"{headline}  N = {n:,}, T{turns}.")
    print("=" * 78)
    print(f"  Every value paired against the default ({knob}={default!r}) on")
    print("  the same seeds, so common random numbers are intact and nothing")
    print("  but the knob differs. A `*` means the delta beats its own bar.\n")
    print(f"  {knob:<22}{'win rate':>22}{'primary proxy':>24}")
    rows = {}
    proxy = "mv_cheated" if which == "lorehold" else "shilgengar_ults"
    for v in values:
        if v == default:
            continue
        r = paired(which, {knob: default}, {knob: v}, n, turns, procs, obs)
        rows[v] = r
        w = r["won"]
        p = r[proxy]
        star_w = "*" if abs(w[2]) > w[3] else " "
        star_p = "*" if abs(p[2]) > p[3] else " "
        print(f"  {str(v):<22}{w[2]:>+10.4f} +-{w[3]:<8.4f}{star_w}"
              f"{p[2]:>+11.3f} +-{p[3]:<8.3f}{star_p}")
    print()
    for v, r in rows.items():
        print(f"  {knob}={v!r}")
        for m, (av, bv, d, hw) in r.items():
            if abs(d) < 1e-9 and hw < 1e-9:
                continue
            star = " *" if abs(d) > hw else "  "
            print(f"      {m:<24}{av:>10.3f} ->{bv:>10.3f}"
                  f"   {d:>+9.4f} +-{hw:<8.4f}{star}")
        print()


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")),
             15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    part_a(n, procs)
    sweep("lorehold", "miracle_reserve", [0, 1, "need", 2, 3], 2,
          n, procs, 20, L_OBS,
          "PART B -- lorehold: how much to hold for the miracle windows.")
    sweep("shilgengar", "shilgengar_ult_reserve", [0, 1, 2, 3, 4], 3,
          n, procs, 20, S_OBS,
          "PART C1 -- shilgengar: how much to hold for the ultimate.")
    sweep("shilgengar", "shilgengar_ult_min_gain", [1, 2, 3, 5], 1,
          n, procs, 20, S_OBS,
          "PART C2 -- shilgengar: how big the reanimation must be to bother.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
