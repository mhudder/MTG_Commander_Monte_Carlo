#!/usr/bin/env python3
"""Are the §0x candidates good replacements for the LAND-ANIMATION genre?

    python -m diagnostics.run_azusa_animation_swap [--n=15000] [--procs=16]

THE QUESTION. §0s measured the deck's four land-animation effects and found
the pillar is nearly a blank: `land_animation` +0.0003, `animated_lands_block`
+0.0013, `rude_awakening_modes` -0.0008, and all the value in that section was
the two Nissas (+0.0210). The animation is worth **9.24 marginal damage a game
in a deck whose damage runs into the thousands** -- it sells this deck the one
thing it already has most of. §0x then produced three candidates scoring
+0.029 / +0.014 / +0.012 over a blank. So: swap the genre out for them?

WHY THIS NEEDS ITS OWN HARNESS AND NOT ARITHMETIC. A candidate's
value-over-a-blank minus an incumbent's ablation score is NOT the swap. Both
are measured against a common baseline with overlapping CIs, and this project
has stopped two changes on exactly that rule (§0c Goldspan, §0e the Penance
slot). The swap has to be measured as the swap, with the cut card absent from
one branch and present in the other, on the same seeds.

THE CUT POOL is four cards, and picking it is a judgement worth stating:

    Sylvan Awakening      +0.0052 +-0.0018    pure animation
    Rude Awakening        +0.0061 +-0.0026    untap mode + animate + entwine
    Nissa, Worldwaker     +0.0079 +-0.0025    her +1 animates four Forests
    Ashaya, Soul of the   +0.0011 +-0.0023    the REVERSE blur -- creatures
      Wild                                    become lands. Weakest of the
                                              four, and §0v is why: the engine
                                              models it as ONE body whose
                                              power is your land count, and a
                                              single creature can only ever
                                              kill one opponent however large.

    NOT IN THE POOL: Nissa, Vastwood Seer // Sage Animist at +0.0277 +-0.0040,
    a top-five card in the deck. §0s is explicit that the Nissas are not the
    animation story, and cutting her would be cutting the finding rather than
    acting on it.

THE DESIGN. Every leg runs on the SAME SEED as the baseline, so each swap is a
paired difference and so the package legs can be compared to the sum of their
parts -- which is the second question here, because **two of the three
candidates grant the same ability**. Ancient Greenwarden and Conduit of Worlds
both say "you may play lands from your graveyard", and the deck already runs
Crucible of Worlds and Ramunap Excavator. Adding both would make FOUR copies
of one effect. §0x flagged that its rows cannot be summed; this measures how
badly.

    A       baseline, azusa_v1 as printed
    12 x    one candidate in for one cut card
    P3      -Sylvan -Rude -Ashaya  +Greenwarden +Greensleeves +Conduit
    P2      -Sylvan -Ashaya        +Greenwarden +Greensleeves
            (P2 drops the REDUNDANT candidate and keeps Nissa Worldwaker and
             Rude Awakening, so it is the conservative version of the change)
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import azusa_v1 as M
from edhmc.azusa import simulate as az_sim
from edhmc.experiment import DEFAULT_CFG, _swap_many

BASE_SEED = 5000                 # the ablation tables' seed base

CUTS = {
    "Sylvan": "Sylvan Awakening",
    "Rude": "Rude Awakening",
    "Worldwaker": "Nissa, Worldwaker",
    "Ashaya": "Ashaya, Soul of the Wild",
}
CANDS = {
    "Greenwarden": M.ANCIENT_GREENWARDEN,
    "Greensleeves": M.GREENSLEEVES,
    "Conduit": M.CONDUIT_OF_WORLDS,
    # Added 2026-09-10, after Springheart's bestow-and-copy mode was
    # implemented (§0z1). Its value-over-a-blank went +0.0105 -> +0.0141 at
    # T20, which puts it AHEAD of Conduit of Worlds -- the card staged for
    # the third slot. That makes this column a direct challenge to a staged
    # change, which is the whole reason to run it.
    "Springheart": M.SPRINGHEART_NANTUKO,
}

# (label, [names out], [cards in])
LEGS = [("A", [], [])]
for ck, cname in CUTS.items():
    for nk, card in CANDS.items():
        LEGS.append((f"{ck}->{nk}", [cname], [card]))
LEGS.append(("P3", [CUTS["Sylvan"], CUTS["Rude"], CUTS["Ashaya"]],
             [CANDS["Greenwarden"], CANDS["Greensleeves"], CANDS["Conduit"]]))
LEGS.append(("P2", [CUTS["Sylvan"], CUTS["Ashaya"]],
             [CANDS["Greenwarden"], CANDS["Greensleeves"]]))
# P3B / P2B: THE SAME PACKAGES WITH ASHAYA KEPT. Added 2026-09-10 (§0z).
# Ashaya's "nontoken creatures you control are Forest lands" is UNIMPLEMENTED
# -- only its */* clause is -- so its +0.0011 ablation row is not evidence
# about the card, and a package that cuts it is resting on a blank the engine
# created. These are the versions that cut only properly-modelled cards.
LEGS.append(("P3B", [CUTS["Sylvan"], CUTS["Rude"], CUTS["Worldwaker"]],
             [CANDS["Greenwarden"], CANDS["Greensleeves"], CANDS["Conduit"]]))
LEGS.append(("P2B", [CUTS["Sylvan"], CUTS["Rude"]],
             [CANDS["Greenwarden"], CANDS["Greensleeves"]]))
# P3C: the STAGED package with Springheart in the third slot instead of
# Conduit of Worlds. Added 2026-09-10 -- Springheart now out-scores Conduit
# over a blank, and Conduit was staged with a note saying it is the one to
# drop if any of the three is dropped. This measures whether that note should
# be acted on.
LEGS.append(("P3C", [CUTS["Sylvan"], CUTS["Rude"], CUTS["Worldwaker"]],
             [CANDS["Greenwarden"], CANDS["Greensleeves"],
              CANDS["Springheart"]]))

METRICS = ("won", "damage", "landfall_triggers", "cards_drawn",
           "lands_played", "lands_from_graveyard", "lands_animated",
           "animated_damage", "tokens_made", "springheart_copies")

_W = {}


def build_leg(outs, ins):
    deck, cmd = M.build()
    if outs:
        deck = _swap_many(deck, outs, ins)
    assert len(deck) + 1 == 100, f"{len(deck) + 1} cards"
    names = [c.name for c in deck] + [cmd.name]
    basics = ("Forest", "Mountain", "Plains", "Swamp", "Island", "Wastes")
    dups = {n for n in names if n not in basics and names.count(n) > 1}
    assert not dups, f"singleton violation {dups}"
    return deck, cmd


def _init(turns):
    _W["legs"] = [(lbl, build_leg(o, i)) for lbl, o, i in LEGS]
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns)


def _one(seed):
    out = []
    for _lbl, (deck, cmd) in _W["legs"]:
        r = az_sim(deck, cmd, _W["cfg"], seed)
        out.append([r[m] for m in METRICS])
    return out


def measure(turns, n, procs):
    with Pool(procs, initializer=_init, initargs=(turns,)) as pool:
        rows = pool.map(_one, range(BASE_SEED, BASE_SEED + n), chunksize=64)
    a = np.array(rows, float)                 # (n, legs, metrics)
    return {lbl: a[:, i, :] for i, (lbl, _o, _i) in enumerate(LEGS)}


def ci(d):
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 15000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)

    print("Azusa: the land-animation genre vs the 2026-09-09 candidates")
    print(f"N = {n:,} paired games per leg, seeds {BASE_SEED}.."
          f"{BASE_SEED + n - 1}, every leg on the same seed.")
    print("Baseline A is azusa_v1 AS PRINTED. Positive = the SWAP is an "
          "improvement.\n")
    print("  CUT POOL     Sylvan Awakening +0.0052 | Rude Awakening +0.0061 |")
    print("               Nissa, Worldwaker +0.0079 | Ashaya +0.0011")
    print("               (their own ablation rows, for reference)\n")

    iw = METRICS.index("won")
    for turns in (10, 20):
        legs = measure(turns, n, procs)
        base_win = legs["A"][:, iw].mean()
        print("=" * 78)
        print(f"T{turns}   baseline win rate {base_win:.4f}")
        print("=" * 78)
        print(f"  {'swap':<26}{'win rate':>22}   {'damage':>16}")
        for lbl, _o, _i in LEGS:
            if lbl == "A":
                continue
            d = legs[lbl] - legs["A"]
            m, hw = ci(d[:, iw])
            dm, dhw = ci(d[:, METRICS.index("damage")])
            star = " *" if abs(m) > hw else "  "
            print(f"  {lbl:<26}{m:>+11.4f} +-{hw:<8.4f}{star}"
                  f"{dm:>+8.2f} +-{dhw:<6.2f}")

        # Additivity: does the package beat the sum of its parts?
        print()
        for pkg, parts in (("P3", ["Sylvan->Greenwarden", "Rude->Greensleeves",
                                   "Ashaya->Conduit"]),
                           ("P2", ["Sylvan->Greenwarden",
                                   "Ashaya->Greensleeves"]),
                           ("P3B", ["Sylvan->Greenwarden",
                                    "Rude->Greensleeves",
                                    "Worldwaker->Conduit"]),
                           ("P2B", ["Sylvan->Greenwarden",
                                    "Rude->Greensleeves"]),
                           ("P3C", ["Sylvan->Greenwarden",
                                    "Rude->Greensleeves",
                                    "Worldwaker->Springheart"])):
            got, _ = ci((legs[pkg] - legs["A"])[:, iw])
            summed = sum(ci((legs[p] - legs["A"])[:, iw])[0] for p in parts)
            print(f"  {pkg}: measured {got:+.4f} vs sum of comparable singles "
                  f"{summed:+.4f}   ({got - summed:+.4f} interaction)")

        # What the swap gives up and what it buys, on the package legs.
        print(f"\n  MECHANISM, package legs vs baseline (T{turns}):")
        show = ("lands_animated", "animated_damage", "landfall_triggers",
                "cards_drawn", "lands_from_graveyard", "tokens_made",
                "springheart_copies")
        print(f"    {'metric':<24}{'P3B':>18}{'P3C':>18}"
              f"{'baseline':>12}")
        for mname in show:
            j = METRICS.index(mname)
            cells = []
            for pkg in ("P3B", "P3C"):
                m, hw = ci((legs[pkg] - legs["A"])[:, j])
                cells.append(f"{m:>+10.2f}+-{hw:<6.2f}")
            print(f"    {mname:<24}" + "".join(f"{c:>18}" for c in cells)
                  + f"{legs['A'][:, j].mean():>12.2f}")
        print()
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
