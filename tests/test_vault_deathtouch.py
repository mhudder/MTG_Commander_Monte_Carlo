#!/usr/bin/env python3
"""§0z230 (§0z206 floor 1): Vault of the Archangel's deathtouch --
"Creatures you control gain deathtouch and lifelink until end of turn" --
read by `opponents.deathtouch_of` on a turn the Vault was activated.

    python -m tests.test_vault_deathtouch
    python -m tests.test_vault_deathtouch --mutate   # 2 mutations, exact sets

Each case: a karlov game, a vanilla 2/2 of yours, `vault_turn` set by hand.

CASES
  A  a Vault turn: the 2/2 has deathtouch, and the defender's view of it
     (`attack_facts`) says so
  B  NEIGHBOUR: the Vault activated LAST turn: no deathtouch
  C  NEIGHBOUR: `vault_deathtouch` False on a Vault turn: none (the old rule)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  vault_deathtouch=False           -> A
  the Vault is always active       -> B

UNMUTATED (§0z15): C is the old rule under every reading.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as KV
import edhmc.opponents as OPP
from edhmc.decks import karlov_v2 as KM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(vault_turn, **cfg):
    deck, cmd = KM.build()
    g = KV.KarlovGame(list(deck), cmd,
                      dict(DEFAULT_CFG, **{**EXTRA_CFG, **cfg}), 1)
    g.board = EN.Board()
    g.turn = 5
    g.vault_turn = vault_turn
    p = EN.Permanent(card=EN.Card(name="Bear", types=frozenset({"Creature"}),
                                  power=2, toughness=2), sick=False)
    g.board.append(p)
    return g, p


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, p = game(5)
    check("A a Vault turn: deathtouch, and attack_facts says so",
          (OPP.deathtouch_of(g, p),
           OPP.attack_facts(g, p, 0, g.opponents[0]).dt), (True, True))

    g, p = game(4)
    check("B NEIGHBOUR: last turn's Vault: none", OPP.deathtouch_of(g, p),
          False)

    g, p = game(5, vault_deathtouch=False)
    check("C NEIGHBOUR: vault_deathtouch False: none",
          OPP.deathtouch_of(g, p), False)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z230: Vault of the Archangel's deathtouch\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "vault_deathtouch=False": ({"A"}, {"vault_deathtouch": False}, []),
        "the Vault is always active": ({"B"}, {}, [
            (EN, "vault_active", lambda g: True)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
        saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
        for obj, name, val in patches:
            setattr(obj, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            for obj, name, val in saved:
                setattr(obj, name, val)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke)}, want {sorted(want)}: "
              f"{'ok' if ok else 'MISMATCH'}\n")
    print(f"{len(muts) - bad} of {len(muts)} mutations exact")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
