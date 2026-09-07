# Handoff

Orientation for a human picking this project up — what it is, what state it's
in, and where to look next. Not exhaustive; `CLAUDE.md` is the exhaustive
version (1000+ lines of dated session notes) and is worth grep-ing, not
reading top to bottom.

## What this is

A Monte Carlo simulator for testing Commander (EDH) decklist changes: "is
card X better than card Y in this deck?", answered with a number and a
confidence interval. Six decks, six simulation engines, one shared opponent
model, one paired A/B statistics harness. Run from the repo root with
Python 3.10+, numpy, scipy (`pip install -r requirements.txt`).

```bash
python -m edhmc.pending            # what's staged for each deck, and why
python validate.py                 # harness self-check — must print +0.00 everywhere
python ablation.py karlov 6000 20  # rank every card in a deck
python audit_cards.py              # every card's data checked against Scryfall
```

## The six decks

| commander | archetype | file | tuning status |
|---|---|---|---|
| Rendmaw, Creaking Nest | tokens / aggro | `edhmc/decks/rendmaw_v12.py` | mature — ablated, staged changes under review |
| Lorehold, the Historian | miracle / top-deck | `edhmc/decks/lorehold_v16.py` | mature |
| Karlov of the Ghost Council | lifegain / drain | `edhmc/decks/karlov_v2.py` | mature |
| Tivit, Seller of Secrets | votes / artifacts | `edhmc/decks/tivit_v1.py` | mature |
| Shilgengar, Sire of Famine | Angels / aristocrats | `edhmc/decks/shilgengar_v1.py` | new — ablated, and its commander's own ability only started firing on 2026-09-07 (`KNOWN_ISSUES.md` 0r) |
| Azusa, Lost but Seeking | landfall / ramp / big creatures | `edhmc/decks/azusa_v1.py` | new — ablated; no `.xlsx` yet, so the module is the only record |

Each of the first four decks, and Shilgengar, is a `.xlsx` (the human-readable system of
record for the card list) plus a matching `edhmc/decks/<name>_v<N>.py`
module (the hand-authored, Scryfall-verified costs the simulator actually
reads) plus its own simulation engine — `edhmc/engine.py` (Rendmaw),
`edhmc/lorehold.py`, `edhmc/karlov.py`, `edhmc/tivit.py`,
`edhmc/shilgengar.py`, `edhmc/azusa.py`. Azusa was submitted as a plain table
rather than a spreadsheet, so its module is the only system of record until
someone builds a `.xlsx` for it. Every engine shares `edhmc/opponents.py`
(the three-opponent interaction model) and `edhmc/experiment.py` (the A/B
harness), and plugs into it the same way:
`run_ab(deck, commander, out_card, in_card, sim=<engine>.simulate)`.

**Why six engines instead of one.** Each commander's payoff is structurally
different enough that a shared turn loop would be mostly `if deck == X`
branches. Rendmaw wins on the board; Lorehold wins by casting free spells off
the top of the library; Karlov by counting lifegain events; Tivit by voting;
Shilgengar by sacrificing creatures for Blood and periodically reanimating
its graveyard; Azusa by playing more lands than one a turn and having that
matter twice — once for the mana, once for every landfall trigger it sets
off. Each engine is a few hundred lines built on the same primitives (`Card`,
`Permanent`, mana, the greedy casting policy).

## Is any of this trustworthy right now?

Run `python validate.py`. It plays each deck against an exact copy of itself
under the same shuffle seed (common random numbers) and must print `+0.00` on
every metric for every engine. If it doesn't, something is leaking randomness
between the two branches of every A/B test in the project and nothing else
here can be trusted until that's fixed.

Run `python audit_cards.py`. It checks every card's cost, power/toughness,
type line, and flying/indestructible against live Scryfall data. It should
print `0 ERR`. A handful of `WARN`/`NOTE` lines are known, deliberate
simplifications (documented inline where they're raised) — read them once,
don't chase them.

## What "staged" and "committed" mean here

A card swap goes through three states:

1. **Measured** — an A/B run produced a confidence interval on win rate (the
   objective) and a couple of proxy metrics (damage, card draw). Written up
   as a comment.
2. **Staged** — recorded in `edhmc/pending.py`'s `CHANGES` list. The deck
   module does NOT yet reflect it; `python -m edhmc.pending` is the only
   trustworthy statement of what's currently staged (don't trust
   `DECK_CHANGES.md`'s table — it's a hand-written summary and it drifts).
