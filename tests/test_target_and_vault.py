#!/usr/bin/env python3
"""Goldspan's targeted Treasure, and the Treasure Vault held back (§0z77).

    python -m tests.test_target_and_vault
    python -m tests.test_target_and_vault --mutate   # 3 mutations, exact sets

    Goldspan Dragon  Whenever Goldspan Dragon attacks or becomes the target of
                     a spell, create a Treasure token.
    Treasure Vault   {T}: Add {C}. {X}{X}, {T}, Sacrifice this land: Create X
                     Treasure tokens.              (Scryfall, verified)

Two floors named in §0z68/§0z69. The pod's spot removal targets Goldspan and
made no Treasure: `opponents.spot_removal` now calls the optional protocol
hook `g.on_targeted(victim)`, which lorehold implements. And the Vault's {C}
was spent in the main phase before its end-of-turn crack could happen:
`engine.vault_held` keeps it out of `rendmaw_mana` while a token doubler is
out (`vault_hold="doubler"`). That mode MEASURED WORSE than spending the
{C} (§0z77), so the default is "never"; D and E pass "doubler" explicitly.

CASES
  A  the pod's spot removal targets Goldspan: one Treasure
  B  it targets a bigger threat instead: no Treasure
  C  `goldspan_targeted=False`: no Treasure (the old Goldspan)
  D  hold "doubler", Primal Vigor out: the Vault's {C} is not in the pool
  E  hold "doubler", no doubler: it is
  F  hold "always", no doubler: it is not
  G  the default ("never"), Primal Vigor out: it is
  H  NEIGHBOUR: the Vault still cracks at the end step (4 Swamps, Primal
     Vigor: X=2, doubled to 4 Treasures)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the targeting hook does nothing           -> A
  the Vault is never held                    -> D, F
  "doubler" holds without a doubler          -> E

UNMUTATED (§0z15): B, C and G are the neighbours and the knob; H is the
§0z68 behaviour the hold must not break.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
import edhmc.opponents as OPP
from edhmc.decks import lorehold_v16 as LM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


LDECK, LCMD = LM.build()
RDECK, RCMD = RM.build()


def lgame(*cards, **cfg):
    g = L.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard = [], []
    g.treasures = 0
    g.turn = 6
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def removal(g):
    rolls = [0.0] * 8
    rolls[5] = rolls[7] = 1.0          # no protection; destroys
    opp = g.opponents[0]
    OPP.spot_removal(g, opp, g.opponents[1:], rolls)


def rgame(*cards, **cfg):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.treasures = 0
    for c in cards:
        g.board.append(EN.Permanent(card=c, sick=False))
    return g


def rcard(name):
    return next(c for c in RDECK if c.name == name)


def vault_in_pool(g):
    units = EN.rendmaw_mana(g)
    return any(getattr(o, "card", None) is not None
               and o.card.name == "Treasure Vault" for o in units.owners)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    gold = LM.GOLDSPAN_DRAGON
    g = lgame(gold)
    removal(g)
    check("A spot removal targets Goldspan: one Treasure", g.treasures, 1)
    g = lgame(gold, LM.MOLECULE_MAN)
    removal(g)
    check("B a bigger threat is targeted: no Treasure", g.treasures, 0)
    g = lgame(gold, goldspan_targeted=False)
    removal(g)
    check("C goldspan_targeted off: no Treasure", g.treasures, 0)
    vault, vigor = rcard("Treasure Vault"), rcard("Primal Vigor")
    check("D doubler out: the Vault is held",
          vault_in_pool(rgame(vault, vigor, vault_hold="doubler")), False)
    check("E no doubler: the Vault pays",
          vault_in_pool(rgame(vault, vault_hold="doubler")), True)
    check("F always: held without a doubler",
          vault_in_pool(rgame(vault, vault_hold="always")), False)
    check("G never (the default): pays with a doubler",
          vault_in_pool(rgame(vault, vigor)), True)
    swamp = EN.Card(name="Swamp", types=frozenset({"Land"}), is_land=True,
                    produces=frozenset({"B"}))
    g = rgame(vault, vigor, *[swamp] * 4)
    EN.treasure_vault(g)
    check("H a held Vault still cracks: 4 Treasures", g.treasures, 4)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Goldspan targeted; the Vault held back\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_target = L.LoreholdGame.on_targeted
    real_held = EN.vault_held

    def doubler_always(g):
        if g.cfg.get("vault_hold", "never") == "doubler":
            g.cfg["vault_hold"] = "always"
            try:
                return real_held(g)
            finally:
                g.cfg["vault_hold"] = "doubler"
        return real_held(g)

    muts = {
        "the targeting hook does nothing":
            ({"A"}, (L.LoreholdGame, "on_targeted", lambda self, p: None)),
        "the Vault is never held":
            ({"D", "F"}, (EN, "vault_held", lambda g: None)),
        "doubler holds without a doubler":
            ({"E"}, (EN, "vault_held", doubler_always)),
    }
    reals = {"on_targeted": real_target, "vault_held": real_held}
    bad = 0
    for label, (want, (mod, name, fn)) in muts.items():
        print(f"-- {label}")
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, reals[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
