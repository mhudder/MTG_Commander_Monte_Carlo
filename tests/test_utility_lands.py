#!/usr/bin/env python3
"""§0z260: azusa's utility lands -- Strip Mine, Wasteland, Ghost Quarter,
Tectonic Edge, Dust Bowl, Buried Ruin -- each sacrifice a land death of yours.

    python -m tests.test_utility_lands
    python -m tests.test_utility_lands --mutate   # 5 mutations, exact sets

Oracle text in `AzusaGame.utility_land_step`'s docstring (Scryfall,
2026-11-25). Every case calls `utility_land_step` directly on a board it
builds: six or seven untapped lands (the floor is six), Titania where a
land death must pay.

CASES
  U1 Strip Mine, Titania out: it is sacrificed -- a land death, one 5/3
  U2 Strip Mine, no Titania and no graveyard access: it stays
  U3 five lands only, Titania out: below the floor, nothing
  U4 Ghost Quarter, Titania out, a Forest left in the library: Quarter and
     one of your Forests die (two 5/3s), a Forest enters untapped from the
     library
  U5 Tectonic Edge, Titania out: not with every opponent under four lands;
     yes once one has four
  U6 Dust Bowl, Titania out, {3} spare: the TAPPED Forest is sacrificed,
     Dust Bowl stays (tapped)
  U7 Buried Ruin, Sol Ring in the graveyard, {2} spare, no Titania: Sol
     Ring to hand, the Ruin to the graveyard
  U8 NEIGHBOUR: the three switches off -- U1, U6 and U7's boards, nothing

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the three switches off everywhere           -> U1, U4, U5, U6, U7
  land_death_pays always False                -> U1, U4, U5, U6
  pod_mana_row reports nine lands             -> U5
  the floor at 0 (cryptic_caves_min_lands=0)  -> U3
  ghost_quarter_own does nothing              -> U4

UNMUTATED (§0z15): U2 and U8 are neighbours -- U2 the payoff gate's off
side, U8 the switches'.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
OFF = {"strip_lands": False, "dust_bowl_sac": False, "buried_ruin": False}
DECK, CMD = build_pending("azusa")
TITANIA = "Titania, Protector of Argoth"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def game(utility, forests=5, titania=True, **cfg):
    """`utility` and `forests` Forests on the battlefield, untapped; Titania
    if asked. One Forest is left in the library (the deck has many)."""
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.library.extend(g.hand)
    g.hand = []
    g.board = EN.Board()
    g.graveyard = []
    g.turn = 3
    for name in utility:
        g.board.append(EN.Permanent(card=take(g, name), sick=False))
    for _ in range(forests):
        g.board.append(EN.Permanent(card=take(g, "Forest"), sick=False))
    if titania:
        g.board.append(EN.Permanent(card=take(g, TITANIA), sick=False))
    return g


def names(g):
    return sorted(p.card.name for p in g.board)


def elementals(g):
    return sum(1 for p in g.board if p.card.name.startswith("Elemental"))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game(["Strip Mine"])
    g.utility_land_step()
    check("U1 Strip Mine with Titania: sacrificed, one 5/3",
          ("Strip Mine" in names(g), elementals(g),
           any(c.name == "Strip Mine" for c in g.graveyard)), (False, 1, True))

    g = game(["Strip Mine"], titania=False)
    g.utility_land_step()
    check("U2 no payoff: Strip Mine stays", "Strip Mine" in names(g), True)

    g = game(["Strip Mine"], forests=4)
    g.utility_land_step()
    check("U3 five lands: below the floor", "Strip Mine" in names(g), True)

    g = game(["Ghost Quarter"])
    lib = len(g.library)
    g.utility_land_step()
    check("U4 Ghost Quarter at your Forest: two 5/3s, a Forest found",
          (names(g).count("Forest"), elementals(g), lib - len(g.library),
           g.m["ghost_quarter_basics"]), (5, 2, 1, 1))

    g = game(["Tectonic Edge"])
    for o in g.opponents:
        o.mana_rows = tuple(OPP.PodMana(1.0, 0, 1.0, 1.0) for _ in range(30))
    g.utility_land_step()
    no = "Tectonic Edge" in names(g)
    g = game(["Tectonic Edge"])
    for o in g.opponents:
        o.mana_rows = tuple(OPP.PodMana(4.0, 0, 4.0, 4.0) for _ in range(30))
    g.utility_land_step()
    check("U5 Tectonic Edge: not under four lands, yes at four",
          (no, "Tectonic Edge" in names(g)), (True, False))

    g = game(["Dust Bowl"])
    tapped = next(p for p in g.board if p.card.name == "Forest")
    tapped.tapped = True
    g.utility_land_step()
    bowl = next((p for p in g.board if p.card.name == "Dust Bowl"), None)
    check("U6 Dust Bowl: the tapped Forest dies, the Bowl stays tapped",
          (any(p is tapped for p in g.board), bowl is not None and bowl.tapped,
           g.m["dust_bowl_sacs"]), (False, True, 1))

    g = game(["Buried Ruin"], titania=False)
    g.graveyard = [take(g, "Sol Ring")]
    g.utility_land_step()
    check("U7 Buried Ruin: Sol Ring to hand, the Ruin to the graveyard",
          ([c.name for c in g.hand], [c.name for c in g.graveyard]),
          (["Sol Ring"], ["Buried Ruin"]))

    g = game(["Strip Mine", "Dust Bowl", "Buried Ruin"], **OFF)
    g.graveyard = [take(g, "Sol Ring")]
    before = names(g)
    g.utility_land_step()
    check("U8 the switches off: nothing", (names(g), g.hand), (before, []))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z260: azusa's utility lands\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_pays = AzusaGame.land_death_pays
    real_row = OPP.pod_mana_row
    real_gq = AzusaGame.ghost_quarter_own

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_pays(v):
        AzusaGame.land_death_pays = v

    def set_row(v):
        OPP.pod_mana_row = v

    def set_gq(v):
        AzusaGame.ghost_quarter_own = v

    muts = {
        "the three switches off everywhere": (
            {"U1", "U4", "U5", "U6", "U7"}, set_cfg, OFF, {}),
        "land_death_pays always False": (
            {"U1", "U4", "U5", "U6"}, set_pays, lambda self: False, real_pays),
        "pod_mana_row reports nine lands": (
            {"U5"}, set_row,
            lambda g, o, t=None: OPP.PodMana(9.0, 0, 9.0, 9.0), real_row),
        "the floor at 0": (
            {"U3"}, set_cfg, {"cryptic_caves_min_lands": 0}, {}),
        "ghost_quarter_own does nothing": (
            {"U4"}, set_gq, lambda self: None, real_gq),
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
