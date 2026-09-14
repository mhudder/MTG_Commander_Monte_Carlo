#!/usr/bin/env python3
"""§7 / §0z19 — the three Lorehold recursion cards, one assertion per clause.

    python -m tests.test_recursion
    python -m tests.test_recursion --mutate    # 4 mutations, exact sets

All three oracle texts verified against Scryfall 2026-09-13. §7 has been open
since the project's early days and its own re-check warned that the last of
these "cuts both ways" — so the cases below pin the DRAWBACK as carefully as
the upside.

    Invoke Calamity  {1}{R}{R}{R}{R} Instant
      You may cast up to two instant and/or sorcery spells with TOTAL mana
      value 6 or less from your graveyard and/or hand without paying their
      mana costs. If those spells would be put into your graveyard, exile them
      instead. Exile Invoke Calamity.

    Volcanic Vision  {5}{R}{R} Sorcery
      Return target instant or sorcery card from your graveyard to your hand.
      Volcanic Vision deals damage equal to that card's mana value to each
      creature your opponents control. Exile Volcanic Vision.

    Goliath Daydreamer  {2}{R}{R} 4/4
      Whenever you cast an instant or sorcery spell from your hand, exile that
      card with a dream counter on it instead of putting it into your
      graveyard as it resolves.
      Whenever this creature attacks, you may cast a spell from among cards you
      own in exile with dream counters on them without paying its mana cost.

TOTAL SIX, NOT SIX EACH, is the clause a from-memory implementation gets
wrong, and case 1 exists for it alone.
"""
import sys

import edhmc.lorehold as L
import edhmc.engine as E
from edhmc.engine import Card, Permanent
from edhmc.decks.lorehold_v16 import build
from edhmc.decks.rendmaw_v12 import build as rw_build
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = build()


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(**extra):
    cfg = dict(DEFAULT_CFG, turns=20, **extra)
    return L.LoreholdGame(list(DECK), CMD, cfg, 1)


def spell(name, mv, kind="Sorcery"):
    return Card(name=name, types=frozenset({kind}), cost={"gen": mv},
                priority=5.0)


def named(name):
    return next(c for c in DECK if c.name == name)


