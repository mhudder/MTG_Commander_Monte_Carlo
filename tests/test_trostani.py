#!/usr/bin/env python3
"""The Trostani engine's mechanisms, one assertion per clause (§0z96).

    python -m tests.test_trostani
    python -m tests.test_trostani --mutate   # 5 mutations, exact sets

Every case builds a scripted board on a fresh `TrostaniGame` and checks one
clause of oracle text, verified against Scryfall 2026-10-01.

CASES
  A  Trostani + Parallel Lives, one Soul of Eternity token created: TWO tokens
     enter, and each trigger reads toughness = life AT RESOLUTION, so life
     goes 40 -> 80 -> 160
  B  Queen Allenal + Parallel Lives, one Angel token created: "those tokens
     plus a 1/1 Soldier", then doubled -- 2 Angels and 2 Soldiers
  C  the legend rule: a copy of King Darien while he is on the battlefield is
     not made; a copy of a nonlegendary token is
  D  Caretaker's Talent draws ONCE for two token batches in one turn, and
     again on the next turn
  E  Bramble Sovereign copies a nontoken Eternal Witness (paying {1}{G}), not
     Trostani (legendary), not a token
  F  Nesting Dovehawk + Primal Vigor: one Soldier becomes two, each puts a
     doubled counter on the Dovehawk -- 4 counters
  G  Mirari's Wake: one Forest offers two {G}, so {G}{G} is affordable from
     it alone; without the Wake it is not
  H  God-Pharaoh's Gift's copy of Soul of Eternity is a 4/4 at 40 life (its
     CDA is not copied, 707.9d)
  I  Selfless Spirit is sacrificed before the pod's wrath; three tokens are
     then indestructible and a destroy-wrath leaves all three
  J  Elspeth's emblem: a Soldier token flies and is a 3/3
  K  Defense of the Heart fires on an opponent with three creatures (two
     creatures onto the battlefield), not on one with two
  L  Mosswort Bridge plays its hidden card only at total power 10 or more
  M  Aetherflux Reservoir fires at 70 life (leaves 20) and not at 64
  N  Alhammarret's Archive: gain 3 -> 6; a draw outside the draw step -> 2
  O  Talisman of Unity: {G} from it costs 1 life, {1} from it costs none
  P  Windswept Heath, played: 1 life, and it finds Temple Garden (the land
     that fixes both colours), which pays 2 more to enter untapped
  Q  encore of Soul of Eternity with Trostani out, three opponents: three
     hasty Soul tokens, life 40 -> 80 -> 160 -> 320
  R  populate copies the Soul token, not the Soldier beside it
  S  Mimic Vat imprints a nontoken Sun Titan that dies, out of the graveyard

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  CDA ignored (base_pt returns the printed P/T)  -> A, Q, R
  no token doublers (doublers() is 0)            -> A, B, F
  legend rule off (LEGENDARY is empty)           -> C, E
  Mirari's Wake adds no mana                     -> G
  no response to the pod's wrath                 -> I

UNMUTATED (§0z15): D, H, J-P and S pin clauses the five mutations above do
not touch; each is its own positive case.
"""
import sys

import edhmc.trostani as T
import edhmc.opponents as OPP
from edhmc.decks import trostani_v1 as TM
from edhmc.engine import Board, Permanent
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = TM.build()
BY_NAME = {c.name: c for c in DECK}
BY_NAME[CMD.name] = CMD


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = T.TrostaniGame(list(DECK), CMD, dict(DEFAULT_CFG, turns=20, **cfg), 1)
    g.board, g.hand, g.graveyard = Board(), [], []
    g.your_life = 40.0
    g.turn = 5
    g.turn_key = (5, 0)
    return g


def put(g, name, token=False, sick=False):
    card = BY_NAME[name]
    p = Permanent(card=card, sick=sick, is_token=token,
                  base_p=card.power, base_t=card.toughness)
    T.enter_loyalty(p)
    g.board.append(p)
    return p


def lands(g, name, n):
    for _ in range(n):
        put(g, name)


