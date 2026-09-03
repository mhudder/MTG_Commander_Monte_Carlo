# EDH Monte Carlo — consolidated project context

Single-file bundle of every document a fresh session needs, so this can be
uploaded to the project's context folder as ONE file instead of six.

Contains, in order: HANDOFF, PENDING CHANGES, KNOWN ISSUES, and the three
ablation tables. It does NOT contain the Python source — that is ~184 KB and is
better added as individual files (or downloaded and re-uploaded) only if a
session needs to run or modify the simulator. Everything below is enough to
understand the state of the project and every decision made so far.



==============================================================================
# FILE: HANDOFF.md
==============================================================================

# Handoff — start here

Monte Carlo simulator for evaluating EDH decklist changes. Three decks, three
engines, a shared opponent model, and a paired A/B harness.

**Read in this order:** this file → `PENDING_CHANGES.md` (decisions awaiting the
spreadsheets) → `KNOWN_ISSUES.md` (open problems, and how to read an ablation
table). `README.md` predates the opponent clock and the Karlov deck; trust it on
methodology, not on file lists or commands.

## State of play

Three decks are modelled. The `.xlsx` files in the project are the system of
record and have **not** been modified.

| deck | engine | win rate | notes |
|---|---|---|---|
| Karlov of the Ghost Council v1 | `karlov.py` | 0.455 | strongest; lifegain triggers |
| Rendmaw, Creaking Nest v11 | `engine.py` | 0.301 | go-wide tokens, type-line payoff |
| Lorehold, the Historian v15 | `lorehold.py` | 0.257 | miracle / top-deck |

**Five changes are staged, none committed.** Four Lorehold, one Rendmaw. All
re-verified against the current model. See `PENDING_CHANGES.md` for evidence and
the commit checklist.

## Running things

Python 3.10+, numpy, scipy. From this directory:

```bash
python -m edhmc.pending            # print the staged changes, validate the lists
python validate.py                 # A/A control + CRN measurement (must be 0.00)
python ablation.py karlov 2500 20  # rank every card; caches and resumes
python compare_decks.py            # cross-deck comparison at matched settings
python tutor_policy.py analyse     # learned tutor target policy
```

`ablation.py` takes ~4 minutes per deck on one core and writes a cache keyed on
deck and horizon, so it survives being interrupted — just rerun to resume.

## The two things that make this work

**Common random numbers.** Deck A and deck B are the same list with slots
swapped, shuffled on the same seed, so the other ~97 cards are dealt identically
and nearly all variance cancels in the difference. Worth roughly 5-7x the sample
size. **`validate.py` must print exactly +0.00 on every metric** — anything else
means randomness is leaking between branches and every result is suspect.

**Opponents have a win condition.** Each of three opponents draws a kill turn
from a bracket-calibrated range (B2 13-18, B3 10-14, B4 8-12, tuned to a pod
whose top seat behaves like a 3.5). Targets are threat-weighted, so being ahead
draws the kill. Games end on their own around turn 12, which is why `turns=20` is
a safety valve rather than a modelling choice. Opponent randomness is pre-rolled
into a fixed grid so it cannot break CRN.

## How not to misread the output

Covered fully at the end of `KNOWN_ISSUES.md`. The short version:

1. **Ignore anything inside its own error bars** (`signal` column reads `--`).
   Roughly a quarter to a third of every deck is statistically unmeasured.
2. **Win rate is the objective; damage is a proxy.** Where they disagree, follow
   win rate. Felidar Sovereign is -6.06 damage and +0.0412 win rate.
3. **Leave-one-out is blind to redundancy.** Karlov's three combo partners score
   +0.02 each and +0.0513 as a group. Ablate interchangeable sets together.
4. **Half of each deck is model-blind.** All removal, protection and wraths
   ablate to ~0.00 because opponents' boards are a blocker count, not real
   permanents. That is a fact about the model, not the cards.

## The lesson this project keeps re-teaching

Almost every large correction here came from a card whose text the engine had
wrong, not from a statistical problem. The mana rocks produced no mana. Blood
Artist drained nothing. Guttersnipe, Land Tax, Mizzix's Mastery and Monument to
Endurance were unimplemented and scored ~0 as a result. Penance and Hidden
Retreat were charged mana they do not cost. Mizzix's was allowed to combine
overload with miracle, which the rules forbid. Toxic Deluge was treated as an X
spell when its X is a life payment.

