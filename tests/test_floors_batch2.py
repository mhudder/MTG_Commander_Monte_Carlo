#!/usr/bin/env python3
"""Items 6 and 7: eight cards whose text the engine now plays (§0z84, §0z85).

    python -m tests.test_floors_batch2
    python -m tests.test_floors_batch2 --mutate   # 6 mutations, exact sets

    Burnished Hart         {3}, Sacrifice: up to two basics, tapped; shuffle.
    Filigree Familiar      ETB: gain 2 life. Dies: draw a card.
    Whip of Erebos         Creatures you control have lifelink. {2}{B}{B},{T}:
                           return a creature card, haste, exile it at the
                           next end step; if it would leave, exile it.
    Shigeki                {1}{G},{T}, return it to hand: reveal four, a land
                           onto the battlefield tapped, the rest to graveyard.
    Herald of War          Attacks: a +1/+1 counter. Angel and Human spells
                           cost {1} less per +1/+1 counter on it.
    Twilight Shepherd      ETB: return to hand the cards put into your
                           graveyard from the battlefield this turn. Persist.
    Serra's Emissary       You and your creatures: protection from the chosen
                           card type ("Creature", `emissary_type`).
    Lurrus of the Dream-Den  Once each of your turns, cast a permanent spell
                           of mana value 2 or less from your graveyard.
                                                  (Scryfall, 2026-09-29)

CASES
  A  rendmaw Hart at the end step with {3} spare: sacrificed (Blood Artist
     drains), two basics fetched
  B  Hart with no spare mana: stays
  C  Filigree Familiar: +2 life entering; destroyed, a card drawn
  D  Whip: an attacker without lifelink gains its power in life
  E  Whip returns Grave Titan before combat: hasty, its Zombies made; the
     end step exiles it (not on the battlefield, not in the graveyard)
  F  a Whip creature destroyed: exiled -- no graveyard, no Blood Artist drain
  G  Shigeki at the end step: one land onto the battlefield tapped, three
     cards to the graveyard, Shigeki back in hand
  H  Shigeki stays home from combat
  I  shilgengar Herald with two counters: a {5}{W} Angel costs {3}{W}; a
     non-Angel non-Human costs what it says
  J  Herald attacks: one +1/+1 counter
  K  Twilight Shepherd destroyed: it persists (back, with a -1/-1 counter)
     and its ETB returns a card sacrificed earlier this turn
  L  a persisted Shepherd destroyed again: it stays in the graveyard
  M  Serra's Emissary: the pod's blockers stop nothing, and the pod's chip
     damage does not reach you
  N  karlov Lurrus: a mana-value-2 permanent is cast from the graveyard, once
     a turn -- the second is not
  O  NEIGHBOUR: `emissary_type="none"` -- blockers stop damage again

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  fetch_basics fetches nothing                -> A
  a Whip creature is not exiled on death      -> F
  protected_from_creatures is always False    -> M
  persist does nothing                        -> K
  Lurrus's pool is always empty               -> N
  herald_cost returns the printed cost        -> I

CASE E FAILED ITS FIRST RUN ON THE TEST, NOT THE ENGINE: it counted tokens
named "Zombie", and rendmaw names them "Zombie token". The Titan's Zombies
were there all along.

UNMUTATED (§0z15): B, C, D, E, G, H, J, L are neighbours or clauses with no
separate seam; O is the knob.
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


def pool(module):
    deck, cmd = module.build()
    cards = list(deck) + [v for v in vars(module).values()
                          if isinstance(v, EN.Card)]
    return deck, cmd, {c.name: c for c in cards}


RDECK, RCMD, R_ = pool(RM)
SDECK, SCMD, S_ = pool(SM)
KDECK, KCMD, K_ = pool(KM)


def body(name, p=2, t=2, **kw):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=t, **kw)


def land(name, col):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({col}))


def perm(c, **kw):
    kw.setdefault("sick", False)
    return EN.Permanent(card=c, base_p=c.power, base_t=c.toughness, **kw)


# --------------------------------------------------------------- rendmaw
def rgame(*cards, lands=(), **cfg):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = ([land("Forest", "G")] * 3 + [land("Swamp", "B")] * 3
                 + [body(f"L{i}") for i in range(20)])
    g.treasures = 0
    g.turn = 6
    for o in g.opponents:
        o.life = 40.0
        o.creatures = 0.0
    for c in list(lands) + list(cards):
        g.board.append(perm(c))
    return g


def case_rendmaw():
    artist, hart = R_["Blood Artist"], R_["Burnished Hart"]
    three = [land(f"Wastes{i}", "C") for i in range(3)]
    g = rgame(artist, hart, lands=three)
    EN.burnished_hart(g)
    check("A Hart: sacrificed, drains, two basics",
          (any(p.card is hart for p in g.board), g.m["drain_damage"],
           g.m["basics_fetched"]), (False, 1.0, 2))
    g = rgame(hart)
    EN.burnished_hart(g)
    check("B Hart without mana stays", any(p.card is hart for p in g.board),
          True)
    fam = R_["Filigree Familiar"]
    g = rgame()
    life, hand = g.your_life, len(g.hand)
    p = perm(fam)
    g.board.append(p)
    EN.run_etb(g, p)
    gained = g.your_life - life
    OPP.destroy(g, p, destroys=True)
    check("C Familiar: +2 entering, a card when it dies",
          (gained, len(g.hand) - hand), (2, 1))
    whip = R_["Whip of Erebos"]
    g = rgame(whip, body("Bear", 3, 3))
    life = g.your_life
    EN.combat(g)
    check("D Whip: a 3/3 attacker gains 3", g.your_life - life, 3)
    titan = R_["Grave Titan"]
    four = [land("SwampA", "B"), land("SwampB", "B"),
            land("WastesA", "C"), land("WastesB", "C")]
    g = rgame(whip, lands=four)
    g.graveyard = [titan]
    EN.whip_of_erebos(g)
    back = next((p for p in g.board if p.card is titan), None)
    zombies = sum(1 for p in g.board if p.card.name == "Zombie token")
    EN.whip_end_step(g)
    check("E Whip: hasty Titan, Zombies made, exiled at the end step",
          (back is not None and not back.sick, zombies,
           any(p.card is titan for p in g.board), titan in g.graveyard),
          (True, 2, False, False))
    g = rgame(whip, artist, lands=four)
    g.graveyard = [titan]
    EN.whip_of_erebos(g)
    back = next(p for p in g.board if p.card is titan)
    OPP.destroy(g, back, destroys=True)
    check("F a Whip creature destroyed: exiled, no drain",
          (titan in g.graveyard, g.m["drain_damage"]), (False, 0))
    shig = R_["Shigeki, Jukai Visionary"]
    g = rgame(shig, lands=[land("ForestA", "G"), land("WastesC", "C")])
    g.library = [body(f"L{i}") for i in range(20)] + [
        body("x1"), land("Forest", "G"), body("x2"), body("x3")]
    EN.shigeki(g)
    lands_now = [p for p in g.board if p.card.name == "Forest"]
    check("G Shigeki: a land tapped, three to the yard, back in hand",
          (len(lands_now), lands_now[0].tapped if lands_now else None,
           len(g.graveyard), shig in g.hand), (1, True, 3, True))
    g = rgame(shig)
    check("H Shigeki stays home", EN.shigeki_stays_home(g, g.board[0]), True)


# ------------------------------------------------------------ shilgengar
def sgame(*cards, **cfg):
    g = SH.ShilgengarGame(list(SDECK), SCMD, dict(DEFAULT_CFG, turns=20, **cfg), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(20)]
    g.turn = 6
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(perm(c))
    return g


def case_shilgengar():
    herald = S_["Herald of War"]
    g = sgame(herald)
    g.board[0].counters = 2
    angel = EN.Card(name="Test Angel", types=frozenset({"Creature"}),
                    cost={"gen": 5, "W": 1}, tags=("angel",))
    plain = EN.Card(name="Test Rock", types=frozenset({"Artifact"}),
                    cost={"gen": 5})
    check("I Herald x2: an Angel costs {3}{W}, a rock costs {5}",
          (g.herald_cost(angel), g.herald_cost(plain)),
          ({"gen": 3, "W": 1}, {"gen": 5}))
    g = sgame(herald)
    g.combat()
    check("J Herald attacks: one counter",
          next(p.counters for p in g.board if p.card is herald), 1)
    shep = S_["Twilight Shepherd"]
    g = sgame(shep)
    early = body("Early")
    pe = perm(early)
    g.board.append(pe)
    g.sacrifice(pe)
    first = g.board[0]
    OPP.destroy(g, first, destroys=True)
    back = next((p for p in g.board if p.card is shep), None)
    check("K Shepherd persists; its ETB returns this turn's dead",
          (back is not None and back.counters == -1, early in g.hand),
          (True, True))
    OPP.destroy(g, back, destroys=True)
    check("L a persisted Shepherd dies for good",
          (any(p.card is shep for p in g.board), shep in g.graveyard),
          (False, True))
    emissary = S_["Serra's Emissary"]
    g = sgame(emissary, body("Big", 6, 6))
    for o in g.opponents:
        o.creatures = 5.0
    through = OPP.damage_through(g, [g.board[1]], g.opponents[0])
    life = g.your_life
    OPP.incidental_damage(g)
    check("M Emissary: nothing blocks, nothing chips",
          (through, g.your_life - life), (6.0, 0))
    g = sgame(emissary, body("Big", 6, 6), emissary_type="none")
    for o in g.opponents:
        o.creatures = 5.0
    through = OPP.damage_through(g, [g.board[1]], g.opponents[0])
    check("O emissary_type none: the blockers stop it", through < 6.0, True)


# ----------------------------------------------------------------- karlov
def case_karlov():
    lurrus = K_["Lurrus of the Dream-Den"]
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(20)]
    g.turn = 6
    g.commander_cast = True
    g.board.append(perm(lurrus))
    for i in range(6):
        g.board.append(perm(land(f"Plains{i}", "W")))
    two_a = EN.Card(name="Two A", types=frozenset({"Artifact"}),
                    cost={"gen": 2}, priority=5)
    two_b = EN.Card(name="Two B", types=frozenset({"Artifact"}),
                    cost={"gen": 2}, priority=5)
    g.graveyard = [two_a, two_b]
    K.main_phase(g)
    cast = [c for c in (two_a, two_b) if any(p.card is c for p in g.board)]
    check("N Lurrus: one MV-2 permanent from the graveyard, not two",
          (len(cast), g.m["lurrus_casts"]), (1, 1))


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    case_rendmaw()
    case_shilgengar()
    case_karlov()
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Items 6 and 7: eight cards\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_exiled = EN.Game.exiled_instead_of_dying

    def no_whip_exile(self, p):
        saved = self.__dict__.pop("whip_returned", None)
        try:
            return real_exiled(self, p)
        finally:
            if saved is not None:
                self.whip_returned = saved

    muts = {
        "fetch_basics fetches nothing":
            ({"A"}, EN, "fetch_basics", lambda g, n: 0),
        "a Whip creature is not exiled on death":
            ({"F"}, EN.Game, "exiled_instead_of_dying", no_whip_exile),
        "protected_from_creatures is always False":
            ({"M"}, OPP, "protected_from_creatures", lambda g: False),
        "persist does nothing":
            ({"K"}, SH.ShilgengarGame, "shepherd_persists",
             lambda self, p: False),
        "Lurrus's pool is always empty":
            ({"N"}, K, "lurrus_pool", lambda g: []),
        "herald_cost returns the printed cost":
            ({"I"}, SH.ShilgengarGame, "herald_cost",
             lambda self, c: c.cost),
    }
    bad = 0
    for label, (want, owner, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(owner, name)
        setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
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
