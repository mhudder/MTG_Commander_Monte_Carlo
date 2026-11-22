#!/usr/bin/env python3
"""Item 45 (§0z248): each fixed-X spell pays its own X, behind its own
switch, OFF until measured.

    python -m tests.test_x_spells
    python -m tests.test_x_spells --mutate   # 6 mutations, exact sets

`engine.largest_x` is the largest X a pool affords, never below the card's
old fixed X (`x_pips`), under the caller's own limit; `engine.x_cost` is the
cost at that X. Green Sun's Zenith plans its X for a target by
`engine.x_plan`, trostani's rule (§0z213).

    Genesis Wave {X}{G}{G}{G}       genesis_wave_x   (azusa)
    Animist's Awakening {X}{G}      animist_x        (azusa)
    Nylea's Intervention {X}{G}{G}  nylea_x          (azusa)
    Green Sun's Zenith {X}{G}       gsz_x_plan       (azusa)
    Torment of Hailfire {X}{B}{B}   torment_x        (tivit)
    Debt to the Deathless {X}{W}{W}{B}{B}  debt_x    (karlov)
    The Meathook Massacre {X}{B}{B}  meathook_x      (rendmaw; its ETB too)
    Agadeem's Awakening {X}{B}{B}{B}  agadeem_x      (shilgengar; its front
                                                      face, never cast before)

CASES
  A  largest_x: {X}{G}{G}{G} at a fixed 6, twelve {G} -- X 9
  B  ... eight {G} cannot pay the fixed 6 -- None
  C  ... twelve {G}, the caller refuses X above 7 -- X 7
  D  azusa, Genesis Wave, eleven Forests, twenty sorceries in the library:
     X 8, eight revealed
  E  NEIGHBOUR: genesis_wave_x off -- six revealed, no X counted
  F  Nylea's Intervention, nine Forests, four Forests in the library: X 4
     (capped at the Forests left), four Forests to hand
  G  Animist's Awakening, ten Forests, six cards in the library: X 6
     (capped at the library), six revealed
  H  Green Sun's Zenith, eight Forests, Eternal Witness and Avenger of
     Zendikar in the library: Avenger enters at X 7
  I  NEIGHBOUR: gsz_x_plan off -- the old rule, Eternal Witness (mana value 3)
  J  tivit, Torment of Hailfire, four Swamps and six Treasures: X 8, every
     Treasure spent, each opponent 40 -> 16
  K  karlov, Debt to the Deathless, three Plains and six Swamps: X 5, each
     opponent 40 -> 30
  L  NEIGHBOUR: debt_x off -- 40 -> 34
  M  rendmaw, The Meathook Massacre, six Swamps, a 2/3 of yours and a 1/1
     token, each opponent's bodies of toughness 1, 2 and 3: X 2 (the 2/3
     stops X at 2), the token dies (each opponent 40 -> 39), the pod's
     toughness-1 and -2 bodies die (six: you 40 -> 46), the 2/3 lives
  N  NEIGHBOUR: meathook_x off -- no ETB: the token and every body live
  O  shilgengar, Agadeem's Awakening, six Swamps, a graveyard of two mana
     value 2 creatures (priority 1 and 5) and one of 5: X 3, the priority-5
     one returns, the other two stay
  P  NEIGHBOUR: agadeem_x off -- the old blank: cast, nothing returns

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  largest_x returns the floor whenever it is affordable
                                    -> A, C, D, F, G, J, K, M, O
  azusa's x_limit is no limit                         -> F, G
  Green Sun's Zenith's switch never reads on         -> H
  every switch off                                    -> D, F, G, H, J, K, M, O
  meathook_x_ok refuses nothing                       -> M
  agadeem_return takes the LOWEST priority at each mana value -> O

UNMUTATED (§0z15): B, E, I, L, N and P are each rule's neighbour -- the floor
that keeps a card castable exactly when it was, and the switches off.
Genesis Wave's decking limit (`draw_is_safe`) does not bind in D; it is
the guard every Wave already had (§0z210), pinned by tests.test_decking.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
import edhmc.shilgengar as S
import edhmc.tivit as T
from edhmc.azusa import AzusaGame
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
ALL_ON = {"genesis_wave_x": True, "animist_x": True, "nylea_x": True,
          "gsz_x_plan": True, "torment_x": True, "debt_x": True,
          "meathook_x": True, "agadeem_x": True}
DECKS = {d: build_pending(d) for d in ("azusa", "tivit", "karlov", "rendmaw",
                                       "shilgengar")}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg_of(cfg):
    return dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                **{**ALL_ON, **cfg, **EXTRA_CFG})


def named(deck, name):
    return next(c for c in DECKS[deck][0] if c.name == name)


def land(name, produces):
    return Card(name=name, types=frozenset({"Land"}), is_land=True,
                produces=frozenset(produces))


def filler(i):
    return Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                cost={"gen": 1})


def lands(spec):
    """[(name, produces, n), ...] -> untapped Permanents, a fresh Card each."""
    return [Permanent(card=land(n, p), sick=False)
            for n, p, k in spec for _ in range(k)]


def azusa(hand, forests, library, **cfg):
    deck, cmd = DECKS["azusa"]
    g = AzusaGame(list(deck), cmd, cfg_of(cfg), 1234)
    g.opening_hand()
    g.board = EN.Board()
    g.board.extend(lands([("Forest", "G", forests)]))
    g.commander_cast = True
    g.bonus_mana = []
    g.hand[:] = [named("azusa", n) for n in hand]
    g.library[:] = list(library)
    g.main_phase()
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    wave = named("azusa", "Genesis Wave")
    g12 = [frozenset("G")] * 12
    check("A largest_x: twelve {G}, X 9",
          EN.largest_x(wave, wave.cost, g12), 9)
    check("B eight {G} cannot pay the fixed 6",
          EN.largest_x(wave, wave.cost, [frozenset("G")] * 8), None)
    check("C the caller refuses X above 7",
          EN.largest_x(wave, wave.cost, g12, ok=lambda x: x <= 7), 7)

    g = azusa(["Genesis Wave"], 11, [filler(i) for i in range(20)])
    check("D Genesis Wave, eleven Forests: X 8, eight revealed",
          (g.m["wave_x"], g.m["wave_revealed"]), (8, 8))

    g = azusa(["Genesis Wave"], 11, [filler(i) for i in range(20)],
              genesis_wave_x=False)
    check("E genesis_wave_x off: six revealed",
          (g.m["wave_x"], g.m["wave_revealed"]), (0, 6))

    g = azusa(["Nylea's Intervention"], 9,
              [filler(i) for i in range(10)]
              + [land("Forest", "G") for _ in range(4)])
    check("F Nylea's Intervention: X 4, four Forests to hand",
          (g.m["nylea_x"], sum(1 for c in g.hand if c.name == "Forest")),
          (4, 4))

    g = azusa(["Animist's Awakening"], 10, [filler(i) for i in range(6)])
    check("G Animist's Awakening: X 6, six revealed",
          (g.m["animist_x"], g.m["awakening_revealed"]), (6, 6))

    lib = [named("azusa", "Eternal Witness"),
           named("azusa", "Avenger of Zendikar")]
    g = azusa(["Green Sun's Zenith"], 8, list(lib))
    check("H Green Sun's Zenith: Avenger at X 7",
          ("Avenger of Zendikar" in [p.card.name for p in g.board],
           g.m["gsz_x"]), (True, 7))

    g = azusa(["Green Sun's Zenith"], 8, list(lib), gsz_x_plan=False)
    check("I gsz_x_plan off: the old rule, Eternal Witness",
          ("Eternal Witness" in [p.card.name for p in g.board],
           "Avenger of Zendikar" in [p.card.name for p in g.board]),
          (True, False))

    deck, cmd = DECKS["tivit"]
    g = T.TivitGame(list(deck), cmd, cfg_of({}), 7)
    g.board = EN.Board()
    g.board.extend(lands([("Swamp", "B", 4)]))
    g.hand, g.graveyard, g.library = [named("tivit", "Torment of Hailfire")], \
        [], [filler(i) for i in range(20)]
    g.tokens["Treasure"] = 6
    g.turn, g.commander_cast = 2, True
    for o in g.opponents:
        o.life = 40.0
    T.main_phase(g)
    check("J Torment: X 8, every Treasure, 40 -> 16",
          (g.m["torment_x"], g.tokens["Treasure"],
           [o.life for o in g.opponents]), (8, 0, [16.0, 16.0, 16.0]))

    def karlov(**cfg):
        deck, cmd = DECKS["karlov"]
        g = K.KarlovGame(list(deck), cmd, cfg_of(cfg), 1)
        g.board = EN.Board()
        g.board.extend(lands([("Plains", "W", 3), ("Swamp", "B", 6)]))
        g.hand, g.graveyard = [named("karlov", "Debt to the Deathless")], []
        g.library = [filler(i) for i in range(20)]
        g.turn, g.commander_cast = 2, True
        for o in g.opponents:
            o.life = 40.0
        K.main_phase(g)
        return g

    g = karlov()
    check("K Debt: X 5, 40 -> 30",
          (g.m["debt_x"], [o.life for o in g.opponents]),
          (5, [30.0, 30.0, 30.0]))
    g = karlov(debt_x=False)
    check("L debt_x off: 40 -> 34",
          [o.life for o in g.opponents], [34.0, 34.0, 34.0])

    def rendmaw(**cfg):
        deck, cmd = DECKS["rendmaw"]
        g = EN.Game(list(deck), cmd, cfg_of(cfg), __import__("random").Random(1),
                    seed_for_pod=1)
        g.board = EN.Board()
        g.board.extend(lands([("Swamp", "B", 6)]))
        bear = Permanent(card=Card(name="Test Bear",
                                   types=frozenset({"Creature"}),
                                   power=2, toughness=3), sick=False)
        bird = Permanent(card=Card(name="Bird token",
                                   types=frozenset({"Creature"}),
                                   power=1, toughness=1),
                         sick=False, is_token=True, base_p=1, base_t=1)
        g.board.extend([bear, bird])
        g.hand, g.graveyard = [named("rendmaw", "The Meathook Massacre")], []
        g.library = [filler(i) for i in range(20)]
        g.turn, g.commander_cast, g.your_life = 2, True, 40.0
        for o in g.opponents:
            o.life = 40.0
            o.bodies = [OPP.PodBody(1, 1), OPP.PodBody(2, 2), OPP.PodBody(3, 3)]
            o.body_tapped = [False] * 3
            o.creatures = 3.0
        EN.main_phase(g)
        return g, bear, bird

    g, bear, bird = rendmaw()
    check("M Meathook: X 2, the token dies, two bodies each, the 2/3 lives",
          (g.m["meathook_x"], bird in g.board, bear in g.board,
           [[b.toughness for b in o.bodies] for o in g.opponents],
           [o.life for o in g.opponents], g.your_life),
          (2, False, True, [[3], [3], [3]], [39.0, 39.0, 39.0], 46.0))
    g, bear, bird = rendmaw(meathook_x=False)
    check("N meathook_x off: no ETB",
          (bird in g.board,
           [[b.toughness for b in o.bodies] for o in g.opponents]),
          (True, [[1, 2, 3], [1, 2, 3], [1, 2, 3]]))

    def creature(name, mv, priority):
        return Card(name=name, types=frozenset({"Creature"}), cost={"gen": mv},
                    power=1, toughness=1, priority=priority)

    def shilgengar(**cfg):
        deck, cmd = DECKS["shilgengar"]
        g = S.ShilgengarGame(list(deck), cmd, cfg_of(cfg), 1)
        g.board = EN.Board()
        g.board.extend(lands([("Swamp", "B", 6)]))
        g.hand = [named("shilgengar", S.AGADEEM)]
        g.graveyard = [creature("Low", 2, 1), creature("High", 2, 5),
                       creature("Big", 5, 9)]
        g.library = [filler(i) for i in range(20)]
        g.turn, g.commander_cast = 2, True
        g.main_phase(reserve=0)
        return g

    g = shilgengar()
    check("O Agadeem: X 3, the priority-5 two returns",
          (g.m["agadeem_x"], [p.card.name for p in g.board
                              if p.card.is_creature],
           sorted(c.name for c in g.graveyard if c.is_creature)),
          (3, ["High"], ["Big", "Low"]))
    g = shilgengar(agadeem_x=False)
    check("P agadeem_x off: the blank",
          (g.m["agadeem_blank_casts"],
           sorted(c.name for c in g.graveyard if c.is_creature)),
          (1, ["Big", "High", "Low"]))
    return set(FAIL)


def _floor_only(card, cost, units, ok=None, floor=None):
    floor = card.x_pips if floor is None else floor
    if not EN.can_afford(EN.x_cost(card, cost, floor), units):
        return None
    return floor


def _lowest_priority(self, x):
    best = {}
    for c in self.yard_creatures():
        mv = int(c.free_mv)
        if mv <= x and (mv not in best or c.priority < best[mv].priority):
            best[mv] = c
    picks = [best[mv] for mv in sorted(best)]
    for c in picks:
        EN.remove_card(self.graveyard, c)
    for c in picks:
        self.make_permanent(c, sick=True)
    self.m["agadeem_x"] += x


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z248: the X spells, each its own X\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_switch = AZ.AzusaGame.x_switch

    def no_gsz(self, script):
        return script != "green_sun" and real_switch(self, script)
    muts = {
        "largest_x returns the floor":
            ({"A", "C", "D", "F", "G", "J", "K", "M", "O"},
             [(m, "largest_x", _floor_only) for m in (EN, AZ, T, K, S)], {}),
        "azusa's x_limit is no limit":
            ({"F", "G"},
             [(AZ.AzusaGame, "x_limit", lambda self, card: None)], {}),
        "Green Sun's Zenith's switch never reads on":
            ({"H"}, [(AZ.AzusaGame, "x_switch", no_gsz)], {}),
        "every switch off":
            ({"D", "F", "G", "H", "J", "K", "M", "O"}, [],
             {k: False for k in ALL_ON}),
        "meathook_x_ok refuses nothing":
            ({"M"}, [(EN, "meathook_x_ok", lambda g, x: True)], {}),
        "agadeem_return takes the lowest priority":
            ({"O"}, [(S.ShilgengarGame, "agadeem_return", _lowest_priority)],
             {}),
    }
    bad = 0
    for label, (want, patches, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
