#!/usr/bin/env python3
"""§0z238 (queue item 50, step 3): Ghostly Prison and Propaganda paid from
the pod's mana, by the owner's rule.

    python -m tests.test_pod_tax
    python -m tests.test_pod_tax --mutate   # 5 mutations, exact sets

The rule's two halves are called directly: `taxed_attack` (which declared
attackers the pod pays for) on values a case names, with a tax of {2} and
your life as the case says; and `tax_kill` (a combat kill under the tax) on
a game of tivit's list (the shared engine's `Game`; only the pod's functions
run) with Ghostly Prison out, opponent 0's body pool set to five
10/10s so its kill force is four of them, and no blockers on your side.

CASES
  A  `_through`: a 6-power trampler blocked by a 2-toughness body gets 4
     through (702.19b); unblocked, its power; blocked without trample, 0
  B  not lethal, mana 10: values 1, 3, 2 -- pays for the 3 and the 2 (each
     worth {2} at 1.0 damage a mana), not the 1
  C  the same with mana 2: one attacker, the strongest
  D  lethal, life 4, values 3, 1.5, 1, mana 4: pays for the 3 and the 1.5
     (4.5 covers 4) -- the 1.5 is below the bar, and lethal pays anyway
  E  lethal but mana 2: the two cannot be afforded, so the bar's rule: the 3
  F  `tax_damage_per_mana` 2.0: a 3 is not worth {2} (the bar is 4): nothing
  H1 a kill with 0 mana and rivals alive: deflected
  H2 a kill on your 15 life with 5 mana: pays {4} for the two 10/10s that
     are lethal, and attacks with those two
  H3 a kill with 2 mana and NOBODY else alive: pays what it can, one 10/10
  H4 a kill on your 15 life with 10 mana and ONE blocker of yours: alone,
     each 10/10 is blocked (value 0); planned as a group, the blocker takes
     one, so THREE are lethal -- it pays {6} and attacks with three
     (ADDED AFTER THE FIRST MEASUREMENT, with the group rule: see below)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  no lethal exception (lethal_subset finds none)  -> D, H2, H4
  the bar ignored (tax_damage_per_mana 0)          -> B, F
  the mana ignored (TAX_NEEDS_MANA False)          -> C, E, H1, H3
  a kill never deflects (TAX_KILL_DEFLECTS False)  -> H1
  lethal judged alone (LETHAL_JOINT False)         -> H4

THE FIRST MEASUREMENT FOUND THE RULE WRONG, NOT A CASE (§0z238): the lethal
test summed each attacker's damage ALONE, so a taxed kill paid for 2.3
attackers that killed you in 10 of 41 games -- and where every attacker is
blocked alone, for none. It plans the GROUP's blocks now; H4 and the
LETHAL_JOINT mutation pin that, and "the mana ignored" gains H3, where
paying what it can is now gated by the mana (it sent the whole lethal
force free before). Written before the re-run.

UNMUTATED (§0z15): A is 702.19b's arithmetic; H3 has nobody to deflect to
under every rule here.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as O
from edhmc.decks import tivit_v1 as TV
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


class G:
    """Just what `taxed_attack` and `lethal_subset` read."""

    def __init__(self, life, **cfg):
        self.your_life = life
        self.cfg = {**DEFAULT_CFG, **cfg, **EXTRA_CFG}


def tivit_game(mana, rivals=True):
    deck, cmd = TV.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "pod_mana": True, "pod_tax_mana": True,
                 **EXTRA_CFG}, random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 8
    g.your_life = 15.0
    prison = next(c for c in list(deck) if c.name == "Ghostly Prison")
    g.board.append(EN.Permanent(card=prison, sick=False))
    o = g.opponents[0]
    o.body_pool = tuple(O.PodBody(10, 4, False, 10) for _ in range(5))
    o.next_body = 0
    o.mana_left = mana
    others = g.opponents[1:] if rivals else []
    if not rivals:
        for x in g.opponents[1:]:
            x.alive = False
    return g, o, others


def run_cases():
    PASS.clear()
    FAIL.clear()

    big = O._Atk(0, ("x", 0), 6, 6, False, False, True, False, False, False,
                 False, 4.0, False)
    plain = big._replace(trample=False)
    g0 = EN.Game(list(TV.build()[0]), TV.build()[1], dict(DEFAULT_CFG),
                 random.Random(1), seed_for_pod=1)
    wall = next(c for c in g0.library if c.is_creature and c.toughness == 2)
    small = EN.Permanent(card=wall, sick=False)

    class B:                     # a blocker with a ref, as plan_blocks gives
        ref = small
    check("A 702.19b: trample 6 over a 2-toughness body is 4",
          (O._through(big, [B()], g0), O._through(big, [], g0),
           O._through(plain, [B()], g0)), (4.0, 6.0, 0.0))

    check("B not lethal, mana 10: the 3 and the 2",
          O.taxed_attack(G(40.0), {0: 1.0, 1: 3.0, 2: 2.0}, 10.0, 2.0),
          [1, 2])
    check("C mana 2: the strongest only",
          O.taxed_attack(G(40.0), {0: 1.0, 1: 3.0, 2: 2.0}, 2.0, 2.0), [1])
    check("D lethal on 4 life: the 3 and the 1.5",
          O.taxed_attack(G(4.0), {0: 3.0, 1: 1.5, 2: 1.0}, 4.0, 2.0), [0, 1])
    check("E lethal but mana 2: the bar's rule, the 3",
          O.taxed_attack(G(4.0), {0: 3.0, 1: 1.5, 2: 1.0}, 2.0, 2.0), [0])
    check("F bar 2.0: a 3 is not worth {2}",
          O.taxed_attack(G(40.0, tax_damage_per_mana=2.0), {1: 3.0}, 10.0,
                         2.0), [])

    g, o, others = tivit_game(0.0)
    check("H1 0 mana, rivals alive: deflected",
          O.tax_kill(g, o, others)[0], True)
    g, o, others = tivit_game(5.0)
    deflected, force = O.tax_kill(g, o, others)
    check("H2 5 mana on 15 life: pays {4}, attacks with two 10/10s",
          (deflected, len(force or ()), o.mana_left), (False, 2, 1.0))
    g, o, others = tivit_game(2.0, rivals=False)
    deflected, force = O.tax_kill(g, o, others)
    check("H3 2 mana, nobody else: pays what it can, one 10/10",
          (deflected, len(force or ()), o.mana_left), (False, 1, 0.0))
    g, o, others = tivit_game(10.0)
    wall = next(c for c in g.library if c.is_creature and c.toughness == 2)
    g.board.append(EN.Permanent(card=wall, sick=False))
    deflected, force = O.tax_kill(g, o, others)
    check("H4 one blocker: three 10/10s are lethal as a group, {6}",
          (deflected, len(force or ()), o.mana_left), (False, 3, 4.0))
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z238: the attack taxes paid from the pod's mana\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "no lethal exception": (
            {"D", "H2", "H4"}, {}, [("lethal_subset", lambda g, values, atks=None: None)]),
        "the bar ignored": ({"B", "F"}, {"tax_damage_per_mana": 0.0}, []),
        "the mana ignored": ({"C", "E", "H1", "H3"}, {},
                             [("TAX_NEEDS_MANA", False)]),
        "a kill never deflects": ({"H1"}, {}, [("TAX_KILL_DEFLECTS", False)]),
        "lethal judged alone": ({"H4"}, {}, [("LETHAL_JOINT", False)]),
    }
    bad = 0
    for label, (want, cfg, patches) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = dict(cfg)
        saved = [(name, getattr(O, name)) for name, _ in patches]
        for name, val in patches:
            setattr(O, name, val)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
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
