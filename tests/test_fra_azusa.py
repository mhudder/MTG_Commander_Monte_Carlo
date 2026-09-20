#!/usr/bin/env python3
"""Pin the two Reality Fracture cards imported into azusa on 2026-09-20.

    python -m tests.test_fra_azusa
    python -m tests.test_fra_azusa --mutate   # 3 mutations, exact sets

PREVIEW TEXT. Reality Fracture releases 2026-10-02; this text was fetched from
Scryfall on 2026-09-20 and can change before release. These checks pin the
ENGINE against the text as fetched, so if the text changes the checks are what
tells you which claims have to be re-read.

WHAT EACH CHECK EXISTS FOR.

Verdant Kraken: "At the beginning of EACH PLAYER'S upkeep, you create a 3/3
green Forest Tentacle land creature token." The card is the word EACH -- at one
upkeep a round it is a 3/3 that taps for {G}, at four it is a landfall engine.
Four properties of the token are load-bearing and each is checked separately,
because Awaken the Woods' token had all four and three of them were gaps that
had to be closed before that card could be measured at all:

  A  four tokens a round, one at your upkeep and three at the pod's
  B  each one is a LANDFALL trigger (this deck's entire payoff surface)
  C  they are FORESTS, so `is_forest` says yes and they tap for {G}
  D  they are SICK the turn they arrive (302.6) and live the turn after
  E  they are CREATURES, so the pod's wraths kill them

Simulacrum Shaper: "When this creature enters, you may search your library for
a basic land card, put that card onto the battlefield TAPPED"; "When this
creature dies, draw a card."

  F  the ETB fetches a basic ONTO THE BATTLEFIELD and fires landfall
  G  the fetched land arrives tapped, so it makes no mana that turn
  H  the death trigger draws exactly one, once per permanent
  I  the ETB does NOT fire for a token copy of something else, and the two
     cards sharing `make_permanent`'s hook still work (§0z28's indentation)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  verdant_kraken_tokens ignores any count but 1  -> A and B
  the token is not a Forest                      -> C only
  the Shaper's ETB does not fetch                -> F and G

TWO OF THE THREE EXPECTATIONS WERE WRONG ON THE FIRST RUN and both errors are
kept here, because the house rule is that a set edited to match the output is a
transcript rather than a test.

  * The first was written as "the pod's three upkeeps are not taken -> A only",
    reasoning that B counts `landfall_triggers` and the pod's three tokens
    would still raise it. That reasoning was about a DIFFERENT DEFECT than the
    mutation implements. Deleting take_turn's pod-side CALL breaks A alone;
    making the METHOD ignore any count but 1 also breaks B, because B calls
    `verdant_kraken_tokens(4)` directly. Both are defects this card could ship
    with, they are distinguishable, and the label now names the one that is
    actually installed.
  * The third predicted F and G and also broke I, because I read
    `shaper_lands` alongside the neighbour's counter. That was a flaw in the
    CHECK, not in the prediction: a case whose job is to prove one card did not
    swallow another's trigger must not depend on the first card working. I now
    reads only `guardian_project_draws`, and the prediction holds.
"""
import sys

