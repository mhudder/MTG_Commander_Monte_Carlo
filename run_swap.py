#!/usr/bin/env python3
"""
Skullclamp  -->  March of the World Ooze, in Rendmaw v11.

Usage:
    python run_swap.py [n_games]
"""
import sys
import statistics as st

from edhmc.decks.rendmaw_v11 import build, MARCH_OF_THE_WORLD_OOZE
from edhmc.experiment import (run_ab, analyse, analyse_conditional,
                              report, lethal_curve)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000

deck, commander = build()
rows_a, rows_b, cfg = run_ab(deck, commander,
                             out_card="Skullclamp",
                             in_card=MARCH_OF_THE_WORLD_OOZE,
                             n=N)

res = analyse(rows_a, rows_b)
report(rows_a, rows_b, "Skullclamp", "March of the World Ooze", cfg, res)

print("\nP(cumulative damage >= 120) by turn")
print(f"{'turn':<6}{'A: Skullclamp':>16}{'B: March':>12}{'diff':>10}")
ca, cb = lethal_curve(rows_a, cfg), lethal_curve(rows_b, cfg)
for (t, pa), (_, pb) in zip(ca, cb):
    if pa or pb:
        print(f"{t:<6}{pa:>16.3f}{pb:>12.3f}{pb - pa:>+10.3f}")

# --- diagnostics ---------------------------------------------------------
print("\nDiagnostics")
cast_a = st.mean([1.0 if r["cast_test_card"] else 0.0 for r in rows_a])
cast_b = st.mean([1.0 if r["cast_test_card"] else 0.0 for r in rows_b])
print(f"  P(test card actually resolves by T{cfg['turns']}):"
      f"  Skullclamp {cast_a:.3f}   March {cast_b:.3f}")
print(f"  Mean turn it resolves:"
      f"  Skullclamp {st.mean([r['test_card_turn'] for r in rows_a if r['cast_test_card']]):.2f}"
      f"   March {st.mean([r['test_card_turn'] for r in rows_b if r['cast_test_card']]):.2f}")
print(f"  Mean Skullclamp activations per game: "
      f"{st.mean([r['clamp_activations'] for r in rows_a]):.2f}")
print(f"  Mean turns with >=1 one-toughness creature available: "
      f"{st.mean([r['fodder_turns'] for r in rows_a]):.2f} / {cfg['turns']}")

ans_a = [r for r in rows_a if r["cast_test_card"]]
ans_b = [r for r in rows_b if r["cast_test_card"]]
cnt_a = [r for r in rows_a if r["cast_test_card"] or r["test_card_countered"]]
cnt_b = [r for r in rows_b if r["cast_test_card"] or r["test_card_countered"]]
print("\n  Of the games where you tried to deploy the card, the pod answered it:")
print(f"    Skullclamp  countered {st.mean([r['test_card_countered'] for r in cnt_a]):.3f}"
      f"   destroyed {st.mean([min(1,r['test_card_removed']) for r in cnt_a]):.3f}")
print(f"    March       countered {st.mean([r['test_card_countered'] for r in cnt_b]):.3f}"
      f"   destroyed {st.mean([min(1,r['test_card_removed']) for r in cnt_b]):.3f}")


# --- conditional on the card actually showing up -------------------------
keep, res_c = analyse_conditional(rows_a, rows_b)
print(f"\nConditional on drawing the swapped card (n={len(keep):,}, "
      f"{len(keep)/len(rows_a):.1%} of games)")
report([rows_a[i] for i in keep], [rows_b[i] for i in keep],
       "Skullclamp", "March of the World Ooze", cfg, res_c)

# --- sensitivity to the unblocked-damage assumption ----------------------
print("\nSensitivity: does the verdict survive a different pod?")
pods = {"no interaction (old model)": dict(opponents=False, derived_blocking=False),
        "all bracket 2": dict(pod_brackets=(2, 2, 2)),
        "mixed (2,3,4)": dict(pod_brackets=(2, 3, 4)),
        "all bracket 3": dict(pod_brackets=(3, 3, 3)),
        "all bracket 4": dict(pod_brackets=(4, 4, 4))}
print(f"  {'pod':<28}{'damage B-A':>18}{'cards drawn B-A':>20}")
for label, override in pods.items():
    ra, rb, c2 = run_ab(deck, commander, "Skullclamp", MARCH_OF_THE_WORLD_OOZE,
                        n=max(3000, N // 4), cfg=override, base_seed=99)
    dd, dc = analyse(ra, rb, metrics=("damage", "cards_drawn"))
    print(f"  {label:<28}{dd.mean_diff:>+9.2f} [{dd.ci_low:+.1f},{dd.ci_high:+.1f}]"
          f"{dc.mean_diff:>+11.2f} [{dc.ci_low:+.1f},{dc.ci_high:+.1f}]")
