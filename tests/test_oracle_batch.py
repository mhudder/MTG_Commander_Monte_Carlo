#!/usr/bin/env python3
"""Pin §0z116's items 6-13, fixed in §0z118.

    python -m tests.test_oracle_batch
    python -m tests.test_oracle_batch --mutate   # 8 mutations, exact sets

CASES
  A  karlov: Mother of Runes in HAND answers nothing -- her text is a {T}
     ability on the battlefield
  B  lorehold: Sejiri Shelter answers a spot removal on a creature, never a
     wrath
  C  lorehold: Dawn's Truce against a wrath grants indestructible (gift
     promised), it does not blank the wrath
  D  karlov: a summoning-sick Mother shrouds nothing; an untapped one does
  E  ... and lorehold's pilot keeps her home from combat while hers is
     the commander's only shroud
  U  shilgengar: Teferi's Protection against the pod's wrath -- your board
     phases out, the pod's creatures still die
  F  karlov: Damn with only {B}{B} available is not cast as a wrath
  G  ... with {2}{W}{W} it is, and all four lands pay for it
  H  tivit: Kambal and five Treasures at once: each opponent loses 1, you
     gain 1
  I  rendmaw: Primal Vigor doubles Steel Overseer's counter
  J  ... and Verdurous Gearhulk's four
  K  rendmaw: Culling Ritual takes Sol Ring and a token, spares Rendmaw (MV 5)
     and the land, and floats {B}/{G} for each
  L  lorehold: Ondu Inversion takes every nonland permanent, Treasures too
  M  lorehold: Ultima takes artifacts and creatures, not enchantments, and
     ends the turn
  N  lorehold: Promise of Loyalty -- you keep the commander, each opponent
     keeps one
  T  rendmaw: the wipe gate casts Culling Ritual over your own Rendmaw,
     because it does not kill her
  O  shilgengar: Giada puts counters on a CAST Angel, one per Angel you have
  P  ... and on an Angel token, as before
  Q  rendmaw: Steel Overseer taps to activate, and a sick one cannot
  R  ... and `activations` no longer runs it free after combat
  S  azusa: Green Sun's Zenith shuffles into the library, not the graveyard

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  protect_events=False   -> A, B, C, D, E, U
  damn_overload=False    -> F, G
  kambal_batch=False     -> H
  vigor_counters=False   -> I, J
  own_wipe_scope=False   -> K, L, M, N, T
  giada_text=False       -> O
  overseer_taps=False    -> Q, R
  gsz_shuffle=False      -> S

UNMUTATED (§0z15): P -- the token path gave Giada's counters before the fix
and gives them after it.
"""
import random
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as TI
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
CFG = {}
DECKS = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
LISTS = {d: build_pending(d) for d in DECKS}


def card(deck, name):
    return next(c for c in LISTS[deck][0] if c.name == name)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def filler(i):
    return EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                   cost={"gen": 1})


def body(name, p=2, types=("Creature",), tags=()):
    return EN.Card(name=name, types=frozenset(types), power=p, toughness=p,
                   cost={"gen": 3}, tags=frozenset(tags))


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, counter_threshold=99,
                **{**kw, **CFG})


def fresh(deck, board=(), hand=(), sick=()):
    d, cmd = LISTS[deck]
    if deck == "rendmaw":
        g = EN.Game(list(d), cmd, cfg(), random.Random(1), seed_for_pod=1)
    elif deck == "karlov":
        g = KA.KarlovGame(list(d), cmd, cfg(), 4242)
    elif deck == "lorehold":
        g = LO.LoreholdGame(list(d), cmd, cfg(), 1)
    elif deck == "shilgengar":
        g = SH.ShilgengarGame(list(d), cmd, cfg(), 7)
    elif deck == "tivit":
        g = TI.TivitGame(list(d), cmd, cfg(), 1)
    else:
        g = AZ.AzusaGame(list(d), cmd, cfg(), 1234)
    g.board = EN.Board()
    g.hand = list(hand)
    g.graveyard = []
    g.library = [filler(i) for i in range(30)]
    g.your_life = 40.0
    g.turn = 5
    for o in g.opponents:
        o.life = 40.0
        o.creatures = 0.0
    for c in board:
        g.board.append(EN.Permanent(card=c, sick=c in sick))
    return g


def lands(deck, *names):
    return [card(deck, n) for n in names]


def perm(g, name):
    return next(p for p in g.board if p.card.name == name)


