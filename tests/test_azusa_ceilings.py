#!/usr/bin/env python3
"""§0z257 and §0z258: Terastodon's ETB on every entry; Craterhoof's pump
and Bane of Progress's wipe to their text (azusa).

    python -m tests.test_azusa_ceilings
    python -m tests.test_azusa_ceilings --mutate   # 6 mutations, exact sets

    Terastodon: "When this creature enters, you may destroy up to three
    target noncreature permanents. For each permanent put into a graveyard
    this way, its controller creates a 3/3 green Elephant creature token."
    Craterhoof Behemoth: "When this creature enters, creatures you control
    gain trample and get +X/+X until end of turn, where X is the number of
    creatures you control."
    Bane of Progress: "When this creature enters, destroy all artifacts and
    enchantments. Put a +1/+1 counter on this creature for each permanent
    destroyed this way."                               (Scryfall 2026-11-25)

CASES (your turn 3; opponent 0 holds the pieces, out since round 0)
  T1 Terastodon PUT in (`etb(cast=False)`), an artifact piece out: it leaves
  T2 Terastodon CAST (`etb(cast=True)`): no entry answer -- `countered`'s
  T3 a COPY (`is_copy=True`): it answers
  T4 NEIGHBOUR: terastodon_etb_returns=False -- T1's entry, nothing leaves
  K  `check_etb_answer_knobs`: the real set passes; a missing switch raises
  C1 Craterhoof: a creature present gets +X; a token made after gets 0
  C2 ... the present one tramples, the token made after does not
  C3 NEIGHBOUR: craterhoof_snapshot=False -- the later token gets +X too
  B1 Bane: the pod's artifact and enchantment pieces leave, the creature
     piece stays; each is a counter
  B2 ... two Treasures, no other mana: the pilot floats them (no counter)
  B3 ... two Clues and {2} untapped: one cracked, one destroyed (a counter)
  B4 ... Scene of the Crime dies, to the graveyard, a counter
  B5 NEIGHBOUR: bane_text=False -- the old rule: pieces, Treasures, Clues
     and the artifact land all stay, no counter
  Q  §0z259: three Clues and {2} untapped -- `crack_clues` cracks ONE, not
     every Clue for the same {2}

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  every switch off                               -> T1, T3, C1, C2, B1, B2, B3, B4
  bane_respond does nothing                      -> B2, B3
  wipe_threat_pieces does nothing                -> B1
  craterhoof_reaches always True                 -> C2
  ETB_ANSWER_KNOBS empty                         -> T1, T3, K
  clue_pay_once=False everywhere                 -> B3, Q

UNMUTATED (§0z15): T2, T4, C3 and B5 are neighbours.
"""
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.azusa import AzusaGame
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
OFF = {"terastodon_etb_returns": False, "craterhoof_snapshot": False,
       "bane_text": False}
DECK, CMD = build_pending("azusa")
CREATURE = OPP.ThreatPiece("Creature", 3, 3, 1)
ARTIFACT = OPP.ThreatPiece("Artifact", 0, 3, 1)
ENCHANTMENT = OPP.ThreatPiece("Enchantment", 0, 3, 1)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(g, name):
    for zone in (g.library, g.hand, g.graveyard):
        for c in zone:
            if c.name == name:
                EN.remove_card(zone, c)
                return c
    raise LookupError(name)


def game(pieces=(), **cfg):
    g = AzusaGame(list(DECK), CMD,
                  dict(DEFAULT_CFG, turns=20, watch=frozenset(),
                       **{**EXTRA_CFG, **cfg}), 1234)
    g.opening_hand()
    g.library.extend(g.hand)
    g.hand = []
    g.board = EN.Board()
    g.bonus_mana = []
    g.clues = 0
    g.turn = 3
    for i, o in enumerate(g.opponents):
        o.pieces = tuple(pieces) if i == 0 else ()
        o.piece_lands = [0] * len(o.pieces)
    return g


def out(g):
    o = g.opponents[0]
    return tuple(o.pieces[k].type for k in OPP.present_pieces(g, o))


def enter(g, name, **kw):
    c = take(g, name)
    p = EN.Permanent(card=c, sick=True)
    g.board.append(p)
    g.etb(c, p, **kw)
    return p


def bear(g):
    p = EN.Permanent(card=EN.Card(name="Test Bear",
                                  types=frozenset({"Creature"}),
                                  power=2, toughness=2), sick=False)
    g.board.append(p)
    return p


def forest(g):
    g.board.append(EN.Permanent(card=take(g, "Forest"), sick=False))


def raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game((ARTIFACT,))
    enter(g, "Terastodon", cast=False)
    check("T1 Terastodon put in: the artifact piece leaves", out(g), ())

    g = game((ARTIFACT,))
    enter(g, "Terastodon", cast=True)
    check("T2 Terastodon cast: no entry answer here",
          (out(g), g.m["entry_answers"]), (("Artifact",), 0))

    g = game((ARTIFACT,))
    enter(g, "Terastodon", is_copy=True)
    check("T3 a copy answers", out(g), ())

    g = game((ARTIFACT,), terastodon_etb_returns=False)
    enter(g, "Terastodon", cast=False)
    check("T4 terastodon_etb_returns=False: nothing leaves",
          out(g), ("Artifact",))

    check("K the switch set is checked against the census",
          (not raises(AZ.check_etb_answer_knobs),
           raises(lambda: AZ.check_etb_answer_knobs(
               knobs={}, run_by=("Terastodon",)))),
          (True, True))

    g = game()
    old = bear(g)
    enter(g, "Craterhoof Behemoth")
    x = g.craterhoof_bonus
    new = g.make_tokens(1, 1, 1, "Insect")[0]
    check("C1 Craterhoof: +X to the bear, 0 to the later token",
          (x, g._pump(old), g._pump(new)), (2, 2, 0))
    check("C2 the bear tramples, the later token does not",
          (OPP.trample_of(g, old), OPP.trample_of(g, new)), (True, False))

    g = game(craterhoof_snapshot=False)
    bear(g)
    enter(g, "Craterhoof Behemoth")
    new = g.make_tokens(1, 1, 1, "Insect")[0]
    check("C3 craterhoof_snapshot=False: the later token gets +X too",
          g._pump(new), 2)

    g = game((ARTIFACT, ENCHANTMENT, CREATURE))
    bane = enter(g, "Bane of Progress")
    check("B1 Bane: the A/E pieces leave, the creature stays; 2 counters",
          (out(g), bane.counters), (("Creature",), 2))

    g = game()
    g.bonus_mana = [AZ.TreasureMana(frozenset("G")) for _ in range(2)]
    bane = enter(g, "Bane of Progress")
    floated = sum(1 for f in g.bonus_mana
                  if type(f) is AZ.FloatingMana and not f.tapped)
    check("B2 two Treasures: floated, no counter",
          (floated, bane.counters, g.m["bane_treasures"]), (2, 0, 0))

    g = game()
    forest(g)
    forest(g)
    g.clues = 2
    bane = enter(g, "Bane of Progress")
    check("B3 two Clues, {2} up: one cracked, one destroyed",
          (g.m["bane_clues_cracked"], g.m["bane_clues"], bane.counters),
          (1, 1, 1))

    g = game()
    scene = take(g, "Scene of the Crime")
    g.board.append(EN.Permanent(card=scene, sick=False))
    bane = enter(g, "Bane of Progress")
    check("B4 Scene of the Crime dies to the graveyard, a counter",
          (scene in g.graveyard, bane.counters), (True, 1))

    g = game((ARTIFACT, ENCHANTMENT), bane_text=False)
    g.bonus_mana = [AZ.TreasureMana(frozenset("G"))]
    g.clues = 1
    scene = take(g, "Scene of the Crime")
    g.board.append(EN.Permanent(card=scene, sick=False))
    bane = enter(g, "Bane of Progress")
    check("B5 bane_text=False: the old rule, nothing of these dies",
          (out(g), len(g.bonus_mana), g.clues,
           any(p.card is scene for p in g.board), bane.counters),
          (("Artifact", "Enchantment"), 1, 1, True, 0))
    g = game()
    forest(g)
    forest(g)
    g.clues = 3
    g.crack_clues(g.available_mana())
    check("Q crack_clues: {2} cracks one Clue of three",
          (g.clues, g.m["cards_drawn"]), (2, 1))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z257, §0z258: azusa's ceilings\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_respond = AzusaGame.bane_respond
    real_wtp = OPP.wipe_threat_pieces
    real_reaches = AzusaGame.craterhoof_reaches
    real_knobs = dict(AZ.ETB_ANSWER_KNOBS)

    def set_cfg(v):
        EXTRA_CFG.clear()
        EXTRA_CFG.update(v)

    def set_respond(v):
        AzusaGame.bane_respond = v

    def set_wtp(v):
        OPP.wipe_threat_pieces = v

    def set_reaches(v):
        AzusaGame.craterhoof_reaches = v

    def set_knobs(v):
        AZ.ETB_ANSWER_KNOBS.clear()
        AZ.ETB_ANSWER_KNOBS.update(v)

    muts = {
        "every switch off": (
            {"T1", "T3", "C1", "C2", "B1", "B2", "B3", "B4"}, set_cfg, OFF, {}),
        "bane_respond does nothing": (
            {"B2", "B3"}, set_respond, lambda self: None, real_respond),
        "wipe_threat_pieces does nothing": (
            {"B1"}, set_wtp, lambda g, card, scope=None, x=None: 0, real_wtp),
        "craterhoof_reaches always True": (
            {"C2"}, set_reaches, lambda self, perm: True, real_reaches),
        "ETB_ANSWER_KNOBS empty": (
            {"T1", "T3", "K"}, set_knobs, {}, real_knobs),
        "clue_pay_once=False everywhere": (
            {"B3", "Q"}, set_cfg, {"clue_pay_once": False}, {}),
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
