# Triage: screening cards before measuring them

**STATUS: PROPOSED, 2026-09-21. Nothing here is implemented.** It is written
down so that the next session can build it, argue with it, or discard it with a
reason. CLAUDE.md queued item 23 is the live pointer; this file is the design.

The idea came from the owner after a session that imported nine Reality Fracture
cards across six decks: *there should be a cheap practice for deciding whether a
card is worth evaluating at all, kept separate from the expensive work of
deciding which card it replaces.* That is the right shape, and this file says
where the expense actually is, because it is not where it feels like it is.

---

## Where the time actually goes

Measured, not estimated, from the 2026-09-20/21 sessions:

| step | observed cost |
|---|---|
| a candidate row (card against a blank) | ~152 CPU-seconds a card |
| a real swap, N=15,000, both horizons | 58–81s a job on karlov, 175–301s on azusa |
| ranking 14 already-measured cards against one reference | **2.6 CPU-hours** |
| rebuilding one deck's ablation table | ~35–40 min wall on four cores |
| **making a card behave like its text** | **the bulk of a session, and no CPU at all** |

**Two conclusions follow, and they point in opposite directions from the
intuition that "screening is expensive".**

1. **Measurement is cheap; implementation is not.** The costly part of adding a
   card is reading its oracle text, finding the hook, writing the branch, and
   pinning it with a mutation-tested check. A screen that runs *after*
   implementation saves almost nothing.
2. **The single largest measurement spend was not screening at all** — it was
   ranking cards that had already been measured, to decide which one takes a
   slot. That is the step §0c forces and §0z35 finally answered, and it is the
   step the owner correctly identified as separate.

So the economy is: **screen on paper before writing code, and escalate N only
for survivors.** Not: measure less carefully at the end.

---

## The five tiers

| tier | the question | cost | what it kills |
|---|---|---|---|
| **0 — paper** | legal, not already known, and can the engine SEE it? | seconds | off-colour, already-measured, MODEL-BLIND |
| **1 — hook** | does its text land on a hook that already exists? | minutes of reading | cards needing new machinery |
| **2 — smoke** | implemented: does its own counter fire? N≈1000 | ~10 CPU-seconds | cards that do nothing |
| **3 — value** | a candidate row at N=15,000 | ~152 CPU-seconds | the merely small |
| **4 — decision** | head-to-head against a named cut | one `run_ab` | picks the cut |

### Tier 0 is the biggest saver, and most of it already exists

`check_proposals()` catches off-colour cards; `tools/card_known.py` answers
"does the repo already know this card" by derivation. What is missing is the
third question, and it is the one that kills most cheaply: **how much of this
card's text can this engine represent at all?**

Worked examples, all from the 2026-09-21 scan, all of which would have been
killed before a line of code:

* **Venser, Fervent Forger** — both ETB modes copy *an opponent's* spell or
  permanent. Opponents hold no spells or permanents as objects (§4), so the
  whole card is invisible and it would have measured as a 6-mana 5/3 body.
* **Ginger, Queen of Sweets** — its engine is the monarch, which this project
  does not model.
* **Saheeli, Consul of Oversight** — triggers on scry and surveil, which the
  tivit list barely does.

**Tier 0's output is a VERDICT, not a note.** The `add-card` skill already asks
for a clause-by-clause visibility review at step 2; what it lacks is teeth — the
review cannot currently *stop* a card.

### Tier 1: the cost of the machinery, costed before it is built

A card whose text lands on an existing hook is cheap; a card that needs a new
one is its own change with its own test. Three deferrals from 2026-09-21, each
with the reason written down at the time:

* **Koth of the Homestead** — needs a landfall hook karlov does not have, and
  lands enter that engine by at least three paths.
* **Pitiless Plunderer** — needs Treasures-as-mana in rendmaw, a decrement
  threaded through the `spend()` five engines share (§0z26).
* **Ob Nixilis, the Ascended** — "at the beginning of each end step" plus
  "tapped creatures your opponents control", neither of which exists.

