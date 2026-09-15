#!/usr/bin/env python3
"""What do the 2026-09-13 Azusa candidates actually DO, per game?

Same shape and the same seeds as `diag_azusa_batch3.py`, for the same reason:
the win rates live in `results/candidates_azusa_batch4_T20.txt`, and a win rate
is not an explanation. A number nobody can trace to a card's text is not a
result yet.

    python -m diagnostics.diag_azusa_batch4 [n_games]
    python -m diagnostics.diag_azusa_batch4 --sweep [n_games]

THREE OF THESE SIX RUN ON A POLICY OR A CONSTANT RATHER THAN ON A RULE, and
this project's standing instruction is to say the knob out loud rather than
bury it:

    awaken_x         Awaken the Woods is {X}{G}{G} and X IS the card. The fixed
                     X convention (Genesis Wave 6, Animist's Awakening 4) is an
                     approximation everywhere it is used and a LOAD-BEARING one
                     here, so `--sweep` measures X = 3, 4, 6, 8 rather than
                     asserting 6.
    archdruid_mode   which mode of a modal card a pilot takes. "auto" is a
                     stated policy; "land" and "creature" are the two pure
                     strategies it is built from, and if the policy is worth
                     anything it beats both.
    zuran_keep       how many lands the pilot refuses to go below, and
                     `zuran_life_floor`, the life total at which two life a
                     land becomes worth it. A card whose whole content is a
                     policy has to have that policy measured, or its row is a
                     measurement of my judgement rather than of the card.
"""
import sys
from dataclasses import replace

import numpy as np

from edhmc.azusa import simulate as azusa_sim
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.pending import build_pending
from edhmc.decks import azusa_v1 as M
from tools.candidates import blank_like, filler_land

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(ARGS[0]) if ARGS else 4000
TURNS = 20
VICTIM = "Sylvan Library"        # see tools/candidates.py DECKS["azusa4"]

# Per-card, and deliberately so: the point is to name the mechanism each card
# claims and show whether it happened.
COUNTERS = {
    "Nissa, Resurgent Animist": ("animist_mana", "animist_cards",
                                 "animist_whiffs", "animist_revealed",
                                 "cards_drawn", "mana_spent"),
    "Traveling Chocobo": ("landfall_triggers", "landfall_ability_resolutions",
                          "lands_from_library", "tokens_made"),
    "Archdruid's Charm": ("charm_lands", "charm_creatures",
                          "landfall_triggers", "stranded_mv"),
    "Awaken the Woods": ("awaken_tokens", "landfall_triggers", "tokens_made",
                         "final_board_power", "wipes_suffered"),
    "Expedition Map": ("map_cracked", "lands_played", "landfall_triggers",
                       "fetches_cracked"),
    "Zuran Orb": ("zuran_sacs", "zuran_life", "final_life", "tokens_made",
                  "lands_played"),
}


def run(cand, cfg_extra=None, n=None):
    deck, cmd = build_pending("azusa")
    blank = blank_like(cand, repl_priority(deck), deck)
    a = _swap_many(deck, [VICTIM], [blank])
    b = _swap_many(deck, [VICTIM], [cand])
    cfg = dict(DEFAULT_CFG, turns=TURNS, watch=frozenset({cand.name}),
               **(cfg_extra or {}))
    n = n or N
    # The same seeds candidates.py uses, so these rows and those rows are the
    # same games and can be read against each other.
    ra = [azusa_sim(a, cmd, cfg, 80000 + j) for j in range(n)]
    rb = [azusa_sim(b, cmd, cfg, 80000 + j) for j in range(n)]
    return ra, rb


def mean(rows, key):
    return float(np.mean([r.get(key, 0.0) for r in rows]))


def med(rows, key):
    """The MEDIAN, for metrics whose mean is meaningless here.

    `final_life` is the sharp case and it is the §0v shape in a second place:
    Courser of Kruphix gains a life per landfall, so a runaway Scute Swarm game
    ends on tens of thousands of life. Measured over 1,500 games the median is
    0 and the mean is 71.5, because a handful of games carry it -- one ended on
    66,319. A mean like that reports the tail, not the card.
    """
    return float(np.median([r.get(key, 0.0) for r in rows]))


