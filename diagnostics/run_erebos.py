#!/usr/bin/env python3
"""Erebos, Bleak-Hearted: three errors on one card. Closes queued work item 8.

    Erebos, Bleak-Hearted  {3}{B}  Legendary Enchantment Creature - God  5/6
      Indestructible
      As long as your devotion to black is less than five, Erebos isn't a
        creature.
      Whenever another creature you control dies, you may pay 2 life. If you do,
        draw a card.
      {1}{B}, Sacrifice another creature: Target creature gets -2/-1 until end
        of turn.

Queued work item 8 named the second line. Verifying the card against Scryfall
found that two of the other three were wrong as well, so all three are measured
here, separately and together:

  devotion_creature_types   THE QUEUED ITEM. Erebos was a creature from the turn
                            it landed, so the early game got a 5/6 ATTACKER that
                            should not exist -- and a 6/6 one under March of the
                            World Ooze, which is the same shape as the Grist bug
                            (KNOWN_ISSUES 0b). Unlike Grist this is conditional
                            on BOARD STATE, so the `impending` sentinel could not
                            express it and it needed a devotion function.

  erebos_death_draw         THE ENGINE GAVE EREBOS DOCKSIDE CHEF'S ABILITY. It
                            was in a branch reading "Erebos / Dockside Chef /
                            Grim Backwoods style sac-for-card, once/turn", which
                            is Dockside Chef's card ({1}{B}, Sacrifice an
                            artifact or creature: Draw a card) and is not on
                            Erebos at all. Erebos's draw is a TRIGGER off deaths
                            that were going to happen anyway -- no sacrifice, no
                            mana, no once-per-turn -- which in a deck that loses
                            a dozen tokens a game is a different card entirely.
                            Its own activated ability is "target creature gets
                            -2/-1", which is model-blind against a blocker count.

  indestructible            Never set, so the card ate removal it cannot eat.
                            `Card.indestructible` and `destroy_share` (0.60, the
                            assumed share of pod interaction that is literally
                            "destroy") have existed since 2026-09-04 and were
                            INERT: no card in any committed list carried the
                            flag. Erebos is the first, so this run is also the
                            first measurement of that machinery, and its number
                            is only as good as that knob.

Two of the three point in OPPOSITE directions -- the body is a loss, the draw
and the indestructibility are gains -- so the combined number is the one to read
and the individual ones are why.

    python run_erebos.py [--n 15000] [--procs 16]
"""
import sys
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

from edhmc.engine import simulate as rendmaw_sim
from edhmc.decks import rendmaw_v12

DECK, CMD = rendmaw_v12.build()
EREBOS = "Erebos, Bleak-Hearted"

# The engine as the committed rendmaw table measured it.
OLD = {"devotion_creature_types": False, "erebos_death_draw": False}
NEW = {"devotion_creature_types": True, "erebos_death_draw": True}

METRICS = ("won", "damage", "cards_drawn", "erebos_draws", "erebos_life_paid",
           "erebos_creature_turns", "final_board_power", "removal_eaten",
           "tokens_made", "final_life", "turns_played")

_W = {}


def _init(flags, turns, indestructible):
    from edhmc.experiment import DEFAULT_CFG, _swap_many
    deck = list(DECK)
    if indestructible is not None:
        card = next(c for c in deck if c.name == EREBOS)
        deck = _swap_many(deck, [EREBOS],
                          [replace(card, indestructible=indestructible)])
    _W["deck"] = deck
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset({EREBOS}),
                     **flags)


def _one(seed):
    r = rendmaw_sim(_W["deck"], CMD, _W["cfg"], seed)
    return [r[m] for m in METRICS]


def leg(flags, turns, n, procs, indestructible=None):
    with Pool(procs, initializer=_init,
              initargs=(flags, turns, indestructible)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


# (label, off-flags, on-flags, off-indestructible, on-indestructible)
CASES = [
    ("devotion_creature_types  (Erebos was a 5/6 attacker from turn one)",
     dict(OLD), dict(OLD, devotion_creature_types=True), False, False),
    ("erebos_death_draw  (it had Dockside Chef's ability, not its own)",
     dict(OLD, devotion_creature_types=True), dict(NEW), False, False),
    ("indestructible  (never set; first live use of destroy_share)",
     dict(NEW), dict(NEW), False, True),
    ("ALL THREE -- the whole Erebos correction",
     dict(OLD), dict(NEW), False, True),
]


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    horizons = (10, 20)

    print(f"Erebos, Bleak-Hearted -- paired CFG flips and one card swap.")
    print(f"N = {n:,} paired games per cell, seeds 5000..{5000 + n - 1}, "
          f"same seeds both legs (CRN intact).")
    print(f"Rendmaw v12, default pod (v3). Applied CUMULATIVELY in the order "
          f"listed, so the three add to ALL THREE.\n")

    for label, off, on, i_off, i_on in CASES:
        print("=" * 78)
        print(label)
        print("=" * 78)
        for turns in horizons:
            a = leg(off, turns, n, procs, i_off)
            b = leg(on, turns, n, procs, i_on)
            print(f"  T{turns}")
            for i, m in enumerate(METRICS):
                d = b[:, i] - a[:, i]
                hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
                if abs(d.mean()) < 1e-9 and hw < 1e-9:
                    continue
                star = " *" if abs(d.mean()) > hw else "  "
                w = 6 if m == "won" else 3
                print(f"      {m:<24}{a[:, i].mean():>10.{w}f} ->"
                      f"{b[:, i].mean():>10.{w}f}   "
                      f"{d.mean():>+10.{w}f} +-{hw:<9.{w}f}{star}")
        print()
    print("* = 95% CI excludes zero. Win rate is the objective; damage and "
          "board power are proxies.")
    print("NOTE erebos_life_paid is a cost this model UNDERPRICES (KNOWN_ISSUES "
          "0i): life loss is")
    print("     nearly free here, so the death-draw number is a CEILING. "
          "`erebos_life_floor` (10) is")
    print("     the only thing standing in for declining the payment, and it is "
          "a judgement call.")


if __name__ == "__main__":
    main()
