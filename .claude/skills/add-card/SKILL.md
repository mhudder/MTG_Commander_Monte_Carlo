---
name: add-card
description: Import a Magic card into the EDH Monte Carlo simulator — verify its text, review which clauses the engine can model, implement it in the right engine, pin the mechanism with a test, measure it, and record the result in the ledger. Use when the user proposes a card, asks to evaluate or test a card, or asks to add a card to a deck.
---

# Adding a card, end to end

This is a procedure, not a checklist of every interaction. It exists because
almost every large correction in this project came from a card whose text the
engine had wrong, not from a statistical problem — and because the same
mistakes have been made more than once by sessions that skipped a step. Each
step names the check that catches the mistake it exists to prevent.

The stages a card passes through, and where each is recorded:

| stage | what exists | where |
|---|---|---|
| PROPOSED | verified oracle text and an argument; nothing measured | `edhmc/pending.py` `PROPOSED` |
| defined | a `C()`/`L()` constant the engine can play | `edhmc/decks/<deck>_v<N>.py` |
| implemented | every clause either modelled, or named as a gap | the engine, `tools/ablation.py`'s classification |
| pinned | a test that fails if the mechanism stops firing | `tests/test_*.py` |
| MEASURED | a candidate row with its bar and signal | `edhmc/pending.py` `MEASURED` |
| STAGED | a head-to-head against a named cut | `edhmc/pending.py` `CHANGES` |
| COMMITTED | module, `.xlsx` and ledger all moved, in one commit | all three legs |

Do them in order. A card that skips "pinned" has produced a wrong headline
number in this project (§0z28); a card that skips "head-to-head" has produced
two withdrawn swaps (§0z, §0z2).

---

## 1. Import: get the text, and check it is not already here

**Fetch the oracle text from Scryfall. Never type it from memory.** Two
proposals were once written into a mono-green deck from memory and were
off-colour; a third had the wrong text. The API needs a `User-Agent` header:

```python
import urllib.request, json
req = urllib.request.Request(
    "https://api.scryfall.com/cards/named?exact=Bloodthirsty%20Conqueror",
    headers={"User-Agent": "EDHMC/1.0", "Accept": "application/json"})
d = json.load(urllib.request.urlopen(req, timeout=30))
d["name"], d["mana_cost"], d["type_line"], d["oracle_text"], d["keywords"]
```

If the proxy answers 403, the environment's network access is at its default
level — CLAUDE.md says how to fix it. Do not proceed on remembered text.

**Then ask the repo whether it already knows the card.** One command, and it
is derived rather than grepped:

```bash
python -m tools.card_known "Card Name" ...     # exit 1 if known anywhere
python -m tools.card_known --stdin --unknown-only < names.txt   # filter a set
```

It checks every deck list and commander, every per-deck catalog, **every card
object in every `tools/candidates.py` batch**, all five ledger lists, and the
name as a string literal in `edhmc/*.py` / `tools/*.py`.

**This step used to say "grep three places", and one of the three could not
work.** `tools/candidates.py` imports card CONSTANTS and never writes a card's
name, so `grep "Enlightened Confidant" tools/candidates.py` finds nothing about
a card that file measures — and on 2026-09-20 a session ran exactly that grep,
concluded the card was unmeasured, and said so. It had been measured on
2026-09-04 at +0.0087 ±0.0034. §0q applies to a PROCEDURE as much as to a name
set: derive the answer instead of asking a human to spell a constant right.

Two of fifteen proposals in one batch were cards that had already been
measured, inside their bars (§0z26). And **behaviour attaches by name at
least as often as by `script=`** (§0z25): Heliod, Sun-Crowned has no script
and is implemented in full in `karlov.py`, which is why the check looks at
string literals in the engines too.

**Record the proposal** as a `Proposal` in `edhmc/pending.py`'s `PROPOSED`
list: deck, card, cost, colour identity, type line, the oracle text verbatim,
the date verified, the rationale, and `implement` — your estimate of what it
would take to make the card behave like its text. `check_proposals()` runs at
import and refuses a card that is off-colour for the deck, already in the
list, or missing its verified text. Run `python -m edhmc.pending` and read
what it prints.

