#!/usr/bin/env python3
"""Harness validation: A/A control + measurement of the CRN variance reduction."""
import numpy as np
from edhmc.decks.rendmaw_v12 import build, SKULLCLAMP
from edhmc.experiment import run_ab, analyse


def main() -> int:
    # Everything below was module-level until 2026-09-17 (L2 of that day's
    # review): importing this file RAN the whole validation. It is a
    # function now; `python -m tools.validate` behaves exactly as before.

    deck, cmd = build()

    print("A/A control — identical decks under common random numbers.")
    print("Any nonzero difference here means the harness is leaking randomness.")
    same = [c for c in deck if c.name == "March of the World Ooze"][0]
    ra, rb, _ = run_ab(deck, cmd, "March of the World Ooze", same, n=5000)
    for r in analyse(ra, rb, metrics=("damage", "cards_drawn", "tokens_made")):
        print("  ", r.line("A", "A"))

    print("\n\nLorehold engine — A/A control")
    from edhmc.decks.lorehold_v16 import build as lh_build
    from edhmc.lorehold import simulate as lh_sim
    ld, lc = lh_build()
    same = [x for x in ld if x.name == "Verge Rangers"][0]
    la, lb, _ = run_ab(ld, lc, "Verge Rangers", same, n=3000,
                       cfg={"turns": 14}, sim=lh_sim)
    for r in analyse(la, lb, metrics=("mv_cheated", "miracles_cast", "damage")):
        print("  ", r.line("A", "A"))

    print("\nTivit engine — A/A control")
    from edhmc.decks.tivit_v1 import build as tv_build
    from edhmc.tivit import simulate as tv_sim
    td, tc = tv_build()
    same = [x for x in td if x.name == "Academy Manufactor"][0]
    ta, tb, _ = run_ab(td, tc, "Academy Manufactor", same, n=3000,
                       cfg={"turns": 14}, sim=tv_sim)
    for r in analyse(ta, tb, metrics=("artifacts_made", "votes_cast", "damage")):
        print("  ", r.line("A", "A"))

    print("\nKarlov engine — A/A control")
    from edhmc.decks.karlov_v2 import build as kv_build
    from edhmc.karlov import simulate as kv_sim
    kd, kc = kv_build()
    same = [x for x in kd if x.name == "Blood Artist"][0]
    ka, kb, _ = run_ab(kd, kc, "Blood Artist", same, n=3000,
                       cfg={"turns": 14}, sim=kv_sim)
    for r in analyse(ka, kb, metrics=("lifegain_triggers", "life_gained", "damage")):
        print("  ", r.line("A", "A"))

    print("\nShilgengar engine — A/A control")
    from edhmc.decks.shilgengar_v1 import build as sg_build
    from edhmc.shilgengar import simulate as sg_sim
    sd, sc = sg_build()
    same = [x for x in sd if x.name == "Blood Artist"][0]
    sa, sb, _ = run_ab(sd, sc, "Blood Artist", same, n=3000,
                       cfg={"turns": 14}, sim=sg_sim)
    for r in analyse(sa, sb, metrics=("blood_made", "creatures_sacrificed", "damage")):
        print("  ", r.line("A", "A"))

    print("\nAzusa engine — A/A control")
    from edhmc.decks.azusa_v1 import build as az_build
    from edhmc.azusa import simulate as az_sim
    ad, ac = az_build()
    same = [x for x in ad if x.name == "Lotus Cobra"][0]
    aa, ab_, _ = run_ab(ad, ac, "Lotus Cobra", same, n=3000,
                        cfg={"turns": 14}, sim=az_sim)
    for r in analyse(aa, ab_, metrics=("landfall_triggers", "lands_played", "damage")):
        print("  ", r.line("A", "A"))

    # ---------------------------------------------------------------------------
    # THE CRN AUDIT — the check the A/A control structurally cannot perform
    # ---------------------------------------------------------------------------
    # Every control above swaps a card for ITSELF. The two branches therefore never
    # diverge, take the same draws in the same order by construction, and print
    # +0.00 whether or not the engine leaks. Eleven mid-game leaks in five files
    # passed that check for months (§0z17 / queued item 19), and one of them —
    # Sunbird's Invocation — took 1,100 mid-game draws in the branch that had it
    # against 132 in the branch that did not, decorrelating 15.3% of seeds.
    #
    # So this runs REAL swaps, where the branches genuinely differ, and asserts the
    # structural invariant instead of a difference: once the opening hand is
    # decided, the game RNG is never touched again. Everything mid-game goes
    # through engine.CRNStreams, which is addressed by effect and occurrence rather
    # than consumed in order, so one branch doing more of something cannot shift
    # what the other branch reads. Nonzero below IS the bug.
    print("\n" + "=" * 78)
    print("CRN audit — real swaps, asserting the game RNG is sealed after the "
          "opening hand")
    print("=" * 78)

    # The swap is a REPLACEMENT-LEVEL BLANK, exactly as `ablation.py` builds one,
    # for two reasons: it is a real divergence (the branches play different games),
    # and it needs no per-deck candidate catalog, so every engine is covered by the
    # same three lines and a new engine cannot be quietly left out of the audit —
    # which is how §0z16's per-deck blind spot happened.
    #
    # THE LISTS ARE `build_pending`'s, NOT THE MODULES' — and getting this wrong
    # once already cost the audit its whole point. The first version built each
    # deck from its module, which is the COMMITTED list, and on that list
    # lorehold's `sunbird()` never executes: Sunbird's Invocation is STAGED, not
    # committed. So the audit ran clean over the single worst leak in the project
    # — the 1,100-draw one this section exists to prevent — and a mutation putting
    # that leak back was not detected, because the code was never reached.
    # `ablation.py` and `candidates.py` both measure `build_pending`, so that is
    # the list an audit of their randomness has to range over. §0z15's rule: a
    # check that skips a category is blind exactly where the bug is.
    from edhmc.engine import Card
    from edhmc.experiment import repl_priority
    from edhmc.pending import build_pending


    def blank_for(d):
        return Card(name="__crn_blank__", types=frozenset({"Creature"}),
                    cost={"gen": 3}, power=1, toughness=1,
                    priority=repl_priority(d))


    # One hand-picked real swap per deck -- the card is the decision a script
    # cannot make; the engine comes from the registry (§0z32), and a deck with no
    # case here is reported rather than silently skipped (§0z15).
    from edhmc.registry import DECKS as REGISTRY
    CRN_CASES = {
        "rendmaw": "March of the World Ooze",
        "lorehold": "Verge Rangers",
        "tivit": "Academy Manufactor",
        "karlov": "Blood Artist",
        "shilgengar": "Blood Artist",
        "azusa": "Lotus Cobra",
    }
    missing = sorted(set(REGISTRY) - set(CRN_CASES))
    if missing:
        raise SystemExit(f"validate.py has no CRN audit case for {missing}; "
                         f"add one -- a deck the audit skips is unaudited.")

    failures = 0
    for name, out_name in CRN_CASES.items():
        sim = REGISTRY[name].sim
        d, c = build_pending(name)
        ra_, rb_, _ = run_ab(d, c, out_name, blank_for(d), n=300,
                             cfg={"turns": 20, "crn_audit": True}, sim=sim)
        leaked_a = sum(r.get("rng_after_opening", 0) for r in ra_)
        leaked_b = sum(r.get("rng_after_opening", 0) for r in rb_)
        mid_a = sum(r.get("crn_draws", 0) for r in ra_)
        mid_b = sum(r.get("crn_draws", 0) for r in rb_)
        ok = (leaked_a == 0 and leaked_b == 0)
        failures += not ok
        print(f"  {name:<10} game-RNG draws after opening hand: "
              f"A={leaked_a} B={leaked_b}   {'OK' if ok else '*** LEAKING ***'}")
        print(f"  {'':<10} addressed mid-game draws (may differ — that is the "
              f"decks differing, not a leak): A={mid_a} B={mid_b}")

    if failures:
        raise SystemExit(
            "\nCRN AUDIT FAILED. A branch drew from the game RNG after its opening "
            "hand, so the two branches of every A/B test can consume different "
            "numbers from the same sequence and the pairing breaks from there on. "
            "Route the draw through engine.crn_random / crn_randrange / "
            "crn_shuffle. See KNOWN_ISSUES.md §0z17.")
    print("  -> sealed on every engine tested.")

    # The same real comparison as always, now run in the other direction: March
    # is in the deck as of v12, so this swaps it back out for the cut Skullclamp.
    print("\nCRN variance reduction on the real comparison:")
    ra, rb, _ = run_ab(deck, cmd, "March of the World Ooze", SKULLCLAMP, n=8000)
    a = np.array([r["damage"] for r in ra]); b = np.array([r["damage"] for r in rb])
    se_p = (b - a).std(ddof=1) / np.sqrt(len(a))
    se_i = np.sqrt(a.var(ddof=1) + b.var(ddof=1)) / np.sqrt(len(a))
    print(f"  corr(A,B)      = {np.corrcoef(a, b)[0,1]:.4f}")
    print(f"  paired SE      = {se_p:.4f}")
    print(f"  independent SE = {se_i:.4f}   ({se_i/se_p:.1f}x wider)")
    print(f"  CRN is worth ~{(se_i/se_p)**2:.0f}x the number of games.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
