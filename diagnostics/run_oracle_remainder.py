#!/usr/bin/env python3
"""What each of §0z151's fixes is worth, deck by deck (§0z116's remainder).

    python -m diagnostics.run_oracle_remainder 15000 OUTDIR [DECK ...]
    python -m diagnostics.run_oracle_remainder --report OUTDIR

Every fix ships behind a switch whose False is the old code, bit for bit
(`check_unchanged_decks --cfg`). So each fix is measured at ONE commit: the
staged list with every switch on (the new default) against the same list
with that one switch off, paired on seeds 5000.. . The "batch" row is every
switch off at once. One T20 game reports T10 too (`snapshot_rounds`, §0z93).
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

KNOBS = ("uncounterable", "cast_triggers_countered", "commander_cast_triggers",
         "modal_land_face", "spell_life_costs", "land_tax_shared",
         "tithe_shared", "wurm_route_pieces", "norn_text", "kalitas_text",
         "sorin_power", "bow_deathtouch")
# The decks each switch can move -- the cards it reads are in their lists.
# shilgengar's Tithe was already the shared rule: its arm is a zero check.
TOUCHES = {
    "rendmaw": ("uncounterable", "cast_triggers_countered", "modal_land_face",
                "spell_life_costs", "bow_deathtouch"),
    "lorehold": ("uncounterable", "cast_triggers_countered", "modal_land_face",
                 "land_tax_shared", "tithe_shared"),
    "karlov": ("uncounterable", "cast_triggers_countered",
               "commander_cast_triggers", "spell_life_costs",
               "land_tax_shared", "kalitas_text", "sorin_power"),
    "tivit": ("uncounterable", "cast_triggers_countered"),
    "shilgengar": ("modal_land_face", "spell_life_costs", "tithe_shared",
                   "wurm_route_pieces", "norn_text"),
    "azusa": ("uncounterable",),
}
MET = ("won", "damage", "countered", "counters_shielded",
       "life_lost_to_own_cards", "kalitas_zombies", "norn_kills",
       "land_tax_fetches", "treasures_made", "modal_land_faces",
       "deluge_life_paid")
CH = 8
TIMEOUT = 3600          # a job, in seconds: a hung worker fails the run


def arms(deck):
    return ["all", "none"] + [f"-{k}" for k in TOUCHES[deck]]


def arm_cfg(arm):
    if arm == "all":
        return {}
    if arm == "none":
        return {k: False for k in KNOBS}
    return {arm[1:]: False}


def job(a):
    deck, arm, lo, hi = a
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    cards, cmd = build_pending(deck)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,), **arm_cfg(arm))
    rows = []
    for s in range(lo, hi):
        out = R[deck].sim(list(cards), cmd, cfg, 5000 + s)
        t10 = out["at_rounds"][10]
        rows.append([float(t10.get("won", 0) or 0)]
                    + [float(out.get(m, 0) or 0) for m in MET])
    return rows


def col(outdir, deck, arm, name):
    a = np.load(os.path.join(outdir, f"{deck}_{arm}.npy"))
    return a[:, 0] if name == "won10" else a[:, 1 + MET.index(name)]


def report(outdir):
    print("§0z151: each fix = every switch on, minus that switch off "
          "(win rate, paired, 95% CI; * = outside its bar)\n")
    for deck in TOUCHES:
        if not os.path.exists(os.path.join(outdir, f"{deck}_all.npy")):
            continue
        n = len(col(outdir, deck, "all", "won"))
        print(f"{deck}  (N={n})")
        for arm in arms(deck)[1:]:
            label = "batch (all off)" if arm == "none" else arm[1:]
            cells = []
            for m in ("won10", "won"):
                d = col(outdir, deck, "all", m) - col(outdir, deck, arm, m)
                mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
                cells.append(f"{mu:+.4f} ±{ci:.4f}{'*' if abs(mu) > ci else ' '}")
            ident = all(np.array_equal(col(outdir, deck, "all", m),
                                       col(outdir, deck, arm, m))
                        for m in ("won10",) + MET)
            print(f"  {label:<26} T10 {cells[0]}   T20 {cells[1]}"
                  + ("   IDENTICAL" if ident else ""))
        print("  mechanism, a game (all on):  " + "  ".join(
            f"{m} {col(outdir, deck, 'all', m).mean():.3f}" for m in MET[2:]
            if col(outdir, deck, "all", m).any()))
        print()


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(sys.argv[2])
        sys.exit(0)
    n, outdir = int(sys.argv[1]), sys.argv[2]
    decks = sys.argv[3:] or list(TOUCHES)
    os.makedirs(outdir, exist_ok=True)
    tasks = [(d, a, k * n // CH, (k + 1) * n // CH)
             for d in decks for a in arms(d) for k in range(CH)]
    with Pool(4, maxtasksperchild=1) as p:
        pending = [p.apply_async(job, (t,)) for t in tasks]
        res = [r.get(timeout=TIMEOUT) for r in pending]
    cols = {}
    for (d, a, _, _), r in zip(tasks, res):
        cols.setdefault((d, a), []).extend(r)
    for (d, a), rows in cols.items():
        np.save(os.path.join(outdir, f"{d}_{a}.npy"), np.array(rows, float))
    print("saved", len(cols), "arms to", outdir)
