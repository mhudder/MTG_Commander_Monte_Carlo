#!/usr/bin/env python3
"""§0z30 — one opening hand and one pod-phase order for six engines.

    python -m tests.test_mulligan_and_pod_order
    python -m tests.test_mulligan_and_pod_order --mutate   # 5 mutations, exact sets

WHAT IS BEING PINNED. Two blocks that every engine carried its own copy of,
and that had drifted (M1 and M2 of the 2026-09-17 review):

  the opening hand    engine.py drew a FIFTH hand when the fourth failed the
                      keep rule; lorehold.py cleared the hand and never redrew
                      (0.11% of games started with no cards); karlov, tivit,
                      shilgengar and azusa neither cleared nor redrew, so the
                      seven cards were in hand AND in the library -- 106-card
                      games, 0.1-0.4% of the time. Only lorehold counted an
                      MDFC's land face for the keep decision, and three other
                      decks carry MDFCs.
  the pod phase       four engines ran chip damage -> clocks -> removal; karlov
                      and tivit ran removal first, so in those two a wrath
                      could clear your board before the clock read it, and
                      the opponents' creatures grew BEFORE they dealt chip
                      damage rather than after.

Both now live in one place -- `engine.london_mulligan` and
`opponents.pod_phase` -- and this file asserts the properties that
distinguish the one rule from every old copy, over every engine's STAGED
list (`build_pending`, the list the tables are measured on):

  A  hand + library is the whole deck, every seed          (the 106-card bug)
  B  the kept hand has at least four cards, every seed     (the empty hand)
  C  at most three reshuffles, every seed                  (the fifth hand)
  D  the four-hand path is actually reached                (or A-C prove nothing)
  E  a hand of one land and one MDFC is a keep             (the MDFC rule)
  F  the pod phase runs damage, clocks, removal, in that order
  G  no engine calls the three pod functions itself        (the order is written once)

MUTATIONS, WRITTEN BEFORE THE RUN. Each restores one old copy into all six
engines and must break EXACTLY the cases that distinguish it:

  karlov's fallback (no clear, no redraw)    -> A, C and E
  lorehold's fallback (clear, never redraw)  -> B and C
  engine's fallback (a fifth hand)           -> C only
  the five engines' keep rule (no MDFC)      -> E only
  karlov's pod order (removal first)         -> F only

THE FIRST EXPECTATION WAS WRONG, and the way it was wrong is the finding:
it said A only, B only, C only. Every old copy ran `for mulls in range(4)`
with the reshuffle INSIDE the loop, so when the fourth hand also failed all
three shuffled a fourth time -- for karlov that fourth shuffle IS the
106-card mechanism (the hand was never cleared, so its seven cards were
shuffled into the library while still in hand), and for lorehold it is
the reshuffle of a hand it had just emptied. C ("at most three reshuffles")
is therefore the signature of the fourth-hand bug in every old copy, not
only engine.py's fifth draw. And karlov's copy counted `is_land` only, so
it fails the MDFC case too. Corrected before the second run; a set edited
to match the output would be a transcript, not a test.

D and G are not mutated: D is the check on the test's own reach, and G reads
the source, which a mutation in-process cannot alter.
"""
import inspect
import sys

import edhmc.engine as ENG
import edhmc.lorehold as LH
import edhmc.karlov as KV
import edhmc.tivit as TV
import edhmc.shilgengar as SH
import edhmc.azusa as AZ
import edhmc.opponents as OPP
from edhmc.engine import Card
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
SEEDS = 6000          # per engine; the four-hand path is ~0.1-0.4% of seeds

ENGINES = {"rendmaw": ENG, "lorehold": LH, "karlov": KV, "tivit": TV,
           "shilgengar": SH, "azusa": AZ}

passed = failed = 0
FAILED_NAMES = []


def check(name, got, want=True):
    global passed, failed
    ok = got == want
    passed += ok
    failed += (not ok)
    if not ok:
        FAILED_NAMES.append(name)
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + ("" if ok else f"  got {got!r}"))


# ---------------------------------------------------------------------------
# The old copies, verbatim, as mutations. Each is what one engine did before
# 2026-09-17; the docstring above says which case each must break.