**Verify oracle text before trusting any number about a card.** When a result is
surprising, the engine is the first suspect, not the deck. And when adding a
card, check `KNOWN_ISSUES.md` item 1 first — alternative costs (overload,
impending, evoke, escape) are the single most common source of silent error.

## Suggested next steps

- Commit the five staged changes to the spreadsheets when ready.
- Two Lorehold cuts are decided but unstaged: **Penance** (same card-cost logic
  as Hidden Retreat) and **Galvanoth** as an addition (+0.0050 win rate).
- Karlov has no staged changes and its deck file was written from the
  spreadsheet without oracle-text verification — that is the largest block of
  unverified card data in the project.
- `KNOWN_ISSUES.md` item 1 is the highest-value structural work remaining:
  `alt_costs` exists but is only wired into the Rendmaw casting loop.


==============================================================================
# FILE: PENDING_CHANGES.md
==============================================================================

# Pending deck changes

**Status: staged, NOT committed.** The `.xlsx` files are untouched and remain the
system of record. Apply these by hand when the batch of changes is final.

Machine-readable source: `edhmc/pending.py`. Print with `python -m edhmc.pending`,
which also runs size, singleton and commander-distinctness checks on each list
(basic lands exempted).

**5 changes staged: 4 Lorehold, 1 Rendmaw.**

## Re-verification, 2026-09-01

All five re-run against the CURRENT model (opponent clock, real life totals,
T20 cap), 7,000 paired games each, tested sequentially so each change is scored
against the list with the earlier ones already applied.

| change | win rate | damage | verdict |
|---|---|---|---|
| L: −Monologue Tax, +Arcane Bombardment | **+0.0189** ±0.0058 | +2.19 ±0.68 | holds |
| L: −Hidden Retreat, +Double Vision | **+0.0116** ±0.0050 | +2.96 ±1.44 | holds |
| L: −Urabrask, +Monastery Mentor | **+0.0066** ±0.0048 | +5.61 ±1.44 | holds |
| R: −Skullclamp, +March of the World Ooze | **+0.0076** ±0.0056 | +1.55 ±0.83 | holds |
| L: −Triumph, +The Dawning Archaic | +0.0019 ±0.0050 | −0.34 ±0.32 | see below |

The Dawning Archaic swap came back inconclusive at 7,000 games, so it was re-run
at **20,000**: win rate **+0.003 ±0.003** (just significant), mv_cheated
**+2.79 ±0.14**, damage **−0.25 ±0.17**. The verdict is unchanged but the honest
description is narrower than the original entry: this is a mana-cheat and
top-end change worth about a third of a percentage point of win rate, not a
meaningful speed increase. It is the weakest of the five by a wide margin.
Further A/B tests should build from `build_pending(deck)` so they measure against
the current intended list rather than a stale baseline.

---

## Lorehold, the Historian — v15 → v16 (pending)

Three changes. Each was tested against the list with the earlier ones already
applied, not against the stale v15 baseline.

| | OUT | IN |
|---|---|---|
| 1 | Triumph of Saint Katherine | The Dawning Archaic |
| 2 | Monologue Tax | Arcane Bombardment |
| 3 | Urabrask // The Great Work | Monastery Mentor |

**Cumulative effect** (6,000 paired games, 14 turns, mixed pod, CRN):

| metric | v15 | v16 pending | change |
|---|---|---|---|
| mv_cheated | 19.48 | 27.38 | **+7.91** ±1.02 |
| damage | 41.86 | 68.25 | **+26.39** ±9.85 |
| win rate | 0.09 | 0.12 | **+0.02** ±0.01 |

### 1. −Triumph of Saint Katherine, +The Dawning Archaic

A 5/5 lifelink body is the weakest miracle hit in a deck whose payoffs are 7–12
mana value spells, and its death trigger shuffles the top six cards of your
library — precisely where this deck stores its resources. The Archaic replaces it
with the cheapest late-game haymaker in the list: the deck averages 8.5 instants
and sorceries in the graveyard by turn 14, leaving it at roughly **{2.45}
effective**.

