#!/usr/bin/env python3
"""
Leave-one-out ablation for the Lorehold deck.

For each nonland card, replace it with a neutral blank of the same mana value
and measure the paired difference. Common random numbers make a one-card
ablation measurable; the blank occupies the same library slot, so the other 98
cards are dealt identically in both branches.

    contribution = metric(with card) - metric(with blank)

Positive means the card earns its slot. Near zero means it does nothing the
model can see.

READ THE CAVEAT
---------------
The engine scripts roughly 30 of the 65 nonland cards. The rest are modelled
faithfully as a mana cost, a type line and a body, which is correct for a
creature but blind for a removal spell: Swords to Plowshares kills nothing here,
because the opponents' boards are abstracted to a blocker count.

So the output is split into two groups. In the MODEL-EVALUATED group a low score
is evidence about the card. In the MODEL-BLIND group a low score is evidence
about the model, and says nothing at all about the card. Do not read the second
table as a cut list.

Usage:  python ablation.py [n_games] [turns]
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.engine import Card, simulate as rendmaw_sim
from edhmc.pending import build_pending
from edhmc.lorehold import simulate as lh_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.experiment import DEFAULT_CFG

DECK = sys.argv[1] if len(sys.argv) > 1 else "lorehold"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
# Report a RANGE of horizons rather than one. The cutoff turn is a free
# parameter created by the fact that opponents have no win condition, and it
# systematically favours slow, accumulating cards. A conclusion is only
# trustworthy if its SIGN and RANK survive the whole range.
HORIZONS = tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 \
    else (20,)   # with the opponent clock, games end on their own around T12
# See blank_like(). Set True to isolate a card's text from its type line.
BLANK_KEEPS_TYPES = os.environ.get("BLANK_KEEPS_TYPES", "0") == "1"

SIM = {"lorehold": lh_sim, "rendmaw": rendmaw_sim,
       "karlov": karlov_sim}[DECK]
METRIC_SETS = {
    "lorehold": ("mv_cheated", "damage", "miracles_cast", "total_mv_cast", "won"),
    "rendmaw": ("damage", "cards_drawn", "tokens_made", "rendmaw_triggers", "won"),
    "karlov": ("damage", "lifegain_triggers", "final_life", "cards_drawn", "won"),
}

# Cards whose actual text the engine implements. Everything else is a body.
SCRIPTED_RENDMAW = {
    # mana
    "Sol Ring", "Arcane Signet", "Golgari Signet", "Copper Myr", "Leaden Myr",
    "Palladium Myr", "Ornithopter of Paradise", "Twitching Doll",
    "Dryad of the Ilysian Grove", "Enduring Vitality", "The Great Henge",
    "Overlord of the Hauntwoods", "Foundry Inspector",
    # token engines
    "Bitterblossom", "Ophiomancer", "Tendershoot Dryad", "Grist, the Hunger Tide",
    "Grave Titan", "Woe Strider", "Arasta of the Endless Web",
    "Primal Vigor", "Metallic Mimic",
    # payoffs / draw / sac
    "Skullclamp", "Idol of Oblivion", "Steel Overseer", "Ohran Frostfang",
    "Coat of Arms", "Beastmaster Ascension", "Verdurous Gearhulk",
    "Roaming Throne", "Erebos, Bleak-Hearted", "Dockside Chef",
    "Solemn Simulacrum",
    # aristocrats drain
    "Blood Artist", "The Meathook Massacre",
    # protection the opponent model respects
    "Heroic Intervention",
    # static P/T setter (implemented in Game.power_of / toughness_of)
    "March of the World Ooze",
}

SCRIPTED_LOREHOLD = {
    # mana
    "Sol Ring", "Arcane Signet", "Boros Signet", "Talisman of Conviction",
    "Ruby Medallion", "Bender's Waterskin", "Victory Chimes",
    # top-of-library manipulation
    "Sensei's Divining Top", "Scroll Rack", "Library of Leng",
    "Hidden Retreat", "Penance", "Verge Rangers",
    # card flow
    "Thrill of Possibility", "Faithless Looting", "Big Score",
    "Unexpected Windfall", "Borrowed Knowledge", "Reforge the Soul",
    "Apex of Power",
    # treasures / cost
    "Storm-Kiln Artist", "Smothering Tithe", "Monologue Tax",
    "Artist's Talent", "Hit the Mother Lode",
    # damage / win conditions
    "Guttersnipe", "Soulfire Eruption", "Storm Herd", "Boros Charm",
    "Emeria's Call", "Approach of the Second Sun", "Rise of the Eldrazi",
    # protection the opponent model respects
    "Lightning Greaves", "Mother of Runes",
    # cost reduction that scales with the graveyard / board
    "The Dawning Archaic", "Blasphemous Act",
}

SCRIPTED_KARLOV = {
    # lifegain engines
    "Soul Warden", "Soul's Attendant", "Suture Priest", "Auriok Champion",
    "Daxos, Blessed by the Sun", "Authority of the Consuls",
    "Ajani's Mantra", "Fountain of Renewal", "Drana's Emissary",
    "Blind Obedience", "Kambal, Consul of Allocation", "Sunscorch Regent",
    "Elas il-Kor, Sadistic Pilgrim", "Benevolent Offering", "Radiant Fountain",
    # lifegain payoffs
    "Voice of the Blessed", "Archangel of Thune", "Cliffhaven Vampire",
    "Marauding Blight-Priest", "Sanguine Bond", "Vito, Thorn of the Dusk Rose",
    "Vizkopa Guildmage", "Exquisite Blood", "Felidar Sovereign",
    "Aetherflux Reservoir", "Well of Lost Dreams", "Cosmos Elixir",
    "Dawn of Hope", "Blood Artist", "Syr Konrad, the Grim",
    "Debt to the Deathless", "Serra Ascendant",
    # other
    "Sol Ring", "Orzhov Signet", "Pristine Talisman", "Land Tax",
    "Phyrexian Arena", "Necropotence", "Mother of Runes", "Lightning Greaves",
    "Swiftfoot Boots", "Whispersilk Cloak", "Sorin, Vengeful Bloodlord",
    "Sorin, Solemn Visitor", "Ranger of Eos", "Kalitas, Traitor of Ghet",
}

SCRIPTED = {"lorehold": SCRIPTED_LOREHOLD, "rendmaw": SCRIPTED_RENDMAW,
            "karlov": SCRIPTED_KARLOV}[DECK]
METRICS = METRIC_SETS[DECK]


def blank_like(card):
    """A do-nothing replacement-level card of the same cost.

    BLANK_KEEPS_TYPES controls what the ablation actually measures, and for a
    typal-payoff commander the difference is large:

      True  - the blank copies the card's type line, so for Rendmaw an Artifact
              Creature blank still triggers the commander. This isolates the
              card's TEXT, with the type-line payoff cancelling out on both
              sides. Right question for "is this card's ability any good".
      False - the blank is a single-type body, so the swapped card's type line
              counts toward its score. Right question for "is this SLOT pulling
              its weight", which is the deckbuilding question.

    Default is False, because a card's type line is part of what it does.
    """
    if BLANK_KEEPS_TYPES:
        types = card.types
    elif card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0,
                priority=0.5)


def ablate(deck, commander, card_name):
    """Returns {horizon: {metric: (mean_diff, ci)}}."""
    idx = next(i for i, c in enumerate(deck) if c.name == card_name)
    deck_b = list(deck)
    deck_b[idx] = blank_like(deck[idx])

    out = {}
    for turns in HORIZONS:
        cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
        keep, drop = [], []
        for i in range(N):
            keep.append(SIM(deck, commander, cfg, 5000 + i))
            drop.append(SIM(deck_b, commander, cfg, 5000 + i))
        cell = {}
        for m in METRICS:
            d = (np.array([k[m] for k in keep], float)
                 - np.array([x[m] for x in drop], float))
            cell[m] = (d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d)))
        out[str(turns)] = cell
    return out


CACHE = (f"ablation_cache_{DECK}_{'-'.join(map(str, HORIZONS))}"
         f"{'_sametype' if BLANK_KEEPS_TYPES else ''}.json")


def _job(name):
    deck, commander = build_pending(DECK)
    return name, ablate(deck, commander, name)


def main():
    deck, commander = build_pending(DECK)
    nonlands = [c.name for c in deck if not c.is_land]

    results = {}
    if os.path.exists(CACHE):
        results = json.load(open(CACHE))
    todo = [n for n in nonlands if n not in results]
    budget = float(os.environ.get("ABLATE_BUDGET", "240"))
    t0 = time.time()
    for name in todo:
        results[name] = ablate(deck, commander, name)
        json.dump(results, open(CACHE, "w"))       # resumable across runs
        print(f"  done {len(results)}/{len(nonlands)}: {name}", file=sys.stderr)
        if time.time() - t0 > budget:
            break
    remaining = [n for n in nonlands if n not in results]
    if remaining:
        print(f"\n{len(remaining)} cards still to do — rerun to resume.",
              file=sys.stderr)
        return

    print(f"""
