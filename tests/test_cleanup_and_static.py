#!/usr/bin/env python3
"""§0z187 and §0z188: "until end of turn" ends at cleanup, a land drawn in
main 2, tivit's sick mana creatures, and Beastmaster Ascension's static.

    python -m tests.test_cleanup_and_static
    python -m tests.test_cleanup_and_static --mutate   # 8 mutations, exact sets

  §0z187 1. CR 514.2: "until end of turn" effects end in YOUR cleanup step
            (`engine.end_turn_effects`, `eot_at_cleanup`), not at the start
            of your next turn, so the pod's round does not read them.
  §0z187 2. Rendmaw and azusa take a land drop at the END of main phase 2
            (`late_land_main2`), as the other four have since §0z182.
  §0z187 3. CR 302.6: tivit's `mana_units` leaves out a summoning-sick
            creature's mana ability (`tivit_sick_mana`). Latent.
  §0z188    CR 611.3a: Beastmaster Ascension's +5/+5 is on whenever it has
            seven quest counters (`Game.beast_on`, `beast_static`), not only
            from the declare-attackers step to your next untap.

CASES
  A  rendmaw: cleanup ends Overwhelming Stampede's +X/+X
  B  NEIGHBOUR: `eot_at_cleanup=False`: it survives cleanup
  C  azusa: cleanup ends Craterhoof's, Wildspeaker's and Godmaw's pumps,
     haste and vigilance
  D  NEIGHBOUR: `eot_at_cleanup=False`: all of them survive cleanup
  E  NEIGHBOUR: cleanup still discards to seven (514.1) before 514.2
  F  Ascension at 7 counters, the flag off (as after your untap): +5/+5
  G  NEIGHBOUR: at 6 counters: no bonus
  H  NEIGHBOUR: `beast_static=False`: the old flag, off, so no bonus
  I  every name in `EOT_EFFECTS` is an attribute some engine sets (§0q:
     a renamed pump leaves no stale entry)
  J  rendmaw: a land put in hand during main 2 is played at its end
  K  NEIGHBOUR: `late_land_main2=False`: it stays in hand
  L  azusa: the same, through azusa's own land step
  M  NEIGHBOUR: `late_land_main2=False`: it stays in hand
  N  tivit: a sick creature's mana ability is not offered; once not sick, it is
  O  NEIGHBOUR: `tivit_sick_mana=False`: offered while sick
  P  NEIGHBOUR: a sick ARTIFACT's mana ability is offered (302.6 is creatures')

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  eot_at_cleanup=False everywhere           -> A, C
  beast_static=False everywhere             -> F
  late_land_main2=False everywhere          -> J, L
  tivit_sick_mana=False everywhere          -> N
  engine.end_turn_effects is a no-op        -> A, C
  EOT_EFFECTS without "eot_pt"              -> C
  Game.beast_on reads the old flag          -> F
  cleanup skips the discard                 -> E

UNMUTATED (§0z15): B, D, G, H, K, M, O and P are the neighbours, each
already on the side its mutation would push it to; I is the set's own check
and no mutation here renames an attribute.
"""
import sys
from pathlib import Path

import edhmc.azusa as AZ
import edhmc.engine as E
import edhmc.tivit as T
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
REND = build_pending("rendmaw")
AZU = build_pending("azusa")
TIV = build_pending("tivit")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                **{**EXTRA_CFG, **kw})


def bear(sick=False):
    c = Card(name="Bear", types=frozenset({"Creature"}), power=2, toughness=2)
    return Permanent(card=c, sick=sick, base_p=2, base_t=2)


def forest_card():
    return Card(name="Forest", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"G"}))


def named(deck, name):
    return next(c for c in deck[0] if c.name == name)


def rendmaw(**kw):
    lst, cmd = REND
    c = cfg(**kw)
    g = E.Game(list(lst), cmd, c, E.make_rng(3, c), seed_for_pod=3)
    g.opening_hand()
    g.board = E.Board()
    g.turn = 4
    return g


def azusa(**kw):
    lst, cmd = AZU
    g = AZ.AzusaGame(list(lst), cmd, cfg(**kw), 1234)
    g.opening_hand()
    g.board = E.Board()
    g.turn = 4
    return g


def tivit(**kw):
    lst, cmd = TIV
    g = T.TivitGame(list(lst), cmd, cfg(**kw), 3)
    g.opening_hand()
    g.board = E.Board()
    g.tokens["Treasure"] = 0
    return g


def ascension(quest):
    p = Permanent(card=named(REND, "Beastmaster Ascension"), sick=False)
    p.quest = quest
    return p


def pumped_azusa(**kw):
    g = azusa(**kw)
    b = bear()
    g.board.append(b)
    g.craterhoof_bonus, g.wildspeaker_bonus = 3, 3
    g.add_eot(b, 1, 1)
    g.eot_haste[id(b)] = b
    g.eot_vigilance[id(b)] = b
    g.hand = []
    E.cleanup_step(g)
    return (g.craterhoof_bonus, g.wildspeaker_bonus, len(g.eot_pt),
            len(g.eot_haste), len(g.eot_vigilance))