12,000 paired games: **mv_cheated +2.46** [+2.28, +2.64]. Re-verified after a
later engine fix (selective top-setter activation), 8,000 games: **+2.67**
[+2.45, +2.89], damage +0.16 (ns), win rate flat.

*Note:* the narrower half of the four-card change originally tested. Molecule Man
was **not** taken and **Verge Rangers stays** — Verge Rangers strips lands off the
top of the library, which matters when 31% of miracle windows fail to a land.

### 2. −Monologue Tax, +Arcane Bombardment

Bombardment reads "your first instant or sorcery **each turn**", not each of
*your* turns. Lorehold's rummage opens a miracle window on all three opponents'
turns, so a round can produce **four triggers instead of one** — and the exile
pile accumulates, so the Nth trigger copies all N cards.

6,000 paired games vs the pending list: **mv_cheated +7.24** [+4.74, +10.05],
damage +5.17 [+3.22, +7.43], win rate +0.01.

**⚠ HIGH VARIANCE — the main reason to think twice.** It fires in only **7.9% of
games**; when it does it averages **13.2 free copies** (max observed 136). Median
damage barely moves (19 → 21) while the mean jumps 41.8 → 60.4. The entire gain
lives in the top decile. It is also strongly horizon-dependent: near zero at 10
turns, large at 14+. Monologue Tax was modelled generously at 2 Treasures a round
for three opponents and still lost.

### 4. −Hidden Retreat, +Double Vision

Same "each turn" clause that makes Arcane Bombardment strong here: Lorehold's
rummage opens a window on all three opponents' turns, so a round can produce four
triggers instead of one. It copies the miracled spell too, so a ten-drop miracled
for {2} becomes two of them.

Hidden Retreat's cost is not mana — it is a **card**. Putting one on top converts
your next draw into something you already held, which costs 0.53–0.68 draws per
game in a deck whose ablation is topped by card flow.

8,000 paired games: win rate **+0.017** [+0.012, +0.021], mv_cheated +3.16,
damage +2.74, cards drawn +0.79. Double Vision resolves in 17.2% of games on turn
9.7, averages 2.39 copies when it does, and is answered only **28.3%** of the
time against 57% for Bombardment.

**Ruling built into the model:** the copy is *put on the stack, not cast*, so it
does NOT trigger Guttersnipe, Monastery Mentor or Bombardment — unlike Mastery's
and Bombardment's copies, which are genuinely cast. That reduction is priced in.

**Honest split:** roughly half the gain is Hidden Retreat being bad rather than
Double Vision being good. Against a same-cost blank, Double Vision's win-rate
contribution does not clear its error bar.

### 3. −Urabrask // The Great Work, +Monastery Mentor

A body-count fix for a deck with only eleven creatures and a top-heavy curve.
Nearly every spell here is noncreature, so Mentor converts the deck's existing
spell density into a board.

6,000 paired games: **damage +4.42** [+3.74, +5.12], combat damage +4.95, win
rate +0.01. mv_cheated −0.14 — it contributes bodies, not mana. Combined with
Bombardment the damage gain (+18.6) exceeds the sum of the parts (+9.6), because
Mentor's Monks are on board to carry the damage Bombardment's free spells make.

*Fairness note:* Urabrask was **under-modelled** in the earlier ablation — its
1 damage per instant/sorcery and its {R} mana ability were not implemented, which
is why it scored near zero. Both are now in the engine, and cutting it costs 0.53
spell damage. It lost anyway.

**⚠ Watch item RESOLVED (2026-09-01).** Your own board wipes now hit your own
board, so Mentor's Monks die to your Farewell and Blasphemous Act as they should.
Re-verified at 20,000 paired games with self-wipes live: win rate **+0.0049
±0.0025**, damage **+3.10 ±0.59**, combat damage +3.73 — still significant on
both, and the swap holds. The margin is roughly a third of what it looked like
before, which is the cost the watch item was warning about.

---

## Rendmaw, Creaking Nest — v11 → v12 (pending)

| | card |
|---|---|
| **OUT** | Skullclamp |
| **IN** | March of the World Ooze |

