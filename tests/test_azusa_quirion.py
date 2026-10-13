#!/usr/bin/env python3
"""Quirion Ranger in azusa (item 24, change 0): KNOWN_BLIND as "untaps a
target creature once a turn for no modelled payoff" -- but in this deck the
COST is the payoff.

    python -m tests.test_azusa_quirion
    python -m tests.test_azusa_quirion --mutate   # 5 mutations, exact sets

    Quirion Ranger {G} 1/1   (Scryfall, verified 2026-10-13)
    Return a Forest you control to its owner's hand: Untap target creature.
    Activate only once each turn.

CASES
  A  a land drop left, no land to play, a TAPPED Forest out: it is returned
     and replayed -- one land played, one landfall, the Forest untapped
  B  a land in hand: the Ranger is not used
  C  once each turn: two drops and nothing to play is ONE bounce
  D  a token Forest is never returned (it would cease to exist)
  E  no Ranger, no bounce
  F  a tapped Forest is returned before an untapped one (the mana line)
  G  `quirion_bounce=False`: no bounce

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  quirion_ranger_bounce never bounces          -> A, C, F
  the once-a-turn guard is gone                -> C
  a token Forest may be returned               -> D
  an untapped Forest is preferred              -> F
  the knob is ignored                          -> G

The first run of "an untapped Forest is preferred" broke A instead of F:
that mutant flipped every Forest's tapped state around the call, which
changed the INPUT rather than the preference. It is now the engine's body
with the key reversed. The mutant was fixed, not the expectation.

UNMUTATED (§0z15): B and E are gates read only by the plain run -- B by
`land_step` asking the Ranger only when `choose_land` found nothing, E by
`has`.
"""
import sys

import edhmc.azusa as AZ
from edhmc.azusa import AzusaGame
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Board, Card, Permanent
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = M.build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def named(name):
    return next(c for c in DECK if c.name == name)


def forest():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"G"}))


def filler(n):
    return [Card(name=f"F{i}", types=frozenset({"Sorcery"}), cost={"gen": 9})
            for i in range(n)]


def game(*perms, drops=1, ranger=True, **cfg):
    g = AzusaGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **cfg), 1234)
    g.board = Board()
    g.hand, g.graveyard = [], []
    g.library = filler(20)
    g.turn = 5
    g.land_drops_used = 0
    g.land_drops_for_turn = lambda: drops
    if ranger:
        g.board.append(Permanent(card=named("Quirion Ranger"), sick=False))
    for p in perms:
        g.board.append(p)
    return g


def land(tapped=False, token=False):
    return Permanent(card=forest(), sick=False, tapped=tapped, is_token=token)


def forests_on(g):
    return [p for p in g.board if p.card.name == "Forest"]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    g = game(land(tapped=True))
    g.land_step()
    fs = forests_on(g)
    check("A a tapped Forest is returned and replayed",
          (g.m["lands_played"], g.m["quirion_bounces"],
           g.m["quirion_tapped_bounces"], len(fs), fs[0].tapped if fs else None),
          (1, 1, 1, 1, False))

    g = game(land(tapped=True))
    g.hand = [forest()]
    g.land_step()
    check("B a land in hand: no bounce",
          (g.m["lands_played"], g.m["quirion_bounces"]), (1, 0))

    g = game(land(tapped=True), land(tapped=True), drops=2)
    g.land_step()
    check("C once each turn",
          (g.m["lands_played"], g.m["quirion_bounces"]), (1, 1))

    g = game(land(tapped=True, token=True))
    g.land_step()
    check("D a token Forest is never returned", g.m["quirion_bounces"], 0)

    g = game(land(tapped=True), ranger=False)
    g.land_step()
    check("E no Ranger, no bounce", g.m["quirion_bounces"], 0)

    g = game(land(tapped=False), land(tapped=True))
    g.land_step()
    check("F the tapped Forest first", g.m["quirion_tapped_bounces"], 1)

    g = game(land(tapped=True), quirion_bounce=False)
    g.land_step()
    check("G the knob off: no bounce", g.m["quirion_bounces"], 0)

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Quirion Ranger (azusa, item 24)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = AzusaGame.quirion_ranger_bounce

    def no_guard(self):
        self.quirion_turn = None
        return real(self)

    def tokens_ok(self):
        saved = [p for p in self.board if p.is_token]
        for p in saved:
            p.is_token = False
        try:
            return real(self)
        finally:
            for p in saved:
                p.is_token = True

    def untapped_first(self):
        # The engine's own body with the preference key reversed.
        if (not self.cfg.get("quirion_bounce", True)
                or not self.has("Quirion Ranger")
                or getattr(self, "quirion_turn", None) == self.turn):
            return False
        pool = [p for p in self.board
                if p.card.is_land and AZ.is_forest(p.card) and not p.is_token
                and not p.card.is_creature and self.animation_of(p) is None]
        if not pool:
            return False
        pick = max(pool, key=lambda p: (not p.tapped, p.card.name == "Forest"))
        self.board.remove(pick)
        self.hand.append(pick.card)
        self.quirion_turn = self.turn
        self.m["quirion_bounces"] += 1
        self.m["quirion_tapped_bounces"] += int(pick.tapped)
        return True

    def ignore_knob(self):
        self.cfg = dict(self.cfg, quirion_bounce=True)
        return real(self)

    muts = {
        "quirion_ranger_bounce never bounces":
            ({"A", "C", "F"}, AzusaGame, "quirion_ranger_bounce",
             lambda self: False),
        "the once-a-turn guard is gone":
            ({"C"}, AzusaGame, "quirion_ranger_bounce", no_guard),
        "a token Forest may be returned":
            ({"D"}, AzusaGame, "quirion_ranger_bounce", tokens_ok),
        "an untapped Forest is preferred":
            ({"F"}, AzusaGame, "quirion_ranger_bounce", untapped_first),
        "the knob is ignored":
            ({"G"}, AzusaGame, "quirion_ranger_bounce", ignore_knob),
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
