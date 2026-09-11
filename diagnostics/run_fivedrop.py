#!/usr/bin/env python3
"""The Lorehold Penance slot, measured three ways against the same cut.

NOT ACTUALLY A "FIVE-DROP SLOT". Galvanoth and Caldera Pyremaw are both
{3}{R}{R}, MV 5. Radiant Scrollwielder is {2}{R}{W}, MV **4**. That is worth
saying out loud, because the whole diagnosis of Galvanoth was that it "is cast
in only 15.6% of games, on turn 9.8" — the card arrives too late in too few
games. A four-drop is a different answer to that problem than a better
five-drop is, and the ledger's phrasing hid the option.


WHY THIS EXISTS. `pending.py` stages `-Penance +Galvanoth` and its own note
says: "cut Penance, but find a better five-drop than Galvanoth before writing
this to the .xlsx." The 2026-09-05 re-verification found that two of the three
contenders had been measured on a broken implementation:

  Galvanoth             correct. +0.0128 [+0.0078, +0.0180] win at 20 turns.
  Caldera Pyremaw       measured as a GROUND creature. tag_flying.py walked
                        mod.build() only, so candidates were constructed with
                        flying=False. It is a 3/3 FLIER that grows.
  Radiant Scrollwielder measured off `library[-1]`. The card reads "exile an
                        instant or sorcery at random FROM YOUR GRAVEYARD".

Both are fixed, so all three are now measured on the same engine, against the
same cut, with common random numbers.

READ THE SCROLLWIELDER NUMBER AS A FLOOR: "instant and sorcery spells you
control have lifelink" is still unmodelled. The other two are modelled in full.

    python run_fivedrop.py                # all three, both horizons
    python run_fivedrop.py galvanoth      # one
    python run_fivedrop.py --n 3000       # smaller sample
"""
import sys

from edhmc.lorehold import simulate as lorehold_sim
from edhmc.pending import build_pending
from edhmc.experiment import run_ab, analyse

from edhmc.decks.lorehold_v16 import (GALVANOTH, CALDERA_PYREMAW,
                                      RADIANT_SCROLLWIELDER)

CUT = "Penance"

CANDIDATES = {
    "galvanoth": GALVANOTH,
    "caldera": CALDERA_PYREMAW,
    "scrollwielder": RADIANT_SCROLLWIELDER,
}

METRICS = ("won", "damage", "mv_cheated", "miracles_cast", "cards_drawn",
           "stranded_mv", "upkeep_free_casts", "scrollwielder_exiles",
           "scrollwielder_casts", "bombardment_copies", "final_life")


def main():
    argv = sys.argv[1:]
    n = 6000
    if "--n" in argv:
        i = argv.index("--n")
        n = int(argv[i + 1])
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]

    # apply_pending=False: -Penance +Galvanoth IS the staged change, so the
    # comparison has to be against the list as it stood before it was staged,
    # or Penance is already gone and _swap_many raises.
    deck, cmd = build_pending("lorehold", apply_pending=False)

    print(f"Lorehold five-drop: -{CUT} +X, {n:,} paired games, "
          f"common random numbers, pod v3 (default).")
    print("Scrollwielder's lifelink clause is unmodelled -> its rows are a "
          "FLOOR.\n")

    if "--head2head" in sys.argv:
        # THE DECISION, measured directly. Three separate swaps against a
        # common baseline have overlapping CIs and cannot be ranked against
        # each other; this puts the two contenders in the same paired
        # comparison, where the shared 98 cards cancel.
        staged, scmd = build_pending("lorehold")     # Galvanoth already in
        for turns in (10, 20):
            ra, rb, _ = run_ab(staged, scmd, ["Galvanoth"], [CALDERA_PYREMAW],
                               n=n, cfg={"turns": turns}, sim=lorehold_sim)
            print(f"=== HEAD TO HEAD  -Galvanoth +Caldera Pyremaw "
                  f"({turns} turns, n={n:,})")
            for r in analyse(ra, rb, metrics=METRICS):
                if r.mean_a == 0 and r.mean_b == 0:
                    continue
                star = " *" if r.significant else "  "
                print(f"      {r.metric:<22}{r.mean_a:>8.3f} ->{r.mean_b:>8.3f}"
                      f"  {r.mean_diff:>+9.4f}"
                      f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
            print()
            sys.stdout.flush()
        return

    for key in (args or list(CANDIDATES)):
        card = CANDIDATES[key]
        for turns in (10, 20):
            ra, rb, cfg = run_ab(deck, cmd, [CUT], [card], n=n,
                                 cfg={"turns": turns}, sim=lorehold_sim)
            res = analyse(ra, rb, metrics=METRICS)
            print(f"=== -{CUT} +{card.name}   ({turns} turns, n={n:,})")
            for r in res:
                if r.mean_a == 0 and r.mean_b == 0:
                    continue            # counter that neither branch touches
                star = " *" if r.significant else "  "
                print(f"      {r.metric:<22}{r.mean_a:>8.3f} ->{r.mean_b:>8.3f}"
                      f"  {r.mean_diff:>+9.4f}"
                      f"  [{r.ci_low:>+8.4f}, {r.ci_high:>+8.4f}]{star}")
            print()
            sys.stdout.flush()


if __name__ == "__main__":
    main()
