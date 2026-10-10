---
name: add-card
description: Import a Magic card into the EDH Monte Carlo simulator — verify its text, review which clauses the engine can model, implement it in the right engine, pin the mechanism with a test, measure it, and record the result in the ledger. Use when the user proposes a card, asks to evaluate or test a card, or asks to add a card to a deck.
---

# Adding a card, end to end

Almost every large correction in this project came from a card whose text the
engine had wrong. Each step below names the check that catches the mistake it
exists to prevent. Do them in order: skipping "pin" once produced a wrong
headline number (§0z28), and skipping the head-to-head produced two withdrawn
swaps (§0z, §0z2). The stages and their names are `docs/LEDGER_STATES.md`.
The longer form, with the story behind each step, is
`docs/archive/ADD_CARD_SKILL_2026-10-10.md`.

| stage | what exists | where |
|---|---|---|
| PROPOSED | verified oracle text and an argument | `edhmc/pending.py` `PROPOSED` |
| defined | a `C()`/`L()` constant | `edhmc/decks/<deck>_v<N>.py` |
| implemented | every clause modelled or named as a gap | the engine; `tools/ablation.py`'s classification |
| pinned | a test that fails if the mechanism stops firing | `tests/test_*.py` |
| MEASURED | a candidate row with its bar and signal | `pending.py` `MEASURED` |
| STAGED | a head-to-head against a named cut | `pending.py` `CHANGES` |
| COMMITTED | module, `.xlsx` and ledger, one commit | all three legs |

---

## 1. Import: the text, and whether the repo already knows the card

**Fetch the oracle text from Scryfall; never type it from memory** (two
proposals were once off-colour, a third had the wrong text). It needs a
`User-Agent`; a 403 from the proxy means the network level, which CLAUDE.md
explains.

```python
import urllib.request, json
req = urllib.request.Request(
    "https://api.scryfall.com/cards/named?exact=Bloodthirsty%20Conqueror",
    headers={"User-Agent": "EDHMC/1.0", "Accept": "application/json"})
d = json.load(urllib.request.urlopen(req, timeout=30))
d["name"], d["mana_cost"], d["type_line"], d["oracle_text"], d["keywords"]
```

**Then ask the repo, by command, not by grep:**

```bash
python -m tools.card_known "Card Name" ...     # exit 1 if known anywhere
python -m tools.card_known --stdin --unknown-only < names.txt
```

It checks every list, catalog, `tools/candidates.py` batch (which names
CONSTANTS, so grepping it for a card name finds nothing), the ledger, and
string literals in the engines, because behaviour attaches by name at least as
often as by `script=` (§0z25). Two of fifteen proposals in one batch had
already been measured (§0z26).

**Record a `Proposal`** in `PROPOSED`: deck, card, cost, identity, type line,
oracle text verbatim, date verified, rationale, and `implement` (what it would
take). `check_proposals()` refuses an off-colour, duplicate or unverified card
at import. Read `python -m edhmc.pending --card "Card Name"`.

---

## 2. Review: which clauses can this engine see?

**This step is a GATE** (item 23). Run the screen first; it costs seconds:

```bash
python -m tools.triage --proposals
```

It calls a card **BLIND** only when every clause matches a §4 limit and the
card has no body, **REVIEW** otherwise. Record `triage="BLIND"` with
`triage_clauses` quoting the blind clauses verbatim, `"DEFERRED"` with
`triage_note` naming the machinery it waits for, or `"LIVE"`; `check_triage`
refuses a BLIND that quotes nothing or quotes text the card lacks. **BLIND or
DEFERRED stops here.**

Otherwise sort every clause into one of three bins, in `implement`:

