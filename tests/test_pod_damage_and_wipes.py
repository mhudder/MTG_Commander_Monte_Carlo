#!/usr/bin/env python3
"""Pin three rules that six engines implement and nothing checked agreed.

    python -m tests.test_pod_damage_and_wipes
    python -m tests.test_pod_damage_and_wipes --mutate

THREE FIXES, ONE FILE, because they are one failure wearing three faces: a
rule written once per engine, drifting, with no check that the copies mean the
same thing (CLAUDE.md's "THE SAME RULE, IMPLEMENTED TWICE, IS IMPLEMENTED TWO
DIFFERENT WAYS").

1. `deal_pod_damage` DIVIDED A FULL-POD TOTAL BY THE LIVING COUNT.
   Every caller writes its amount for a full pod -- `9.0` commented "each of 3
   opponents loses 3", `6.0` for Guttersnipe's 2 apiece -- and the divisor
   shrank as opponents died while the numerator did not. "Each opponent loses
   1" dealt 1.5 apiece with two players left and 3.0 with one. The bias runs
   one way and it runs in the endgame, which is where drain converts to a win.
   `tivit.py` was the only engine that came out right, and it got there by
   multiplying its two call sites by the living count -- cancelling a divisor
   the other five were being wronged by. See `opponents.pod_size`.

2. YOUR OWN SWEEPER IGNORED INDESTRUCTIBLE; THE POD'S DID NOT.
   `resolve_own_wipe` called `board.remove()` directly while `board_wipe` went
   through `destroy()`. Same effect, two rules, decided by who cast it. Live in
   two of six BUILT lists — shilgengar (Avacyn + Damn/Wrath of God) and rendmaw
   (Erebos + Culling Ritual) — and Avacyn is the sharp case: she grants
   indestructible to your whole board and your own Wrath was ignoring it.

   Heliod, Sun-Crowned is used as the specimen below because it is a real card
   with the real keyword; note it is a karlov CANDIDATE, not a karlov deck
   member, so the fix is inert in that list until it is staged in.

   The branch is taken from the SWEEPER'S OWN ORACLE TEXT, not from
   `destroy_share`'s coin flip, because your own wipe is a named card whose
   text the deck list states. Every classification in
   `opponents.WIPE_IGNORES_INDESTRUCTIBLE` / `WIPE_DESTROYS` was read from
   api.scryfall.com on 2026-09-11 and is quoted beside the name.

3. A WRATH KILLED THINGS THAT ARE NOT CREATURES.
   `opponents.py` asked `card.is_creature` -- the type line AS PLAYED -- at
   every site, while the engine's own combat step has always used
   `is_battlefield_creature`. So a permanent could be too-not-a-creature to
   attack and creature enough to die to a board wipe. All three affected cards
   sit in the rendmaw list alongside its two sweepers: Grist (a Planeswalker
   once it lands), an Impending Overlord, and Erebos below devotion 5.

`--mutate` restores all three old rules and asserts exactly the cases that
depend on the fixes fail.
"""
import random
import sys

from edhmc import opponents as OPP
from edhmc.engine import Game, Card, Permanent
from edhmc.decks import discover_current_decks
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

# The mutant is the pre-fix set of rules, each behind its own knob.
#
# `pod_reads_battlefield_creatures` is the switch for the third fix, and it is
# NOT `battlefield_creature_types`: that one gates only the NEVER stamp applied
# at ETB, so it does nothing to a case like the ones below that set `impending`
# directly, and nothing to the devotion clause either. Reusing it would have
# produced a mutation run that passed while claiming to restore the old rule.
MUT = {"pod_damage_full_pod": False, "own_wipe_indestructible": False,
       "pod_reads_battlefield_creatures": False}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(extra=None, deck=None, cmd=None):
    """A Game with the pod built and nothing played."""
    from edhmc.decks.rendmaw_v12 import build
    d, c = build()
    cfg = dict(DEFAULT_CFG, **(MUT if MUTATE else {}), **(extra or {}))
    return Game(list(deck or d), cmd or c, cfg, random.Random(1), seed_for_pod=1)


