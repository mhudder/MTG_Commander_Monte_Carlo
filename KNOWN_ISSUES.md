# Known issues — deferred, not blocking

Nothing here invalidates the four staged changes in `PENDING_CHANGES.md`. Rendmaw's
type lines were verified clean against the spreadsheet (1 mismatch in 89, and that
one is a sheet error), and both Lorehold swaps were measured after the Mizzix fix
landed.

Ordered by how much they could distort a future result.

## 1. PARTLY RESOLVED — alternative costs and X-spell mana values

`Card` now carries `alt_costs`, a tuple of `(cost_dict, tag)` alternatives, and
the casting policy tries them when the printed cost is unaffordable. First user:
**Overlord of the Hauntwoods**, which can now be deployed via **Impending 4** for
{1}{G}{G} instead of {3}{G}{G}, entering as a noncreature enchantment (excluded
from combat) until turn+4. It fires in 8.7% of games; the card's ablation moved
from **-0.14 ±0.76 damage** to **+1.48 ±0.39**, i.e. from unmeasured to
significantly positive. The single-cost assumption had been hiding a real card.

`Card.x_pips` records how much of a cost stands in for {X}, and `free_mv` returns
`mv - x_pips` — the mana value a card has anywhere but the stack. Used by every
place that copies or free-casts: Arcane Bombardment, Mizzix's Mastery, The
Dawning Archaic, Galvanoth, Double Vision.

| card | cast MV | MV in graveyard |
|---|---|---|
| The Meathook Massacre `{X}{B}{B}` | 4 (at X=2) | **2** |
| Debt to the Deathless `{X}{W}{W}{B}{B}` | 6 (at X=2) | **4** |
| Toxic Deluge `{2}{B}` | 3 | **3** |
| Culling Ritual `{2}{B}{G}` | 4 | **4** |

Two mistakes were made and corrected here, both worth remembering:

1. **Toxic Deluge and Culling Ritual are not X spells.** Toxic Deluge's X is a
   life payment ("as an additional cost, pay X life") and Culling Ritual's is a
   count of permanents destroyed. Neither has {X} in its mana cost, so their
   mana values are fixed at 3 and 4. Scryfall states it directly: "you'll still
   choose a value for X and pay X life. This is because it doesn't have {X} in
   its mana cost." A card reading "X" in its text box is not an X spell.
2. **A real X spell's graveyard MV is the fixed portion, not zero.** `{X}{B}{B}`
   is MV 2 in the graveyard, not 0. The first implementation returned 0 for all
   of them, which was wrong in the opposite direction.

Debt to the Deathless was also under-costed in the Karlov deck file at
`{gen 2}{W}{B}`; corrected to `{gen 2}{W}{W}{B}{B}`.

**Still open:** the mechanism is only wired into the Rendmaw engine's casting
loop, and nothing uses it for overload, evoke, escape, or kicker. Mizzix's
Mastery remains a hand-written special case in `lorehold.py` rather than an
`alt_costs` entry.

## 1b. (original entry) Cards can only have one cost — structural

The engine gives every card exactly one mana cost and one mana value. Every error
found in the audit was a violation of that single assumption:

- **Mizzix's Mastery** — overload is a second alternative cost, and it cannot be
  combined with miracle. *Fixed*, but only as a special case in `main_phase`.
- **Overlord of the Hauntwoods** (Rendmaw) — Impending 4 lets you cast it for
  {1}{G}{G} instead of {3}{G}{G}, entering as a noncreature enchantment for four
  turns. Not modelled. Understates the card's early flexibility.
- **X spells** — Toxic Deluge, The Meathook Massacre, Culling Ritual all have
  **MV 0 in the graveyard**. The engine stores 3, 4 and 4. Harmless in Rendmaw
  today, but the Lorehold engine reads graveyard MV constantly (Bombardment
  copies ~1.6/game, Archaic free casts ~0.4, Mastery ~0.3), so any X spell added
  to that deck would silently inflate `mv_cheated`.

The real fix is to let `Card` carry a list of castable modes rather than a single
cost, and have the casting policy choose among them. That closes the whole
category instead of patching instances, and it is worth doing before many more
modal cards get added.

