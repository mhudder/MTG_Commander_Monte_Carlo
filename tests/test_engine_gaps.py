#!/usr/bin/env python3
"""Three engine gaps closed together (§0z90, §0z91, §0z92).

    python -m tests.test_engine_gaps
    python -m tests.test_engine_gaps --mutate   # 6 mutations, exact sets

    Exquisite Blood /      "Whenever an opponent loses life, you gain that
    Bloodthirsty Conqueror  much life."                 (Scryfall, 2026-09-30)
    Starscape Cleric /     "Whenever you gain life, each opponent loses 1
    Blight-Priest /         life."
    Cliffhaven Vampire
    Tivit, Seller of       "Whenever Tivit enters or deals combat damage to a
    Secrets                 player, ..."
    trample                a blocked trampler assigns what its blockers
                            cannot absorb to the player

CASES
  A  Exquisite Blood alone, each opponent loses 1: three lifegain EVENTS,
     three life
  B  Blood AND Conqueror, one opponent loses 4: two events, eight life
  C  Blood + Starscape Cleric, one lifegain event: the drain loop wins,
     `win_route` 5
  D  NEIGHBOUR: Cleric without Blood -- each opponent loses 1, no win
  E  NEIGHBOUR: `exquisite_general=False` -- case A gains nothing
  F  NEIGHBOUR: both knobs off -- case C drains each opponent once, no win
  G  Tivit attacked and was blocked, a token connected: NO trigger
  H  Tivit connected: the trigger fires
  I  NEIGHBOUR: `tivit_trigger_connects=False` -- G's combat fires (the old
     reading, "damage was dealt and Tivit attacked")
  J  a 6/6 trampler blocked by one 2-toughness chump: 4 through
  K  `blocker_toughness=4`: 2 through
  L  rendmaw after Overwhelming Stampede: a vanilla 5/5, blocked, gets 3
     through (the team has trample)
  M  NEIGHBOUR: a vanilla 6/6 blocked: 0 through
  N  one blocker, a 6/6 trampler and a 4/4: the defender blocks the 4/4,
     because it stops more there -- 6 through (old rule: 4)
  O  an azusa land animated WITH trample reads as trampling

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  opponents.lost_life never calls the hook        -> A, B
  the hook gains once however many copies         -> B
  drain_loop_partner is always False              -> C
  the Tivit trigger ignores who connected         -> G
  trample_of is always False                      -> J, K, L, N, O
  chump ignores what a trampler's block stops     -> J, K, L, N

UNMUTATED (§0z15): D, E, F, I and M are neighbours and knobs; H is the
positive half of G's seam.
"""
import random
import sys
import types

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.opponents as OPP
import edhmc.tivit as T
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def body(name, p=2, t=2, **kw):
    return EN.Card(name=name, types=frozenset({"Creature"}), power=p,
                   toughness=t, **kw)


def perm(c, **kw):
    kw.setdefault("sick", False)
    return EN.Permanent(card=c, base_p=c.power, base_t=c.toughness, **kw)


KDECK, KCMD = KM.build()
K_ = {c.name: c for c in KDECK}
K_["Bloodthirsty Conqueror"] = KM.BLOODTHIRSTY_CONQUEROR \
    if hasattr(KM, "BLOODTHIRSTY_CONQUEROR") else body(
        "Bloodthirsty Conqueror", 5, 5)


def kgame(*names, **cfg):
    g = K.KarlovGame(list(KDECK), KCMD, {**DEFAULT_CFG, **EXTRA_CFG, **cfg}, 3)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 5
    for o in g.opponents:
        o.life = 40.0
    for n in names:
        g.board.append(perm(K_[n]))
    return g


def run_karlov():
    g = kgame("Exquisite Blood")
    life = g.your_life
    OPP.damage_each(g, 1)
    check("A Blood alone: three events, three life",
          (g.m["lifegain_triggers"], g.your_life - life), (3, 3))
    g = kgame("Exquisite Blood", "Bloodthirsty Conqueror")
    life = g.your_life
    OPP.damage_single(g, 4)
    check("B Blood and Conqueror: two events, eight life",
          (g.m["lifegain_triggers"], g.your_life - life), (2, 8))
    g = kgame("Exquisite Blood", "Starscape Cleric")
    K.gain_life(g, 1)
    check("C Blood + Cleric: the drain loop wins", (g.result, g.m["win_route"]),
          ("win", 5))
    g = kgame("Starscape Cleric")
    K.gain_life(g, 1)
    check("D Cleric alone: each opponent loses 1, no win",
          (g.result, [o.life for o in g.opponents]), (None, [39.0] * 3))
    g = kgame("Exquisite Blood", exquisite_general=False)
    life = g.your_life
    OPP.damage_each(g, 1)
    check("E exquisite_general=False: no gain", g.your_life - life, 0)
    g = kgame("Exquisite Blood", "Starscape Cleric", exquisite_general=False,
              exquisite_drain_loop=False)
    K.gain_life(g, 1)
    check("F both knobs off: one drain, no win",
          (g.result, [o.life for o in g.opponents]), (None, [39.0] * 3))


