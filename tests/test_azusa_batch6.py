#!/usr/bin/env python3
"""Pin the seven landfall payoffs of azusa batch 6 (2026-10-03, §0z101).

    python -m tests.test_azusa_batch6
    python -m tests.test_azusa_batch6 --mutate   # 8 mutations, exact sets

The batch-3/4 shape: put the permanent on the battlefield, fire the trigger,
assert the printed effect. One case per clause, plus the ORDER and SNAPSHOT
claims, which are the ones that look right and are not:

  * A landfall trigger belongs to the permanents that were there WHEN THE LAND
    ENTERED. A Racetrack Bird made by a land does not pump off it -- even with
    Greenwarden doubling the Racetrack -- and a Springheart copy of Mossborn
    Hydra made by a land is not doubled by it (E, R).
  * Mossborn Hydra's doubling is ordered after every counter of the same land
    (Bristly Bill's), and Glacier Godmaw's pump after every token, as a pilot
    stacks them (Q, Y).
  * Dancing from Dark to Dawn reads creature SPELLS: a tutored creature is not
    cast (I).

CASES
  A  Elfsworn Giant: a 1/1 Elf Warrior per landfall
  B  ... doubled by Ancient Greenwarden
  C  Chocobo Racetrack: a 2/2 Bird per landfall
  D  a Bird gets +1/+0 for each LATER land this turn
  E  with Greenwarden, no Bird sees the land that made it
  F  the Birds' pump ends with the turn
  G  Dancing from Dark to Dawn: a 2/2 Bear per landfall
  H  ... a creature spell cast in the main phase puts MV counters on a creature
  I  ... a tutored creature puts none
  J  Mole Man: graveyard lands are playable with him and not without
  K  ... a Moloid per landfall
  L  a Moloid mills on attack while graveyard play is live and a drop is unused
  M  ... and not when every land drop is spent
  N  Mossborn Hydra enters with a +1/+1 counter
  O  ... doubles per landfall: three lands, eight counters
  P  ... twice per land with Greenwarden
  Q  Bristly Bill's counter lands BEFORE the Hydra doubles
  R  a Springheart copy of the Hydra made by a land is not doubled by it
  S  counter_target="focus": evasive beats power, the Hydra beats both
  T  Bill's activation doubles every creature's counters, precombat
  U  ... and is not taken below `bristly_min_counters`
  V  Avenger of Zendikar pumps Bristly Bill, who is a Plant
  W  Glacier Godmaw's ETB makes a Lander token
  X  a Lander is cracked precombat: a tapped Forest, a landfall, no Lander
  Y  Godmaw's pump and haste reach the tokens the same land made
  Z  a sick creature Godmaw hasted attacks
  AA a +1/+1 counter on a */* card adds to its land count
  AB the land-enabler check reads `_landfall_payoffs` now
  AC the 0/0 check accepts Mossborn Hydra (it enters with a counter)
  AD counter_target="spread": the smallest creature, and the Hydra still first

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  ENTERS_WITH_COUNTERS is empty              -> N, O, P, Q, R, AC
  trigger lists read live, not snapshotted   -> E, R, AB
  Godmaw resolves FIRST, before token makers -> Y, AB
  power_of discards counters on a */* card   -> AA
  PLANT is empty                             -> V
  creature_spell_cast does nothing           -> H
  yard_land_access forgets Mole Man          -> J, L
  counter_target ignores its policy knob     -> AD   (added with AD, before
                                                     its first run)

TWO OF THESE SETS WERE WRONG ON THE FIRST RUN, and the error is recorded
rather than edited away: both mutations that WRAP `_landfall_payoffs` also
broke AB. `check_land_enabler_coverage` reads the SOURCE of the method bound
on the class, and a wrapper's source names none of the cards -- so with the
wrapper in place, dropping Elfsworn Giant from LAND_ENABLERS no longer raises.
That is the check working as written (it watches whatever is bound), not an
engine defect, and it is worth knowing: a monkeypatched payoff method blinds
the coverage check. AB was added to both sets after that run.

UNMUTATED (§0z15): A, B, C, D, F, G, K, M, S, T, U, W, X, Z are each the
card's own one line, with no seam a mutation could separate from the case;
AB is itself a check of a check.
"""
import sys

