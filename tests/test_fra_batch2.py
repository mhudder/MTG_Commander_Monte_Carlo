#!/usr/bin/env python3
"""Pin the four Reality Fracture cards imported on 2026-09-21, one per deck.

    python -m tests.test_fra_batch2
    python -m tests.test_fra_batch2 --mutate   # 4 mutations, exact sets

PREVIEW TEXT. Reality Fracture releases 2026-10-02; this text was fetched from
Scryfall on 2026-09-21 and can change before release.

  rendmaw     Proft, Sinister Mastermind  Threshold: uncastable under 7 cards
                                          in the graveyard (601.3, a
                                          CASTABILITY restriction)
  lorehold    Stingcaster Mage            one flashback cast, at FULL price
  tivit       Memnarch, the Warden        two MYR ARTIFACT tokens on ETB; on
                                          attack, draw per artifact
  shilgengar  Lyra, Archangel of Dawn     lifegain -> a counter on each ANGEL

CASES
  A  Proft is not an option with six cards in the yard
  B  Proft IS an option with seven, and the gate counter moved only in A
  C  Stingcaster casts exactly ONE card from the graveyard, and exiles it
  D  Stingcaster pays FULL PRICE (mana leaves, mv_cheated does not move)
  E  Memnarch's ETB makes two tokens that `artifact_count()` SEES
  F  Memnarch's attack trigger draws once per artifact, on declaration
  G  Lyra puts a counter on each Angel and on nothing else
  H  Lyra counts EVENTS, not points of life
  I  702.34a: the flashed-back card is EXILED, not re-filed in the yard

MUTATIONS, exact sets:
  the Threshold gate is removed          -> A
  Stingcaster's cap is lifted to 6       -> C and I
  the flashback exile is removed         -> C and I
  Memnarch's tokens are not artifacts    -> E
  Lyra's trigger ignores the Angel test  -> G and H

ALL FIVE EXPECTATIONS WERE WRONG ON THE FIRST RUN, in two different ways, and
both are kept because a set edited to match the output is a transcript.

TWO MUTATIONS WERE NEVER INSTALLED. "The Threshold gate is removed" and "the
flashback exile is removed" set module flags -- `PROFT_GATE_OFF`,
`LOREHOLD_NO_EXILE` -- that no production code reads, so they broke NOTHING and
would have read as "the checks do not depend on these rules". The fix was in the
engine, not the test: the Threshold count is now the named constant
`engine.PROFT_THRESHOLD` and the exile is now `lorehold.exile_flashback`, both
reachable. A mutation that changes no behaviour is the failure mode §0z15 warns
about, arrived at from the other direction.

THREE PREDICTIONS WERE WRONG FOR REAL REASONS.
  * Lifting Stingcaster's cap also breaks I, because I asserts an exact exile
    COUNT of one and a cap of six exiles three. Keeping the exact count is
    worth more than an expectation that reads {C} alone.
  * Un-typing Memnarch's tokens breaks E and NOT F, because F asserts a RATIO
    -- draws equal `artifact_count()` as it stands after the ETB -- which holds
    at any token typing. That is the right split: E checks the tokens are in the
    count, F checks the trigger reads the count.
  * Removing the exile breaks C as well as I, because C's second element is
    the graveyard SHRINK -- which is the exile, measured from the other side.
    Its label says "and exiles it from the yard", so that is the case doing
    what it says rather than an accident; the prediction of {I} alone simply
    forgot that two cases cover one rule.
  * Widening Lyra's Angel test breaks G and H, because H asserts two counters
    per event (Lyra and one other Angel) and a Bear on the board makes three.
"""
import sys

from edhmc.experiment import DEFAULT_CFG
from edhmc.engine import Card, Permanent
import edhmc.engine as EN
import edhmc.lorehold as LH
import edhmc.tivit as TV
import edhmc.shilgengar as SH
from edhmc.decks import rendmaw_v12 as RM, lorehold_v16 as LM
from edhmc.decks import tivit_v1 as TM, shilgengar_v1 as SM

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(mod, sim_mod, turns=20, seed=1234):
    deck, cmd = mod.build()
    return sim_mod(deck, cmd, dict(DEFAULT_CFG, turns=turns), seed)


def rendmaw_game():
    # engine.Game takes a random.Random, not a seed -- the other five engines
    # take the seed. Passing 1234 here raised inside the constructor's shuffle.
    deck, cmd = RM.build()
    cfg = dict(DEFAULT_CFG, turns=20)
    return EN.Game(deck, cmd, cfg, EN.make_rng(1234, cfg), seed_for_pod=1234)


