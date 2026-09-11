#!/usr/bin/env python3
"""Is the Tivit + Time Sieve loop observed? Three ways of asking.

THE CLAIM UNDER TEST, which is a fact about the cards and not about this model:

    Time Sieve  {U}{B}  "{T}, Sacrifice five artifacts: Take an extra turn
                        after this one."
    Tivit       "Whenever Tivit enters or DEALS COMBAT DAMAGE TO A PLAYER,
                council's dilemma ... While voting, you may vote an additional
                time." Both halves of the dilemma make an artifact, so an
                adversarial pod can change the MIX and not the COUNT.

In a four-player game you cast two votes and the pod casts three, so one Tivit
attack is exactly five artifacts -- exactly Time Sieve's cost, with nothing to
spare. The Sieve untaps on the turn it just bought, so:

    attack -> 5 tokens -> sacrifice -> extra turn -> untap -> attack -> ...

is unbounded, and the two cards together should be one of the best things this
deck can do. `ablation_tivit.txt` scored Time Sieve at -0.0025, i.e. slightly
NEGATIVE and inside its bar. This script is the "when a result is surprising,
the engine is the first suspect" check.

    python diag_time_sieve.py [--n 4000]

PART A  the loop on a forced board -- does it chain at all?
PART B  real games: how often the pair assembles, and what it produces.
PART C  each of the three fixes as a paired CFG flip.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import tivit_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc import tivit as T

DECK, CMD = tivit_v1.build()
BY_NAME = {c.name: c for c in DECK}

# Flag sets. "old" is the engine as it stood in the committed tivit table.
OLD = {"sieve_taps": False, "extra_turns_chain": False,
       "extra_turns_skip_opponents": False}
NEW = {"sieve_taps": True, "extra_turns_chain": True,
       "extra_turns_skip_opponents": True}


# ---------------------------------------------------------------------------
# PART A -- the loop on a forced board
# ---------------------------------------------------------------------------

def forced(flags, lands=6, turns=20):
    """Tivit and Time Sieve already on the battlefield, six lands, nothing else.

    Deliberately the MINIMUM board the claim needs, so what comes out is the
    two-card loop and not a good game of Magic. Drives simulate()'s own turn
    loop rather than reimplementing it, so the extra-turn accounting under test
    is the real one.

    The opponents are given unkillable life totals ON PURPOSE. A 6/6 flier
    swinging into a pod whose blockers are a float kills the table on turn four
    -- which is the answer to the question, but it ENDS the measurement before
    the turn structure has shown anything. Removing the win condition is what
    makes the loop itself visible. (`pod_life` is the wrong knob for this:
    opponents are dealt `starting_life` each by `make_pod`.)
    """
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)
    g = T.TivitGame(DECK, CMD, cfg, 1)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.opening_hand()
    g.board.append(Permanent(card=CMD, sick=False))
    g.commander_cast = True
    g.board.append(Permanent(card=BY_NAME["Time Sieve"], sick=False))
    for c in [x for x in DECK if x.is_land][:lands]:
        g.board.append(Permanent(card=c, sick=False))

    # Calls tivit.take_extra_turns rather than reimplementing it, so this
    # diagnostic cannot drift from the engine it is diagnosing.
    played = 0
    while played < turns and g.result is None:
        T.take_turn(g)
        played += 1
        if g.result is not None:
            break
        played = T.take_extra_turns(g, played, turns)
    return g


def part_a():
    print("=" * 78)
    print("PART A -- Tivit + Time Sieve + 6 lands on the battlefield, turn 0.")
    print("=" * 78)
    print("  Opponents given unkillable life so the loop's own turn structure")
    print("  is visible over a 20-turn horizon. `pod rounds` is how many times")
    print("  the three opponents actually got to untap.\n")
    print(f"  {'engine':<7}{'turns':>6}{'extra':>7}{'pod rnds':>10}"
          f"{'sieve acts':>12}{'chain':>7}{'tivit trig':>12}"
          f"{'damage':>9}{'ended':>9}")
    for label, flags in (("old", OLD), ("new", NEW)):
        g = forced(flags)
        print(f"  {label:<7}{g.turn:>6}{g.m['extra_turns_taken']:>7}"
              f"{g.m['pod_rounds']:>10}{g.m['sieve_activations']:>12}"
              f"{g.m['sieve_chain_max']:>7}{g.m['tivit_triggers']:>12}"
              f"{g.m['damage']:>9.1f}{g.result or 'horizon':>9}")
    print()


# ---------------------------------------------------------------------------
# PART B / C -- real games
# ---------------------------------------------------------------------------

_W = {}
OBS = ("won", "damage", "turns_played", "extra_turns", "sieve_activations",
       "sieve_chain_max", "tivit_triggers", "artifacts_made", "wipes_suffered",
       "removal_eaten")


def _init(flags, turns):
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset({"Time Sieve"}),
                     **flags)
    _W["deck"], _W["cmd"] = DECK, CMD


def _one(seed):
    r = T.simulate(_W["deck"], _W["cmd"], _W["cfg"], seed)
    return [r[m] for m in OBS] + [r["cast_test_card"]]


def observe(flags, n, turns, procs):
    with Pool(procs, initializer=_init, initargs=(flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def part_b(n, procs, turns=20):
    print("=" * 78)
    print(f"PART B -- real games, N = {n:,}, T{turns}, default pod.")
    print("=" * 78)
    print("  P(cast) is how often Time Sieve is cast at all. The rest are "
          "per-game means.\n")
    print(f"  {'engine':<10}{'P(cast)':>9}{'sieve acts':>12}"
          f"{'extra turns':>13}{'longest chain':>15}{'turns':>8}"
          f"{'damage':>9}{'win':>8}")
    out = {}
    for label, flags in (("old", OLD), ("new", NEW)):
        a = observe(flags, n, turns, procs)
        col = {m: a[:, i] for i, m in enumerate(OBS)}
        cast = a[:, len(OBS)]
        out[label] = col
        print(f"  {label:<10}{cast.mean():>9.3f}"
              f"{col['sieve_activations'].mean():>12.2f}"
              f"{col['extra_turns'].mean():>13.2f}"
              f"{col['sieve_chain_max'].mean():>15.2f}"
              f"{col['turns_played'].mean():>8.2f}"
              f"{col['damage'].mean():>9.1f}{col['won'].mean():>8.3f}")
    print()
    # Conditional on the pair actually assembling, which is the number the
    # unconditional mean hides: one card is drawn in a minority of games.
    for label in ("old", "new"):
        col = out[label]
        got = col["sieve_activations"] > 0
        if got.sum():
            print(f"  {label}: in the {got.mean():.1%} of games where Time "
                  f"Sieve activated at least once -- "
                  f"{col['sieve_activations'][got].mean():.2f} activations, "
                  f"longest chain {col['sieve_chain_max'][got].mean():.2f}, "
                  f"win rate {col['won'][got].mean():.3f} "
                  f"(vs {col['won'][~got].mean():.3f} when it did not)")
    print()


CASES = [
    ("sieve_taps            ({T} means ONCE PER TURN, not ten times)",
     dict(OLD), dict(OLD, sieve_taps=True)),
    ("extra_turns_chain     (an extra turn's own extra turn was discarded)",
     dict(OLD, sieve_taps=True),
     dict(OLD, sieve_taps=True, extra_turns_chain=True)),
    ("extra_turns_skip_opponents  (an extra turn handed the pod a round)",
     dict(OLD, sieve_taps=True, extra_turns_chain=True), dict(NEW)),
    ("ALL THREE",
     dict(OLD), dict(NEW)),
]


def part_c(n, procs, turns=20):
    print("=" * 78)
    print(f"PART C -- each fix as a paired CFG flip, N = {n:,}, T{turns}.")
    print("=" * 78)
    print("  Same deck, same seeds, flag off vs on, so common random numbers")
    print("  are intact and nothing but the flag differs. Applied CUMULATIVELY")
    print("  in the order listed, so the three deltas add up to ALL THREE.\n")
    for label, off, on in CASES:
        a = observe(off, n, turns, procs)
        b = observe(on, n, turns, procs)
        print(f"  {label}")
        for i, m in enumerate(OBS):
            d = b[:, i] - a[:, i]
            hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
            if abs(d.mean()) < 1e-9 and hw < 1e-9:
                continue
            star = " *" if abs(d.mean()) > hw else "  "
            print(f"      {m:<20}{a[:, i].mean():>9.3f} ->"
                  f"{b[:, i].mean():>9.3f}   {d.mean():>+9.4f} "
                  f"+-{hw:<8.4f}{star}")
        print()


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 4000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    part_a()
    part_b(n, procs)
    part_c(n, procs)


if __name__ == "__main__":
    main()
