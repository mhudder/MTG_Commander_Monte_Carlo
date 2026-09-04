#!/usr/bin/env python3
"""
Lorehold, the Historian v15:
    OUT  Verge Rangers, Triumph of Saint Katherine
    IN   Molecule Man, The Dawning Archaic

Runs the combined 2-for-2 swap plus each half in isolation, so the effect can
be attributed rather than just observed.

Usage:  python run_lorehold_swap.py [n_games] [turns]
"""
import sys
import statistics as st

from edhmc.decks.lorehold_v16 import build, MOLECULE_MAN, THE_DAWNING_ARCHAIC
from edhmc.lorehold import simulate as lh_sim
from edhmc.experiment import run_ab, analyse, report

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
TURNS = int(sys.argv[2]) if len(sys.argv) > 2 else 14

METRICS = ("mv_cheated", "miracles_cast", "total_mv_cast", "spells_cast",
           "cards_drawn", "damage", "spell_damage", "combat_damage", "won",
           "mana_floated", "free_casts")

deck, commander = build()

EXPERIMENTS = [
    ("combined 2-for-2",
     ["Triumph of Saint Katherine", "Verge Rangers"],
     [MOLECULE_MAN, THE_DAWNING_ARCHAIC]),
    ("Molecule Man only (for Triumph)",
     ["Triumph of Saint Katherine"], [MOLECULE_MAN]),
    ("Dawning Archaic only (for Verge Rangers)",
     ["Verge Rangers"], [THE_DAWNING_ARCHAIC]),
]

for label, outs, ins in EXPERIMENTS:
    a, b, cfg = run_ab(deck, commander, outs, ins, n=N,
                       cfg={"turns": TURNS}, sim=lh_sim)
    res = analyse(a, b, metrics=METRICS)
    print()
    report(a, b, "current", label, cfg, res)

    print("  Diagnostics")
    for name, rows in (("A (current)", a), (label, b)):
        cast = st.mean([r["cast_test_card"] for r in rows])
        turns_ = [r["test_card_turn"] for r in rows if r["cast_test_card"]]
        print(f"    {name:<42} P(deploy)={cast:.3f}"
              f"  mean turn={st.mean(turns_) if turns_ else float('nan'):.2f}"
              f"  answered={st.mean([min(1, r['test_card_answered']) for r in rows]):.3f}")

# --- how much of the effect is the horizon? -------------------------------
print("\n\nSensitivity: game length")
print(f"  {'turns':<8}{'mv_cheated B-A':>20}{'miracles B-A':>18}")
for t in (10, 12, 14, 16):
    a, b, _ = run_ab(deck, commander,
                     ["Triumph of Saint Katherine", "Verge Rangers"],
                     [MOLECULE_MAN, THE_DAWNING_ARCHAIC],
                     n=max(3000, N // 4), cfg={"turns": t},
                     base_seed=77, sim=lh_sim)
    dm, dc = analyse(a, b, metrics=("mv_cheated", "miracles_cast"))
    print(f"  {t:<8}{dm.mean_diff:>+11.2f} [{dm.ci_low:+.1f},{dm.ci_high:+.1f}]"
          f"{dc.mean_diff:>+10.2f} [{dc.ci_low:+.2f},{dc.ci_high:+.2f}]")

print("\nSensitivity: pod power")
print(f"  {'pod':<28}{'mv_cheated B-A':>20}")
for label, br in (("no interaction", None), ("all bracket 2", (2, 2, 2)),
                  ("mixed 2/3/4", (2, 3, 4)), ("all bracket 4", (4, 4, 4))):
    over = {"turns": TURNS}
    over.update({"opponents": False} if br is None else {"pod_brackets": br})
    a, b, _ = run_ab(deck, commander,
                     ["Triumph of Saint Katherine", "Verge Rangers"],
                     [MOLECULE_MAN, THE_DAWNING_ARCHAIC],
                     n=max(3000, N // 4), cfg=over, base_seed=77, sim=lh_sim)
    d = analyse(a, b, metrics=("mv_cheated",))[0]
    print(f"  {label:<28}{d.mean_diff:>+11.2f} [{d.ci_low:+.1f},{d.ci_high:+.1f}]")
