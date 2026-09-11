# How to read an ablation table

Moved out of `KNOWN_ISSUES.md` on 2026-09-09: it is methodology, not an issue,
and it was the only section of that file nobody could cite by number.
`CLAUDE.md`'s "Standing findings" is the short version; this is the long one.

The examples below are quoted at the sample size they were measured at, mostly
N=6,000. **All six live tables are N=15,000** and their bars are correspondingly
tighter — the numbers here illustrate the failure modes, they are not current
card evaluations. Read the current tables in `results/`.


A reasonable first filter is: **a card is pulling its weight if it is positive on
damage, on win rate, or both; a card positive on neither is a cut candidate.**
That is right most of the time. Three failure modes, in the order they bite.

## 1. A "+" is not necessarily a real "+"

The tables print point estimates. Many of them are smaller than their own error
bars. At 6,000 paired games on Karlov:

| card | damage | win rate | survives? |
|---|---|---|---|
| Suture Priest | +3.07 ±0.59 | +0.0108 ±0.0047 | both |
| Kambal | +3.14 ±0.59 | +0.0047 ±0.0050 | damage only |
| Mother of Runes | +0.70 ±0.55 | +0.0033 ±0.0040 | damage only |
| Pristine Talisman | +0.24 ±0.41 | −0.0003 ±0.0032 | **neither** |

Anything under roughly **+0.6 damage** or **+0.005 win rate** at this sample size
is indistinguishable from a blank. Treat the bottom of the table as unranked
rather than ranked.

## 2. Win rate beats damage where they disagree

Since the opponent clock landed, win rate is the actual objective and damage is
only a proxy. Extra damage on a game you were winning anyway buys nothing.

Archangel of Thune is +5.13 damage but only +0.0030 win rate. Well of Lost
Dreams is +2.35 damage and **+0.0210 win rate** — the highest in the deck. Vito
is +0.29 damage and +0.0200 win. The damage column ranks those three in exactly
the wrong order. **When the columns disagree, believe win rate.**

## 3. Leave-one-out is blind to redundancy

This is the one that produces genuinely wrong cuts. Removing one card of an
interchangeable set understates all of them, because the others cover.

Karlov runs three combo partners for Exquisite Blood. Removing any single one:

| removed | damage | win rate |
|---|---|---|
| Sanguine Bond | +1.40 | +0.0203 |
| Vito | +1.40 | +0.0163 |
| Vizkopa Guildmage | −1.76 | +0.0095 |
| **all three together** | −1.71 | **+0.0513** |
| Exquisite Blood alone | −7.01 | +0.0240 |

The three partners are worth +0.0513 win rate as a group — **more than double**
the largest individual score, and far more than any of them looks worth alone.
Vizkopa Guildmage in particular reads negative on damage and would be cut under
the simple rule, when it is a third of a package worth five points of win rate.

The same logic applies to the soul sisters, the equipment suite, and the wraths.
For any set of interchangeable effects, **ablate the group, not the members.**
`ablation.py`'s `ablate()` already accepts a list of names.

## 4. The blank is not replacement level, and the bottom of the table pays for it

Full write-up in **§0j**. `blank_like()` copies the card's cost and nothing
else, so the comparison is really:

    (card, hand-assigned threat 5-9, cast eagerly)
      vs
    (blank, derived threat 0.5-2.5, cast only when nothing else is affordable)

and the whole difference is charged to the card. It is independent of what the
card does, so it is invisible on a strong card and can be the entire score on a
weak one. Corrected, karlov's Blood Artist goes −0.0050 → +0.0014 and lorehold's
Smothering Tithe −0.0002 → +0.0050, while Blasphemous Act and Lightning Greaves
do not move at all.

The cheap test before trusting any low row: **does the card carry an explicit
`threat`?** If it is `0.0`, the blank derives threat by the same rule and that
channel cancels. If it is set, run `diag_threat_blank.py` on it.

## The rule, restated

1. Ignore anything inside its own error bars.
2. Where damage and win rate disagree, follow win rate.
3. Before cutting, ask whether another card in the deck does the same job — and
   if so, ablate them together.
4. Before cutting a card that carries an explicit `threat`, check what it scores
   against a blank that is not a free ride — `diag_threat_blank.py`.