---

## 2. Review: which clauses can this engine see?

> **This step is a GATE** (queued item 23, built 2026-09-26). Run the screen
> first; it costs seconds and implementation costs a session:
>
> ```bash
> python -m tools.triage --proposals     # every live Proposal, clause by clause
> ```
>
> It calls a card **BLIND** only when every clause matches a §4 limit and the
> card has no body, and **REVIEW** otherwise — it is optimistic by
> construction, because its only fatal error is discarding a good card. Record
> the verdict on the Proposal: `triage="BLIND"` with `triage_clauses` quoting
> the blind clauses verbatim, `triage="DEFERRED"` with `triage_note` naming the
> machinery it waits for, or `triage="LIVE"`. `check_triage` refuses a BLIND
> that quotes nothing, or quotes text the card does not have. **A BLIND or
> DEFERRED card stops here**; REVIEW means you do the sort below by hand.

Read the oracle text clause by clause and sort every clause into one of
three bins. Write the sort down in the proposal's `implement` field; it is
the card's classification later.

**Modelled** — the clause maps onto something the engine represents. The
engine represents: your hand, library, graveyard and board; your mana, life
and land drops; your creatures' power, toughness, flying and indestructible;
tokens; your own spells cast and permanents entering; the opponents' life
totals, an abstract creature count per opponent, and a per-opponent clock.
`docs/ARCHITECTURE.md` names the hooks: entering the battlefield
(`run_etb`, `make_permanent`), dying (`on_creature_death`), tokens
(`make_tokens`), upkeep, draw, end step, and each engine's `resolve` /
`apply_spell_effects` for a spell's own effect.

**Blind** — the clause needs something the model does not have. **Opponents'
boards are an abstract number, not permanents** (§4), so targeted removal,
counterspells, wraths aimed at them, "whenever an opponent casts", "target
opponent sacrifices" and decking an OPPONENT (they have no library) are
all blind. Commander damage (104.3j) is NOT, since §0z65 -- but only YOUR
commander's, dealt through `opponents.combat_damage`; a card that grows or
protects the commander now has a second channel to show up in. Decking YOURSELF is modelled since
§0z42: a draw from an empty library loses, and an optional draw is declined
by `engine.draw_is_safe` -- a card that draws must say which of its draws are
a choice. A blind clause is not a defect to fix in the card; it is a
limit of the model to name. A card whose value is entirely blind goes in
`KNOWN_BLIND` with the reason and its row will read as a blank — which is
"not measured", never "bad".

**Partly** — some clauses modelled, one named clause not. The card's row is
then a FLOOR and prints under PARTLY MODELLED with the missing clause as its
reason, wrapped under the row in the table so a reader who copies the row
copies the caveat. **Every symmetric wipe is PARTLY by construction** and is
derived rather than listed (`symmetric_wipes`): your half is faithful, the
opponents' half only zeroes an abstract count, so the COST is modelled and
the BENEFIT is an estimate. A hand-written entry wins over the derived one
when it can name a more specific clause — Promise of Loyalty says "everyone
KEEPS ONE, and the model keeps none", which is more useful than the generic
wipe reason.

While sorting, ask four questions that have each cost a session:

- **Does the same rule already exist elsewhere?** Grep the other five engines
  for the mechanism (not just the card): "whenever you gain life",
  "create a token", "extra turn". The same rule implemented twice has been
  implemented two different ways six times (§0u, §0z8). Reuse the shared
  primitive; if one engine has quietly opted out of it, ask what it knew.
- **Is it a replacement effect on mana or tokens?** Then it has to be said in
  EVERY path that produces the thing. A mana doubler lives in both
  `available_mana` and `spend` or it does nothing (§0z4); tivit has two token
  paths and Anointed Procession had to be said in both.
- **Does it read a subtype?** `Card.types` holds card types only. Human,
  Forest, Elf, Elemental come from the generated sets in
  `decks/_evasion.py`, never typed by hand (§0z4).
- **Does it read a zone that something else can change?** Compute the pool of
  candidates per use, or re-check membership before touching it: a selection
  is a snapshot and the zone is live (§0z19).