def old_karlov_style(g):
    for mulls in range(4):
        g.hand = [g.library.pop() for _ in range(7)]
        if 2 <= sum(1 for c in g.hand if c.is_land) <= 5:
            break
        g.library.extend(g.hand)
        g.rng.shuffle(g.library)
    for _ in range(mulls):
        if g.hand:
            worst = max(g.hand, key=lambda c: (not c.is_land, c.mv))
            g.hand.remove(worst)
            g.library.insert(0, worst)


def old_lorehold_style(g):
    for mulls in range(4):
        g.hand = [g.library.pop() for _ in range(7)]
        lands = sum(1 for c in g.hand if c.is_land or c.land_face)
        if 2 <= lands <= 5:
            break
        g.library.extend(g.hand)
        g.rng.shuffle(g.library)
        g.hand = []
    for _ in range(mulls):
        if g.hand:
            worst = max(g.hand, key=lambda c: (not c.is_land, c.mv))
            g.hand.remove(worst)
            g.library.insert(0, worst)


def old_engine_style(g):
    for mulls in range(4):
        g.hand = [g.library.pop() for _ in range(7)]
        lands = sum(1 for c in g.hand if c.is_land or c.land_face)
        if 2 <= lands <= 5:
            break
        g.library.extend(g.hand)
        g.rng.shuffle(g.library)
        g.hand = []
    else:
        g.hand = [g.library.pop() for _ in range(7)]
    for _ in range(mulls):
        if g.hand:
            worst = max(g.hand, key=lambda c: (not c.is_land, c.mv))
            g.hand.remove(worst)
            g.library.insert(0, worst)


def old_pod_order(g, before_act=None):
    if before_act is not None:
        before_act(g)
    OPP.opponents_act(g)
    OPP.incidental_damage(g)
    OPP.resolve_clocks(g)


MUTATIONS = {
    "karlov's fallback (no clear, no redraw)":
        ("mulligan", old_karlov_style),
    "lorehold's fallback (clear, never redraw)":
        ("mulligan", old_lorehold_style),
    "engine's fallback (a fifth hand)":
        ("mulligan", old_engine_style),
    "the five engines' keep rule (no MDFC)":
        ("keep", lambda c: c.is_land),
    "karlov's pod order (removal first)":
        ("pod", old_pod_order),
}
EXPECTED = {
    "karlov's fallback (no clear, no redraw)": {"A", "C", "E"},
    "lorehold's fallback (clear, never redraw)": {"B", "C"},
    "engine's fallback (a fifth hand)": {"C"},
    "the five engines' keep rule (no MDFC)": {"E"},
    "karlov's pod order (removal first)": {"F"},
}


# ---------------------------------------------------------------------------

def instrumented(fn, record):
    """Run `fn(g)` counting reshuffles, then record (hand, library, shuffles)."""
    def run(g):
        count = {"n": 0}
        orig = g.rng.shuffle

        def sh(x):
            count["n"] += 1
            orig(x)
        g.rng.shuffle = sh
        try:
            fn(g)
        finally:
            g.rng.shuffle = orig
        record.append((len(g.hand), len(g.library), count["n"]))
    return run


def install_mulligan(fn):
    for mod in ENGINES.values():
        mod.london_mulligan = fn


