#!/usr/bin/env python3
"""§0z261: eight of shilgengar's missing clauses (fix 6).

    python -m tests.test_fix6
    python -m tests.test_fix6 --mutate   # 5 mutations, exact sets

Oracle text in each method's docstring (Scryfall, 2026-11-25). Every case
builds its board by hand on `test_oracle_remainder.fresh("shilgengar")`.

CASES
  F  Flawless Maneuver: with the commander on the battlefield and no mana,
     the response is cast free; without the commander and no mana, it is not
  M  Mind Stone: six lands and {1} spare -- cracked for a card; with five
     lands it stays
  S  Viscera Seer, the commander not cast, a land on top with five lands
     out: the scry bottoms it
  P  Priest of Fell Rites' unearth: the Priest in the graveyard, Sun Titan
     there too, {3}{W}{B}: Sun Titan returns, the Priest is gone (exiled),
     3 life paid
  B1 Black Market Connections at 40 life: all three modes -- a card, a
     Treasure, a 3/2 Shapeshifter -- and 6 life
  B2 ... at 23 life: the card only (the floor of 20)
  R  Resplendent Angel attacking with {3}{W}{W}{W} up: pumped -- +2 power,
     lifelink
  G  Giada: ready, an Angel's cost loses one {W}; summoning sick, nothing
  C  Cartel Aristocrat aimed at, a token beside it: the token is sacrificed
     and the removal stopped; aimed at another creature, nothing
  N  NEIGHBOUR: every switch off -- F, M, P, B1, R, G and C's first halves
     do nothing

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  every switch off everywhere                     -> F, M, S, P, B1, R, G, C
  free_with_commander ignores the commander       -> F
  mind_stone_min_lands at 0                       -> M
  bmc_life_floor at 0                             -> B2
  giada_ready ignores summoning sickness          -> G

UNMUTATED (§0z15): N is the switches' neighbour. Its first run had the
Mind Stone's six Plains on the board where Flawless was cast, so Flawless
was simply PAID; its Flawless half has no lands now (the setup, not the
rule; the expected value unchanged).
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as S
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
OFF = {"flawless_free": False, "mind_stone_draw": False, "seer_scry": False,
       "priest_unearth": False, "bmc_modes": False,
       "resplendent_pump": False, "giada_mana": False,
       "cartel_protects": False}
CMD = B.LISTS["shilgengar"][1]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return B.card("shilgengar", name)


def game(board=(), **cfg):
    g = B.fresh("shilgengar", board=list(board), **{**EXTRA_CFG, **cfg})
    g.treasures = 0
    return g


def lands(*names):
    return B.lands("shilgengar", *names)


def perm(g, name):
    return next((p for p in g.board if p.card.name == name), None)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game(board=[CMD])
    fm = card("Flawless Maneuver")
    g.hand = [fm]
    a = OPP._cast_response(g, fm, "protect")
    g = game()
    g.hand = [fm]
    b = OPP._cast_response(g, fm, "protect")
    check("F Flawless: free with the commander out, not without", (a, b),
          (True, False))

    g = game(board=lands(*["Plains"] * 6) + [card("Mind Stone")])
    g.mind_stone_crack()
    m6 = (perm(g, "Mind Stone") is None, g.m["mind_stone_draws"])
    g = game(board=lands(*["Plains"] * 5) + [card("Mind Stone")])
    g.mind_stone_crack()
    check("M Mind Stone: cracked at six lands, kept at five",
          (m6, perm(g, "Mind Stone") is not None), ((True, 1), True))

    g = game(board=lands(*["Plains"] * 5) + [card("Viscera Seer")])
    top = lands("Swamp")[0]
    g.library.append(top)
    g.seer_scry()
    check("S Viscera Seer's scry bottoms a land", g.library[0] is top, True)

    g = game(board=lands("Plains", "Swamp", "Plains", "Swamp", "Plains"))
    g.graveyard = [card("Priest of Fell Rites"), card("Sun Titan")]
    life = g.your_life
    g.priest_unearth()
    check("P the unearth: Sun Titan back, the Priest exiled, 3 life",
          (perm(g, "Sun Titan") is not None,
           any(c.name == "Priest of Fell Rites" for c in g.graveyard),
           perm(g, "Priest of Fell Rites") is None, life - g.your_life),
          (True, False, True, 3.0))

    g = game(board=[card("Black Market Connections")])
    g.your_life = 40.0
    hand = len(g.hand)
    g.black_market_step()
    check("B1 at 40 life: a card, a Treasure, a Shapeshifter, 6 life",
          (len(g.hand) - hand, g.treasures,
           perm(g, "Shapeshifter token") is not None, g.your_life),
          (1, 1, True, 34.0))

    g = game(board=[card("Black Market Connections")])
    g.your_life = 23.0
    g.black_market_step()
    check("B2 at 23 life: the card only",
          (g.treasures, perm(g, "Shapeshifter token") is None, g.your_life),
          (0, True, 21.0))

    g = game(board=lands("Plains", "Plains", "Plains", "Swamp", "Swamp",
                         "Swamp") + [card("Resplendent Angel")])
    angel = perm(g, "Resplendent Angel")
    power = g.power_of(angel)
    g.resplendent_step([angel])
    check("R Resplendent: +2 power and lifelink",
          (g.power_of(angel) - power, bool(g.lifelink_of(angel))), (2, True))

    g = game(board=[card("Giada, Font of Hope")])
    angel = card("Angel of Despair")
    ready = g.giada_cost(angel, dict(angel.cost))
    perm(g, "Giada, Font of Hope").sick = True
    sick = g.giada_cost(angel, dict(angel.cost))
    check("G Giada: one {W} off an Angel when ready; nothing when sick",
          (ready.get("W"), sick.get("W")),
          (angel.cost["W"] - 1, angel.cost["W"]))

    g = game(board=[card("Cartel Aristocrat"), card("Viscera Seer")])
    tok = g.make_creature_token(EN.Card(name="Spirit token",
                                        types=frozenset({"Creature"}),
                                        power=1, toughness=1))
    arist = perm(g, "Cartel Aristocrat")
    saved = g.self_protects(arist)
    other = g.self_protects(perm(g, "Viscera Seer"))
    check("C Cartel Aristocrat: the token dies, the removal stopped; not "
          "for another creature",
          (saved, tok in g.board, other), (True, False, False))

    g = game(board=[CMD, card("Cartel Aristocrat"), card("Viscera Seer")],
             **OFF)
    fm = card("Flawless Maneuver")
    g.hand = [fm]
    results = (OPP._cast_response(g, fm, "protect"),
               g.self_protects(perm(g, "Cartel Aristocrat")))
    g = game(board=lands(*["Plains"] * 6) + [card("Mind Stone")], **OFF)
    g.graveyard = [card("Priest of Fell Rites"), card("Sun Titan")]
    g.mind_stone_crack()
    g.priest_unearth()
    check("N every switch off: nothing",
          (results, perm(g, "Mind Stone") is not None,
           perm(g, "Sun Titan") is None), ((False, False), True, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z261: fix 6, eight clauses\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_free = OPP.free_with_commander
    real_ready = S.ShilgengarGame.giada_ready

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_free(v):
        OPP.free_with_commander = v

    def set_ready(v):
        S.ShilgengarGame.giada_ready = v

    def free_anyway(g, c):
        # the commander check dropped, the switch kept: the first stand-in
        # dropped both, and broke N too (§0z141's shape, caught on the run)
        return (c.name in OPP.FREE_WITH_COMMANDER
                and g.cfg.get("flawless_free", True))

    def ready_sick(self):
        return next((p for p in self.board
                     if p.card.name == "Giada, Font of Hope"
                     and not p.tapped), None)

    muts = {
        "every switch off everywhere": (
            {"F", "M", "S", "P", "B1", "R", "G", "C"}, set_cfg, OFF, {}),
        "free_with_commander ignores the commander": (
            {"F"}, set_free, free_anyway, real_free),
        "mind_stone_min_lands at 0": (
            {"M"}, set_cfg, {"mind_stone_min_lands": 0}, {}),
        "bmc_life_floor at 0": ({"B2"}, set_cfg, {"bmc_life_floor": 0}, {}),
        "giada_ready ignores summoning sickness": (
            {"G"}, set_ready, ready_sick, real_ready),
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
