#!/usr/bin/env python3
"""
Evaluate candidate ADDITIONS without committing to a cut.

Method: replace one existing slot with a neutral blank of the candidate's cost
(deck A), then with the candidate itself (deck B), and take the paired
difference under common random numbers. That isolates "what does this card add
over a replacement-level slot", which is directly comparable to the numbers
`ablation.py` produces for cards already in the deck.

So the cut decision is: is the candidate's score higher than the ablation score
of your weakest card? If yes, the swap is justified whatever that card is.
"""
import numpy as np

from edhmc.engine import Card, simulate as rendmaw_sim
from edhmc.lorehold import simulate as lorehold_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG, _swap_many, repl_priority
from edhmc.decks.rendmaw_v12 import (NOXIOUS_GEARHULK, BABA_LYSAGA,
                                     EZURIS_PREDATION,
                                     CAULDRON_OF_ESSENCE, REVITALIZING_REPAST,
                                     WURMCOIL_ENGINE)
from edhmc.decks.lorehold_v16 import (GALVANOTH, RADIANT_SCROLLWIELDER,
                                      GOLDSPAN_DRAGON,
                                      SUNBIRDS_INVOCATION, BRASSS_BOUNTY,
                                      UNDERWORLD_BREACH,
                                      CALDERA_PYREMAW, INVINCIBLE_HYMN,
                                      REVERSE_THE_SANDS)
from edhmc.decks.karlov_v2 import (HELIOD_SUN_CROWNED, EXEMPLAR_OF_LIGHT,
                                   GUIDE_OF_SOULS, ENDURING_TENACITY,
                                   STARSCAPE_CLERIC, THE_WIND_CRYSTAL,
                                   ENLIGHTENED_CONFIDANT, CRYPT_GHAST,
                                   DARK_CONFIDANT)
from edhmc.azusa import simulate as azusa_sim
from edhmc.decks.azusa_v1 import (GREENSLEEVES, ANCIENT_GREENWARDEN,
                                  CULTIVATOR_COLOSSUS,
                                  CASE_OF_THE_LOCKED_HOTHOUSE,
                                  CONDUIT_OF_WORLDS, WALK_IN_CLOSET,
                                  SPRINGHEART_NANTUKO,
                                  BURGEONING, CONSTANT_MISTS,
                                  RETURN_OF_THE_WILDSPEAKER,
                                  FINALE_OF_DEVASTATION, THE_GREAT_HENGE,
                                  SAPLING_NURSERY,
                                  NISSA_WHO_SHAKES_THE_WORLD,
                                  WAR_ROOM, CASTLE_GARENBRIG)

N = 6000


def blank_like(card, priority, deck):
    """A do-nothing replacement-level card of the same cost.

    This MUST match `ablation.py`'s blank, or the two tables are not on the same
    scale and the cut decision above is meaningless. It previously copied the
    candidate's whole type line, which silently cancelled the type line's own
    payoff: for Rendmaw an Artifact Creature blank triggers the commander, so
    Wurmcoil Engine was being scored against a blank that also made a Bird, and
    every card in `ablation_rendmaw.txt` was not. Single-type blank, same as
    ablation.py with BLANK_KEEPS_TYPES=0 — a card's type line is part of what
    it does.

    2026-09-06: `priority` is now passed in from `ablation.repl_priority()` for
    the same reason. It was hardcoded to 0.5, below the minimum priority of
    every deck, so BOTH tables were scoring against a card that is never cast.
    The bias does not cancel between them: it is proportional to the card's own
    priority, so comparing a high-priority candidate against a low-priority cut
    target — which is exactly what the decision rule above does — was biased
    toward the cut target. Any candidate number produced before 2026-09-06 is
    on the wrong scale for this reason, on top of the 2026-09-04 type-line one.

    2026-09-10: THE LAND BRANCH WAS DEAD CODE AND IT WAS WRONG. It copied the
    candidate's type line but never set `is_land` or `produces`, so a land
    candidate was measured against a zero-cost NONLAND that sat in hand being
    cast for no effect -- a blank that is not merely worse than the candidate
    but worse than a card. It went unnoticed because nothing had ever taken
    this branch: `ablation.py` blanks only nonlands (`names = {c.name for c in
    deck if not c.is_land}`), and the two land candidates measured before now
    (Cryptic Caves and the three rival sac-lands, §0z3) were run as real swaps
    by run_azusa_draw.py rather than through here. See `filler_land`.
    """
    if card.is_land:
        return filler_land(deck)
    if card.is_creature:
        types = frozenset({"Creature"})
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0, priority=priority)