Skullclamp has almost no fodder in this deck. Rendmaw's Birds are 2/2, and the
clamp makes them 3/1, so they live; with Metallic Mimic naming Bird they are 4/2
and still live. It finds a legal 1-toughness target on **0.35 turns per game**.
Cutting it was justified independently of what replaced it.

20,000 paired games, 10 turns, mixed pod: **damage +2.85** [+2.64, +3.06],
**cards drawn −1.01** [−1.06, −0.96].

Baseline shift (6,000 games, 10 turns):

| metric | v11 | v12 pending |
|---|---|---|
| damage | 25.89 | **28.91** |
| final board power | 15.90 | 16.98 |
| cards drawn | 12.39 | **11.40** |
| tokens made | 4.67 | 4.46 |
| Rendmaw triggers | 5.95 | 5.78 |

*(Baselines above predate the engine fixes. Corrected baseline: damage 34.30 →
37.56.)*

Cumulative Rendmaw effect (6,000 paired games, 10 turns): damage 25.77 → 28.95
(**+3.19** ±0.42), board power 15.76 → 16.89, cards drawn 12.38 → 11.41.

**Re-verified after two engine fixes** (mana rocks now produce mana; Blood
Artist / Meathook Massacre drain now counted), 12,000 paired games, 10 turns:
damage **+3.25** [+2.92, +3.57], cards drawn −1.08, **win rate +0.01** [+0.01,
+0.01], board power +1.06. The change now clears on win rate too, which it did
not before. The decision holds and is better supported than when staged.

**Watch item:** the margin shrinks as the pod gets stronger — +5.86 damage at all
bracket 2, **+1.09 at all bracket 4**, where it is close to a wash against the
card-draw loss. March is answered roughly **57%** of the times you deploy it,
against ~15% for Skullclamp. If your regular pod is high-powered, revisit this
one; the case for cutting Skullclamp holds either way.

---

## When committing

1. Update the `.xlsx` decklists.
2. Update `edhmc/decks/rendmaw_v11.py` and `edhmc/decks/lorehold_v15.py` (and
   rename to the new version numbers).
3. Move the entries in `edhmc/pending.py` from `CHANGES` to `COMMITTED`.


==============================================================================
# FILE: KNOWN_ISSUES.md
==============================================================================

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


==============================================================================
# FILE: ablation_rendmaw.txt
==============================================================================