Read the comprehensive rules (`docs/MagicCompRules_20260807.txt`, grep by
rule number) when a clause's timing matters. A rule number is evidence about
the game, not about this engine.

---

## 3. Define the card in the deck module

In `edhmc/decks/<deck>_v<N>.py`, in the candidates block at the bottom, as a
module-level constant — never a second definition of a card already in the
list (that is dead code the moment it is written, and two decks had one).

```python
BLOODTHIRSTY_CONQUEROR = C("Bloodthirsty Conqueror", "Creature",
                           {"gen": 3, "B": 2}, 5, 5,
                           priority=8.5, threat=8.0)
```

- **Costs, not mana values.** `{"gen": 3, "B": 2}` — colour screw is exactly
  what the harness is good at surfacing, and a mana value cannot express it.
  Copy the cost from Scryfall's `mana_cost`.
- **`priority`** drives the greedy casting policy (queued item 18: it is
  greedy and it is the weakest link). Put the card near cards of similar
  value in the same deck; the number is a policy, not a fact, and the tables
  were tuned with it.
- **`threat`** is how badly opponents want it dead; `0` derives it from
  power and mana value. An explicit `threat` on a weak card can be the whole
  score (§0j, queued item 22). Set it only when the card's text warrants it.
- **`script="name"`** only if the engine will dispatch on it (step 4). A
  script nothing dispatches, and a tag nothing reads, is a loaded gun, not
  inert (§0z12).
- **Flying and indestructible are NOT parameters you set.** They come from
  Scryfall through the generated file:

```bash
python -m tools.tag_flying --write     # regenerates edhmc/decks/_evasion.py
```

Run it now, in the same change. A card added without it is a ground creature
whatever its text says, and that is how a 5/5 flier was staged as a ground
creature (§0z29). `python -m tools.check_docs` fails until you do.

Add the constant to the deck's batch tuple (e.g. `BATCH_2026_09_16`) so
`tools/candidates.py` can find it, and to `edhmc/pending.py`'s `DECKS`
catalog so a `Change` can name it.

---

## 4. Implement: put each modelled clause where behaviour lives

`docs/ARCHITECTURE.md` "Where a card's behaviour can live" is the map. The
short version, by engine:

| engine | a spell's effect | a permanent entering | a trigger |
|---|---|---|---|
| `engine.py` (rendmaw) | `main_phase`, `if card.script == "..."` after the cast | `run_etb` | `make_tokens`, `on_creature_death`, `upkeep`, `activations`, `attack_triggers` |
| `lorehold.py` | `apply_spell_effects` | `resolve_spell` | the miracle/top-deck loop, `upkeep` |
| `karlov.py` | `resolve` | `creature_entered` | `gain_life` (every lifegain EVENT), `upkeep`, `end_step` |
| `tivit.py` | `resolve` | `run_etb` | `on_tokens_created`, both token paths |
| `shilgengar.py` | `Game.resolve` | `creature_entered` | `activations`, `upkeep`, `end_step` |
| `azusa.py` | `Game.resolve` | `make_permanent` | `_landfall_payoffs`, `activations` |

Shared state and primitives live in `engine.py` (`BaseGame`, `Card`,
`Permanent`, `can_pay`, `spend`, `play_land`) and the pod in
`opponents.py`. A rule that lives in a module-level function is written once;
a rule that lives in a method has six copies and drifts (§0z30, §0z32). Put
anything shared in a function.

Rules that are not optional:

- **Add a mechanism counter.** `g.m["conqueror_triggers"] += 1` at the point
  the card's text fires. This is how a card is shown to work: a mechanism
  that fires zero times is unmistakable where a win rate 0.03 too low is not
  (CLAUDE.md, "The biggest corrections have been POLICY"). `g.m` is a
  `Metrics` and reads 0 for a name nothing has written, so the counter needs
  no declaration — but if the card draws, check `cards_drawn` against the sum
  of every draw counter afterwards (§0z28).
- **Randomness goes through `crn_random` / `crn_randrange` / `crn_shuffle`.**
  Never `g.rng` after the opening hand. `tests/test_crn_streams.py` catches
  it; the A/A control cannot (§0z17).
