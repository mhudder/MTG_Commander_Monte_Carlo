#!/usr/bin/env python3
"""Queued item 17 -- drawing from an empty library loses, and the pilot knows it.

    python -m tests.test_decking
    python -m tests.test_decking --mutate   # 5 mutations, exact sets

THE RULE. 704.5b: "If a player attempted to draw a card from a library with
no cards in it since the last time state-based actions were checked, that
player loses the game." Until 2026-09-22 every `draw` in six engines stopped
silently at an empty library. It lives in ONE function now,
`engine.drew_from_empty`, called by the three draw paths the engines have:
`BaseGame.draw`, karlov's Alhammarret's Archive override, and lorehold's
`draw_card`.

THE PILOT. The rule on its own decked azusa in 3.3% of games at T20 and
lorehold in 1.6% -- in exactly the games they were winning, with a draw engine
running. A pilot declines an OPTIONAL draw rather than deck, so
`engine.draw_is_safe` guards every site whose card text gives a choice (a
"may", an activation, a mode, a spell not yet cast, a land drop under Horn of
Greed), and none whose text does not.

AND A BUG THE MEASUREMENT FOUND (§0z41). Horn of Greed's draw sat inside the
loop Ancient Greenwarden and Traveling Chocobo multiply, so one land drop drew
three cards. Greenwarden's 2020-09-25 ruling: "An ability that triggers
whenever you play a land won't trigger an additional time."

CASES
  A  rendmaw: a draw from an empty library is a loss, loss_route 3
  B  `decking_loss=False`: the same draw is counted and nothing is lost
  C  a game already WON is not turned into a loss by a later empty draw
  D  karlov: Archive's SECOND draw off a one-card library loses too
  E  lorehold: `draw_card` from an empty library loses
  F  `draw_is_safe` arithmetic, and both knobs that switch it off
  G  azusa: Horn of Greed draws ONCE with Greenwarden and Chocobo out
  H  azusa: `horn_doubled_legacy=True` reproduces the old triple draw
  I  azusa: a land drop under Horn is declined one card from empty, and
     taken from a full library
  J  azusa: `draws_on_resolve` reads Momentous Fall off its smallest fodder
  K  lorehold: `pilot_may_cast` refuses a wheel off a short library
  L  lorehold: `spell_draws` equals what `apply_spell_effects` ACTUALLY draws,
     for every scripted card in the list -- derived, so a new draw script
     that is not named in SPELL_DRAWS fails here (§0q)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  an empty draw does not lose (count only)        -> A, D, E
  the pilot never holds back                      -> F, I, K
  Horn of Greed back inside the doubled loop      -> G
  SPELL_DRAWS forgets the wheel                   -> K, L
  a later empty draw overwrites an existing win   -> C

WHAT HAS NO MUTATION (§0z15). B and H are the knobs' own contracts; J is
the fodder arithmetic, which no guard mutation reaches because J reads the
count and not the decision. Each is a regression case with nothing behind it.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.lorehold as LH
from edhmc.azusa import AzusaGame
from edhmc.karlov import KarlovGame
from edhmc.decks import (azusa_v1 as AZM, karlov_v2 as KM, lorehold_v16 as LM,
                         rendmaw_v12 as RM)
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return dict(DEFAULT_CFG, turns=20, watch=frozenset(), **kw)


def rendmaw(**kw):
    deck, cmd = RM.build()
    return EN.Game(deck, cmd, cfg(**kw), random.Random(7), 1234)


def card_named(module, name):
    deck, _ = module.build()
    return next(c for c in deck if c.name == name)


def azusa(**kw):
    deck, cmd = AZM.build()
    return AzusaGame(deck, cmd, cfg(**kw), 1234)


def lorehold(**kw):
    deck, cmd = LM.build()
    return LH.LoreholdGame(deck, cmd, cfg(**kw), 1234)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: the rule ----------------------------------------------------
    g = rendmaw()
    g.library = []
    g.draw(1)
    check("A an empty draw loses (rendmaw), loss_route 3",
          (g.result, g.m["loss_route"], g.m["drew_from_empty"]),
          ("loss", 3, 1))

    # ---- B: the knob that turns it off -------------------------------------
    g = rendmaw(decking_loss=False)
    g.library = []
    g.draw(2)
    check("B decking_loss=False: counted, not lost",
          (g.result, g.m["drew_from_empty"]), (None, 1))

    # ---- C: first result wins ------------------------------------------
    g = rendmaw()
    g.library = []
    g.result = "win"
    g.draw(1)
    check("C a game already won stays won", g.result, "win")

    # ---- D: karlov's Archive -- the replacement draw is a draw ---------
    deck, cmd = KM.build()
    g = KarlovGame(deck, cmd, cfg(), 1234)
    g.board.append(Permanent(card=KM.ALHAMMARRETS_ARCHIVE, sick=False))
    g.in_draw_step = False
    g.library = g.library[-1:]
    g.draw(1)
    check("D karlov: Archive's second draw off one card loses",
          (g.m["cards_drawn"], g.result, g.m["loss_route"]), (1, "loss", 3))

    # ---- E: lorehold's own draw path -----------------------------------
    g = lorehold()
    g.library = []
    got = g.draw_card()
    check("E lorehold: draw_card from empty loses",
          (got, g.result, g.m["loss_route"]), (None, "loss", 3))

    # ---- F: the pilot's arithmetic -------------------------------------
    g = rendmaw()
    g.library = g.library[:5]
    got = (EN.draw_is_safe(g, 4), EN.draw_is_safe(g, 5))
    g.cfg["decking_reserve"] = 0
    got += (EN.draw_is_safe(g, 5),)
    g.cfg["decking_reserve"] = 1
    g.cfg["decking_pilot"] = False
    got += (EN.draw_is_safe(g, 50),)
    g.cfg["decking_pilot"] = True
    g.cfg["decking_loss"] = False
    got += (EN.draw_is_safe(g, 50),)
    check("F draw_is_safe: 5 cards keep 1 back; both knobs switch it off",
          got, (True, False, True, True, True))

    # ---- G / H: Horn of Greed is not doubled ----------------------------
    for tag, legacy, want in (("G", False, 1), ("H", True, 3)):
        # G takes the DEFAULT, never passes the knob -- passing False here
        # would override the mutation that reverts the default.
        g = azusa(horn_doubled_legacy=True) if legacy else azusa()
        for name in ("Horn of Greed", "Ancient Greenwarden"):
            g.make_permanent(card_named(AZM, name), sick=False)
        g.make_permanent(AZM.TRAVELING_CHOCOBO, sick=False)
        forest = next(c for c in g.library if c.name == "Forest")
        g.library.remove(forest)
        before = g.m["cards_drawn"]
        g.land_entered(forest, played=True)
        check(f"{tag} Horn of Greed with Greenwarden + Chocobo, legacy="
              f"{legacy}: draws {want}", g.m["cards_drawn"] - before, want)

    # ---- I: a land drop under Horn, declined at the edge ---------------
    got = []
    for keep in (1, 40):
        g = azusa()
        g.make_permanent(card_named(AZM, "Horn of Greed"), sick=False)
        forest = next(c for c in g.library if c.name == "Forest")
        g.library.remove(forest)
        g.hand = [forest]
        g.library = [c for c in g.library if not c.is_land][:keep]
        g.land_step()
        got.append((g.m["lands_played"], g.result))
    check("I Horn out: no land drop one card from empty, one from a full "
          "library", got, [(0, None), (1, None)])

    # ---- J: Momentous Fall's draw count ------------------------------------
    g = azusa()
    tok = EN.Card(name="Beast token", types=frozenset({"Creature"}),
                  power=4, toughness=4)
    big = EN.Card(name="Wurm token", types=frozenset({"Creature"}),
                  power=9, toughness=9)
    for c in (tok, big):
        # through make_permanent: azusa's power_of reads `base_p`, which only
        # the engine's own constructor sets
        g.make_permanent(c, sick=False, is_token=True)
    check("J draws_on_resolve(Momentous Fall) is the smallest fodder's power",
          g.draws_on_resolve(card_named(AZM, "Momentous Fall")), 4)

    # ---- K: the lorehold cast guard ------------------------------------
    wheel = EN.Card(name="a wheel", types=frozenset({"Sorcery"}),
                    script="wheel")
    g = lorehold()
    g.library = g.library[:5]
    short = LH.pilot_may_cast(g, wheel)
    g.library = lorehold().library[:50]
    check("K pilot_may_cast: a wheel is refused off 5 cards, cast off 50",
          (short, LH.pilot_may_cast(g, wheel)), (False, True))

    # ---- L: spell_draws is derived-checked against the resolution --------
    deck, _ = LM.build()
    wrong = []
    for c in deck:
        if c.is_land or not c.script:
            continue
        g = lorehold()
        g.hand, g.graveyard = [], []
        want = LH.spell_draws(g, c)
        before = g.m["cards_drawn"]
        LH.apply_spell_effects(g, c)
        if g.m["cards_drawn"] - before != want:
            wrong.append((c.name, want, g.m["cards_drawn"] - before))
    # the scripts are also checked from the table's side: each fixed count
    # in SPELL_DRAWS is exercised by a synthetic card, whether or not the
    # current list carries one.
    for sc, n in LH.SPELL_DRAWS.items():
        g = lorehold()
        g.hand, g.graveyard = [], []
        before = g.m["cards_drawn"]
        LH.apply_spell_effects(g, EN.Card(name=f"synthetic {sc}",
                                          types=frozenset({"Sorcery"}),
                                          script=sc))
        if g.m["cards_drawn"] - before != n:
            wrong.append((sc, n, g.m["cards_drawn"] - before))
    check("L spell_draws matches what resolution draws, every script", wrong,
          [])
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("decking -- 704.5b, and the pilot that avoids it\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_dfe = EN.drew_from_empty
    real_safe = EN.draw_is_safe
    real_cfg = dict(DEFAULT_CFG)
    real_table = dict(LH.SPELL_DRAWS)
    expected = {
        "an empty draw does not lose (count only)": {"A", "D", "E"},
        "the pilot never holds back": {"F", "I", "K"},
        "Horn of Greed back inside the doubled loop": {"G"},
        "SPELL_DRAWS forgets the wheel": {"K", "L"},
        "a later empty draw overwrites an existing win": {"C"},
    }
    # The engines bind these by NAME at import (`from edhmc.engine import
    # drew_from_empty`), so a mutation must be installed in every module that
    # holds the name or it reaches nothing -- test_floating_mana's lesson.
    import edhmc.azusa as AZ
    import edhmc.karlov as KA
    holders_dfe = (EN, KA, LH)
    holders_safe = (EN, AZ, LH)

    def install(name, fn, holders):
        for mod in holders:
            setattr(mod, name, fn)

    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "an empty draw does not lose (count only)":
            def count_only(g):
                g.m["drew_from_empty"] += 1
            install("drew_from_empty", count_only, holders_dfe)
        elif label == "the pilot never holds back":
            install("draw_is_safe", lambda g, n: True, holders_safe)
        elif label == "Horn of Greed back inside the doubled loop":
            # the legacy branch IS the pre-fix code, so forcing it on for
            # every game is the revert. H already sets it and still passes.
            DEFAULT_CFG["horn_doubled_legacy"] = True
        elif label == "SPELL_DRAWS forgets the wheel":
            del LH.SPELL_DRAWS["wheel"]
        else:
            # ONLY the first-result guard is dropped. The first version of
            # this mutation dropped the `decking_loss` gate with it and broke
            # B as well as C -- two rules mutated, one reported (the same
            # slip test_monarch records). The expected set was right.
            def overwrites(g):
                g.m["drew_from_empty"] += 1
                if g.cfg.get("decking_loss", True):
                    g.result = "loss"
                    g.m["loss_route"] = 3
            install("drew_from_empty", overwrites, holders_dfe)
        try:
            broke = run_cases()
        finally:
            install("drew_from_empty", real_dfe, holders_dfe)
            install("draw_is_safe", real_safe, holders_safe)
            DEFAULT_CFG.clear()
            DEFAULT_CFG.update(real_cfg)
            LH.SPELL_DRAWS.clear()
            LH.SPELL_DRAWS.update(real_table)
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
