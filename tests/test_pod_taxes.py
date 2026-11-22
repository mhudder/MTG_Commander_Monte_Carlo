#!/usr/bin/env python3
"""§0z246 (queue item 52, part A): your tax cards read the pod's mana.

    python -m tests.test_pod_taxes
    python -m tests.test_pod_taxes --mutate   # 4 mutations, exact sets

Rhystic Study ("whenever an opponent casts a spell, you may draw a card
unless that player pays {1}"), Smothering Tithe ("whenever an opponent
draws a card, that player may pay {2}; if the player doesn't, you create a
Treasure"), Monologue Tax ("whenever an opponent casts their second spell
each turn, you create a Treasure") and Mind's Eye ("whenever an opponent
draws a card, you may pay {1}; if you do, draw a card"). THE PAYMENT RULE
(the owner, 2026-11-22): an opponent pays only from what it has LEFT OVER
after its turn's spending and the mana it keeps up for yours
(`opponents.pod_spare`).

Each case drives `opponents.pod_cast` / `settle_pod_taxes` (or the engine
function that reads them) on a tivit game with `pod_mana` on, opponent 0
holding the mana the case names and no counterspell left unless it says.

CASES
  A  Rhystic, opponent 0's OWN turn, two spells, 1 left over at its end
     step: it pays for one; you are owed one draw
  B  Rhystic on YOUR turn: with nothing left over you are owed the draw at
     once (B1); with 3 left over it pays, and has 2 (B2)
  C  the mana it keeps up is not left over: a counterspell left (its cost,
     2, kept up) and 2 untapped -- it cannot pay, you are owed the draw
  D  Tithe at its end step: 3 left over pays the {2} and has 1 (D1); 1
     left over does not, you are owed a Treasure (D2); Tithe and one
     Rhystic trigger on 2 left over -- Tithe's draw step comes first, so
     Tithe is paid and the Rhystic trigger is not (D3)
  E  Monologue Tax: the second spell of a turn owes a Treasure, the third
     does not; a second spell on a NEW turn owes another
  F  `engine.tithe_treasures` hands over what is owed, then nothing
  G  the switches off are the flat rates: Tithe one a living opponent (3),
     Monologue Tax `monologue_tax_rate` (2)
  H  Mind's Eye, azusa, at an opponent's upkeep: an untapped Forest pays
     {1} and you draw (H1); everything tapped, no draw (H2)
  J  a TAX is not a spell: `pod_spend(..., "tax")` triggers no Rhystic
     Study, `pod_spend(..., "spot")` does

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  nobody ever pays (TAXES_SETTLED False)          -> A, B2, D1, D3
  the kept-up mana counts as left over
    (pod_spare is mana_left alone)                -> C
  a tax counts as a spell (POD_SPELL_KINDS + tax)  -> J
  what is owed is never cleared (take_owed keeps it) -> F

UNMUTATED (§0z15): B1, D2, E, G and H; E and H are their own rules (the
second-spell count, your own mana), G the old rates, B1 and D2 cases where
nothing is paid under every rule here.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as O
import edhmc.tivit as TI
from edhmc.decks import azusa_v1 as AV, lorehold_v17 as LV, tivit_v1 as TV
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def card(module, name):
    return next(c for c in module.build()[0] if c.name == name)


def game(*names, mana=0.0, seat=None, **cfg):
    deck, cmd = TV.build()
    g = TI.TivitGame(list(deck), cmd,
                     {**DEFAULT_CFG, "pod_mana": True, **cfg}, 1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 6
    g.pod_seat = seat
    for o in g.opponents:
        o.mana_left, o.counters_left = mana, 0
        o.held_rolls = None
    for n in names:
        mod = LV if n == "Smothering Tithe" else TV
        g.board.append(EN.Permanent(card(mod, n), sick=False))
    return g, g.opponents[0]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game("Rhystic Study", mana=1.0, seat=0)
    O.pod_cast(g, o, "body")
    O.pod_cast(g, o, "piece")
    O.settle_pod_taxes(g, 0)
    check("A own turn: two spells, 1 left over -- one paid, one owed",
          (g.m["rhystic_paid"], O.pod_owed(g)["rhystic"], o.mana_left),
          (1, 1, 0.0))

    g, o = game("Rhystic Study", mana=0.0)
    O.pod_cast(g, o, "counter")
    check("B1 your turn, nothing left over: owed at once",
          O.pod_owed(g)["rhystic"], 1)
    g, o = game("Rhystic Study", mana=3.0)
    O.pod_cast(g, o, "counter")
    check("B2 your turn, 3 left over: paid, 2 left",
          (O.pod_owed(g)["rhystic"], o.mana_left), (0, 2.0))

    g, o = game("Rhystic Study", mana=2.0)
    o.counters_left = 1
    O.pod_cast(g, o, "spot")
    check("C a counterspell's cost kept up is not left over: owed",
          (O.pod_owed(g)["rhystic"], o.mana_left), (1, 2.0))

    g, o = game("Smothering Tithe", mana=3.0, seat=0)
    O.settle_pod_taxes(g, 0)
    check("D1 Tithe, 3 left over: pays {2}, 1 left",
          (O.pod_owed(g)["tithe"], o.mana_left), (0, 1.0))
    g, o = game("Smothering Tithe", mana=1.0, seat=0)
    O.settle_pod_taxes(g, 0)
    check("D2 Tithe, 1 left over: a Treasure owed",
          (O.pod_owed(g)["tithe"], o.mana_left), (1, 1.0))
    g, o = game("Smothering Tithe", "Rhystic Study", mana=2.0, seat=0)
    O.pod_cast(g, o, "body")
    O.settle_pod_taxes(g, 0)
    check("D3 Tithe's draw step first: Tithe paid, the Rhystic trigger not",
          (O.pod_owed(g)["tithe"], O.pod_owed(g)["rhystic"]), (0, 1))

    g, o = game("Monologue Tax", mana=0.0, seat=0)
    for what in ("body", "body", "spot"):
        O.pod_cast(g, o, what)
    one_turn = O.pod_owed(g)["monologue"]
    g.turn = 7
    O.pod_cast(g, o, "body")
    O.pod_cast(g, o, "piece")
    check("E the second spell each turn: one a turn, a new turn another",
          [one_turn, O.pod_owed(g)["monologue"]], [1, 2])

    g, o = game("Smothering Tithe", mana=0.0, seat=0)
    O.settle_pod_taxes(g, 0)
    O.settle_pod_taxes(g, 1)
    check("F tithe_treasures hands over what is owed, then nothing",
          [EN.tithe_treasures(g), EN.tithe_treasures(g)], [2, 0])

    g, o = game("Smothering Tithe", "Monologue Tax", tithe_from_pod=False,
                monologue_from_pod=False)
    check("G the switches off: the flat rates",
          [EN.tithe_treasures(g), EN.monologue_treasures(g)], [3, 2])

    def azusa(untapped):
        deck, cmd = AV.build()
        a = AZ.AzusaGame(list(deck), cmd, {**DEFAULT_CFG, "pod_mana": True},
                         1)
        a.board = EN.Board()
        a.hand, a.graveyard = [], []
        a.turn = 6
        a.board.append(EN.Permanent(card(AV, "Mind's Eye"), sick=False))
        a.board.append(EN.Permanent(card(AV, "Forest"), sick=False,
                                    tapped=not untapped))
        a.minds_eye(0)
        forest = next(p for p in a.board if p.card.name == "Forest")
        return len(a.hand), forest.tapped

    check("H1 Mind's Eye: the untapped Forest pays, you draw",
          azusa(True), (1, True))
    check("H2 Mind's Eye: everything tapped, no draw", azusa(False),
          (0, True))

    g, o = game("Rhystic Study", mana=5.0)
    O.pod_spend(g, o, 2.0, "tax")
    taxed = g.m["rhystic_triggers"]
    O.pod_spend(g, o, 1.0, "spot")
    check("J a tax is not a spell; a removal spell is",
          [taxed, g.m["rhystic_triggers"]], [0, 1])
    return set(FAIL)


def _keep_owed(g, kind):
    return O.pod_owed(g)[kind]


def main() -> int:
    if not MUTATE:
        print("§0z246: your tax cards read the pod's mana\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "nobody ever pays": (
            {"A", "B2", "D1", "D3"}, [("TAXES_SETTLED", False)]),
        "the kept-up mana counts as left over": (
            {"C"}, [("pod_spare", lambda g, o: o.mana_left)]),
        "a tax counts as a spell": (
            {"J"}, [("POD_SPELL_KINDS", O.POD_SPELL_KINDS | {"tax"})]),
        "what is owed is never cleared": (
            {"F"}, [("take_owed", _keep_owed)]),
    }
    bad = 0
    for label, (want, patches) in muts.items():
        print(f"-- {label}")
        saved = [(name, getattr(O, name)) for name, _ in patches]
        for name, val in patches:
            setattr(O, name, val)
        try:
            broke = run_cases()
        finally:
            for name, val in saved:
                setattr(O, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
