#!/usr/bin/env python3
"""§0z186 (queue item 36): your TAPPED creatures do not block on the pod's
turns; vigilance keeps an attacker untapped; tivit's attackers tap; and the
pilot holds blockers back from a crack-back that would kill.

    python -m tests.test_untapped_blockers
    python -m tests.test_untapped_blockers --mutate   # 6 mutations, exact sets

`opponents.combat_share` aims each opponent's attack by 1 / (1 + blockers),
and its blockers were every creature you control. CR 508.1f taps an
attacker, 509.1a lets only an untapped creature block, and 502.3 untaps
yours only in your untap step. Each case builds a game by hand: a karlov,
tivit or shilgengar game with an empty battlefield and the pod set.

CASES
  A  your blockers are your untapped creatures: three, two tapped -> one,
     and the two are counted (`tapped_not_blocking`)
  B  NEIGHBOUR: `untapped_blockers=False` counts all three
  C  vigilance: Sun Titan (the generated set) yes, a vanilla body no, a token
     made with it yes, Voice of the Blessed at four counters yes and three no
  D  a vigilant attacker does not tap; under the switch off it does
  E  tivit's attackers tap
  F  NEIGHBOUR: tivit with the switch off leaves them untapped, as it did
  G  hold-back: with a crack-back that kills, the weakest attackers stay home
     -- the fewest that save you, and no fewer
  H  hold-back sends everything when the crack-back does not kill
  I  hold-back sends everything when the swing's damage through covers every
     opponent's life
  J  NEIGHBOUR: `hold_back=False` sends everything into a lethal crack-back
  K  asking changes nothing: the metrics and every tapped flag are as they
     were, but for `held_back` and `hold_back_turns`
  L  THE ADOPTED PAD (§0z191): with `hold_back_pad` at its default, 10, a
     crack-back that would leave you at 10 or less holds the weakest home;
     pad 0 sends all three into the same table

G-K are §0z186's mechanism at `hold_back_pad=0` (their life totals sit
between pad 0's thresholds), so `lethal_game` pins it; L alone reads the
default.

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  untapped_blockers=False everywhere            -> A, D, E, G, K, L
  vigilant() is always False                    -> C, D
  hold_back=False everywhere                    -> G, K, L
  your_creatures counts tapped ones too         -> A, G, K, L  (K added
                                                   after the first run;
                                                   below)
  hold_back keeps the STRONGEST home first      -> G, L
  hold_back_pad=0 everywhere                    -> L

L AND THE SIXTH MUTATION WERE ADDED WITH §0z191 (2026-11-09), their sets
written before that run: L breaks under every mutation that stops the
hold-back firing (the first, third and fourth), under the fifth because its
stand-in reads pad 0 as §0z186's did, and under the sixth by construction.

THE FIRST RUN FAILED I, AND THE TEST WAS WRONG: its opponents held seven
creatures each, which chump the whole swing, so `damage_through` never
covered their life and the guard I is about was never asked. They hold one
each now -- no blocks, a crack-back still there. The expected sets above are
as first written.

THE FIRST MUTATION RUN DIFFERED TWICE, BOTH THE TEST'S. The fourth broke K
too, and the set above lacked it although its own reason -- nothing is held
-- is K's under the first and third: the derivation was wrong, not the code.
The fifth broke G, I and J: its stand-in had dropped `hold_back`'s mode
check and its win guard, so it broke I and J for reasons that are not the
order (§0z141's shape). The stand-in keeps both now and its set is as first
written.

UNMUTATED (§0z15): B, F, H, I and J are the neighbours. K breaks under the
first and third because a hold-back that never fires writes no
`held_back` -- K asserts the count it expects as well as the restore.
The fourth breaks G as well as A: with tapped attackers still counted as
blockers, the crack-back never looks lethal and nothing is held.
"""
import sys

