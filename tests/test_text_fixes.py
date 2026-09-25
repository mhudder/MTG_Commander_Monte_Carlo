#!/usr/bin/env python3
"""Four cards whose text the engine had approximated (§0z49 to §0z52).

    python -m tests.test_text_fixes
    python -m tests.test_text_fixes --mutate   # 9 mutations, exact sets

    Storm Herd  {8}{W}{W} Sorcery  (Scryfall, verified 2026-09-25)
    Create X 1/1 white Pegasus creature tokens with flying, where X is your
    life total.
      -- X was cfg["storm_herd_x"] = 40, from before lorehold tracked life.

    Radiant Scrollwielder  {2}{R}{W} 2/4
    Instant and sorcery spells you control have lifelink. [...]
      -- the lifelink clause was unmodelled; `deal_pod_damage` now takes a
         required `spell` argument and every call site states it.

    Ranger of Eos  {3}{W} 3/2
    When this creature enters, you may search your library for up to two
    creature cards with mana value 1 or less, reveal them, put them into your
    hand, then shuffle.
      -- it was `script="draw2"`.

    Lurrus of the Dream-Den  {1}{W/B}{W/B}
      -- flattened to {1}{W}{B}: castable off {W}{W} or {B}{B} in reality,
         and two hybrid pips are TWO devotion to white (and two to black).

CASES
  A  Storm Herd at 27 life: 27 Pegasi, and they fly
  B  Storm Herd at -3 life: none
  C  `storm_herd_x=40` still forces the old constant
  D  Scrollwielder out, Boros Charm's 4 to one player: you gain 4
  E  Scrollwielder out, a Guttersnipe trigger (a PERMANENT source): no gain
  F  no Scrollwielder, the same spell: no gain
  G  Scrollwielder out, a spell dealing 2 to each of three, one of them on
     1 life: you gain 6 -- lifelink gains what was DEALT (702.15b), not the
     bounded "could have mattered" 5 the damage metric records
  H  NEIGHBOUR: Monument to Endurance's drain is life LOSS, so Scrollwielder
     gains nothing from it
  J  Ranger of Eos resolves with Vito, Mother of Runes, Soul Warden and Serra
     Ascendant in the library: hand gains Soul Warden and Mother of Runes
     (the two highest-priority ONE-DROPS; Vito is MV 3)
  K  no one-drop creature in the library: nothing found
  L  one one-drop in the library: one found
  M  the search's shuffle does not touch `g.rng` (the §0z17 invariant)
  N  Lurrus is castable from {W}{W}{C}
  O  devotion to white counts Lurrus as 2
  P  NEIGHBOUR: devotion still counts Karlov ({W}{B}) as 1 and Daxos
     ({W}{W}) as 2 -- non-hybrid costs are unchanged

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  Storm Herd's X is the constant 40             -> A, B
  the `storm_herd_x` override is ignored        -> C
  Scrollwielder's lifelink does nothing         -> D, G
  lifelink without Scrollwielder on board       -> F
  Ranger of Eos's search does nothing           -> J, L
  the search ignores "mana value 1 or less"     -> J, K, L
  the search finds only one                     -> J
  hybrid alternatives are ignored when casting   -> N
  devotion reads the printed cost only (the old code) -> O

UNMUTATED, and written down (§0z15): E and H are gated by the `spell=False`
their call sites pass, and no seam separates that gate from
`deal_pod_damage`; M is the invariant tests/test_crn_streams.py mutates; P
is the neighbour the devotion change must not move.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.lorehold as L
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v16 as LM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


LDECK, LCMD = LM.build()
KDECK, KCMD = KM.build()
STORM = next(c for c in LDECK if c.name == "Storm Herd")
BOROS = next(c for c in LDECK if c.name == "Boros Charm")
SNIPE = next(c for c in LDECK if c.name == "Guttersnipe")
MONUMENT = next(c for c in LDECK if c.name == "Monument to Endurance")
SCROLL = LM.RADIANT_SCROLLWIELDER
FILLER = [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                  cost={"gen": 1}) for i in range(20)]


def lgame(*cards, **cfg):
    g = L.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard = [], []
    g.library = list(FILLER)
    g.before_draw_step = False
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def pegasi(life, **cfg):
    g = lgame(**cfg)
    g.your_life = float(life)
    L.apply_spell_effects(g, STORM)
    toks = [p for p in g.board if p.card.name == "Pegasus token"]
    return len(toks), all(p.card.flying for p in toks)


def gained(g, fn):
    before = g.your_life
    fn(g)
    return round(g.your_life - before, 3)


def kgame(library):
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20), 4242)
    g.board = EN.Board()
    g.hand = []
    g.library = list(library)
    return g


def kcard(name):
    return next(c for c in KDECK if c.name == name)


def ranger(names):
    g = kgame([kcard(n) for n in names] + list(FILLER))
    L_before = len(g.library)
    K.resolve(g, kcard("Ranger of Eos"))
    got = sorted(c.name for c in g.hand)
    return got, L_before - len(g.library), g


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    check("A Storm Herd at 27 life: 27 flying Pegasi", pegasi(27), (27, True))
    check("B Storm Herd at -3 life: none", pegasi(-3)[0], 0)
    check("C storm_herd_x=40 forces 40", pegasi(27, storm_herd_x=40)[0], 40)
    check("D Scrollwielder, Boros Charm's 4: gain 4",
          gained(lgame(SCROLL), lambda g: L.apply_spell_effects(g, BOROS)), 4.0)
    g = lgame(SCROLL, SNIPE)
    check("E Scrollwielder, a Guttersnipe trigger: no gain",
          gained(g, lambda g: L.on_cast_triggers(g, FILLER[0])), 0.0)
    check("F no Scrollwielder, a spell: no gain",
          gained(lgame(), lambda g: L.apply_spell_effects(g, BOROS)), 0.0)
    g = lgame(SCROLL)
    g.opponents[0].life = 1.0
    check("G spell 2 to each of three, one on 1 life: gain 6",
          gained(g, lambda g: L.deal_pod_damage(g, 6.0, hits=3, spell=True)),
          6.0)
    g = lgame(SCROLL, MONUMENT, monument_order=("drain", "draw", "treasure"))
    check("H Monument's drain is life loss: no gain",
          gained(g, lambda g: L.discard_triggers(g, 1)), 0.0)
    got, found, _ = ranger(["Vito, Thorn of the Dusk Rose", "Mother of Runes",
                            "Soul Warden", "Serra Ascendant"])
    check("J Ranger finds Soul Warden and Mother of Runes",
          (got, found), (["Mother of Runes", "Soul Warden"], 2))
    got, found, _ = ranger(["Vito, Thorn of the Dusk Rose",
                            "Kalitas, Traitor of Ghet"])
    check("K no one-drop in the library: nothing found", found, 0)
    got, found, _ = ranger(["Vito, Thorn of the Dusk Rose", "Serra Ascendant"])
    check("L one one-drop: one found", (got, found), (["Serra Ascendant"], 1))
    g = kgame([kcard("Soul Warden")] + list(FILLER))
    state = g.rng.getstate()
    K.ranger_of_eos_etb(g)
    check("M the search's shuffle does not touch g.rng",
          g.rng.getstate() == state, True)
    lurrus = kcard("Lurrus of the Dream-Den")
    units = [frozenset({"W"}), frozenset({"W"}), frozenset({"C"})]
    check("N Lurrus castable from {W}{W}{C}",
          EN.choose_mode(lurrus, dict(lurrus.cost), units) is not None, True)
    g = kgame([])
    g.board.append(EN.Permanent(card=lurrus, sick=False))
    check("O devotion to white counts Lurrus as 2", K.devotion_white(g), 2)
    g = kgame([])
    for n in ("Daxos, Blessed by the Sun",):
        g.board.append(EN.Permanent(card=kcard(n), sick=False))
    g.board.append(EN.Permanent(card=KCMD, sick=False))
    check("P devotion: Karlov 1 + Daxos 2 = 3", K.devotion_white(g), 3)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Storm Herd, Radiant Scrollwielder, Ranger of Eos\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_x, real_ll = L.storm_herd_x, L.scrollwielder_lifelink
    real_etb, real_pick = K.ranger_of_eos_etb, K.ranger_of_eos_pick

    def gain_anyway(g, dealt):
        if dealt > 0:
            g.your_life += dealt

    def pick_any_creature(g):
        pool = [c for c in g.library if c.is_creature]
        return sorted(pool, key=lambda c: (-c.priority, c.name))[:2]

    muts = {
        "Storm Herd's X is the constant 40":
            ({"A", "B"}, L, "storm_herd_x", lambda g: 40),
        "the storm_herd_x override is ignored":
            ({"C"}, L, "storm_herd_x", lambda g: max(0, int(g.your_life))),
        "Scrollwielder's lifelink does nothing":
            ({"D", "G"}, L, "scrollwielder_lifelink", lambda g, d: None),
        "lifelink without Scrollwielder on board":
            ({"F"}, L, "scrollwielder_lifelink", gain_anyway),
        "Ranger of Eos's search does nothing":
            ({"J", "L"}, K, "ranger_of_eos_etb", lambda g: None),
        "the search ignores mana value 1 or less":
            ({"J", "K", "L"}, K, "ranger_of_eos_pick", pick_any_creature),
        "the search finds only one":
            ({"J"}, K, "ranger_of_eos_pick", lambda g: real_pick(g)[:1]),
        "hybrid alternatives are ignored when casting":
            ({"N"}, EN, "castable_modes",
             lambda card, base: [(base, None, 0.0)]),
        "devotion reads the printed cost only (the old code)":
            ({"O"}, K, "devotion_white",
             lambda g: sum(p.card.cost.get("W", 0) for p in g.board)),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    assert (L.storm_herd_x, L.scrollwielder_lifelink, K.ranger_of_eos_etb,
            K.ranger_of_eos_pick) == (real_x, real_ll, real_etb, real_pick)
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