import edhmc.azusa as AZ
from edhmc.azusa import AzusaGame
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    deck, cmd = M.build()
    return AzusaGame(deck, cmd, dict(DEFAULT_CFG, turns=20, **cfg), 1234)


def forest():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"G"}))


def landfall(g, n=1):
    for _ in range(n):
        land = forest()
        g.make_permanent(land)
        g.land_entered(land, played=True)


def named(name):
    return next(c for c in M.build()[0] if c.name == name)


def toks(g, name):
    return [p for p in g.board if p.is_token and p.card.name == name]


def put(g, card, sick=False):
    return g.make_permanent(card, sick=sick)


def untapped_forests(g, n):
    for _ in range(n):
        p = g.make_permanent(forest())
        p.tapped = False


def run_cases():
    PASS.clear()
    FAIL.clear()
    GW = named("Ancient Greenwarden")

    # ---- Elfsworn Giant ---------------------------------------------------
    g = fresh()
    put(g, M.ELFSWORN_GIANT)
    landfall(g, 2)
    t = toks(g, "Elf Warrior token")
    check("A Elfsworn Giant makes a 1/1 Elf Warrior per landfall",
          (len(t), {(g.power_of(p), g.toughness_of(p)) for p in t}),
          (2, {(1, 1)}))

    g = fresh()
    put(g, M.ELFSWORN_GIANT)
    put(g, GW)
    landfall(g, 1)
    check("B Greenwarden doubles Elfsworn Giant's trigger",
          len(toks(g, "Elf Warrior token")), 2)

    # ---- Chocobo Racetrack ------------------------------------------------
    g = fresh()
    put(g, M.CHOCOBO_RACETRACK)
    landfall(g, 1)
    t = toks(g, "Bird token")
    check("C Chocobo Racetrack makes a 2/2 Bird per landfall",
          [(g.power_of(p), g.toughness_of(p)) for p in t], [(2, 2)])

    g = fresh()
    put(g, M.CHOCOBO_RACETRACK)
    landfall(g, 3)
    t = toks(g, "Bird token")
    check("D a Bird gets +1/+0 for each LATER land this turn",
          (sorted(g.power_of(p) for p in t),
           {g.toughness_of(p) for p in t}), ([2, 3, 4], {2}))

    g = fresh()
    put(g, M.CHOCOBO_RACETRACK)
    put(g, GW)
    landfall(g, 1)
    check("E with Greenwarden, neither Bird sees the land that made it",
          sorted(g.power_of(p) for p in toks(g, "Bird token")), [2, 2])

    g = fresh(opponents=False)
    put(g, M.CHOCOBO_RACETRACK)
    landfall(g, 3)
    g.hand = []
    g.library = [named("Kozilek, Butcher of Truth"),
                 named("Ulamog, the Infinite Gyre"),
                 named("Craterhoof Behemoth")]
    g.commander_cast = True
    AZ.take_turn(g)
    check("F the Birds' pump ends with the turn",
          sorted(g.power_of(p) for p in toks(g, "Bird token")), [2, 2, 2])

    # ---- Dancing from Dark to Dawn ----------------------------------------
    g = fresh()
    put(g, M.DANCING_FROM_DARK_TO_DAWN)
    landfall(g, 1)
    t = toks(g, "Bear token")
    check("G Dancing makes a 2/2 Bear per landfall",
          [(g.power_of(p), g.toughness_of(p)) for p in t], [(2, 2)])

    g = fresh()
    put(g, M.DANCING_FROM_DARK_TO_DAWN)
    giant = put(g, M.ELFSWORN_GIANT)
    untapped_forests(g, 5)
    g.commander_cast = True
    g.hand = [named("Lotus Cobra")]
    g.main_phase()
    check("H a creature spell cast puts MV counters on a creature you control",
          (g.m["dancing_counters"], giant.counters), (2, 2))

    g = fresh()
    put(g, M.DANCING_FROM_DARK_TO_DAWN)
    put(g, M.ELFSWORN_GIANT)
    before = sum(1 for p in g.board if p.card.is_creature)
    g.tutor_creature(3)
    check("I a tutored creature is not cast and puts no counters",
          (sum(1 for p in g.board if p.card.is_creature) - before,
           g.m["dancing_counters"]), (1, 0))

    # ---- Mole Man, Moloid Master ------------------------------------------
    g = fresh()
    g.graveyard.append(forest())
    without = any(z == "graveyard" for _, z in g.playable_lands())
    put(g, M.MOLE_MAN)
    with_him = any(z == "graveyard" for _, z in g.playable_lands())
    check("J graveyard lands are playable with Mole Man and not without",
          (without, with_him), (False, True))

    g = fresh()
    put(g, M.MOLE_MAN)
    landfall(g, 2)
    t = toks(g, "Moloid token")
    check("K Mole Man makes a 1/1 Moloid per landfall",
          (len(t), {(g.power_of(p), g.toughness_of(p)) for p in t}),
          (2, {(1, 1)}))

    def moloid_attack(drops_spent):
        g = fresh()
        put(g, M.MOLE_MAN)
        g.make_tokens(1, 1, 1, "Moloid")
        for p in g.board:
            p.sick = False
        g.land_drops_used = g.land_drops_for_turn() if drops_spent else 0
        yard = len(g.graveyard)
        g.combat()
        return g.m["moloid_mills"], len(g.graveyard) - yard

    check("L a Moloid mills on attack while a land drop is unused",
          moloid_attack(False), (1, 1))
    check("M ... and does not when every land drop is spent",
          moloid_attack(True), (0, 0))

    # ---- Mossborn Hydra ---------------------------------------------------
    g = fresh()
    h = put(g, M.MOSSBORN_HYDRA)
    check("N Mossborn Hydra enters with a +1/+1 counter",
          (h.counters, g.power_of(h), g.toughness_of(h)), (1, 1, 1))

    g = fresh()
    h = put(g, M.MOSSBORN_HYDRA)
    landfall(g, 3)
    check("O Mossborn Hydra doubles per landfall: three lands, eight counters",
          h.counters, 8)

    g = fresh()
    h = put(g, M.MOSSBORN_HYDRA)
    put(g, GW)
    landfall(g, 1)
    check("P with Greenwarden one land doubles it twice", h.counters, 4)

    g = fresh()
    h = put(g, M.MOSSBORN_HYDRA)
    put(g, M.BRISTLY_BILL)
    landfall(g, 1)
    check("Q Bristly Bill's counter lands BEFORE the Hydra doubles",
          h.counters, 4)

    g = fresh()
    h = put(g, M.MOSSBORN_HYDRA)
    put(g, named("Springheart Nantuko"))
    g.springheart_host = h
    h.counters += 1                     # "enchanted creature gets +1/+1"
    untapped_forests(g, 3)
    landfall(g, 1)
    copies = [p for p in g.board if p.is_token
              and p.card.name == "Mossborn Hydra"]
    check("R a Springheart copy of the Hydra made by a land is not doubled "
          "by it", (h.counters, [p.counters for p in copies]), (4, [1]))

    # ---- Bristly Bill, Spine Sower ----------------------------------------
    g = fresh(counter_target="focus")
    put(g, M.BRISTLY_BILL)
    put(g, named("Kozilek, Butcher of Truth"))
    put(g, named("Rampaging Baloths"))
    first = g.counter_target().card.name
    put(g, M.MOSSBORN_HYDRA)
    second = g.counter_target().card.name
    check("S counter_target='focus': evasive beats power, the Hydra beats both",
          (first, second), ("Rampaging Baloths", "Mossborn Hydra"))

    g = fresh()
    put(g, M.BRISTLY_BILL)
    a = put(g, M.ELFSWORN_GIANT)
    b = put(g, named("Kozilek, Butcher of Truth"))
    a.counters, b.counters = 2, 1
    untapped_forests(g, 5)
    g.precombat_step()
    check("T Bill's activation doubles every creature's counters, precombat",
          (a.counters, b.counters, g.m["bristly_activations"],
           g.m["bristly_counters_added"]), (4, 2, 1, 3))

    g = fresh()
    put(g, M.BRISTLY_BILL)
    a = put(g, M.ELFSWORN_GIANT)
    a.counters = 1
    untapped_forests(g, 10)
    g.precombat_step()
    check("U ... and is not taken below bristly_min_counters",
          (a.counters, g.m["bristly_activations"]), (1, 0))

    # "focus" so Bill's OWN counter goes to the 5/5 Avenger and this case
    # pins Avenger's half alone. Under the default "spread" Bill, the smallest
    # creature, takes his own counter as well -- V failed exactly that way the
    # day the default flipped, which is the policy working, not Avenger.
    g = fresh(counter_target="focus")
    put(g, named("Avenger of Zendikar"))
    bill = put(g, M.BRISTLY_BILL)
    landfall(g, 1)
    check("V Avenger of Zendikar pumps Bristly Bill, who is a Plant",
          bill.counters, 1)

    # ---- Glacier Godmaw ---------------------------------------------------
    g = fresh()
    gm = put(g, M.GLACIER_GODMAW)
    g.etb(M.GLACIER_GODMAW, gm)
    check("W Glacier Godmaw's ETB makes a Lander token",
          (len(toks(g, "Lander token")), g.m["landers_made"]), (1, 1))

    g = fresh()
    g.make_lander()
    untapped_forests(g, 2)
    lands = sum(1 for p in g.board if p.card.is_land)
    lf = g.m["landfall_triggers"]
    g.precombat_step()
    new = [p for p in g.board if p.card.is_land][-1]
    check("X a Lander is cracked precombat: a tapped Forest and a landfall",
          (g.m["landers_cracked"], len(toks(g, "Lander token")),
           sum(1 for p in g.board if p.card.is_land) - lands,
           g.m["landfall_triggers"] - lf, new.card.name, new.tapped),
          (1, 0, 1, 1, "Forest", True))

    g = fresh()
    gm = put(g, M.GLACIER_GODMAW)
    put(g, named("Rampaging Baloths"))
    landfall(g, 1)
    beast = toks(g, "Beast token")[0]
    check("Y Godmaw's pump and haste reach the token the same land made",
          ((g.power_of(beast), g.toughness_of(beast)),
           id(beast) in g.eot_haste, g.power_of(gm)), ((5, 5), True, 7))

    g = fresh()
    put(g, M.GLACIER_GODMAW)
    koz = put(g, named("Kozilek, Butcher of Truth"), sick=True)
    landfall(g, 1)
    g.combat()
    check("Z a sick creature Godmaw hasted attacks",
          (koz.tapped, g.m["godmaw_hasted"]), (True, 1))

    # ---- the engine fixes the batch depends on ----------------------------
    g = fresh()
    gs = put(g, named("Greensleeves, Maro-Sorcerer"))
    gs.counters = 2
    check("AA a +1/+1 counter on a */* card adds to its land count",
          g.power_of(gs), g.land_count() + 2)

    saved = AZ.LAND_ENABLERS
    AZ.LAND_ENABLERS = saved - {"Elfsworn Giant"}
    try:
        AZ.check_land_enabler_coverage()
        raised = False
    except AssertionError:
        raised = True
    finally:
        AZ.LAND_ENABLERS = saved
    check("AB the land-enabler check reads _landfall_payoffs", raised, True)

    try:
        AZ.check_dynamic_pt_coverage()
        ok = True
    except AssertionError:
        ok = False
    check("AC the 0/0 check accepts Mossborn Hydra", ok, True)

    g = fresh(counter_target="spread")
    put(g, M.BRISTLY_BILL)
    put(g, named("Kozilek, Butcher of Truth"))
    put(g, named("Rampaging Baloths"))
    small = put(g, M.MOLE_MAN)               # 1/1, the smallest
    first = g.counter_target() is small
    put(g, M.MOSSBORN_HYDRA)
    second = g.counter_target().card.name
    check("AD counter_target='spread': the smallest creature, the Hydra first",
          (first, second), (True, "Mossborn Hydra"))

    return set(FAIL)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------