def alive(g, n):
    """Leave exactly `n` opponents alive, each on full life."""
    for o in g.opponents[n:]:
        o.alive, o.life = False, 0.0
    return [o.life for o in OPP.living(g)]


def creature(name, p=2, t=2, indestructible=False):
    return Card(name=name, types=frozenset({"Creature"}), power=p, toughness=t,
                indestructible=indestructible)


# ---------------------------------------------------------------------------
# 1. "each opponent loses N" means N, whoever is left
# ---------------------------------------------------------------------------

def test_pod_total_is_per_opponent():
    print("\n'each opponent loses N' after an elimination")
    for n in (3, 2, 1):
        g = game()
        before = alive(g, n)
        # engine.on_creature_death's Meathook branch: "each opponent loses 1
        # life", one creature dying, one copy on the battlefield.
        g.deal_pod_damage(3.0 * 1 * 1)
        lost = [round(b - o.life, 3) for b, o in zip(before, OPP.living(g))]
        check(f"Meathook with {n} opponent(s) alive costs each of them 1.0",
              lost, [1.0] * n)

    for n in (3, 2, 1):
        g = game()
        before = alive(g, n)
        g.deal_pod_damage(9.0)          # Baba Lysaga, "each of 3 loses 3"
        lost = [round(b - o.life, 3) for b, o in zip(before, OPP.living(g))]
        check(f"Baba Lysaga with {n} opponent(s) alive costs each of them 3.0",
              lost, [3.0] * n)


def test_tivit_call_sites_agree():
    """tivit's two sites were the ones compensating; they must agree now."""
    print("\ntivit's own call sites, on the same scale as everyone else's")
    for n in (3, 2, 1):
        g = game()
        before = alive(g, n)
        # tivit.py's Tyrant's Choice, verbatim: a POD TOTAL for 4 apiece.
        g.deal_pod_damage(4.0 * len(g.opponents))
        lost = [round(b - o.life, 3) for b, o in zip(before, OPP.living(g))]
        check(f"Tyrant's Choice with {n} opponent(s) alive costs each 4.0",
              lost, [4.0] * n)


def test_single_target_is_untouched():
    """`each=False` never divided and must not start."""
    print("\nsingle-target drain is not a pod total and is unaffected")
    for n in (3, 2, 1):
        g = game()
        alive(g, n)
        low = min(OPP.living(g), key=lambda o: o.life)
        before = low.life
        g.deal_pod_damage(1.0, each=False)     # Blood Artist
        check(f"Blood Artist with {n} alive drains exactly 1 from one player",
              round(before - low.life, 3), 1.0)


# ---------------------------------------------------------------------------
# 2. your own sweeper obeys the same indestructible rule the pod's does
# ---------------------------------------------------------------------------

def wipe_board(sweeper_name, board, cfg=None):
    """Cast `sweeper_name` into `board`; return the names left behind."""
    g = game(cfg)
    for c in board:
        g.board.append(Permanent(card=c, sick=False))
    card = Card(name=sweeper_name, types=frozenset({"Sorcery"}), tags=("wipe",))
    OPP.resolve_own_wipe(g, card=card)
    return sorted(p.card.name for p in g.board)


def test_own_wipe_honours_indestructible():
    print("\nyour own sweeper, against an indestructible body")
    board = [creature("Bear"), creature("Heliod, Sun-Crowned",
                                        indestructible=True)]
    check("Wrath of God ('Destroy all creatures') leaves Heliod",
          wipe_board("Wrath of God", board), ["Heliod, Sun-Crowned"])
    check("Damn (overloaded, destroys) leaves Heliod",
          wipe_board("Damn", board), ["Heliod, Sun-Crowned"])
    check("Blasphemous Act (13 DAMAGE, not destruction) still leaves Heliod",
          wipe_board("Blasphemous Act", board), ["Heliod, Sun-Crowned"])