def tokens(g, name=None):
    return [p for p in g.board if p.is_token
            and (name is None or p.card.name == name)]


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    soul = BY_NAME["Soul of Eternity"]

    g = fresh()
    put(g, CMD.name); put(g, "Parallel Lives")
    g.create_tokens(soul, 1)
    check("A two Soul tokens: 40 -> 80 -> 160", (len(tokens(g)), g.your_life),
          (2, 160.0))

    g = fresh()
    put(g, "Queen Allenal of Ruadach"); put(g, "Parallel Lives")
    g.create_tokens(T.ANGEL, 1)
    check("B Queen + Lives, one Angel: 2 Angels and 2 Soldiers",
          (len(tokens(g, "Angel token")), len(tokens(g, "Soldier token"))),
          (2, 2))

    g = fresh()
    put(g, "King Darien XLVIII")
    a = g.copy_token(BY_NAME["King Darien XLVIII"])
    b = g.copy_token(T.SOLDIER)
    check("C legend rule: no Darien copy, a Soldier copy", (len(a), len(b)),
          (0, 1))

    g = fresh()
    put(g, "Caretaker's Talent")
    g.library = [BY_NAME["Plains"]] * 20
    g.create_tokens(T.SOLDIER, 1)
    g.create_tokens(T.SOLDIER, 1)
    once = len(g.hand)
    g.turn_key = (6, 0)
    g.create_tokens(T.SOLDIER, 1)
    check("D Caretaker draws once per turn", (once, len(g.hand)), (1, 2))

    g = fresh()
    put(g, "Bramble Sovereign"); lands(g, "Forest", 6)
    g.library = [BY_NAME["Plains"]] * 20
    g.put_creature(BY_NAME["Eternal Witness"])
    witness = len(tokens(g, "Eternal Witness"))
    g.put_creature(CMD)
    trost = len(tokens(g, CMD.name))
    g.create_tokens(T.SOLDIER, 1)
    check("E Bramble: Witness copied, Trostani not, a token not",
          (witness, trost, len(tokens(g, "Soldier token"))), (1, 0, 1))

    g = fresh()
    d = put(g, "Nesting Dovehawk"); put(g, "Primal Vigor")
    g.create_tokens(T.SOLDIER, 1)
    check("F Vigor: two Soldiers, four Dovehawk counters",
          (len(tokens(g, "Soldier token")), d.counters), (2, 4))

    g = fresh()
    put(g, "Mirari's Wake"); put(g, "Forest")
    with_wake = (len(g.available_mana()), g.can_afford({"G": 2}))
    g2 = fresh()
    put(g2, "Forest")
    without = (len(g2.available_mana()), g2.can_afford({"G": 2}))
    check("G Wake: one Forest pays {G}{G}", (with_wake, without),
          ((2, True), (1, False)))

    g = fresh()
    gpg = g.create_tokens(T.copy_card(soul, fixed=(4, 4), colours="B"), 1)[0]
    check("H GPG's Soul is a 4/4 at 40 life",
          (g.power_of(gpg), g.toughness_of(gpg)), (4, 4))

    g = fresh()
    put(g, "Selfless Spirit")
    for _ in range(3):
        g.board.append(Permanent(card=T.SOLDIER, sick=False, is_token=True,
                                 base_p=1, base_t=1))
    g.before_wipe()
    with OPP.simultaneous(g):
        for p in [p for p in g.board if OPP.is_creature_now(g, p)]:
            OPP.destroy(g, p, 0.0, kind="wipe")
    check("I Spirit sacrificed; three tokens survive a destroy-wrath",
          (g.has("Selfless Spirit"), len(tokens(g))), (False, 3))

    g = fresh()
    g.emblems = 1
    s = Permanent(card=T.SOLDIER, sick=False, is_token=True, base_p=1, base_t=1)
    g.board.append(s)
    check("J emblem: Soldier flies, 3/3",
          (OPP.flying_of(g, s), g.power_of(s), g.toughness_of(s)),
          (True, 3, 3))

    def defense(n):
        g = fresh()
        put(g, "Defense of the Heart")
        g.library = [BY_NAME["Soul of Eternity"], BY_NAME["Seedborn Muse"],
                     BY_NAME["Plains"]]
        for o in g.opponents:
            o.creatures = 0.0
        g.opponents[1].creatures = float(n)
        g.upkeep()
        return (g.has("Defense of the Heart"),
                sum(1 for p in g.board if p.card.is_creature))
    check("K Defense: fires at 3, not at 2", (defense(3), defense(2)),
          ((False, 2), (True, 0)))

    def bridge(power):
        g = fresh()
        br = put(g, "Mosswort Bridge"); put(g, "Forest")
        g.hideaway[id(br)] = BY_NAME["Seedborn Muse"]
        g.board.append(Permanent(card=T.minion(power), sick=False,
                                 is_token=True, base_p=power, base_t=power))
        g.precombat_actions()
        return g.has("Seedborn Muse")
    check("L Bridge: power 9 no, power 10 yes", (bridge(9), bridge(10)),
          (False, True))

    def reservoir(life):
        g = fresh()
        put(g, "Aetherflux Reservoir")
        g.your_life = float(life)
        g.reservoir()
        return g.your_life, g.m["reservoir_shots"]
    check("M Reservoir: 70 fires once, 64 does not",
          (reservoir(70), reservoir(64)), ((20.0, 1), (64.0, 0)))

    g = fresh()
    put(g, "Alhammarret's Archive")
    g.library = [BY_NAME["Plains"]] * 10
    g.gain_life(3)
    g.draw(1)
    check("N Archive: +6 life, two cards", (g.your_life, len(g.hand)),
          (46.0, 2))

    def talisman(cost):
        g = fresh()
        put(g, "Talisman of Unity")
        g.pay(cost)
        return g.your_life
    check("O Talisman: {G} costs 1 life, {1} none",
          (talisman({"G": 1}), talisman({"gen": 1})), (39.0, 40.0))

    g = fresh()
    g.library = [BY_NAME["Forest"], BY_NAME["Temple Garden"], BY_NAME["Plains"]]
    g.hand = [BY_NAME["Windswept Heath"]]
    g.land_step()
    land = [p for p in g.board if p.card.is_land]
    check("P Heath finds Temple Garden, 3 life, untapped",
          ([p.card.name for p in land], land[0].tapped, g.your_life),
          (["Temple Garden"], False, 37.0))

    g = fresh()
    put(g, CMD.name); lands(g, "Plains", 9)
    g.graveyard = [soul]
    g.precombat_actions()
    souls = tokens(g, "Soul of Eternity")
    check("Q encore: three hasty Souls, 40 -> 320",
          (len(souls), all(id(p) in g.hasty for p in souls), g.your_life),
          (3, True, 320.0))

    g = fresh()
    g.board.append(Permanent(card=T.SOLDIER, sick=False, is_token=True,
                             base_p=1, base_t=1))
    g.board.append(Permanent(card=soul, sick=False, is_token=True))
    g.populate("test")
    check("R populate copies the Soul", g.m["soul_tokens_made"], 1)

    g = fresh()
    vat = put(g, "Mimic Vat")
    titan = put(g, "Sun Titan")
    g.sacrifice(titan)
    check("S Vat imprints Sun Titan out of the graveyard",
          (g.vat.get(id(vat)) is BY_NAME["Sun Titan"],
           any(c.name == "Sun Titan" for c in g.graveyard)), (True, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The Trostani engine, clause by clause\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    G = T.TrostaniGame
    real = {"base_pt": G.base_pt, "doublers": G.doublers,
            "available_mana": G.available_mana, "before_wipe": G.before_wipe}
    real_legendary = T.LEGENDARY

    def printed_pt(self, perm):
        if perm.is_token:
            return perm.base_p, perm.base_t
        return perm.card.power, perm.card.toughness

    muts = {
        "CDA ignored": ({"A", "Q", "R"},
                        lambda: setattr(G, "base_pt", printed_pt)),
        "no token doublers": ({"A", "B", "F"},
                              lambda: setattr(G, "doublers", lambda self: 0)),
        "legend rule off": ({"C", "E"},
                            lambda: setattr(T, "LEGENDARY", frozenset())),
        "Mirari's Wake adds no mana": (
            {"G"}, lambda: setattr(G, "available_mana",
                                   lambda self: T.shared_available_mana(self))),
        "no response to the pod's wrath": (
            {"I"}, lambda: setattr(G, "before_wipe", lambda self: None)),
    }
    bad = 0
    for label, (want, apply) in muts.items():
        print(f"-- {label}")
        apply()
        try:
            broke = run_cases()
        finally:
            for k, v in real.items():
                setattr(G, k, v)
            T.LEGENDARY = real_legendary
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