```

Horizons: (20,).  All figures are paired differences with 95% CIs.

  signal = both : the card beats its error bars on damage AND win rate
           dmg  : significant on damage only
           win  : significant on win rate only
           --   : INSIDE its own error bars - indistinguishable from a blank.
                  Not a weak card, an unmeasured one. Do not rank these.

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.

====================================================================================
MODEL-EVALUATED — a low score is evidence about the card
====================================================================================
card                                    damage T20             win rate    signal
Beastmaster Ascension                 +5.14+-0.86        +0.0136+-0.0078      both
Ohran Frostfang                       +3.62+-0.98        +0.0060+-0.0069       dmg
Sol Ring                              +3.16+-0.78        +0.0088+-0.0071      both
March of the World Ooze               +3.13+-0.79        +0.0088+-0.0084      both
Bitterblossom                         +2.36+-0.66        +0.0048+-0.0074       dmg
Golgari Signet                        +1.89+-0.75        +0.0004+-0.0070       dmg
Arcane Signet                         +1.56+-0.70        +0.0032+-0.0076       dmg
Solemn Simulacrum                     +1.48+-0.52        +0.0064+-0.0065       dmg
Steel Overseer                        +1.28+-0.45        +0.0060+-0.0059      both
Overlord of the Hauntwoods            +1.17+-0.45        +0.0076+-0.0060      both
Arasta of the Endless Web             +1.12+-0.39        +0.0036+-0.0055       dmg
The Great Henge                       +1.12+-0.64        +0.0052+-0.0055       dmg
Grist, the Hunger Tide                +1.10+-0.71        -0.0032+-0.0064       dmg
Erebos, Bleak-Hearted                 +1.03+-0.48        +0.0040+-0.0054       dmg
Foundry Inspector                     +0.99+-0.49        +0.0004+-0.0057       dmg
Grave Titan                           +0.92+-0.42        +0.0048+-0.0061       dmg
Verdurous Gearhulk                    +0.89+-0.57        +0.0048+-0.0073       dmg
Coat of Arms                          +0.88+-0.69        +0.0024+-0.0068       dmg
Heroic Intervention                   +0.83+-0.37        +0.0004+-0.0038       dmg
Palladium Myr                         +0.76+-0.49        +0.0008+-0.0054       dmg
Metallic Mimic                        +0.74+-0.46        -0.0008+-0.0054       dmg
Dryad of the Ilysian Grove            +0.73+-0.49        -0.0016+-0.0059       dmg
The Meathook Massacre                 +0.72+-0.27        +0.0076+-0.0046      both
Roaming Throne                        +0.71+-0.45        +0.0016+-0.0053       dmg
Copper Myr                            +0.67+-0.38        +0.0024+-0.0050       dmg
Dockside Chef                         +0.60+-0.47        +0.0060+-0.0058      both
Ophiomancer                           +0.53+-0.50        -0.0004+-0.0060       dmg
Woe Strider                           +0.50+-0.36        +0.0032+-0.0052       dmg
Enduring Vitality                     +0.47+-0.59        -0.0004+-0.0055        --
Primal Vigor                          +0.44+-0.52        -0.0016+-0.0058        --
Twitching Doll                        +0.32+-0.37        -0.0040+-0.0047        --
Tendershoot Dryad                     +0.25+-0.34        +0.0004+-0.0046        --
Idol of Oblivion                      +0.17+-0.55        -0.0012+-0.0058        --
Blood Artist                          +0.12+-0.31        +0.0028+-0.0048        --
Leaden Myr                            +0.12+-0.45        -0.0004+-0.0049        --
Ornithopter of Paradise               +0.07+-0.42        -0.0008+-0.0058        --

====================================================================================
MODEL-BLIND — a low score is evidence about the MODEL, not the card
====================================================================================
card                                    damage T20             win rate    signal
Overwhelming Stampede                 +1.27+-0.57        -0.0008+-0.0066       dmg
Gloomshrieker                         +0.78+-0.29        +0.0000+-0.0046       dmg
Shigeki, Jukai Visionary              +0.77+-0.26        +0.0032+-0.0040       dmg
Village Rites                         +0.69+-0.48        +0.0008+-0.0051       dmg
Scrap Trawler                         +0.60+-0.31        +0.0048+-0.0047      both
Burnished Hart                        +0.52+-0.38        +0.0000+-0.0053       dmg
Junk Diver                            +0.52+-0.20        +0.0016+-0.0035       dmg
Filigree Familiar                     +0.48+-0.33        +0.0032+-0.0043       dmg
Myr Retriever                         +0.44+-0.21        +0.0032+-0.0037       dmg
Midnight Reaper                       +0.42+-0.35        +0.0012+-0.0045       dmg
Massacre Wurm                         +0.41+-0.17        +0.0040+-0.0033      both
Pygmy Kavu                            +0.31+-0.20        +0.0016+-0.0029       dmg
Lignify                               +0.25+-0.19        +0.0008+-0.0029       dmg
Nameless Inversion                    +0.25+-0.18        +0.0016+-0.0029       dmg
Whip of Erebos                        +0.12+-0.15        -0.0004+-0.0028        --
Bow of Nylea                          +0.10+-0.21        -0.0016+-0.0033        --
Beast Within                          +0.03+-0.12        -0.0008+-0.0016        --
Reap                                  +0.02+-0.02        +0.0004+-0.0008        --
Assassin's Trophy                     +0.01+-0.02        +0.0004+-0.0008        --
Culling Ritual                        +0.00+-0.01        +0.0000+-0.0000        --
Eyeblight's Ending                    +0.00+-0.05        +0.0000+-0.0011        --
Toxic Deluge                          +0.00+-0.00        +0.0000+-0.0000        --
Sakura-Tribe Elder                    -0.08+-0.22        +0.0000+-0.0038        --
Haywire Mite                          -0.10+-0.26        +0.0008+-0.0048        --
Deathreap Ritual                      -0.26+-0.31        -0.0020+-0.0039        --
Ashnod's Altar                        -0.33+-0.33        -0.0012+-0.0034       dmg
Biotransference                       -0.72+-0.42        -0.0044+-0.0042      both

```


