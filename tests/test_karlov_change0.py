#!/usr/bin/env python3
"""Item 24's change 0 in karlov: four cards that were KNOWN_BLIND for want of
code, not for want of a model.

    python -m tests.test_karlov_change0
    python -m tests.test_karlov_change0 --mutate   # 12 mutations

    Sun Titan {4}{W}{W} 6/6   (Scryfall, every text verified 2026-10-13)
    Vigilance / Whenever this creature enters or attacks, you may return
    target permanent card with mana value 3 or less from your graveyard to
    the battlefield.
    Soulmender {W} 1/1
    {T}: You gain 1 life.
    Phyrexian Reclamation {B} Enchantment
    {1}{B}, Pay 2 life: Return target creature card from your graveyard to
    your hand.
    Umezawa's Jitte {2} Legendary Artifact -- Equipment
    Whenever equipped creature deals combat damage, put two charge counters
    on Umezawa's Jitte. / Remove a charge counter from Umezawa's Jitte:
    Choose one -- Equipped creature gets +2/+2 until end of turn; Target
    creature gets -1/-1 until end of turn; You gain 2 life. / Equip {2}

CASES
  A  Sun Titan resolving returns the highest-priority permanent card of mana
     value 3 or less (a 3-drop over a 1-drop)
  B  ... and nothing when the only permanent card is mana value 4
  C  ... a nonland over a land, whatever the priorities
  D  ... and a land, alone, comes back as a land
  E  Sun Titan ATTACKING returns a card
  F  a creature it returns ENTERS: Soul Warden gains 1
  G  Soulmender at the end step: tapped, one lifegain event of 1
  H  ... a summoning-sick Soulmender is not tapped
  I  Soulmender never attacks; under `soulmender_tap=False` it attacks and
     the end step taps nothing
  J  Reclamation at the end step: a creature card to hand, 2 life paid
  K  ... not at 12 life (12 - 2 is not above the floor of 10)
  L  ... before the second main, only when the mana also recasts it: two
     lands and a 1-drop is nothing; three lands returns it
  M  the Jitte is equipped on the attacker, for {2}
  N  the holder attacks: two counters, both spent as two 2-life events
  O  a holder that did not attack gets no counters
  P  a Jitte that left and came back is a NEW object (CR 400.7, §0z136):
     the old holder attacks and the new Jitte gets no counters
  Q  ... and equipping the new Jitte pays {2} again

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  sun_titan_pick finds nothing             -> A, C, D, E, F
  sun_titan_pick has no mana-value cap     -> B
  sun_titan_pick prefers a land            -> C
  creature_entered does nothing            -> F
  soulmender_step does nothing             -> G
  may_attack lets Soulmender attack        -> I
  Reclamation ignores its life floor       -> K
  Reclamation's recast window ignores the card's cost   -> L
  jitte_combat does nothing                -> N, P   (P added after the
                                       run, §0z14: written as N alone, but
                                       P also reads that the stale holder
                                       is cleared, which `jitte_combat`'s
                                       call to `jitte_holder` does)
  jitte_combat credits a holder that stayed home        -> O
  jitte_equip does nothing                 -> M, N, Q
  jitte_holder keeps the old holder        -> P, Q    (§0z136; written
                                                       before the run)

UNMUTATED, and written down (§0z15): the attack half of Sun Titan (E) has no
seam of its own -- it calls the same `sun_titan` the enter half does, so the
first mutation breaks both. H's sickness gate and J's end-step window are
covered only by their plain runs.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
from edhmc.decks import karlov_v2 as KM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


KDECK, KCMD = KM.build()
FILLER = [EN.Card(name=f"Filler {i}", types=frozenset({"Sorcery"}),
                  cost={"gen": 1}) for i in range(30)]


def kcard(name):
    return next(c for c in KDECK if c.name == name)


def kgame(*perms, life=40.0, **cfg):
    g = K.KarlovGame(list(KDECK), KCMD, dict(DEFAULT_CFG, turns=20, **cfg), 4242)
    g.board = EN.Board()
    g.hand = []
    g.graveyard = []
    g.library = list(FILLER)
    g.your_life = life
    g.turn = 6
    for i, o in enumerate(g.opponents):
        o.creatures = 0.0
        o.life = 40.0
    for p in perms:
        g.board.append(p if isinstance(p, EN.Permanent)
                       else EN.Permanent(card=p, sick=False))
    return g


def lands(n, name="Swamp"):
    return [EN.Permanent(card=kcard(name), sick=False) for _ in range(n)]


def creature(name, cost, priority, p=2, t=2):
    return EN.Card(name=name, types=frozenset({"Creature"}), cost=cost,
                   power=p, toughness=t, priority=priority)


def on_board(g, card):
    return any(p.card is card for p in g.board)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    titan = kcard("Sun Titan")

    # -- Sun Titan --------------------------------------------------------
    three = creature("Three", {"gen": 2, "W": 1}, priority=9)
    one = creature("One", {"W": 1}, priority=2)
    g = kgame()
    g.graveyard = [one, three]
    K.enter_permanent(g, titan)
    check("A Titan returns the higher-priority 3-drop",
          (on_board(g, three), on_board(g, one), g.m["sun_titan_returns"]),
          (True, False, 1))

    four = creature("Four", {"gen": 3, "W": 1}, priority=9)
    g = kgame()
    g.graveyard = [four]
    K.enter_permanent(g, titan)
    check("B a mana value 4 card is not returned",
          (on_board(g, four), g.m["sun_titan_returns"]), (False, 0))

    plains = kcard("Plains")
    g = kgame()
    g.graveyard = [plains, one]
    K.enter_permanent(g, titan)
    check("C a nonland over a land",
          (on_board(g, one), on_board(g, plains)), (True, False))

    g = kgame()
    g.graveyard = [plains]
    K.enter_permanent(g, titan)
    check("D a land alone comes back as a land",
          (on_board(g, plains), len(g.graveyard)), (True, 0))

    g = kgame(titan)
    g.graveyard = [three]
    K.combat(g)
    check("E Titan attacking returns a card",
          (on_board(g, three), g.m["sun_titan_returns"]), (True, 1))

    g = kgame(kcard("Soul Warden"))
    g.graveyard = [three]
    life0 = g.your_life
    K.enter_permanent(g, titan)
    # Soul Warden sees the Titan AND the 3-drop enter: two events of 1.
    check("F a returned creature enters (Soul Warden)",
          g.your_life - life0, 2.0)

    # -- Soulmender ------------------------------------------------------
    mender = kcard("Soulmender")
    g = kgame(mender)
    life0 = g.your_life
    K.soulmender_step(g)
    check("G Soulmender taps for one lifegain event",
          (g.your_life - life0, g.m["soulmender_taps"], g.board[0].tapped),
          (1.0, 1, True))

    g = kgame(EN.Permanent(card=mender, sick=True))
    K.soulmender_step(g)
    check("H a sick Soulmender is not tapped", g.m["soulmender_taps"], 0)

    g = kgame(mender)
    stays = K.may_attack(g, g.board[0])
    g2 = kgame(mender, soulmender_tap=False)
    K.soulmender_step(g2)
    check("I Soulmender stays home; the naive pilot attacks with it",
          (stays, K.may_attack(g2, g2.board[0]), g2.m["soulmender_taps"]),
          (False, True, 0))

    # -- Phyrexian Reclamation -------------------------------------------
    recl = kcard("Phyrexian Reclamation")
    g = kgame(recl, *lands(2))
    g.graveyard = [three]
    K.reclamation_step(g, recast=False)
    check("J Reclamation: card to hand, 2 life paid",
          (three in g.hand, g.your_life, g.m["reclamation_returns"]),
          (True, 38.0, 1))

    g = kgame(recl, *lands(2), life=12.0)
    g.graveyard = [three]
    K.reclamation_step(g, recast=False)
    check("K not at 12 life (the floor is 10)",
          (three in g.hand, g.your_life), (False, 12.0))

    blk = creature("Black One", {"B": 1}, priority=5)
    g = kgame(recl, *lands(2))
    g.graveyard = [blk]
    K.reclamation_step(g, recast=True)
    g3 = kgame(recl, *lands(3))
    g3.graveyard = [blk]
    K.reclamation_step(g3, recast=True)
    check("L the recast window needs the card's cost too",
          (blk in g.hand, blk in g3.hand), (False, True))

    # -- Umezawa's Jitte --------------------------------------------------
    jitte = kcard("Umezawa's Jitte")
    body = creature("Body", {"gen": 2}, priority=5, p=3, t=3)
    g = kgame(jitte, body, *lands(2))
    K.jitte_equip(g)
    holder = g.jitte_on
    check("M the Jitte is equipped on the attacker, for {2}",
          (holder is not None and holder.card is body, g.m["jitte_equips"],
           sum(1 for p in g.board if p.card.is_land and p.tapped)),
          (True, 1, 2))

    g = kgame(jitte, body, *lands(2))
    K.jitte_equip(g)
    life0 = g.your_life
    K.combat(g)
    check("N the holder attacks: two counters, two 2-life events",
          (g.m["jitte_counters"], g.m["jitte_life_events"],
           g.your_life - life0, g.jitte_counters),
          (2, 2, 4.0, 0))

    g = kgame(jitte, body)
    g.jitte_on = g.board[1]
    g.jitte_bound = g.board[0]        # equipped from THIS Jitte (§0z136)
    K.jitte_combat(g, [])
    check("O a holder that stayed home gets nothing",
          (g.m["jitte_counters"], g.jitte_counters), (0, 0))

    # The pod destroys the Jitte; Sun Titan returns it. A new object.
    def returned_jitte(**cfg):
        g = kgame(jitte, body, *lands(4), **cfg)
        K.jitte_equip(g)
        holder = g.jitte_on
        for p in g.board:
            if p.card.is_land:
                p.tapped = False
        g.board.remove(K.jitte_perm(g))
        g.board.append(EN.Permanent(card=jitte, sick=False))
        return g, holder

    g, holder = returned_jitte()
    K.jitte_combat(g, [holder])
    check("P a returned Jitte is not on the old holder: no counters",
          (g.m["jitte_counters"], g.jitte_on), (0, None))

    g, holder = returned_jitte()
    K.jitte_equip(g)
    check("Q ... and equipping it again pays {2}",
          (g.m["jitte_equips"], g.jitte_on is holder,
           sum(1 for p in g.board if p.card.is_land and p.tapped)),
          (2, True, 2))

    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Sun Titan, Soulmender, Phyrexian Reclamation, Umezawa's Jitte "
              "(karlov, item 24)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_pick = K.sun_titan_pick
    real_recl = K.reclamation_step
    real_jcombat = K.jitte_combat

    def stale_holder(g):          # the first version: the holder alone
        holder = getattr(g, "jitte_on", None)
        return holder if K.jitte_perm(g) is not None else None

    def no_cap(graveyard, exclude=()):
        pool = [c for c in graveyard if c.is_permanent]
        return max(pool, key=lambda c: (not c.is_land, c.priority, c.mv),
                   default=None)

    def land_first(graveyard, exclude=()):
        pool = [c for c in graveyard if c.is_permanent and c.free_mv <= 3]
        return max(pool, key=lambda c: (c.is_land, c.priority, c.mv),
                   default=None)

    def no_floor(g, recast):
        g.cfg = dict(g.cfg, reclamation_life_floor=-999)
        real_recl(g, recast)

    def no_recast_check(g, recast):
        real_recl(g, False)

    def credit_home(g, attackers):
        real_jcombat(g, list(attackers) + [g.jitte_on])

    muts = {
        "sun_titan_pick finds nothing":
            ({"A", "C", "D", "E", "F"}, K, "sun_titan_pick",
             lambda graveyard, exclude=(): None),
        "sun_titan_pick has no mana-value cap":
            ({"B"}, K, "sun_titan_pick", no_cap),
        "sun_titan_pick prefers a land":
            ({"C"}, K, "sun_titan_pick", land_first),
        "creature_entered does nothing":
            ({"F"}, K, "creature_entered", lambda g, *a, **k: None),
        "soulmender_step does nothing":
            ({"G"}, K, "soulmender_step", lambda g: None),
        "may_attack lets Soulmender attack":
            ({"I"}, K, "may_attack",
             lambda g, p: (K.is_creature_now(g, p.card) and not p.tapped
                           and not p.sick and not K.OPP.holds_back(g, p))),
        "Reclamation ignores its life floor":
            ({"K"}, K, "reclamation_step", no_floor),
        "Reclamation's recast window ignores the card's cost":
            ({"L"}, K, "reclamation_step", no_recast_check),
        "jitte_combat does nothing":
            ({"N", "P"}, K, "jitte_combat", lambda g, attackers: None),
        "jitte_combat credits a holder that stayed home":
            ({"O"}, K, "jitte_combat", credit_home),
        "jitte_equip does nothing":
            ({"M", "N", "Q"}, K, "jitte_equip", lambda g: None),
        "jitte_holder keeps the old holder":
            ({"P", "Q"}, K, "jitte_holder", stale_holder),
    }
    bad = 0
    for label, (want, mod, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(mod, name)
        setattr(mod, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(mod, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