- **Modelled**: your hand, library, graveyard, board, mana, life, land drops;
  your creatures' power, toughness, flying, indestructible; tokens; your
  spells and permanents entering; each opponent's life, an abstract creature
  count, and a clock; YOUR commander's damage (104.3j, §0z65); decking
  yourself (§0z42 — say which of the card's draws are optional).
- **Blind**: anything needing opponents' permanents (§4): targeted removal,
  counterspells, "whenever an opponent casts", "target opponent sacrifices",
  milling an opponent. Name it; do not implement it. A wholly blind card goes
  in `KNOWN_BLIND` and its row reads "not measured", never "bad".
- **Partly**: some clauses modelled, one named clause not. The row is a FLOOR
  and prints under PARTLY MODELLED with the missing clause. **Every symmetric
  wipe is PARTLY by construction** (`symmetric_wipes`); a hand entry wins
  when it can name a more specific clause.

Four questions that have each cost a session:

- **Does the same rule exist elsewhere?** Grep the other engines for the
  MECHANISM ("whenever you gain life", "create a token"), not just the card
  (§0u, §0z8). Reuse the shared primitive.
- **Is it a replacement effect on mana or tokens?** Say it in EVERY path: a
  doubler in both `available_mana` and `spend` (§0z4); tivit has two token
  paths.
- **Does it read a subtype?** Use the generated sets in `decks/_evasion.py`,
  never a typed one (§0z4).
- **Does it read a zone something else can change?** Recompute the pool per
  use (§0z19).

Timing questions: grep `docs/MagicCompRules_20260807.txt` by rule number.

---

## 3. Define the card in the deck module

A module-level constant in the candidates block of
`edhmc/decks/<deck>_v<N>.py`; never a second definition of a card already in
the list.

```python
BLOODTHIRSTY_CONQUEROR = C("Bloodthirsty Conqueror", "Creature",
                           {"gen": 3, "B": 2}, 5, 5,
                           priority=8.5, threat=8.0)
```

- **Costs, not mana values**, copied from Scryfall's `mana_cost`.
- **`priority`** drives the greedy casting policy; place it near cards of
  similar value in that deck. It is a policy, and the tables were tuned with it
  (item 18).
- **`threat`**: `0` derives it. An explicit threat on a weak card can be its
  whole score (§0j); set it only when the text warrants it.
- **`script="name"`** only if the engine dispatches on it (step 4): a tag
  nothing reads is a loaded gun (§0z12).
- **Flying, indestructible and subtypes come from Scryfall**:
  `python -m tools.tag_flying --write`, in the same change (§0z29;
  `check_docs` fails until it is run).

Add the constant to the deck's batch tuple (for `tools/candidates.py`) and to
`pending.py`'s `DECKS` catalog (so a `Change` can name it).

---

## 4. Implement each modelled clause where behaviour lives

`docs/ARCHITECTURE.md`, "Where a card's behaviour can live", is the full map.

| engine | a spell's effect | a permanent entering | a trigger |
|---|---|---|---|
| `engine.py` (rendmaw) | `main_phase`, by `card.script` | `run_etb` | `make_tokens`, `on_creature_death`, `upkeep`, `activations`, `attack_triggers` |
| `lorehold.py` | `apply_spell_effects` | `resolve_spell` | the miracle/top-deck loop, `upkeep` |
| `karlov.py` | `resolve` | `creature_entered` | `gain_life` (every lifegain EVENT), `upkeep`, `end_step` |
| `tivit.py` | `resolve` | `run_etb` | `on_tokens_created`, both token paths |
| `shilgengar.py` | `Game.resolve` | `creature_entered` | `activations`, `upkeep`, `end_step` |
| `azusa.py` | `Game.resolve` | `make_permanent` | `_landfall_payoffs`, `activations` |
| `trostani.py` | `resolve` | `make_permanent`, `creature_entered` | `create_tokens` (the one token path), `populate`, `upkeep`, `end_step` |

Shared primitives live in `engine.py` (`BaseGame`, `Card`, `Permanent`,
`can_pay`, `spend`, `play_land`) and the pod in `opponents.py`. A rule in a
module-level function is written once; one in a method drifts (§0z30, §0z32).

- **Add a mechanism counter**: `g.m["conqueror_triggers"] += 1` where the
  text fires. A mechanism that fires zero times is unmistakable; a win rate
  0.03 low is not. If the card draws, check `cards_drawn` against the sum of
  every draw counter (§0z28).
- **Randomness through `crn_random` / `crn_randrange` / `crn_shuffle`**,
  never `g.rng` after the opening hand (§0z17; `test_crn_streams` catches it).
- **On a shared hook, read the neighbour** and re-run its test: two cards on
  one hook are one indentation apart (§0z28).
- **A knob** is `cfg.get("name", default)`, then `python -m tools.knobs
  --write`, and you say it out loud in the write-up.
- **Life costs are charged** to `g.your_life` (§0i, §0z7).

Then classify in `tools/ablation.py`: `SCRIPTED_<DECK>`, `PARTLY_MODELLED`
with the missing clause, or `KNOWN_BLIND` with the reason.
`check_scripted_coverage` refuses a measured card in none of them.

---

## 5. Pin the mechanism before measuring anything

`tests/test_<card>.py` in the house shape (`tests/test_devotion.py` is a small
one): a `check(name, got, want)` tally, `N passed, M failed` last, non-zero
exit on failure, and `MUTATE = "--mutate" in sys.argv`. **Write each
mutation's expected failure set before you run it** (§0z14). One assertion per
clause: it fires when the text says, and not when it doesn't, on a game state
you construct (`tests/test_combat_split.py` stubs one).

```bash
python -m tests.<your module>           # plain
python -m tests.<your module> --mutate  # the exact sets
python -m tests                         # every pinned mechanism
python -m tools.validate                # +0.00 on every metric of every engine
```

**If you touched shared code**, prove the other decks did not move with the
`check_unchanged_decks` recipe in CLAUDE.md (worktree at HEAD, `--out` both
sides, `--diff`). Bit-identical is the pass. If you unified copies that
differed, compare every output key (§0z32).

---

## 6. Measure: smoke, candidate row, head-to-head

**Smoke first** (tier 2): a count is decidable in seconds.

```bash
python -m tools.triage --smoke karlov "New Card" --n 1000
```

**The card's own counter must be among the counters that moved**, and they
must be the ones its text predicts. If not, fix the engine; a candidate row
would only put a bar on the bug (Sai's Thopters, §0z26).

**The candidate row**: a batch in `tools/candidates.py`'s `DECKS`, in the
victim slot the deck already uses, at the tables' N:

```python
"karlov3": ("KARLOV", "karlov", karlov_sim, 20, "Soulmender", (NEW_CARD,)),
```

```bash
python -m tools.candidates karlov3 --n=15000 > results/candidates_karlov3.txt
```

Read it with its bar and signal (`--` is unmeasured, not bad). Record a
`Candidate` in `MEASURED`, with `limits` naming every floor and ceiling and
`verdict` saying what the number supports. A top-set card whose counter
barely fires is an engine blank: suspect the engine.

**A candidate row is not a swap** (§0c). Staging needs the real swap against
a named cut, same seeds, both horizons, written as a diagnostic
(`diagnostics/run_karlov_conqueror.py` is the shape):

```python
from edhmc.experiment import run_ab, analyse
ra, rb, cfg = run_ab(deck, cmd, "Soulmender", NEW_CARD, n=15000, turns=20, sim=sim)
```

Record it as `Simulated` until someone decides. **The cut must be a card
whose row was evidence**: the ledger refuses a MODEL-BLIND or PARTLY cut
without `cut_unmeasured` (§0z31), and a blind cut can cost win rate rather
than flatter (§0z36). A basic land cut passes with a note: the harness
flatters land cuts. If the card duplicates a trigger the deck has, ablate
the package as a group (§0z27).

---

## 7. Stage, rebuild, commit, write down

**Stage**: a `Change(deck, remove, add, staged, rationale, evidence, notes)`
in `CHANGES`, with the head-to-head as `evidence`. Staging moves the list
every cached number was measured against, so **only a rebuild clears that
deck's cache** — `check_unchanged_decks` would certify nothing:

```bash
rm results/caches/ablation_cache_<deck>_10-20_n15000_medblank.json
ABLATE_BUDGET=1800 python -m tools.ablation <deck> 15000 10,20 > results/ablation_<deck>.txt
```

Loop it until the table prints (`tools/regen_tables.sh` shows the loop); for
several decks, the parallel-rebuild skill. Compare the new table with the old
row by row and write down what moved.

**Commit** only when all three legs agree — module, `.xlsx` (azusa has none)
and the ledger entry moved to `COMMITTED` — in one commit, then the
session-close skill's checklist (`tag_flying --write` always, for a new card).

**Write it down**: the measurement under a new `§` in `KNOWN_ISSUES.md`, with
an index row of at most 250 characters; only its lesson, undated, goes to
`CLAUDE.md`.
