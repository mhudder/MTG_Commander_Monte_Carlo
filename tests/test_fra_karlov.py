#!/usr/bin/env python3
"""Pin the two Reality Fracture cards imported into karlov on 2026-09-20.

    python -m tests.test_fra_karlov
    python -m tests.test_fra_karlov --mutate   # 3 mutations, exact sets

PREVIEW TEXT. Reality Fracture releases 2026-10-02; this was fetched from
Scryfall on 2026-09-20 and can change before release.

BOTH CARDS TURN ON THE WORD "ANOTHER", and that word is where this deck has
already been wrong once: until 2026-09-05 five of its six enters-triggers
ignored it and each gained a phantom life per game (`another_creature_clause`
exists to reproduce the old tables). So each card is checked BOTH ways --
that it triggers for another permanent, and that it does NOT trigger for
itself.

WHAT MATTERS ABOUT THESE TWO IS THE EVENT, NOT THE LIFE. Karlov's counters,
Exemplar of Light, Voice of the Blessed and Vito all read the lifegain EVENT,
so a check that only asserted `life_gained` would pass against an engine that
gained 1 life without ever firing a trigger. Every case below reads the
trigger counter AND the payoff counter.

CASES
  A  Liliana gains 1 life when another creature enters
  B  Liliana does NOT trigger off herself entering
  C  Liliana's trigger is a lifegain EVENT (Karlov's counter moves)
  D  Edgar gains 1 life when another creature dies
  E  Edgar does NOT trigger off his own death
  F  a wipe that kills several creatures triggers Edgar once per death

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the "another" clause is switched off   -> B and E
  Liliana's trigger is removed           -> A, B and C
  Edgar's trigger is removed             -> D, E and F

B and E assert a NON-event, so each also carries the positive half in the same
tuple -- otherwise removing the trigger entirely would make them pass. That is
why "Liliana's trigger is removed" breaks B as well as A.

AND EDGAR'S SELF-EXCLUSION IS ENFORCED TWICE. `opponents.destroy` removes the
permanent from the board before calling `on_creature_death`, so `has()` is
already False when Edgar himself dies -- the card's own "another" is a second
guard on top of an ordering in shared code. The first version of mutation 1
defeated only the card's guard and broke nothing; it now defeats both, and
`_no_another` records why. If that ordering ever changes, this is the check
that notices.
"""
import sys

from edhmc.karlov import KarlovGame
import edhmc.karlov as KV
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import karlov_v2 as M
from edhmc.engine import Card, Permanent
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
    return KarlovGame(deck, cmd, dict(DEFAULT_CFG, turns=20), 1234)


def body(name="Bear"):
    return Card(name=name, types=frozenset({"Creature"}), power=2, toughness=2)