- **When you add to a shared hook, read the neighbour.** Two cards on one
  hook are one indentation apart (§0z28): inserting Guardian Project between
  The Great Henge's counter and its draw moved the draw into the new `if`.
  Re-run the test that pins the neighbour.
- **If the card needs a knob** — a cap, a reserve, a policy switch — read it
  with `cfg.get("name", default)`, then `python -m tools.knobs --write`, and
  say the knob out loud in the write-up. A knob whose setting a card's
  ranking rests on is a judgement, not a measurement.
- **Life costs are real** (§0i, §0z7): a card that pays life charges
  `g.your_life`. Life decides games since pod v3.
- **Do not implement the blind clauses.** Name them.

Then classify the card in `tools/ablation.py`: `SCRIPTED_<DECK>` if every
clause that matters is implemented, `PARTLY_MODELLED[deck]` with the missing
clause as the reason, or `KNOWN_BLIND[deck]` with the reason. A card in the
measured list that is in none of the three makes `check_scripted_coverage`
refuse to run. The classification is a claim about the engine, made on
purpose, and it decides which section the card's row prints under.

---

## 5. Pin the mechanism before measuring anything

Write `tests/test_<card_or_mechanism>.py` in the house shape (see
`tests/test_metrics_and_render.py` for a small one): a `check(name, got,
want)` tally, `N passed, M failed` printed last, a non-zero exit on failure,
and a `--mutate` mode. **Write the mutation's expected failure set before you
run it.** Every mutation list this project has added was wrong on its first
try, and every error was informative (§0z14, §0z30); a set edited to match
the output is a transcript, not a test.

What to pin: that the counter fires when the text says it should, on a
scripted game state you construct (a stub game with `Metrics()` for `m` is
fine — see `tests/test_combat_split.py`), and that it does not fire when the
text says it should not. One assertion per clause.

Then:

```bash
python -m tests.<your new module>            # yours, plain
python -m tests.<your new module> --mutate   # the exact set
python -m tests                              # every pinned mechanism
python -m tools.validate                     # +0.00 on all 18 metrics
```

**If you touched `engine.py`, `opponents.py`, `experiment.py` or any shared
primitive**, prove the other decks did not move:

```bash
git worktree add ../edhmc_head HEAD
(cd ../edhmc_head && python -m tools.check_unchanged_decks --out=old.json)
python -m tools.check_unchanged_decks --out=new.json
python -m tools.check_unchanged_decks --diff old.json new.json
```

Bit-identical is the pass. Anything else is a deck whose table needs
rebuilding — and if you unified copies that differed, compare every output
key, not the eight baseline metrics (§0z32).

---

## 6. Measure: a smoke run, a candidate row, then a head-to-head

**The smoke run (tier 2), before anything at N=15,000.** A count has far
lower variance than a win rate, so "does this card fire" is decidable in
seconds:

```bash
python -m tools.triage --smoke karlov "New Card" --n 1000
```