import edhmc.engine as E
import edhmc.karlov as K
import edhmc.opponents as OPP
import edhmc.shilgengar as S
import edhmc.tivit as T
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG, POD_PRE_COMBAT
# The pre-flip pod, stated (§0z204): this file pins rules that live behind
# item 44's switches; the default pod's combat is pinned in
# test_attacker_deaths, test_you_block, test_rival_combat,
# test_pod_hold_back and test_predicted_bodies.
PRE_COMBAT_CFG = dict(DEFAULT_CFG, **POD_PRE_COMBAT)
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
KARLOV = build_pending("karlov")
TIVIT = build_pending("tivit")
SHIL = build_pending("shilgengar")


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg(**kw):
    return dict(PRE_COMBAT_CFG, watch=frozenset(), **{**EXTRA_CFG, **kw})


def body(power=2, tapped=False, name="Bear", vigilance=False):
    c = Card(name=name, types=frozenset({"Creature"}), power=power,
             toughness=2, vigilance=vigilance)
    return Permanent(card=c, sick=False, tapped=tapped, base_p=power,
                     base_t=2)


def named(deck, name):
    return next(c for c in deck[0] if c.name == name)


def game(cls=K.KarlovGame, deck=KARLOV, opp_creatures=7.0, opp_life=1e9,
         turn=5, **kw):
    lst, cmd = deck
    g = cls(list(lst), cmd, cfg(**kw), 3)
    g.opening_hand()
    g.board = E.Board()
    g.turn = turn
    for o in g.opponents:
        o.kill_turn, o.life, o.creatures = 99, float(opp_life), opp_creatures
    return g


def crack(g, send):
    """The pod's next round at you with `send` tapped (vigilance aside)."""
    snap = dict(g.m)
    saved = [(p, p.tapped) for p in send]
    for p in send:
        if not OPP.vigilant(g, p):
            p.tapped = True
    try:
        return OPP.predicted_chip(g)
    finally:
        for p, t in saved:
            p.tapped = t
        g.m.clear()
        g.m.update(snap)


def lethal_game(**kw):
    """Three attackers (power 1, 2, 5) and a life total between the crack-back
    with all three tapped and with only the weakest one tapped -- pad 0's
    thresholds, so the pad is pinned at 0 (§0z191 adopted 10)."""
    kw.setdefault("hold_back_pad", 0.0)
    g = game(**kw)
    bodies = [body(1, name="One"), body(2, name="Two"), body(5, name="Five")]
    g.board.extend(bodies)
    all_in = crack(g, bodies)
    one_home = crack(g, bodies[1:])
    g.your_life = (all_in + one_home) / 2.0
    return g, bodies


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    g.board.extend([body(), body(tapped=True), body(tapped=True)])
    check("A blockers are the untapped: one of three, two counted",
          (OPP.your_creatures(g), g.m["tapped_not_blocking"]), (1, 2))

    g = game(untapped_blockers=False)
    g.board.extend([body(), body(tapped=True), body(tapped=True)])
    check("B untapped_blockers=False counts all three",
          OPP.your_creatures(g), 3)

    g = game()
    titan = Permanent(card=named(KARLOV, "Sun Titan"), sick=False)
    voice = Permanent(card=named(KARLOV, "Voice of the Blessed"), sick=False)
    voice.counters = 4
    voice3 = Permanent(card=named(KARLOV, "Voice of the Blessed"), sick=False)
    voice3.counters = 3
    check("C vigilance: Titan, token, Voice at 4 yes; bear, Voice at 3 no",
          [OPP.vigilant(g, p) for p in (titan, body(), body(vigilance=True),
                                        voice, voice3)],
          [True, False, True, True, False])

    g = game()
    off = game(untapped_blockers=False)
    check("D a vigilant attacker does not tap; off, it does",
          (OPP.taps_to_attack(g, titan), OPP.taps_to_attack(off, titan)),
          (False, True))

    g = game(cls=T.TivitGame, deck=TIVIT, hold_back=False)
    bear = body()
    g.board.append(bear)
    T.combat(g)
    check("E tivit's attackers tap", bear.tapped, True)

    g = game(cls=T.TivitGame, deck=TIVIT, untapped_blockers=False)
    bear = body()
    g.board.append(bear)
    T.combat(g)
    check("F untapped_blockers=False: tivit leaves them untapped",
          bear.tapped, False)

    g, bodies = lethal_game()
    sent = OPP.hold_back(g, list(bodies))
    names = sorted(p.card.name for p in sent)
    check("G a lethal crack-back: the weakest stays home, and only it",
          (names, g.your_life - crack(g, sent) > 0), (["Five", "Two"], True))

    g, bodies = lethal_game()
    g.your_life = crack(g, bodies) + 5.0
    check("H no lethal crack-back: all three sent",
          len(OPP.hold_back(g, list(bodies))), 3)

    g, bodies = lethal_game(opp_life=1.0, opp_creatures=1.0)
    check("I a swing that can win: all three sent",
          len(OPP.hold_back(g, list(bodies))), 3)

    g, bodies = lethal_game(hold_back=False)
    check("J hold_back=False: all three sent into it",
          len(OPP.hold_back(g, list(bodies))), 3)

    g, bodies = lethal_game()
    before = {k: v for k, v in g.m.items()}
    taps = [p.tapped for p in g.board]
    OPP.hold_back(g, list(bodies))
    after = {k: v for k, v in g.m.items()
             if k not in ("held_back", "hold_back_turns")}
    check("K asking changes nothing but the hold-back's own counts",
          (after == before, [p.tapped for p in g.board] == taps,
           g.m["held_back"], g.m["hold_back_turns"]), (True, True, 1, 1))

    def pad_table(**kw):
        g = game(**kw)
        bodies = [body(1, name="One"), body(2, name="Two"),
                  body(5, name="Five")]
        g.board.extend(bodies)
        g.your_life = (crack(g, bodies) + crack(g, bodies[1:])) / 2.0 + 10.0
        return g, bodies
    g, bodies = pad_table()
    names = sorted(p.card.name for p in OPP.hold_back(g, list(bodies)))
    g0, bodies0 = pad_table(hold_back_pad=0.0)
    check("L the default pad, 10: the weakest stays home; pad 0 sends all",
          (names, len(OPP.hold_back(g0, list(bodies0)))),
          (["Five", "Two"], 3))
    return set(FAIL)