REAL_LAST = AzusaGame._landfall_last
REAL_PAYOFFS = AzusaGame._landfall_payoffs
REAL_YARD = AzusaGame.yard_land_access


def live_last(self, reps, hydras, godmaws):
    return REAL_LAST(self, reps,
                     [p for p in self.board if p.card.name == "Mossborn Hydra"],
                     [p for p in self.board if p.card.name == "Glacier Godmaw"])


def live_payoffs(self, card, played=False, birds=()):
    return REAL_PAYOFFS(self, card, played,
                        [p for p in self.board
                         if p.is_token and p.card.name == "Bird token"])


def godmaw_first_payoffs(self, card, played=False, birds=()):
    for gm in [p for p in self.board if p.card.name == "Glacier Godmaw"]:
        for p in self.board:
            if self.counts_as_creature(p):
                self.add_eot(p, 1, 1)
                if p.sick:
                    self.eot_haste[id(p)] = p
    return REAL_PAYOFFS(self, card, played, birds)


def godmaw_first_last(self, reps, hydras, godmaws):
    return REAL_LAST(self, reps, hydras, [])


def old_power_of(self, perm):
    anim = self.animation_of(perm) if perm.card.is_land else None
    if anim is not None:
        return (anim["power"] + perm.counters + self._pump(perm)
                + self._eot(perm, 1))
    base = perm.base_p if perm.is_token else perm.card.power
    p = base + perm.counters
    if perm.card.name in AZ.DYNAMIC_PT_LANDS:
        p = self.land_count()
    return p + self._pump(perm) + self._eot(perm, 1)


