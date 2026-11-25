#!/usr/bin/env python3
"""§0z254: Massacre Wurm's, Sun Titan's and Twilight Shepherd's ETBs on
every entry, not on a cast alone (shilgengar).

    python -m tests.test_returned_etbs
    python -m tests.test_returned_etbs --mutate   # 4 mutations, exact sets

    Massacre Wurm: "When this creature enters, creatures your opponents
    control get -2/-2 until end of turn."
    Sun Titan: "Whenever this creature enters or attacks, you may return
    target permanent card with mana value 3 or less from your graveyard to
    the battlefield."
    Twilight Shepherd: "When this creature enters, return to your hand all
    cards in your graveyard that were put there from the battlefield this
    turn."                                              (Scryfall 2026-11-25)

`resolve` (the cast, `cast=True`) fired all three; every other entry goes
through `make_permanent` without it, and `returned_etb` fires them there.

CASES
  A  Wurm off the cast path: each opponent's toughness-2 body dies, the
     5-toughness one stays
  B  Wurm through resolve: the same kill, and no second ETB
  C  Sun Titan off the cast path: Viscera Seer (mv 1) back from the graveyard
  D  Sun Titan through resolve, two small cards in the graveyard: ONE back
  E  Shepherd off the cast path: a card put in the graveyard this turn to hand
  F  Shepherd's persist: its ETB fires exactly once
  G  NEIGHBOUR: all three switches off -- A, C and E's entries do nothing
  H  NEIGHBOUR: shepherd_etb_returns=False -- persist still fires it once
  I  the ultimate returns Sun Titan and two small creatures together: each
     enters once, and Titan's ETB takes Mind Stone, the one mv<=3 permanent
     left in the graveyard (the pool left it first, §0z19)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  all three switches off everywhere          -> A, C, E, F, I
  make_permanent ignores its cast flag        -> B, D
  CREATURE_ETB_KNOBS without Sun Titan        -> C, I
  wurm_etb does nothing                       -> A, B

UNMUTATED (§0z15): G and H are the switches' neighbours; the old rule's
persist call (H) is reached by no mutation of the new rule.

The first mutation run broke F too under "ignores its cast flag": F and H
put the Shepherd on the battlefield with `make_permanent(cast=True)`, so
the mutation fired an ETB in the SETUP. They now build it by hand
(`dead_shepherd`); the expected sets are unchanged.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as S
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
OFF = {"wurm_etb_returns": False, "titan_etb_returns": False,
       "shepherd_etb_returns": False}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return B.card("shilgengar", name)


def game(board=(), **cfg):
    g = B.fresh("shilgengar", board=list(board), **{**EXTRA_CFG, **cfg})
    for o in g.opponents:
        o.bodies = [OPP.PodBody(2, 2), OPP.PodBody(5, 4)]
        o.creatures = 2.0
    return g


def bodies(g):
    return [[b.toughness for b in o.bodies] for o in g.opponents]


def names(zone):
    return sorted(getattr(x, "card", x).name for x in zone)


def dead_shepherd(g):
    """A Shepherd that was on the battlefield and has just died: a bare
    Permanent, its card in the graveyard. Built by hand, not through
    `make_permanent`, so the setup reads no cast flag."""
    c = card("Twilight Shepherd")
    g.graveyard.append(c)
    return EN.Permanent(card=c, sick=False)


def counting_shepherd(g):
    calls = []
    real = g.shepherd_etb

    def wrapped():
        calls.append(1)
        real()
    g.shepherd_etb = wrapped
    return calls


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    g.make_permanent(card("Massacre Wurm"))
    check("A Wurm off the cast path: the toughness-2 bodies die",
          bodies(g), [[5], [5], [5]])

    g = game()
    g.resolve(card("Massacre Wurm"))
    check("B Wurm through resolve: the kill, no second ETB",
          (bodies(g), g.m["wurm_etb_returns"]), ([[5], [5], [5]], 0))

    g = game()
    g.graveyard = [card("Viscera Seer")]
    g.make_permanent(card("Sun Titan"))
    check("C Sun Titan off the cast path: Viscera Seer back",
          (names(g.board), g.graveyard), (["Sun Titan", "Viscera Seer"], []))

    g = game()
    g.graveyard = [card("Viscera Seer"), card("Cartel Aristocrat")]
    g.resolve(card("Sun Titan"))
    check("D Sun Titan through resolve: one card back, not two",
          (len(g.board), len(g.graveyard)), (2, 1))

    g = game()
    seer = card("Viscera Seer")
    g.graveyard = [seer]
    g.to_yard_this_turn.add(id(seer))
    g.make_permanent(card("Twilight Shepherd"))
    check("E Shepherd off the cast path: this turn's card to hand",
          (names(g.hand), g.graveyard), (["Viscera Seer"], []))

    g = game()
    shep = dead_shepherd(g)
    calls = counting_shepherd(g)
    g.shepherd_persists(shep)
    check("F Shepherd's persist: its ETB once",
          (len(calls), g.m["shepherd_etb_returns"]), (1, 1))

    g = game(**OFF)
    g.graveyard = [card("Viscera Seer")]
    g.to_yard_this_turn.add(id(g.graveyard[0]))
    g.make_permanent(card("Massacre Wurm"))
    g.make_permanent(card("Sun Titan"))
    g.make_permanent(card("Twilight Shepherd"))
    check("G all three off: nothing fires",
          (bodies(g), names(g.graveyard), g.hand),
          ([[2, 5], [2, 5], [2, 5]], ["Viscera Seer"], []))

    g = game(shepherd_etb_returns=False)
    shep = dead_shepherd(g)
    calls = counting_shepherd(g)
    g.shepherd_persists(shep)
    check("H shepherd_etb_returns=False: persist fires it once",
          len(calls), 1)

    g = game(board=B.lands("shilgengar", "Plains", "Plains", "Plains"))
    g.commander_cast, g.blood = True, 6
    g.graveyard = [card("Sun Titan"), card("Viscera Seer"),
                   card("Cartel Aristocrat"), card("Mind Stone")]
    g.shilgengar_ultimate()
    check("I the ultimate: each once, Titan takes Mind Stone",
          (sorted(n for n in names(g.board) if n != "Plains"), g.graveyard),
          (["Cartel Aristocrat", "Mind Stone", "Sun Titan", "Viscera Seer"],
           []))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z254: returned creatures' ETBs\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_mp = S.ShilgengarGame.make_permanent
    real_wurm = S.ShilgengarGame.wurm_etb
    real_knobs = dict(S.CREATURE_ETB_KNOBS)

    def ignore_cast(self, card, *a, cast=False, **k):
        return real_mp(self, card, *a, **k)

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_mp(v):
        S.ShilgengarGame.make_permanent = v

    def set_knobs(v):
        S.CREATURE_ETB_KNOBS.clear()
        S.CREATURE_ETB_KNOBS.update(v)

    def set_wurm(v):
        S.ShilgengarGame.wurm_etb = v

    muts = {
        "all three switches off everywhere": (
            {"A", "C", "E", "F", "I"}, set_cfg, OFF, {}),
        "make_permanent ignores its cast flag": (
            {"B", "D"}, set_mp, ignore_cast, real_mp),
        "CREATURE_ETB_KNOBS without Sun Titan": (
            {"C", "I"}, set_knobs,
            {k: v for k, v in real_knobs.items() if k != "Sun Titan"},
            real_knobs),
        "wurm_etb does nothing": (
            {"A", "B"}, set_wurm, lambda self, card: None, real_wurm),
    }
    bad = 0
    for label, (want, setter, value, restore) in muts.items():
        print(f"-- {label}")
        setter(value)
        try:
            broke = run_cases()
        finally:
            setter(restore)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
