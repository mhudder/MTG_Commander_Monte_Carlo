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