def main():
    print(__doc__.split("\n\n")[0]); print()
    invoke = named("Invoke Calamity")
    vision = named("Volcanic Vision")

    # -- 1. TOTAL 6, not 6 each --------------------------------------------
    g = game()
    g.graveyard[:] = [spell("Four", 4), spell("Three", 3), spell("Two", 2)]
    g.hand[:] = []
    L.invoke_calamity(g, self_card=invoke)
    check("1  total MV <= 6 across BOTH, not 6 each (4+3 illegal, 4+2 legal)",
          round(g.m["invoke_mv"], 2), 6.0)
    check("1b it cast exactly two", g.m["invoke_free_casts"], 2)

    # -- 2. it is not a legal target for itself ----------------------------
    g = game()
    g.graveyard[:] = []
    g.hand[:] = [invoke]          # the miracle path leaves it in hand
    L.invoke_calamity(g, self_card=invoke)
    check("2  Invoke Calamity cannot select itself", g.m["invoke_free_casts"], 0)
    check("2b and it is still in hand, uncast", invoke in g.hand, True)

    # -- 3. the spells it casts are EXILED, not put in the graveyard -------
    g = game()
    g.graveyard[:] = [spell("Two", 2)]
    g.hand[:] = []
    L.invoke_calamity(g, self_card=invoke)
    check("3  a spell cast this way is exiled, not recycled",
          [c.name for c in g.graveyard], [])

    # -- 4. "Exile Invoke Calamity" / "Exile Volcanic Vision" --------------
    g = game()
    g.graveyard[:] = []
    L.resolve_spell(g, invoke, paid=5)
    check("4  Invoke Calamity exiles ITSELF (not in the graveyard)",
          [c.name for c in g.graveyard], [])

    # -- 5. Volcanic Vision returns the LARGEST instant/sorcery to hand ----
    g = game()
    g.graveyard[:] = [spell("Two", 2), spell("Seven", 7), spell("Four", 4)]
    g.hand[:] = []
    L.volcanic_vision(g)
    check("5  Volcanic Vision returns the biggest spell to HAND",
          [c.name for c in g.hand], ["Seven"])
    check("5b and it leaves the graveyard",
          sorted(c.name for c in g.graveyard), ["Four", "Two"])

    # -- 6. Volcanic Vision exiles itself ----------------------------------
    g = game()
    g.graveyard[:] = []
    L.resolve_spell(g, vision, paid=7)
    check("6  Volcanic Vision exiles ITSELF", vision in g.graveyard, False)

    # -- 7. Goliath: a spell cast FROM HAND is exiled with a dream counter -
    g = game()
    g.board.append(Permanent(card=named("Goliath Daydreamer"), sick=False))
    g.graveyard[:] = []
    s = spell("Bolt", 1, "Instant")
    L.resolve_spell(g, s, paid=1, from_hand=True)
    check("7  from hand -> dream exile, NOT the graveyard",
          (len(g.dream_exile), len(g.graveyard)), (1, 0))

    # -- 8. ... and a spell NOT cast from hand still goes to the graveyard --
    g = game()
    g.board.append(Permanent(card=named("Goliath Daydreamer"), sick=False))
    g.graveyard[:] = []
    s = spell("Bolt", 1, "Instant")
    L.resolve_spell(g, s, paid=1, from_hand=False)
    check("8  NOT from hand -> the graveyard, as normal",
          (len(g.dream_exile), len(g.graveyard)), (0, 1))

    # -- 9. attacking casts one free from the dream exile ------------------
    g = game()
    g.dream_exile[:] = [spell("Big", 6), spell("Small", 1)]
    before = g.m["mv_cheated"]
    L.goliath_attack(g)
    check("9  attacking casts one dream card free, biggest first",
          (g.m["dream_free_casts"], round(g.m["mv_cheated"] - before, 2)),
          (1, 6.0))

    # -- 10-13. Rendmaw artifact recursion ---------------------------------
    rd, rc = rw_build()

    def rgame():
        return E.Game(list(rd), rc, dict(DEFAULT_CFG, turns=20),
                      __import__("random").Random(1), seed_for_pod=1)

    def art(name, mv):
        return Card(name=name, types=frozenset({"Artifact"}),
                    cost={"gen": mv})

    myr = next(c for c in rd if c.name == "Myr Retriever")
    trawler = next(c for c in rd if c.name == "Scrap Trawler")

    g = rgame()
    g.graveyard[:] = [art("Big", 5), art("Small", 1)]
    g.hand[:] = []
    g.artifact_died(myr)
    check("10 Myr Retriever returns the biggest OTHER artifact to hand",
          [c.name for c in g.hand], ["Big"])

    g = rgame()
    g.graveyard[:] = [myr]                 # only itself
    g.hand[:] = []
    g.artifact_died(myr)
    check("10b 'ANOTHER' — it cannot return itself", g.hand, [])

    g = rgame()
    g.board.append(Permanent(card=trawler, sick=False))
    g.graveyard[:] = [art("Equal", 3), art("Lesser", 2)]
    g.hand[:] = []
    g.artifact_died(art("Dead", 3))
    check("11 Scrap Trawler returns LESSER mana value only, never equal",
          [c.name for c in g.hand], ["Lesser"])

    g = rgame()
    g.graveyard[:] = [art("Small", 1)]
    g.hand[:] = []
    g.artifact_died(Card(name="Not an artifact",
                         types=frozenset({"Creature"}), cost={"gen": 3}))
    check("12 a non-artifact death triggers nothing", g.hand, [])

    # BOTH triggers on one death: Myr Retriever dying with Scrap Trawler out.
    # This is the case whose stale-pool bug crashed the first implementation.
    g = rgame()
    g.board.append(Permanent(card=trawler, sick=False))
    g.graveyard[:] = [art("Big", 5), art("Tiny", 1)]
    g.hand[:] = []
    g.artifact_died(myr)                   # Myr Retriever is MV 2
    check("13 both triggers on one death take two DIFFERENT cards",
          sorted(c.name for c in g.hand), ["Big", "Tiny"])

    print()
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if MUTATE:
        return {f.split()[0] for f in FAIL}
    if FAIL:
        raise SystemExit(f"FAILED: {FAIL}")
    print("  PASS")
    return set()