def filler_land(deck):
    """The deck's own replacement-level land: the land it runs most copies of.

    DERIVED FROM THE DECK, for the same reason `repl_priority()` is (§0j). A
    land candidate is not competing with "a blank" -- there is no such thing as
    a blank land, since every land taps for something -- it is competing with
    the twenty-first Forest, which is the slot it would actually take. That is
    also how §0z3 framed Scene of the Crime, which went into the list for a
    Forest.

    Inventing a colourless or mono-green constant here instead would decide the
    answer: a colourless blank would make War Room look free when its real cost
    is that it does not tap for {G} in a deck with {G}{G} costs in it.
    """
    lands = [c for c in deck if c.is_land]
    if not lands:
        raise ValueError("deck has no lands to take a replacement level from")
    modal = max({c.name for c in lands},
                key=lambda n: sum(1 for c in lands if c.name == n))
    return next(c for c in lands if c.name == modal)


def add_value(deck_name, sim, turns, cand, victim, n=N, extra=()):
    deck, cmd = build_pending(deck_name)
    # A CANDIDATE THAT IS ALREADY IN THE LIST IS NOT A CANDIDATE. `build_pending`
    # applies the staged changes, so a card can be promoted from candidate to
    # deck member without anything here noticing -- and then this function
    # measures the marginal value of a SECOND COPY, in a singleton-illegal
    # 101st-card deck, and prints it under the heading "value over a blank".
    # Caldera Pyremaw did exactly that between 2026-09-04, when it was a
    # candidate, and 2026-09-05, when `-Penance +Caldera Pyremaw` was staged.
    # Same shape as the SCRIPTED_* sets and tag_flying.py's candidate gap: a
    # hand-maintained list the deck moved past.
    if any(c.name == cand.name for c in deck):
        raise SystemExit(
            f"{cand.name!r} is ALREADY IN the {deck_name} list (staged or "
            f"committed), so it cannot be measured as an addition. Remove it "
            f"from DECKS[{deck_name!r}] in candidates.py, or measure it as a "
            f"swap with experiment.run_ab instead.")
    a = _swap_many(deck, [victim], [blank_like(cand, repl_priority(deck), deck)])
    b = _swap_many(deck, [victim], [cand])
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset({cand.name}))
    ra = [sim(a, cmd, cfg, 80000 + j) for j in range(n)]
    rb = [sim(b, cmd, cfg, 80000 + j) for j in range(n)]
    out = {}
    for m in ("damage", "won") + tuple(extra):
        x = (np.array([r[m] for r in rb], float)
             - np.array([r[m] for r in ra], float))
        out[m] = (x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)))
    out["deploy"] = np.mean([r["cast_test_card"] for r in rb])
    return out


import sys

