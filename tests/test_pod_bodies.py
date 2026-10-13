#!/usr/bin/env python3
"""The pod's creatures as bodies (item 24, change 1; `pod_bodies`, OFF by
default).

    python -m tests.test_pod_bodies
    python -m tests.test_pod_bodies --mutate   # 8 mutations, exact sets

Each opponent's creatures stay the COUNT every existing reader uses; under
`pod_bodies` they are also pre-rolled bodies with a toughness and a mana
value, for the effects that ask about one, and each death is an event the
engine's `on_pod_creature_deaths` hook hears. Texts verified 2026-10-13:
Immolating Gyre ("X damage to each creature ... you don't control"),
Massacre Wurm ("-2/-2" and "that player loses 2 life"), Culling Ritual
("mana value 2 or less"), Promise of Loyalty ("sacrifices the rest"), Blood
Artist ("this creature or another creature dies"), Revel in Riches ("create
a Treasure token"), Volcanic Vision ("damage equal to that card's mana value
to each creature your opponents control").

CASES
  A  OFF changes nothing in `make_pod`: the same opponents and rolls, and no
     pool; ON adds a pool and draws nothing from the pod's stream
  B  a pool's toughness lies in 1..`gyre_full_x` and its mana value in
     1..round(2 / `culling_pod_share`), and it repeats per seed
  C  bodies follow the count: 2.7 -> two; 3.1 -> three, the first two the
     same; 1.0 -> the FIRST one stays (the newest leave first)
  D  `kill_pod_bodies` kills what its rule names, keeps the fraction, and
     tells the hook (opponent, n)
  E  Immolating Gyre at X=3 kills toughness 3 or less -- and the wipe gate
     expected the same survivors
  F  rendmaw's Massacre Wurm under bodies: toughness 2 or less die, and that
     player loses 2 for each
  G  Culling Ritual kills mana value 2 or less
  H  Promise of Loyalty keeps the toughest, the count goes to 1
  I  an opponent's wrath kills every body, each an event; the count is 0
  J  OFF: Gyre's survivors are the count's share, as before
  K  tivit's Revel in Riches: a Treasure per death, doubled by Anointed
     Procession
  L  karlov's Blood Artist drains for an opponent's creature
  M  lorehold's Volcanic Vision returning a 4-drop kills toughness 4 or less
  N  shilgengar's Massacre Wurm under bodies: 2 per death, not twice that
  O  rendmaw resolves a sweeping permanent BEFORE it enters: Massacre Wurm
     cast from hand still drains for the deaths its own -2/-2 causes
  P  an edict for more than the board leaves 0, not a fraction (the count's
     own arithmetic)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  kill_pod_bodies never tells the hook           -> D, F, I, K, L, N, O*
  every own sweeper kills every body             -> E, F, G, H, O*
  bodies leave oldest-first                      -> C
  the wipe gate ignores bodies                   -> E
  an opponent's wrath zeroes without events      -> I
  Volcanic Vision's damage half is gone          -> M
  (added with O and P, before their run)
  * O WAS ADDED AFTER THE FIRST TWO SETS WERE WRITTEN, and they were not
    extended before the run: both broke O as well. That is right -- O reads
    the hook and the -2/-2 rule like F does -- and it is recorded as a
    transcript, not a prediction (§0z14).
  the entering source is not named               -> O
  an edict leaves the fraction                   -> P

UNMUTATED (§0z15): A and B are properties of `roll_body_pools`, read by the
plain run; J is the OFF path.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.lorehold as L
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as T
from edhmc.decks import karlov_v2 as KM
from edhmc.decks import lorehold_v17 as LM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
B = OPP.PodBody


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def find(module, name):
    deck, cmd = module.build()
    pool = list(deck) + [cmd] + [v for v in vars(module).values()
                                 if isinstance(v, EN.Card)]
    return next(c for c in pool if c.name == name)


POOL = (B(1, 1), B(2, 3), B(3, 2), B(4, 4), B(5, 1), B(6, 3), B(2, 2), B(1, 4))


def ready(g, creatures=(4.0, 0.0, 0.0), pool=POOL):
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [EN.Card(name=f"L{i}", types=frozenset({"Creature"}))
                 for i in range(30)]
    g.turn = 6
    g.your_life = 40.0
    for o, n in zip(g.opponents, creatures):
        o.life, o.creatures = 40.0, n
        o.body_pool, o.bodies, o.next_body = pool, [], 0
    return g


def rgame(**cfg):
    deck, cmd = RM.build()
    return ready(EN.Game(list(deck), cmd, dict(DEFAULT_CFG,
                                               **dict(dict(pod_bodies=True),
                                                      **cfg)),
                         random.Random(1), seed_for_pod=1))


def put(g, card):
    g.board.append(EN.Permanent(card=card, sick=False, base_p=card.power,
                                base_t=card.toughness))


def instant(i):
    return EN.Card(name=f"I{i}", types=frozenset({"Instant"}))


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    cfg = dict(DEFAULT_CFG)

    a_off = OPP.make_pod(dict(cfg, pod_bodies=False), 77)
    a_on = OPP.make_pod(dict(cfg, pod_bodies=True), 77)
    same = (a_off[1] == a_on[1] and a_off[2] == a_on[2]
            and [(o.kill_turn, o.has_blue) for o in a_off[0]]
            == [(o.kill_turn, o.has_blue) for o in a_on[0]])
    check("A OFF changes nothing; ON adds a pool and nothing else",
          (same, all(not o.body_pool for o in a_off[0]),
           all(len(o.body_pool) == OPP.POD_BODY_POOL for o in a_on[0])),
          (True, True, True))

    pools = [o.body_pool for o in a_on[0]]
    again = [o.body_pool for o in OPP.make_pod(dict(cfg, pod_bodies=True),
                                               77)[0]]
    flat = [b for p in pools for b in p]
    check("B pool ranges, per-seed repeat, per-opponent difference",
          (min(b.toughness for b in flat), max(b.toughness for b in flat),
           min(b.mv for b in flat), max(b.mv for b in flat),
           pools == again, pools[0] != pools[1]),
          (1, 6, 1, 4, True, True))

    g = rgame()
    o = g.opponents[0]
    o.creatures = 2.7
    two = list(OPP.pod_bodies(g, o))
    o.creatures = 3.1
    three = list(OPP.pod_bodies(g, o))
    o.creatures = 1.0
    one = list(OPP.pod_bodies(g, o))
    check("C bodies follow the count, newest leave first",
          (len(two), three[:2] == two, len(three), one),
          (2, True, 3, [POOL[0]]))

    seen = []
    g = rgame()
    g.on_pod_creature_deaths = lambda o, n: seen.append((o, n))
    o = g.opponents[0]
    o.creatures = 4.5
    n = OPP.kill_pod_bodies(g, o, lambda b: b.toughness <= 2)
    check("D the rule's bodies die, the fraction stays, the hook hears",
          (n, o.creatures, [b.toughness for b in o.bodies], seen),
          (2, 2.5, [3, 4], [(o, 2)]))

    gyre = find(LM, "Immolating Gyre")
    g = rgame()
    g.graveyard = [instant(i) for i in range(3)]
    o = g.opponents[0]                       # 4 bodies: t 1, 2, 3, 4
    expect = OPP.pod_left_for_gate(g, gyre, o)
    OPP.resolve_own_wipe(g, spare_own=True, card=gyre)
    check("E Gyre X=3 kills toughness 3 or less; the gate agreed",
          ([b.toughness for b in o.bodies], o.creatures, expect),
          ([4], 1.0, 1.0))

    wurm = find(RM, "Massacre Wurm")
    g = rgame()
    put(g, wurm)
    o = g.opponents[0]
    OPP.resolve_own_wipe(g, spare_own=True, card=wurm)
    check("F rendmaw Massacre Wurm: t<=2 die, 2 life each",
          ([b.toughness for b in o.bodies], o.life), ([3, 4], 36.0))

    culling = find(RM, "Culling Ritual")
    g = rgame()
    o = g.opponents[0]                       # mv 1, 3, 2, 4
    OPP.resolve_own_wipe(g, spare_own=True, card=culling)
    check("G Culling Ritual kills mana value 2 or less",
          [b.mv for b in o.bodies], [3, 4])

    promise = find(LM, "Promise of Loyalty")
    g = rgame()
    o = g.opponents[0]
    OPP.resolve_own_wipe(g, spare_own=True, card=promise)
    check("H Promise keeps the toughest",
          ([b.toughness for b in o.bodies], o.creatures), ([4], 1.0))

    seen = []
    g = rgame()
    g.on_pod_creature_deaths = lambda o, n: seen.append(n)
    for o in g.opponents:
        o.creatures = 3.0
    OPP.pod_wipe_board(g, g.opponents[0])
    check("I a pod wrath: every body an event, the count 0",
          (seen, g.opponents[0].creatures, g.opponents[0].bodies),
          ([3], 0.0, []))

    g = rgame(pod_bodies=False)
    g.graveyard = [instant(i) for i in range(3)]
    o = g.opponents[0]
    OPP.resolve_own_wipe(g, spare_own=True, card=gyre)
    check("J OFF: the count's share, as before", o.creatures, 2.0)

    revel = find(TM, "Revel in Riches")
    proc = find(TM, "Anointed Procession")
    deck, cmd = TM.build()
    g = ready(T.TivitGame(list(deck), cmd,
                          dict(DEFAULT_CFG, pod_bodies=True), 1))
    put(g, revel)
    put(g, proc)
    t0 = g.tokens["Treasure"]
    OPP.kill_pod_bodies(g, g.opponents[0], lambda b: b.toughness <= 2)
    check("K Revel: a Treasure per death, doubled",
          (g.tokens["Treasure"] - t0, g.m["revel_treasures"]), (4, 4))

    deck, cmd = KM.build()
    g = ready(K.KarlovGame(list(deck), cmd,
                           dict(DEFAULT_CFG, pod_bodies=True), 1))
    put(g, find(KM, "Blood Artist"))
    OPP.kill_pod_bodies(g, g.opponents[0], lambda b: b.toughness == 1)
    check("L karlov Blood Artist drains for a pod death",
          (g.m["artist_pod_drains"], g.your_life > 40.0), (1, True))

    deck, cmd = LM.build()
    g = ready(L.LoreholdGame(list(deck), cmd,
                             dict(DEFAULT_CFG, pod_bodies=True), 1))
    four = EN.Card(name="Four", types=frozenset({"Sorcery"}), cost={"gen": 4})
    g.graveyard = [four]
    L.volcanic_vision(g)
    check("M Volcanic Vision on a 4-drop kills toughness 4 or less",
          (g.opponents[0].bodies, g.m["vision_pod_killed"]), ([], 4))

    deck, cmd = SM.build()
    g = ready(SH.ShilgengarGame(list(deck), cmd,
                                dict(DEFAULT_CFG, pod_bodies=True), 1))
    swurm = find(SM, "Massacre Wurm")
    g.resolve(swurm)
    o = g.opponents[0]
    check("N shilgengar Wurm: 2 life per death, once",
          ([b.toughness for b in o.bodies], o.life, g.m["wurm_drains"]),
          ([3, 4], 36.0, 2))

    g = rgame()
    o = g.opponents[0]
    EN.resolve_wipe_spell(g, wurm)           # the Wurm is NOT on g.board
    check("O a Wurm cast from hand drains for its own -2/-2",
          ([b.toughness for b in o.bodies], o.life), ([3, 4], 36.0))

    g = rgame()
    o = g.opponents[0]
    o.creatures = 2.6
    OPP.kill_pod_count(g, o, 4)
    check("P an edict past the board leaves 0", o.creatures, 0.0)

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("The pod's creatures as bodies (item 24, change 1)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_kill = OPP.kill_pod_bodies
    real_vision = L.volcanic_vision

    def silent_kill(g, o, dies=None):
        hook = getattr(g, "on_pod_creature_deaths", None)
        g.on_pod_creature_deaths = None
        try:
            return real_kill(g, o, dies)
        finally:
            if hook is not None:
                g.on_pod_creature_deaths = hook
            else:
                del g.on_pod_creature_deaths

    def oldest_first(g, o):
        n = int(o.creatures + 1e-9)
        pool = o.body_pool
        while len(o.bodies) < n and pool:
            o.bodies.append(pool[o.next_body % len(pool)])
            o.next_body += 1
        del o.bodies[:max(0, len(o.bodies) - n)]
        return o.bodies

    def gate_legacy(g, card, o):
        return OPP.own_wipe_pod_left(g, card, o.creatures)

    def zero_board(g, o):
        o.creatures = 0.0

    real_count = OPP.kill_pod_count

    def edict_fraction(g, o, n, biggest=True):
        keep = o.creatures
        killed = real_count(g, o, n, biggest)
        o.creatures = max(0.0, keep - killed)
        return killed

    def vision_no_damage(g):
        cfg = g.cfg
        g.cfg = dict(cfg, pod_bodies=False)
        try:
            real_vision(g)
        finally:
            g.cfg = cfg

    muts = {
        "kill_pod_bodies never tells the hook":
            ({"D", "F", "I", "K", "L", "N", "O"}, OPP, "kill_pod_bodies",
             silent_kill),
        "every own sweeper kills every body":
            ({"E", "F", "G", "H", "O"}, OPP, "own_wipe_body_rule",
             lambda g, card: None),
        "bodies leave oldest-first":
            ({"C"}, OPP, "pod_bodies", oldest_first),
        "the wipe gate ignores bodies":
            ({"E"}, OPP, "pod_left_for_gate", gate_legacy),
        "an opponent's wrath zeroes without events":
            ({"I"}, OPP, "pod_wipe_board", zero_board),
        "Volcanic Vision's damage half is gone":
            ({"M"}, L, "volcanic_vision", vision_no_damage),
        "the entering source is not named":
            ({"O"}, EN, "resolve_wipe_spell",
             lambda g, card: OPP.resolve_own_wipe(
                 g, spare_own="onesided" in card.tags, card=card)),
        "an edict leaves the fraction":
            ({"P"}, OPP, "kill_pod_count", edict_fraction),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        orig = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, orig)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
