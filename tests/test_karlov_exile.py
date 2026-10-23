#!/usr/bin/env python3
"""Pin Karlov's own "{W}{B}, Remove six +1/+1 counters: Exile target
creature." -- queue item 5's last karlov line, the owner's policy (§0z155).

    python -m tests.test_karlov_exile
    python -m tests.test_karlov_exile --mutate   # 3 mutations, exact sets

On the default pod (POD_V4). Every case calls `karlov.karlov_exile_step` as
`take_turn` does, after the pod's round has opened (`pod_round_of`).

CASES
  A  twelve counters, {W}{B} untapped, a creature route piece out: one
     exile -- six counters and six power gone, the piece off the battlefield
  B  eighteen counters, {W}{B} twice, three creature pieces: two exiles,
     the mana is what runs out
  C  only an artifact piece is out: no activation
  D  {W}{W} untapped, no {B}: no activation
  E  `karlov_exile_keep=6` with eleven counters: no activation
  F  a piece that landed THIS round is out at the end of it, and exiled
  G  Karlov is not on the battlefield: no activation

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  karlov_exile=False                    -> A, B, F
  karlov_exile_keep=0 (over E's 6)      -> E
  end_step_target -> answer_target      -> F   (the end-of-round read is
                                                what makes F's piece "out")

UNMUTATED (§0z15): C, D and G are negative controls -- the reach's type,
the colour of the mana, the commander's presence. No switch reaches them;
they would catch an activation that ignored all three.
"""
import sys

import edhmc.karlov as KA
import edhmc.opponents as OPP
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
card, lands, fresh, perm = B.card, B.lands, B.fresh, B.perm
KARLOV = B.LISTS["karlov"][1]
CREATURE = OPP.ThreatPiece("Creature", 3, 3, 1)
ARTIFACT = OPP.ThreatPiece("Artifact", 0, 3, 1)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(mana, counters, pieces=(CREATURE,), lands_at=0, karlov=True, **kw):
    g = fresh("karlov", board=lands("karlov", *mana)
              + ([KARLOV] if karlov else []), **kw)
    g.commander_cast = karlov
    g.karlov_counters = counters
    g.pod_round_of = g.turn            # the end of the pod's round
    o = g.opponents[0]
    o.pieces = tuple(pieces)
    o.piece_lands = [lands_at] * len(pieces)
    return g, o


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, o = game(("Plains", "Swamp"), 12)
    power = g.power_of(perm(g, KARLOV.name))
    n = KA.karlov_exile_step(g)
    check("A one exile: six counters, six power, the piece gone",
          (n, g.karlov_counters, power - g.power_of(perm(g, KARLOV.name)),
           OPP.end_step_target(g, KA.KARLOV_EXILE)),
          (1, 6, 6, None))

    g, o = game(("Plains", "Swamp", "Plains", "Swamp"), 18,
                pieces=(CREATURE,) * 3)
    check("B two exiles: the mana runs out first",
          (KA.karlov_exile_step(g), g.karlov_counters, g.m["karlov_exiles"]),
          (2, 6, 2))

    g, o = game(("Plains", "Swamp"), 12, pieces=(ARTIFACT,))
    check("C an artifact piece is no target", KA.karlov_exile_step(g), 0)

    g, o = game(("Plains", "Plains"), 12)
    check("D no {B}, no activation",
          (KA.karlov_exile_step(g), g.karlov_counters), (0, 12))

    g, o = game(("Plains", "Swamp"), 11, karlov_exile_keep=6)
    check("E a reserve of six keeps eleven counters",
          (KA.karlov_exile_step(g), g.karlov_counters), (0, 11))

    g, o = game(("Plains", "Swamp"), 6, lands_at=7)
    check("F a piece that landed this round is exiled at its end",
          (KA.karlov_exile_step(g), g.karlov_counters), (1, 0))

    g, o = game(("Plains", "Swamp"), 12, karlov=False)
    check("G Karlov off the battlefield", KA.karlov_exile_step(g), 0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Karlov's six-counter exile (§0z155)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    real = OPP.end_step_target

    def answer_target(g, reach):       # the same signature (§0z141)
        return OPP.answer_target(g, reach)

    mutations = [
        ({"karlov_exile": False}, None, {"A", "B", "F"}),
        ({"karlov_exile_keep": 0}, None, {"E"}),
        ({}, answer_target, {"F"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, stand_in, want in mutations:
        B.CFG.update(over)
        if stand_in is not None:
            OPP.end_step_target = stand_in
        try:
            broke = run_cases()
        finally:
            B.CFG.clear()
            OPP.end_step_target = real
        ok = broke == want
        bad += not ok
        name = over or {"end_step_target": stand_in.__name__}
        print(f"   {name}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
