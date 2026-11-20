#!/usr/bin/env python3
"""§0z233 (queue item 51): the death step's tokens, `altar_death_step`.

    python -m tests.test_altar_death_step
    python -m tests.test_altar_death_step --mutate   # 4 mutations, exact sets

Each case: a rendmaw game on a battlefield set by hand -- Ashnod's Altar, the
drain card the case names, and eight 0/1 Goat tokens (`altar_keep` 6, so two
are `altar_fodder`'s excess) -- then `activations`. A case reads how many
Goats died (`death_step_sacs`) and what the case is about.

CASES
  A  "two", Blood Artist: two Goats sacrificed (the old rule)
  B  "none", Blood Artist: nothing sacrificed
  C  "lethal", The Meathook Massacre, rivals on 40/40/3: three sacrificed,
     the one on 3 dead
  D  "lethal", Meathook, rivals on 40/40/40: nothing sacrificed
  E  "safe", Blood Artist, your life 1000, the LAST Goat on the board
     tapped: two sacrificed, the tapped one among them
  F  "safe", Blood Artist, your life 5 (at or under `hold_back_pad` 10 for
     any prediction): nothing sacrificed
  G  "safe", Meathook, your life 5, a rival on 2: two sacrificed -- the
     lethal reading outranks the guard -- and that rival dead
  H  NEIGHBOUR: "two", no drain card on the board: nothing sacrificed (the
     step's own gate, unchanged)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  death_step_lethal returns []           -> C, G
  predicted_chip reads -1e9 (no guard)   -> F
  death_step_tokens in board order       -> E
  altar_death_step="two" in every case   -> B, C, D, E, F

UNMUTATED (§0z15): A is the old rule, which no mutation here reaches; H
has no drain card under any rule. G passes under "two" as well (two
Meathook deaths finish a rival on 2), so the old-rule mutation cannot see
it: the lethal mutation is what pins G.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.opponents as OPP
from edhmc.decks import rendmaw_v12 as RM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def take(zone, name):
    c = next(x for x in zone if x.name == name)
    EN.remove_card(zone, c)
    return c


def game(mode, drain="Blood Artist", life=40.0, rivals=(40.0, 40.0, 40.0),
         tap_last=False):
    deck, cmd = RM.build()
    g = EN.Game(list(deck), cmd,
                {**DEFAULT_CFG, "altar_death_step": mode, **EXTRA_CFG},
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.commander_cast = True
    g.turn = 6
    g.your_life = life
    for o, hp in zip(g.opponents, rivals):
        o.life = hp
    names = ["Ashnod's Altar"] + ([drain] if drain else [])
    for n in names:
        g.board.append(EN.Permanent(card=take(g.library, n), sick=False))
    g.make_tokens(8, 0, 1, "Goat")
    for p in g.board:
        p.sick = False
    goats = [p for p in g.board if p.is_token]
    if tap_last:
        goats[-1].tapped = True
    return g, goats


def died(g, goats):
    return [p for p in goats if not any(p is q for q in g.board)]


def run_cases():
    PASS.clear()
    FAIL.clear()

    g, goats = game("two")
    EN.activations(g)
    check("A two: two sacrificed", (len(died(g, goats)),
                                    g.m["death_step_sacs"]), (2, 2))

    g, goats = game("none")
    EN.activations(g)
    check("B none: nothing sacrificed", len(died(g, goats)), 0)

    g, goats = game("lethal", drain="The Meathook Massacre",
                    rivals=(40.0, 40.0, 3.0))
    EN.activations(g)
    check("C lethal, a rival on 3: three sacrificed, that rival dead",
          (len(died(g, goats)), g.opponents[2].alive), (3, False))

    g, goats = game("lethal", drain="The Meathook Massacre")
    EN.activations(g)
    check("D lethal, rivals on 40: nothing sacrificed",
          len(died(g, goats)), 0)

    g, goats = game("safe", life=1000.0, tap_last=True)
    EN.activations(g)
    gone = died(g, goats)
    check("E safe, life 1000: two sacrificed, the tapped one among them",
          (len(gone), any(p is goats[-1] for p in gone)), (2, True))

    g, goats = game("safe", life=5.0)
    EN.activations(g)
    check("F safe, life 5: nothing sacrificed", len(died(g, goats)), 0)

    g, goats = game("safe", drain="The Meathook Massacre", life=5.0,
                    rivals=(40.0, 40.0, 2.0))
    EN.activations(g)
    check("G safe, life 5, a rival on 2: two sacrificed, that rival dead",
          (len(died(g, goats)), g.opponents[2].alive), (2, False))

    g, goats = game("two", drain=None)
    EN.activations(g)
    check("H NEIGHBOUR: no drain card: nothing sacrificed",
          len(died(g, goats)), 0)
    return set(FAIL)


def main() -> int:
    global EXTRA_CFG
    if not MUTATE:
        print("§0z233: the death step's tokens\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    board_order = lambda g: [p for p in g.board                  # noqa: E731
                             if p.is_token and p.card.is_creature]
    muts = {
        "death_step_lethal returns []": ({"C", "G"}, {}, [
            (EN, "death_step_lethal", lambda g, pool: [])]),
        "predicted_chip reads -1e9": ({"F"}, {}, [
            (OPP, "predicted_chip", lambda g, rounds=1: -1e9)]),
        "death_step_tokens in board order": ({"E"}, {}, [
            (EN, "death_step_tokens", board_order)]),
        'altar_death_step="two" in every case': (
            {"B", "C", "D", "E", "F"}, {"altar_death_step": "two"}, []),
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
