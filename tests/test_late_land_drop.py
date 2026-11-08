#!/usr/bin/env python3
"""§0z182: a land drop in either main phase, not only before main phase 1.

    python -m tests.test_late_land_drop
    python -m tests.test_late_land_drop --mutate   # 6 mutations, exact sets

CR 305.1 / 505.6b: a land may be played in either main phase while a drop is
left. Lorehold, karlov, tivit and shilgengar took their one drop before main
phase 1 and never again, so a land drawn later in the turn waited a turn.
`engine.late_land_drop` is the rule, written once; each of the four engines
calls it at the end of main 1, at the start of main 2 and at the end of
main 2, and runs the main phase again on the land's mana.

The helper cases drive `late_land_drop` on a tivit game. The engine cases
drive each engine's `take_turn` with its main phase and combat replaced by
loggers (the turn's SHAPE is the subject, not what is cast), every land taken
out of the hand and moved to the bottom of the library so the land step and
the draws find none, and the pod off. A logger hands the hand one of the
deck's own lands at one point of the turn, and records how many lands are on
the battlefield at each main-phase call.

CASES
  A  helper: a drop left and a land in hand -> played, True, counted
  B  helper: the drop already used -> False, the hand untouched
  C  helper: no land in hand -> False
  D  NEIGHBOUR: `late_land_drop=False` -> False, nothing played
  E-<deck>  a land handed over in main 1 is played in main 1, and main 1
            runs again with it (two main calls before combat, the second
            seeing one more land)
  F-<deck>  a land handed over in combat is played as main 2 begins (main
            2's first call sees one more land)
  G-<deck>  a land handed over in main 2's first call is played, and main 2
            runs again with it
  H  NEIGHBOUR: tivit with `late_land_drop=False`: the main-1 land stays in
     hand and main 1 runs once

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  late_land_drop=False everywhere       -> A, E-*, F-*, G-* (13 cases)
  the helper ignores the drop limit     -> B
  tivit's late_land_drop always False   -> E-tivit, F-tivit, G-tivit
  lorehold's ...                        -> E-lorehold, F-lorehold, G-lorehold
  karlov's ...                          -> E-karlov, F-karlov, G-karlov
  shilgengar's ...                      -> E-shilgengar, F-shilgengar,
                                           G-shilgengar

UNMUTATED (§0z15): C, D and H are the neighbours -- the helper's no-op paths,
which every mutation leaves returning False. The per-engine mutations are
what pin each engine's own call sites: the first mutation alone would pass
with one engine's wiring deleted.
"""
import sys

import edhmc.engine as E
import edhmc.karlov as K
import edhmc.lorehold as L
import edhmc.shilgengar as S
import edhmc.tivit as T
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}

ENGINES = {          # deck -> (module, game class, main/combat on the game?)
    "tivit": (T, T.TivitGame, False),
    "lorehold": (L, L.LoreholdGame, False),
    "karlov": (K, K.KarlovGame, False),
    "shilgengar": (S, S.ShilgengarGame, True),
}
LISTS = {d: build_pending(d) for d in ENGINES}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(deck, **cfg):
    """A game at turn 4, no land in hand or near the top; returns (g, land)
    where `land` is one of the deck's own lands, out of every zone."""
    mod, cls, _ = ENGINES[deck]
    lst, cmd = LISTS[deck]
    g = cls(list(lst), cmd, dict(DEFAULT_CFG, watch=frozenset(),
                                 opponents=False, **{**EXTRA_CFG, **cfg}), 3)
    g.opening_hand()
    g.turn = 3
    lands = [c for c in g.hand if c.is_land or c.land_face]
    for c in lands:
        E.remove_card(g.hand, c)
    lib_lands = [c for c in g.library if c.is_land or c.land_face]
    rest = [c for c in g.library if not (c.is_land or c.land_face)]
    g.library = lands + lib_lands + rest          # top is library[-1]
    basics = ("Plains", "Swamp", "Island", "Mountain", "Forest")
    land = next(c for c in g.library if c.is_land and c.name in basics)
    E.remove_card(g.library, land)
    return g, land


def lands_out(g):
    return sum(1 for p in g.board if p.card.is_land)