def _counts_tapped(g):
    ask = getattr(g, "counts_as_creature", None)
    return sum(1 for p in g.board
               if (ask(p) if ask else OPP.is_creature_now(g, p)))


def _strongest_first(g, attackers):
    """`hold_back` with the home order reversed: strongest kept first. Every
    guard of the real one is kept (the first stand-in dropped two)."""
    mode = g.cfg.get("hold_back", "lethal")
    mode = {True: "lethal", False: "none"}.get(mode, mode)
    if (mode == "none" or not OPP.untapped_blockers(g) or not attackers
            or not g.cfg.get("opponents", True) or g.result is not None):
        return attackers
    living_life = sum(o.life for o in OPP.living(g))
    if living_life <= 0 or OPP.damage_through(g, attackers) >= living_life:
        return attackers
    life = g.your_life
    if life - crack(g, attackers) > 0:
        return attackers
    home = []
    for p in sorted((q for q in attackers if not OPP.vigilant(g, q)),
                    key=g.power_of, reverse=True):
        home.append(p)
        send = [q for q in attackers if not any(q is h for h in home)]
        if life - crack(g, send) > 0:
            g.m["held_back"] += len(home)
            g.m["hold_back_turns"] += 1
            return send
    return attackers


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z186: untapped blockers, vigilance, the hold-back\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "untapped_blockers=False everywhere":
            ({"A", "D", "E", "G", "K", "L"}, None,
             {"untapped_blockers": False}),
        "vigilant() is always False":
            ({"C", "D"}, (OPP, "vigilant", lambda g, p: False), {}),
        "hold_back=False everywhere":
            ({"G", "K", "L"}, None, {"hold_back": False}),
        "your_creatures counts tapped ones too":
            ({"A", "G", "K", "L"}, (OPP, "your_creatures", _counts_tapped),
             {}),
        "hold_back keeps the STRONGEST home first":
            ({"G", "L"}, (OPP, "hold_back", _strongest_first), {}),
        "hold_back_pad=0 everywhere":
            ({"L"}, None, {"hold_back_pad": 0.0}),
    }
    bad = 0
    for label, (want, patch, extra) in muts.items():
        print(f"-- {label}")
        EXTRA_CFG = extra
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
