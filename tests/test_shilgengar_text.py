#!/usr/bin/env python3
"""§0z215: shilgengar's cards and steps by their text -- §0z208 items 1-3
and §0z184 finding 7's timing pair.

    python -m tests.test_shilgengar_text
    python -m tests.test_shilgengar_text --mutate   # 6 mutations, exact sets

Each fix is behind its own switch, and each switch False is the old rule:

  requiem_subtypes   Requiem Angel's "non-Spirit" read from the subtype
                     (Bloodghast and Kokusho are Spirits), not the name
  landfall_each      every land that enters is a landfall: Emeria Shepherd
                     once per land (a cracked fetch is two), and Wayfarer's
                     Bauble's basic fires it
  lifelink_snapshot  combat lifelink at the power each attacker dealt, read
                     before the first gain's counters
  bmc_main1          Black Market Connections at the first main phase,
                     after the draw, not in the upkeep
  main2_order        Pearl Collector's second-main trigger BEFORE the
                     sorcery-speed activations (inert on this list: Pearl
                     Collector is not in it)

CASES
  A  Requiem Angel, Bloodghast dies: no Spirit
  B  Requiem Angel, Viscera Seer dies: one Spirit
  C  Requiem Angel, Kokusho dies: no Spirit
  D  Emeria Shepherd, a Marsh Flats played and cracked: two landfalls, so
     both nonland permanents in the graveyard come back
  E  Emeria Shepherd, Wayfarer's Bauble cracked: its basic is a landfall,
     the graveyard's permanent comes back
  F  Archangel of Thune (3) and Speaker of the Heavens (1) lifelink: 4 life
     gained, the powers they dealt
  G  Black Market Connections: no card in the upkeep, one at the first main
     phase, 2 life
  H  the turn's order: the draw, then Connections, then the land step; and
     combat, then Pearl's trigger, then the activations

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  requiem_subtypes=False                         -> A, C
  landfall_each=False                            -> D, E
  lifelink_snapshot=False                        -> F
  bmc_main1=False                                -> G
  main2_order=False                              -> H
  Emeria once per land STEP, not per land        -> D

UNMUTATED (§0z15): B is the non-Spirit that still makes one. H's first
half is `bmc_main1`'s too, but `black_market_step` is called either way
(and does nothing with the switch off), so only the second half moves.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.shilgengar import ShilgengarGame

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("shilgengar")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = ShilgengarGame(list(DECK), CMD,
                       dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                            **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    return g


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def put(g, *names, sick=False):
    out = []
    for n in names:
        p = Permanent(card=take(g, n), sick=sick)
        g.board.append(p)
        out.append(p)
    return out


def spirits(g):
    return sum(1 for p in g.board if p.card.name == "Spirit token")


def yard_permanents(g):
    return sorted(c.name for c in g.graveyard
                  if c.is_permanent and not c.is_land)


def run_cases():
    PASS.clear()
    FAIL.clear()

    for label, victim, want in (("A", "Bloodghast", 0),
                                ("B", "Viscera Seer", 1),
                                ("C", "Kokusho, the Evening Star", 0)):
        g = fresh()
        put(g, "Requiem Angel")
        v, = put(g, victim)
        OPP.destroy(g, v, destroys=True)
        check(f"{label} Requiem Angel, {victim} dies: {want} Spirit",
              spirits(g), want)

    g = fresh()
    put(g, "Emeria Shepherd")
    g.hand[:] = [take(g, "Marsh Flats")]
    g.graveyard[:] = [take(g, "Viscera Seer"), take(g, "Wayfarer's Bauble")]
    g.land_step()
    check("D a cracked fetch is two landfalls: both permanents back",
          yard_permanents(g), [])

    g = fresh()
    put(g, "Emeria Shepherd", "Wayfarer's Bauble", "Swamp", "Swamp")
    g.hand[:] = []
    g.graveyard[:] = [take(g, "Viscera Seer")]
    g.activations()
    check("E Wayfarer's Bauble's basic is a landfall",
          yard_permanents(g), [])

    g = fresh()
    attackers = put(g, "Archangel of Thune", "Speaker of the Heavens")
    gained = g.m["life_gained"]
    g.combat_lifelink(attackers)
    check("F lifelink at the powers dealt: 3 + 1",
          g.m["life_gained"] - gained, 4)

    # bmc_modes=False (§0z261): G pins the TIMING; the modes are
    # tests/test_fix6.py's B1/B2. At 40 life the modes take all three for
    # 6 life, which G's 2 was the old one-mode rule's.
    g = fresh(bmc_modes=False)
    put(g, "Black Market Connections")
    hand, life = len(g.hand), g.your_life
    g.upkeep()
    up = len(g.hand) - hand
    g.black_market_step()
    check("G Connections at the first main phase, not the upkeep",
          (up, len(g.hand) - hand, life - g.your_life), (0, 1, 2))

    g = fresh()
    log = []
    for name in ("upkeep", "land_step", "main_phase", "walker_step",
                 "combat", "activations", "speaker_step", "pearl_sink",
                 "avacyn_feed", "end_step", "black_market_step"):
        setattr(g, name, (lambda n: lambda *a, **k: log.append(n))(name))
    g.draw = lambda *a, **k: log.append("draw")
    real_pearl, real_late = SH.pearl_collector_trigger, SH.late_land_drop
    SH.pearl_collector_trigger = lambda *a, **k: log.append("pearl")
    SH.late_land_drop = lambda *a, **k: False
    try:
        SH.take_turn(g)
    finally:
        SH.pearl_collector_trigger, SH.late_land_drop = real_pearl, real_late
    order = [n for n in log if n in ("draw", "black_market_step",
                                     "land_step", "combat", "pearl",
                                     "activations")]
    check("H the turn's order",
          order, ["draw", "black_market_step", "land_step", "combat",
                  "pearl", "activations"])
    return set(FAIL)


def _emeria_once(self, lands):
    if not lands:
        return
    self.bloodghast_landfall()
    if self.has("Emeria Shepherd"):
        self.emeria_return("Plains" in EN.land_types(lands[-1].card))


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z215: shilgengar by its text\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "requiem_subtypes=False": ({"A", "C"}, None,
                                   {"requiem_subtypes": False}),
        "landfall_each=False": ({"D", "E"}, None, {"landfall_each": False}),
        "lifelink_snapshot=False": ({"F"}, None,
                                    {"lifelink_snapshot": False}),
        "bmc_main1=False": ({"G"}, None, {"bmc_main1": False}),
        "main2_order=False": ({"H"}, None, {"main2_order": False}),
        "Emeria once per land step": ({"D"}, _emeria_once, {}),
    }
    bad = 0
    for label, (want, fn, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = ShilgengarGame.landfall
        if fn is not None:
            ShilgengarGame.landfall = fn
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            ShilgengarGame.landfall = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
