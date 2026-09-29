#!/usr/bin/env python3
"""Mystery Booster Commander Edition: nine cards, twelve deck pairs, each
against its deck's cut (§0z74).

The set releases 2026-11-09 and its new cards read `not_legal` in Commander on
Scryfall; the owner's table plays them (2026-09-29). Text fetched 2026-09-29.

THE CUTS are each deck's weakest MODEL-EVALUATED row by win rate in the
current table, keeping the cut the last batch used wherever it is still in the
list (so the rows are comparable with §0z45's):

    deck        cut                          its row (T20 win rate)
    rendmaw     Ashnod's Altar               -0.0011 +-0.0011  dmg
    lorehold    Lightning Greaves            -0.0010 +-0.0029  --   (Ruby
                Medallion's point estimate is lower, -0.0031 +-0.0036, and
                also inside its bar; Greaves is the cut §0z53 named)
    karlov      Swiftfoot Boots              -0.0041 +-0.0022  both (the
                owner KEPT the Boots on 2026-09-26 for the shroud this model
                cannot fully see -- it is the named cut, not a decision)
    tivit       Tamiyo's Journal             +0.0020 +-0.0020  both
    shilgengar  Skullclamp                   -0.0008 +-0.0013  dmg  (Vampiric
                Rites, the last batch's cut, is already cut by the staged Lyra)
    azusa       Titania, Protector of Argoth +0.0030 +-0.0030  both (Yavimaya
                Elder, the last batch's cut, was committed out 2026-09-22)

None is a land, and all six classify MODEL-EVALUATED (§0z31).

    python -m diagnostics.run_mbc > results/mbc_batch.txt
    python -m diagnostics.run_mbc --smoke > results/mbc_smoke.txt   # tier 2
    python -m diagnostics.run_mbc --n=40                            # a check
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.registry import DECKS as REGISTRY
from edhmc.pending import DECKS as CATALOG, build_pending
from edhmc.experiment import run_ab, analyse

N = 15000
HORIZONS = (10, 20)
CUT = {
    "rendmaw": "Ashnod's Altar",
    "lorehold": "Lightning Greaves",
    "karlov": "Swiftfoot Boots",
    "tivit": "Tamiyo's Journal",
    "shilgengar": "Skullclamp",
    "azusa": "Titania, Protector of Argoth",
}
# (deck, card, the card's own counters -- which a smoke run must see move)
PLAN = [
    ("shilgengar", "Selenia, the Cursed Heart",
     ("won", "damage", "curses_made", "selenia_extra_life", "blood_made",
      "life_gained")),
    ("shilgengar", "Seluma, Light of Aysen",
     ("won", "damage", "seluma_hits", "seluma_returns", "blood_made")),
    ("shilgengar", "Thomil, the Destroyer",
     ("won", "damage", "thomil_zombies", "thomil_lords", "lord_sacrifices",
      "lord_self_damage", "blood_made")),
    ("shilgengar", "Pearl Collector",
     ("won", "damage", "mox_pearls_conjured", "pearl_lifelink_grants",
      "life_gained")),
    ("karlov", "Selenia, the Cursed Heart",
     ("won", "damage", "curses_made", "selenia_extra_life", "life_gained")),
    ("karlov", "Pearl Collector",
     ("won", "damage", "mox_pearls_conjured", "pearl_lifelink_grants",
      "lifegain_triggers")),
    ("tivit", "Venser, Visionary Traveler",
     ("won", "damage", "venser_blinks", "venser_counters", "tivit_triggers",
      "extra_turns")),
    ("tivit", "Dyfed, the Guiding Hand",
     ("won", "damage", "powerstones_made", "powerstone_mana", "dyfed_untaps",
      "dyfed_tutors", "extra_turns")),
    ("azusa", "Autumn Willow, Harmony",
     ("won", "damage", "willow_dryads", "willow_taps", "landfall_triggers")),
    ("rendmaw", "Davvol, Evincar of Rath",
     ("won", "damage", "davvol_triggers", "davvol_mana_spent",
      "davvol_mana_lost", "final_life")),
    ("rendmaw", "Thomil, the Destroyer",
     ("won", "damage", "thomil_zombies", "thomil_lords", "lord_sacrifices",
      "lord_self_damage")),
    ("lorehold", "Chief Magistrate of Mercadia",
     ("won", "damage", "monarch_gained", "monarch_draws",
      "magistrate_goblins", "magistrate_copies")),
]


def job(args):
    i, turns, n = args
    deck, add, metrics = PLAN[i]
    cut = CUT[deck]
    cards, cmd = build_pending(deck)
    assert any(c.name == cut for c in cards), f"{cut} is not in {deck}'s list"
    _mod, catalog = CATALOG[deck]
    t0 = time.time()
    ra, rb, _cfg = run_ab(cards, cmd, cut, catalog[add], n=n, turns=turns,
                          sim=REGISTRY[deck].sim)
    return (i, turns, time.time() - t0,
            float(np.mean([r["won"] for r in ra])),
            [(r.metric, r.mean_diff, r.ci_low, r.ci_high, r.significant)
             for r in analyse(ra, rb, metrics=metrics)])


def smoke_job(i):
    from tools.triage import smoke
    deck, add, metrics = PLAN[i]
    _mod, catalog = CATALOG[deck]
    return i, smoke(deck, catalog[add], n=1000, slot=CUT[deck])


def run_smoke(procs) -> int:
    print("Tier 2 smoke: each card against a blank in its cut's slot, N=1,000 "
          "(tools.triage.smoke). Its OWN counter must move.\n")
    missing = 0
    with Pool(procs) as pool:
        for i, rows in sorted(pool.imap_unordered(smoke_job, range(len(PLAN)))):
            deck, add, metrics = PLAN[i]
            own = [m for m in metrics if m not in ("won", "damage",
                                                   "life_gained", "blood_made",
                                                   "lifegain_triggers",
                                                   "tivit_triggers",
                                                   "extra_turns",
                                                   "landfall_triggers",
                                                   "final_life")]
            moved = {k for k, *_ in rows}
            ok = any(m in moved for m in own)
            missing += not ok
            print(f"{deck} + {add}  (slot: {CUT[deck]})   "
                  f"{'OWN COUNTER MOVED' if ok else '!!! OWN COUNTER SILENT'}")
            for k, with_card, with_blank, z in rows[:9]:
                zs = "" if z != z else f"z={z:+.1f}"
                print(f"    {k:<28}{with_card:>10.3f}{with_blank:>10.3f}  {zs}")
            print()
    return 1 if missing else 0


def main() -> int:
    n = next((int(a.split("=")[1]) for a in sys.argv[1:]
              if a.startswith("--n=")), N)
    procs = next((int(a.split("=")[1]) for a in sys.argv[1:]
                  if a.startswith("--procs=")), os.cpu_count() or 4)
    if "--smoke" in sys.argv:
        return run_smoke(procs)
    jobs = [(i, t, n) for i in range(len(PLAN)) for t in HORIZONS]
    print(f"Mystery Booster Commander Edition, §0z74. N={n:,} paired, same "
          f"seeds both legs, base = build_pending(<deck>).")
    for deck, add, _m in PLAN:
        print(f"  {deck:<12}-{CUT[deck]} +{add}")
    print()
    sys.stdout.flush()
    done = {}
    with Pool(procs) as pool:
        for i, turns, secs, base_won, rows in pool.imap_unordered(job, jobs):
            done[(i, turns)] = rows
            deck, add, _m = PLAN[i]
            print(f"  {deck}  -{CUT[deck]} +{add}  T{turns}  ({secs:.0f}s)   "
                  f"A-leg won {base_won:.4f}")
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<22}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()

    print("=" * 86)
    print("SUMMARY: win rate of the real swap, paired")
    print("=" * 86)
    print(f"{'deck':<12}{'swap':<54}{'win T10':>16}{'win T20':>16}")
    for i, (deck, add, _m) in enumerate(PLAN):
        cells = []
        for t in HORIZONS:
            rows = done.get((i, t))
            if rows is None:
                cells.append("     (not run)")
                continue
            _m2, diff, lo, hi, sig = rows[0]
            cells.append(f"{diff:>+8.4f} +-{(hi - lo) / 2:.4f}"
                         f"{' *' if sig else '  '}")
        print(f"{deck:<12}{'-' + CUT[deck] + ' +' + add:<54}"
              f"{cells[0]:>16}{cells[1]:>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