Horizons: {HORIZONS}.  All figures are paired differences with 95% CIs.

  signal = both : the card beats its error bars on damage AND win rate
           dmg  : significant on damage only
           win  : significant on win rate only
           --   : INSIDE its own error bars - indistinguishable from a blank.
                  Not a weak card, an unmeasured one. Do not rank these.

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.""")
    for title, group in (("MODEL-EVALUATED — a low score is evidence about the card",
                          [n for n in nonlands if n in SCRIPTED]),
                         ("MODEL-BLIND — a low score is evidence about the MODEL, not the card",
                          [n for n in nonlands if n not in SCRIPTED])):
        last = str(HORIZONS[-1])
        rows = sorted(group, key=lambda n: -results[n][last]["damage"][0])
        print(f"\n{'=' * 84}\n{title}\n{'=' * 84}")
        hz = [str(h) for h in HORIZONS]
        last = hz[-1]
        head = "".join(f"{'damage T' + h:>20}" for h in hz)
        print(f"{'card':<30}{head}{'win rate':>21}{'signal':>10}")
        for n in rows:
            cells = ""
            for h in hz:
                m, ci = results[n][h]["damage"]
                cells += f"{m:>+13.2f}+-{ci:<5.2f}"
            w, wci = results[n][last]["won"]
            # A score inside its own error bar is indistinguishable from a
            # blank. Say so, rather than letting the sign imply a ranking.
            d_sig = abs(results[n][last]["damage"][0]) > results[n][last]["damage"][1]
            w_sig = abs(w) > wci
            sig = ("both" if d_sig and w_sig else
                   "dmg" if d_sig else "win" if w_sig else "--")
            if len(HORIZONS) > 1 and len({np.sign(results[n][h]["damage"][0])
                                          for h in hz}) > 1:
                sig = "FLIP"
            print(f"{n:<30}{cells}{w:>+14.4f}+-{wci:<5.4f}{sig:>10}")


if __name__ == "__main__":
    main()
