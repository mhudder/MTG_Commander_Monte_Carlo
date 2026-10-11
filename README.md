# EDH Monte Carlo — paired A/B testing for Commander decklists

A simulator and a statistics harness for one question: **is card X better than
card Y in this deck?** The answer is a paired difference with a confidence
interval, not a vibe, and a result is not accepted until its mechanism can be
traced to the card's text.

Seven decks, one simulation engine per deck, one shared opponent model, one
paired A/B harness.

**New here? Read [`HANDOFF.md`](HANDOFF.md).** It is the orientation: what this
is, how it works, and the ways previous sessions got burned.
[`docs/STATUS.md`](docs/STATUS.md) is what is true now (tables, noise floors,
staged swaps), generated from the repository rather than written by hand.

## How it works

- **Common random numbers.** Deck A and deck B are the same list with one slot
  swapped, shuffled on the same seed, so the other 98 cards sit in the same
  library positions in both games. Every random effect after the opening hand
  draws from its own addressed stream, so the two games stay aligned however
  their boards diverge. Nearly all game-to-game variance cancels in the
  difference; `python -m tools.validate` prints how much it buys.
- **Paired inference.** Every number is a mean of per-game differences
  `metric(B) - metric(A)` with its 95% CI, never two means compared.
- **Leave-one-out ablation.** `tools.ablation` replaces each nonland card with a
  blank of the same cost, cast at the deck's median priority, and reports the
  paired difference for every card.
- **A pod that fights back.** Three opponents with bracket-calibrated kill
  clocks, threat-weighted removal, counterspells and wipes. Win rate is the
  objective; damage and the mechanism counters are diagnostics.

## What it cannot see

Opponents' boards are an abstract number, so your removal, counterspells and
wipes have nothing to hit. Those cards are labelled **MODEL-BLIND**: not
measured, which is not the same as bad. A table is a set of significant rows,
not a ranking, and a swap is decided by a head-to-head run with the cut in one
leg and the candidate in the other, never by subtracting two rows. `HANDOFF.md`
and `docs/READING_TABLES.md` say how to read the output.

## Start here

Python 3.10+, numpy, scipy, openpyxl. Everything runs from the repo root with
`-m`.

```bash
pip install -r requirements.txt
python -m tools.status       # what state is the project in?
python -m tools.validate     # A/A control: must print exactly +0.00
python -m edhmc.pending      # what is staged, and is every list legal?
python -m tests              # do the pinned mechanisms still hold?
python -m tools.check_docs   # do the docs still describe the repo?
```

Every other command is in [`docs/COMMANDS.md`](docs/COMMANDS.md), discovered
from disk. How the modules connect is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The original methodology writeup, with its September 2026 results, is kept as
provenance in `docs/archive/README_2026-09.md`. Its numbers are superseded.
