#!/usr/bin/env python3
"""What each fix in a batch of oracle fixes is worth, deck by deck: §0z151
(§0z116's remainder) and §0z153 (queue item 5's last lines).

    python -m diagnostics.run_oracle_remainder 15000 OUTDIR [DECK ...] [--batch=0z153]
    python -m diagnostics.run_oracle_remainder --report OUTDIR [--batch=0z153]

`--batch` is 0z151 when omitted. Every fix ships behind a switch whose False
is the old code, bit for bit (`check_unchanged_decks --cfg`). So each fix is
measured at ONE commit: the staged list with every switch on (the new
default) against the same list with that one switch off, paired on seeds
5000.. . The "batch" row is every switch of the batch off at once. One T20
game reports T10 too (`snapshot_rounds`, §0z93).
"""
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

# knobs: every switch of the batch. touches: the decks each switch can move --
# the cards it reads are in their lists. met: the columns kept.
BATCHES = {
    "0z151": {
        "knobs": ("uncounterable", "cast_triggers_countered",
                  "commander_cast_triggers", "modal_land_face",
                  "spell_life_costs", "land_tax_shared", "tithe_shared",
                  "wurm_route_pieces", "norn_text", "kalitas_text",
                  "sorin_power", "bow_deathtouch"),
        # shilgengar's Tithe was already the shared rule: a zero check.
        "touches": {
            "rendmaw": ("uncounterable", "cast_triggers_countered",
                        "modal_land_face", "spell_life_costs",
                        "bow_deathtouch"),
            "lorehold": ("uncounterable", "cast_triggers_countered",
                         "modal_land_face", "land_tax_shared", "tithe_shared"),
            "karlov": ("uncounterable", "cast_triggers_countered",
                       "commander_cast_triggers", "spell_life_costs",
                       "land_tax_shared", "kalitas_text", "sorin_power"),
            "tivit": ("uncounterable", "cast_triggers_countered"),
            "shilgengar": ("modal_land_face", "spell_life_costs",
                           "tithe_shared", "wurm_route_pieces", "norn_text"),
            "azusa": ("uncounterable",),
        },
        "met": ("won", "damage", "countered", "counters_shielded",
                "life_lost_to_own_cards", "kalitas_zombies", "norn_kills",
                "land_tax_fetches", "treasures_made", "modal_land_faces",
                "deluge_life_paid"),
    },
    "0z153": {
        "knobs": ("extra_turn_full", "reservoir_any_time", "extort_hybrid",
                  "konrad_text", "sorin_loyalty", "gearhulk_best",
                  "snake_types", "throne_etb", "beast_quest", "coat_types",
                  "frostfang_connect", "act_pod_count", "tithe_forced_draws",
                  "alt_win_at_upkeep", "dilemma_counters", "jays_discard",
                  "tyrant_death", "speaker_taps", "resplendent_each_end",
                  "revel_at_upkeep", "shepherd_plains", "provisioner_treasure",
                  "momentous_biggest", "realms_text", "search_shuffle"),
        "touches": {
            "rendmaw": ("gearhulk_best", "snake_types", "throne_etb",
                        "beast_quest", "coat_types", "frostfang_connect"),
            "lorehold": ("extra_turn_full", "act_pod_count",
                         "tithe_forced_draws"),
            "karlov": ("reservoir_any_time", "extort_hybrid", "konrad_text",
                       "sorin_loyalty"),
            "tivit": ("alt_win_at_upkeep", "dilemma_counters", "jays_discard",
                      "tyrant_death"),
            "shilgengar": ("speaker_taps", "resplendent_each_end",
                           "revel_at_upkeep", "shepherd_plains"),
            "azusa": ("provisioner_treasure", "momentous_biggest",
                      "realms_text", "search_shuffle"),
        },
        "met": ("won", "damage", "extra_turns_taken", "konrad_card_triggers",
                "konrad_mills", "sorin_reanimations", "frostfang_draws",
                "tithe_forced_treasures", "tyrant_sacrifices",
                "speaker_angels", "resplendent_pod_angels", "realms_binned",
                "library_shuffles"),
    },
}
CH = 8
TIMEOUT = 3600          # a job, in seconds: a hung worker fails the run


