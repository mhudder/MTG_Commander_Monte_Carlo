# Handoff — start here

Monte Carlo simulator for evaluating EDH decklist changes. Three decks, three
engines, a shared opponent model, and a paired A/B harness.

**Read in this order:** this file → `COMMITTED_CHANGES.md` (what has actually
shipped, and the evidence for each) → `PENDING_CHANGES.md` (decisions awaiting
the spreadsheets) → `KNOWN_ISSUES.md` (open problems, and how to read an ablation
table). `README.md` predates the opponent clock and the Karlov deck; trust it on
methodology, not on file lists or commands.

## State of play

Three decks are modelled. The `.xlsx` files in the project are the system of
record and have **not** been modified.

| deck | engine | win rate | notes |
|---|---|---|---|
| Karlov of the Ghost Council v1 | `karlov.py` | 0.455 | strongest; lifegain triggers |
| Rendmaw, Creaking Nest **v12** | `engine.py` | — | go-wide tokens, type-line payoff |
| Lorehold, the Historian **v16** | `lorehold.py` | — | miracle / top-deck |

**Nothing is staged. The five changes committed 2026-09-02** — four Lorehold,
one Rendmaw. See `COMMITTED_CHANGES.md` for the full record and the evidence at
commit time.

The win rates above are the pre-commit v11/v15 figures and are now **stale for
Rendmaw and Lorehold**; only Karlov's is current. Post-commit `validate.py`
baselines: Rendmaw damage 40.67 (was 37.86), Lorehold mv_cheated 34.84 (was
23.30), damage 40.19 (was 34.52). **The three ablation tables were generated
against the pre-commit lists and are stale — regenerate before ranking anything.**

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

- Regenerate all three ablation tables against the committed lists.
- Two Lorehold changes are decided but unstaged: cut **Penance** (same card-cost
  logic as Hidden Retreat) and add **Galvanoth** (+0.0050 win rate).
- Karlov has no staged changes and its deck file was written from the
  spreadsheet without oracle-text verification — that is the largest block of
  unverified card data in the project.
- `KNOWN_ISSUES.md` item 1 is the highest-value structural work remaining:
  `alt_costs` exists but is only wired into the Rendmaw casting loop.

---

# Environment and repo config — READ FIRST IN A NEW SESSION

## Repository

    https://github.com/mhudder/MTG_Commander_Monte_Carlo    (public)

Clone it. It is also synced into project knowledge, but that is a search index
returning truncated chunks — readable, not runnable. Only a clone executes.

**The repo does not run as cloned.** The single commit is "Add files via
upload", a drag-and-drop that flattened the package. Every file sits at the
root, but the imports expect a package, so a fresh clone raises
`ModuleNotFoundError: No module named 'edhmc'` on every entry point.
Reconstruct before running anything:

    mkdir -p work/edhmc/decks
    cp engine.py lorehold.py karlov.py opponents.py experiment.py pending.py work/edhmc/
    cp __init__.py work/edhmc/__init__.py
    cp rendmaw_v12.py lorehold_v16.py karlov_v1.py work/edhmc/decks/
    touch work/edhmc/decks/__init__.py          # lost in the upload
    cp validate.py ablation.py audit_cards.py tag_flying.py *.txt *.md *.xlsx work/

Pushing that structure would remove this step permanently.

The three `.xlsx` decklists are in the repo as of 2026-09-03 and are the system
of record. Two others are present — `Seluma_...` and `Shilgengar_...` — with no
engine or deck module; nothing touches them.

## Sandbox limits, learned the hard way

- **Tool calls are killed at roughly 300 seconds**, and the kill takes the whole
  process tree with it. A `nohup` background job does NOT survive it: an attempt
  to run all three ablations in the background died at the first long poll
  having completed 3 cards.
- The working pattern is chunked foreground runs. `ablation.py` writes its cache
  after every card and `ABLATE_BUDGET` stops a pass cleanly, so:

      ABLATE_BUDGET=220 timeout 265 python3 ablation.py <deck> 6000 20 >/dev/null 2>&1

  Repeat until cached == total, then run once more redirected to
  `ablation_<deck>.txt` to emit the table. ~8 cards per call at ~28s/card;
  a full three-deck regen is ~95 minutes and ~25 calls.
- Network egress is allowlisted. `pypi.org` and `github.com` work.
  **`api.scryfall.com` does NOT** — the proxy returns 403 with
  `x-deny-reason: host_not_allowed`, even though the declared environment config
  lists it as permitted. The declared and enforced policies are out of sync;
  a fresh container may pick the change up. Until it does, no oracle-text
  verification is possible and `tag_flying.py` cannot run.

## Ablation cache

The key now includes the sample size: `ablation_cache_<deck>_<horizons>_n<N>.json`.
Previously it did not, so resuming at a different N silently merged two sample
sizes into one table. **The three caches from the 2026-09-02 regen are named
without `_n6000` and will not be found.** Rename them to insert `_n6000` before
`.json` to reuse that work; the finished `.txt` tables are unaffected.
