#!/usr/bin/env python3
"""§0z221, A3: route-aware kills -- an opponent's clock that picks you
resolves by its ROUTE instead of ending the game (`route_kills`).

    python -m tests.test_route_kills
    python -m tests.test_route_kills --mutate   # 3 mutations, exact sets

Each case: a shilgengar game, an empty battlefield, opponent 0's clock due
on turn 6 with the route set by hand and the other two already eliminated,
and every roll -1, below any share: the clock picks you.

CASES
  A  a DRAIN kill at 50 life: you lose 40, live at 10, and the clock re-arms
     one round on
  B  a drain kill at 40 life: a loss, by the clock
  C  a COMBAT kill at 60 life, no blockers: the kill force's whole power is
     damage, and you live
  D  a combat kill at 45 with three untapped 1/1s: the hit would leave you
     under the chump floor (10), so they chump, and less gets through
  E  a COMBO kill at 1,000 life: a loss, as before
  F  Angel of Suffering and a combat kill at 30: no damage reaches you, the
     library is milled, and you live
  G  NEIGHBOUR: `route_kills` False, a drain kill at 1,000 life: a loss

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  route_kills=False                        -> A, C, D
    (CORRECTED AFTER THE RUN, said so: F was written in this set and does
    not break -- the old rule's `angel_prevents_kill` already prevented a
    combat kill, and milled for it. F pins that the new rule keeps it.)
  your blocks ignored (plan_blocks -> {})  -> D
  the kill's damage not through damage_you -> F

UNMUTATED (§0z15): B, E and G are losses under both rules; F is the Angel
under both.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {"route_kills": True}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(route, life, **cfg):
    deck, cmd = SM.build()
    g = SH.ShilgengarGame(list(deck), cmd,
                          dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}), 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(200)]
    g.turn = 6
    g.your_life = float(life)
    for o in g.opponents:
        o.life, o.creatures, o.alive = 40.0, 0.0, True
    o = g.opponents[0]
    o.route, o.kill_turn, o.clock_fired = route, 6, False
    for other in g.opponents[1:]:      # the last opponent left: it must
        other.kill_turn = 99           # pick you
        other.alive, other.life = False, 0.0
    # a roll of -1 is below any share, even an empty board's 0
    g.opp_rolls = [[[-1.0] * OPP.N_SLOTS for _ in g.opponents]
                   for _ in range(30)]
    return g, o


def soldier(g, n):
    for i in range(n):
        g.board.append(EN.Permanent(
            card=EN.Card(name=f"Soldier {i}", types=frozenset({"Creature"}),
                         power=1, toughness=1), sick=False, is_token=True))


def force_power(o):
    return sum(b.power for b in OPP.kill_force(None, o, 40))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game("drain", 50)
    OPP.resolve_clocks(g)
    check("A a drain kill at 50: live at 10, the clock re-armed",
          (g.result, g.your_life, o.kill_turn, o.clock_fired),
          (None, 10.0, 7, False))

    g, o = game("drain", 40)
    OPP.resolve_clocks(g)
    check("B a drain kill at 40: a loss by the clock",
          (g.result, g.m["loss_route"]), ("loss", 2))

    g, o = game("combat", 60)
    want = 60.0 - force_power(o)
    OPP.resolve_clocks(g)
    check("C a combat kill at 60, no blockers: the whole force is damage",
          (g.result, g.your_life), (None, want))

    g, o = game("combat", 45)          # 45 - 41 is under the chump floor
    soldier(g, 3)
    open_board = 45.0 - force_power(o)
    OPP.resolve_clocks(g)
    check("D three 1/1s block: more life left than on an open board",
          (g.result, g.your_life > open_board, g.m["kill_blocked"] >= 1),
          (None, True, True))

    g, o = game("combo", 1000)
    OPP.resolve_clocks(g)
    check("E a combo kill at 1,000 life: a loss", g.result, "loss")

    g, o = game("combat", 30)
    g.board.append(EN.Permanent(
        card=next(c for c in SM.build()[0] if c.name == "Angel of Suffering"),
        sick=False))
    lib = len(g.library)
    OPP.resolve_clocks(g)
    check("F Angel of Suffering: no damage, milled, you live",
          (g.result, g.your_life, len(g.library) < lib), (None, 30.0, True))

    g, o = game("drain", 1000, route_kills=False)
    OPP.resolve_clocks(g)
    check("G NEIGHBOUR: route_kills False, a drain at 1,000 life: a loss",
          g.result, "loss")
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z221 A3: route-aware kills\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    import edhmc.engine as ENG
    muts = {
        "route_kills=False": ({"A", "C", "D"}, {"route_kills": False},
                              []),
        "your blocks ignored": ({"D"}, {}, [
            (OPP, "plan_blocks", lambda *a, **k: {})]),
        "the kill's damage not through damage_you": ({"F"}, {}, [
            (ENG, "damage_you", lambda g, n: n)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = {"route_kills": True, **cfg}
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {"route_kills": True}
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