## 2. RESOLVED — Hagra Mauling is now a proper MDFC

Defined with `land_face=("B", True)` and a {2}{B} instant front face, like the
Lorehold three. Rendmaw now reads as 35 true lands plus one MDFC land face, and
the engine plays whichever face it needs. Baseline effect was negligible, which
is the expected result for one flexible card.

## 3. Ashnod's Altar and Deathreap Ritual remain unresolved

Both still ablate slightly negative (−0.28, −0.19) and neither result should be
trusted. The Altar's mana arrives after the main phase in the engine's turn
structure, so it cannot be spent — modelling the cost without the benefit. Valuing
it properly needs sacrifice mana to feed back into casting, which is an engine
change, not a card script.

## 4. Opponents' boards are a blocker count

This is the deepest limitation. Swords to Plowshares, Path to Exile, Chaos Warp,
Generous Gift, Assassin's Trophy, Beast Within, Toxic Deluge and Culling Ritual
cannot be evaluated at all, because there are no opposing permanents to remove.
About 28 of 63 Rendmaw cards and a similar share of Lorehold sit in this bucket.
They ablate to ~0.00 and **that is a fact about the model, not the cards.**

## 5. RESOLVED — your own board wipes now hit your own board

Wipes carry a `wipe` tag (`onesided` for Massacre Wurm and Orlorin's Searing
Light, which spare your side). On resolution they clear the opponents' boards and
your own, and deaths route through `on_creature_death` so aristocrats drains
still fire.

The casting policy needed the more careful work: a greedy engine will happily
wrath its own winning board. `should_cast_own_wipe()` gates it on board state —
only sweep when the table's creature count meaningfully exceeds yours
(`wipe_threshold`, default 1.4).

Effect on baselines (5,000 games, T20):

| deck | win before | win after | own wipes cast |
|---|---|---|---|
| Rendmaw | 0.309 | 0.299 | 0.12 |
| Lorehold | 0.258 | **0.186** | 1.38 |
| Karlov | 0.455 | **0.378** | 0.52 |

Lorehold casts 1.38 of its own sweepers a game, and paying for them properly
costs it seven points of win rate. Every Lorehold number from before this change
is optimistic.

## 6. RESOLVED — life totals are tracked

Resolved as a side effect of the opponent clock. `your_life` starts at 40, is
reduced by threat-weighted incidental damage each turn, and is read by Storm
Herd's X, Felidar Sovereign, Aetherflux Reservoir and Serra Ascendant. This entry
sat stale for several sessions claiming otherwise — worth re-auditing the rest of
this file against the code rather than trusting it.

## 7. Unmodelled recursion in Lorehold

Copy-from-graveyard is modelled (Bombardment, Mastery, Dawning Archaic). True
recursion is not: Invoke Calamity's free graveyard cast, Volcanic Vision's return
to hand, Apex of Power's "add 10 red mana if cast from hand", Scrap Trawler / Myr
Retriever / Junk Diver in Rendmaw. All of these **understate** their cards, which
is the safer direction to be wrong.

## RESOLVED — opponents now have a win condition

Each opponent draws a kill turn from a bracket-calibrated range, pre-rolled from
the dedicated opponent RNG stream so common random numbers survive. When a clock
comes due the target is **threat-weighted** — the biggest board at the table
draws the kill, so being ahead now carries a real cost. If the clock misses you
it eliminates a rival and **re-arms**, because a deck that just killed someone
has not stopped being a problem.

Clock ranges, calibrated from bracket descriptions and then corrected against
the pod actually being played (the top seat behaves like a 3.5, not a true
bracket 4):

| bracket | threatens lethal |
|---|---|
| 2 | turns 13-18 |
| 3 | turns 10-14 |
| 4 | turns 8-12 |

Resulting four-player win rates against a mixed 2/3/4 pod, 5,000 games:
Rendmaw **0.307**, Lorehold **0.253**, mean game length 12.1 and 12.9 turns.
Both sit near the 0.25 baseline a four-player race should produce.

**The horizon parameter is gone.** Win rate is flat from a turn cap of 16 to 30
(0.280 / 0.298 / 0.298 / 0.277) because games now end on their own at ~12 turns.
Set the cap to 20 and forget it. `turns` is now a safety valve, not a modelling
choice.