def test_own_wipe_that_gets_around_it():
    print("\n...and against the three sweepers whose text gets around it")
    board = [creature("Bear"), creature("Heliod, Sun-Crowned",
                                        indestructible=True)]
    check("Toxic Deluge (-X/-X) kills Heliod anyway",
          wipe_board("Toxic Deluge", board), [])
    check("Farewell (EXILE all creatures) kills Heliod anyway",
          wipe_board("Farewell", board), [])
    check("Promise of Loyalty (SACRIFICE the rest) kills Heliod anyway",
          wipe_board("Promise of Loyalty", board), [])


def test_avacyn_grants_it_to_the_whole_board():
    """The sharp case: she protects everything, and your Wrath was ignoring it."""
    print("\nAvacyn grants indestructible to everything you control")
    board = [creature("Bear"), creature("Serra Angel"),
             creature("Avacyn, Angel of Hope", indestructible=True)]
    check("Wrath of God with Avacyn out is a blank",
          wipe_board("Wrath of God", board),
          ["Avacyn, Angel of Hope", "Bear", "Serra Angel"])
    check("...and Farewell still exiles the lot",
          wipe_board("Farewell", board), [])


def test_pod_wipe_and_own_wipe_agree():
    """The invariant that makes the rest worth having: the SAME sweeper effect
    kills the same things whoever cast it."""
    print("\nthe pod's wipe and yours now answer the same question")
    board = [creature("Bear"), creature("Heliod, Sun-Crowned",
                                        indestructible=True)]
    g = game()
    for c in board:
        g.board.append(Permanent(card=c, sick=False))
    # The pod's destroy-effect branch: roll below destroy_share == "it said
    # destroy", which is what a Wrath is.
    for p in list(g.board):
        OPP.destroy(g, p, roll=0.0)
    theirs = sorted(p.card.name for p in g.board)
    mine = wipe_board("Wrath of God", board)
    check("a destroy-wipe spares Heliod from either side of the table",
          mine, theirs)


# ---------------------------------------------------------------------------
# 3. the name set is a claim, so it is checked
# ---------------------------------------------------------------------------

def test_wipe_coverage():
    print("\nevery `wipe`-tagged card in every live deck is classified")
    decks = {n: mod.build()[0] for n, mod in discover_current_decks().items()}
    stale = OPP.check_wipe_coverage(decks)      # raises on an unclassified card
    check("check_wipe_coverage() passes on the six live decks", True, True)
    if stale:
        print(f"    NOTE: classified but in no current deck: {', '.join(stale)}")

    # ...and prove the check can fail, which is the only thing that makes it
    # worth having (§0q).
    fake = dict(decks)
    fake["_probe"] = [Card(name="Nevinyrral's Disk",
                           types=frozenset({"Artifact"}), tags=("wipe",))]
    try:
        OPP.check_wipe_coverage(fake)
    except SystemExit:
        check("...and RAISES on a `wipe` card in neither set", True, True)
    else:
        check("...and RAISES on a `wipe` card in neither set", False, True)


# ---------------------------------------------------------------------------
# 4. a wrath kills CREATURES, not everything with Creature on its type line
# ---------------------------------------------------------------------------

