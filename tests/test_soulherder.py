#!/usr/bin/env python3
"""§0z269: Soulherder's +1/+1 counter (tivit, §0z207 item 9).

    python -m tests.test_soulherder
    python -m tests.test_soulherder --mutate   # 5 mutations, exact sets

    "Whenever a creature is exiled from the battlefield, put a +1/+1
    counter on this creature. At the beginning of your end step, you may
    exile another target creature you control, then return that card to
    the battlefield under its owner's control."
                                   ({1}{W}{U} 1/1; Scryfall 2026-11-27)

Only the end-step blink was modelled. `tivit.soulherder_counters` is the
first ability, read by every blink (`blink_tivit`) and, through
`opponents.piece_exiled`, by your exile answers on a creature route piece.

CASES (tivit; Tivit and Soulherder on the battlefield unless said)
  A  one blink: one counter, Soulherder reads 2/2
  B  two blinks: two counters
  C  no Soulherder: a blink counts no reach
  D  NEIGHBOUR: soulherder_counters=False -- no counter, the reach counted
  E  no Tivit on the battlefield: the blink does nothing, no counter
  F  Path to Exile (`answer_pieces`) on a creature piece: one counter
  G  Council's Judgment exiles an ARTIFACT piece: no counter
  H  Void Rend (destroy) on a creature piece: no counter
  I  Council's Judgment (`voting.judgment`, vote control) on a creature
     piece: one counter

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  the counter never placed (the reach still counted)  -> A, B, F, I
  piece_exiled ignores the census (any removal exiles) -> H
  piece_exiled ignores the piece's type                -> G
  voting.judgment never tells piece_exiled             -> I
  the game hook missing (no on_creature_exiled)        -> F, I

UNMUTATED (§0z15): C, D and E are the trigger's off sides.

BLIND HERE: the response (`respond_to_pieces`) and end-step
(`end_step_answers`) sites call `piece_exiled` the same way as
`answer_pieces`; no case drives them.
"""
import sys

import edhmc.opponents as OPP
import edhmc.tivit as TI
import edhmc.voting as V
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
HERDER = "Soulherder"
CREATURE = OPP.ThreatPiece("Creature", 3, 3, 1)
ARTIFACT = OPP.ThreatPiece("Artifact", 0, 3, 1)


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(herder=True, tivit=True, pieces=(), **cfg):
    board = ([B.LISTS["tivit"][1]] if tivit else []) + (
        [B.card("tivit", HERDER)] if herder else [])
    g = B.fresh("tivit", board=board, **{**EXTRA_CFG, **cfg})
    g.turn = 3
    for i, o in enumerate(g.opponents):
        o.pieces = tuple(pieces) if i == 0 else ()
        o.piece_lands = [0] * len(o.pieces)
    return g


def herder(g):
    p = next((p for p in g.board if p.card.name == HERDER), None)
    return None if p is None else (p.counters, g.power_of(p),
                                   g.toughness_of(p))


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game()
    TI.blink_tivit(g, "Ephemerate")
    check("A one blink: one counter, a 2/2", herder(g), (1, 2, 2))
    TI.blink_tivit(g, "Teleportation Circle")
    check("B two blinks: two counters", herder(g)[0], 2)

    g = game(herder=False)
    TI.blink_tivit(g, "Ephemerate")
    check("C no Soulherder: no reach", g.m["soulherder_exiles_seen"], 0)

    g = game(soulherder_counters=False)
    TI.blink_tivit(g, "Ephemerate")
    check("D soulherder_counters=False: no counter, the reach counted",
          (herder(g)[0], g.m["soulherder_exiles_seen"]), (0, 1))

    g = game(tivit=False)
    TI.blink_tivit(g, "Ephemerate")
    check("E no Tivit: no blink, no counter", herder(g)[0], 0)

    g = game(pieces=(CREATURE,))
    OPP.answer_pieces(g, "Path to Exile", OPP.ANSWERS["Path to Exile"])
    check("F Path on a creature piece: one counter", herder(g)[0], 1)

    g = game(pieces=(ARTIFACT,))
    g.illusion_active = True                 # vote control: the vote is won
    V.judgment(g)
    check("G Judgment on an artifact piece: no counter",
          (herder(g)[0], g.m["vote_answers_won"]), (0, 1))

    g = game(pieces=(CREATURE,))
    OPP.answer_pieces(g, "Void Rend", OPP.ANSWERS["Void Rend"])
    check("H Void Rend destroys: no counter",
          (herder(g)[0], g.m["threat_pieces_removed"]), (0, 1))

    g = game(pieces=(CREATURE,))
    g.illusion_active = True
    V.judgment(g)
    check("I Judgment on a creature piece: one counter", herder(g)[0], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z269: Soulherder's +1/+1 counter\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_counters = TI.soulherder_counters
    real_exiled = OPP.piece_exiled
    real_hook = TI.TivitGame.on_creature_exiled
    from edhmc.decks import _removal

    def no_counter(g, n=1):
        if g.has(HERDER):
            g.m["soulherder_exiles_seen"] += n

    def any_removal(g, o, k, name):
        hook = getattr(g, "on_creature_exiled", None)
        if hook is not None and o.pieces[k].type == "Creature":
            hook(1)

    def any_type(g, o, k, name):
        hook = getattr(g, "on_creature_exiled", None)
        entry = _removal.INTERACTION.get(name)
        if hook is not None and entry is not None and "exile" in entry[2]:
            hook(1)

    def judgment_silent(g, o, k, name):
        if name != "Council's Judgment":
            real_exiled(g, o, k, name)

    def set_counters(v):
        TI.soulherder_counters = v

    def set_exiled(v):
        OPP.piece_exiled = v

    def set_hook(v):
        TI.TivitGame.on_creature_exiled = v

    muts = {
        "the counter never placed": (
            {"A", "B", "F", "I"}, set_counters, no_counter, real_counters),
        "piece_exiled ignores the census": (
            {"H"}, set_exiled, any_removal, real_exiled),
        "piece_exiled ignores the piece's type": (
            {"G"}, set_exiled, any_type, real_exiled),
        "voting.judgment never tells piece_exiled": (
            {"I"}, set_exiled, judgment_silent, real_exiled),
        "the game hook missing": ({"F", "I"}, set_hook, None, real_hook),
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
