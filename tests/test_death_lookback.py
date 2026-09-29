#!/usr/bin/env python3
"""Death triggers look back in time (§0z76).

    python -m tests.test_death_lookback
    python -m tests.test_death_lookback --mutate   # 3 mutations, exact sets

    CR 603.10a: leaves-the-battlefield abilities "look back in time" -- they
    trigger based on the game as it was just before the event, so a source
    that dies in the same event, or IS the creature dying, still sees it.

`opponents.destroy` removes creatures one at a time, and every engine's death
handler checked the LIVE board: a Blood Artist removed third in a wipe missed
every death after it, and Blood Artist's own death -- "Whenever THIS creature
or another creature dies" -- could never trigger it. `opponents.simultaneous`
marks one event (both wipe paths use it) and `opponents.watching` is the one
look-back reader, with `another=True` for "another creature" wording.

CASES (the payoff is placed FIRST on the board, so the wipe removes it first)
  A  rendmaw wipe: Blood Artist and three creatures -- four drains (its own
     death included); the live-board engine drained none
  B  rendmaw wipe: Pitiless Plunderer and three creatures -- three Treasures
     ("another": not its own death)
  C  rendmaw: Blood Artist destroyed alone -- it drains for its own death
  D  rendmaw: Pitiless Plunderer destroyed alone -- no Treasure
  E  shilgengar wipe: Grim Haruspex and two nontoken creatures -- two draws
  F  karlov wipe: Blood Artist, Syr Konrad and one creature -- Blood Artist
     sees three deaths, Syr Konrad two (not his own); 3 + 2*3 = 9 pod damage
  G  `death_lookback=False`: A's wipe drains nothing, as before §0z76
  H  after the wipe the simultaneous context is closed (`g.dying` is None)
  I  the wipe itself (`opponents.board_wipe`) opens the context: A through
     the real wipe path
  J  Voldaren Bloodcaster's trigger fires. It was checked as "Voldaren
     Bloodcaster" against a card named "Voldaren Bloodcaster // Bloodbat
     Summoner" and had never fired once.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  watching ignores the simultaneous event        -> A, B, E, F, I
  watching ignores the dying permanent itself    -> A, C, F, I
  the "another" flag is ignored                  -> B, D, E, F

UNMUTATED (§0z15): G is the knob reproducing the old engine; H is a
property of the context manager; J is a name fix with no seam.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def find(module, name):
    deck, _ = module.build()
    pool = list(deck) + [v for v in vars(module).values()
                         if isinstance(v, EN.Card)]
    return next(c for c in pool if c.name == name)


def body(name, nontoken=True):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=2,
                   toughness=2)


def setup(g, *cards):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(30)]
    g.turn = 6
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False, base_p=c.power,
                                    base_t=c.toughness))
    return g


def rgame(*cards, **cfg):
    deck, cmd = RM.build()
    return setup(EN.Game(list(deck), cmd, dict(DEFAULT_CFG, **cfg),
                         random.Random(1), seed_for_pod=1), *cards)


def wipe(g):
    with OPP.simultaneous(g):
        for p in [p for p in g.board if OPP.is_creature_now(g, p)]:
            OPP.destroy(g, p, destroys=True)


def others(n):
    return [body(f"Bear{i}") for i in range(n)]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    artist = find(RM, "Blood Artist")
    plunderer = RM.PITILESS_PLUNDERER
    g = rgame(artist, *others(3))
    wipe(g)
    check("A rendmaw wipe: Blood Artist drains four times",
          g.m["drain_damage"], 4.0)
    g = rgame(plunderer, *others(3))
    wipe(g)
    check("B rendmaw wipe: Plunderer makes three Treasures", g.treasures, 3)
    g = rgame(artist)
    OPP.destroy(g, g.board[0], destroys=True)
    check("C Blood Artist alone: drains for its own death",
          g.m["drain_damage"], 1.0)
    g = rgame(plunderer)
    OPP.destroy(g, g.board[0], destroys=True)
    check("D Plunderer alone: no Treasure", g.treasures, 0)
    sdeck, scmd = SM.build()
    g = setup(SH.ShilgengarGame(list(sdeck), scmd, dict(DEFAULT_CFG), 7),
              find(SM, "Grim Haruspex"), *others(2))
    hand = len(g.hand)
    wipe(g)
    check("E shilgengar wipe: Grim Haruspex draws two", len(g.hand) - hand, 2)
    kdeck, kcmd = KM.build()
    g = setup(K.KarlovGame(list(kdeck), kcmd, dict(DEFAULT_CFG), 7),
              find(KM, "Blood Artist"), find(KM, "Syr Konrad, the Grim"),
              *others(1))
    wipe(g)
    check("F karlov wipe: 3 drains + 2 Konrad triggers x3 = 9",
          round(g.m["damage"], 6), 9.0)
    g = rgame(artist, *others(3), death_lookback=False)
    wipe(g)
    check("G death_lookback off: nothing, as before", g.m["drain_damage"], 0)
    check("H the context is closed after the wipe",
          getattr(g, "dying", None), None)
    g = rgame(artist, *others(3))
    rolls = [0.0] * 8
    rolls[5] = rolls[7] = 1.0
    OPP.board_wipe(g, g.opponents[0], rolls)
    check("I the real wipe path: four drains", g.m["drain_damage"], 4.0)
    sdeck, scmd = SM.build()
    g = setup(SH.ShilgengarGame(list(sdeck), scmd, dict(DEFAULT_CFG), 7),
              find(SM, "Voldaren Bloodcaster // Bloodbat Summoner"),
              *others(1))
    OPP.destroy(g, g.board[1], destroys=True)
    check("J Voldaren Bloodcaster fires", g.m["blood_made"], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Death triggers look back\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = OPP.watching

    def no_event(g, name, perm=None, another=False):
        saved = getattr(g, "dying", None)
        g.dying = None
        try:
            return real(g, name, perm, another)
        finally:
            g.dying = saved

    def no_self(g, name, perm=None, another=False):
        n = g.count(name) if not g.cfg.get("death_lookback", True) else None
        if n is not None:
            return n
        n = g.count(name)
        seen = {id(p) for p in g.board}
        for p in getattr(g, "dying", None) or ():
            if p.card.name == name and id(p) not in seen and p is not perm:
                n += 1
                seen.add(id(p))
        return n

    def no_another(g, name, perm=None, another=False):
        return real(g, name, perm, False)

    muts = {
        "watching ignores the simultaneous event":
            ({"A", "B", "E", "F", "I"}, no_event),
        "watching ignores the dying permanent itself":
            ({"A", "C", "F", "I"}, no_self),
        "the another flag is ignored":
            ({"B", "D", "E", "F"}, no_another),
    }
    bad = 0
    for label, (want, fn) in muts.items():
        print(f"-- {label}")
        OPP.watching = fn
        try:
            broke = run_cases()
        finally:
            OPP.watching = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
