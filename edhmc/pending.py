"""
edhmc.pending — staged deck changes, not yet written to the spreadsheets.

The .xlsx files remain the system of record and are untouched. This module
holds changes that have been decided but not committed, so that:

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

from edhmc.decks import rendmaw_v11, lorehold_v15, karlov_v1
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


# ---------------------------------------------------------------------------
# Staged — decided, not yet in the spreadsheets
# ---------------------------------------------------------------------------
CHANGES: list[Change] = [
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
    ),
]

# ---------------------------------------------------------------------------
# Committed — already reflected in the spreadsheets
# ---------------------------------------------------------------------------
COMMITTED: list[Change] = []


DECKS = {
    "rendmaw": (rendmaw_v11, {"March of the World Ooze":
                              rendmaw_v11.MARCH_OF_THE_WORLD_OOZE}),
    "lorehold": (lorehold_v15, {
        "The Dawning Archaic": lorehold_v15.THE_DAWNING_ARCHAIC,
        "Molecule Man": lorehold_v15.MOLECULE_MAN,
        "Monastery Mentor": lorehold_v15.MONASTERY_MENTOR,
        "Arcane Bombardment": lorehold_v15.ARCANE_BOMBARDMENT,
        "Double Vision": lorehold_v15.DOUBLE_VISION,
        "Galvanoth": lorehold_v15.GALVANOTH}),
    "karlov": (karlov_v1, {}),
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
        print("  (none)")
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
        print("\nCOMMITTED (already in the spreadsheets)")
        for c in COMMITTED:
            print(f"  {c.deck}: -{c.remove} +{c.add} ({c.staged})")


if __name__ == "__main__":
    ledger()
