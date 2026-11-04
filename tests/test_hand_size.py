#!/usr/bin/env python3
"""Pin the cleanup step: discard to seven at the end of your turn (§0z171).

    python -m tests.test_hand_size
    python -m tests.test_hand_size --mutate   # 5 mutations, exact sets

CR 514.1: "the active player discards down to their maximum hand size", seven
by CR 402.2. No engine did it before 2026-11-04 (queue item 30, found in
§0z162). `engine.cleanup_step` is the rule, once, and every engine calls it at
the end of each of its own turns.

CASES
  A karlov, ten cards in hand, no Tower: three are discarded, seven kept,
    and the three are in the GRAVEYARD (where reanimation and regrowth look)
  B the three are the want order's tail (`engine.want_order`): keep the best
    seven
  C Reliquary Tower on the battlefield: nothing is discarded
  D lorehold with Library of Leng out: nothing is discarded
  E Necropotence out: "Whenever you discard a card, exile that card from your
    graveyard" -- the three never stay in the graveyard
  F lorehold with Monument to Endurance, nine in hand: two go by the
    rummage's pick, Monument draws on the first (its first mode), the hand is
    eight again, and CR 514.3a's second cleanup step discards one more
  G `hand_size_rule=False` restores the old games: nothing is discarded
  H every engine calls `cleanup_step` in a played game (each module's own
    reference, counted)
  J two EQUAL cards in hand (two Swamps, distinct objects): the one discarded
    is the one that leaves the hand -- no object ends in hand AND graveyard
    (`remove_exact`; `remove_card` took the first equal one, §0z171)
  I the generator reads the text: "You have no maximum hand size." is True,
    Ultima's reminder text is not a static, and any other text about the
    maximum RAISES (`tag_flying.no_max_hand_size`) -- and the generated set
    holds Reliquary Tower and Library of Leng

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  hand_size_rule False (cfg)           -> A, B, E, F
  NO_MAX_HAND_SIZE emptied             -> C, D
  put_discarded ignores Necropotence   -> E
  cleanup_repeat_max 1 (cfg)           -> F
  remove_exact is remove_card          -> J

UNMUTATED (§0z15): G is the switch itself. H is blind to WHERE in the turn the
call sits -- that it follows the end step and precedes the pod's round is read
off the source, not tested -- and I is a pure function of text.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
from edhmc.decks import _evasion
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import DECKS
from tools.tag_flying import no_max_hand_size

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
KDECK, KCMD = build_pending("karlov")
LDECK, LCMD = build_pending("lorehold")
KCARD = {c.name: c for c in KDECK}
LCARD = {c.name: c for c in LDECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def karlov(hand_n=10, extra=()):
    g = KA.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20, **CFG), 1)
    g.board = EN.Board()
    for card in extra:
        g.board.append(EN.Permanent(card=card, sick=False))
    spells = [c for c in KDECK if not c.is_land and c.name not in
              ("Reliquary Tower", "Necropotence")]
    g.hand = spells[:hand_n]
    g.graveyard = []
    return g


def lorehold(hand_n, extra=()):
    g = LO.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, turns=20, **CFG), 1)
    g.board = EN.Board()
    for card in extra:
        g.board.append(EN.Permanent(card=card, sick=False))
    g.hand = [c for c in LDECK if not c.is_land
              and c.name not in ("Library of Leng", "Monument to Endurance")
              ][:hand_n]
    g.graveyard = []
    g.monument_used = set()
    return g


def names(cards):
    return sorted(c.name for c in cards)


def run_cases():
    PASS.clear()
    FAIL.clear()
    g = karlov()
    order = EN.want_order(g, list(g.hand))
    n = EN.cleanup_step(g)
    check("A ten in hand: three discarded to the graveyard, seven kept",
          (n, len(g.hand), len(g.graveyard)), (3, 7, 3))
    check("B the discards are the want order's tail",
          names(g.graveyard), names(order[7:]))

    g = karlov(extra=[KCARD["Reliquary Tower"]])
    check("C Reliquary Tower: no maximum hand size",
          (EN.cleanup_step(g), len(g.hand)), (0, 10))

    g = lorehold(10, extra=[LCARD["Library of Leng"]])
    check("D Library of Leng: no maximum hand size",
          (EN.cleanup_step(g, pick=LO.rummage_discard_choice,
                           after=LO.discard_triggers), len(g.hand)), (0, 10))

    g = karlov(extra=[KCARD["Necropotence"]])
    n = EN.cleanup_step(g)
    check("E Necropotence exiles every discard",
          (n, len(g.graveyard), g.m["necro_discard_exiled"]), (3, 0, 3))

    g = lorehold(9, extra=[LCARD["Monument to Endurance"]])
    n = EN.cleanup_step(g, pick=LO.rummage_discard_choice,
                        after=LO.discard_triggers)
    check("F Monument draws, and a second cleanup step discards again",
          (n, len(g.hand), g.m["monument_triggers"],
           sorted(g.monument_used)), (3, 7, 3, ["drain", "draw", "treasure"]))

    CFG_SAVED = dict(CFG)
    CFG["hand_size_rule"] = False
    g = karlov()
    check("G hand_size_rule=False: nothing discarded",
          (EN.cleanup_step(g), len(g.hand)), (0, 10))
    CFG.clear()
    CFG.update(CFG_SAVED)

    calls = {}
    for deck, spec in DECKS.items():
        mod = spec.engine_module
        real = mod.cleanup_step

        def counting(g, *a, _d=deck, _r=real, **k):
            calls[_d] = calls.get(_d, 0) + 1
            return _r(g, *a, **k)
        mod.cleanup_step = counting
        try:
            d, c = build_pending(deck)
            spec.sim(d, c, dict(DEFAULT_CFG, turns=6), 5000)
        finally:
            mod.cleanup_step = real
    check("H every engine calls cleanup_step in a played game",
          sorted(d for d in DECKS if calls.get(d, 0) > 0), sorted(DECKS))

    import copy
    g = karlov(hand_n=6)
    swamp = next(c for c in KDECK if c.name == "Swamp")
    a, b = copy.copy(swamp), copy.copy(swamp)
    g.hand = [a] + g.hand + [b]
    EN.cleanup_step(g)
    gy = {id(c) for c in g.graveyard}
    check("J two equal cards: the one discarded is the one that leaves",
          (len(g.hand) + len(g.graveyard),
           sum(1 for c in g.hand if id(c) in gy)), (8, 0))

    raised = False
    try:
        no_max_hand_size("X", "Your maximum hand size is increased by one.")
    except ValueError:
        raised = True
    check("I the generator reads hand-size text, and raises on the rest",
          (no_max_hand_size("T", "You have no maximum hand size.\n{T}: Add {C}."),
           no_max_hand_size("U", "End the turn. (The player discards down to "
                                 "their maximum hand size.)"),
           raised, sorted(_evasion.NO_MAX_HAND_SIZE)),
          (True, False, True, ["Library of Leng", "Reliquary Tower"]))
    return set(FAIL)


def main():
    if not MUTATE:
        print("the cleanup step: discard to seven (§0z171)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_put = EN.put_discarded

    def put_ignores_necro(g, card):
        g.graveyard.append(card)

    real_set = EN.NO_MAX_HAND_SIZE
    real_exact = EN.remove_exact
    muts = [("hand_size_rule False", {"A", "B", "E", "F"},
             {"hand_size_rule": False}, None),
            ("NO_MAX_HAND_SIZE emptied", {"C", "D"}, {},
             ("NO_MAX_HAND_SIZE", frozenset())),
            ("put_discarded ignores Necropotence", {"E"}, {},
             ("put_discarded", put_ignores_necro)),
            ("cleanup_repeat_max 1", {"F"}, {"cleanup_repeat_max": 1}, None),
            ("remove_exact is remove_card", {"J"}, {},
             ("remove_exact", EN.remove_card))]
    bad = 0
    for label, want, cfg, patch in muts:
        print(f"-- {label}")
        CFG.clear()
        CFG.update(cfg)
        if patch:
            setattr(EN, patch[0], patch[1])
        try:
            broke = run_cases()
        finally:
            CFG.clear()
            EN.put_discarded = real_put
            EN.NO_MAX_HAND_SIZE = real_set
            EN.remove_exact = real_exact
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