==============================================================================
# FILE: ablation_lorehold.txt
==============================================================================

```

Horizons: (20,).  All figures are paired differences with 95% CIs.

  signal = both : the card beats its error bars on damage AND win rate
           dmg  : significant on damage only
           win  : significant on win rate only
           --   : INSIDE its own error bars - indistinguishable from a blank.
                  Not a weak card, an unmeasured one. Do not rank these.

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.

====================================================================================
MODEL-EVALUATED — a low score is evidence about the card
====================================================================================
card                                    damage T20             win rate    signal
Storm Herd                            +9.84+-1.50        +0.0660+-0.0115      both
Rise of the Eldrazi                   +4.55+-1.36        +0.0312+-0.0088      both
Guttersnipe                           +2.75+-1.01        +0.0200+-0.0073      both
Apex of Power                         +2.64+-1.63        +0.0196+-0.0078      both
Thrill of Possibility                 +2.58+-1.99        +0.0124+-0.0085      both
Big Score                             +2.39+-1.18        +0.0100+-0.0081      both
Borrowed Knowledge                    +2.32+-1.32        +0.0100+-0.0084      both
Unexpected Windfall                   +2.31+-1.88        +0.0068+-0.0080       dmg
Emeria's Call                         +2.29+-0.97        +0.0148+-0.0088      both
Faithless Looting                     +2.26+-1.36        +0.0108+-0.0086      both
Reforge the Soul                      +2.18+-1.65        +0.0248+-0.0094      both
Talisman of Conviction                +1.19+-0.77        +0.0048+-0.0081       dmg
Library of Leng                       +1.18+-1.97        +0.0036+-0.0078        --
Storm-Kiln Artist                     +1.18+-1.17        +0.0016+-0.0063       dmg
Soulfire Eruption                     +1.00+-1.24        +0.0080+-0.0076       win
Sensei's Divining Top                 +0.87+-0.89        +0.0040+-0.0087        --
Verge Rangers                         +0.79+-0.62        +0.0052+-0.0062       dmg
Sol Ring                              +0.77+-1.48        +0.0136+-0.0078       win
Mother of Runes                       +0.76+-1.36        +0.0024+-0.0055        --
Boros Signet                          +0.48+-0.95        -0.0076+-0.0079        --
Bender's Waterskin                    +0.44+-0.71        -0.0020+-0.0082        --
Hit the Mother Lode                   +0.32+-0.78        +0.0076+-0.0054       win
Boros Charm                           +0.27+-1.30        +0.0048+-0.0043       win
Lightning Greaves                     +0.27+-1.04        -0.0020+-0.0062        --
Blasphemous Act                       +0.09+-0.36        -0.0008+-0.0040        --
Approach of the Second Sun            -0.17+-0.25        -0.0036+-0.0028       win
Artist's Talent                       -0.21+-0.87        -0.0028+-0.0071        --
Arcane Signet                         -0.25+-2.05        -0.0040+-0.0081        --
Ruby Medallion                        -0.28+-2.58        -0.0028+-0.0071        --
The Dawning Archaic                   -0.96+-1.97        +0.0028+-0.0045        --
Victory Chimes                        -1.07+-2.51        +0.0000+-0.0082        --
Scroll Rack                           -1.67+-1.37        -0.0072+-0.0080       dmg
Hidden Retreat                        -1.72+-1.42        -0.0032+-0.0091       dmg
Smothering Tithe                      -2.36+-3.26        -0.0060+-0.0094        --
Penance                               -2.45+-1.34        -0.0092+-0.0085      both

====================================================================================
MODEL-BLIND — a low score is evidence about the MODEL, not the card
====================================================================================
card                                    damage T20             win rate    signal
Monastery Mentor                      +6.33+-2.07        +0.0216+-0.0094      both
Arcane Bombardment                    +3.77+-2.17        +0.0096+-0.0089      both
Monument to Endurance                 +3.70+-1.48        +0.0212+-0.0095      both
Land Tax                              +2.83+-1.56        +0.0104+-0.0078      both
Mizzix's Mastery                      +2.72+-1.48        +0.0164+-0.0082      both
Sejiri Shelter                        +1.21+-1.59        +0.0048+-0.0067        --
Dragon's Rage Channeler               +1.16+-1.47        +0.0012+-0.0056        --
Goliath Daydreamer                    +0.32+-0.22        +0.0016+-0.0044       dmg
Farewell                              +0.18+-0.55        +0.0008+-0.0022        --
Hexing Squelcher                      +0.14+-0.31        +0.0016+-0.0041        --
Dawn's Truce                          +0.11+-0.16        +0.0016+-0.0022        --
Generous Gift                         +0.05+-0.06        +0.0008+-0.0011        --
Invoke Calamity                       +0.03+-0.24        +0.0000+-0.0019        --
Longshot Rebel Bowman                 +0.02+-0.43        +0.0012+-0.0046        --
Chaos Warp                            +0.02+-0.05        +0.0004+-0.0008        --
Path to Exile                         +0.01+-0.06        +0.0000+-0.0000        --
Pinnacle Monk                         +0.00+-2.03        -0.0004+-0.0046        --
Restoration Seminar                   +0.00+-0.15        +0.0000+-0.0027        --
Bolt Bend                             +0.00+-0.00        +0.0000+-0.0000        --
Swords to Plowshares                  -0.00+-0.00        +0.0000+-0.0000        --
Ultima                                -0.02+-0.22        -0.0004+-0.0028        --
Orlorin's Searing Light               -0.04+-0.09        +0.0000+-0.0016        --
Volcanic Vision                       -0.05+-0.15        +0.0004+-0.0026        --
Improvisation Capstone                -0.06+-0.17        -0.0004+-0.0026        --
Gamble                                -0.07+-0.26        -0.0008+-0.0016        --
Promise of Loyalty                    -0.12+-0.27        -0.0004+-0.0014        --
Perch Protection                      -0.28+-1.74        +0.0012+-0.0044        --
Ondu Inversion                        -0.33+-1.92        +0.0008+-0.0054        --
Call Forth the Tempest                -0.37+-0.89        +0.0008+-0.0011        --
Enlightened Tutor                     -1.37+-1.62        -0.0028+-0.0076        --

```


