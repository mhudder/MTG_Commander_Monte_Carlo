#!/usr/bin/env python3
"""Time Sieve eats real artifacts, conservatively (§0z71, queued item 8c).

    python -m tests.test_sieve_real_fuel
    python -m tests.test_sieve_real_fuel --mutate   # 5 mutations, exact sets

    Time Sieve {U}{B} Artifact: {T}, Sacrifice five artifacts: Take an extra
    turn after this one.                      (Scryfall, verified 2026-09-27)

Until §0z71 only the Food/Clue/Treasure piles were fuel. The owner's two
conditions are `sieve_real_fuel`: "cap" lets a shortfall be made up from real
artifacts of mana value <= `sieve_real_mv_cap` (2), "combo" does the same only
while Tivit is on the battlefield, "never" is the old rule. Never Time Sieve,
never a creature; non-mana artifacts first, then rocks by mana made, lands
last. Disciple of the Vault and Marionette Master read a real artifact the
way they read a Treasure.

CASES
  A never: 3 Clues and three cheap rocks -- no activation, nothing eaten
  B cap: 3 Clues, Sol Ring, Azorius Signet, Lightning Greaves -- activated;
     Greaves and the Signet go, Sol Ring (two mana) stays
  C combo without Tivit on the battlefield: not activated
  D combo with Tivit: activated
  E cap: 4 Clues and Coercive Portal (MV 4) -- not activated
  F cap: 4 Clues and nothing else -- Time Sieve is not its own fuel
  G cap: 4 Clues, Ancient Den, Arcane Signet -- the Signet goes, the land stays
  H Marionette Master: 4 Clues + Sol Ring drain 4 x 5 = 20
  I Disciple of the Vault: 4 Clues + Sol Ring drain 5 (one each, 3 opponents)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  real fuel is never allowed                 -> B, D, G, H, I
  combo ignores whether Tivit is out         -> C
  the order is mana value alone              -> B, G
  Disciple does not read the sacrifice       -> I
  the mana-value cap is ignored              -> E

UNMUTATED (§0z15): A is the old rule reproduced; F is a name exclusion with
no seam of its own.
"""
import sys

from edhmc import tivit as T
from edhmc.decks import tivit_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DECK, CMD = tivit_v1.build()
BY = {c.name: c for c in DECK}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(names, clues, mode="cap", tivit=False):
    g = T.TivitGame(DECK, CMD, dict(DEFAULT_CFG, turns=20,
                                    sieve_real_fuel=mode), 1)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.board = type(g.board)()
    for n in ["Time Sieve"] + list(names):
        g.board.append(Permanent(card=BY[n], sick=False))
    if tivit:
        g.board.append(Permanent(card=CMD, sick=False))
    for k in list(g.tokens):
        g.tokens[k] = 0
    g.tokens["Clue"] = clues
    g.extra_turns = 0
    return g


def fired(g):
    T.time_sieve(g)
    return g.m["sieve_activations"]


def on_board(g, name):
    return any(p.card.name == name for p in g.board)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    rocks = ["Sol Ring", "Azorius Signet", "Lightning Greaves"]
    g = game(rocks, 3, mode="never")
    check("A never: no activation, nothing eaten",
          (fired(g), all(on_board(g, n) for n in rocks)), (0, True))
    g = game(rocks, 3)
    check("B cap: Greaves and Signet go, Sol Ring stays",
          (fired(g), on_board(g, "Lightning Greaves"),
           on_board(g, "Azorius Signet"), on_board(g, "Sol Ring")),
          (1, False, False, True))
    g = game(rocks, 3, mode="combo")
    check("C combo without Tivit: not activated", fired(g), 0)
    g = game(rocks, 3, mode="combo", tivit=True)
    check("D combo with Tivit: activated", fired(g), 1)
    g = game(["Coercive Portal"], 4)
    check("E an MV-4 artifact is not fuel", fired(g), 0)
    g = game([], 4)
    check("F Time Sieve is not its own fuel", fired(g), 0)
    g = game(["Ancient Den", "Arcane Signet"], 4)
    check("G the Signet goes, the land stays",
          (fired(g), on_board(g, "Arcane Signet"), on_board(g, "Ancient Den")),
          (1, False, True))
    g = game(["Sol Ring", "Marionette Master"], 4)
    fired(g)
    check("H Marionette Master: 4 x 5 = 20", g.m["artifact_drain"], 20.0)
    g = game(["Sol Ring", "Disciple of the Vault"], 4)
    fired(g)
    check("I Disciple: 5 (one each over three opponents)",
          round(g.m["token_drain"], 6), 5.0)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Time Sieve's real-artifact fuel\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {n: getattr(T, n) for n in ("sieve_real_fuel", "disciple_share")}

    def ignore_tivit(g):
        if g.cfg.get("sieve_real_fuel") == "combo":
            g.cfg["sieve_real_fuel"] = "cap"
            try:
                return real["sieve_real_fuel"](g)
            finally:
                g.cfg["sieve_real_fuel"] = "combo"
        return real["sieve_real_fuel"](g)

    def mv_only(g):
        return sorted(real["sieve_real_fuel"](g), key=lambda p: p.card.mv)

    def no_cap(g):
        g.cfg["sieve_real_mv_cap"] = 99
        return real["sieve_real_fuel"](g)

    muts = {
        "real fuel is never allowed":
            ({"B", "D", "G", "H", "I"}, "sieve_real_fuel", lambda g: []),
        "combo ignores whether Tivit is out":
            ({"C"}, "sieve_real_fuel", ignore_tivit),
        "the order is mana value alone":
            ({"B", "G"}, "sieve_real_fuel", mv_only),
        "Disciple does not read the sacrifice":
            ({"I"}, "disciple_share", lambda g: 0.0),
        "the mana-value cap is ignored":
            ({"E"}, "sieve_real_fuel", no_cap),
    }
    bad = 0
    for label, (want, name, fn) in muts.items():
        print(f"-- {label}")
        setattr(T, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(T, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