3. **Committed** — applied to all three legs at once: the deck module, the
   `.xlsx`, and `pending.py`'s `COMMITTED` list. A change is not considered
   done until all three move together.

As of this writing there are three staged, uncommitted swaps (two on
Lorehold, one on Rendmaw) — run `python -m edhmc.pending` for the current
list and the evidence behind each.

## The one rule that matters more than any other

**Half of every deck is invisible to this model, and that's fine as long as
you know which half.** Opponents' boards are an abstract number, not real
permanents — so any removal spell, counterspell, or board wipe you play
scores as an inert body, because there's nothing concrete for it to remove.
That's not a bug and it's not a verdict on the card; every ablation table
splits its output into MODEL-EVALUATED (a low score means something) and
MODEL-BLIND (a low score means the model has no eyes there). Read the
MODEL-BLIND table as "not measured," never as a cut list.

The corollary: **win rate is the objective, damage and other proxies are
not.** They disagree more often than you'd expect (a card can raise the mana
you're casting each turn while win rate doesn't move at all). Where they
disagree, the project's own rule is to follow win rate.

## If you're adding another deck

1. Get the `.xlsx` into the repo root.
2. Verify costs/P-T/keywords against Scryfall before writing anything —
   `audit_cards.py`'s `fetch()` function shows the pattern. Don't hand-tag
   flying or indestructible from memory; both are Scryfall-keyword-generated
   (`tag_flying.py --write`) for the reason explained in that file's
   docstring — a partial tag list biases every comparison toward whichever
   cards you happened to remember.
3. Write `edhmc/decks/<name>_v1.py` (the `C()`/`L()` card-list pattern —
   copy an existing deck module) and `edhmc/<name>.py` (the engine — copy
   whichever existing engine is the closest structural match; `karlov.py` is
   the shortest full example).
4. `audit_cards.py` and `tag_flying.py` will find it automatically — see
   `edhmc/decks/__init__.py`. Everything else needs a deliberate edit: add
   the deck to `ablation.py`'s `SIM`/`METRIC_SETS`/`SCRIPTED_*`/`KNOWN_BLIND`
   dicts (twice — there's a duplicate in the multiprocessing worker init),
   `pending.py`'s `DECKS` dict, `cache_manifest.py`'s `PER_DECK`, and add an
   A/A control block to `validate.py`.
5. `python validate.py` must come back `+0.00` before you trust a single
   number out of the new engine.

## Reading order

- **This file** — orientation, current state, how to not get burned.
- **`README.md`** — the methodology writeup (common random numbers, paired
  inference, why they work). Trustworthy on technique; the numbers it quotes
  predate several corrections and shouldn't be cited.
- **`CLAUDE.md`** — the full dated history. Every correction, every bug, every
  "the model said X, it was wrong because Y." Worth searching, not reading
  linearly — the "Current state" section near the top is the part that's
  kept up to date.
- **`KNOWN_ISSUES.md`** — per-question diagnostics with numbered findings,
  cross-referenced from `CLAUDE.md`.

## A pattern worth knowing before you trust any card's row

Three of the largest corrections in this project were not a card's TEXT being
wrong. They were a POLICY — a decision about how the deck is piloted — written
down as conservatism and never measured:

| policy | what it actually asserted | worth |
|---|---|---|
| Azusa's `land_step` ran once, before any spell resolved | every land enabler is dead on the turn it lands | 0.074 win rate |
| Shilgengar would only sacrifice 1/1 tokens | the commander's own ability does nothing | 0.034 win rate |
| Shilgengar's main phase spent every point of mana | an after-combat ability is never affordable | 0.008 win rate |

None of the three was visible in an ablation table, because in each case the
affected cards produced *plausible* numbers — a bit low, nothing to notice.
The tell is a card whose text says it should be central to the deck and whose
row says it is ordinary. When you see one, suspect the engine before the card,
and check the MECHANISM COUNTERS (`blood_made`, `landfall_triggers`,
`pw_activations`) rather than the win rate: a mechanism that fires zero times
is unmistakable where a win rate 0.03 too low is not.