def lorehold_game():
    deck, cmd = LM.build()
    return LH.LoreholdGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def tivit_game():
    deck, cmd = TM.build()
    return TV.TivitGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def shil_game():
    deck, cmd = SM.build()
    return SH.ShilgengarGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def bear(name="Bear"):
    return Card(name=name, types=frozenset({"Creature"}), power=2, toughness=2)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A / B: Proft's Threshold -----------------------------------------
    for n_yard, want_option in ((6, False), (7, True)):
        g = rendmaw_game()
        g.hand = [RM.PROFT_SINISTER_MASTERMIND]
        g.graveyard = [bear(f"junk {i}") for i in range(n_yard)]
        # enough mana to cast it, so the ONLY thing that can stop it is the gate
        for i in range(5):
            g.board.append(Permanent(card=Card(
                name="Swamp", types=frozenset({"Land"}), is_land=True,
                produces=frozenset({"B"})), sick=False))
        before = g.m["proft_gated"]
        EN.main_phase(g)
        cast = not any(c.name == "Proft, Sinister Mastermind" for c in g.hand)
        gated = g.m["proft_gated"] - before
        if n_yard == 6:
            check("A Proft is not castable under seven cards in the yard",
                  (cast, gated > 0), (False, True))
        else:
            check("B Proft is castable at seven, and the gate did not fire",
                  (cast, gated), (True, 0))

    # ---- C / D: Stingcaster Mage ------------------------------------------
    g = lorehold_game()
    bolt = next(c for c in LM.build()[0]
                if ("Instant" in c.types or "Sorcery" in c.types) and c.mv <= 2)
    g.graveyard = [bolt, next(c for c in LM.build()[0]
                              if ("Instant" in c.types or "Sorcery" in c.types)
                              and c is not bolt and c.mv <= 2)]
    # BOTH COLOURS. Six Mountains could not pay for this deck's two cheapest
    # spells (Swords to Plowshares and Path to Exile are both {W}), so the
    # first version of C and D failed on the test's mana, not on the card.
    for colour in ("R", "W"):
        for i in range(3):
            g.board.append(Permanent(card=Card(
                name=f"{colour} source", types=frozenset({"Land"}),
                is_land=True, produces=frozenset({colour})), sick=False))
    yard_before, mv_before = len(g.graveyard), g.m["mv_cheated"]
    spent_before = g.m["mana_spent"]
    # UNTAPPED LANDS, not untapped permanents. The first version of case D
    # counted permanents and read 6 before and 6 after -- because Stingcaster
    # itself enters untapped and masked the land that WAS tapped. That looked
    # like free mana and was an off-by-one-permanent in the test.
    lands_up_before = sum(1 for p in g.board if p.card.is_land and not p.tapped)
    LH.resolve_spell(g, LM.STINGCASTER_MAGE, 2, from_hand=True)
    check("C Stingcaster casts exactly one card and exiles it from the yard",
          (g.m["stingcaster_casts"], yard_before - len(g.graveyard)), (1, 1))
    check("D Stingcaster pays full price: mana spent, nothing cheated",
          (g.m["mv_cheated"] - mv_before,
           g.m["mana_spent"] > spent_before,
           sum(1 for p in g.board if p.card.is_land and not p.tapped)
           < lands_up_before),
          (0, True, True))

    # ---- I: 702.34a, the flashed-back card is EXILED ----------------------
    # It is not enough that `past_in_flames` removes it before resolving:
    # `resolve_spell` files every non-permanent into the graveyard, so without
    # the second removal the card comes straight back and the same spell can be
    # cast up to `flashback_cap` times off one Past in Flames.
    check("I the flashed-back card is exiled, not returned to the yard",
          (bolt in g.graveyard, g.m["flashback_exiled"]), (False, 1))

    # ---- E / F: Memnarch --------------------------------------------------
    g = tivit_game()
    arts_before = g.artifact_count()
    TV.resolve(g, TM.MEMNARCH_THE_WARDEN)
    check("E the ETB makes two tokens that artifact_count() sees",
          g.artifact_count() - arts_before, 3)      # 2 Myr + Memnarch itself
    perm = next(p for p in g.board if p.card.name == "Memnarch, the Warden")
    perm.sick = False
    drew_before, arts = g.m["memnarch_draws"], g.artifact_count()
    TV.combat(g)
    check("F the attack trigger draws once per artifact",
          g.m["memnarch_draws"] - drew_before, arts)

    # ---- G / H: Lyra ------------------------------------------------------
    g = shil_game()
    angel = next(c for c in SM.build()[0] if "angel" in c.tags)
    g.board.append(Permanent(card=SM.LYRA_ARCHANGEL_OF_DAWN, sick=False))
    g.board.append(Permanent(card=angel, sick=False))
    g.board.append(Permanent(card=bear("Not An Angel"), sick=False))
    g.gain_life(1)
    counters = {p.card.name: p.counters for p in g.board}
    check("G a counter on each Angel and on nothing else",
          (counters["Lyra, Archangel of Dawn"], counters[angel.name],
           counters["Not An Angel"]), (1, 1, 0))
    before = g.m["lyra_counters"]
    g.gain_life(7)                      # one EVENT worth seven points
    check("H one counter per lifegain EVENT, not per point of life",
          g.m["lyra_counters"] - before, 2)     # Lyra + the other Angel
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Reality Fracture batch 2 -- one card per remaining deck\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_flames = LH.past_in_flames
    real_exile = LH.exile_flashback
    real_tokens = TV.TivitGame.make_tokens
    real_angel = SH.ShilgengarGame.is_angel
    expected = {
        "the Threshold gate is removed": {"A"},
        "Stingcaster's cap is lifted to 6": {"C", "I"},
        "the flashback exile is removed": {"C", "I"},
        "Memnarch's tokens are not artifacts": {"E"},
        "Lyra's trigger ignores the Angel test": {"G", "H"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == "the Threshold gate is removed":
            EN.PROFT_THRESHOLD = 0
        elif label == "Stingcaster's cap is lifted to 6":
            LH.past_in_flames = (lambda g, self_card=None, cap=None:
                                 real_flames(g, self_card=self_card, cap=6))
        elif label == "the flashback exile is removed":
            LH.exile_flashback = lambda g, card: None
        elif label == "Memnarch's tokens are not artifacts":
            TV.TivitGame.make_tokens = (
                lambda self, n, p, t, subtype="", tapped=False, artifact=False:
                real_tokens(self, n, p, t, subtype, tapped, False))
        else:
            SH.ShilgengarGame.is_angel = lambda self, perm: True
        try:
            broke = run_cases()
        finally:
            EN.PROFT_THRESHOLD = 7
            LH.exile_flashback = real_exile
            LH.past_in_flames = real_flames
            TV.TivitGame.make_tokens = real_tokens
            SH.ShilgengarGame.is_angel = real_angel
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
