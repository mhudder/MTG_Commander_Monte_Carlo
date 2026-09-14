#!/usr/bin/env python3
"""§0z17 — the mid-game randomness is addressed, not ordered.

    python -m tests.test_crn_streams
    python -m tests.test_crn_streams --mutate    # exactly 5 of 6 MUST fail

WHAT IS BEING PINNED. Common random numbers are the reason this project can
resolve 0.003 win rate at all: deck A and deck B are the same list with one
slot swapped, shuffled on the same seed, so the other ~97 cards land in the
same places and nearly all variance cancels in the difference. That holds only
while both branches consume the same random numbers in the same order.

Eleven call sites in five files drew mid-game from the single game RNG. Once
two branches' boards diverged they took a DIFFERENT NUMBER of draws, and from
there every later draw in both games read a different slot of one sequence.
`engine.CRNStreams` replaces the ordering with ADDRESSING: each effect has its
own stream and its Nth firing reads index N, so nothing another effect does can
shift it.

THE INVARIANT THIS FILE ASSERTS is not a difference but a structural property,
which is why it needs no second branch to compare against and why it holds per
game: **after the opening hand is decided, `g.rng` is never touched again.**

WHY `tools/validate.py`'S A/A CONTROL CANNOT ASSERT IT. That control swaps a
card for ITSELF. The branches never diverge, the call sequence is identical by
construction, and all eleven leaks passed it for months while it printed +0.00
on eighteen metrics. A check that cannot fail is worse than no check (§0z15).

THE LISTS ARE `build_pending`'S, and the first version of this test got that
wrong in a way worth recording. Built from the deck MODULES, lorehold's
`sunbird()` never executes -- Sunbird's Invocation is STAGED, not committed --
so the test ran clean over the single worst leak in the project (1,100
mid-game draws against the other branch's 132) and a mutation restoring that
leak went UNDETECTED, because the code was never reached. `ablation.py` and
`candidates.py` both measure `build_pending`, so that is what an audit of
their randomness has to range over.

ONE OF THE ELEVEN SITES CANNOT BE TESTED AND THAT IS RECORDED RATHER THAN
HIDDEN. `lorehold.py`'s gated-setter draw is guarded by
`GATED_SETTERS = {"Hidden Retreat"}`, and Hidden Retreat was committed OUT of
the deck on 2026-09-01. The branch is unreachable in the current list, so the
mutation that restores its leak is expected NOT to be detected -- the sixth
case below. It is a dead call site, and a fifth instance of §0q: a
hand-maintained name set naming a card the deck has moved past.
"""
import sys

from edhmc.engine import Card
import edhmc.engine as ENG
import edhmc.lorehold as LH
import edhmc.karlov as KV
import edhmc.tivit as TV
from edhmc.experiment import run_ab, repl_priority
from edhmc.pending import build_pending

N = 200

SIMS = {"rendmaw": None, "lorehold": LH.simulate,
        "karlov": KV.simulate, "tivit": TV.simulate,
        "shilgengar": None, "azusa": None}
CUTS = {"rendmaw": "March of the World Ooze", "lorehold": "Verge Rangers",
        "karlov": "Blood Artist", "tivit": "Academy Manufactor",
        "shilgengar": "Blood Artist", "azusa": "Lotus Cobra"}


def _sim(deck):
    if SIMS[deck] is None and deck != "rendmaw":
        import edhmc.shilgengar as SG
        import edhmc.azusa as AZ
        SIMS["shilgengar"], SIMS["azusa"] = SG.simulate, AZ.simulate
    return SIMS[deck]


def leaked(deck, n=N):
    """Draws taken from the GAME rng after the opening hand, over a real swap.

    The swap is a replacement-level blank, exactly as `ablation.py` builds one:
    a real divergence that needs no per-deck candidate catalog, so adding an
    engine cannot quietly leave it out of the audit.
    """
    d, c = build_pending(deck)
    blank = Card(name="__crn_blank__", types=frozenset({"Creature"}),
                 cost={"gen": 3}, power=1, toughness=1,
                 priority=repl_priority(d))
    a, b, _ = run_ab(d, c, CUTS[deck], blank, n=n,
                     cfg={"turns": 20, "crn_audit": True}, sim=_sim(deck))
    return (sum(r["rng_after_opening"] for r in a)
            + sum(r["rng_after_opening"] for r in b))


# (label, module, accessor, deck it is reached through, MUST the audit see it?)
CASES = [
    ("lorehold sunbird shuffle",      LH,  "crn_shuffle",   "lorehold", True),
    ("lorehold bombardment / tutor",  LH,  "crn_randrange", "lorehold", True),
    ("engine   Arasta / Deathreap",   ENG, "crn_random",    "rendmaw",  True),
    ("karlov   Kambal",               KV,  "crn_random",    "karlov",   True),
    ("tivit    Master of Ceremonies", TV,  "crn_randrange", "tivit",    True),
    ("lorehold gated setter (DEAD)",  LH,  "crn_random",    "lorehold", False),
]

LEAKS = {"crn_random":    lambda g, name: g.rng.random(),
         "crn_randrange": lambda g, name, n: g.rng.randrange(n),
         "crn_shuffle":   lambda g, name, seq: g.rng.shuffle(seq)}


def main(mutate=False):
    print(__doc__.split("\n\n")[0])
    print()
    if not mutate:
        bad = 0
        for deck in sorted(SIMS):
            n = leaked(deck)
            ok = n == 0
            bad += not ok
            print(f"  {deck:<11} game-RNG draws after the opening hand: "
                  f"{n:<6} {'OK' if ok else '*** LEAKING ***'}")
        if bad:
            raise SystemExit(f"\nFAIL: {bad} engine(s) leaking. See §0z17.")
        print("\nPASS — every engine seals its game RNG after the opening hand.")
        return

    print("MUTATION: each row puts one site back on the game RNG.")
    print("EXPECTATION, WRITTEN BEFORE THE RUN: exactly 5 of 6 detected; the")
    print("sixth is a dead call site (Hidden Retreat left the deck 2026-09-01).")
    print()
    got, want = [], []
    for label, mod, fn, deck, must in CASES:
        orig = getattr(mod, fn)
        setattr(mod, fn, LEAKS[fn])
        try:
            n = leaked(deck)
        finally:
            setattr(mod, fn, orig)
        hit = n > 0
        got.append(hit)
        want.append(must)
        mark = "OK" if hit == must else "!!! UNEXPECTED"
        print(f"  {label:<30} leaked={n:<6} detected={str(hit):<5} "
              f"expected={str(must):<5} {mark}")
    print()
    print(f"  detected {sum(got)} of {len(CASES)}; expected exactly {sum(want)}")
    if got != want:
        raise SystemExit(
            "\nFAIL: the audit did not behave as specified. A mutation that "
            "was expected to be caught and was not means the audit does not "
            "reach that code -- check the card is in build_pending's list "
            "before concluding the audit is sound.")
    print("PASS — the audit detects every reachable reintroduction of §0z17.")


if __name__ == "__main__":
    main(mutate="--mutate" in sys.argv)
