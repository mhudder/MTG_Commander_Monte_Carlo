#!/usr/bin/env python3
"""§0z253: Journey of Discovery's second mode and its entwine.

    python -m tests.test_journey
    python -m tests.test_journey --mutate   # 4 mutations, exact sets

    "Choose one -- * Search your library for up to two basic land cards,
    reveal them, put them into your hand, then shuffle. * You may play up
    to two additional lands this turn. Entwine {2}{G}"
                                    ({2}{G}, Sorcery; Scryfall 2026-11-25)

Every case resolves the card directly (its own {2}{G} is the caller's), so
the untapped Forests on the board are exactly the entwine budget. The
commander is not cast and nothing grants drops: one drop a turn, unused.

CASES
  A  three Forests untapped, no land in hand: ENTWINED -- the three tapped,
     two Forests to hand, two extra drops (`land_drops_for_turn` 3)
  B  two Forests untapped, no land in hand: the basics mode, nothing tapped
  C  two untapped, three lands in hand (two spare): the drops mode, no
     search (hand and library unchanged)
  D  two untapped, two lands in hand (one spare): the basics mode
  E  NEIGHBOUR: journey_text=False, A's setup -- the old rule, two Forests,
     nothing tapped, no drops
  F  after C, a land step plays three lands, not one
  G  the extra drops end with the turn: `take_turn` resets them
  H  cast in the pre-land main phase (`journey_pre_land`)
  I  NEIGHBOUR: journey_pre_land=False -- not cast before the drops
  J  `journey_resolved`, the A/B's reach, counts under the old rule too

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  journey_text=False everywhere                     -> A, C, F, H
  land_drops_for_turn ignores the Journey drops     -> A, F
  JOURNEY_SPARE 1, not 2                            -> D
  journey_pre_land always False                     -> H

UNMUTATED (§0z15): B and D's basics are what the old rule also does; E, I
and J are neighbours. G's reset is one line in `take_turn`; no switch
reaches it, so it is pinned and not mutated. H and I put the commander on
the battlefield: the first run had her uncast, and the pre-land phase spent
the three Forests on Azusa (caught then; the expected sets unchanged).
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    """The named card out of the library, hand or graveyard: a DISTINCT
    object per call (§0z112)."""
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def game(untapped, lands_in_hand, **cfg):
    """`untapped` Forests on the battlefield, `lands_in_hand` Forests and
    Journey in hand, nothing else in hand; one land drop, unused."""
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.library.extend(g.hand)
    g.hand = []
    g.board = EN.Board()
    for _ in range(untapped):
        g.board.append(EN.Permanent(card=take(g, "Forest"), sick=False))
    journey = take(g, "Journey of Discovery")
    g.hand = [take(g, "Forest") for _ in range(lands_in_hand)] + [journey]
    g.commander_cast = False
    g.turn, g.land_drops, g.land_drops_used = 3, 1, 0
    return g, journey


def resolved(g, journey):
    EN.remove_card(g.hand, journey)
    g.resolve(journey)


def lands(zone):
    return sum(1 for c in zone if c.is_land)


def tapped(g):
    return sum(1 for p in g.board if p.tapped)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, j = game(3, 0)
    resolved(g, j)
    check("A entwined: three tapped, two Forests, three drops",
          (tapped(g), lands(g.hand), g.journey_drops,
           g.land_drops_for_turn(), g.m["journey_entwined"]),
          (3, 2, 2, 3, 1))

    g, j = game(2, 0)
    resolved(g, j)
    check("B no entwine, no land in hand: the basics",
          (tapped(g), lands(g.hand), g.journey_drops), (0, 2, 0))

    g, j = game(2, 3)
    lib = len(g.library)
    resolved(g, j)
    check("C two spare lands in hand: the drops, no search",
          (lands(g.hand), len(g.library) - lib, g.journey_drops),
          (3, 0, 2))
    g.land_step()
    check("F after C, the land step plays three",
          g.m["lands_played"], 3)

    g, j = game(2, 2)
    resolved(g, j)
    check("D one spare land: the basics",
          (lands(g.hand), g.journey_drops), (4, 0))

    g, j = game(3, 0, journey_text=False)
    resolved(g, j)
    check("E journey_text=False: the old rule",
          (tapped(g), lands(g.hand), g.journey_drops,
           g.m["journey_resolved"]), (0, 2, 0, 1))

    g, j = game(2, 3)
    g.journey_drops = 2
    AZ.take_turn(g)
    check("G the drops end with the turn", g.journey_drops, 0)

    g, j = game(3, 0)
    g.commander_cast = True              # else the pre-land phase casts her
    g.main_phase(enablers_only=True)
    check("H cast before the drops", j in g.graveyard, True)

    g, j = game(3, 0, journey_pre_land=False)
    g.commander_cast = True
    g.main_phase(enablers_only=True)
    check("I journey_pre_land=False: not cast before the drops",
          j in g.hand, True)

    g, j = game(2, 0, journey_text=False)
    resolved(g, j)
    check("J the reach counts under the old rule",
          g.m["journey_resolved"], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z253: Journey of Discovery\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_drops = AzusaGame.land_drops_for_turn
    real_pre = AZ.journey_pre_land

    def no_journey(self):
        return real_drops(self) - self.journey_drops

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_drops(v):
        AzusaGame.land_drops_for_turn = v

    def set_spare(v):
        AZ.JOURNEY_SPARE = v

    def set_pre(v):
        AZ.journey_pre_land = v

    muts = {
        "journey_text=False everywhere": (
            {"A", "C", "F", "H"}, set_cfg, {"journey_text": False}, {}),
        "land_drops_for_turn ignores the Journey drops": (
            {"A", "F"}, set_drops, no_journey, real_drops),
        "JOURNEY_SPARE 1, not 2": ({"D"}, set_spare, 1, 2),
        "journey_pre_land always False": (
            {"H"}, set_pre, lambda g: False, real_pre),
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
