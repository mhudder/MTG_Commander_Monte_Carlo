#!/usr/bin/env python3
"""§0z211: Animist's Awakening reveals the top X and keeps the lands among
them, by its text, where it used to take the first X lands anywhere.

    python -m tests.test_animist_awakening
    python -m tests.test_animist_awakening --mutate   # 3 mutations, exact sets

    "Reveal the top X cards of your library. Put all land cards from among
    them onto the battlefield tapped and the rest on the bottom of your
    library in a random order. Spell mastery -- If there are two or more
    instant and/or sorcery cards in your graveyard, untap those lands."

The old rule (`animist_reveal=False`) took `next(c for c in self.library if
c.is_land)` four times -- the four DEEPEST lands, since index 0 is the
bottom -- and always tapped (§0z209 item 2). The new rule, the default,
reveals the top four at the fixed X (`x_pips` 4), puts the lands among them
in, bottoms the rest on the `awakening_bottom` stream, and untaps the lands
with spell mastery (`engine.spell_mastery`, shared with lorehold's two
readers). The library's top is its END.

CASES -- the top four, top first: Forest, Harmonize, Forest, Sol Ring; a
third Forest is the fifth card.
  A  the two Forests among the top four enter; the fifth card is the top now
  B  Harmonize and Sol Ring are the library's bottom two; the library is two
     shorter; only the Awakening is in the graveyard
  C  an empty graveyard: no spell mastery, both lands tapped
  D  Cultivate and Kodama's Reach in the graveyard: mastery, both untapped
  E  Cultivate and Eternal Witness: one sorcery is not two -- tapped
  F  each land put fires landfall: `landfall_triggers` +2
  G  the counters: `awakening_revealed` 4, `awakening_lands` 2,
     `awakening_mastery` 0
  H  a three-card library (Sol Ring, Forest, Harmonize): three revealed,
     the Forest in, the two others the whole library, no crash
  I  NEIGHBOUR: `animist_reveal=False` is the old rule -- four lands, all
     tapped, the library four shorter
  J  the bottom's random order does not touch `g.rng` (§0z17)
  K  `spell_mastery` itself: a sorcery and an artifact, False; two
     sorceries, True

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  animist_reveal=False everywhere                -> A, B, D, F, G, H
  spell_mastery reads ONE instant or sorcery     -> E, K
  the bottom shuffled on g.rng, not the stream   -> J

UNMUTATED (§0z15): C, I and K's False half are the neighbours. C is the
tapped default, which the old rule shares, so no mutation here reaches it;
it pins that mastery is not read as always-on. C and E read only whether
every land is tapped: the first mutation run had them compare the whole
list, which the old rule's four lands broke on the COUNT, and the count is
A's to pin (caught then, the expected set unchanged). J is reached by the stream
mutation alone: the old rule shuffles nothing.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
DECK, CMD = build_pending("azusa")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def fresh(**cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.board = EN.Board()
    return g


def take(g, name):
    """The named card out of the library, hand or graveyard: a DISTINCT
    object per call (§0z112)."""
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


TOP4 = ["Forest", "Harmonize", "Forest", "Sol Ring"]


def stacked(graveyard=(), **cfg):
    """A game with TOP4 on top of the library, a third Forest under it, and
    `graveyard` in the graveyard. Returns the game, the Awakening and the
    fifth card."""
    g = fresh(**cfg)
    awaken = take(g, "Animist's Awakening")
    top = [take(g, n) for n in TOP4]
    fifth = take(g, "Forest")
    g.graveyard[:] = [take(g, n) for n in graveyard]
    g.library.append(fifth)
    g.library.extend(reversed(top))
    return g, awaken, fifth


def lands_tapped(g):
    return [p.tapped for p in g.board if p.card.is_land]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, awaken, fifth = stacked()
    lib, lf = len(g.library), g.m["landfall_triggers"]
    state = g.rng.getstate()
    g.resolve(awaken)
    check("A the two Forests among the top four enter; the fifth is the top",
          (sorted(p.card.name for p in g.board), g.library[-1] is fifth),
          (["Forest", "Forest"], True))
    check("B the rest on the bottom; two shorter; only the Awakening milled",
          (sorted(c.name for c in g.library[:2]), lib - len(g.library),
           [c.name for c in g.graveyard]),
          (["Harmonize", "Sol Ring"], 2, ["Animist's Awakening"]))
    check("C an empty graveyard: no mastery, tapped",
          set(lands_tapped(g)), {True})
    check("F each land fires landfall", g.m["landfall_triggers"] - lf, 2)
    check("G the counters",
          (g.m["awakening_revealed"], g.m["awakening_lands"],
           g.m["awakening_mastery"]), (4, 2, 0))
    check("J the bottom's order leaves g.rng alone",
          g.rng.getstate() == state, True)

    g, awaken, _ = stacked(graveyard=["Cultivate", "Kodama's Reach"])
    g.resolve(awaken)
    check("D two sorceries in the graveyard: mastery, untapped",
          lands_tapped(g), [False, False])

    g, awaken, _ = stacked(graveyard=["Cultivate", "Eternal Witness"])
    g.resolve(awaken)
    check("E one sorcery and a creature: no mastery, tapped",
          set(lands_tapped(g)), {True})

    g = fresh()
    awaken = take(g, "Animist's Awakening")
    g.library[:] = [take(g, n) for n in ("Sol Ring", "Forest", "Harmonize")]
    g.resolve(awaken)
    check("H a three-card library: three revealed, the Forest in",
          (g.m["awakening_revealed"], [p.card.name for p in g.board],
           sorted(c.name for c in g.library)),
          (3, ["Forest"], ["Harmonize", "Sol Ring"]))

    g, awaken, _ = stacked(animist_reveal=False)
    lib = len(g.library)
    g.resolve(awaken)
    check("I animist_reveal=False: four lands, tapped, four shorter",
          (len(lands_tapped(g)), all(lands_tapped(g)), lib - len(g.library)),
          (4, True, 4))

    g = fresh()
    g.graveyard[:] = [take(g, "Harmonize"), take(g, "Sol Ring")]
    one = EN.spell_mastery(g)
    g.graveyard[:] = [take(g, "Cultivate"), take(g, "Kodama's Reach")]
    check("K spell_mastery: one sorcery False, two True",
          (one, EN.spell_mastery(g)), (False, True))
    return set(FAIL)


def _one_spell(g):
    return any("Instant" in c.types or "Sorcery" in c.types
               for c in g.graveyard)


def _rng_shuffle(g, name, seq):
    g.rng.shuffle(seq)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z211: Animist's Awakening reveals the top X\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "animist_reveal=False everywhere":
            ({"A", "B", "D", "F", "G", "H"}, {}, {"animist_reveal": False}),
        "spell_mastery reads one instant or sorcery":
            ({"E", "K"}, {"mastery": _one_spell}, {}),
        "the bottom shuffled on g.rng":
            ({"J"}, {"shuffle": _rng_shuffle}, {}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = (AZ.spell_mastery, EN.spell_mastery, AZ.crn_shuffle)
        if "mastery" in patch:
            AZ.spell_mastery = EN.spell_mastery = patch["mastery"]
        if "shuffle" in patch:
            AZ.crn_shuffle = patch["shuffle"]
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            AZ.spell_mastery, EN.spell_mastery, AZ.crn_shuffle = real
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
