#!/usr/bin/env python3
"""§0z212: a creature put onto the battlefield by a tutor or Genesis Wave
fires its ETB, after the spell that put it there has finished.

    python -m tests.test_tutored_etb
    python -m tests.test_tutored_etb --mutate   # 4 mutations, exact sets

§0z209 item 3: `AzusaGame.etb` was split out of `resolve` so that every
way a creature enters could fire it, and only `resolve` and Springheart's
copy called it. `tutor_creature` (Green Sun's Zenith, Chord of Calling,
Finale of Devastation, Woodland Bellower) and `wave_enter` (Genesis Wave)
put the creature in with `make_permanent` and nothing else.

Now each queues the ETB (`queue_etb`) and `resolve` fires the queue once
the spell has left the stack -- the Chord, Finale or Wave in the graveyard,
Green Sun's Zenith shuffled away -- because a triggered ability resolves
after the spell that caused it (CR 603.3): a Witness tutored by Chord can
return the Chord. Outside a resolution (Bellower's ETB tutoring from its
own trigger) the queue is fired by the same loop. The Wave's ETBs come
after its lands' landfall: a Zabu made by a Waved Ka-Zar did not exist
when the lands entered. `tutor_etb=False` is the old rule exactly.

CASES
  A  Green Sun's Zenith fetches Eternal Witness (the only creature of mana
     value 3 or less): Witness returns Harmonize, the graveyard's best
  B  Chord of Calling fetches Witness: Witness returns the CHORD (mana value
     7 here), which is in the graveyard by the time the ETB resolves
  C  Finale fetches Woodland Bellower (6), whose ETB fetches Witness, whose
     ETB returns the Finale: the chain
  D  Genesis Wave puts Ka-Zar in with two Forests: Zabu is made, with no
     counters -- the lands entered before it existed
  E  Genesis Wave puts Witness in: Witness returns the Wave itself (9)
  F  NEIGHBOUR: `tutor_etb=False`: Chord's Witness fires nothing
  G  NEIGHBOUR: Witness CAST from hand still returns the graveyard's best
  H  `tutor_etbs` counts the ETBs this rule fired: A's game, 1
  I  Chord fetches Springheart Nantuko with a Scute Swarm on the board: it
     enters as a creature, NOT bestowed -- bestow is paid by casting

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  tutor_etb=False everywhere                     -> A, B, C, D, E, H
  queue_etb fires at once (no deferral)          -> B, C, E
  wave_enter fires its ETBs before the landfall  -> D, E
  queue_etb's ETB read as a cast (cast=True)     -> I

UNMUTATED (§0z15): F and G are the neighbours, the switch and the cast
path. A is reached by the switch alone: Green Sun's Zenith shuffles itself
into the library, so whether its Witness fires during or after the spell,
the graveyard holds the same cards.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
from edhmc.azusa import AzusaGame
from edhmc.decks.azusa_v1 import FINALE_OF_DEVASTATION
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
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def setup(spell, library, graveyard=(), **cfg):
    """A game holding `spell`, with exactly `library` (BOTTOM first) as its
    library and `graveyard` in its graveyard; the hand emptied, so what
    returns to it is what an ETB put there."""
    g = fresh(**cfg)
    # Finale is not in the staged list: the deck module's own Card
    s = (FINALE_OF_DEVASTATION if spell == "Finale of Devastation"
         else take(g, spell))
    lib = [take(g, n) for n in library]
    gy = [take(g, n) for n in graveyard]
    g.library[:] = lib
    g.graveyard[:] = gy
    g.hand[:] = []
    return g, s


def names(zone):
    return sorted(getattr(x, "card", x).name for x in zone
                  if not getattr(x, "is_token", False))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, s = setup("Green Sun's Zenith", ["Sol Ring", "Eternal Witness"],
                 graveyard=["Harmonize"])
    g.resolve(s)
    check("A Zenith's Witness returns Harmonize",
          (names(g.board), names(g.hand)),
          (["Eternal Witness"], ["Harmonize"]))
    check("H tutor_etbs counts the ETB fired", g.m["tutor_etbs"], 1)

    g, s = setup("Chord of Calling", ["Sol Ring", "Eternal Witness"],
                 graveyard=["Harmonize"])
    g.resolve(s)
    check("B Chord's Witness returns the Chord",
          (names(g.board), names(g.hand), names(g.graveyard)),
          (["Eternal Witness"], ["Chord of Calling"], ["Harmonize"]))

    g, s = setup("Finale of Devastation",
                 ["Sol Ring", "Eternal Witness", "Woodland Bellower"],
                 graveyard=["Harmonize"])
    g.resolve(s)
    check("C Finale -> Bellower -> Witness -> the Finale",
          (names(g.board), names(g.hand)),
          (["Eternal Witness", "Woodland Bellower"],
           ["Finale of Devastation"]))

    g, s = setup("Genesis Wave",
                 ["Cultivate", "Sol Ring", "Harmonize", "Forest",
                  "Ka-Zar of the Savage Land", "Forest"])
    g.resolve(s)
    zabu = [p for p in g.board if p.card.name == "Zabu"]
    check("D a Waved Ka-Zar's Zabu does not see the Wave's lands",
          [p.counters for p in zabu], [0])

    g, s = setup("Genesis Wave",
                 ["Cultivate", "Forest", "Harmonize", "Sol Ring", "Forest",
                  "Eternal Witness"])
    g.resolve(s)
    check("E a Waved Witness returns the Wave", names(g.hand),
          ["Genesis Wave"])

    g, s = setup("Chord of Calling", ["Sol Ring", "Eternal Witness"],
                 graveyard=["Harmonize"], tutor_etb=False)
    g.resolve(s)
    check("F tutor_etb=False: the Witness fires nothing",
          (names(g.hand), names(g.graveyard)),
          ([], ["Chord of Calling", "Harmonize"]))

    g, s = setup("Eternal Witness", ["Sol Ring"],
                 graveyard=["Harmonize", "Cultivate"])
    g.resolve(s)
    check("G a cast Witness returns the graveyard's best", names(g.hand),
          ["Harmonize"])

    g, s = setup("Chord of Calling", ["Sol Ring", "Springheart Nantuko"],
                 graveyard=["Scute Swarm"])
    swarm = take(g, "Scute Swarm")        # Chord searches the library only
    g.board.append(EN.Permanent(card=swarm, sick=False))
    g.resolve(s)
    check("I a tutored Springheart is not bestowed",
          (g.springheart_host, g.m["springheart_bestowed"],
           "Springheart Nantuko" in names(g.board)),
          (None, 0, True))
    return set(FAIL)


def _as_cast(self, card, perm):
    self.m["tutor_etbs"] += 1
    if self._resolving:
        self._etb_queue.append((card, perm))
    else:
        self.etb(card, perm)


def _flush_as_cast(self):
    while self._etb_queue:
        card, perm = self._etb_queue.pop(0)
        self.etb(card, perm)


def _at_once(self, card, perm):
    """The timing alone: still not a cast (it copied the pre-`cast` call
    first, and broke I too -- §0z141's stand-in that copies a signature)."""
    self.m["tutor_etbs"] += 1
    self.etb(card, perm, cast=False)


def _etb_first(self, cards):
    perms = [(c, self.make_permanent(c, sick=not c.haste,
                                     tapped=bool(c.tapped))) for c in cards]
    for c, p in perms:
        if not c.is_land:
            self.etb(c, p)
    for c in cards:
        if c.is_land:
            self.land_entered(c, played=False)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z212: a tutored or Waved creature fires its ETB\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "tutor_etb=False everywhere":
            ({"A", "B", "C", "D", "E", "H"}, {}, {"tutor_etb": False}),
        "queue_etb fires at once":
            ({"B", "C", "E"}, {"queue_etb": _at_once}, {}),
        "wave_enter fires its ETBs before the landfall":
            ({"D", "E"}, {"wave_enter": _etb_first}, {}),
        "queue_etb's ETB read as a cast":
            ({"I"}, {"queue_etb": _as_cast, "flush_etbs": _flush_as_cast}, {}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        real = {k: getattr(AzusaGame, k) for k in patch}
        for k, fn in patch.items():
            setattr(AzusaGame, k, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for k, fn in real.items():
                setattr(AzusaGame, k, fn)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