def arms(batch, deck):
    return ["all", "none"] + [f"-{k}" for k in BATCHES[batch]["touches"][deck]]


def arm_cfg(batch, arm):
    if arm == "all":
        return {}
    if arm == "none":
        return {k: False for k in BATCHES[batch]["knobs"]}
    return {arm[1:]: False}


def job(a):
    batch, deck, arm, lo, hi = a
    from edhmc.registry import DECKS as R
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    met = BATCHES[batch]["met"]
    cards, cmd = build_pending(deck)
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               **arm_cfg(batch, arm))
    rows = []
    for s in range(lo, hi):
        out = R[deck].sim(list(cards), cmd, cfg, 5000 + s)
        t10 = out["at_rounds"][10]
        rows.append([float(t10.get("won", 0) or 0)]
                    + [float(out.get(m, 0) or 0) for m in met])
    return rows


def col(batch, outdir, deck, arm, name):
    a = np.load(os.path.join(outdir, f"{deck}_{arm}.npy"))
    met = BATCHES[batch]["met"]
    return a[:, 0] if name == "won10" else a[:, 1 + met.index(name)]


def report(batch, outdir):
    met = BATCHES[batch]["met"]
    print(f"§{batch}: each fix = every switch on, minus that switch off "
          "(win rate, paired, 95% CI; * = outside its bar)\n")
    for deck in BATCHES[batch]["touches"]:
        if not os.path.exists(os.path.join(outdir, f"{deck}_all.npy")):
            continue
        c = lambda arm, m: col(batch, outdir, deck, arm, m)   # noqa: E731
        print(f"{deck}  (N={len(c('all', 'won'))})")
        for arm in arms(batch, deck)[1:]:
            label = "batch (all off)" if arm == "none" else arm[1:]
            cells = []
            for m in ("won10", "won"):
                d = c("all", m) - c(arm, m)
                mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
                cells.append(f"{mu:+.4f} ±{ci:.4f}{'*' if abs(mu) > ci else ' '}")
            ident = all(np.array_equal(c("all", m), c(arm, m))
                        for m in ("won10",) + met)
            print(f"  {label:<26} T10 {cells[0]}   T20 {cells[1]}"
                  + ("   IDENTICAL" if ident else ""))
        print("  mechanism, a game (all on):  " + "  ".join(
            f"{m} {c('all', m).mean():.3f}" for m in met[2:]
            if c("all", m).any()))
        print()


if __name__ == "__main__":
    batch = next((a.split("=", 1)[1] for a in sys.argv[1:]
                  if a.startswith("--batch=")), "0z151")
    args = [a for a in sys.argv[1:] if not a.startswith("--batch=")]
    if args[0] == "--report":
        report(batch, args[1])
        sys.exit(0)
    n, outdir = int(args[0]), args[1]
    decks = args[2:] or list(BATCHES[batch]["touches"])
    os.makedirs(outdir, exist_ok=True)
    tasks = [(batch, d, a, k * n // CH, (k + 1) * n // CH)
             for d in decks for a in arms(batch, d) for k in range(CH)]
    with Pool(4, maxtasksperchild=1) as p:
        pending = [p.apply_async(job, (t,)) for t in tasks]
        res = [r.get(timeout=TIMEOUT) for r in pending]
    cols = {}
    for (_, d, a, _, _), r in zip(tasks, res):
        cols.setdefault((d, a), []).extend(r)
    for (d, a), rows in cols.items():
        np.save(os.path.join(outdir, f"{d}_{a}.npy"), np.array(rows, float))
    print("saved", len(cols), "arms to", outdir)
