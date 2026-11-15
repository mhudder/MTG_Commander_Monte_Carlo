#!/usr/bin/env python3
"""§0z210: Genesis Wave reveals the top X and keeps the permanents among
them, by its text, where it used to tutor the whole library.

    python -m tests.test_genesis_wave
    python -m tests.test_genesis_wave --mutate   # 3 mutations, exact sets

    "Reveal the top X cards of your library. You may put any number of
    permanent cards with mana value X or less from among them onto the
    battlefield. Then put all cards revealed this way that weren't put onto
    the battlefield into your graveyard."

The old rule (`genesis_wave_reveal=False`) took the three highest-mana-value
permanents of mana value 6 or less from ANYWHERE in the library (§0z209,
`docs/ORACLE_AUDIT_AZUSA.md` item 1). The new rule, the default, reveals the
top six at the project's fixed X (`x_pips=6`), puts EVERY permanent of mana
value 6 or less among them onto the battlefield (the "may" is a policy: all
of them), and mills the rest. The permanents enter together, so each
permanent that enters with a land sees that land's landfall (CR 603.6a).

Each case builds a game with an empty battlefield and stacks the library's
top by hand. The library's top is its END (`library.pop()` draws).

CASES -- the top six, top first: Forest, Rampaging Baloths (mv 6), Harmonize
(a sorcery), Craterhoof Behemoth (mv 8), Sol Ring, Forest; Ancient
Greenwarden (mv 6) is the seventh card.
  A  the four permanents of mana value 6 or less enter; Greenwarden does not
  B  Harmonize, Craterhoof and the Wave itself are in the graveyard; the
     library is six cards shorter
  C  each land put fires landfall: `landfall_triggers` +2
  D  603.6a: Baloths, entering with the two lands, sees both -- two Beasts
  E  the counters: `wave_revealed` 6, `wave_put` 4, `wave_milled` 2
  F  a three-card library (Forest, Harmonize, Sol Ring): three revealed,
     the library empty, Harmonize milled, no crash
  G  NEIGHBOUR: `genesis_wave_reveal=False` is the old rule: three
     permanents, every one mana value 6, nothing milled, the library three
     shorter
  H  NEIGHBOUR: Animist's Awakening still takes four lands (its own fix,
     item 47's next, is not this one)
  I  the pilot's decking guard reads the reveal as six cards out of the
     library (`draws_on_resolve` 6, so `draw_is_safe` holds the Wave back
     below 11 cards); under the old rule, 0, as it was

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  genesis_wave_reveal=False everywhere          -> A, B, C, D, E, F, I
  wave_enter fires each land's landfall as it enters, in reveal order
                                                 -> D
  wave_keeps reads mana value < X               -> A, B, D, E

UNMUTATED (§0z15): G and H are the neighbours (I's second half is the
switch's too) -- the switch and the
lands-only branch that shares `wave`. C is reached by the switch alone: the
interleaving still fires both lands, and the mana-value edge moves no land.
F holds Sol Ring and a Forest, neither near the edge, and no landfall payoff.
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
    """The named card, out of the hand or the library: a DISTINCT object
    per call, so two Forests are two cards (§0z112)."""
    for zone in (g.library, g.hand):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def stack(g, top_first, below=()):
    """Put `below` (top first) under `top_first` on top of the library."""
    cards = [take(g, n) for n in top_first]
    under = [take(g, n) for n in below]
    g.library.extend(reversed(under))
    g.library.extend(reversed(cards))


TOP6 = ["Forest", "Rampaging Baloths", "Harmonize", "Craterhoof Behemoth",
        "Sol Ring", "Forest"]


def beasts(g):
    return sum(1 for p in g.board if p.is_token and "Beast" in p.card.name)


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = fresh()
    wave = take(g, "Genesis Wave")
    stack(g, TOP6, below=["Ancient Greenwarden"])
    lib, lf = len(g.library), g.m["landfall_triggers"]
    g.resolve(wave)
    check("A the four permanents of mana value <= 6 enter, not the seventh",
          sorted(p.card.name for p in g.board if not p.is_token),
          sorted(["Forest", "Forest", "Rampaging Baloths", "Sol Ring"]))
    check("B the rest and the Wave milled; the library six shorter",
          (sorted(c.name for c in g.graveyard), lib - len(g.library)),
          (sorted(["Craterhoof Behemoth", "Genesis Wave", "Harmonize"]), 6))
    check("C each land put fires landfall",
          g.m["landfall_triggers"] - lf, 2)
    check("D 603.6a: Baloths sees both lands it entered with", beasts(g), 2)
    check("E the counters",
          (g.m["wave_revealed"], g.m["wave_put"], g.m["wave_milled"]),
          (6, 4, 2))

    g = fresh()
    wave = take(g, "Genesis Wave")
    keep = [take(g, n) for n in ("Sol Ring", "Harmonize", "Forest")]
    g.library[:] = keep                       # top is the end: Forest
    g.resolve(wave)
    check("F a three-card library: three revealed, Harmonize milled",
          (len(g.library), sorted(p.card.name for p in g.board),
           sorted(c.name for c in g.graveyard)),
          (0, ["Forest", "Sol Ring"], ["Genesis Wave", "Harmonize"]))

    g = fresh(genesis_wave_reveal=False)
    wave = take(g, "Genesis Wave")
    stack(g, TOP6, below=["Ancient Greenwarden"])
    lib = len(g.library)
    g.resolve(wave)
    check("G genesis_wave_reveal=False: three mana-value-6 permanents",
          (len(g.board) - beasts(g),
           all(p.card.mv == 6 for p in g.board if not p.is_token),
           sorted(c.name for c in g.graveyard), lib - len(g.library)),
          (3, True, ["Genesis Wave"], 3))

    g = fresh()
    awaken = take(g, "Animist's Awakening")
    g.resolve(awaken)
    check("H Animist's Awakening still takes four lands",
          sum(1 for p in g.board if p.card.is_land), 4)

    g = fresh()
    wave = next(c for c in DECK if c.name == "Genesis Wave")
    old = fresh(genesis_wave_reveal=False)
    check("I the decking guard reads the reveal; the old rule unguarded",
          (g.draws_on_resolve(wave), old.draws_on_resolve(wave)),
          (6, 0))
    return set(FAIL)


def _interleaved(self, cards):
    for c in cards:
        self.make_permanent(c, sick=not c.haste, tapped=bool(c.tapped))
        if c.is_land:
            self.land_entered(c, played=False)


def _strict(card, x):
    return card.is_permanent and card.mv < x


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z210: Genesis Wave reveals the top X\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "genesis_wave_reveal=False everywhere":
            ({"A", "B", "C", "D", "E", "F", "I"}, {},
             {"genesis_wave_reveal": False}),
        "wave_enter interleaves landfall, in reveal order":
            ({"D"}, {"wave_enter": _interleaved}, {}),
        "wave_keeps reads mana value < X":
            ({"A", "B", "D", "E"}, {"keeps": _strict}, {}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real_enter, real_keeps = AzusaGame.wave_enter, AZ.wave_keeps
        if "wave_enter" in patch:
            AzusaGame.wave_enter = patch["wave_enter"]
        if "keeps" in patch:
            AZ.wave_keeps = patch["keeps"]
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            AzusaGame.wave_enter, AZ.wave_keeps = real_enter, real_keeps
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
