#!/usr/bin/env python3
"""§0z235 (queue item 50): the mana census's classifier, on fixed text.

    python -m tests.test_mana_census
    python -m tests.test_mana_census --mutate   # 4 mutations, exact sets

`tools.removal_census.classify_ramp` reads the pod's ramp from oracle text.
Each case hands it one card's type line and text -- copied from Scryfall on
2026-11-20 for the real cards, made up for P and M -- with no network, and
reads the bucket.

CASES
  A  Sol Ring: a rock, two mana a turn
  B  Azorius Signet: a rock, ONE net ({1}, {T}: Add {W}{U})
  C  Marble Diamond: a rock that enters tapped
  D  Birds of Paradise: NOT ramp -- a creature's mana, queue item 52
  E  Solemn Simulacrum: LAND ramp, one land, tapped (a creature that fetches:
     the land stays when it dies)
  F  Burnished Hart: land ramp, two lands, cost 6 (3 to cast, {3} to use)
  G  Cultivate: land ramp, ONE land (the other goes to hand)
  H  Path to Exile: NOT ramp -- a gift, its controller fetches a land
  I  Exploration: an extra land drop
  J  Dryad of the Ilysian Grove: NOT ramp -- a creature's extra land, item 52
  K  Ashnod's Altar: NOT ramp -- a sacrifice outlet
  L  Mind Stone: a rock, one net (its sacrifice ability is not its mana)
  O  Bender's Waterskin: a rock flagged `untaps_each_turn`
  P  a one-shot rock ("{T}, Sacrifice this artifact: Add ..."): RAISES -- no
     rule reads it, and a cost with a sacrifice is not a rock
  M  an unreadable rock ("Add mana equal to ..."): RAISES
  N  Lightning Bolt: not mana at all (None)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the creature-mana rule never matches       -> D, J
  a sacrifice in a rock's cost is allowed    -> P
  the gift rule removed                      -> H
  activation costs read as 0                 -> B, F

M FAILED ON THE FIRST RUN, AND THE CENSUS WAS WRONG, NOT THE CASE: "Add mana
equal to ..." did not match `RAMP_CANDIDATE`, so such a card was read as
not mana at all -- silently, where the classifier exists to raise. The
candidate now reads "add mana" and "add an amount"; no expectation changed.

UNMUTATED (§0z15): A, C, E, G, I, K, L, O, M and N; each is read by a rule
no mutation here touches.
"""
import re
import sys

import tools.removal_census as RC

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []

CARDS = {
    "A": ("Sol Ring", "Artifact", "{T}: Add {C}{C}.", 1),
    "B": ("Azorius Signet", "Artifact", "{1}, {T}: Add {W}{U}.", 2),
    "C": ("Marble Diamond", "Artifact",
          "This artifact enters tapped.\n{T}: Add {W}.", 2),
    "D": ("Birds of Paradise", "Creature — Bird",
          "Flying\n{T}: Add one mana of any color.", 1),
    "E": ("Solemn Simulacrum", "Artifact Creature — Golem",
          "When this creature enters, you may search your library for a basic "
          "land card, put that card onto the battlefield tapped, then "
          "shuffle.\nWhen this creature dies, you may draw a card.", 4),
    "F": ("Burnished Hart", "Artifact Creature — Elk",
          "{3}, Sacrifice this creature: Search your library for up to two "
          "basic land cards, put them onto the battlefield tapped, then "
          "shuffle.", 3),
    "G": ("Cultivate", "Sorcery",
          "Search your library for up to two basic land cards, reveal those "
          "cards, put one onto the battlefield tapped and the other into your "
          "hand, then shuffle.", 3),
    "H": ("Path to Exile", "Instant",
          "Exile target creature. Its controller may search their library for "
          "a basic land card, put that card onto the battlefield tapped, then "
          "shuffle.", 1),
    "I": ("Exploration", "Enchantment",
          "You may play an additional land on each of your turns.", 1),
    "J": ("Dryad of the Ilysian Grove", "Enchantment Creature — Nymph Dryad",
          "You may play an additional land on each of your turns.\nLands you "
          "control are every basic land type in addition to their other "
          "types.", 3),
    "K": ("Ashnod's Altar", "Artifact", "Sacrifice a creature: Add {C}{C}.", 3),
    "L": ("Mind Stone", "Artifact",
          "{T}: Add {C}.\n{1}, {T}, Sacrifice this artifact: Draw a card.", 2),
    "O": ("Bender's Waterskin", "Artifact",
          "Untap this artifact during each other player's untap step.\n{T}: "
          "Add one mana of any color.", 3),
    "P": ("Not A Real Petal", "Artifact",
          "{T}, Sacrifice this artifact: Add one mana of any color.", 0),
    "M": ("Not A Real Rock", "Artifact",
          "{T}: Add mana equal to the number of lands you control.", 4),
    "N": ("Lightning Bolt", "Instant",
          "Lightning Bolt deals 3 damage to any target.", 1),
}