def drive(deck, when, **cfg):
    """Play one turn with logging stubs; hand `land` over at `when`
    ("main1", "combat" or "main2"). Returns (log, land in hand at the end)."""
    mod, cls, on_game = ENGINES[deck]
    g, land = game(deck, **cfg)
    log, seen = [], {"combat": False, "mains": 0}

    def mp(*a, **k):
        seen["mains"] += 1
        tag = "main2" if seen["combat"] else "main1"
        log.append((tag, lands_out(g)))
        first2 = tag == "main2" and sum(1 for t, _ in log if t == "main2") == 1
        if (when == "main1" and seen["mains"] == 1) or \
                (when == "main2" and first2):
            g.hand.append(land)

    def cb(*a, **k):
        seen["combat"] = True
        log.append(("combat", lands_out(g)))
        if when == "combat":
            g.hand.append(land)

    if on_game:
        g.main_phase, g.combat = mp, cb
        real = None
    else:
        real = (mod.main_phase, mod.combat)
        mod.main_phase, mod.combat = mp, cb
    try:
        mod.take_turn(g)
    finally:
        if real is not None:
            mod.main_phase, mod.combat = real
    return log, any(c is land for c in g.hand)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, land = game("tivit")
    g.hand.append(land)
    n0 = lands_out(g)
    got = E.late_land_drop(g)
    check("A a drop left, a land in hand: played, True, counted",
          (got, lands_out(g) - n0, g.land_drops_used, g.m["late_land_drops"],
           any(c is land for c in g.hand)), (True, 1, 1, 1, False))

    g, land = game("tivit")
    g.hand.append(land)
    g.land_drops_used = g.land_drops
    hand = list(g.hand)
    check("B the drop used: False, the hand untouched",
          (E.late_land_drop(g), g.hand == hand), (False, True))

    g, _ = game("tivit")
    check("C no land in hand: False", E.late_land_drop(g), False)

    g, land = game("tivit", late_land_drop=False)
    g.hand.append(land)
    n0 = lands_out(g)
    check("D late_land_drop=False: False, nothing played",
          (E.late_land_drop(g), lands_out(g) - n0), (False, 0))

    for deck in ENGINES:
        log, held = drive(deck, "main1")
        pre = [n for t, n in log if t == "main1"]
        check(f"E-{deck} a main-1 land: played in main 1, main 1 again",
              (len(pre), pre[-1] - pre[0] if pre else None, held),
              (2, 1, False))

        log, held = drive(deck, "combat")
        at_combat = next(n for t, n in log if t == "combat")
        first2 = next(n for t, n in log if t == "main2")
        check(f"F-{deck} a combat land: played as main 2 begins",
              (first2 - at_combat, held), (1, False))

        log, held = drive(deck, "main2")
        m2 = [n for t, n in log if t == "main2"]
        check(f"G-{deck} a main-2 land: played, main 2 again",
              (len(m2) >= 2, m2[-1] - m2[0], held), (True, 1, False))

    log, held = drive("tivit", "main1", late_land_drop=False)
    check("H tivit, late_land_drop=False: the land stays, main 1 once",
          (len([t for t, _ in log if t == "main1"]), held), (1, True))
    return set(FAIL)


def _ignores_limit(g, step=None):
    """`late_land_drop` with its drop-limit test removed (mutation 2)."""
    if not g.cfg.get("late_land_drop", True) or g.result is not None:
        return False
    if not any(c.is_land or c.land_face for c in g.hand):
        return False
    g.land_drops = g.land_drops_used + 1
    before = g.land_drops_used
    (step or E.play_land)(g)
    if g.land_drops_used == before:
        return False
    g.m["late_land_drops"] += 1
    return True


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z182: a land drop in either main phase\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    every = {f"{c}-{d}" for c in "EFG" for d in ENGINES}
    muts = {
        "late_land_drop=False everywhere":
            ({"A"} | every, [], {"late_land_drop": False}),
        "the helper ignores the drop limit":
            ({"B"}, [(E, "late_land_drop", _ignores_limit)], {}),
    }
    for d, (mod, _, _) in ENGINES.items():
        muts[f"{d}'s late_land_drop always False"] = (
            {f"{c}-{d}" for c in "EFG"},
            [(mod, "late_land_drop", lambda g, step=None: False)], {})
    bad = 0
    for label, (want, patches, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        saved = [(o, n, getattr(o, n)) for o, n, _ in patches]
        for o, n, fn in patches:
            setattr(o, n, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for o, n, fn in saved:
                setattr(o, n, fn)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