# Each mutation reintroduces ONE plausible misreading of the rules text. The
# expected sets are written from the clause, before running -- CLAUDE.md's
# rule, and the one that caught a duplicated rule in §0z18.
def _cap_each():
    """The misreading this test exists for: 6 EACH instead of 6 TOTAL."""
    orig = L.invoke_calamity
    def patched(g, self_card=None):
        cfg = g.cfg
        g.cfg = dict(cfg, invoke_mv_cap=99)      # no total cap at all
        try:
            orig(g, self_card=self_card)
        finally:
            g.cfg = cfg
    L.invoke_calamity = patched


def _may_target_self():
    orig = L.invoke_calamity
    L.invoke_calamity = lambda g, self_card=None: orig(g, self_card=None)


def _no_self_exile():
    L.SELF_EXILING = set()


def _goliath_off():
    L.LoreholdGame.has = (lambda self, name:
                          False if name == "Goliath Daydreamer"
                          else L._HAS(self, name))


def _trawler_allows_equal():
    """<= instead of <, the loop the LESSER clause exists to prevent."""
    orig = E.Game.artifact_died
    def patched(self, dead):
        real_mv = type(dead).mv
        orig(self, dead)
    # simpler: patch by widening the comparison through a stand-in card
    E.Game.artifact_died = _equal_variant


def _equal_variant(self, dead):
    if "Artifact" not in dead.types:
        return
    def take(pred, tag):
        pool = [c for c in self.graveyard
                if "Artifact" in c.types and c is not dead and pred(c)]
        if not pool:
            return
        best = max(pool, key=lambda c: c.mv)
        self.graveyard.remove(best)
        self.hand.append(best)
    if dead.name in ("Myr Retriever", "Junk Diver"):
        take(lambda c: True, "r")
    if dead.name == "Scrap Trawler" or self.has("Scrap Trawler"):
        take(lambda c: c.mv <= dead.mv, "t")       # <= is the mutation


def _artifact_recursion_off():
    E.Game.artifact_died = lambda self, dead: None


MUTATIONS = [
    ("rendmaw: Trawler allows EQUAL mana value", _trawler_allows_equal,
     {"11"}),
    ("rendmaw: artifact recursion off", _artifact_recursion_off,
     {"10", "11", "13"}),
    ("Invoke: cap applied per card, not to the total", _cap_each,
     {"1"}),
    ("Invoke: may target itself", _may_target_self,
     {"2", "2b"}),
    ("neither spell exiles itself", _no_self_exile,
     {"4", "6"}),
    # Case 8 asserts the ABSENCE of dream-exiling and stays true with Goliath
    # gone, so it must NOT fail -- the §0z18 lesson, applied in advance.
    ("Goliath not on the battlefield", _goliath_off,
     {"7"}),
]


def run_mutations():
    import copy
    saved = (L.invoke_calamity, set(L.SELF_EXILING), L.LoreholdGame.has)
    saved_art = E.Game.artifact_died
    L._HAS = L.LoreholdGame.has
    ok = True
    for label, patch, want in MUTATIONS:
        L.invoke_calamity, L.SELF_EXILING, L.LoreholdGame.has = \
            saved[0], set(saved[1]), saved[2]
        E.Game.artifact_died = saved_art
        PASS.clear(); FAIL.clear()
        patch()
        print(f"=== MUTATION: {label}")
        print(f"    expected to fail: {sorted(want)}")
        got = main()
        if got == want:
            print(f"    OK - exactly {sorted(want)} failed")
        else:
            ok = False
            print(f"    !!! UNEXPECTED - got {sorted(got)}")
    L.invoke_calamity, L.SELF_EXILING, L.LoreholdGame.has = \
        saved[0], set(saved[1]), saved[2]
    E.Game.artifact_died = saved_art
    if not ok:
        raise SystemExit("FAIL: a mutation did not behave as specified.")
    print("PASS - every clause is independently pinned.")


if __name__ == "__main__":
    if MUTATE:
        run_mutations()
    else:
        main()