Life totals are live as a consequence, so Storm Herd's X, lifelink and
Witch-Blessed Meadow's pay-3-life all mean something now (item 6 is partly
resolved).

## RESOLVED — error bars restored, all three decks re-run

`ablation.py` now prints 95% CIs on every figure plus a `signal` column
(both / dmg / win / --). All three tables regenerated at 2,500 paired games
against the current model, single horizon T20.

| deck | evaluated | significant on both | inside error bars |
|---|---|---|---|
| Rendmaw | 36 | 7 | 8 |
| Lorehold | 35 | 11 | 13 |
| Karlov | 45 | 15 | 11 |

**Roughly a quarter to a third of every evaluated card is statistically
unmeasured at this sample size.** Those rows carry a real point estimate and a
sign, and under the old format they looked rankable. They are not. Raise `N` if
a specific one matters.

## 8. (superseded) Re-run both ablations

**Now doubly stale — the opponent clock changes every number.** Every ranking in
`ablation_lorehold.txt` and `ablation_rendmaw.txt` predates the clock, the
mana-rock fix, the drain implementation, the nine model-blind implementations and
the Mizzix correction. The caches are cleared, so a fresh pass will pick up the
new baselines.

    python ablation.py rendmaw 2000 20
    python ablation.py lorehold 2000 20

With the clock in place a single turn cap is correct again, so the multi-horizon
reporting is now belt-and-braces rather than necessary.

---

# How to read an ablation table

A reasonable first filter is: **a card is pulling its weight if it is positive on
damage, on win rate, or both; a card positive on neither is a cut candidate.**
That is right most of the time. Three failure modes, in the order they bite.

## 1. A "+" is not necessarily a real "+"

The tables print point estimates. Many of them are smaller than their own error
bars. At 6,000 paired games on Karlov:

| card | damage | win rate | survives? |
|---|---|---|---|
| Suture Priest | +3.07 ±0.59 | +0.0108 ±0.0047 | both |
| Kambal | +3.14 ±0.59 | +0.0047 ±0.0050 | damage only |
| Mother of Runes | +0.70 ±0.55 | +0.0033 ±0.0040 | damage only |
| Pristine Talisman | +0.24 ±0.41 | −0.0003 ±0.0032 | **neither** |

Anything under roughly **+0.6 damage** or **+0.005 win rate** at this sample size
is indistinguishable from a blank. Treat the bottom of the table as unranked
rather than ranked.

## 2. Win rate beats damage where they disagree

Since the opponent clock landed, win rate is the actual objective and damage is
only a proxy. Extra damage on a game you were winning anyway buys nothing.

Archangel of Thune is +5.13 damage but only +0.0030 win rate. Well of Lost
Dreams is +2.35 damage and **+0.0210 win rate** — the highest in the deck. Vito
is +0.29 damage and +0.0200 win. The damage column ranks those three in exactly
the wrong order. **When the columns disagree, believe win rate.**

## 3. Leave-one-out is blind to redundancy

This is the one that produces genuinely wrong cuts. Removing one card of an
interchangeable set understates all of them, because the others cover.

Karlov runs three combo partners for Exquisite Blood. Removing any single one:

| removed | damage | win rate |
|---|---|---|
| Sanguine Bond | +1.40 | +0.0203 |
| Vito | +1.40 | +0.0163 |
| Vizkopa Guildmage | −1.76 | +0.0095 |
| **all three together** | −1.71 | **+0.0513** |
| Exquisite Blood alone | −7.01 | +0.0240 |

The three partners are worth +0.0513 win rate as a group — **more than double**
the largest individual score, and far more than any of them looks worth alone.
Vizkopa Guildmage in particular reads negative on damage and would be cut under
the simple rule, when it is a third of a package worth five points of win rate.

The same logic applies to the soul sisters, the equipment suite, and the wraths.
For any set of interchangeable effects, **ablate the group, not the members.**
`ablation.py`'s `ablate()` already accepts a list of names.

## The rule, restated

1. Ignore anything inside its own error bars.
2. Where damage and win rate disagree, follow win rate.
3. Before cutting, ask whether another card in the deck does the same job — and
   if so, ablate them together.
