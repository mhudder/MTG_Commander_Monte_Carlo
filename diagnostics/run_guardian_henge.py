#!/usr/bin/env python3
"""Re-measure Guardian Project and The Great Henge after the §0z28 hook fix.

WHY. `azusa.make_permanent` hooks both cards on "a nontoken creature entered".
The §0z25 commit inserted the Guardian Project branch between The Great
Henge's counter and its draw, so the Henge's `draw(1)` ended up INSIDE the
Guardian Project `if`: Guardian Project drew TWICE per creature and the Henge
drew never. Guardian Project's +0.0481 +-0.0042 (§0z25) was measured on that
code. tests/test_azusa_batch3.py had pinned the Henge's draw and was failing
the whole time; nothing ran it.

Same method as the number it corrects: `tools/candidates.add_value`, Sylvan
Library victim slot, T20, N=15,000 paired -- so the corrected row sits on the
same scale as every other azusa candidate. The two mechanism counters are
printed beside `cards_drawn` because that is the check that would have caught
this: the extra draw was credited to `henge_draws`, so reading only
`guardian_project_draws` against eligible ETBs "proved" a bound the card was
already past. Compare `cards_drawn` against the SUM of every draw counter.

    python -m diagnostics.run_guardian_henge            # N=15000, ~10 min
    python -m diagnostics.run_guardian_henge --n=2000   # a quick look
"""
import sys

from edhmc.azusa import simulate as azusa_sim
from edhmc.decks.azusa_v1 import GUARDIAN_PROJECT, THE_GREAT_HENGE
from tools.candidates import add_value

N = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--n=")),
         15000)
VICTIM = "Sylvan Library"
EXTRA = ("cards_drawn", "guardian_project_draws", "henge_draws",
         "landfall_triggers", "lands_played")


def main() -> int:
    print(f"AZUSA -- Guardian Project and The Great Henge after the §0z28 fix\n"
          f"value over a blank in the {VICTIM} slot, T20, N={N:,} paired\n")
    head = f"  {'card':<20}{'damage':>16}{'win rate':>18}"
    for e in EXTRA:
        head += f"{e:>24}"
    print(head + f"{'P(deploy)':>11}")
    for cand in (GUARDIAN_PROJECT, THE_GREAT_HENGE):
        r = add_value("azusa", azusa_sim, 20, cand, VICTIM, n=N, extra=EXTRA)
        line = (f"  {cand.name:<20}"
                f"{r['damage'][0]:>+10.2f}+-{r['damage'][1]:<5.2f}"
                f"{r['won'][0]:>+11.4f}+-{r['won'][1]:<5.4f}")
        for e in EXTRA:
            line += f"{r[e][0]:>+18.2f}+-{r[e][1]:<5.2f}"
        print(line + f"{r['deploy']:>11.3f}")
    print("\nThe two draw counters are per game, deck B minus deck A; deck A "
          "never has the card, so each is the card's own count. With the "
          "fix, Guardian Project's henge_draws is 0 and The Great Henge's "
          "guardian_project_draws is 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
