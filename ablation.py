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

# Card names carry non-ASCII (Olórin's Searing Light). On Windows a redirected
# stdout defaults to the console codepage and writes cp1252, which makes the
# saved table invalid UTF-8. Force it.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

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
    # payoffs / draw / sac  (Skullclamp left the deck in v12)
    "Idol of Oblivion", "Steel Overseer", "Ohran Frostfang",
    "Coat of Arms", "Beastmaster Ascension", "Verdurous Gearhulk",
    "Roaming Throne", "Erebos, Bleak-Hearted", "Dockside Chef",
    "Solemn Simulacrum",
    # aristocrats drain
    "Blood Artist", "The Meathook Massacre",
    # Staged 2026-09-04. Both halves are in engine.py: the "each opponent
    # loses 1 life and you gain 1" death trigger, and the {1}{B}{G}, {T}, sac
    # a creature reanimation in activations().
    "Cauldron of Essence",
    # protection the opponent model respects
    "Heroic Intervention",
    # static P/T setter (implemented in Game.power_of / toughness_of)
    "March of the World Ooze",
}

# Reviewed 2026-09-03. Monologue Tax, Hidden Retreat, Urabrask and Triumph of
# Saint Katherine left the deck in v16 and are gone from this list with them.
SCRIPTED_LOREHOLD = {
    # mana
    "Sol Ring", "Arcane Signet", "Boros Signet", "Talisman of Conviction",
    "Ruby Medallion", "Bender's Waterskin", "Victory Chimes",
    # top-of-library manipulation
    "Sensei's Divining Top", "Scroll Rack", "Library of Leng",
    "Penance", "Verge Rangers",
    # card flow
    "Thrill of Possibility", "Faithless Looting", "Big Score",
    "Unexpected Windfall", "Borrowed Knowledge", "Reforge the Soul",
    "Apex of Power",
    # treasures / cost
    "Storm-Kiln Artist", "Smothering Tithe", "Hit the Mother Lode",
    # damage / win conditions
    "Guttersnipe", "Longshot, Rebel Bowman", "Soulfire Eruption",
    "Boros Charm", "Olórin's Searing Light", "Emeria's Call",
    "Rise of the Eldrazi",
    # Staged 2026-09-04. lorehold.sunbird() implements the whole text: reveal
    # the top X where X is the triggering spell's mana value, free-cast one
    # spell of MV <= X from among them, bottom the rest in random order — and
    # it fires only on casts FROM HAND, so miracles trigger it and Galvanoth,
    # Scrollwielder, Archaic and the copy engines do not.
    "Sunbird's Invocation",
    # copy engines
    "Double Vision", "Arcane Bombardment", "Mizzix's Mastery",
    "Monastery Mentor", "Monument to Endurance",
    # protection the opponent model respects
    "Lightning Greaves", "Mother of Runes",
    # cost reduction that scales with the graveyard / board
    "The Dawning Archaic", "Blasphemous Act",
    # BLIND, despite having engine code — the implementation is not the card:
    #   Artist's Talent - Level 2 granted free and instantly; Levels 1 and 3
    #                     do not exist, and Level 3 is a damage doubler
    #   Storm Herd      - X is cfg["storm_herd_x"]=40, not your life total
    #   Approach of the Second Sun - never gets its second cast, because the
    #                     card is not put seventh from the top
}