# The victim slot is removed in BOTH legs, so its identity does not bias the
# comparison — it only decides which 98 cards the candidate is measured
# alongside. Each is a card the ablation table scores near zero.
DECKS = {
    "rendmaw": ("RENDMAW", "rendmaw", rendmaw_sim, 10, "Pygmy Kavu",
                (CAULDRON_OF_ESSENCE, REVITALIZING_REPAST, WURMCOIL_ENGINE)),
    # CALDERA_PYREMAW was here and has been REMOVED: `-Penance +Caldera
    # Pyremaw` was staged on 2026-09-05, so `build_pending` now puts it in the
    # list and measuring it as an addition scores a second copy. The guard in
    # add_value() makes that an error rather than a number; this is the fix it
    # points at. Its real evidence is the head-to-head in run_fivedrop.py.
    "lorehold": ("LOREHOLD", "lorehold", lorehold_sim, 14, "Pinnacle Monk",
                 (GOLDSPAN_DRAGON, INVINCIBLE_HYMN, REVERSE_THE_SANDS)),
    "karlov": ("KARLOV", "karlov", karlov_sim, 10, "Soulmender",
               (ENLIGHTENED_CONFIDANT, CRYPT_GHAST, DARK_CONFIDANT)),
    # 2026-09-09 batch. The victim is Perilous Forays, the one card in
    # results/ablation_azusa.txt whose signal reads `--` -- inside its own
    # bars on both damage and win rate, so removing it in BOTH legs biases
    # nothing. T20 because this deck's payoffs are long-horizon: its whole
    # table is quoted at T20 and its T10 win rate is 0.042.
    "azusa": ("AZUSA", "azusa", azusa_sim, 20, "Perilous Forays",
              (GREENSLEEVES, ANCIENT_GREENWARDEN, CULTIVATOR_COLOSSUS,
               CASE_OF_THE_LOCKED_HOTHOUSE, CONDUIT_OF_WORLDS,
               WALK_IN_CLOSET, SPRINGHEART_NANTUKO,
               # The two the model cannot see. Measured anyway and printed
               # under the same heading, because a MODEL-BLIND card scoring
               # ~0.000 is the model having no eyes -- and this project's own
               # rule is that a proved blank and an unmeasured card look
               # identical unless you say which is which. See the notes in
               # decks/azusa_v1.py.
               BURGEONING, CONSTANT_MISTS)),
    # 2026-09-10 third batch. THE VICTIM CHANGED, and not by choice: the
    # 2026-09-09 batch above used Perilous Forays, which the staged Ka-Zar swap
    # CUTS -- so `build_pending("azusa")` no longer contains it and that entry
    # can no longer run at all. (It could not anyway: three of its nine
    # candidates were committed to the deck on 2026-09-10, so add_value()'s
    # §0o guard raises on them by design. Both failures are loud, which is the
    # point of the guard; the entry is kept as provenance for §0x.)
    #
    # Sylvan Library is the replacement victim and is the most neutral slot in
    # the deck: -0.0002 +-0.0017 win rate in the current table, signal `--`,
    # the tightest bar around zero of any row. It is also the deck module's
    # one enchantment with NO script at all, so removing it from both legs
    # removes nothing the engine was modelling -- which is exactly what a
    # victim slot should be.
    "azusa3": ("AZUSA", "azusa", azusa_sim, 20, "Sylvan Library",
               (RETURN_OF_THE_WILDSPEAKER, FINALE_OF_DEVASTATION,
                THE_GREAT_HENGE, SAPLING_NURSERY,
                NISSA_WHO_SHAKES_THE_WORLD, WAR_ROOM, CASTLE_GARENBRIG)),
    # 2026-09-04 first batch, kept so the runs are reproducible
    "lorehold1": ("LOREHOLD", "lorehold", lorehold_sim, 14, "Pinnacle Monk",
                  (SUNBIRDS_INVOCATION, BRASSS_BOUNTY, UNDERWORLD_BREACH)),
    "karlov1": ("KARLOV", "karlov", karlov_sim, 10, "Soulmender",
                (HELIOD_SUN_CROWNED, EXEMPLAR_OF_LIGHT, GUIDE_OF_SOULS,
                 ENDURING_TENACITY, STARSCAPE_CLERIC, THE_WIND_CRYSTAL)),
}

OLD = {
    "rendmaw": (NOXIOUS_GEARHULK, BABA_LYSAGA, EZURIS_PREDATION),
    "lorehold": (GALVANOTH, RADIANT_SCROLLWIELDER, GOLDSPAN_DRAGON),
}

if __name__ == "__main__":
    args = sys.argv[1:]
    override = next((int(a.split("=")[1]) for a in args
                     if a.startswith("--turns=")), None)
    # N IS PART OF THE IDENTITY OF A NUMBER, the same way it is for a table:
    # a candidate is only comparable to an ablation row measured at the same
    # sample size, and that comparison is the whole decision rule this script
    # exists to serve. The default stays 6000 so every pre-2026-09-09 run
    # reproduces; the azusa batch was run at 15000 to sit on its table's scale.
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    want = [a for a in args if not a.startswith("--")] or list(DECKS)
    for label, name, sim, turns, victim, cands in (DECKS[w] for w in want):
        turns = override or turns
        print(f"\n{label} candidates — value over a blank of the same cost "
              f"({turns} turns, n={n:,} paired)")
        # Lorehold's primary metric is mana cheated, not damage; the deck is
        # not built to put power on the board, so damage is the proxy there and
        # mv_cheated is the objective-adjacent number.
        extra = ("mv_cheated",) if name == "lorehold" else ()
        # Azusa's mechanism counters, so a number can be traced to the card's
        # text rather than just reported. landfall_triggers is the one that
        # separates a landfall PAYOFF from a land-supply enabler, and
        # lands_played separates both from a card that just draws.
        if name == "azusa":
            extra = ("landfall_triggers", "lands_played", "cards_drawn")
        head = f"  {'card':<28}{'MV':>4}{'damage':>16}{'win rate':>18}"
        for e in extra:
            head += f"{e:>16}"
        print(head + f"{'P(deploy)':>11}")
        for cand in cands:
            r = add_value(name, sim, turns, cand, victim, n=n, extra=extra)
            line = (f"  {cand.name:<28}{cand.mv:>4}"
                    f"{r['damage'][0]:>+10.2f}+-{r['damage'][1]:<5.2f}"
                    f"{r['won'][0]:>+11.4f}+-{r['won'][1]:<5.4f}")
            for e in extra:
                line += f"{r[e][0]:>+10.2f}+-{r[e][1]:<5.2f}"
            print(line + f"{r['deploy']:>11.3f}")