def run_cases(mulligan_fn, keep_fn, pod_fn):
    """A..G with the given implementations installed. Returns the set of
    failed case letters, and prints each."""
    global FAILED_NAMES
    FAILED_NAMES = []
    saved = ({m: mod.london_mulligan for m, mod in ENGINES.items()},
             ENG.counts_as_land_in_hand, OPP.pod_phase)
    try:
        ENG.counts_as_land_in_hand = keep_fn
        OPP.pod_phase = pod_fn
        for name, mod in ENGINES.items():
            record = []
            mod.london_mulligan = instrumented(mulligan_fn, record)
            deck, cmd = build_pending(name)
            size = len(deck)
            cfg = dict(DEFAULT_CFG, turns=0, watch=frozenset())
            for s in range(SEEDS):
                mod.simulate(deck, cmd, cfg, s)
            whole = all(h + lib == size for h, lib, _ in record)
            check(f"A {name}: hand + library == {size} on every seed", whole)
            check(f"B {name}: at least four cards kept on every seed",
                  all(h >= 4 for h, _, _ in record))
            check(f"C {name}: at most three reshuffles on every seed",
                  all(n <= 3 for _, _, n in record))
            four = sum(1 for _, _, n in record if n >= 3)
            check(f"D {name}: the four-hand path is reached ({four} of {SEEDS})",
                  four >= 1)
    finally:
        for m, mod in ENGINES.items():
            mod.london_mulligan = saved[0][m]
        ENG.counts_as_land_in_hand = saved[1]
        OPP.pod_phase = saved[2]

    # E: one land + one MDFC is a keep. A stub game with a scripted library.
    ENG.counts_as_land_in_hand = keep_fn
    try:
        land = Card(name="Plains", types=frozenset({"Land"}), is_land=True)
        mdfc = Card(name="Pinnacle Monk", types=frozenset({"Creature"}),
                    cost={"gen": 3, "R": 2}, power=2, toughness=2,
                    land_face=("R", True))
        spell = Card(name="Spell", types=frozenset({"Sorcery"}),
                     cost={"gen": 2}, )
        top7 = [land, mdfc, spell, spell, spell, spell, spell]

        class Stub:
            pass
        g = Stub()
        g.library = [spell] * 92 + list(reversed(top7))     # pop() draws top7 in order
        g.hand = []
        shuffles = []

        class R:
            def shuffle(self, x):
                shuffles.append(1)
        g.rng = R()
        mulligan_fn(g)
        check("E one land + one MDFC is kept (no reshuffle, seven cards)",
              (len(shuffles), len(g.hand)), (0, 7))
    finally:
        ENG.counts_as_land_in_hand = saved[1]

    # F: the order, observed through recorders on a real game.
    order = []
    real = (OPP.incidental_damage, OPP.resolve_clocks, OPP.opponents_act)
    try:
        OPP.incidental_damage = lambda g: order.append("damage")
        OPP.resolve_clocks = lambda g: order.append("clocks")
        OPP.opponents_act = lambda g: order.append("removal")
        deck, cmd = build_pending("karlov")
        g = KV.KarlovGame(deck, cmd, dict(DEFAULT_CFG, watch=frozenset()), 1)
        g.opening_hand()
        g.turn = 5
        pod_fn(g, before_act=lambda g: order.append("activity"))
        check("F pod phase: damage, clocks, then removal (activity just before it)",
              order, ["damage", "clocks", "activity", "removal"])
    finally:
        OPP.incidental_damage, OPP.resolve_clocks, OPP.opponents_act = real

    # G: written once. No engine calls the three pod functions itself.
    callers = []
    for name, mod in ENGINES.items():
        src = inspect.getsource(mod)
        for fn in ("OPP.incidental_damage(", "OPP.resolve_clocks(",
                   "OPP.opponents_act("):
            if fn in src:
                callers.append(f"{name}:{fn}")
        if "OPP.pod_phase(" not in src:
            callers.append(f"{name}: no OPP.pod_phase call")
    check("G every engine calls OPP.pod_phase and none calls the three parts",
          callers, [])
    return {n[0] for n in FAILED_NAMES}


def main() -> int:
    if not MUTATE:
        print("§0z30 -- one opening hand, one pod-phase order, six engines\n")
        run_cases(ENG.london_mulligan, ENG.counts_as_land_in_hand, OPP.pod_phase)
        print(f"\n{passed} passed, {failed} failed")
        return 1 if failed else 0

    print("MUTATION RUN -- each old copy must break exactly its own cases\n")
    bad = 0
    for label, (kind, fn) in MUTATIONS.items():
        print(f"-- {label}")
        mull = fn if kind == "mulligan" else ENG.london_mulligan
        keep = fn if kind == "keep" else ENG.counts_as_land_in_hand
        pod = fn if kind == "pod" else OPP.pod_phase
        broke = run_cases(mull, keep, pod)
        ok = broke == EXPECTED[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(EXPECTED[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    total = len(MUTATIONS)
    print(f"{total - bad} passed, {bad} failed  "
          f"({total} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