It prints P(cast) and every counter that moved against a blank in the
candidates slot, sorted by |z|. **The card's own counter must be in that
list.** If it is not, or the counters that moved are not the ones its text
predicts, the implementation or the deck is the problem, and a candidate row
would only put a confidence interval on it (Sai's Thopters, §0z26).


**The candidate row.** Add a batch to `tools/candidates.py`'s `DECKS` dict
naming the victim slot the deck already uses, then run it at the tables' N:

```python
"karlov3": ("KARLOV", "karlov", karlov_sim, 20, "Soulmender", (NEW_CARD,)),
```

```bash
python -m tools.candidates karlov3 --n=15000 > results/candidates_karlov3.txt
```

Read the row with its bar and its signal (`both` / `dmg` / `win` / `--`).
`--` means inside its own bar: unmeasured, not bad. Record it as a
`Candidate` in `edhmc/pending.py`'s `MEASURED` list, with `limits` naming
every floor and ceiling (the blind clause, a life cost the model does not
charge, decking) and `verdict` saying what the number supports and what it
does not.

**Check the counter.** If the card is a top-set candidate and its counter
fires 0.155 times a game, the engine has made it a blank — Sai reads artifact
SPELLS and tivit makes artifact TOKENS (§0z26). Suspect the engine before the
card.

**A candidate row is not a swap** (§0c). It is value over a blank in a freed
slot. Staging needs the real swap against a named cut, same seeds both legs:

```python
from edhmc.experiment import run_ab, analyse
ra, rb, cfg = run_ab(deck, cmd, "Soulmender", NEW_CARD, n=15000, turns=20, sim=sim)
for r in analyse(ra, rb, metrics=("won", "damage", ...)): ...
```

`diagnostics/run_karlov_conqueror.py` and `run_tivit_procession.py` are the
shape: a diagnostic file, output to `results/`, both horizons. The swap is
smaller than the candidate row — it pays for what it cut — and the swap is
the number a decision rests on.

**The cut must be a card whose row was evidence.** `python -m edhmc.pending`
classifies every staged and proposed cut; a MODEL-BLIND or PARTLY MODELLED
cut is refused unless `cut_unmeasured` says why it is cut anyway, because
the head-to-head against a blind cut is a ceiling (§0z31). A basic land cut
passes with a note: the harness flatters land cuts.

**Leave-one-out is blind to redundancy.** If the card duplicates a trigger
the deck already has, its partners' rows are understated and the package
must be ablated as a group (§0z27).

---

## 7. Stage, then commit

**Stage** by writing a `Change(deck, remove, add, staged, rationale,
evidence, notes)` into `CHANGES`. The `evidence` is the head-to-head with
its bars and horizons; `notes` carries every caveat a reader would need
months later. Staging changes `build_pending`, which is the list every
cached number was measured against, so the deck's cache goes SUSPECT and
**nothing but a rebuild clears it** — `check_unchanged_decks` builds from the
module and would certify nothing (CLAUDE.md, "more than one right check"):

```bash
rm results/caches/ablation_cache_<deck>_10-20_n15000_medblank.json
ABLATE_BUDGET=1800 python -m tools.ablation <deck> 15000 10,20 > results/ablation_<deck>.txt
```

Loop it until the table prints (`tools/regen_tables.sh` shows the loop), or
run the script for the one deck. Twenty to forty minutes for one deck on
four cores; the six-deck run is about four hours, which is why only the deck
whose baseline moved is rebuilt. Compare the new table with the old row by
row and write down what moved — the redundancy finding (§0z27) was found
exactly this way.

**Commit** a deck change only when all three legs agree — the deck module,
the `.xlsx` in `spreadsheets/` (azusa has none), and the ledger entry moved
to `COMMITTED` — in one git commit. Then the closing checklist, which is
`.claude/skills/session-close/SKILL.md`:

```bash
python -m tools.knobs --write           # if you touched a cfg.get
python -m tools.tag_flying --write      # you added a card: always
python -m tools.cache_manifest --write  # if a cache changed
python -m tools.status --write          # always
python -m tools.check_docs              # must pass
python -m edhmc.pending                 # legality, and the cut report
python -m tests                         # must pass
```

**Write it down.** The measurement goes in `KNOWN_ISSUES.md` under a new
`§0z<n>` with its evidence; only its lesson, with no date in it, is promoted
to `CLAUDE.md`. A number nobody can trace to a card's text is not a result
yet.

---

## The short form, for the agent in a hurry

1. Scryfall, with a User-Agent. Grep the deck, `candidates.py` and the
   engines for the NAME. Write the `Proposal`.
2. `python -m tools.triage --proposals`: BLIND or DEFERRED stops here, with
   the flag and its clauses on the Proposal. Otherwise sort every clause:
   modelled / partly / blind. Grep the other engines for the same rule.
   Doublers go in every path.
3. `C()` with the real cost; `tag_flying --write`; batch tuple; catalog.
4. Implement in the hook the map names; add a counter; CRN for randomness;
   classify in `ablation.py`.
5. A test with a mutation set written first; `python -m tests`; `validate`
   at +0.00; `check_unchanged_decks` if shared code moved.
6. `tools.triage --smoke` at N=1000: its own counter must move. Then the
   candidate row at N=15,000 → `MEASURED`. Then a real swap against a cut
   whose row was evidence.
7. `Change` → rebuild that deck's table → three legs in one commit → the
   closing checklist → a `§` for the measurement.
