#!/usr/bin/env python3
"""§0z273: Cyberdrive Awakener by its text (tivit, §0z207 item 12).

    python -m tests.test_cyberdrive
    python -m tests.test_cyberdrive --mutate   # 5 mutations, exact sets

    "Flying. Other artifact creatures you control have flying. When this
    creature enters, each noncreature artifact you control becomes a 4/4
    artifact creature until end of turn."  ({5}{U} 4/4; Scryfall 2026-11-27)

The ETB was a lump of 4 x every token, as a multiplier on whatever else
attacked: summoning-sick tokens counted, nothing attacked if nothing else
did, and the grant of flying was not read. Now the tokens that can attack
are real 4/4 flying attackers for that combat (`cyberdrive_animate`) and
go back to their piles after (`cyberdrive_revert`); `flying_granted` is
the static.

CASES (tivit, Cyberdrive Awakener entered this turn; the pod has no bodies)
  A  3 Clues and 2 Treasures since the turn began: 5 attack, deal 20, and
     after combat the piles are 3 and 2 again, the Treasures tapped
  B  3 Clues, 1 of them there as the turn began: 1 attacks
  C  2 Powerstones, both tapped: none attacks
  D  an animated token has flying, and so does Academy Manufactor
  E  NEIGHBOUR: cyberdrive_text=False -- nothing animated, the Manufactor
     does not fly
  F  not the turn it entered: nothing animated
  G  an animated token that dies: its pile is one less, and Marionette
     Master hears an artifact go to the graveyard

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  tokens made this turn attack too              -> B
  tapped tokens attack too                      -> C
  the flying grant never read                   -> D
  a dead token's artifact leave not heard       -> G
  the survivors never go back to their piles    -> A, G

UNMUTATED (§0z15): E and F are the off sides.
"""
import sys

import edhmc.opponents as OPP
import edhmc.tivit as TI
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA_CFG = {}
CYBER = "Cyberdrive Awakener"


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def game(now, start=None, extra=(), entered=True, **cfg):
    board = [B.card("tivit", CYBER)] + [B.card("tivit", n) for n in extra]
    g = B.fresh("tivit", board=board, sick=board[:1],
                **{**EXTRA_CFG, **cfg})
    for k in g.tokens:
        g.tokens[k] = 0
    g.tokens.update(now)
    g.tokens_at_start = dict(start if start is not None else now)
    g.treasures_tapped = g.powerstones_tapped = 0
    g.cyberdrive_turn = g.turn if entered else g.turn - 1
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    g = game({"Clue": 3, "Treasure": 2})
    TI.combat(g)
    check("A five attack for 20; the piles back, the Treasures tapped",
          (g.m["cyberdrive_animated"], g.m["combat_damage"] >= 20,
           g.tokens["Clue"], g.tokens["Treasure"], g.treasures_tapped),
          (5, True, 3, 2, 2))

    g = game({"Clue": 3}, start={"Clue": 1})
    TI.combat(g)
    check("B only the Clue there as the turn began attacks",
          g.m["cyberdrive_animated"], 1)

    g = game({"Powerstone": 2})
    g.powerstones_tapped = 2
    TI.combat(g)
    check("C tapped Powerstones do not attack", g.m["cyberdrive_animated"], 0)

    g = game({"Clue": 1}, extra=["Academy Manufactor"])
    perms = TI.cyberdrive_animate(g)
    manu = next(p for p in g.board if p.card.name == "Academy Manufactor")
    check("D the animated token and the Manufactor fly",
          (OPP.flying_of(g, perms[0]), OPP.flying_of(g, manu)), (True, True))

    g = game({"Clue": 3}, extra=["Academy Manufactor"], cyberdrive_text=False)
    TI.combat(g)
    manu = next(p for p in g.board if p.card.name == "Academy Manufactor")
    check("E cyberdrive_text=False: nothing animated, no flying",
          (g.m["cyberdrive_animated"], OPP.flying_of(g, manu)), (0, False))

    g = game({"Clue": 3}, entered=False)
    TI.combat(g)
    check("F not its ETB turn: nothing", g.m["cyberdrive_animated"], 0)

    g = game({"Clue": 2}, extra=["Marionette Master"])
    perms = TI.cyberdrive_animate(g)
    OPP.destroy(g, perms[0], destroys=True)
    before = g.m["artifact_drain"]
    TI.cyberdrive_revert(g, perms)
    check("G a dead token: the pile one less, Marionette drains",
          (g.tokens["Clue"], g.m["artifact_drain"] > before), (1, True))
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("§0z273: Cyberdrive Awakener by its text\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real_anim, real_revert = TI.cyberdrive_animate, TI.cyberdrive_revert
    real_grant = TI.TivitGame.flying_granted
    real_left = TI._artifacts_left

    def sick_too(g):
        g.tokens_at_start = dict(g.tokens)
        return real_anim(g)

    def tapped_too(g):
        t, s = g.treasures_tapped, g.powerstones_tapped
        g.treasures_tapped = g.powerstones_tapped = 0
        try:
            return real_anim(g)
        finally:
            g.treasures_tapped, g.powerstones_tapped = t, s

    def no_return(g, animated):
        for perm in animated:
            g.animated.pop(id(perm), None)
            if perm in g.board:
                g.board.remove(perm)
            else:
                TI._artifacts_left(g, 1)

    def set_anim(v):
        TI.cyberdrive_animate = v

    def set_revert(v):
        TI.cyberdrive_revert = v

    def set_grant(v):
        TI.TivitGame.flying_granted = v

    def set_left(v):
        TI._artifacts_left = v

    muts = {
        "tokens made this turn attack too": ({"B"}, set_anim, sick_too,
                                             real_anim),
        "tapped tokens attack too": ({"C"}, set_anim, tapped_too, real_anim),
        "the flying grant never read": ({"D"}, set_grant,
                                        lambda self, perm: False, real_grant),
        "a dead token's artifact leave not heard": (
            {"G"}, set_left, lambda g, n: None, real_left),
        "the survivors never go back to their piles": (
            {"A", "G"}, set_revert, no_return, real_revert),
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
