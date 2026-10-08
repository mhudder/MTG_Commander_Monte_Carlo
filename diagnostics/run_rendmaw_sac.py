#!/usr/bin/env python3
"""Rendmaw's sacrifice engines as a group (§0z121).

    python -m diagnostics.run_rendmaw_sac 15000 results/rendmaw_sac_20261008.json
    python -m diagnostics.run_rendmaw_sac --report results/rendmaw_sac_20261008.json

THE QUESTION (the owner, 2026-10-08): is Ashnod's Altar at the bottom of the
table because it is the weakest of several outlets that cover for each other,
or because sacrifice outlets do not do much in this deck at all?
Leave-one-out cannot tell those apart (CLAUDE.md: it is blind to redundancy),
so every arm below blanks a SET, paired on the tables' seeds and blank.

ARMS (cards blanked together, `ablation.blank_like` at `repl_priority` of the
full list, exactly as `run_groups` does):
  outlets   Ashnod's Altar, Village Rites, Dockside Chef -- the nonland cards
            that sacrifice ANOTHER creature for value. The three land outlets
            (Grim Backwoods, High Market, Castle Locthwain) are not blanked:
            a land's slot is a basic, not a blank (§0z112). Woe Strider's
            "Sacrifice another creature: Scry 1" is not implemented.
  payoffs   Blood Artist, The Meathook Massacre, Erebos, Bleak-Hearted -- the
            cards that turn a death into damage or a card.

THE COMPARISONS, each a paired difference on the same seeds:
  Altar alone             base - (-Altar): must reproduce the cached row
  Altar, no other outlets (-Rites -Chef) - (-outlets)
  Altar, no payoffs       (-payoffs) - (-payoffs -Altar)
  outlets as a group      base - (-outlets), against the sum of the rows
  payoffs as a group      base - (-payoffs)
  the whole package       base - (-outlets -payoffs)

Run it under the interpreter the table was built on (§0z119), or the first
row will not reproduce the cache to the last bit.
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

import tools.ablation as AB
from edhmc.experiment import DEFAULT_CFG, repl_priority
from edhmc.pending import build_pending

DECK = "rendmaw"
ALTAR, RITES, CHEF = "Ashnod's Altar", "Village Rites", "Dockside Chef"
OUTLETS = [ALTAR, RITES, CHEF]
PAYOFFS = ["Blood Artist", "The Meathook Massacre", "Erebos, Bleak-Hearted"]
ARMS = {
    "base": [],
    "-Altar": [ALTAR],
    "-Rites": [RITES],
    "-Chef": [CHEF],
    "-outlets": OUTLETS,
    "-Rites -Chef": [RITES, CHEF],
    "-payoffs": PAYOFFS,
    "-payoffs -Altar": PAYOFFS + [ALTAR],
    "-outlets -payoffs": OUTLETS + PAYOFFS,
}
# (label, keep arm, drop arm): value = keep - drop, the table's sign.
COMPARE = [
    ("Ashnod's Altar (the table's row)", "base", "-Altar"),
    ("Village Rites (row)", "base", "-Rites"),
    ("Dockside Chef (row)", "base", "-Chef"),
    ("Altar, the other two outlets gone", "-Rites -Chef", "-outlets"),
    ("Altar, the three payoffs gone", "-payoffs", "-payoffs -Altar"),
    ("outlets as a group (3)", "base", "-outlets"),
    ("payoffs as a group (3)", "base", "-payoffs"),
    ("outlets + payoffs (6)", "base", "-outlets -payoffs"),
]
TOP, REST = 20, 10
COUNTERS = ("altar_sacrifices", "altar_mana_made", "altar_wasted",
            "village_rites_cast", "chef_activations", "backwoods_activations",
            "high_market_sacs", "drain_damage", "cards_drawn")


def arm_deck(arm):
    deck, cmd = build_pending(DECK)
    run = AB.Run(DECK, 1, (REST, TOP))
    prio = repl_priority(deck)
    out = list(deck)
    for name in ARMS[arm]:
        i = next(i for i, c in enumerate(out) if c.name == name)
        out[i] = AB.blank_like(out[i], prio, keep_types=run.blank_keeps_types)
    return run, out, cmd


def job(task):
    arm, lo, hi = task
    run, deck, cmd = arm_deck(arm)
    cfg = dict(DEFAULT_CFG, turns=TOP, watch=frozenset(),
               snapshot_rounds=(REST,))
    cols = {k: [] for k in ("won10", "won20", "damage20") + COUNTERS}
    for i in range(lo, hi):
        r = run.sim(deck, cmd, cfg, 5000 + i)
        cols["won10"].append(r["at_rounds"][REST]["won"])
        cols["won20"].append(r["won"])
        cols["damage20"].append(r["damage"])
        for k in COUNTERS:
            cols[k].append(float(r.get(k, 0.0)))
    return task, cols


def measure(n, out_path, procs=4):
    for arm in ARMS:
        arm_deck(arm)                       # fail fast on a missing name
    parts = AB._chunks(n, procs)
    tasks = [(a, lo, hi) for a in ARMS for lo, hi in parts]
    got = {}
    with Pool(procs) as pool:
        for task, cols in pool.imap_unordered(job, tasks):
            got[task] = cols
            print(f"  {task[0]:<20} seeds {task[1]}..{task[2]}",
                  file=sys.stderr)
    data = {a: {k: np.concatenate([got[(a, lo, hi)][k] for lo, hi in parts])
                for k in got[(a, *parts[0])]} for a in ARMS}
    json.dump(summarise(n, data), open(out_path, "w"), indent=1)
    print("saved", out_path)


def ci(d):
    d = np.asarray(d, float)
    return d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))


def summarise(n, data):
    """The paired differences and the mechanism means -- not the per-game
    columns, which are 50 times the size of every other results file."""
    out = {"n": n, "arms": ARMS, "compare": {}, "counters": {}, "repro": {}}
    for label, keep, drop in COMPARE:
        out["compare"][label] = {
            key: list(ci(data[keep][key] - data[drop][key]))
            for key in ("won10", "won20", "damage20")}
    for a in ARMS:
        out["counters"][a] = {k: float(data[a][k].mean()) for k in COUNTERS}
    path = AB.Run(DECK, n, (REST, TOP)).cache
    if os.path.exists(path):
        row = json.load(open(path))[ALTAR]
        for t, key in ((REST, "won10"), (TOP, "won20")):
            m = ci(data["base"][key] - data["-Altar"][key])[0]
            out["repro"][f"T{t}"] = [m, row[str(t)]["won"][0]]
    return out


def report(path):
    res = json.load(open(path))
    n = res["n"]
    print(f"RENDMAW SACRIFICE ENGINES, N={n:,} paired, seeds 5000.., staged "
          f"list, the tables' blank. value = with - without; * beats its bar.\n")
    for t, (m, cached) in res["repro"].items():
        same = abs(m - cached) < 1e-12
        print(f"  reproduces the cached Ashnod's Altar row at {t}: "
              f"{'YES' if same else 'NO'} ({m:+.6f} vs {cached:+.6f})")
    print()
    print(f"  {'':<38}{'win T10':>18}{'win T20':>18}{'damage T20':>16}")
    for label, cells_ in res["compare"].items():
        cells = []
        for key in ("won10", "won20", "damage20"):
            m, h = cells_[key]
            fmt = "{:+.4f} +-{:.4f}" if key != "damage20" else "{:+.2f} +-{:.2f}"
            cells.append(fmt.format(m, h) + ("*" if abs(m) > h else " "))
        print(f"  {label:<38}" + "".join(f"{c:>18}" for c in cells))
    rows = sum(res["compare"][l]["won20"][0] for l in
               ("Ashnod's Altar (the table's row)", "Village Rites (row)",
                "Dockside Chef (row)"))
    g = res["compare"]["outlets as a group (3)"]["won20"][0]
    print(f"\n  outlets at T20: group {g:+.4f} against the rows' sum "
          f"{rows:+.4f} -- interaction {g - rows:+.4f}")
    print("\n  MECHANISM, per game, T20 (base | -Altar | -Rites -Chef | -payoffs):")
    for k in COUNTERS:
        vals = [res["counters"][a][k] for a in ("base", "-Altar",
                                                "-Rites -Chef", "-payoffs")]
        print(f"    {k:<24}" + "".join(f"{v:>10.3f}" for v in vals))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        measure(int(sys.argv[1]), sys.argv[2])
