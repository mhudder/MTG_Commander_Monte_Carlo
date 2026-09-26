# The ledger's states: a vocabulary for a 50-card funnel

**STATUS: THE TRIAGE FLAGS ARE BUILT (2026-09-26, §0z66); THE STATES ARE
NOT.** `Proposal.triage` carries LIVE / BLIND / DEFERRED, with
`triage_clauses` and `triage_note`, and `pending.check_triage` enforces the
"must record" column below. PREPARED, and splitting `Change` into SIMULATED +
STAGED, are still proposals. This is the naming half of `docs/TRIAGE.md` —
that file designs the *screen*, this one designs the *states a card passes
through and the states it dies in*. CLAUDE.md queued item 23 is the live
pointer for both.

The vocabulary is the owner's, written out. The one part of it that was an
inference — splitting today's STAGED into SIMULATED + STAGED — **was put to
the owner and confirmed on 2026-09-22.**

---

## Why the current vocabulary will not survive the volume

Today the ledger runs at five states and a handful of cards per deck. The
intended workload is **50+ proposals at a time**, triaged for implementation
cost, with **the vast majority discarded before any head-to-head**. Three
things already fail at today's volume and fail worse at that one:

1. **`HANDOFF.md` documents the state machine by hand, and it has rotted.**
   Its section opens "A card swap goes through three states", describes
   Measured → Staged → Committed, then adds withdrawn as "a fourth state".
   `PROPOSED` was added on 2026-09-16 and never reached the prose. That is
   §0q — a hand-maintained list drifting from the thing it describes —
   pointed at the vocabulary itself.

2. **`STAGED` reads as the opposite of what it means.** In ordinary English
   "staged" is *set aside for consideration*. Here it means the far end of
   the pipeline: a named cut, head-to-head evidence, and a commitment strong
   enough that `build_pending()` applies it to every baseline measured
   afterwards. The word invites exactly the wrong reading, which is a real
   cost when a funnel is mostly made of cards that are genuinely only under
   consideration.

3. **The discard states are unnamed, and they are where most cards will
   end up.** At 50 proposals a quarter, the dead cards outnumber the live
   ones by an order of magnitude. This project has already paid for losing
   them twice: Heliod, Sun-Crowned and Underworld Breach were proposed as
   new ideas when both had already been measured inside their bars, which is
   what `tools/card_known.py` was built to prevent. `WITHDRAWN` and
   `Proposal.rejected` both exist for the same stated reason — the
   alternative was a chat message, and **a chat message is the state most
   easily lost.**

---

## Two questions, not one

The pipeline is often read as a single ladder of confidence. It is not. Each
state answers one of two independent questions, and the funnel's crucial
decision sits where they cross:

| | question | cheap to answer? |
|---|---|---|
| **evidence** | how much do we know about what this card is worth? | yes — CPU only |
| **cost** | how much engine work stands between us and knowing? | yes — reading only |

**Deciding which unmeasured cards deserve engine work is a ranking over the
cost axis, not a step along the evidence axis.** A card parked for machinery
is not "earlier in the pipeline" than a measured one; it is off to the side
with a price tag. That is why the discard/park verdicts are flags rather
than positions in the order (below), and why a state list alone cannot
express "deferred, but probably the best card we have seen".

---

## The six states

| state | what is true of the card | what it cost to get here |
|---|---|---|
| **PROPOSED** | oracle text fetched verbatim from Scryfall, and an argument tied to a measured weakness of that deck | minutes |
| **PREPARED** | implemented in the engine and pinned by a mutation-tested check | **the bulk of a session** |
| **MEASURED** | T10/T20 win rate with bars, against a *convenient* baseline. Names no real cut | ~152 CPU-seconds |
| **SIMULATED** | the real swap: current decklist, against a cut **deliberately chosen for weakness**, paired on common seeds | one `run_ab` |
| **STAGED** | the decision is taken. `build_pending()` applies it; every later baseline contains it | judgement |
| **COMMITTED** | all legs moved in one commit: module, `.xlsx`, ledger | judgement |

### PREPARED resolves the "PREPARED/TRIAGED" slash

Those are two different things and only one of them is a state:

* **TRIAGED** is an *assessment* — we now know what this card would cost and
  whether the engine can see it. Its output is a verdict, recorded as a flag
  on the Proposal (the owner's call, and the cheaper one).
* **PREPARED** is a *state* — the engine work is done and pinned. This is the
  expensive transition, and it deserves a name because it is where every
  sunk session-hour lives. `docs/TRIAGE.md` measured this: *"making a card
  behave like its text — the bulk of a session, and no CPU at all."*

A card can be TRIAGED for months without ever becoming PREPARED. That is the
parked queue, and it is the thing the funnel is for.

### The split that is new — confirmed 2026-09-22

Today, `Change` conflates two claims: *we ran a head-to-head against a named
cut* (evidence) and *we have decided to put this in* (decision). Splitting
SIMULATED from STAGED separates them. At 50 cards this matters: many cards
will earn a head-to-head and lose it, and today there is nowhere to record a
head-to-head that did not result in a staging — the two azusa Reality
Fracture cards of 2026-09-20 are exactly that shape.

**CONFIRMED by the owner, 2026-09-22.** SIMULATED carries the head-to-head
evidence; STAGED carries the decision that acts on it. The consequence to
implement is that `Change` stops being one record: a head-to-head that did not
stage is a SIMULATED record with no STAGED partner, and that is a legal,
recordable outcome rather than a gap.

---

## The triage verdicts are flags on PROPOSED

Per the owner's decision: lighter weight than first-class states, in the
shape `Proposal.rejected` already has.

| flag | meaning | must record |
|---|---|---|
| `LIVE` | survived triage; escalate | — |
| `BLIND` | the engine cannot see enough of the text to measure it | **at least one clause**, so it can be revisited |
| `DEFERRED` | needs machinery that does not exist | **what the machinery is** |
| `REJECTED` | illegal, off-colour, or already known | which — `check_proposals()` and `card_known.py` already answer this |

**Why BLIND must name clauses, even as a flag.** §0z13: a note saying
something is infeasible is a claim with a date on it. `KNOWN_ISSUES` §0i said
Talisman of Conviction "cannot easily" be charged; that stopped being true
one day earlier at §0z8, and nothing re-read it. A BLIND verdict that names
its clauses can be re-run when an engine gap closes. One that says "engine
can't see it" cannot.

---

## Five rules that fall out of the split

**1. A MEASURED number is never decision evidence.** It is a screen. The
decision rests on SIMULATED. This is §0c, restated for the new boundary:
cards sharing a baseline have overlapping CIs by construction and cannot be
ranked against one another.

**2. MEASURED sorts; it does not rank.** With 50 rows the temptation is to
order them. Use a threshold — *does this clear the bar for a SIMULATED run?*
— and never an ordering. §0z35 is the standing example: two azusa cards
measured equal by a common baseline, and only the paired in-slot run
separated them.

**3. MEASURED is optimistic by construction, and that is the correct bias.**
A screen's only fatal error is the false negative — discarding a good card.
`docs/TRIAGE.md`'s acceptance test says exactly this: *"the screen FAILS if
it assigns BLIND to any card whose measured row was significant."* An
over-admitting screen is working as intended; the SIMULATED tier pays for
the over-admission, and it is cheap.

**4. A MEASURED number carries the baseline it was measured against.** The
owner's definition permits a stale decklist, and that is fine *if it is
recorded*. This repo's whole cache-provenance system (§0z23) exists because
a number without the code that produced it cannot be re-checked. A screening
row measured against last month's list is usable; one that does not say so
is not.

**5. Keep the §0j blank as the MEASURED victim — do not cut a basic land.**
`experiment.repl_priority()` casts the blank at the deck's own median
nonland priority, derived rather than invented. A basic-land cut is a
*different* imperfect baseline with a known direction of error: CLAUDE.md
records that "a land cut is the kind of change this harness flatters",
because the model's mana logic is simpler than a pilot's. Rule 3 wants an
optimistic screen, but it wants a *calibrated* one, and §0j is the
calibration this project already paid for.

---

## What a first implementation would touch

* `edhmc/pending.py` — a `Prepared` state (or a flag on `Proposal` recording
  that the engine work and its test exist); `verdict` + the required-content
  check on `Proposal`; splitting `Change` into evidence and decision halves.
* `HANDOFF.md` — **delete** the hand-written state list and point at this
  file, per the repo's own anti-drift pattern.
* `tools/status.py` — derive the funnel counts per state, so nothing quotes
  them by hand.
* `tools/check_docs.py` — a check that every state named here exists in
  `pending.py` and vice versa. A glossary is a hand-maintained name set, and
  §0q says it needs its derivation check in the same change.
* this file — replace PROPOSED with what was built.

## What it costs

`MEASURED` keeps its current meaning under this proposal, which matters:
the term carries 61 code references and 69 doc references, many inside
evidence strings describing past runs. Re-pointing it would falsify the
historical record. `STAGED` narrows rather than moves — every current
`CHANGES` entry already holds head-to-head evidence, so each becomes a
SIMULATED record plus a STAGED decision, mechanically.

**The two things `docs/TRIAGE.md` says must not be economised are unchanged
by any of this:** the head-to-head against a named cut, and the
mutation-pinned test.