==============================================================================
# FILE: ablation_karlov.txt
==============================================================================

```

Horizons: (20,).  All figures are paired differences with 95% CIs.

  signal = both : the card beats its error bars on damage AND win rate
           dmg  : significant on damage only
           win  : significant on win rate only
           --   : INSIDE its own error bars - indistinguishable from a blank.
                  Not a weak card, an unmeasured one. Do not rank these.

Win rate is the objective; damage is a proxy. Where they disagree, follow win
rate. And before cutting anything, check whether another card does the same job
- leave-one-out understates every member of an interchangeable group. Pass a
list of names to ablate() to score a package together.

====================================================================================
MODEL-EVALUATED — a low score is evidence about the card
====================================================================================
card                                    damage T20             win rate    signal
Archangel of Thune                    +5.73+-1.55        +0.0064+-0.0082       dmg
Marauding Blight-Priest               +3.71+-0.96        +0.0104+-0.0071      both
Kambal, Consul of Allocation          +3.67+-0.82        +0.0148+-0.0077      both
Cliffhaven Vampire                    +3.39+-1.03        +0.0128+-0.0081      both
Daxos, Blessed by the Sun             +3.25+-0.97        +0.0088+-0.0073      both
Aetherflux Reservoir                  +2.90+-0.79        +0.0032+-0.0067       dmg
Suture Priest                         +2.45+-1.28        +0.0040+-0.0077       dmg
Soul's Attendant                      +2.36+-1.29        +0.0044+-0.0073       dmg
Well of Lost Dreams                   +2.30+-1.39        +0.0176+-0.0081      both
Soul Warden                           +2.24+-1.20        +0.0132+-0.0069      both
Auriok Champion                       +2.04+-1.18        +0.0056+-0.0065       dmg
Debt to the Deathless                 +1.92+-0.79        +0.0080+-0.0071      both
Voice of the Blessed                  +1.74+-0.72        +0.0028+-0.0065       dmg
Sorin, Vengeful Bloodlord             +1.60+-0.82        +0.0068+-0.0071       dmg
Drana's Emissary                      +1.44+-0.52        +0.0036+-0.0053       dmg
Dawn of Hope                          +1.38+-1.16        +0.0120+-0.0070      both
Blind Obedience                       +1.27+-0.70        +0.0044+-0.0068       dmg
Mother of Runes                       +1.26+-1.16        -0.0020+-0.0066       dmg
Ranger of Eos                         +1.25+-0.61        +0.0068+-0.0054      both
Land Tax                              +1.23+-0.89        +0.0068+-0.0064      both
Sorin, Solemn Visitor                 +1.23+-0.50        +0.0088+-0.0060      both
Sunscorch Regent                      +1.21+-0.54        +0.0068+-0.0059      both
Fountain of Renewal                   +1.11+-0.62        +0.0032+-0.0057       dmg
Authority of the Consuls              +1.09+-0.97        +0.0048+-0.0067       dmg
Phyrexian Arena                       +0.90+-0.73        +0.0080+-0.0073      both
Elas il-Kor, Sadistic Pilgrim         +0.89+-1.30        +0.0088+-0.0066       win
Syr Konrad, the Grim                  +0.83+-0.37        +0.0028+-0.0050       dmg
Vito, Thorn of the Dusk Rose          +0.61+-1.20        +0.0220+-0.0081       win
Ajani's Mantra                        +0.58+-0.60        +0.0004+-0.0051        --
Cosmos Elixir                         +0.47+-0.50        +0.0056+-0.0057        --
Pristine Talisman                     +0.47+-0.68        +0.0000+-0.0051        --
Swiftfoot Boots                       +0.39+-0.51        +0.0016+-0.0052        --
Sol Ring                              +0.37+-1.12        +0.0096+-0.0066       win
Kalitas, Traitor of Ghet              +0.23+-0.58        +0.0004+-0.0060        --
Serra Ascendant                       +0.21+-0.87        +0.0000+-0.0054        --
Whispersilk Cloak                     +0.16+-0.33        +0.0016+-0.0044        --
Benevolent Offering                   +0.08+-0.30        +0.0020+-0.0032        --
Necropotence                          -0.14+-1.01        -0.0028+-0.0069        --
Lightning Greaves                     -0.19+-0.48        +0.0028+-0.0046        --
Blood Artist                          -0.62+-0.83        -0.0056+-0.0051       win
Orzhov Signet                         -0.62+-0.96        +0.0072+-0.0069       win
Sanguine Bond                         -0.87+-1.24        +0.0116+-0.0082       win
Vizkopa Guildmage                     -1.33+-1.65        +0.0016+-0.0067        --
Felidar Sovereign                     -6.06+-1.31        +0.0412+-0.0084      both
Exquisite Blood                       -7.17+-1.95        +0.0180+-0.0085      both

====================================================================================
MODEL-BLIND — a low score is evidence about the MODEL, not the card
====================================================================================
card                                    damage T20             win rate    signal
Lurrus of the Dream-Den               +0.35+-0.38        +0.0008+-0.0041        --
Sun Titan                             +0.30+-0.26        +0.0008+-0.0033       dmg
Austere Command                       +0.10+-0.18        +0.0000+-0.0000        --
Damn                                  +0.00+-0.00        +0.0004+-0.0008        --
Swords to Plowshares                  +0.00+-0.00        +0.0000+-0.0000        --
Path to Exile                         +0.00+-0.00        +0.0000+-0.0000        --
Anguished Unmaking                    +0.00+-0.00        +0.0000+-0.0000        --
Fracture                              +0.00+-0.00        +0.0000+-0.0000        --
Toxic Deluge                          +0.00+-0.00        +0.0000+-0.0000        --
Damnation                             +0.00+-0.00        +0.0000+-0.0000        --
Farewell                              -0.00+-0.00        +0.0000+-0.0000        --
Return to Dust                        -0.01+-0.01        +0.0000+-0.0000        --
Enlightened Tutor                     -0.07+-0.16        +0.0000+-0.0011        --
Soulmender                            -0.08+-0.21        -0.0032+-0.0025       win
Phyrexian Reclamation                 -0.36+-0.25        -0.0036+-0.0028      both
Sensei's Divining Top                 -0.42+-0.31        +0.0000+-0.0029       dmg
Umezawa's Jitte                       -0.57+-0.45        +0.0000+-0.0033       dmg

```