TDECK, TCMD = TM.build()


def tivit_combat(hit_tivit, **cfg):
    """Tivit and a token attack; a stubbed pod reports who connected."""
    g = T.TivitGame(list(TDECK), TCMD, {**DEFAULT_CFG, **EXTRA_CFG, **cfg}, 3)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.turn = 5
    tivit, token = perm(TCMD), perm(body("Soldier token", 1, 1), is_token=True)
    g.board.extend([tivit, token])
    g.commander_cast = True
    fired = []
    real_combat, real_dilemma = OPP.combat_damage, T.tivit_dilemma

    def pod(g_, attackers, scale=1.0):
        OPP.record_hits(g_, [tivit] if hit_tivit else [token])
        return 1.0

    OPP.combat_damage = pod
    T.tivit_dilemma = lambda g_: fired.append(1)
    try:
        T.combat(g)
    finally:
        OPP.combat_damage, T.tivit_dilemma = real_combat, real_dilemma
    return len(fired)


def run_tivit():
    check("G Tivit blocked, a token connected: no trigger",
          tivit_combat(False), 0)
    check("H Tivit connected: the trigger fires", tivit_combat(True), 1)
    check("I tivit_trigger_connects=False: the old reading fires",
          tivit_combat(False, tivit_trigger_connects=False), 1)


RDECK, RCMD = RM.build()
TRAMPLER = next(n for n in ("Rampaging Baloths", "Verdurous Gearhulk",
                            "Cultivator Colossus"))


def rgame(**cfg):
    g = EN.Game(list(RDECK), RCMD, {**DEFAULT_CFG, **EXTRA_CFG, **cfg},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.turn = 6
    return g


def one_blocker(g):
    """A defender whose board yields exactly one ground blocker."""
    d = g.opponents[0]
    d.creatures, d.goaded_birds = 2.0, 0.0
    assert OPP._blocker_counts(g, d) == (1, 0)
    return d


def run_trample():
    g = rgame()
    big = perm(body(TRAMPLER, 6, 6))
    d = one_blocker(g)
    check("J a blocked 6/6 trampler: 4 through",
          OPP.damage_through(g, [big], defender=d), 4.0)
    g = rgame(blocker_toughness=4)
    d = one_blocker(g)
    check("K blocker_toughness=4: 2 through",
          OPP.damage_through(g, [big], defender=d), 2.0)
    g = rgame()
    d = one_blocker(g)
    g.stampede_bonus = 1
    five = perm(body("Vanilla", 4, 4))          # 5/5 with the +1 bonus
    check("L after Stampede, a blocked 5/5: 3 through",
          OPP.damage_through(g, [five], defender=d), 3.0)
    g = rgame()
    d = one_blocker(g)
    check("M a blocked vanilla 6/6: nothing through",
          OPP.damage_through(g, [perm(body("Vanilla", 6, 6))], defender=d),
          0.0)
    g = rgame()
    d = one_blocker(g)
    check("N the defender blocks the 4/4, not the trampler: 6 through",
          OPP.damage_through(g, [big, perm(body("Bear", 4, 4))], defender=d),
          6.0)
    fake = types.SimpleNamespace(cfg={**DEFAULT_CFG, **EXTRA_CFG},
                                 animation_of=lambda p: {"trample": True})
    check("O an animated land with trample tramples",
          OPP.trample_of(fake, perm(body("Forest", 4, 4))), True)


def run_cases():
    PASS.clear()
    FAIL.clear()
    run_karlov()
    run_tivit()
    run_trample()
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("Items 1-3: Exquisite Blood, Tivit's trigger, trample\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_chump = OPP.chump

    def gains_once(self, o, loss):
        if self.cfg.get("exquisite_general", True) and K.has_combo_a(self):
            K.gain_life(self, loss)

    muts = {
        "opponents.lost_life never calls the hook":
            ({"A", "B"}, (OPP, "lost_life", lambda g, losses: None), {}),
        "the hook gains once however many copies":
            ({"B"}, (K.KarlovGame, "on_opponent_lost_life", gains_once), {}),
        "drain_loop_partner is always False":
            ({"C"}, (K, "drain_loop_partner", lambda g: False), {}),
        "the Tivit trigger ignores who connected":
            ({"G"}, None, {"tivit_trigger_connects": False}),
        "trample_of is always False":
            ({"J", "K", "L", "N", "O"},
             (OPP, "trample_of", lambda g, p: False), {}),
        "chump ignores what a trampler's block stops":
            ({"J", "K", "L", "N"},
             (OPP, "chump", lambda items, budget, blocked=None: real_chump(
                 [it[:4] for it in items], budget, blocked)), {}),
    }
    bad = 0
    for label, (want, patch, cfg) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = cfg
        if patch:
            owner, name, fn = patch
            real = getattr(owner, name)
            setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            EXTRA_CFG = {}
            if patch:
                setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
