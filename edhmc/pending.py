"""
edhmc.pending — staged deck changes, not yet written to the spreadsheets.

The .xlsx files remain the system of record. This module holds changes that
have been decided but not yet applied to all three legs (deck module, .xlsx,
this ledger), so that:

  1. further A/B tests run against the CURRENT intended list rather than a
     stale baseline, and
  2. there is one place to read off the full pending diff when it is time to
     update the spreadsheets.

Usage:
    from edhmc.pending import build_pending, ledger
    deck, commander = build_pending("rendmaw")     # changes applied
    deck, commander = build_pending("rendmaw", apply_pending=False)  # original
    ledger()                                       # print the diff

To stage another change, append to CHANGES. To commit, update the spreadsheet
and the deck module, then move the entry to COMMITTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from edhmc.decks import rendmaw_v12, lorehold_v16, karlov_v1
from edhmc.experiment import _swap_many


@dataclass
class Change:
    deck: str
    remove: str
    add: str
    staged: str                 # date staged
    rationale: str
    evidence: str = ""
    notes: str = ""
    reverified: str = ""        # re-measured after an engine change


# ---------------------------------------------------------------------------
# Committed — reflected in BOTH the deck module and the .xlsx
# ---------------------------------------------------------------------------
COMMITTED: list[Change] = [
    Change(
        deck="lorehold",
        remove="Triumph of Saint Katherine",
        add="The Dawning Archaic",
        staged="2026-08-31",
        rationale=(
            "Weakest miracle hit in the deck replaced by its cheapest late-game "
            "haymaker. A 5/5 lifelink body is a poor payoff in a deck whose "
            "miracle targets are 7-12 MV spells, and its death trigger shuffles "
            "the top six cards of the library, which is where this deck keeps "
            "its resources."
        ),
        evidence=(
            "12,000 paired games, 14 turns, mixed pod: mv_cheated +2.46 "
            "[+2.28, +2.64]. Archaic's cost reduction leaves it at ~{2.45} "
            "effective, since the deck averages 8.5 instants/sorceries in the "
            "graveyard by turn 14."
        ),
        notes=(
            "Damage -0.52 and P(win) flat. Taken for the mana-cheat and "
            "top-end case, not for speed. This was the narrower, "
            "better-supported half of the four-card change originally "
            "considered; Molecule Man was NOT taken and Verge Rangers stays."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Monologue Tax",
        add="Arcane Bombardment",
        staged="2026-08-31",
        rationale=(
            "Bombardment reads 'your first instant or sorcery each turn', not "
            "each of YOUR turns. Lorehold's rummage opens a miracle window on "
            "all three opponents' turns, so a round can produce four triggers "
            "instead of one, and the exile pile accumulates so the Nth trigger "
            "copies all N cards."
        ),
        evidence=(
            "6,000 paired games vs the pending v16 list, 14 turns, mixed pod: "
            "mv_cheated +7.24 [+4.74, +10.05], damage +5.17 [+3.22, +7.43], "
            "win rate +0.01 [+0.00, +0.01]."
        ),
        notes=(
            "HIGH VARIANCE. Fires in only 7.9% of games; when it does it "
            "averages 13.2 free copies (max observed 136). Median damage barely "
            "moves while the mean jumps - the whole gain is in the top decile. "
            "Also strongly horizon-dependent: near zero at 10 turns, large at "
            "14+. Monologue Tax was modelled generously at 2 Treasures a round "
            "for three opponents and still lost."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Urabrask // The Great Work",
        add="Monastery Mentor",
        staged="2026-08-31",
        rationale=(
            "A body-count fix for a deck with only eleven creatures and a "
            "top-heavy curve. Nearly every spell here is noncreature, so Mentor "
            "converts the deck's existing spell density into a board."
        ),
        evidence=(
            "6,000 paired games vs the pending v16 list, 14 turns: damage +4.42 "
            "[+3.74, +5.12], combat damage +4.95, win rate +0.01 [+0.01, +0.02]. "
            "mv_cheated -0.14, i.e. it contributes bodies, not mana."
        ),
        notes=(
            "Urabrask was UNDER-modelled in earlier ablations - its 1 damage per "
            "instant/sorcery and its {R} mana ability were not implemented, which "
            "is why it scored near zero. Both are now in the engine; cutting it "
            "costs 0.53 spell damage. It lost anyway. Tension to watch: the deck "
            "runs eight board wipes, which kill your own Monks. The engine does "
            "not model your own wipes hitting your board, so Mentor is flattered "
            "here to an unknown degree."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Hidden Retreat",
        add="Double Vision",
        staged="2026-09-01",
        rationale=(
            "Same 'each turn' clause that makes Arcane Bombardment strong here: "
            "Lorehold's rummage opens a window on all three opponents' turns, so "
            "a round can produce four triggers instead of one. It copies the "
            "miracled spell too, so a ten-drop miracled for {2} becomes two. "
            "Hidden Retreat's cost is not mana but a CARD - putting one on top "
            "converts your next draw into something you already held."
        ),
        evidence=(
            "8,000 paired games, mixed pod: win rate +0.017 [+0.012, +0.021], "
            "mv_cheated +3.16 [+2.63, +3.68], damage +2.74 [+1.45, +4.03], "
            "cards drawn +0.79. Double Vision resolves in 17.2% of games on turn "
            "9.7 and averages 2.39 copies when it does; answered only 28.3% of "
            "the time, against 57% for Bombardment."
        ),
        notes=(
            "The copy is PUT ON THE STACK, not cast (ruling 2020-06-23), so it "
            "does NOT trigger Guttersnipe, Monastery Mentor or Bombardment - "
            "unlike Mastery's and Bombardment's copies, which are genuinely "
            "cast. That reduction is already priced in. Note also that roughly "
            "half the gain is Hidden Retreat being bad rather than Double Vision "
            "being good: against a same-cost blank, Double Vision's win-rate "
            "contribution does not clear its error bar."
        ),
    ),
    Change(
        deck="rendmaw",
        remove="Skullclamp",
        add="March of the World Ooze",
        staged="2026-08-31",
        rationale=(
            "Skullclamp has almost no fodder here: Rendmaw's Birds are 2/2, and "
            "the clamp makes them 3/1, so they live. It finds a legal "
            "1-toughness target on 0.35 turns per game. Cutting it was "
            "justified independently of the replacement."
        ),
        evidence=(
            "20,000 paired games, 10 turns, mixed pod: damage +2.85 "
            "[+2.64, +3.06], cards drawn -1.01 [-1.06, -0.96]."
        ),
        notes=(
            "The margin shrinks as the pod gets stronger: +5.86 damage at all "
            "bracket 2, +1.09 at all bracket 4, where it is close to a wash "
            "against the card-draw loss. March is also answered ~57% of the "
            "times you deploy it, against ~15% for Skullclamp. Worth "
            "revisiting if the regular pod is high-powered."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-03 on the oracle-corrected engine, because "
            "the original evidence predates that audit and both cards were "
            "touched by it. 6,000 paired games, mixed pod: at 10 turns damage "
            "+3.02 [+2.57, +3.48] and win rate +0.0077 [+0.0053, +0.0101]; at "
            "20 turns damage +2.79 [+2.17, +3.40] and win rate +0.0018 "
            "[-0.0041, +0.0077], i.e. inside its bar at the long horizon. "
            "Sign and rank survive the whole horizon range, and damage and "
            "cards drawn both land within a rounding error of the original "
            "(+2.85 and -1.01). The decision stands."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Staged — decided, not yet in the spreadsheets
# ---------------------------------------------------------------------------
CHANGES: list[Change] = [
    Change(
        deck="karlov",
        remove="Swamp",
        add="Starscape Cleric",
        staged="2026-09-04",
        rationale=(
            "Marauding Blight-Priest's trigger word for word — 'whenever you "
            "gain life, each opponent loses 1 life' — at half the mana, on a "
            "two-power flier. This deck produces 16+ lifegain EVENTS a game "
            "and each one is 3 pod life, so the rate matters far more than the "
            "body. It out-damages every card in ablation_karlov.txt: +4.13 "
            "over a blank at 10 turns against Kambal's +3.64."
        ),
        evidence=(
            "Measured as the real 2-for-2 (this and Enduring Tenacity in, a "
            "Swamp and Whispersilk Cloak out), 6,000 paired games, mixed pod: "
            "win rate +0.0353 [+0.0297, +0.0413] at 10 turns and +0.0480 "
            "[+0.0400, +0.0558] at 20; damage +6.94 and +7.05. Alone against a "
            "blank of the same cost it is +4.13+-0.46 damage and +0.0118+-"
            "0.0035 win at 10 turns, both signals at both horizons."
        ),
        notes=(
            "FLOOR in two places. Flying is unmodelled anywhere in the engine "
            "(queued work item 1), and its Offspring cost is paid in only 25% "
            "of casts because the greedy main phase has usually spent the mana "
            "already. Its 'can't block' drawback is also unmodelled, but the "
            "engine never blocks with your creatures, so that costs it "
            "nothing it would otherwise have. The land cut is the real price: "
            "stranded_mv +1.85 at 10 turns. 37 lands -> 36."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    Change(
        deck="karlov",
        remove="Whispersilk Cloak",
        add="Enduring Tenacity",
        staged="2026-09-04",
        rationale=(
            "A FOURTH Exquisite Blood combo piece, which is the larger half of "
            "its value. Its trigger is Sanguine Bond's word for word ('whenever "
            "you gain life, target opponent loses that much life'), so it loops "
            "with Exquisite Blood unaided and with no mana; karlov.COMBO_LOOP "
            "was corrected to include it. It assembles the loop in 8.8% of the "
            "games it resolves. Whispersilk Cloak ablates to +0.32/+0.25 "
            "damage and -0.0007 win rate — inside its own bars, and three "
            "other shroud sources remain (Swiftfoot Boots, Mother of Runes, "
            "Lightning Greaves)."
        ),
        evidence=(
            "Against a blank of the same cost, 6,000 paired games: win rate "
            "+0.0195 [+0.0154, +0.0236] at 10 turns and +0.0217 [+0.0163, "
            "+0.0271] at 20; damage +2.74 and +2.48. That win rate would rank "
            "FOURTH in the whole deck, behind only Felidar Sovereign "
            "(+0.0587), Exquisite Blood (+0.0242) and Vito (+0.0228)."
        ),
        notes=(
            "This is the ADDITION measurement, so the redundancy with Sanguine "
            "Bond and Vito is already priced in — unlike leave-one-out, which "
            "understates every member of an interchangeable group. Its death "
            "trigger fires 0.60 times a game: it returns as a noncreature "
            "enchantment and keeps draining through a wrath."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    Change(
        deck="karlov",
        remove="Lightning Greaves",
        add="Exemplar of Light",
        staged="2026-09-04",
        rationale=(
            "Lightning Greaves is the worst card in the deck by win rate "
            "(-0.0040+-0.0029, signal 'both') and the only one whose damage is "
            "negative at both horizons. Cutting it still leaves Swiftfoot "
            "Boots and Mother of Runes as shroud sources for the commander. "
            "Exemplar of Light takes a +1/+1 counter per lifegain EVENT — 16.3 "
            "of them a game — and draws a card the first time each turn it "
            "gets one, so it is a threat and a draw engine off the same "
            "trigger the whole deck is built on."
        ),
        evidence=(
            "Measured as the real 3-for-3 alongside the two changes above "
            "(Swamp, Whispersilk Cloak and Lightning Greaves out; Starscape "
            "Cleric, Enduring Tenacity and Exemplar of Light in), 6,000 paired "
            "games: win rate +0.0397 [+0.0335, +0.0463] at 10 turns and "
            "+0.0617 [+0.0527, +0.0707] at 20, against +0.0353 and +0.0480 "
            "for the 2-for-2 without it. Damage +8.40 and +9.23. Alone against "
            "a blank of the same cost, +2.11+-0.47 damage and +0.0090+-0.0046 "
            "win rate at 20 turns."
        ),
        notes=(
            "COST, measured: this is the swap that strands mana. stranded_mv "
            "+5.56 at 10 turns for the 3-for-3 against +1.85 for the 2-for-2 "
            "— a four-drop replacing a two-drop on top of the Swamp already "
            "cut. Watch the curve if the deck starts stumbling. Its flying is "
            "unmodelled (queued work item 1), so the body is a floor."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, which is now the DEFAULT pod (combat_targeting='open', incidental_rate=1.0, clock_shift=2, archetypes on) and the first pod model in which your life total is load-bearing. Measured as the same 3-for-3, 6,000 paired games: win rate +0.0362 [+0.0300, +0.0425] at 10 turns and +0.0638 [+0.0550, +0.0727] at 20; damage +6.89 and +7.68. Against +0.0397 and +0.0617 on the old pod, and +0.0483 / +0.0773 on pod v2 without archetypes. Significant at both horizons on every pod tried. The package adds two blockers and a lifelinker to a deck that now takes real attacks, so it holds up precisely where the modelling got better. Decision stands."
        ),
    ),
    Change(
        deck="rendmaw",
        remove="Idol of Oblivion",
        add="Cauldron of Essence",
        staged="2026-09-04",
        rationale=(
            "Cauldron's drain half is The Meathook Massacre's text word for "
            "word — 'each opponent loses 1 life and you gain 1 life' — so it "
            "is 3 pod life per creature death in a deck that loses a dozen "
            "tokens a game: 12.4 drain damage per game it resolves. Its second "
            "half is a repeatable sac outlet AND recursion (0.55 reanimations "
            "a game), stocked mostly by the pod's own wraths, which is exactly "
            "when you want it. Idol of Oblivion is a noncreature artifact that "
            "ablates inside its own error bars, so cutting it costs no body."
        ),
        evidence=(
            "Measured as the real swap under POD v3 (the current default), "
            "6,000 paired games: win rate +0.0027 [+0.0007, +0.0048] at 10 "
            "turns and +0.0135 [+0.0088, +0.0182] at 20; damage +0.95 and "
            "+1.03. Significant on both metrics at both horizons."
        ),
        notes=(
            "THE CUT CHANGED, and this is the clearest thing the new pod model "
            "has produced. The original staging cut Ornithopter of Paradise, "
            "which measured fine on the old pod (+0.0025 / +0.0158) and then "
            "DECAYED as the model improved: v2 +0.0018 / +0.0155, v3 -0.0015 "
            "[-0.0037, +0.0007] / +0.0088. The mechanism is that Ornithopter "
            "is a 0/2 BODY as well as a dork and Cauldron is not a creature — "
            "under pod v3 creatures attack whoever cannot block, so a spare "
            "blocker is worth something the old pod priced at exactly zero. "
            "Controlled check, same card in, three different cuts, pod v3, "
            "20 turns: cutting the noncreature Idol +0.0135 [+0.0088, +0.0182]; "
            "cutting the 0/2 Ornithopter +0.0088 [+0.0038, +0.0138]; cutting "
            "the 1/2 Dockside Chef +0.0048 [+0.0000, +0.0097]. Monotonic in "
            "whether the cut was a body. "
            "COSTS, both measured and both real: Cauldron is one card type, so "
            "the swap still loses a commander trigger, and Idol is this deck's "
            "token-payoff draw engine — tokens_made -0.15. "
            "SEPARATELY: the engine models Blood Artist at 3x its real drain, "
            "which inflates the baseline Cauldron is measured alongside. "
            "Cauldron's 3.0 is the one of the two that is correct."
        ),
    ),
    Change(
        deck="lorehold",
        remove="Scroll Rack",
        add="Sunbird's Invocation",
        staged="2026-09-04",
        rationale=(
            "'Whenever you cast a spell FROM YOUR HAND, reveal the top X, X = "
            "that spell's mana value; you may cast a spell with mana value X "
            "or less from among them free.' X scaling off the triggering "
            "spell is what makes it a Lorehold card rather than a generic "
            "one: this curve tops out at twelve, so a big spell digs deep and "
            "can free-cast something big. Fires 3.6 times a game for an "
            "average free spell of MV 3.8. Miracles DO trigger it (a miracled "
            "card is cast from hand); Galvanoth, Radiant Scrollwielder, The "
            "Dawning Archaic and Bombardment/Mastery copies do not."
        ),
        evidence=(
            "Measured as the real swap, 6,000 paired games: win rate +0.0077 "
            "[+0.0047, +0.0108] at 10 turns and +0.0215 [+0.0142, +0.0288] at "
            "20; mv_cheated +2.12 and +4.91; damage +2.14 and +4.20; cards "
            "drawn +0.68 and +0.90. Every metric significant at both horizons."
        ),
        notes=(
            "Scroll Rack is the cut because it is the deck's worst "
            "model-evaluated NON-WIPE card (-1.78 damage, -0.0100 win, signal "
            "'both'): paying {1} and a tap to set the top competes with the "
            "miracle payment itself. Penance is deliberately left alone — it "
            "is already earmarked for Galvanoth in the queued work. "
            "COST: replacing a two-drop with a six-drop, stranded_mv +4.28 at "
            "10 turns. The alternative cut of Improvisation Capstone strands "
            "LESS (-0.98) but wins less (+0.0045 / +0.0128), so this is the "
            "better of the two measured options."
        ),
        reverified=(
            "RE-VERIFIED 2026-09-04 under POD v3, now the default. 6,000 paired games: win rate +0.0032 [+0.0005, +0.0058] at 10 turns and +0.0167 [+0.0103, +0.0228] at 20; damage +1.98 and +3.05. Against +0.0077 / +0.0215 on the old pod. Significant at both horizons, but the 10-turn margin is thin and Lorehold is the deck the new pod punishes hardest — eleven creatures, so it eats the pod's attacks and carries the highest life-share of losses of the three decks. Sign, significance and rank all survive. Decision stands."
        ),
    ),
]


DECKS = {
    # March of the World Ooze is COMMITTED as of v12, so it is in the deck
    # list itself and no longer a swap-in candidate.
    "rendmaw": (rendmaw_v12, {
        "Cauldron of Essence": rendmaw_v12.CAULDRON_OF_ESSENCE}),
    # The four 2026-08-31/09-01 Lorehold changes are COMMITTED as of v16, so
    # they are in the deck list itself and no longer swap-in candidates.
    "lorehold": (lorehold_v16, {
        "Molecule Man": lorehold_v16.MOLECULE_MAN,
        "Galvanoth": lorehold_v16.GALVANOTH,
        "Sunbird's Invocation": lorehold_v16.SUNBIRDS_INVOCATION}),
    "karlov": (karlov_v1, {
        "Starscape Cleric": karlov_v1.STARSCAPE_CLERIC,
        "Enduring Tenacity": karlov_v1.ENDURING_TENACITY,
        "Exemplar of Light": karlov_v1.EXEMPLAR_OF_LIGHT}),
}


def pending_for(deck_name: str) -> list[Change]:
    return [c for c in CHANGES if c.deck == deck_name]


def build_pending(deck_name: str, apply_pending: bool = True, up_to: int = None):
    """Build a deck with staged changes applied.

    apply_pending=False gives the original spreadsheet list. `up_to=n` applies
    only the first n staged changes, which is how an experiment run earlier in
    the sequence can be reproduced after later changes are staged on top.
    """
    module, catalog = DECKS[deck_name]
    deck, commander = module.build()
    if not apply_pending:
        return deck, commander
    changes = pending_for(deck_name)
    if up_to is not None:
        changes = changes[:up_to]
    if not changes:
        return deck, commander
    outs = [c.remove for c in changes]
    ins = []
    for c in changes:
        if c.add not in catalog:
            raise KeyError(f"{c.add} has no card definition in {deck_name}")
        ins.append(catalog[c.add])
    deck = _swap_many(deck, outs, ins)
    validate(deck, commander)
    return deck, commander


BASICS = {"Mountain", "Plains", "Forest", "Swamp", "Island", "Wastes"}


def validate(deck, commander) -> None:
    """Singleton and size checks. Basic lands are the legal exception."""
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    seen = {}
    for card in deck:
        if card.name in BASICS:
            continue
        seen[card.name] = seen.get(card.name, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    assert not dupes, f"singleton violation: {dupes}"
    assert commander.name not in seen, (
        f"{commander.name} appears in the 99 as well as the command zone")


def ledger(verbose: bool = True) -> None:
    print("=" * 78)
    print("PENDING DECK CHANGES — not yet written to the .xlsx files")
    print("=" * 78)
    if not CHANGES:
        print("  (none — every decided change is applied on all three legs)")
        for deck_name in sorted(DECKS):
            deck, cmd = build_pending(deck_name)
            print(f"  {deck_name:<10} -> {len(deck) + 1} cards, "
                  f"singleton-legal, commander distinct")
    for deck_name in sorted({c.deck for c in CHANGES}):
        rows = pending_for(deck_name)
        print(f"\n{deck_name.upper()}  ({len(rows)} change"
              f"{'s' if len(rows) != 1 else ''})")
        for c in rows:
            print(f"  - OUT  {c.remove}")
            print(f"  + IN   {c.add}")
            print(f"    staged {c.staged}")
            if verbose:
                print(f"    why    {c.rationale}")
                print(f"    data   {c.evidence}")
                if c.notes:
                    print(f"    note   {c.notes}")
        deck, cmd = build_pending(deck_name)
        print(f"    -> {len(deck) + 1} cards, singleton-legal, commander distinct")
    if COMMITTED:
        print("\nCOMMITTED (in the deck module AND the .xlsx)")
        for c in COMMITTED:
            print(f"  {c.deck}: -{c.remove} +{c.add} ({c.staged})")
            if verbose and c.reverified:
                print(f"    recheck {c.reverified}")


if __name__ == "__main__":
    ledger()
