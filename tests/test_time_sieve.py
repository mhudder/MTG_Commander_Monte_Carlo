#!/usr/bin/env python3
"""The Tivit + Time Sieve turn loop, pinned as a test.

`tivit.time_sieve`'s docstring makes three quantitative claims, and this project's
standing lesson is that a docstring claiming a mechanism is not evidence of one --
two deck modules once documented their own errors as deliberate, and Time Sieve
itself sat at -0.0025 win rate for a day with a comment saying it took extra
turns. So the claims are checked here:

  1. ONE ACTIVATION PER TURN. The cost is "{T}, Sacrifice five artifacts", and
     the {T} is Time Sieve's own tap.
  2. THE CHAIN RUNS. Time Sieve untaps on the turn it just bought, so extra turns
     chain until the horizon runs out.
  3. AN EXTRA TURN IS NOT A ROUND. The three opponents do not act during it.

And the fact about the cards that makes the loop work at all: in a four-player
game Tivit's dilemma is FIVE votes (your two plus three opponents'), every vote
makes an artifact whichever way it goes, and five artifacts is exactly the
Sieve's cost.

    python test_time_sieve.py
"""
import sys

from edhmc.decks import tivit_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc import tivit as T
from edhmc import voting as V

DECK, CMD = tivit_v1.build()
BY_NAME = {c.name: c for c in DECK}
TURNS = 12


def setup(**flags):
    """Tivit and Time Sieve on the battlefield, six lands, unkillable opponents.

    The opponents' life is set out of reach on purpose: a 6/6 flier swinging into
    a pod whose blockers are a float kills the table on turn four, which ends the
    game before the turn structure has shown anything.
    """
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset(), **flags)
    g = T.TivitGame(DECK, CMD, cfg, 1)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.opening_hand()
    g.board.append(Permanent(card=CMD, sick=False))
    g.commander_cast = True
    g.board.append(Permanent(card=BY_NAME["Time Sieve"], sick=False))
    for c in [x for x in DECK if x.is_land][:6]:
        g.board.append(Permanent(card=c, sick=False))
    return g


def drive(g):
    """simulate()'s turn loop, calling the REAL extra-turn accounting.

    An earlier version of this reimplemented `take_extra_turns` inline and
    silently failed to record `sieve_chain_max`, reporting a chain of 0 while the
    chain was plainly running. That is why the accounting was extracted into
    `tivit.take_extra_turns` -- a duplicated loop is a claim, same as a name in a
    set.
    """
    budget = g.cfg["turns"]
    played = 0
    while played < budget and g.result is None:
        T.take_turn(g)
        played += 1
        if g.result is not None:
            break
        played = T.take_extra_turns(g, played, budget)
    return played


def main():
    fails = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'}  {msg}")
        if not cond:
            fails.append(msg)

    print("THE VOTE COUNT, which is what makes five artifacts a turn\n")
    g = setup()
    mine, theirs = V.my_votes(g), V.opp_votes(g)
    check(mine == 2, f"Tivit gives you a second vote: my_votes = {mine}")
    check(theirs == 3, f"three opponents vote: opp_votes = {theirs}")
    before = sum(g.tokens.values())
    T.tivit_dilemma(g)
    made = sum(g.tokens.values()) - before
    check(made == 5, f"one dilemma makes five artifacts (got {made}) -- and it "
                     f"is five whichever way an adversarial pod votes, because "
                     f"both halves make one")
    check(made >= 5, "five is exactly Time Sieve's cost, with nothing spare")

    print("\nONE ACTIVATION PER TURN, because the cost is a tap of itself\n")
    g = setup()
    g.tokens["Treasure"] = 50          # ten activations' worth
    T.time_sieve(g)
    check(g.m["sieve_activations"] == 1,
          f"50 tokens still buys ONE activation, not ten "
          f"(got {g.m['sieve_activations']})")
    check(g.tokens["Treasure"] == 45,
          f"exactly five tokens were eaten (left {g.tokens['Treasure']})")
    T.time_sieve(g)
    check(g.m["sieve_activations"] == 1,
          "a second activation in the same turn is refused while it is tapped")

    print("\nTHE CHAIN RUNS, and the pod does not get a round for each turn\n")
    g = setup()
    played = drive(g)
    taken, rounds = g.m["extra_turns_taken"], g.m["pod_rounds"]
    acts, chain = g.m["sieve_activations"], g.m["sieve_chain_max"]
    print(f"        {played} turns played, {taken} of them extra, "
          f"{rounds} pod rounds, {acts} sieve activations, "
          f"longest chain {chain}")
    check(taken >= TURNS // 2,
          f"most turns are extra turns ({taken} of {played})")
    check(chain >= TURNS // 2,
          f"they arrive as ONE chain, not one per real turn (longest {chain})")
    check(rounds <= 2,
          f"the pod got {rounds} round(s), not one per turn")
    check(acts <= played,
          f"activations ({acts}) never exceed turns ({played})")

    print("\nTHE OLD ENGINE, for contrast -- all three flags off\n")
    old = dict(sieve_taps=False, extra_turns_chain=False,
               extra_turns_skip_opponents=False)
    g = setup(**old)
    played = drive(g)
    print(f"        {played} turns played, {g.m['extra_turns_taken']} extra, "
          f"{g.m['pod_rounds']} pod rounds, "
          f"{g.m['sieve_activations']} sieve activations, "
          f"longest chain {g.m['sieve_chain_max']}")
    check(g.m["pod_rounds"] >= played,
          f"it gave the pod a round for EVERY turn ({g.m['pod_rounds']} for "
          f"{played}) -- the bug, reproduced")

    print()
    if fails:
        print(f"FAILED ({len(fails)}):")
        for f in fails:
            print("   ", f)
        return 1
    print("OK -- the loop behaves as tivit.time_sieve() and KNOWN_ISSUES 0m say.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
