#!/usr/bin/env python3
"""Bloodghast in shilgengar (item 24, change 0): KNOWN_BLIND for want of
code -- "not worth the engine complexity", its note said.

    python -m tests.test_shilgengar_bloodghast
    python -m tests.test_shilgengar_bloodghast --mutate   # 6 mutations

    Bloodghast {B}{B} 2/1   (Scryfall, verified 2026-10-13)
    This creature can't block. / This creature has haste as long as an
    opponent has 10 or less life. / Landfall -- Whenever a land you control
    enters, you may return this card from your graveyard to the battlefield.

CASES
  A  a land played with Bloodghast in the graveyard: it returns
  B  no land played: it stays in the graveyard
  C  a Bloodghast carrying a finality counter is not returned (§0z75)
  D  an opponent at 10 life: a summoning-sick Bloodghast attacks
  E  ... at 11 it does not
  F  the aristocrats step sacrifices it when a land in hand will bring it
     back (Viscera Seer, Blood Artist out)
  G  ... and not with no land in hand
  H  ... and not under `bloodghast_fodder=False`

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  bloodghast_landfall does nothing             -> A
  landfall ignores the finality counter        -> C
  bloodghast_hasty is always False             -> D
  bloodghast_hasty is always True              -> E
  bloodghast_fodder ignores the land in hand   -> G
  bloodghast_fodder offers nothing             -> F

The first run of the finality mutation broke A as well: the mutant omitted
the `bloodghast_returns` counter, so it differed from the engine in two ways.
The mutant was fixed, not the expectation.

UNMUTATED (§0z15): B's gate is `land_step`'s "did a land enter", read only
by the plain run; H is a knob read.
"""
import sys

import edhmc.engine as EN
import edhmc.shilgengar as SH
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = SM.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return next(c for c in DECK if c.name == name)


def body(name="Bear", p=2, t=2):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=t)


def perm(c, sick=False):
    return EN.Permanent(card=c, sick=sick, base_p=c.power, base_t=c.toughness)


def game(*perms, **cfg):
    g = SH.ShilgengarGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **cfg), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(20)]
    g.turn = 5
    g.land_drops, g.land_drops_used = 1, 0
    for o in g.opponents:
        o.life = 40.0
        o.creatures = 0.0
    for p in perms:
        g.board.append(p)
    return g


def on_board(g, c):
    return any(p.card is c for p in g.board)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    ghast = card("Bloodghast")
    swamp = card("Swamp")

    g = game()
    g.graveyard = [ghast]
    g.hand = [swamp]
    g.land_step()
    check("A a land enters: Bloodghast returns",
          (on_board(g, ghast), ghast in g.graveyard, g.m["bloodghast_returns"]),
          (True, False, 1))

    g = game()
    g.graveyard = [ghast]
    g.land_step()
    check("B no land: it stays", ghast in g.graveyard, True)

    g = game()
    g.graveyard = [ghast]
    g.finality.add(id(ghast))
    g.hand = [swamp]
    g.land_step()
    check("C a finality Bloodghast stays", on_board(g, ghast), False)

    g = game(perm(ghast, sick=True))
    g.opponents[1].life = 10.0
    g.combat()
    check("D an opponent at 10: it attacks with haste",
          (g.board[0].tapped, g.m["bloodghast_hasty"]), (True, 1))

    g = game(perm(ghast, sick=True))
    g.opponents[1].life = 11.0
    g.combat()
    check("E at 11 it does not", g.board[0].tapped, False)

    def fodder_game(**cfg):
        g = game(perm(card("Viscera Seer")), perm(card("Blood Artist")),
                 perm(ghast), **cfg)
        return g

    g = fodder_game()
    g.hand = [swamp]
    g.aristocrats_step()
    check("F sacrificed when a land in hand brings it back",
          (on_board(g, ghast), ghast in g.graveyard), (False, True))

    g = fodder_game()
    g.aristocrats_step()
    check("G not with no land in hand", on_board(g, ghast), True)

    g = fodder_game(bloodghast_fodder=False)
    g.hand = [swamp]
    g.aristocrats_step()
    check("H not for the naive pilot", on_board(g, ghast), True)

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Bloodghast (shilgengar, item 24)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    G = SH.ShilgengarGame

    def landfall_any(self):
        for c in [c for c in self.graveyard if c.name == "Bloodghast"]:
            self.graveyard.remove(c)
            self.creature_entered(self.make_permanent(c, sick=True))
            self.m["bloodghast_returns"] += 1

    def fodder_no_land(self):
        if not self.cfg.get("bloodghast_fodder", True):
            return []
        return [p for p in self.board if p.card.name == "Bloodghast"
                and not p.is_token and not p.sick]

    muts = {
        "bloodghast_landfall does nothing":
            ({"A"}, G, "bloodghast_landfall", lambda self: None),
        "landfall ignores the finality counter":
            ({"C"}, G, "bloodghast_landfall", landfall_any),
        "bloodghast_hasty is always False":
            ({"D"}, G, "bloodghast_hasty", lambda self: False),
        "bloodghast_hasty is always True":
            ({"E"}, G, "bloodghast_hasty", lambda self: True),
        "bloodghast_fodder ignores the land in hand":
            ({"G"}, G, "bloodghast_fodder", fodder_no_land),
        "bloodghast_fodder offers nothing":
            ({"F"}, G, "bloodghast_fodder", lambda self: []),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