Deferring is not rejecting. The verdict records what the machinery is, so the
next session can decide whether to build it on purpose rather than discover it
halfway through.

### Tier 2 is the tier that does not exist yet, and it is nearly free

**A count has far lower variance than a win-rate difference.** "Does this card
fire?" is answerable at N≈1000 in seconds, where "is it worth 0.005 win rate?"
needs 15,000 games. Two cards from this project's history show the value:

* **Sai, Master Thopterist** made **0.155 Thopters a game** in a deck that
  produces 51 artifacts, because it reads artifact SPELLS and tivit makes
  artifact TOKENS (§0z26). A blank explained by mechanism, at N=1000.
* **Stingcaster Mage** casts **0.18 times a game** (2026-09-21). Not a kill —
  its swap still measured +0.0107 — but knowing the rate *before* the full run
  is what stops a win rate being read as the card doing the work.

`tools/candidates.py` already prints `P(deploy)`. It is not used as a gate.

---

## What must NOT be economised

Both of these have already cost this project real money, and both are cheap.

**The head-to-head against a named cut.** Skipping it produced two withdrawn
swaps (§0z, §0z2). On 2026-09-20 it showed karlov's *already staged* cut was the
worse of two available by **+0.0147** (§0z36). It is one `run_ab` call.

**The pinning test, with mutations.** §0z28's headline +0.0481 was wrong — the
real figure was +0.0279 — because a card drew twice and no test said so. On
2026-09-21 a mutation run caught that **two of five mutations were not
installed**: they set module flags no production code read, so they broke
nothing and would have read as "these checks do not depend on these rules"
(§0z38). An unpinned implementation is how a wrong number gets published.

---

## Proposed ledger states

`edhmc/pending.py` has PROPOSED → MEASURED → STAGED → COMMITTED / WITHDRAWN.
Triage adds three verdicts *before* MEASURED, so the cheap kills stop living in
a conversation — the same problem the `Candidate` class was invented to fix:

* **BLIND** — tier 0 or 2 killed it. Records WHICH clauses the engine cannot
  see, so the verdict can be revisited when a gap closes. §0z13 is the warning:
  a note saying something is infeasible is a claim with a date on it.
* **DEFERRED** — tier 1 killed it for now. Records the machinery it needs.
* **LIVE** — survived, escalate to tier 3.

---

## How to validate the screen itself

**A cheap screen that quietly discards good cards is worse than no screen**, and
this is testable rather than arguable, because **the repo already holds the
labelled data**: every row in `MEASURED`, every `results/candidates_*.txt`, and
every ablation table is a card with a known outcome.

Proposed acceptance test, in the spirit of the mutation runs:

1. Run the triage rules over every card already measured in this repo.
2. **The screen FAILS if it assigns BLIND to any card whose measured row was
   significant.** Those are its false negatives and they are the only failures
   that matter.
3. It should assign BLIND to the known mechanism-blanks — Sai, and Splendid
   Reclamation, whose proposal rationale was backwards (§0z25).
4. Write the expected sets down BEFORE running it, per the standing rule.

**And one scope limit, stated so nobody expects more of it:** triage predicts
**MEASURABILITY, not value.** Heliod, Sun-Crowned and Underworld Breach are
implemented in full and measured inside their bars (§0z25) — a visibility screen
would correctly pass both, and they are still not worth a slot. Deciding that is
tier 3 and tier 4, and it is not what this saves.

---

## What a first implementation would touch

* a `tools.triage` module: tier 0 by derivation (identity, `card_known`, and a
  clause-by-clause prompt the agent must answer), and tier 2 as a small-N run
  reading the card's own counter.
* `edhmc/pending.py`: the three verdicts, with a check that a BLIND verdict
  names at least one clause.
* `.claude/skills/add-card/SKILL.md`: promote step 2 from a review to a gate,
  and add tier 2 before the tier-3 measurement.
* this file: replace "PROPOSED" with what was built, and record what the
  back-test showed.
