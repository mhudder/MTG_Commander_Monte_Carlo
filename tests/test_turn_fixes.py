#!/usr/bin/env python3
"""§0z185: three of §0z184's turn-structure findings, fixed.

    python -m tests.test_turn_fixes
    python -m tests.test_turn_fixes --mutate   # 5 mutations, exact sets

  3. The pod's END STEPS on pod turns 1 and 2 (`pod_end_steps_early`): the
     hook sat under removal's pod-turn-3 gate.
  4. Rendmaw's "at the beginning of EACH upkeep" cards at each opponent's
     upkeep (`rendmaw_seat_upkeeps`, `Game.pod_upkeep`): Tendershoot Dryad
     made the round's four Saprolings at your upkeep; Ophiomancer checked
     your upkeep only.
  5. Victory Chimes / Bender's Waterskin ("Untap this artifact during each
     other player's untap step") give ONE mana in each opponent's turn, with
     Lorehold out or not, and are not in your end-of-turn float as well
     (`cross_turn_untaps`).

CASES
  A  seat order, pod turn 1: opponents 0, 1, 2 each have an end step
  B  NEIGHBOUR: `pod_end_steps_early=False`: none on pod turn 1
  C  NEIGHBOUR: pod turn 3: all three, with the switch on or off
  D  the old round (`pod_seat_turns=False`), pod turn 1: all three
  E  Tendershoot: your upkeep makes ONE Saproling, each opponent's upkeep
     one more -- four a round
  F  NEIGHBOUR: `rendmaw_seat_upkeeps=False`: four at your upkeep, none at
     theirs
  G  Ophiomancer at opponents' upkeeps: a Snake, then none while it lives,
     then one again once it is gone
  H  Lorehold not out, one Victory Chimes: each opponent's upkeep adds one
     mana to the float
  I  your end-of-turn float leaves out an untapped Victory Chimes
  J  NEIGHBOUR: `cross_turn_untaps=False`: H adds nothing, I counts it

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  pod_end_steps_early=False everywhere      -> A, D
  rendmaw_seat_upkeeps=False everywhere     -> E, G
  cross_turn_untaps=False everywhere        -> H, I
  Game.pod_upkeep is a no-op                -> E, G
  lorehold.cross_turn_count returns 0       -> H

UNMUTATED (§0z15): B, C, F and J are the neighbours. The fifth mutation
leaves I standing because the float's exclusion reads the tag itself, not
the count -- so a count that stopped counting would show in H alone.
"""
import sys

import edhmc.engine as E
import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
REND = build_pending("rendmaw")
LORE = build_pending("lorehold")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return dict(DEFAULT_CFG, watch=frozenset(), **{**EXTRA_CFG, **kw})


def rendmaw(turn=1, **kw):
    lst, cmd = REND
    g = E.Game(list(lst), cmd, cfg(**kw), E.make_rng(3, cfg(**kw)),
               seed_for_pod=3)
    g.opening_hand()
    g.board = E.Board()
    g.turn = turn
    for o in g.opponents:
        o.kill_turn, o.life = 99, float(10 ** 9)
    return g


def card(deck, name):
    return next(c for c in deck[0] if c.name == name)


def end_steps(turn, **kw):
    """The seats whose end step ran in one pod round at `turn`."""
    g = rendmaw(turn=turn, **kw)
    seen = []
    real = E.Game.pod_end_step
    E.Game.pod_end_step = lambda self, i: seen.append(i)
    try:
        OPP.pod_phase(g)
    finally:
        E.Game.pod_end_step = real
    return seen


def saprolings(g):
    return sum(1 for p in g.board if p.is_token
               and p.card.name.startswith("Saproling"))


def snakes(g):
    return sum(1 for p in g.board if p.is_token
               and p.card.name.startswith("Snake"))


def lorehold(**kw):
    lst, cmd = LORE
    g = L.LoreholdGame(list(lst), cmd, cfg(**kw), 3)
    g.opening_hand()
    g.board = E.Board()
    g.board.append(Permanent(card=card(LORE, "Victory Chimes"), sick=False))
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    check("A seat order, pod turn 1: three end steps", end_steps(1),
          [0, 1, 2])
    check("B pod_end_steps_early=False: none on pod turn 1",
          end_steps(1, pod_end_steps_early=False), [])
    check("C pod turn 3: three, switch on or off",
          (end_steps(3), end_steps(3, pod_end_steps_early=False)),
          ([0, 1, 2], [0, 1, 2]))
    check("D the old round, pod turn 1: three end steps",
          end_steps(1, pod_seat_turns=False), [0, 1, 2])

    g = rendmaw(turn=4)
    g.board.append(Permanent(card=card(REND, "Tendershoot Dryad"), sick=False))
    E.upkeep(g)
    own = saprolings(g)
    for i in range(3):
        g.pod_upkeep(i)
    check("E Tendershoot: one at your upkeep, one at each of theirs",
          (own, saprolings(g)), (1, 4))

    g = rendmaw(turn=4, rendmaw_seat_upkeeps=False)
    g.board.append(Permanent(card=card(REND, "Tendershoot Dryad"), sick=False))
    E.upkeep(g)
    own = saprolings(g)
    for i in range(3):
        g.pod_upkeep(i)
    check("F rendmaw_seat_upkeeps=False: four at yours, none at theirs",
          (own, saprolings(g)), (4, 4))

    g = rendmaw(turn=4)
    g.board.append(Permanent(card=card(REND, "Ophiomancer"), sick=False))
    g.pod_upkeep(0)
    first = snakes(g)
    g.pod_upkeep(1)
    second = snakes(g)
    g.board = E.Board([p for p in g.board
                       if not (p.is_token and p.card.name.startswith("Snake"))])
    g.pod_upkeep(2)
    check("G Ophiomancer: a Snake, none while it lives, one once it is gone",
          (first, second, snakes(g)), (1, 1, 1))

    g = lorehold()
    g.commander_cast = False
    g.float_mana = 0
    for i in range(3):
        g.pod_upkeep(i)
    check("H Lorehold not out: each opponent's upkeep adds the Chimes' one",
          g.float_mana, 3)

    g = lorehold()
    check("I the end-of-turn float leaves out an untapped Chimes",
          L.end_of_turn_float(g), 0)

    g = lorehold(cross_turn_untaps=False)
    g.commander_cast = False
    g.float_mana = 0
    for i in range(3):
        g.pod_upkeep(i)
    check("J cross_turn_untaps=False: none added, the float counts it",
          (g.float_mana, L.end_of_turn_float(lorehold(cross_turn_untaps=False))),
          (0, 1))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z185: the pod's early end steps, rendmaw's seat upkeeps, "
              "the cross-turn untaps\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "pod_end_steps_early=False everywhere":
            ({"A", "D"}, None, {"pod_end_steps_early": False}),
        "rendmaw_seat_upkeeps=False everywhere":
            ({"E", "G"}, None, {"rendmaw_seat_upkeeps": False}),
        "cross_turn_untaps=False everywhere":
            ({"H", "I"}, None, {"cross_turn_untaps": False}),
        "Game.pod_upkeep is a no-op":
            ({"E", "G"}, (E.Game, "pod_upkeep", lambda self, i: None), {}),
        "lorehold.cross_turn_count returns 0":
            ({"H"}, (L, "cross_turn_count", lambda g: 0), {}),
    }
    bad = 0
    for label, (want, patch, extra) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = extra
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
