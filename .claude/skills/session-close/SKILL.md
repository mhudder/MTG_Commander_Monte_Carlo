---
name: session-close
description: Close out a working session on the EDH Monte Carlo repo — regenerate the derived docs, run the drift check, and decide what gets written down where. Use when finishing a piece of work, before the last commit of a session, or when the user says they are wrapping up, handing off, or stopping for the day.
---

# Closing a session

The point of this protocol is that **the next session should not have to
reconstruct anything.** Everything derivable is derived; everything else is
written down once, in the one place that owns it.

## 1. Regenerate the derived docs

They do not update themselves. The one time that was left to memory it produced
a generated file describing ten cache files that a commit had deleted.

```bash
python -m tools.knobs --write           # if you touched any cfg.get
python -m tools.cache_manifest --write  # ONLY if the caches were regenerated
python -m tools.status --write          # always; it is cheap and fully derived
```

**If `check_docs` reports a SUSPECT cache, do not regenerate the tables.** A
SUSPECT cache means a shared file changed, so the fingerprint moved and nobody
has checked whether the NUMBERS moved. Those are different questions and the
second one is answerable in seconds:

```bash
git worktree add ../edhmc_at <built_commit>      # from docs/ABLATION_CACHES.md
python -m tools.check_unchanged_decks --out=new.json
(cd ../edhmc_at && python -m tools.check_unchanged_decks --out=old.json)
python -m tools.check_unchanged_decks --diff old.json new.json
python -m tools.cache_manifest --verified <deck> "what you ran and what it showed"
python -m tools.cache_manifest --write
```

Bit-identical means the cache is still good. **Only a deck whose baseline
actually moved needs its table rebuilt, and only that deck** — a six-deck
regeneration is four hours and the last one moved 0 of 379 rows (§0z23).

`cache_manifest --write` records the STATE, never the built-at stamp — that is
written by `ablation.py` when the numbers are measured, so regenerating the
manifest cannot forge provenance. Run it when caches or their verifications
change.

## 2. Run the checks

```bash
python -m tools.check_docs     # must pass
python -m edhmc.pending        # 100 cards / singleton-legal / commander distinct
python -m tools.validate       # +0.00 on all 18 metrics, if you touched an engine
```

`check_docs` verifies that every `§` cited from code resolves, that every
documented command exists, that each generated doc was actually regenerated,
and that every cache matches its recorded fingerprint. Run `--mutate`
occasionally to confirm the checks still can fail.

If a check fails for a reason you are deliberately accepting, **say so in the
commit message and in the relevant doc.** A known-failing check that nobody
explains becomes a check everybody ignores.

## 3. Decide where each thing you learned goes

This is the part that keeps `CLAUDE.md` small. One rule:

> **A measurement goes in `KNOWN_ISSUES.md` under a new `§`. Only its LESSON is
> promoted to `CLAUDE.md`, and a lesson has no date in it.**

| what you have | where it goes |
|---|---|
| a number, a CI, a before/after | `KNOWN_ISSUES.md`, new `§`, with the harness that produced it |
| a decision about a card swap | `edhmc/pending.py` — `MEASURED`, `CHANGES`, `COMMITTED` or `WITHDRAWN` |
| a rule that will still be true in a month | `CLAUDE.md`, **Standing findings**, phrased without a date |
| the session's narrative, "we tried X and it failed because Y" | `docs/HISTORY.md` |
| which tables are current, what is staged, what can be run | **nowhere — it is derived.** `python -m tools.status --write` |
| a doc that is now superseded | `docs/archive/`, with a banner saying what replaced it |

**Never write into a doc something the repo already knows.** If you find
yourself typing a noise floor, a row count, a staged-swap list or a script
name into prose, stop: that is `docs/STATUS.md`'s job, and a hand-copy of it
will be wrong within two sessions. Three of the six noise floors `CLAUDE.md`
used to quote had already drifted a digit from the tables they described.

## 4. New section ids are permanent

A new finding takes the next free letter in the `0*` series of
`KNOWN_ISSUES.md`, gets an index row, and is **never renumbered** — 43 places
in the code cite these ids, and `check_docs` verifies every one still lands.
Add the index row in the same edit as the heading; `check_docs` enforces that
the two sets match, in both directions.

## 5. Commit

All legs of a deck change move in ONE commit: the deck module, the `.xlsx`,
and the `pending.py` ledger. Azusa has no `.xlsx` and moves in two legs.

Write the commit message so the next session can tell, without running
anything, **what moved and what was checked.** Say which decks' numbers
changed and which were verified unchanged — "checked, not argued" is the
project's own standard, and `tools/check_unchanged_decks.py` is how it is met.