def put(g, card):
    """Put a permanent on the battlefield the way `karlov.resolve` does.

    This engine has no `make_permanent` -- `resolve()` appends a Permanent and
    calls `creature_entered` itself, so a test that invented its own entry path
    would be testing a path the game never takes.
    """
    perm = Permanent(card=card, sick=False)
    g.board.append(perm)
    if KV.is_creature_now(g, card):
        KV.creature_entered(g, mine=True, entering=perm)
    return perm


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A: another creature enters --------------------------------------
    g = fresh()
    put(g, M.LILIANA_THE_FAULTLESS)
    life, trig = g.your_life, g.m["liliana_triggers"]
    put(g, body())
    check("A Liliana gains 1 life when another creature enters",
          (g.m["liliana_triggers"] - trig, g.your_life - life), (1, 1))

    # ---- B: not off herself ----------------------------------------------
    g = fresh()
    trig = g.m["liliana_triggers"]
    put(g, M.LILIANA_THE_FAULTLESS)
    self_only = g.m["liliana_triggers"] - trig
    put(g, body())          # the positive half
    check("B Liliana does not trigger off herself, and does off another",
          (self_only, g.m["liliana_triggers"] - trig), (0, 1))

    # ---- C: it is a lifegain EVENT ---------------------------------------
    g = fresh()
    put(g, M.LILIANA_THE_FAULTLESS)
    # KARLOV'S COUNTERS KEY ON `commander_cast`, A FLAG -- not on a permanent
    # being on the battlefield. A first version of this case put him on the
    # board and asserted the counters moved; they did not, and the card was
    # briefly the suspect. Setting the flag is what "he is in play" means to
    # `gain_life`, and the distinction is worth pinning because every payoff
    # in this deck reads that function.
    put(g, M.build()[1])
    g.commander_cast = True
    counters, events = g.m["karlov_counters"], g.m["lifegain_triggers"]
    put(g, body("Another Bear"))
    check("C Liliana's life is an EVENT the payoffs count",
          (g.m["lifegain_triggers"] - events > 0,
           g.m["karlov_counters"] - counters > 0), (True, True))

    # ---- D: another creature dies ----------------------------------------
    g = fresh()
    put(g, M.EDGAR_ANCIENT_BLOODLORD)
    put(g, body())
    victim = next(p for p in g.board if p.card.name == "Bear")
    life, trig = g.your_life, g.m["edgar_triggers"]
    OPP.destroy(g, victim, destroys=False)
    check("D Edgar gains 1 life when another creature dies",
          (g.m["edgar_triggers"] - trig, g.your_life - life), (1, 1))

    # ---- E: not off his own death ----------------------------------------
    g = fresh()
    put(g, M.EDGAR_ANCIENT_BLOODLORD)
    put(g, body())
    edgar = next(p for p in g.board
                 if p.card.name == "Edgar, Ancient Bloodlord")
    trig = g.m["edgar_triggers"]
    OPP.destroy(g, edgar, destroys=False)
    self_only = g.m["edgar_triggers"] - trig
    # and with Edgar gone, a later death must not trigger either
    g2 = fresh()
    put(g2, M.EDGAR_ANCIENT_BLOODLORD)
    put(g2, body())
    OPP.destroy(g2, next(p for p in g2.board if p.card.name == "Bear"),
                destroys=False)
    check("E Edgar does not trigger off his own death, but does off another's",
          (self_only, g2.m["edgar_triggers"]), (0, 1))

    # ---- F: once per death in a wipe --------------------------------------
    g = fresh()
    put(g, M.EDGAR_ANCIENT_BLOODLORD)
    for i in range(3):
        put(g, body(f"Bear {i}"))
    trig = g.m["edgar_triggers"]
    for i in range(3):
        OPP.destroy(g, next(p for p in g.board if p.card.name == f"Bear {i}"),
                    destroys=False)
    check("F three deaths are three Edgar triggers",
          g.m["edgar_triggers"] - trig, 3)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Reality Fracture in karlov -- Liliana the Faultless, Edgar\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_entered = KV.creature_entered
    real_death = KV.KarlovGame.on_creature_death
    real_gain = KV.gain_life
    expected = {
        'the "another" clause is switched off': {"B", "E"},
        "Liliana's trigger is removed": {"A", "B", "C"},
        "Edgar's trigger is removed": {"D", "E", "F"},
    }
    bad = 0
    for label in expected:
        print(f"-- {label}")
        if label == 'the "another" clause is switched off':
            # `others()` reads cfg["another_creature_clause"] for the ETB half;
            # Edgar's death half excludes by NAME, so the mutation has to turn
            # off both spellings of the same word to model one defect.
            KV.creature_entered = lambda g, mine=True, entering=None: (
                real_entered(g, mine=mine, entering=None))
            KV.KarlovGame.on_creature_death = _no_another(real_death)
        elif label == "Liliana's trigger is removed":
            KV.creature_entered = _without(real_entered,
                                           "Liliana the Faultless")
        else:
            KV.KarlovGame.on_creature_death = _edgarless(real_death)
        try:
            broke = run_cases()
        finally:
            KV.creature_entered = real_entered
            KV.KarlovGame.on_creature_death = real_death
            KV.gain_life = real_gain
        ok = broke == expected[label]
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(expected[label])}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(expected) - bad} passed, {bad} failed "
          f"({len(expected)} mutations, exact sets)")
    return 1 if bad else 0


def _hidden(g, name):
    """Take every permanent of that name off the board for one call."""
    keep = [p for p in g.board if p.card.name == name]
    for p in keep:
        g.board.remove(p)
    return keep


def _without(real_entered, name):
    def patched(g, mine=True, entering=None):
        keep = _hidden(g, name)
        try:
            return real_entered(g, mine=mine, entering=entering)
        finally:
            g.board.extend(keep)
    return patched


def _edgarless(real_death):
    def patched(self, n=1, perm=None):
        keep = _hidden(self, "Edgar, Ancient Bloodlord")
        try:
            return real_death(self, n, perm)
        finally:
            self.board.extend(keep)
    return patched


def _no_another(real_death):
    """Edgar triggers off his OWN death too -- the clause ignored.

    THE FIRST VERSION OF THIS MUTATION CHANGED NOTHING, and finding out why is
    the most useful thing this file learned. It nulled `perm` so the name check
    could not exclude Edgar, and case E still passed -- because
    `opponents.destroy` REMOVES the permanent from the board BEFORE calling
    this hook, so `self.has("Edgar, Ancient Bloodlord")` is already False by
    the time the trigger is considered. The self-exclusion is enforced TWICE,
    once by the card's own word and once by an ordering in shared code that
    says nothing about this card.

    So the mutation has to defeat both guards to model one defect: put Edgar
    back on the board AND null the perm. If `destroy`'s ordering ever changes,
    the name check in karlov.py is the only thing left standing, and this
    mutation is what would notice.
    """
    def patched(self, n=1, perm=None):
        back = None
        if perm is not None and perm.card.name == "Edgar, Ancient Bloodlord":
            back, perm = perm, None
            self.board.append(back)
        try:
            return real_death(self, n, perm)
        finally:
            if back is not None and back in self.board:
                self.board.remove(back)
    return patched


if __name__ == "__main__":
    sys.exit(main())