def run_cases():
    PASS.clear()
    FAIL.clear()

    # -- 6: protection answers the events its text answers -------------------
    five = lands("karlov", "Plains", "Plains", "Swamp", "Swamp", "Plains")
    g = fresh("karlov", board=five, hand=[card("karlov", "Mother of Runes")])
    check("A Mother of Runes in hand answers no wrath",
          OPP.try_protect(g, 0.0, "wipe"), None)
    five = lands("lorehold", *["Plains"] * 5)
    g = fresh("lorehold", board=five + [body("Bear")],
              hand=[card("lorehold", "Sejiri Shelter")])
    check("B Sejiri Shelter: a creature's spot removal, never a wrath",
          (OPP.try_protect(g, 0.0, "wipe"),
           OPP.try_protect(g, 0.0, "spot", perm(g, "Bear"))),
          (None, "blank"))
    g = fresh("lorehold", board=five, hand=[card("lorehold", "Dawn's Truce")])
    check("C Dawn's Truce against a wrath: indestructible, not a blank",
          OPP.try_protect(g, 0.0, "wipe"), "indestructible")
    mother = card("karlov", "Mother of Runes")
    shrouded = []
    for sick in (True, False):
        g = fresh("karlov", board=[mother, g_cmd := LISTS["karlov"][1]],
                  sick=(mother,) if sick else ())
        g.commander_cast = True
        shrouded.append(OPP.commander_shrouded(g))
    check("D a sick Mother shrouds nothing; an untapped one does",
          shrouded, [False, True])
    # lorehold's pilot keeps her home while her shroud is the commander's
    # only one ("needed"); karlov's attacks with her ("never"), measured.
    lm = card("lorehold", "Mother of Runes")
    g = fresh("lorehold", board=[lm, LISTS["lorehold"][1]])
    home = OPP.holds_back(g, perm(g, "Mother of Runes"))
    g.board.append(EN.Permanent(card=card("lorehold", "Lightning Greaves")))
    check("E ... lorehold keeps her home while hers is the only shroud",
          (home, OPP.holds_back(g, perm(g, "Mother of Runes"))),
          (True, False))

    g = fresh("shilgengar",
              board=lands("shilgengar", *["Plains"] * 5) + [body("Bear")],
              hand=[card("shilgengar", "Teferi's Protection")])
    g.turn = 10
    for o in g.opponents:
        o.creatures = 4.0
    OPP.board_wipe(g, g.opponents[0], [0.0] * 8)
    check("U Teferi's Protection: you phase out, the pod's creatures die",
          ([p.card.name for p in g.board if not p.card.is_land],
           [o.creatures for o in g.opponents]),
          (["Bear"], [0.0, 0.0, 0.0]))

    # -- 7: Damn is a wrath only at its overload -----------------------------
    damn = card("karlov", "Damn")
    tapped = []
    for names in (("Swamp", "Swamp"), ("Plains", "Plains", "Swamp", "Swamp")):
        g = fresh("karlov", board=lands("karlov", *names), hand=[damn])
        g.commander_cast = True
        for o in g.opponents:
            o.creatures = 3.0
        KA.main_phase(g)
        tapped.append((damn in g.hand, g.m["own_wipes_cast"],
                       sum(p.tapped for p in g.board if p.card.is_land)))
    check("F Damn with {B}{B} only is held", tapped[0], (True, 0, 0))
    check("G ... and cast for {2}{W}{W} as the wrath", tapped[1],
          (False, 1, 4))

    # -- 8: Kambal, once per batch ------------------------------------------
    g = fresh("tivit", board=[card("tivit", "Kambal, Profiteering Mayor")])
    for k in list(g.tokens):
        g.tokens[k] = 0
    TI.make_token(g, "Treasure", 5)
    check("H Kambal: five Treasures at once drain 1 each, gain 1",
          ([o.life for o in g.opponents], g.your_life),
          ([39.0, 39.0, 39.0], 41.0))

    # -- 9: Primal Vigor's counters in rendmaw -------------------------------
    myr = body("Myr", 1, ("Artifact", "Creature"))
    g = fresh("rendmaw", board=[card("rendmaw", "Primal Vigor"),
                                card("rendmaw", "Steel Overseer"), myr])
    # Both paths, so exactly one activation runs whichever way
    # `overseer_taps` is set: I pins Vigor, not the tap (the first run of
    # this mutation list expected I to hold under `overseer_taps=False`; it
    # broke, because only `steel_overseer` was called).
    EN.steel_overseer(g)
    EN.activations(g)
    check("I Primal Vigor doubles Steel Overseer's counter",
          perm(g, "Myr").counters, 2)
    bear = body("Bear")
    g = fresh("rendmaw", board=[card("rendmaw", "Primal Vigor"), bear])
    hulk = EN.Permanent(card=card("rendmaw", "Verdurous Gearhulk"), sick=True)
    g.board.append(hulk)
    EN.run_etb(g, hulk)
    check("J ... and Verdurous Gearhulk's four", perm(g, "Bear").counters, 8)

    # -- 10: each sweeper destroys what its text says -------------------------
    rendmaw = LISTS["rendmaw"][1]
    token = EN.Card(name="Saproling token", types=frozenset({"Creature"}),
                    power=1, toughness=1)
    g = fresh("rendmaw", board=[rendmaw, card("rendmaw", "Sol Ring"),
                                card("rendmaw", "Forest")])
    g.commander_cast = True
    g.board.append(EN.Permanent(card=token, is_token=True, sick=False))
    OPP.resolve_own_wipe(g, card=card("rendmaw", "Culling Ritual"))
    check("K Culling Ritual: MV 2 or less, and {B}/{G} for each",
          (sorted(p.card.name for p in g.board), g.ritual_float,
           sum(u == frozenset({"B", "G"}) for u in EN.rendmaw_mana(g))),
          (["Forest", "Rendmaw, Creaking Nest"], 2, 2))

    ench = EN.Card(name="An Enchantment", types=frozenset({"Enchantment"}),
                   cost={"gen": 2})
    rock = EN.Card(name="A Rock", types=frozenset({"Artifact"}),
                   cost={"gen": 2})
    g = fresh("lorehold", board=[card("lorehold", "Plains"), ench, rock])
    g.treasures = 3
    OPP.resolve_own_wipe(g, card=card("lorehold", "Ondu Inversion"))
    check("L Ondu Inversion: every nonland permanent",
          (sorted(p.card.name for p in g.board), g.treasures),
          (["Plains"], 0))
    g = fresh("lorehold", board=[card("lorehold", "Plains"), ench, rock,
                                 body("Bear")])
    LO.apply_spell_effects(g, card("lorehold", "Ultima"))
    check("M Ultima: artifacts and creatures, then the turn ends",
          (sorted(p.card.name for p in g.board), g.turn_ended),
          (["An Enchantment", "Plains"], True))
    lore = LISTS["lorehold"][1]
    g = fresh("lorehold", board=[lore, body("Bear", 5)])
    g.commander_cast = True
    for o in g.opponents:
        o.creatures = 3.0
    OPP.resolve_own_wipe(g, card=card("lorehold", "Promise of Loyalty"))
    check("N Promise of Loyalty: you keep the commander, they keep one",
          (sorted(p.card.name for p in g.board),
           [o.creatures for o in g.opponents]),
          ([lore.name], [1.0, 1.0, 1.0]))
    g = fresh("rendmaw", board=[rendmaw])
    g.commander_cast = True
    for o in g.opponents:
        o.creatures = 2.0
        o._pcache = dict(o.p, power=1.0)
    check("T the gate casts Culling Ritual over Rendmaw: it spares her",
          OPP.should_cast_own_wipe(g, card("rendmaw", "Culling Ritual")),
          True)

    # -- 11: Giada on every Angel --------------------------------------------
    giada = card("shilgengar", "Giada, Font of Hope")
    other = body("An Angel", 3, tags=("angel",))
    g = fresh("shilgengar", board=[giada, other])
    cast = g.make_permanent(body("Cast Angel", 3, tags=("angel",)))
    check("O Giada: a cast Angel enters with one counter per Angel",
          cast.counters, 2)
    g = fresh("shilgengar", board=[giada, other])
    g.make_angel_tokens(1)
    check("P ... and an Angel token, as before",
          g.board[-1].counters, 2)

    # -- 12: Steel Overseer taps ----------------------------------------------
    over = card("rendmaw", "Steel Overseer")
    got = []
    for sick in (False, True):
        g = fresh("rendmaw", board=[over, myr], sick=(over,) if sick else ())
        EN.steel_overseer(g)
        got += [perm(g, "Steel Overseer").tapped, perm(g, "Myr").counters]
    check("Q Steel Overseer taps to activate; a sick one cannot", got,
          [True, 1, False, 0])
    g = fresh("rendmaw", board=[over, myr])
    EN.activations(g)
    check("R ... and does not activate free after combat",
          perm(g, "Myr").counters, 0)

    # -- 13: Green Sun's Zenith shuffles itself in ----------------------------
    gsz = card("azusa", "Green Sun's Zenith")
    g = fresh("azusa")
    g.resolve(gsz)
    check("S Green Sun's Zenith: into the library, not the graveyard",
          (gsz in g.library, gsz in g.graveyard), (True, False))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z116's items 6-13 (§0z118)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"protect_events": False}, {"A", "B", "C", "D", "E", "U"}),
        ({"damn_overload": False}, {"F", "G"}),
        ({"kambal_batch": False}, {"H"}),
        ({"vigor_counters": False}, {"I", "J"}),
        ({"own_wipe_scope": False}, {"K", "L", "M", "N", "T"}),
        ({"giada_text": False}, {"O"}),
        ({"overseer_taps": False}, {"Q", "R"}),
        ({"gsz_shuffle": False}, {"S"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, want in mutations:
        CFG.update(over)
        try:
            broke = run_cases()
        finally:
            CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {over}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