def awaken_at(x):
    """Awaken the Woods with X set to `x` -- COST AND EFFECT TOGETHER.

    The first version of this sweep set a cfg knob that changed only the number
    of tokens, so it measured eight tokens for the price of six and the deploy
    rate came back identical at every X, which is the tell. X is one number in
    two places on the card, so a sweep of it has to vary the card.
    """
    return replace(M.AWAKEN_THE_WOODS, cost={"gen": x, "G": 2}, x_pips=x)


def paired(ra, rb, key="won"):
    d = np.array([rb[i].get(key, 0.0) - ra[i].get(key, 0.0)
                  for i in range(len(ra))], float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def mechanisms():
    print(f"AZUSA batch 4 -- mechanism counters, {N:,} paired games, "
          f"{TURNS} turns")
    print(f"victim slot: {VICTIM}   (land candidates are measured against a "
          f"{filler_land(build_pending('azusa')[0]).name})\n")
    for cand in M.BATCH4_CANDIDATES:
        ra, rb = run(cand)
        deployed = mean(rb, "cast_test_card")
        turn = [r["test_card_turn"] for r in rb if r["test_card_turn"] < 99]
        answered = mean(rb, "test_card_answered")
        w, hw = paired(ra, rb, "won")
        print(f"  {cand.name}  (MV {cand.mv})   win {w:+.4f} +-{hw:.4f}")
        print(f"      resolves in {deployed:6.1%} of games"
              + (f", first on turn {np.mean(turn):.1f}" if turn else "")
              + (f", answered {answered:.1%}" if answered else ""))
        for key in COUNTERS.get(cand.name, ()):
            a, b = mean(ra, key), mean(rb, key)
            # The conditional column is a PAIRED DIFFERENCE on the games where
            # the card resolved, not a B-side level -- see diag_azusa_batch3.py
            # for why a level would be unreadable here.
            live = [i for i in range(len(rb)) if rb[i]["cast_test_card"]]
            cond = (float(np.mean([rb[i].get(key, 0.0) - ra[i].get(key, 0.0)
                                   for i in live])) if live else 0.0)
            print(f"      {key:<30}{a:>9.2f} -> {b:>9.2f}   "
                  f"{b - a:>+8.2f}   (when it resolves: {cond:>+8.2f})")
        print()


def sweeps():
    """The three knobs, measured rather than asserted."""
    n = max(1500, N // 2)
    print(f"KNOB SWEEPS, {n:,} paired games each, {TURNS} turns\n")

    # X=8 IS DELIBERATELY ABSENT AND THIS IS NOT A ROUNDING OF THE RANGE. At
    # X=8 one seed in the first 700 (80683) stops finishing: the original sweep
    # sat on it for 5.7 HOURS. X = 3, 4, 6 each complete 4,000 games in about
    # 75 seconds.
    #
    # THE CAUSE IS NOT THIS CARD AND NOT THIS ENGINE, which is why it is
    # recorded here rather than worked around. Profiled (90s, seed 80683):
    # 17,299,692 calls to `generic_key` inside `engine.can_pay`, 112s of the
    # 180s profiled run, against 11,299 calls to `can_pay` itself -- roughly
    # 1,500 key evaluations PER CALL. `can_pay` picks each generic pip with a
    # `min` over every available mana unit, so one call costs about
    # (units x generic pips), and this deck drives BOTH factors up together:
    # Ashaya makes every nontoken creature a Forest, Awaken adds eight more
    # land tokens, and Kozilek and Ulamog ask for {11}. A big-board game makes
    # ~11,000 such calls.
    #
    # It is SHARED code (all six engines pay it) and it is a performance
    # property rather than a wrong answer, so fixing it inside a candidate
    # evaluation would be the wrong trade -- the same reasoning queued item 17
    # gives for not changing an engine-wide rule mid-measurement. §0z21.
    print("  Awaken the Woods -- X, varied as the CARD: {X}{G}{G} for X tokens")
    for x in (3, 4, 6):
        cand = awaken_at(x)
        ra, rb = run(cand, None, n)
        w, hw = paired(ra, rb)
        print(f"      X={x} (MV {cand.mv})   win {w:+.4f} +-{hw:.4f}   "
              f"tokens {mean(rb, 'awaken_tokens'):5.2f}   "
              f"landfall {mean(rb, 'landfall_triggers'):6.2f}   "
              f"deploy {mean(rb, 'cast_test_card'):.1%}")

    print("\n  Archdruid's Charm -- archdruid_mode (a policy, and both pure "
          "strategies)")
    for mode in ("auto", "land", "creature"):
        ra, rb = run(M.ARCHDRUIDS_CHARM, {"archdruid_mode": mode}, n)
        w, hw = paired(ra, rb)
        print(f"      {mode:<9} win {w:+.4f} +-{hw:.4f}   "
              f"lands {mean(rb, 'charm_lands'):.2f}   "
              f"creatures {mean(rb, 'charm_creatures'):.2f}")

    print("\n  Zuran Orb -- zuran_keep and zuran_life_floor (the card IS the "
          "policy)")
    for keep, floor in ((4, 8), (6, 8), (8, 8), (6, 1), (6, 15)):
        ra, rb = run(M.ZURAN_ORB,
                     {"zuran_keep": keep, "zuran_life_floor": floor}, n)
        w, hw = paired(ra, rb)
        print(f"      keep={keep:<3} life_floor={floor:<3} "
              f"win {w:+.4f} +-{hw:.4f}   "
              f"sacs {mean(rb, 'zuran_sacs'):5.2f}   "
              f"life gained {mean(rb, 'life_gained'):6.2f}   "
              f"median final life {med(rb, 'final_life'):5.1f}")


def dryad_arbor():
    """THE REGRESSION THIS BATCH TURNED UP, measured on its own.

    Awaken the Woods cannot be implemented without answering "does a land
    creature tap for mana the turn it arrives", and the answer turned out to
    be that this engine already got it wrong for a card that has been in the
    list since 2026-09-07: DRYAD ARBOR, a Land Creature -- Forest Dryad, whose
    {G} was available on the turn it was played for the life of the project.
    302.6 says otherwise and the card is no different from any other creature.

    This is an ENGINE change, not a candidate, so it is measured the way every
    other engine change here is: the same deck, the same seeds, the knob on and
    off, so the only thing that differs is the rule. `land_creature_sick=False`
    reproduces every azusa number published before 2026-09-13.
    """
    deck, cmd = build_pending("azusa")
    print(f"DRYAD ARBOR / 302.6 -- land creatures are summoning sick for their "
          f"own mana ability\n{N:,} paired games, the staged azusa list, same "
          f"seeds, knob off vs on\n")
    for turns in (10, 20):
        cfg_old = dict(DEFAULT_CFG, turns=turns, land_creature_sick=False)
        cfg_new = dict(DEFAULT_CFG, turns=turns, land_creature_sick=True)
        ra = [azusa_sim(deck, cmd, cfg_old, 80000 + j) for j in range(N)]
        rb = [azusa_sim(deck, cmd, cfg_new, 80000 + j) for j in range(N)]
        ident = sum(1 for i in range(N)
                    if all(ra[i].get(k) == rb[i].get(k)
                           for k in ("won", "damage", "lands_played",
                                     "landfall_triggers")))
        print(f"  T{turns}")
        for key in ("won", "damage", "mana_spent", "lands_played",
                    "landfall_triggers", "turns_played"):
            d, hw = paired(ra, rb, key)
            star = " *" if abs(d) > hw else ""
            print(f"      {key:<20}{mean(ra, key):>10.4f} -> "
                  f"{mean(rb, key):>10.4f}   {d:>+9.4f} +-{hw:<8.4f}{star}")
        print(f"      games identical on all four headline metrics: "
              f"{ident}/{N} ({ident / N:.1%})\n")


def main():
    if "--sweep" in sys.argv:
        sweeps()
    elif "--dryad" in sys.argv:
        dryad_arbor()
    else:
        mechanisms()


if __name__ == "__main__":
    main()
