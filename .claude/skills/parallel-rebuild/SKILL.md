---
name: parallel-rebuild
description: Rebuild the ablation tables of several EDH Monte Carlo decks at once, one cloud session per deck, all at one commit, then merge and close them out. Use when the owner calls a table rebuild (the "batched rebuild"), when several decks' caches are SUSPECT because their baselines moved, or when asked to run decks in parallel.
---

# Rebuilding several decks in parallel

**THIS IS THE PROTOCOL FOR A MULTI-DECK REBUILD** (§0z94). One machine has
four cores and each deck's ablation already uses all four, so running decks
side by side on it gains ~3%. Six SESSIONS are six machines: the wall time
becomes the slowest deck's instead of the sum. `./tools/regen_tables.sh` in
series is still correct, and is the fallback.

The numbers do not depend on which machine produced them -- the harness is
deterministic for one Python and numpy (shilgengar and azusa came back
byte-identical from the §0z60 rebuild) -- so a table from a leg session IS the
table a serial run would have printed. Three things keep that true, and each step below
exists for one of them: **one commit**, **one interpreter**, **no shared file
written by two legs**.

## 0. Before: everything that will be in the tables is committed

The rebuild measures a commit. Engine changes made after it are not in the
tables, so finish them first -- the owner's standing practice is "as many
engine changes as possible, then rebuild".

```bash
python -m tools.validate        # 18 x +0.00
python -m tests                 # green, except a test that names the stale
                                # caches themselves (test_metrics_and_render C)
python -m tools.check_docs      # green except the SUSPECT caches
python -m edhmc.pending         # legal on every deck
git status                      # clean
git push origin <branch>        # the legs clone from the remote
```

Record `git rev-parse --short HEAD` -- that is THE commit -- and
`python -c 'import sys, numpy; print(sys.version.split()[0], numpy.__version__)'`.

## 1. Launch one session per deck

`mcp__Claude_Code_Remote__create_session`, once per deck, with
`source_url` the repo, `source_revision` the branch, `outcome_branch` the
branch, and this prompt (fill the three blanks):

> Rebuild ONE deck's ablation table for the EDH Monte Carlo repo as one leg
> of a parallel rebuild. Do nothing else: no other edits, no docs, no gates.
> From the repo root run, IN THE BACKGROUND (it takes 20-60 minutes; wait for
> its completion notification rather than sleeping):
> `./tools/rebuild_deck.sh <deck> <commit> <branch>`
> It checks out <commit>, rebuilds only <deck>, commits that deck's three
> files and pushes them to <branch>, retrying on a race with the other legs.
> When it exits, report its last 20 lines of output and its exit code. If it
> fails, report the error and STOP -- do not fix, retry differently, or push
> anything by another route.

The legs need nothing from Scryfall and no network beyond git.

## 2. Wait without polling hard

Each leg's session ends its turn when the script exits. Check them with
`mcp__Claude_Code_Remote__get_session` (status_bucket) and their pushed
commits with `git fetch && git log origin/<branch>`; schedule a check-in with
`send_later` rather than sleeping. A leg that FAILED is re-run alone -- in a
new session or locally with the same three arguments; the others are
unaffected, because no leg reads another's files.

## 3. Collect

```bash
git pull origin <branch>
git log --format='%s%n%b' <commit>..HEAD | grep -E '^Rebuild|^Interpreter'
```

**Every leg's `Interpreter:` line must match yours.** A leg on another
Python or numpy is re-run, not merged.

```bash
python -m tools.cache_manifest --merge-shards   # refuses a shard built on
                                                # any other code
python -m tools.cache_manifest --write
python -m tools.status --write
```

## 4. Close out as one rebuild

```bash
python -m tools.validate
python -m tests                 # now fully green: the caches cover the decks
python -m tools.check_docs      # now fully green: every cache CURRENT
python -m edhmc.pending
```

Then, as for any rebuild:

* diff each new table against the one it replaced and write down what moved
  beyond its old bar, by deck, in a new `KNOWN_ISSUES.md` section;
* record each cache's provenance prose with
  `python -m tools.cache_manifest --note <deck> "..."`;
* record the WALL time of the slowest leg -- it replaces the serial figure;
* commit, push, and fast-forward `main` only if every gate is green;
* archive the leg sessions (`mcp__Claude_Code_Remote__archive_session`).

## What can go wrong, and the check that catches it

| failure | caught by |
|---|---|
| a leg measured a different commit | `rebuild_deck.sh` checks out <commit>; `--merge-shards` refuses a fingerprint that is not the live one |
| a leg ran a different interpreter | the `Interpreter:` line in its commit, step 3 |
| two legs wrote one file | `rebuild_deck.sh` refuses any change outside its deck's own three files; PROVENANCE.json is never written by a leg |
| a shard never merged | `check_docs`: an unmerged `provenance.<deck>.json` fails the cache check |
| a leg pushed a partial table | `regen_tables.sh` only installs a table once the run printed MODEL-EVALUATED, and `rebuild_deck.sh` refuses if the table is missing |
