#!/usr/bin/env python3
"""Group ablations for every deck: what a FUNCTION is worth, not one card.

    python -m diagnostics.run_groups 15000 results/groups_20261001.json
    python -m diagnostics.run_groups --report results/groups_20261001.json
    python -m diagnostics.run_groups 200 /tmp/smoke.json        # smoke
    python -m diagnostics.run_groups 15000 OUT.json --decks=trostani
                       # re-measure some decks and MERGE them into OUT.json

WHY. Every table is leave-one-out, and leave-one-out is blind to redundancy
(CLAUDE.md): Karlov's combo partners were +0.02 each and +0.0513 together.
Here each group's cards are blanked TOGETHER, with exactly the tables' blank
(`ablation.blank_like` at `repl_priority` of the full list), seeds
5000..5000+N-1, horizons 10 and 20 read off one T20 game (§0z93), and the
staged list (`build_pending`) -- so a group's number is directly comparable
with the sum of its members' rows in the committed caches.

THE COMPARISON IS THE FINDING:
  group > sum of rows   the cards COVER for each other (substitutes): each row
                        understates its card, and cutting one costs little
  group < sum of rows   the cards NEED each other (complements, a combo): each
                        row already carries the package
  group ~ sum           the cards act independently

The interaction's CI is CONSERVATIVE: the per-game columns of the single rows
are not cached, so the sum's CI is bounded by the sum of the rows' CIs (a
standard deviation of a sum never exceeds the sum of the standard deviations).
An interaction marked `*` beats that bound; one inside it may still be real.

TWO CHECKS RUN WITH THE MEASUREMENT:
  * the first entry per deck re-measures ONE cached row as a group of one and
    must reproduce the cache to 1e-12 -- a tool whose output is a difference
    from another tool's baseline must reproduce that baseline (§0z35);
  * every group ends with a CONTROL of MODEL-BLIND removal where a deck has
    one: the engine cannot see those cards, so the control should read near
    zero, and a large control means the harness is wrong, not the cards.

GROUPS ARE A JUDGEMENT about what each card is FOR, written by hand -- so the
names are checked at import against each deck's staged list and its cache,
and a group naming a card the deck no longer runs raises (§0q).
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import repl_priority
from edhmc.pending import build_pending

N_DEFAULT = 15000
HORIZONS = (10, 20)
METRICS = ("won", "damage")

GROUPS = {
    "rendmaw": {
        "@check": ["Sol Ring"],
        "mana rocks": ["Sol Ring", "Golgari Signet", "Arcane Signet"],
        "mana Myrs": ["Palladium Myr", "Copper Myr", "Leaden Myr",
                      "Ornithopter of Paradise"],
        "land ramp": ["Sakura-Tribe Elder", "Solemn Simulacrum",
                      "Burnished Hart"],
        "token makers": ["Tendershoot Dryad", "Bitterblossom", "Grave Titan",
                         "March of the World Ooze",
                         "Overlord of the Hauntwoods",
                         "Arasta of the Endless Web", "Ophiomancer"],
        "anthems": ["Beastmaster Ascension", "Coat of Arms",
                    "Overwhelming Stampede"],
        "death drains": ["Blood Artist", "The Meathook Massacre"],
        "sac outlets": ["Ashnod's Altar", "Village Rites"],
        "artifact recursion": ["Scrap Trawler", "Myr Retriever", "Junk Diver"],
        "spot removal (control)": ["Beast Within", "Assassin's Trophy",
                                   "Reap", "Eyeblight's Ending",
                                   "Nameless Inversion", "Lignify"],
    },
    "lorehold": {
        "@check": ["Sol Ring"],
        "mana rocks": ["Sol Ring", "Boros Signet", "Talisman of Conviction",
                       "Arcane Signet", "Bender's Waterskin",
                       "Victory Chimes"],
        "card flow": ["Faithless Looting", "Thrill of Possibility",
                      "Big Score", "Unexpected Windfall", "Reforge the Soul"],
        "top-setters": ["Sensei's Divining Top", "Library of Leng"],
        "spell payoffs": ["Guttersnipe", "Monastery Mentor",
                          "Storm-Kiln Artist", "Arcane Bombardment",
                          "Double Vision", "Longshot, Rebel Bowman"],
        "finishers": ["Storm Herd", "Approach of the Second Sun",
                      "Rise of the Eldrazi"],
        "protection": ["Mother of Runes", "Lightning Greaves"],
        # Blasphemous Act rejoined 2026-10-05: its swap for Goldspan was
        # withdrawn (§0z105), so it is in the staged list again.
        "own wipes": ["Farewell", "Ultima", "Promise of Loyalty",
                      "Blasphemous Act"],
        "spot removal (control)": ["Path to Exile", "Swords to Plowshares",
                                   "Chaos Warp", "Generous Gift"],
    },
    "karlov": {
        "@check": ["Sol Ring"],
        "life loss -> gain": ["Exquisite Blood", "Bloodthirsty Conqueror"],
        "gain -> drain": ["Sanguine Bond", "Vito, Thorn of the Dusk Rose",
                          "Cliffhaven Vampire", "Marauding Blight-Priest",
                          "Starscape Cleric"],
        "soul sisters": ["Soul Warden", "Soul's Attendant", "Auriok Champion"],
        "alternate wins": ["Felidar Sovereign", "Aetherflux Reservoir"],
        "card advantage": ["Phyrexian Arena", "Necropotence",
                           "Well of Lost Dreams", "Cosmos Elixir"],
        "mana rocks": ["Sol Ring", "Orzhov Signet", "Pristine Talisman"],
        "shroud": ["Swiftfoot Boots", "Mother of Runes"],
        "own wipes": ["Farewell", "Austere Command", "Damnation",
                      "Toxic Deluge", "Damn"],
        "spot removal (control)": ["Path to Exile", "Swords to Plowshares",
                                   "Fracture"],
    },
    "tivit": {
        "@check": ["Sol Ring"],
        "four signets": ["Dimir Signet", "Azorius Signet", "Arcane Signet",
                         "Orzhov Signet"],
        "token drains": ["Mirkwood Bats", "Kambal, Profiteering Mayor",
                         "Nadier's Nightblade"],
        "artifact drains": ["Disciple of the Vault", "Marionette Master"],
        "extra votes": ["Ballot Broker", "Brago's Representative"],
        "blink": ["Ephemerate", "Displacer Kitten", "Deadeye Navigator",
                  "Conjurer's Closet", "Teleportation Circle", "Soulherder"],
        "tutors": ["Demonic Tutor", "Idyllic Tutor"],
        "token doublers": ["Anointed Procession", "Academy Manufactor"],
        "counters and removal (control)": ["Counterspell", "Dovin's Veto",
                                           "Muddle the Mixture",
                                           "An Offer You Can't Refuse",
                                           "Swords to Plowshares",
                                           "Path to Exile"],
    },
    "shilgengar": {
        "@check": ["Sol Ring"],
        "mana rocks": ["Sol Ring", "Fellwar Stone", "Talisman of Hierarchy",
                       "Arcane Signet", "Orzhov Signet", "Marble Diamond",
                       "Mind Stone"],
        "angel lords": ["Lyra Dawnbringer", "Lyra, Archangel of Dawn",
                        "Righteous Valkyrie"],
        "lifegain payoffs": ["Archangel of Thune", "Resplendent Angel",
                             "Youthful Valkyrie", "Speaker of the Heavens"],
        "death payoffs": ["Zulaport Cutthroat", "Blood Artist",
                          "Midnight Reaper", "Grim Haruspex",
                          "Pitiless Plunderer"],
        "sac outlets": ["Viscera Seer", "Cartel Aristocrat"],
        "draw engines": ["Phyrexian Arena", "Black Market Connections",
                         "Dark Prophecy", "Skullclamp"],
        "own wipes": ["Wrath of God", "Damn"],
        "spot removal (control)": ["Path to Exile", "Swords to Plowshares",
                                   "Generous Gift", "Vindicate"],
    },
    "azusa": {
        "@check": ["Sol Ring"],
        "lands from the top": ["Oracle of Mul Daya", "Courser of Kruphix",
                               "Augur of Autumn"],
        # Wayward Swordtooth was committed out for Mole Man (§0z102), so the
        # pair this group measured in §0z99 no longer exists.
        "ramp spells": ["Kodama's Reach", "Cultivate", "Realms Uncharted",
                        "Seek the Horizon", "Journey of Discovery"],
        "landfall creatures": ["Scute Swarm", "Avenger of Zendikar",
                               "Rampaging Baloths", "Greensleeves, Maro-Sorcerer"],
        # Life from the Loam was committed out for Mossborn Hydra (§0z103);
        # the four cards that now share "play lands from your graveyard":
        "lands from the graveyard": ["Ramunap Excavator", "Crucible of Worlds",
                                     "Mole Man, Moloid Master",
                                     "Ancient Greenwarden"],
        "finishers": ["Craterhoof Behemoth", "Ulamog, the Infinite Gyre",
                      "Kozilek, Butcher of Truth"],
        "card recursion": ["Regrowth", "Eternal Witness"],
        "tutors": ["Green Sun's Zenith", "Chord of Calling", "Sylvan Scrying",
                   "Crop Rotation"],
    },
    "trostani": {
        "@check": ["Sol Ring"],
        "mana dorks": ["Elvish Mystic", "Birds of Paradise",
                       "Avacyn's Pilgrim", "Sylvan Caryatid"],
        "mana rocks": ["Sol Ring", "Arcane Signet", "Talisman of Unity"],
        "land ramp": ["Sakura-Tribe Elder", "Wood Elves", "Farhaven Elf",
                      "Skyshroud Claim", "Solemn Simulacrum"],
        "tutors": ["Worldly Tutor", "Eladamri's Call", "Enlightened Tutor",
                   "Congregation at Dawn", "Chord of Calling",
                   "Green Sun's Zenith"],
        "token doublers": ["Primal Vigor", "Anointed Procession",
                           "Parallel Lives", "Mondrak, Glory Dominus"],
        "populate cards": ["Nesting Dovehawk", "Growing Ranks",
                           "Selesnya Eulogist", "Sundering Growth"],
        "recursion": ["Eternal Witness", "Timeless Witness", "Karmic Guide"],
        "removal (control)": ["Swords to Plowshares", "Path to Exile",
                              "Beast Within", "Aura Shards"],
    },
}


def cache_path(deck, n):
    return AB.Run(deck, n, HORIZONS).cache


def check_groups(n, decks=None):
    """Every name must be in the staged list AND in the deck's cache -- a
    group is a claim about the deck, and claims rot (§0q)."""
    bad = []
    for deck, groups in GROUPS.items():
        if decks and deck not in decks:
            continue
        names = {c.name for c in build_pending(deck)[0]}
        path = cache_path(deck, n)
        cached = json.load(open(path)) if os.path.exists(path) else {}
        for g, members in groups.items():
            for m in members:
                if m not in names:
                    bad.append(f"{deck}/{g}: {m!r} is not in the staged list")
                elif n == N_DEFAULT and m not in cached:
                    bad.append(f"{deck}/{g}: {m!r} has no cached row")
    if bad:
        raise SystemExit("run_groups: GROUPS has drifted from the decks:\n  "
                         + "\n  ".join(bad))


def blank_group(run, deck, members):
    prio = repl_priority(deck)
    out = list(deck)
    for name in members:
        i = next(i for i, c in enumerate(out) if c.name == name)
        out[i] = AB.blank_like(out[i], prio, keep_types=run.blank_keeps_types)
    return out


def job(task):
    deck_name, group, lo, hi = task
    run = AB.Run(deck_name, 1, HORIZONS)
    deck, cmd = build_pending(deck_name)
    if group is not None:
        deck = blank_group(run, deck, GROUPS[deck_name][group])
    cols = AB.columns_all(run, deck, cmd, lo, hi)
    return task, {t: {m: cols[t][m] for m in METRICS} for t in HORIZONS}


def measure(n, out_path, procs=4, decks=None):
    check_groups(n, decks)
    parts = AB._chunks(n, procs)
    tasks = [(d, g, lo, hi) for d, groups in GROUPS.items()
             if not decks or d in decks
             for g in [None, *groups] for lo, hi in parts]
    got = {}
    with Pool(procs) as pool:
        for k, (task, cols) in enumerate(
                pool.imap_unordered(job, tasks, chunksize=1), 1):
            got[task] = cols
            if k % procs == 0:
                print(f"  {k}/{len(tasks)}", flush=True)

    def full(d, g, t, m):
        return np.concatenate([got[(d, g, lo, hi)][t][m] for lo, hi in parts])

    result = {"n": n, "horizons": list(HORIZONS), "decks": {}}
    if decks and os.path.exists(out_path):
        result = json.load(open(out_path))
        assert result["n"] == n, "merging two sample sizes into one file"
    for d, groups in GROUPS.items():
        if decks and d not in decks:
            continue
        path = cache_path(d, n)
        cached = json.load(open(path)) if os.path.exists(path) else {}
        rows = {}
        for g, members in groups.items():
            cell = {}
            for t in HORIZONS:
                for m in METRICS:
                    diff = full(d, None, t, m) - full(d, g, t, m)
                    ci = 1.96 * diff.std(ddof=1) / np.sqrt(n)
                    singles = [cached.get(x, {}).get(str(t), {}).get(m)
                               for x in members]
                    have = all(s is not None for s in singles)
                    cell[f"{m}{t}"] = {
                        "group": [float(diff.mean()), float(ci)],
                        "sum": ([float(sum(s[0] for s in singles)),
                                 float(sum(s[1] for s in singles))]
                                if have else None)}
            rows[g] = {"members": members, "cells": cell}
        result["decks"][d] = rows
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=1)
    print("saved", out_path)


def report(path):
    res = json.load(open(path))
    print(f"GROUP ABLATIONS, N={res['n']:,} paired, seeds 5000.., staged lists,"
          f" the tables' blank. Win rate; `sum` is the members' committed rows"
          f" added up.\n  ratio = group / sum: >1 the cards cover for each "
          f"other, <1 they need each other.\n  interaction = group - sum, "
          f"`*` beats the conservative bound (group CI + every row's CI).\n")
    for deck, rows in res["decks"].items():
        print(deck.upper())
        # `sum` is re-read from the cache NOW rather than the copy stored at
        # measurement time, so a table rebuilt after the group run is the one
        # compared against (§0z100).
        cpath = cache_path(deck, res["n"])
        if os.path.exists(cpath):
            live = json.load(open(cpath))
            for row in rows.values():
                for key, cell in row["cells"].items():
                    m, t = key.rstrip("0123456789"), key[len(key.rstrip("0123456789")):]
                    vals = [live.get(x, {}).get(t, {}).get(m) for x in row["members"]]
                    if all(v is not None for v in vals):
                        cell["sum"] = [sum(v[0] for v in vals),
                                       sum(v[1] for v in vals)]
        chk = rows["@check"]["cells"]
        for t in res["horizons"]:
            g, s = chk[f"won{t}"]["group"], chk[f"won{t}"]["sum"]
            ok = s is not None and abs(g[0] - s[0]) < 1e-12
            print(f"  reproduces the cached {rows['@check']['members'][0]} "
                  f"row at T{t}: {'YES' if ok else 'NO -- the harness is wrong'}")
        for name, row in rows.items():
            if name == "@check":
                continue
            line = f"  {name:<30}({len(row['members'])})"
            for t in res["horizons"]:
                c = row["cells"][f"won{t}"]
                g, s = c["group"], c["sum"]
                sig = "*" if abs(g[0]) > g[1] else " "
                txt = f"  T{t} group {g[0]:+.4f}±{g[1]:.4f}{sig}"
                if s is not None:
                    inter = g[0] - s[0]
                    bound = g[1] + s[1]
                    ratio = (f"{g[0] / s[0]:5.2f}" if abs(s[0]) > 1e-4
                             else "  n/a")
                    txt += (f" sum {s[0]:+.4f} ratio {ratio} inter "
                            f"{inter:+.4f}{'*' if abs(inter) > bound else ' '}")
                line += txt
            print(line)
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        only = next((a.split("=", 1)[1].split(",") for a in sys.argv[3:]
                     if a.startswith("--decks=")), None)
        measure(int(sys.argv[1]), sys.argv[2], decks=only)
