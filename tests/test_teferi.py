#!/usr/bin/env python3
"""§0z262: Teferi's Protection, its whole round, on the owner's policy.

    python -m tests.test_teferi
    python -m tests.test_teferi --mutate   # 5 mutations, exact sets

    "Until your next turn, your life total can't change and you gain
    protection from everything. All permanents you control phase out.
    Exile Teferi's Protection."          ({2}{W}, Instant; Scryfall 2026-11-25)

The owner (2026-11-26): "whichever comes first ... Perhaps not avoiding a
boardwipe with just a single meaningless creature" -- a wrath that would
kill two nontoken creatures or the commander, or a lethal drain or combat
kill aimed at you; never one spot removal.

CASES (shilgengar; {2}{W} untapped unless said)
  T1 the wipe bar: two nontoken creatures yes, one no, the commander alone yes
  T2 a spot removal: not answered (the old rule blanked it)
  T3 a wrath at two nontoken creatures: cast, the round live; at one: not
  T4 the round live: the pod's spot removal at you destroys nothing, and a
     wrath spares your creatures
  T5 a drain kill at 30 life: cast, the round live, life unchanged, the
     clock re-armed a round on
  T6 the same kill at 50 life (over `kill_size` 40): not cast
  T7 a combo kill: not stopped, the card stays in hand
  T8 the round ends as your next turn begins
  T9 the round live: the pod's chip damage leaves your life unchanged

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  teferi_full=False everywhere               -> T2, T3, T5
  teferi_wipe_min at 1                       -> T1, T3
  phased_out always False                    -> T3, T4, T5, T8, T9
  lethality ignored (kill_size 999)          -> T6
  a combo kill treated as a drain            -> T7

UNMUTATED (§0z15): none -- every case is reached by at least one.
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
CMD = B.LISTS["shilgengar"][1]
ROUTES = ("drain", "combat")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(name):
    return B.card("shilgengar", name)


def creature(name="Body"):
    return EN.Permanent(card=EN.Card(name=name, types=frozenset({"Creature"}),
                                     power=3, toughness=3), sick=False)


def game(n_creatures=0, mana=True, commander=False, **cfg):
    board = B.lands("shilgengar", "Plains", "Plains", "Plains") if mana else []
    if commander:
        board = board + [CMD]
    g = B.fresh("shilgengar", board=board,
                **{"pod_mana": False, **EXTRA_CFG, **cfg})
    for i in range(n_creatures):
        g.board.append(creature(f"Body {i}"))
    g.hand = [card(OPP.TEFERI)]
    return g


def live(g):
    return OPP.phased_out(g)


def run_cases():
    PASS.clear()
    FAIL.clear()

    check("T1 the wipe bar: 2 yes, 1 no, the commander alone yes",
          (OPP.teferi_wipe_worth(game(2)), OPP.teferi_wipe_worth(game(1)),
           OPP.teferi_wipe_worth(game(0, commander=True))),
          (True, False, True))

    g = game(1)
    victim = g.board[-1]
    check("T2 a spot removal is not answered",
          OPP.try_protect(g, 0.0, event="spot", victim=victim), None)

    g = game(2)
    a = (OPP.try_protect(g, 0.0, event="wipe"), live(g))
    g = game(1)
    b = (OPP.try_protect(g, 0.0, event="wipe"), live(g))
    check("T3 a wrath at two: cast, live; at one: not",
          (a, b), (("blank", True), (None, False)))

    g = game(2)
    OPP.start_teferi(g)
    mine = [p for p in g.board if p.card.is_creature]
    OPP._spot_at_you(g, [0.0] * 8, opp=g.opponents[0])
    after_spot = sum(1 for p in mine if p in g.board)
    o = g.opponents[0]
    o.creatures = 2.0
    OPP.board_wipe(g, o, [0.0] * 8)
    check("T4 the round live: spot and wrath leave your creatures",
          (after_spot, sum(1 for p in mine if p in g.board), o.creatures),
          (2, 2, 0.0))

    g = game()
    g.your_life = 30.0
    o = g.opponents[0]
    o.route = "drain"
    saved = OPP.teferi_saves(g, o)
    check("T5 a drain kill at 30: cast, live, life kept, re-armed",
          (saved, live(g), g.your_life, o.kill_turn, g.hand),
          (True, True, 30.0, OPP.pod_turn(g) + 1, []))

    g = game()
    g.your_life = 50.0
    o = g.opponents[0]
    o.route = "drain"
    check("T6 at 50 life: not cast",
          (OPP.teferi_saves(g, o), len(g.hand)), (False, 1))

    g = game()
    g.your_life = 30.0
    o = g.opponents[0]
    o.route = "combo"
    check("T7 a combo kill: not stopped",
          (OPP.teferi_saves(g, o), len(g.hand)), (False, 1))

    g = game()
    OPP.start_teferi(g)
    before = live(g)
    g.turn += 1
    check("T8 the round ends with your next turn", (before, live(g)),
          (True, False))

    g = game()
    OPP.start_teferi(g)
    o = g.opponents[0]
    o.creatures = 6.0
    life = g.your_life
    OPP._chip_seat(g, 0, 1.0)
    check("T9 chip damage leaves your life", g.your_life, life)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z262: Teferi's Protection\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_phased = OPP.phased_out
    real_saves = OPP.teferi_saves

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_phased(v):
        OPP.phased_out = v

    def set_saves(v):
        OPP.teferi_saves = v

    def combo_as_drain(g, opp):
        if getattr(opp, "route", None) == "combo":
            opp.route = "drain"
        return real_saves(g, opp)

    muts = {
        "teferi_full=False everywhere": (
            {"T2", "T3", "T5"}, set_cfg, {"teferi_full": False}, {}),
        "teferi_wipe_min at 1": (
            {"T1", "T3"}, set_cfg, {"teferi_wipe_min": 1}, {}),
        "phased_out always False": (
            {"T3", "T4", "T5", "T8", "T9"}, set_phased, lambda g: False,
            real_phased),
        "lethality ignored": ({"T6"}, set_cfg, {"kill_size": 999}, {}),
        "a combo kill treated as a drain": (
            {"T7"}, set_saves, combo_as_drain, real_saves),
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