def test_wipe_reads_the_battlefield_not_the_type_line():
    """`opponents.py` asked `card.is_creature` — the type line AS PLAYED."""
    print("\na sweeper and the three cards that are not creatures on the board")
    from edhmc.engine import NEVER
    from edhmc.decks.rendmaw_v12 import build as rendmaw_build
    rdeck, _ = rendmaw_build()
    by = {c.name: c for c in rdeck}
    sweeper = Card(name="Wrath of God", types=frozenset({"Sorcery"}),
                   tags=("wipe",))

    # Grist: "As long as Grist ISN'T ON THE BATTLEFIELD, it's a 1/1 Insect
    # creature" — so on the battlefield it is a bare Planeswalker.
    g = game()
    g.board = type(g.board)()
    g.board.append(Permanent(card=by["Grist, the Hunger Tide"], sick=False,
                             impending=NEVER))
    g.board.append(Permanent(card=creature("Bear"), sick=False))
    OPP.resolve_own_wipe(g, card=sweeper)
    check("a Wrath leaves Grist, which is a Planeswalker on the battlefield",
          sorted(p.card.name for p in g.board), ["Grist, the Hunger Tide"])

    # Overlord deployed for Impending: "isn't a creature until the last time
    # counter is removed".
    for turn, want in ((2, ["Overlord of the Hauntwoods"]), (7, [])):
        g = game()
        g.board = type(g.board)()
        g.turn = turn
        p = Permanent(card=by["Overlord of the Hauntwoods"], sick=False)
        p.impending = 6
        g.board.append(p)
        OPP.resolve_own_wipe(g, card=sweeper)
        label = ("an IMPENDING Overlord survives while it is an enchantment"
                 if turn == 2 else
                 "...and dies once the last time counter is gone")
        check(label, sorted(p.card.name for p in g.board), want)

    # The narrowing must not broaden: a plain creature still dies.
    g = game()
    g.board = type(g.board)()
    g.board.append(Permanent(card=creature("Bear"), sick=False))
    OPP.resolve_own_wipe(g, card=sweeper)
    check("an ordinary creature still dies to the same Wrath",
          sorted(p.card.name for p in g.board), [])


def main():
    print(__doc__.split("\n\n")[0])
    if MUTATE:
        print("\nMUTATION RUN: pod_damage_full_pod=False, "
              "own_wipe_indestructible=False\n")
    test_pod_total_is_per_opponent()
    test_tivit_call_sites_agree()
    test_single_target_is_untouched()
    test_own_wipe_honours_indestructible()
    test_own_wipe_that_gets_around_it()
    test_avacyn_grants_it_to_the_whole_board()
    test_pod_wipe_and_own_wipe_agree()
    test_wipe_reads_the_battlefield_not_the_type_line()
    test_wipe_coverage()

    print(f"\n  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        # What the two old rules should and should not break:
        #   pod damage   only the 2-alive and 1-alive rows; 3-alive is the case
        #                the old divisor got right, and single-target never
        #                divided at all.
        #   own wipe     only the sweepers that DESTROY. The three that get
        #                around indestructible killed Heliod under the old rule
        #                too -- by being wrong for the right reason -- so they
        #                must still pass, and the agreement case fails because
        #                only one side of it moved.
        expected = {
            "Meathook with 2 opponent(s) alive costs each of them 1.0",
            "Meathook with 1 opponent(s) alive costs each of them 1.0",
            "Baba Lysaga with 2 opponent(s) alive costs each of them 3.0",
            "Baba Lysaga with 1 opponent(s) alive costs each of them 3.0",
            "Tyrant's Choice with 2 opponent(s) alive costs each 4.0",
            "Tyrant's Choice with 1 opponent(s) alive costs each 4.0",
            "Wrath of God ('Destroy all creatures') leaves Heliod",
            "Damn (overloaded, destroys) leaves Heliod",
            "Blasphemous Act (13 DAMAGE, not destruction) still leaves Heliod",
            "Wrath of God with Avacyn out is a blank",
            "a destroy-wipe spares Heliod from either side of the table",
            "a Wrath leaves Grist, which is a Planeswalker on the battlefield",
            "an IMPENDING Overlord survives while it is an enchantment",
        }
        actual = set(FAIL)
        if actual == expected:
            print("  MUTATION CHECK OK -- exactly the 13 cases that depend on "
                  "the three fixes failed. The ones that did NOT are the "
                  "three-opponent rows, single-target drain, and the three "
                  "sweepers that get around indestructible: all three were "
                  "already killing the right thing, for the wrong reason.")
            return 0
        print(f"  MUTATION CHECK FAILED\n"
              f"    only in expected: {sorted(expected - actual)}\n"
              f"    only in actual:   {sorted(actual - expected)}")
        return 1
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