def rendmaw_main2_land(**kw):
    """One rendmaw turn, opponents off, a library of nonlands: Thomil's step
    (the last thing in main 2 before the end-of-main-2 drop) hands it a Forest."""
    g = rendmaw(opponents=False, **kw)
    g.turn = 3
    g.hand = []
    g.library = [c for c in REND[0] if not c.is_land][:30]
    real = E.thomil_step

    def thomil(gg, **k):
        real(gg, **k)
        gg.hand.append(forest_card())
    E.thomil_step = thomil
    try:
        E.take_turn(g)
    finally:
        E.thomil_step = real
    return (g.m["late_land_drops"], sum(1 for c in g.hand if c.is_land))


def azusa_main2_land(**kw):
    """One azusa turn, opponents off: the land step that opens main 2 hands
    it a Forest after it has looked, so only the end-of-main-2 drop sees it."""
    g = azusa(opponents=False, **kw)
    g.turn = 3
    g.hand = []
    g.library = [c for c in AZU[0] if not c.is_land][:30]
    calls = []
    real = g.land_step

    def step():
        real()
        calls.append(1)
        if len(calls) == 2:
            g.hand.append(forest_card())
    g.land_step = step
    AZ.take_turn(g)
    return (g.m["late_land_drops"], sum(1 for c in g.hand if c.is_land))


def sick_units(sick, artifact=False, **kw):
    g = tivit(**kw)
    types = {"Artifact"} if artifact else {"Creature"}
    c = Card(name="Test Dork", types=frozenset(types), power=1, toughness=1,
             mana_ability=(1, frozenset({"G"})))
    g.board.append(Permanent(card=c, sick=sick))
    return len(T.mana_units(g))


def run_cases():
    PASS.clear()
    FAIL.clear()

    for label, kw, want in (
            ("A rendmaw: cleanup ends Stampede's +X/+X", {}, (6, 2, 0)),
            ("B eot_at_cleanup=False: it survives cleanup",
             {"eot_at_cleanup": False}, (6, 6, 4))):
        g = rendmaw(**kw)
        b = bear()
        g.board.append(b)
        g.stampede_bonus = 4
        g.hand = []
        before = g.power_of(b)
        E.cleanup_step(g)
        check(label, (before, g.power_of(b), g.stampede_bonus), want)

    check("C azusa: cleanup ends every until-end-of-turn pump",
          pumped_azusa(), (0, 0, 0, 0, 0))
    check("D eot_at_cleanup=False: they all survive cleanup",
          pumped_azusa(eot_at_cleanup=False), (3, 3, 1, 1, 1))

    g = rendmaw()
    g.hand = [c for c in REND[0] if not c.is_land][:9]
    check("E cleanup still discards to seven",
          (E.cleanup_step(g), len(g.hand)), (2, 7))

    for label, quest, kw, want in (
            ("F Ascension at 7, the flag off: +5/+5", 7, {}, (7, 7)),
            ("G at 6 counters: no bonus", 6, {}, (2, 2)),
            ("H beast_static=False: the old flag, off", 7,
             {"beast_static": False}, (2, 2))):
        g = rendmaw(**kw)
        b = bear()
        g.board.append(ascension(quest))
        g.board.append(b)
        g.beast_active = False             # as every untap step left it
        check(label, (g.power_of(b), g.toughness_of(b)), want)

    src = "".join(p.read_text(encoding="utf-8")
                  for p in Path(E.__file__).parent.glob("*.py"))
    missing = [n for n in E.EOT_EFFECTS
               if f"self.{n} =" not in src and f"self.{n}: " not in src]
    check("I every EOT_EFFECTS name is an engine's attribute", missing, [])

    check("J rendmaw: a land drawn in main 2 is played at its end",
          rendmaw_main2_land(), (1, 0))
    check("K late_land_main2=False: it stays in hand",
          rendmaw_main2_land(late_land_main2=False), (0, 1))
    check("L azusa: a land drawn in main 2 is played at its end",
          azusa_main2_land(), (1, 0))
    check("M late_land_main2=False: it stays in hand",
          azusa_main2_land(late_land_main2=False), (0, 1))

    check("N tivit: a sick creature's mana is not offered; unsick, it is",
          (sick_units(True), sick_units(False)), (0, 1))
    check("O tivit_sick_mana=False: offered while sick",
          sick_units(True, tivit_sick_mana=False), 1)
    check("P a sick artifact's mana is offered",
          sick_units(True, artifact=True), 1)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z187, §0z188: until end of turn at cleanup, a main-2 land, "
              "tivit's sick mana, Beastmaster's static\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    no_pt = tuple(n for n in E.EOT_EFFECTS if n != "eot_pt")
    muts = {
        "eot_at_cleanup=False everywhere":
            ({"A", "C"}, None, {"eot_at_cleanup": False}),
        "beast_static=False everywhere":
            ({"F"}, None, {"beast_static": False}),
        "late_land_main2=False everywhere":
            ({"J", "L"}, None, {"late_land_main2": False}),
        "tivit_sick_mana=False everywhere":
            ({"N"}, None, {"tivit_sick_mana": False}),
        "engine.end_turn_effects is a no-op":
            ({"A", "C"}, (E, "end_turn_effects", lambda g: None), {}),
        'EOT_EFFECTS without "eot_pt"':
            ({"C"}, (E, "EOT_EFFECTS", no_pt), {}),
        "Game.beast_on reads the old flag":
            ({"F"}, (E.Game, "beast_on",
                     lambda self: (self.has("Beastmaster Ascension")
                                   and self.beast_active)), {}),
        "cleanup skips the discard":
            ({"E"}, (E, "_discard_to_hand_size",
                     lambda g, pick=None, after=None: 0), {}),
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
