# MTG_Commander_Monte_Carlo

[HANDOFF.md](https://github.com/user-attachments/files/31762756/HANDOFF.md)
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