from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import azusa_v1 as M
from edhmc.engine import Card
import edhmc.azusa as AZ
from edhmc import opponents as OPP

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh():
    deck, cmd = M.build()
    return AzusaGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: four tokens a round ------------------------------------------
    g = fresh()
    g.make_permanent(M.VERDANT_KRAKEN, sick=False)
    AZ.take_turn(g)
    check("A four Forest Tentacles a round (1 upkeep + 3 pod)",
          g.m["kraken_tokens"], 4)

    # ---- B: each token is a landfall trigger ------------------------------
    g = fresh()
    before = g.m["landfall_triggers"]
    g.make_permanent(M.VERDANT_KRAKEN, sick=False)
    g.verdant_kraken_tokens(4)
    check("B each token fires landfall",
          g.m["landfall_triggers"] - before, 4)

    # ---- C: the token is a Forest and taps for {G} ------------------------
    g = fresh()
    g.make_permanent(M.VERDANT_KRAKEN, sick=False)
    g.verdant_kraken_tokens(1)
    tok = next(p for p in g.board if p.card.name == "Forest Tentacle token")
    check("C the token is a Forest that produces {G}",
          (AZ.is_forest(tok.card), sorted(tok.card.produces)), (True, ["G"]))

    # ---- D: sick the turn it lands, live the turn after -------------------
    g = fresh()
    g.make_permanent(M.VERDANT_KRAKEN, sick=False)
    g.verdant_kraken_tokens(1)
    tok = next(p for p in g.board if p.card.name == "Forest Tentacle token")
    now = g.land_mana_live(tok)
    tok.sick = False                      # what the next untap step does
    check("D the token makes no mana the turn it arrives, and does after",
          (now, g.land_mana_live(tok)), (False, True))

    # ---- E: it is a creature, so a wrath kills it ------------------------
    g = fresh()
    g.make_permanent(M.VERDANT_KRAKEN, sick=False)
    g.verdant_kraken_tokens(1)
    tok = next(p for p in g.board if p.card.name == "Forest Tentacle token")
    OPP.destroy(g, tok, destroys=False)
    check("E a wrath kills the token",
          any(p.card.name == "Forest Tentacle token" for p in g.board), False)

    # ---- F: the Shaper's ETB fetches a basic and fires landfall -----------
    g = fresh()
    lands_before = sum(1 for p in g.board if p.card.is_land)
    lf_before = g.m["landfall_triggers"]
    g.make_permanent(M.SIMULACRUM_SHAPER, sick=False)
    check("F the ETB puts a basic on the battlefield and fires landfall",
          (g.m["shaper_lands"],
           sum(1 for p in g.board if p.card.is_land) - lands_before,
           g.m["landfall_triggers"] - lf_before), (1, 1, 1))

    # ---- G: the fetched land arrives tapped -------------------------------
    g = fresh()
    g.make_permanent(M.SIMULACRUM_SHAPER, sick=False)
    # `next(..., None)` rather than a bare `next`: under the third mutation no
    # land is fetched at all, and a StopIteration here would CRASH the mutation
    # run instead of failing this case -- §0z15's exact shape, caught in the
    # run that exists to prove these checks can fail.
    land = next((p for p in g.board if p.card.is_land), None)
    check("G the fetched basic arrives tapped",
          land.tapped if land is not None else None, True)

    # ---- H: the death trigger draws one -----------------------------------
    g = fresh()
    g.make_permanent(M.SIMULACRUM_SHAPER, sick=False)
    perm = next(p for p in g.board if p.card.name == "Simulacrum Shaper")
    hand_before, drew_before = len(g.hand), g.m["shaper_draws"]
    OPP.destroy(g, perm, destroys=False)
    check("H the death trigger draws exactly one card",
          (g.m["shaper_draws"] - drew_before, len(g.hand) - hand_before), (1, 1))

    # ---- I: a token does not trigger it, and the hook's neighbours live ---
    g = fresh()
    g.make_permanent(M.GUARDIAN_PROJECT, sick=False)
    before = g.m["guardian_project_draws"]
    g.make_tokens(1, 1, 1, "Insect")                 # a token creature enters
    after_token = g.m["guardian_project_draws"]
    g.make_permanent(M.SIMULACRUM_SHAPER, sick=False)  # a nontoken creature
    # DELIBERATELY reads only the NEIGHBOUR's counter. It used to read
    # `shaper_lands` as well, which made it fail under the fetch mutation and
    # broke its own expected set: a check that exists to prove one card did not
    # eat another's trigger must not depend on that other card working.
    check("I a token triggers nothing, a nontoken still triggers the neighbour",
          (after_token - before, g.m["guardian_project_draws"] - after_token),
          (0, 1))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Reality Fracture in azusa -- Verdant Kraken, Simulacrum Shaper\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_tokens = AZ.AzusaGame.verdant_kraken_tokens
    real_forests = AZ.FOREST_TOKENS
    real_make = AZ.AzusaGame.make_permanent
    expected = {
        "verdant_kraken_tokens ignores any count but 1": {"A", "B"},
        "the token is not a Forest": {"C"},
        "the Shaper's ETB does not fetch": {"F", "G"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "verdant_kraken_tokens ignores any count but 1":
            AZ.AzusaGame.verdant_kraken_tokens = (
                lambda self, upkeeps: real_tokens(self, 1 if upkeeps == 1 else 0))
        elif label == "the token is not a Forest":
            AZ.FOREST_TOKENS = frozenset()
        else:
            # Remove the fetch itself: empty the library of basics.
            AZ.AzusaGame.make_permanent = lambda self, card, *a, **kw: (
                real_make(self, card, *a, **kw)
                if card.name != "Simulacrum Shaper"
                else (self.library.__setitem__(
                    slice(None), [c for c in self.library if c.name != "Forest"])
                      or real_make(self, card, *a, **kw)))
        try:
            broke = run_cases()
        finally:
            AZ.AzusaGame.verdant_kraken_tokens = real_tokens
            AZ.FOREST_TOKENS = real_forests
            AZ.AzusaGame.make_permanent = real_make
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