def yard_without_mole_man(self):
    return (self.has("Ramunap Excavator") or self.has("Crucible of Worlds")
            or self.has("Conduit of Worlds")
            or self.has("Ancient Greenwarden")
            or self.has("Walk-In Closet // Forgotten Cellar"))


def focus_only(self):
    mine = [p for p in self.board
            if p.card.is_creature and not p.card.is_land]
    if not mine:
        return None
    hydra = [p for p in mine if p.card.name == "Mossborn Hydra"]
    if hydra:
        return hydra[0]
    return max(mine, key=lambda p: (
        AZ.OPP.flying_of(self, p) or AZ.OPP.trample_of(self, p),
        self.power_of(p)))


MUTATIONS = {
    "ENTERS_WITH_COUNTERS is empty":
        ({"N", "O", "P", "Q", "R", "AC"},
         [(AZ, "ENTERS_WITH_COUNTERS", {})]),
    "trigger lists read live, not snapshotted":
        ({"E", "R", "AB"},
         [(AzusaGame, "_landfall_last", live_last),
          (AzusaGame, "_landfall_payoffs", live_payoffs)]),
    "Godmaw resolves FIRST, before token makers":
        ({"Y", "AB"},
         [(AzusaGame, "_landfall_last", godmaw_first_last),
          (AzusaGame, "_landfall_payoffs", godmaw_first_payoffs)]),
    "power_of discards counters on a */* card":
        ({"AA"}, [(AzusaGame, "power_of", old_power_of)]),
    "PLANT is empty":
        ({"V"}, [(AZ, "PLANT", frozenset())]),
    "creature_spell_cast does nothing":
        ({"H"}, [(AzusaGame, "creature_spell_cast", lambda self, c: None)]),
    "yard_land_access forgets Mole Man":
        ({"J", "L"}, [(AzusaGame, "yard_land_access", yard_without_mole_man)]),
    "counter_target ignores its policy knob":
        ({"AD"}, [(AzusaGame, "counter_target", focus_only)]),
}


def main():
    if not MUTATE:
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for label, (want, patches) in MUTATIONS.items():
        print(f"-- {label}")
        real = [(o, n, getattr(o, n)) for o, n, _ in patches]
        for o, n, v in patches:
            setattr(o, n, v)
        try:
            broke = run_cases()
        finally:
            for o, n, v in real:
                setattr(o, n, v)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(MUTATIONS) - bad} passed, {bad} failed "
          f"({len(MUTATIONS)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
