#!/usr/bin/env python3
"""Measures `cfg["combat_split"]` — one attack declared at the whole pod, with
removal insurance — against the old "everything at one player" combat.

    python run_combat_split.py [--n=15000] [--turns=10,20] [--deck=azusa] [--procs=N]

WHY THIS EXISTS. `opponents.damage_single` sent the entire combat swing at one
opponent. Measured on azusa: 491 swings of 120+ damage (the pod's whole combined
life) and every one killed EXACTLY ONE opponent while a mean of 1.82 were still
alive; the largest single hit was 933,017 damage and killed one player. So a
board that deals 933,017 was worth the same as one that deals 41, and the deck's
whole payoff -- go arbitrarily wide -- was capped at one kill a turn when you
need three.

THE FLAGS ARE THE ONLY DIFFERENCE BETWEEN THE LEGS. Both legs run the same
seeds through the same code; `combat_split` is passed through the cfg, NOT
monkeypatched, because on Windows `multiprocessing` spawns fresh interpreters
and a patch installed in the parent never reaches the workers -- which is how
KNOWN_ISSUES.md 0u's harness silently measured nothing and returned an exact
+0.0000 on every metric.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG

DECKS = {
    "azusa": ("edhmc.azusa", "edhmc.decks.azusa_v1"),
    "rendmaw": ("edhmc.engine", "edhmc.decks.rendmaw_v12"),
    "lorehold": ("edhmc.lorehold", "edhmc.decks.lorehold_v16"),
    "karlov": ("edhmc.karlov", "edhmc.decks.karlov_v2"),
    "tivit": ("edhmc.tivit", "edhmc.decks.tivit_v1"),
    "shilgengar": ("edhmc.shilgengar", "edhmc.decks.shilgengar_v1"),
}

OBS = ("won", "damage", "raw_damage", "opponents_killed",
       "attack_targets", "turn_won", "turn_lethal", "landfall_triggers")

_W = {}


def _init(deck_name, flags, turns):
    import importlib
    eng_mod, deck_mod = DECKS[deck_name]
    eng = importlib.import_module(eng_mod)
    deck = importlib.import_module(deck_mod)
    _W["sim"] = eng.simulate
    _W["deck"], _W["cmd"] = deck.build()
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    r = _W["sim"](_W["deck"], _W["cmd"], _W["cfg"], seed)
    return [float(r.get(m, 0.0)) for m in OBS]


def observe(deck_name, flags, n, turns, procs):
    with Pool(procs, initializer=_init,
              initargs=(deck_name, flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=32)
    return np.array(rows, float)


def report(a, b, n, label):
    print(f"\n  {label}")
    print(f"    {'metric':<20}{'off':>14}{'on':>14}{'delta':>16}")
    for i, m in enumerate(OBS):
        d = b[:, i] - a[:, i]
        hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
        star = "*" if abs(d.mean()) > hw else " "
        print(f"    {m:<20}{a[:, i].mean():>14.3f}{b[:, i].mean():>14.3f}"
              f"{d.mean():>+12.4f} +-{hw:<9.4f}{star}")


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    deck = next((a.split("=")[1] for a in args if a.startswith("--deck=")), "azusa")
    horizons = next((a.split("=")[1] for a in args
                     if a.startswith("--turns=")), "10,20")

    # CUMULATIVE LEGS, because the split necessarily fixes a second defect as a
    # side effect and a single before/after would report the two as one number.
    #   blockers  single swing, but blocked by the player actually being hit
    #             (the old path counts the WEAKEST board including DEAD
    #             opponents, i.e. zero blockers after the first elimination)
    #   split     the whole change: one attack declared at the whole pod
    # So `split` minus `blockers` is the split's own contribution.
    # EVERY LEG NAMES EVERY FLAG EXPLICITLY, including the baseline. As of
    # 2026-09-08 azusa's own __init__ does cfg.setdefault("combat_split", True),
    # so a leg that simply omits the flag gets the NEW behaviour and the
    # baseline would silently become the treatment -- the harness would then
    # measure nothing and say so with a suspiciously round number, which is the
    # KNOWN_ISSUES.md 0u failure wearing a different hat.
    BASE = {"combat_split": False, "combat_defender": "weakest"}
    LEGS = [
        ("blockers  (single swing, target's own blockers)",
         {"combat_split": False, "combat_defender": "target"}),
        ("split     (+ one attack at the whole pod, with insurance)",
         {"combat_split": True}),
    ]

    print(f"combat_split on {deck}: N={n} paired games, seeds 5000..{5000+n-1}")
    print("  '*' = the paired difference beats its own 95% CI half-width.")
    print("  Each leg is measured against the SAME baseline (both flags off).")
    for turns in (int(t) for t in horizons.split(",")):
        base = observe(deck, BASE, n, turns, procs)
        print(f"\n{'='*78}\nT{turns}\n{'='*78}")
        legs = []
        for label, flags in LEGS:
            b = observe(deck, flags, n, turns, procs)
            report(base, b, n, label)
            legs.append(b)
        # THE SPLIT'S OWN CONTRIBUTION, as a real paired difference rather than
        # the difference of two deltas -- same seeds, only `combat_split` moves,
        # so this is the number the split is actually worth and it carries its
        # own CI instead of an implied one.
        report(legs[0], legs[1], n,
               "THE SPLIT ALONE (leg 2 vs leg 1: only combat_split differs)")


if __name__ == "__main__":
    main()