WANT = {
    "A": ("rock", 1.0, 2, ()),
    "B": ("rock", 2.0, 1, ()),
    "C": ("rock", 2.0, 1, ("tapped",)),
    "D": ("not", "on a creature: queue item 52"),
    "E": ("land", 4.0, 1, ("tapped",)),
    "F": ("land", 6.0, 2, ("tapped",)),
    "G": ("land", 3.0, 1, ("tapped",)),
    "H": ("not", "gift"),
    "I": ("drop", 1.0, 1, ()),
    "J": ("not", "on a creature: queue item 52"),
    "K": ("not", "sacrifice outlet"),
    "L": ("rock", 2.0, 1, ()),
    "O": ("rock", 3.0, 1, ("untaps_each_turn",)),
    "P": "raises",
    "M": "raises",
    "N": None,
}


def read(key):
    name, tl, text, mv = CARDS[key]
    try:
        hit = RC.classify_ramp(name, tl, text, mv)
    except ValueError:
        return "raises"
    if hit is None:
        return None
    # the clause is the evidence, not the verdict: compare the rest
    return hit[:2] if hit[0] == "not" else hit[:4]


def run_cases():
    PASS.clear()
    FAIL.clear()
    for key in CARDS:
        got, want = read(key), WANT[key]
        ok = got == want
        (PASS if ok else FAIL).append(key)
        print(f"  {'PASS' if ok else 'FAIL'}  {key} {CARDS[key][0]}"
              + ("" if ok else f"   got {got!r}, want {want!r}"))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z235: the mana census's classifier\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    never = re.compile(r"(?!x)x")
    no_gift = tuple(r for r in RC.NOT_RAMP_RULES if r[0] != "gift")
    sac_ok = re.compile(r"(?:^|\n)((?:\{[^}]+\}, )*\{t\}(?:, [^:\n]*)?): "
                        r"add ([^.\n]*)")
    muts = {
        "the creature-mana rule never matches": (
            {"D", "J"}, [("CREATURE_MANA", never)]),
        "a sacrifice in a rock's cost is allowed": (
            {"P"}, [("ROCK_ABILITY", _SacAllowed(sac_ok))]),
        "the gift rule removed": ({"H"}, [("NOT_RAMP_RULES", no_gift)]),
        "activation costs read as 0": (
            {"B", "F"}, [("generic", lambda cost: 0)]),
    }
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        saved = [(name, getattr(RC, name)) for name, _ in patches]
        for name, val in patches:
            setattr(RC, name, val)
        try:
            broke = run_cases()
        finally:
            for name, val in saved:
                setattr(RC, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


class _SacAllowed:
    """A ROCK_ABILITY whose matches hide the word "sacrifice" from the cost,
    so `classify_ramp`'s "no sacrifice in a rock's cost" test passes them."""

    def __init__(self, pat):
        self.pat = pat

    def findall(self, text):
        return [(c.replace("sacrifice", "sac"), a)
                for c, a in self.pat.findall(text)]

    def search(self, text):
        return self.pat.search(text)


if __name__ == "__main__":
    sys.exit(main())