# Reviewed 2026-09-03 against the oracle audit. Membership here is a claim
# that the ENGINE implements the card's text, so a low score is evidence about
# the card. Cards whose text is still approximated belong in the blind group
# even when they are not literally absent from the engine.
SCRIPTED_KARLOV = {
    # lifegain engines
    "Soul Warden", "Soul's Attendant", "Suture Priest", "Auriok Champion",
    "Daxos, Blessed by the Sun", "Authority of the Consuls",
    "Ajani's Mantra", "Fountain of Renewal", "Drana's Emissary",
    "Blind Obedience", "Kambal, Consul of Allocation", "Sunscorch Regent",
    "Elas il-Kor, Sadistic Pilgrim", "Radiant Fountain",
    # lifegain payoffs
    "Voice of the Blessed", "Archangel of Thune", "Cliffhaven Vampire",
    "Marauding Blight-Priest", "Sanguine Bond", "Vito, Thorn of the Dusk Rose",
    "Vizkopa Guildmage", "Exquisite Blood", "Felidar Sovereign",
    "Aetherflux Reservoir", "Well of Lost Dreams", "Cosmos Elixir",
    "Dawn of Hope", "Blood Artist", "Syr Konrad, the Grim",
    "Debt to the Deathless", "Serra Ascendant",
    # other
    "Sol Ring", "Orzhov Signet", "Pristine Talisman", "Land Tax",
    "Phyrexian Arena", "Mother of Runes",
    "Swiftfoot Boots", "Sorin, Vengeful Bloodlord",
    "Sorin, Solemn Visitor", "Kalitas, Traitor of Ghet",
    # Added to the deck in v2, 2026-09-04. All three have their full text in
    # karlov.py: Starscape Cleric's "each opponent loses 1" and its Offspring
    # token copy, Enduring Tenacity's Sanguine Bond trigger AND its
    # return-as-an-enchantment death trigger (it is also in COMBO_LOOP), and
    # Exemplar of Light's counter-per-lifegain-event with the once-a-turn
    # draw. Their FLYING is unmodelled, but flying is unmodelled for every
    # creature in the engine — a global gap, not a per-card approximation, and
    # the same one Serra Ascendant already carries in this set.
    "Starscape Cleric", "Enduring Tenacity", "Exemplar of Light",
    # MOVED OUT to the blind group 2026-09-03, still approximated:
    #   Necropotence      - modelled as "draw 2", not skip-draw-step + pay life
    #   Benevolent Offering - flat 4 life, no per-creature scaling, no tokens
    #   Ranger of Eos     - "draw 2", not a tutor for two specific one-drops
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


# The key MUST include N. It used to key on deck and horizons only, so
# resuming a run at a different sample size silently merged two sample sizes
# into one table.
CACHE = (f"ablation_cache_{DECK}_{'-'.join(map(str, HORIZONS))}_n{N}"
         f"{'_sametype' if BLANK_KEEPS_TYPES else ''}.json")


def _job(name):
    deck, commander = build_pending(DECK)
    return name, ablate(deck, commander, name)


# Cards deliberately left out of the SCRIPTED set: the engine does NOT
# implement their text and a low score is evidence about the model. Listing
# them explicitly is what lets the assertion below be strict.
KNOWN_BLIND = {
    "rendmaw": {
        "Ashnod's Altar",
        "Assassin's Trophy",
        'Beast Within',
        'Biotransference',
        'Bow of Nylea',
        'Burnished Hart',
        'Culling Ritual',
        'Deathreap Ritual',
        "Eyeblight's Ending",
        'Filigree Familiar',
        'Gloomshrieker',
        'Hagra Mauling',
        'Haywire Mite',
        'Junk Diver',
        'Lignify',
        'Massacre Wurm',
        'Midnight Reaper',
        'Myr Retriever',
        'Nameless Inversion',
        'Overwhelming Stampede',
        'Pygmy Kavu',
        'Reap',
        'Sakura-Tribe Elder',
        'Scrap Trawler',
        'Shigeki, Jukai Visionary',
        'Toxic Deluge',
        'Village Rites',
        'Whip of Erebos',
    },
    "lorehold": {
        'Approach of the Second Sun',
        "Artist's Talent",
        'Bolt Bend',
        'Call Forth the Tempest',
        'Chaos Warp',
        "Dawn's Truce",
        "Dragon's Rage Channeler",
        'Enlightened Tutor',
        'Farewell',
        'Gamble',
        'Generous Gift',
        'Goliath Daydreamer',
        'Hexing Squelcher',
        'Improvisation Capstone',
        'Invoke Calamity',
        'Land Tax',
        'Ondu Inversion',
        'Path to Exile',
        'Perch Protection',
        'Pinnacle Monk',
        'Promise of Loyalty',
        'Restoration Seminar',
        'Sejiri Shelter',
        'Storm Herd',
        'Swords to Plowshares',
        'Ultima',
        'Volcanic Vision',
    },
    "karlov": {
        'Anguished Unmaking',
        'Austere Command',
        'Benevolent Offering',
        'Damn',
        'Damnation',
        'Enlightened Tutor',
        'Farewell',
        'Fracture',
        'Lurrus of the Dream-Den',
        'Necropotence',
        'Path to Exile',
        'Phyrexian Reclamation',
        'Ranger of Eos',
        'Return to Dust',
        "Sensei's Divining Top",
        'Soulmender',
        'Sun Titan',
        'Swords to Plowshares',
        'Toxic Deluge',
        "Umezawa's Jitte",
    },
}


def check_scripted_coverage(deck):
    """Every nonland card must be classified ON PURPOSE.

    The SCRIPTED_* sets are hand-maintained name sets and NOTHING used to check
    them against the deck. On 2026-09-04 five newly added cards were
    implemented in full and then printed under MODEL-BLIND, because adding a
    card to a deck is two edits and only one of them got made. The numbers were
    right; the label was wrong, and the label is the part that tells you whether
    a low score means anything.

    A name in SCRIPTED that is no longer in the deck is stale rather than
    dangerous, so it warns. A card in the deck that is in neither SCRIPTED nor
    KNOWN_BLIND is the failure that actually bit, so it raises.
    """
    names = {c.name for c in deck if not c.is_land}
    stale = SCRIPTED - {c.name for c in deck}   # lands may be scripted too
    if stale:
        print(f"  NOTE: {len(stale)} name(s) in SCRIPTED_{DECK.upper()} are no "
              f"longer in the deck: {', '.join(sorted(stale))}", file=sys.stderr)
    unclassified = names - SCRIPTED - KNOWN_BLIND[DECK]
    if unclassified:
        raise SystemExit(
            f"\n{len(unclassified)} card(s) in the {DECK} deck are in neither "
            f"SCRIPTED_{DECK.upper()} nor KNOWN_BLIND:\n"
            + "".join(f"    {n}\n" for n in sorted(unclassified))
            + "Add each to SCRIPTED_ if the engine implements its text, or to "
              "KNOWN_BLIND if it does not. The split between MODEL-EVALUATED "
              "and MODEL-BLIND is a CLAIM, and it has to be made deliberately.")


def main():
    deck, commander = build_pending(DECK)
    nonlands = [c.name for c in deck if not c.is_land]
    check_scripted_coverage(deck)

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
