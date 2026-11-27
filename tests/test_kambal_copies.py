#!/usr/bin/env python3
"""§0z267: Kambal, Profiteering Mayor's first ability (tivit).

    python -m tests.test_kambal_copies
    python -m tests.test_kambal_copies --mutate   # 5 mutations, exact sets

    "Whenever one or more tokens your opponents control enter, for each of
    them, create a tapped token that's a copy of it. This ability triggers
    only once each turn."                ({1}{W}{B}; Scryfall 2026-11-27)

`tivit.pod_tokens_enter` is the trigger; one call is one batch. Its copies
enter tapped: a copied Treasure is in the pile but no mana until your untap
(`treasures_tapped`).

CASES (tivit, Kambal on the battlefield unless said)
  A  two opponent Treasures: two Treasures for you, both tapped, one trigger
  B  a second batch the same turn: nothing ("only once each turn"), counted
  C  the next pod seat's turn is a new turn: it copies again
  D  no Kambal: nothing, and no reach counted
  E  NEIGHBOUR: kambal_copies=False -- nothing made, the reach counted
  F  the tapped copies are not mana: the mana units hold no Treasure
  G  Academy Manufactor: one copied Treasure is a Treasure, a Clue and a
     Food; the one Treasure tapped
  H  two Rabbits: two tapped 1/1 creature tokens on your battlefield
  I  An Offer You Can't Refuse through `opponents.pod_gift`: two copies
  J  Tempting Contract's upkeep, three takers: three copies in ONE trigger
  K  the copies are a batch YOU create: Kambal's second ability once
  L  a sacrifice not for mana takes a tapped Treasure first; a Treasure
     spent for mana leaves the tapped ones tapped

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  "once each turn" never holds (a new key every call)   -> B
  the copies enter untapped (make_token's tapped dropped) -> A, F, G
  pod_gift never announces (no game hook)                -> I
  the turn key ignores the pod seat                      -> C
  tapped Treasures still counted as mana                 -> F

THE FIRST RUN (§0z11): the first mutation broke B and C. C continued B's
game, so B's extra copy moved C's counts -- a setup slip, not the rule.
C is its own game now; the expected sets are as written.

UNMUTATED (§0z15): D and E are the trigger's off sides; H, J, K and L
hold under every mutation above (H's tapped flag is make_tokens', not
make_token's; J's batch is one call; L's counts are set by hand).
"""
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
import edhmc.tivit as TI
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
KAMBAL = "Kambal, Profiteering Mayor"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(kambal=True, extra=(), **cfg):
    names = ([KAMBAL] if kambal else []) + list(extra)
    board = [B.card("tivit", n) for n in names]
    g = B.fresh("tivit", board=board, **{**EXTRA_CFG, **cfg})
    g.turn = 4
    g.pod_seat = None
    for k in g.tokens:
        g.tokens[k] = 0
    g.treasures_tapped = 0
    g.kambal_copy_turn = None
    return g


def treasure_units(g):
    return sum(1 for u in TI.mana_units(g) if u == frozenset("WUBC"))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    TI.pod_tokens_enter(g, "Treasure", 2)
    check("A two Treasures: two tapped copies, one trigger",
          (g.tokens["Treasure"], g.treasures_tapped,
           g.m["kambal_copy_triggers"]), (2, 2, 1))
    TI.pod_tokens_enter(g, "Treasure", 1)
    check("B a second batch this turn: nothing, counted",
          (g.tokens["Treasure"], g.m["kambal_copy_once"]), (2, 1))
    g = game()
    TI.pod_tokens_enter(g, "Treasure", 1)
    g.pod_seat = 0
    TI.pod_tokens_enter(g, "Treasure", 1)
    check("C the next seat's turn: copies again",
          (g.tokens["Treasure"], g.m["kambal_copy_triggers"]), (2, 2))

    g = game(kambal=False)
    TI.pod_tokens_enter(g, "Treasure", 2)
    check("D no Kambal: nothing, no reach",
          (g.tokens["Treasure"], g.m["kambal_copy_seen"]), (0, 0))

    g = game(kambal_copies=False)
    TI.pod_tokens_enter(g, "Treasure", 2)
    check("E kambal_copies=False: nothing, the reach counted",
          (g.tokens["Treasure"], g.m["kambal_copy_seen"]), (0, 1))

    g = game()
    TI.pod_tokens_enter(g, "Treasure", 2)
    check("F the tapped copies are no mana", treasure_units(g), 0)

    g = game(extra=["Academy Manufactor"])
    TI.pod_tokens_enter(g, "Treasure", 1)
    check("G Manufactor: Treasure, Clue, Food; the Treasure tapped",
          (g.tokens["Treasure"], g.tokens["Clue"], g.tokens["Food"],
           g.treasures_tapped), (1, 1, 1, 1))

    g = game()
    TI.pod_tokens_enter(g, "Rabbit", 2)
    rabbits = [p for p in g.board if p.card.name == "Rabbit token"]
    check("H two Rabbits: two tapped 1/1 tokens",
          [(p.tapped, p.card.power, p.card.toughness) for p in rabbits],
          [(True, 1, 1)] * 2)

    g = game()
    OPP.pod_gift(g, g.opponents[0], "An Offer You Can't Refuse")
    check("I An Offer through pod_gift: two copies",
          g.m["kambal_copies"], 2)

    g = game(extra=["Tempting Contract"], tempting_offer_rate=1.0)
    TI.upkeep(g)
    check("J Contract, three takers: three copies, one trigger",
          (g.m["kambal_copies"], g.m["kambal_copy_triggers"]), (3, 1))

    g = game()
    before = g.m["kambal_triggers"]
    TI.pod_tokens_enter(g, "Treasure", 3)
    check("K the copies are one batch of yours: Kambal's second ability once",
          g.m["kambal_triggers"] - before, 1)

    g = game()
    g.tokens["Treasure"], g.treasures_tapped = 3, 2
    TI.sacrifice_tokens(g, "Treasure", 1)
    first = g.treasures_tapped
    g.tokens["Treasure"], g.treasures_tapped = 3, 2
    TI.pay(g, {"gen": 1})
    check("L a sacrifice takes a tapped one; mana spends an untapped one",
          (first, g.tokens["Treasure"], g.treasures_tapped), (1, 2, 2))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z267: Kambal, Profiteering Mayor's copies\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_key, real_make, real_units = (TI.kambal_turn_key, TI.make_token,
                                       TI.untapped_treasures)
    real_hook = TI.TivitGame.pod_tokens_enter

    def set_key(v):
        TI.kambal_turn_key = v

    def set_make(v):
        TI.make_token = v

    def set_hook(v):
        TI.TivitGame.pod_tokens_enter = v

    def set_units(v):
        TI.untapped_treasures = v

    muts = {
        "'once each turn' never holds": (
            {"B"}, set_key, lambda g: object(), real_key),
        "the copies enter untapped": (
            {"A", "F", "G"}, set_make,
            lambda g, kind, n=1, tapped=False: real_make(g, kind, n),
            real_make),
        "pod_gift never announces": ({"I"}, set_hook, None, real_hook),
        "the turn key ignores the pod seat": (
            {"C"}, set_key, lambda g: g.turn, real_key),
        "tapped Treasures still counted as mana": (
            {"F"}, set_units, lambda g: g.tokens["Treasure"], real_units),
    }
    bad = 0
    for label, (want, setter, value, restore) in muts.items():
        print(f"-- {label}")
        setter(value)
        try:
            broke = run_cases()
        finally:
            setter(restore)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts)} mutations, {len(muts) - bad} exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
