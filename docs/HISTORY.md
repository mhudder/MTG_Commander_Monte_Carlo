# Session history

Every dated session note, in the order they were written. Moved here verbatim
from `CLAUDE.md` on 2026-09-09, when that file was split into an operational
core and this archive; nothing below was reworded, and the two edits that were
made are marked inline as `[2026-09-09]`.

**This file is the PROVENANCE, not the current state.** Every number in it was
true when it was written and many have since been superseded — several sections
say so themselves, and the ones that do not are dated so you can check. For
what is true now, read `CLAUDE.md`. For a numbered finding, read
`KNOWN_ISSUES.md`, which is cross-referenced from here by section (`§0j`,
`§0r`, and so on) and whose ids are stable.

Read this file the way the project reads an ablation table: **the reasoning is
the durable part, the numbers are dated.** Sections marked VOID are kept for
exactly that reason — a table that was wrong is still evidence about how it
came to be wrong, and this project has twice recovered a real finding from one.

The order below is the order these were written in `CLAUDE.md`, deliberately
unchanged: many sections refer to each other as "the section below" or "above",
and reordering them into strict reverse chronology would have broken those
references silently. Where a reference pointed at something that stayed behind
in `CLAUDE.md`, it is marked.

---

## 2026-09-08: THE MANA RESERVE IS FREE UNTIL IT COSTS A SPELL

`KNOWN_ISSUES.md` §0t; `run_reserve_sweep.py` is the harness and
`reserve_sweep.txt` the output. Nothing changed default; both reserves are
confirmed, and one standing claim is now supported on the side it was missing.

Two engines hold mana back for a later ability, and both numbers had been set
to match a printed cost rather than measured. The question put to them was
whether a LOWER hold would do better — in particular whether it is worth
withholding mana for a play that gets answered before it can be made.

**THE WASTE IS REAL AND BIGGER THAN EXPECTED.** Lorehold holds mana on 3.73
turns a game, 7.45 mana in total, and **54% of it buys no miracle at all**. On
**0.87 turns a game the commander is dead before the windows open** — they
open after `opponents_act`, so removal takes them with it. That is 23% of the
turns it holds, and it is exactly the failure the question described.

**AND REMOVING IT GAINS NOTHING.** Dropping `miracle_reserve` to 0 is
−0.0003 ±0.0052 win rate. The mechanism is the whole answer:

    spells_cast    +0.08      <- the reserve was costing almost no spells
    mana_floated   -3.00      <- the released mana goes back into the FLOAT
    miracles_cast  -0.34      <- and the miracles it bought are real
    mv_cheated     -1.02

**The reserve was not costing the deck spells. It was parking mana the deck
could not spend anyway** — so there was nothing to win back, however wasteful
the holding looks. A reserve is free exactly while it is smaller than the
deck's spare mana, and the diagnostic for that is `spells_cast`, not the
waste counter.

**THREE IS WHERE IT STARTS COSTING SPELLS, AND THAT IS WHERE WIN RATE
BREAKS**: `spells_cast` −0.31, `stranded_mv` +2.58, win **−0.0055 ±0.0042**.
Note what the proxy does on the way there — **it casts MORE miracles (+0.063)
and LOSES games.** That is the sharpest proxy/objective disagreement this
project has produced, because here the proxy is the very quantity the knob
exists to serve. Follow win rate.

This SHARPENS the standing claim rather than overturning it. CLAUDE.md said
"raising `miracle_reserve` above 2 makes it worse — the default is right",
and that was evidence about raising it only. Lowering it is now measured too,
and it is flat: 2 is right, and it is right because it sits just under the
line where holding starts to cost a spell.

**A knob that is exactly right is not better than one that is roughly right.**
`miracle_reserve="need"` holds `miracle_need(g)` — 1 with Artist's Talent, 0
with Molecule Man — instead of a constant 2, and removes all 0.38 mana a game
of over-holding for **−0.0001 ±0.0014** win rate. A wash, so the default stays
2 and the option is documented rather than adopted. The interesting part is
why it is not free: being exact costs 0.01 miracles a game, because the
cost-reducer can be answered between your main phase and the window, and then
the need is 2 again and you held 1. **The same removal exposure that motivated
the question, one level down.**

**Shilgengar's reserve is correctly sized and for a checkable reason.**
Monotone below the ultimate's cost (0: −0.0056, 1: −0.0041, 2: −0.0023, all
significant) and flat above it (4: −0.0009 ±0.0012). Its target costs exactly
{3} or does not happen, where Lorehold's miracle can happen at several prices
or not at all — which is also why Shilgengar's is not exposed to removal at
all: `activations()` runs on your own turn between combat and a postcombat
main phase that is passed no reserve, so anything unspent is released the same
turn.

**One modelling gap this turned up and did not fix: Shilgengar's Treasures are
never spent as mana.** They accumulate for Revel in Riches' alternate win and
nothing else reads them. A real pilot holding four Treasures pays for the
ultimate out of them and reserves nothing — so the measured cost of that
reserve is an overestimate, and Pitiless Plunderer, Smothering Tithe and Black
Market Connections are all understated by whatever that is worth. Making
Treasures spendable changes every row in the deck and needs its own
regeneration, so it is filed rather than done.

**`shilgengar_ult_min_gain` is a local optimum, not one end of a slope.**
Raising it (2, 3, 5) was already known to be monotonically worse; the trend
said to check lowering it too. `run_mingain_sweep.py`: relaxing the "must be
a net gain" gate to 0 or −2 fires the ultimate MORE (+0.45 / +0.62 ults and
reanimated creatures a game) and is WORSE (**−0.0321 ±0.0044** / **−0.0327
±0.0044**). The default of 1 is a peak in both directions — a shuffle or a
small net loss costs more in tempo than the extra reanimation buys back.


---

## 2026-09-08 (later): THREE COPIES OF "THE MIRACLE DISCOUNT" HAD DRIFTED APART

`KNOWN_ISSUES.md` §0u; `run_miracle_reducer_fix.py` is the harness.
`ablation_lorehold.txt` regenerated; the previous table is void.

Asked, while investigating the mana reserve above, whether any other card
lowers the miracle cost the way Molecule Man and Artist's Talent already do.
Two more exist in this deck — **Ruby Medallion** ("Red spells you cast cost
{1} less") and **Longshot, Rebel Bowman** ("Noncreature spells you cast cost
{1} less") — and neither was consistently applied, because the discount was
computed independently in three places that had quietly drifted apart:
`miracle_value` (Molecule Man only), `miracle_need` (+ Artist's Talent), and
the real payment inside `miracle_window` (+ Ruby Medallion). **Longshot never
discounted a miracle at all**, even though every card this deck ever miracles
is an instant or sorcery — i.e. always noncreature, so his discount is not
conditional here. Ruby Medallion discounted the real payment but not either
gate that decides whether to attempt one, so `set_top` and Library of Leng
could both decline a miracle they could actually afford.

**Consolidated into one function, `miracle_reduction(g, card)`, everything
else now reads.** `set_top` and Library of Leng's redirect gate both had the
specific card in scope already (the latter needed reordering: the
affordability check used to run before the card it was checking against was
chosen) and now pass it through for the exact figure; the one card-blind
call site — the mana reserve above — keeps the same conservative worst-case
number that section already established.

**The mechanism moved; the objective did not, and both facts are legible.**

| metric, N=15,000, T20 | delta |
|---|---|
| `miracles_cast` | **+0.107 ±0.012** |
| `leng_to_top` | **+0.024 ±0.007** |
| `leng_miracled` | **+0.018 ±0.005** |
| win rate | −0.0012 ±0.0023, inside its bar |

Ruby Medallion and Longshot both have to be drawn, kept on the battlefield,
AND line up with a specific card's colour or type at the moment a miracle is
decided — rare enough in a 99-card deck that the aggregate win rate cannot
resolve it at this N, even though the mechanism counters that fire on every
relevant turn clearly can.

**A monkeypatched before/after comparison silently measured nothing, and
here is what that looks like.** The first cut of the harness patched the OLD
behaviour into the module in the parent process before creating a `Pool`.
Windows' `multiprocessing` has no fork — workers are spawned as fresh
interpreters that re-import `edhmc.lorehold` from scratch — so the patch
never reached them, and both legs silently ran the current code. The result
was an exact `+0.0000` on every single metric, not a small number: **when a
before/after diff comes back at literally zero on everything, the patch
did not apply — it is not evidence of "no effect."** Fixed by installing the
patch inside each worker's own `_init`.

**Checked for anywhere else this could apply first.** Grepped all six decks'
card lists for "costs {N} less" text: Karlov has one more (The Wind Crystal),
with a single call site in `karlov.reduce_cost` and no drift possible — no
miracle-equivalent mechanic exists there to duplicate the logic against.
Lorehold is the special case, because the decision/payment split its miracle
windows require is what created three consumers of one fact in the first
place.

**Zero of the regenerated ablation table's 64 rows moved by more than their
own old CI half-width, and zero already-significant rows flipped sign** —
including Ruby Medallion's own (win 0.0009 → 0.0007) and Longshot's own
(0.0205 → 0.0214), both comfortably inside their bars. Individual values did
shift a little; nothing shifted far enough to register. Leave-one-out
ablation measures a card's presence or absence, and both cards already
carried their existing discounts either way — what the fix changed is a
DECISION (which card to hold, whether a gate believes a miracle is
affordable), visible in the paired harness above (same seeds, only the fix
differs) well before it would register in a per-card table at this N.


---

## 2026-09-07 (later still): TWO COMMANDERS' OWN CARDS WERE NOT BEING PLAYED

Both decks' first tables, published earlier the same day, are **void**. Both
engines changed; `validate.py` is `+0.00` on all eighteen metrics across six
engines and `corr(A,B)` is unchanged at 0.9053.

The two started as separate queued items and turned out to be the same bug
twice: **a policy decision, written down as conservatism, that amounted to
asserting a card does nothing.** Neither was visible in an ablation table,
because in both cases the card's own row looked like an ordinary bad row.

### Shilgengar's ultimate fired ZERO times in 3,000 games — and it is worth 0.034

`KNOWN_ISSUES.md` §0r; `diag_shilgengar_ult.py` is the evidence.

The commander reads "sacrifice another creature: create a Blood token, or
Blood equal to its TOUGHNESS if it was an Angel", then "sacrifice six Blood:
return each creature card from your graveyard to the battlefield". The deck is
half Angels. `blood_made` averaged **0.10 a game**.

`aristocrats_step` would only ever sacrifice 1/1 Spirit tokens, and Spirit
tokens only exist once an Angel has already died — so the engine was starved
by construction. The docstring said this understated the ability. It did not
say it reduced it to zero, and nobody had measured which.

**THE FIX IS ARITHMETIC, NOT A PILOT'S JUDGEMENT, which is why it was safe to
automate.** The ultimate returns *the Angel you just sacrificed to pay for
it*, and `activations()` runs after combat, so the bodies fed to it have
already attacked. A nontoken sacrifice is a LOAN. So the line is taken only
when it completes the ultimate that same turn — and **real cards now sort
ahead of tokens as fodder, the exact reverse of the old policy**, because the
card comes back and the token does not.

| flip, 4,000 paired games, T20 | win rate |
|---|---|
| the fodder policy | +0.0267 ±0.0067 |
| **the mana reserve** — `main_phase` is greedy and `activations()` runs after it, so the {3} was never there | +0.0075 ±0.0048 |
| **both** | **+0.0343 ±0.0079** |

Deck win rate **0.208 → 0.242**; the ultimate now fires in **39.5% of games**.
The second row is worth reading twice: a fifth of the effect was not the
policy at all, it was that nothing in the engine ever held mana back for an
after-combat ability. That is a shape other engines may share.

**THE REGENERATED TABLE MOVES FOR REASONS YOU CAN READ OFF THE CARDS**, which
is the check that the fix is real rather than merely large: 10 of 64 rows
moved by more than their own old CI half-width, zero already-significant rows
flipped sign, and the movers are exactly the cards the mechanism touches.
**Righteous Valkyrie (+0.0086 → +0.0130, 2.0x its old bar) and Elesh Norn
(+0.0059 → +0.0083), because +2/+2 on an Angel is literally +2 Blood when you
sacrifice it.** Bishop of Wings (2.2x) and Requiem Angel, because they make
Spirit tokens off deaths that now happen. Blood Artist and Zulaport Cutthroat,
because their triggers now fire. Reya Dawnbringer went DOWN (+0.0074 →
+0.0045): she reanimates one creature a turn out of a graveyard the ultimate
now empties, and finality counters keep what it returned out of her pool.

**And the rows that did NOT move are a finding rather than an omission.** The
sac OUTLETS are still flat to negative — Viscera Seer −0.0005, Skullclamp
−0.0013, Vampiric Rites −0.0016, Cartel Aristocrat +0.0011. **The commander is
the only sacrifice outlet this deck needs**, so the redundant ones buy nothing.
That is now a statement about the cards, where the old table's version of it
was a statement about the policy — and it is the same conclusion read off a
table that can finally see the mechanism.

**FINALITY COUNTERS HAD TO BE MODELLED IN THE SAME CHANGE**, or the fix plays
a card the game does not print: the returned creatures come back "with a
finality counter", so the same Angel cannot be fed to a second ultimate. Two
versions of that check passed while proving nothing — the first because after
an ultimate the graveyard is empty so a second cast has nothing to return
either way, the second because it ran out of mana before it ran out of
finality. Both are written up in §0r, because "the check passed" was wrong
twice for reasons that had nothing to do with the mechanism.

### Azusa's land animation: implemented at last, and it is NOT the story

`KNOWN_ISSUES.md` §0s; `diag_azusa_animation.py` is the evidence.

Four effects, of which **one** was implemented as animation at all. Sylvan
Awakening was a turn-scoped flag whose lands attacked as fabricated 2/2s that
were never on the battlefield — so attacking with them tapped nothing and the
same lands still paid for the postcombat main phase. Rude Awakening was its
untap mode only: no animate mode, no entwine. Nissa, Worldwaker had no
abilities at all. And Nissa, Vastwood Seer never transformed, so her whole
back face was unreachable in a deck that hits seven lands on turn five.

| flip, 4,000 paired games, T20, cumulative | win rate |
|---|---|
| `land_animation` — a real continuous effect, and attacking taps it | +0.0003 ±0.0008 |
| `animated_lands_block` — Sylvan lasts until YOUR NEXT TURN, so they block | +0.0013 ±0.0011 |
| `rude_awakening_modes` — the animate mode and the entwine | −0.0008 ±0.0019 |
| **`planeswalker_abilities` — both Nissas** | **+0.0210 ±0.0068** |
| **all four** | **+0.0217 ±0.0071** |

**THE PILLAR IS REAL AND IT IS NEARLY A BLANK. THE TWO NISSAS ARE NOT.** All
three animation fixes together sit inside their own bars — and that is now a
RESULT rather than an absence, which is the entire point of doing the work.
The mechanism is legible: the animation is worth **9.24 marginal damage a
game** in a deck whose damage runs into the thousands, because Scute Swarm's
doubling dwarfs it. **This deck does not need more damage. The animation sells
it the one thing it already has most of.**

The Nissas sell it what it is short of, and this is the land-sequencing
finding arriving from a second direction: **+1.29 landfall triggers and +0.36
lands played a game.** The corrected table already said this deck is
CARD-limited rather than drop-limited; Nissa, Sage Animist's +1 is a card or a
free land every single turn, and that is why she scores where three land
animations do not.

**"Untested, not disproved" was the right thing to have written down.** It was
also worth 0.022 win rate to settle, and almost none of it came from the card
the note was about.

**WHAT THE REGENERATED TABLE DID, which is the check that the work was
targeted: 3 of 58 rows moved by more than their own old CI half-width, and
they are the three cards whose implementation changed.**

| card | old | new | vs its own old bar |
|---|---|---|---|
| Nissa, Vastwood Seer // Sage Animist | +0.0039 | **+0.0215** | 6.1x |
| Nissa, Worldwaker | −0.0001 (`FLIP`) | **+0.0061** (`win`) | 4.4x |
| Sylvan Awakening | +0.0021 | +0.0048 | 1.9x |

Zero sign flips among rows that were already significant, and Rude Awakening
(+0.0019 → +0.0046) did not move by more than its own bar. **Nissa, Vastwood
Seer is now a top-five card in the deck** — behind Scute Swarm (+0.0328),
Rampaging Baloths (+0.0309), Avenger of Zendikar (+0.0281) and Horn of Greed
(+0.0277) — where the previous table had her as an ordinary +0.0039. Both
Awakenings are now *significant* and *small*, which is the shape you want from
a mechanism that is real and does not matter much.

### Planeswalker loyalty exists now, and it is the third checked name set

`PLANESWALKERS` holds starting loyalty; `Permanent.counters` holds the current
value, so no field was added to a dataclass five other engines share.
`check_planeswalker_coverage()` raises at import if a Planeswalker in the deck
has no entry — the §0q rule applied in the same change, because a walker
missing from that table enters at zero loyalty and does nothing, silently,
which is the exact state both Nissas were in.

**Nissa, Worldwaker moved from `KNOWN_BLIND` to `SCRIPTED_AZUSA`** in the same
commit. Her old entry read "planeswalker activated abilities — nothing in this
project tracks loyalty". That stopped being true, and leaving it would have
printed an implemented card under MODEL-BLIND — §0q's first instance verbatim,
for the third time.

### One shared-code change, and the check that it moved nothing else

`opponents.combat_share` now counts blockers through `your_creatures(g)`,
which asks the engine `counts_as_creature` when it defines one. Animated lands
are blockers; the other five engines define no such hook and get the identical
expression they always had. **Deliberately NOT named `is_creature_now`**:
`karlov.is_creature_now(g, card)` is a module-level function with a different
signature, and a `getattr` hook sharing that name is a silent failure waiting
for whoever turns karlov's into a method.

**CHECKED, NOT ARGUED**, because this file records one occasion when the
argument was right about one change and wrong about another in the same
commit. `check_unchanged_decks.py` is that check, made repeatable: a git
worktree at the previous commit runs the same seeds through both versions of
all six decks and diffs every metric exactly.

    rendmaw, lorehold, karlov, tivit    BIT-IDENTICAL on all 8 metrics
    shilgengar, azusa                   moved -- their own engines changed

So only two of the six tables needed regenerating, and all six fingerprints
moved anyway because `opponents.py` is shared. That gap between "the
fingerprint moved" and "the numbers moved" is exactly what the tool is for.

---

## 2026-09-07: AZUSA WAS PLAYING ITS LANDS WRONG, and it was worth 0.074 win rate

Four separate defects in one place — `land_step` ran ONCE, before any spell
resolved, and chose lands with `max(options, key=mv)`. Every land has mana
value 0, so that key is constant, `max` returns the first option, and
`playable_lands` builds the hand first. Measured with `diag_azusa_lands.py`:

| | before | after |
|---|---|---|
| zone priority | hand-first ALWAYS | library → graveyard → hand |
| top-enabler resolved too late to matter | 32.5% | 10.4% |
| Lotus Cobra too late to see a drop | 51.1% | 35.0% |
| turns ending with a wasted drop | 12.8% (2.25/game) | 1.0% (0.17/game) |
| **land drops on the turn AZUSA resolves** | **1.08** | **3.10** |

**The commander's own case was the worst of them** and was not on anyone's
list: `land_drops_for_turn()` reads `commander_cast`, and land_step ran before
the commander was ever cast, so Azusa granted nothing on the turn she landed.

**Deck win rate 0.205 → 0.279 at T20** (0.038 → 0.074 at T10). That is a
bigger move than any single card in the table — the deck was losing more to
its own sequencing than to any card choice in it.

Four changes, in `edhmc/azusa.py`:

1. `choose_land()` replaces the mv sort. Library → graveyard → hand, and
   within a zone a fetch outranks a plain land (two landfall triggers, not
   one).
2. **The reroll line is modelled.** With top-of-library access live and the
   top card NOT a land, a FETCH IN THE GRAVEYARD outranks everything: cracking
   it searches and then SHUFFLES, re-rolling a dead top card into a fresh
   look, at no card cost because the fetch is already in the yard — plus two
   landfall triggers and a Titania trigger for one drop. It correctly declines
   when the top IS a land (take the free land instead). Fires ~1.15 times a
   game. Unit-tested on all four branches in `diag_azusa_lands.py`.
3. `main_phase(enablers_only=True)` runs before the drops and **again between
   them**, because a one-shot pre-land phase cannot cast a two-mana Lotus
   Cobra on turn two — the mana for it comes from the land drop itself. A
   second `land_step()` after combat mirrors `engine.py`'s two `play_land`
   calls.
4. `crack_fetch` shuffles, in rules order (search → battlefield → shuffle →
   landfall trigger).

**THE SHUFFLE NEARLY BROKE COMMON RANDOM NUMBERS, which would have been much
worse than the bug it fixes.** Across every engine in this project `self.rng`
is touched only for the opening shuffle and mulligans. A mid-game shuffle
drawing from it would give decks A and B different library orders the moment
they diverged and decorrelate every later draw — the exact failure
`opponents.py`'s design note is about. The seeds are therefore PRE-ROLLED from
a dedicated stream and indexed by shuffle count, so the Nth shuffle in both
branches applies the same index permutation, which is the property that makes
the opening shuffle CRN-safe. Verified: A/A control still exactly `+0.00`, and
on a real swap (Lotus Cobra vs a blank, n=4,000) CRN is still worth 6.5x on
damage, 9.8x on win rate and 24.7x on landfall triggers.

### And the corrected finding: this deck is LAND-SUPPLY limited, not drop limited

The reason Exploration is still worth nothing while Courser and Crucible are
worth a lot, traced rather than asserted:

    land drops GRANTED per turn   2.77
    land drops USED per turn      1.33   (48.1% utilisation)
    turns with an unused drop and NO land anywhere to play   57.9%

Azusa already grants more drops than the deck can feed. Put plainly: the deck
is allowed roughly three land drops a turn and draws **one card** a turn, so
the binding constraint is CARDS, not permission. A card that adds a FOURTH
drop does nothing on the 58% of turns where the third one is already going
begging — so Exploration (+0.0023, inside its bar) and Wayward Swordtooth
(+0.0030) are near-blanks.

Everything that scores well attacks the card constraint instead, and the
ranking falls straight out of that one idea:

- **more PLACES to find lands** — Courser +0.0177, Augur +0.0144, Oracle
  +0.0143, Excavator +0.0131, Crucible +0.0101. The graveyard and the top of
  the library are extra card sources that do not cost you a draw. This is why
  they roughly doubled the moment the sequencing let them be used.
- **turning drops back INTO cards** — Horn of Greed +0.0151 → **+0.0289**,
  now the #2 card in the deck. It draws a card per land played, which feeds
  the exact resource that ran out. Tireless Tracker (+0.0201) and Seer's
  Sundial (+0.0144) are the same effect at a slower rate.

A mono-green ramp deck with multiple drops a turn is card-limited almost by
construction, and this table is that fact measured.

**That is the deckbuilding statement to act on, and it is the opposite of the
obvious one for a deck whose commander reads "play two additional lands."**

---

## 2026-09-07: first ablation tables for shilgengar and azusa

> **BOTH TABLES IN THIS SECTION ARE VOID, superseded later the same day.**
> Shilgengar's engine never fired its commander's ability (KNOWN_ISSUES.md
> 0r) and Azusa's had one of its four land animations implemented and
> neither Nissa (0s). Both are regenerated. The section is kept because
> the REASONING in it is still how these tables should be read -- and
> because the paragraph below about the aristocrats package being starved
> by its own policy is the note that led to the fix.

Both at the common N=15,000 and horizons 10,20, so they are comparable
row-for-row with the other four. Baseline win rate at T20: **shilgengar
0.209, azusa 0.205** — below rendmaw (0.307), tivit (0.397) and karlov
(0.455), which is what "least tuned" looks like from the outside. Noise
floors ±0.0019 and ±0.0022.

**THE FIRST FULL-SIZE RUN FOUND A CRASH, NOT A FINDING.** `azusa.wave()`
(Genesis Wave) removed cards from the library one at a time while
`land_entered` could fire Seer's Sundial, which draws, which pops the library
out from under the loop — `ValueError: x not in list` after ~1.8M games had
already run for the other deck. The cards now all leave the library before
any ETB resolves, which is also what the card actually does. The same
interleaved shape existed in `shilgengar_ultimate` and was NOT reachable
(nothing between those removals touches the graveyard); it was hardened
anyway, and the claim that this was behaviour-neutral is backed by
regenerating the whole shilgengar table and diffing it **byte for byte**,
not by argument.

### shilgengar: the Angels carry it and the aristocrats package does not

| tier | cards |
|---|---|
| top, and a real gap below them | Archangel of Thune (**+0.0268**), Massacre Wurm (+0.0242), Lyra Dawnbringer (+0.0230) |
| next | Avacyn (+0.0101), Righteous Valkyrie (+0.0086), Requiem Angel (+0.0081) |
| tests NEGATIVE or flat | Vampiric Rites (−0.0019, significant), Skullclamp (−0.0011), Pitiless Plunderer (−0.0009), Viscera Seer (−0.0009), Blood Artist (−0.0008), Black Market Connections (**−0.0027**) |

The top three are 6x the noise floor clear of the fourth card, so that is a
meaningful SET (not an order). All three are lifegain/anthem Angels; none of
them sacrifices anything.

**DO NOT READ THE NEGATIVE ARISTOCRATS ROWS AS A CUT LIST.**
`aristocrats_step` only ever sacrifices worthless 1/1 Spirit tokens, never a
real card — a policy chosen deliberately and documented in
`edhmc/shilgengar.py` — and Spirit tokens only exist once an Angel has
already died. So the sac engine is starved by construction: `blood_made`
averages **0.13 a game** and **the commander's six-Blood mass-reanimation
ultimate fired ZERO times in 3,000 games.** The deck's namesake ability is
currently untested rather than tested-and-found-wanting. That is the first
thing to fix about this engine, and until it is fixed these rows are a fact
about the policy at least as much as about the cards.

> **FIXED later the same day, and this paragraph is why.** The policy now
> feeds real Angels to the ability whenever that completes the ultimate in the
> same turn, which is a loan rather than a cost because the ultimate returns
> the Angel it was paid with. Worth **+0.0343 win rate**, and the rows above
> are void -- see the section at the top of this file and KNOWN_ISSUES.md 0r.
> Note what the regenerated table did NOT do: the sac OUTLETS (Viscera Seer,
> Vampiric Rites, Cartel Aristocrat, Skullclamp) are still flat to negative,
> because the commander is the only outlet the deck needs. What moved is the
> death-trigger PAYOFFS and, best of all, the TOUGHNESS BUFFS -- Righteous
> Valkyrie 2.0x its own old error bar and Elesh Norn 1.1x, because +2/+2 on an
> Angel is literally +2 Blood when you sacrifice it. A ranking that moves for
> a reason you can read off the card is the check that the fix is real.

**Two proxy/objective disagreements, both the right way round.** Damn is
−1.17 damage at T10 and **+0.0061 win rate**; Wrath of God −1.14 and
+0.0043. A wrath costs you damage and wins you games. Smothering Tithe is
−0.59 damage and +0.0041 win. Follow win rate.

**A knob result, said out loud.** Revel in Riches sits in the MODEL-BLIND
table and is the only card there that is not near zero (+0.0063 ±0.0019).
Traced: its Treasure clause is unmodelled, but its ten-Treasure ALTERNATE WIN
is live and fires off Treasures other cards made. It resolves in 12.1% of
games and wins via that route in 0.83% of all games — and in **33 of 33** of
those wins Smothering Tithe was on the battlefield. `shilgengar.upkeep` hands
Tithe one Treasure per living opponent per turn on the assumption opponents
never pay the {2}. Make them pay sometimes and this line gets much worse.

### azusa: read the win-rate column and nothing else

**THE DAMAGE COLUMNS ARE UNUSABLE.** Scute Swarm's landfall doubling gives
this deck a far heavier damage tail than any other — CIs of ±278 against
point estimates of the same order — and **13 rows carry a FLIP signal that is
pure damage noise**, not a horizon effect. Same situation as tivit, one step
worse. Win rate is an order of magnitude tighter.

| tier | cards |
|---|---|
| the deck | Scute Swarm (**+0.0261**), Avenger of Zendikar (+0.0249), Rampaging Baloths (+0.0233) |
| next | Horn of Greed (+0.0151), Genesis Wave (+0.0137), Tireless Tracker (+0.0131), Ulamog (+0.0129), Courser of Kruphix (+0.0117) |
| unmeasured (`--`) | Perilous Forays (+0.0010), Yavimaya Elder (−0.0003) |

~~**THE PAYOFFS BEAT THE ENABLERS, AND IT IS NOT CLOSE.**~~
> **HALF RETRACTED 2026-09-07, later the same day — see the land-sequencing
> section below.** The claim was measured on an engine that spent its land
> drops before any spell resolved, which denied every enabler its first turn
> of value. On the corrected engine the ZONE enablers roughly double
> (Augur of Autumn +0.0065 → **+0.0144**, Oracle of Mul Daya +0.0077 →
> **+0.0143**, Ramunap Excavator +0.0074 → **+0.0131**, Crucible of Worlds
> +0.0060 → **+0.0101**, Courser of Kruphix +0.0117 → **+0.0177**) and the
> claim does not survive for them. It DOES survive, and gets sharper, for the
> drop-COUNT enablers: Exploration +0.0021 → **+0.0023 and still inside its
> own bar**, Wayward Swordtooth +0.0056 → **+0.0030**. The original framing
> was too coarse because it lumped the two kinds together.

**Damage and win rate point in opposite directions at the top**, and the
mechanism is game length: Avenger of Zendikar is −6.1 damage at T20 and
+0.0249 win; Rampaging Baloths −20.1 and +0.0233; Ulamog −194 and +0.0129.
They end games sooner, so less total damage accumulates. Follow win rate.

**"Land animation" is barely modelled and its rows say so.** Sylvan Awakening
+0.0017 and Rude Awakening +0.0019, both inside or at their bars. Only one of
the deck's three animation effects is implemented as animation at all
(`sylvan_awakening`); Rude Awakening is modelled as its untap mode and Nissa,
Worldwaker's abilities are not modelled. This pillar of the deck is untested,
not disproved.

**The blind table is the check that the classification is right** — every row
in it is at or near zero except the two noted above.

---

## State as of 2026-09-08 — SUPERSEDED, see `CLAUDE.md`

> **[2026-09-09] RETITLED.** This section was headed "Current state — READ THIS
> BEFORE TRUSTING ANY DOC" while it lived in `CLAUDE.md`. It is no longer the
> current state and a heading that says otherwise inside an archive is the
> exact failure this section's own closing paragraph describes. The live
> current state is in `CLAUDE.md`; everything below is kept as provenance for
> the numbers quoted around it.
>
> It also predates the combat split (`KNOWN_ISSUES.md` §0v, 2026-09-08), which
> regenerated all six ablation tables — so every table this section calls
> current has since been replaced.

Verified 2026-09-03 after the oracle-text audit; deck table updated 2026-09-07.

| deck | module | spreadsheet | status |
|---|---|---|---|
| Rendmaw, Creaking Nest | `rendmaw_v12.py` | v12 `.xlsx` | agrees |
| Lorehold, the Historian | `lorehold_v16.py` | v16 `.xlsx` | agrees |
| Karlov of the Ghost Council | `karlov_v2.py` | v2 `.xlsx` | agrees |
| Tivit, Seller of Secrets | `tivit_v1.py` | v1 `.xlsx` | agrees |
| Shilgengar, Sire of Famine | `shilgengar_v1.py` | v1 `.xlsx` | agrees |
| Azusa, Lost but Seeking | `azusa_v1.py` | none — submitted as a table | n/a |

**2026-09-07 (later the same day): a sixth deck — Azusa, Lost but Seeking.**
Submitted as a plain decklist table, not a spreadsheet — there is no `.xlsx`
for this one, so the module (`edhmc/decks/azusa_v1.py`) IS the system of
record until one exists. **The submitted list was 99 cards, not 100** —
counted programmatically before writing anything — and a 21st Forest was
added to reach the legal count; flagged in the module docstring in case a
different 100th card was intended. Two submitted mana values were wrong
against Scryfall and are corrected in the module: Avenger of Zendikar is
{5}{G}{G} (MV 7, not 8) and Lotus Cobra is {1}{G} (MV 2, not 3).

Landfall, extra land drops, and a fetch-land-as-two-landfall-triggers
mechanic are all real engine code in `edhmc/azusa.py` — the last one is worth
reading if you extend this deck, since it is the same class of "a doubled
trigger, modelled as one" correction this project's Blood Artist and Elas
il-Kor fixes were about. Scute Swarm's landfall-doubling is implemented
directly and can produce very large damage outliers (mean damage over a batch
run was in the hundreds, occasionally much higher) — checked against
`validate.py` and it is not a harness leak, just a genuinely swingy card in a
deck built to go wide fast. Two Planeswalkers (Nissa, Worldwaker and the
transformed back of Nissa, Vastwood Seer) have no activated abilities
modelled — nothing else in this project tracks loyalty, and this seemed like
the wrong card to be the first. `validate.py` is clean and `audit_cards.py` is
0 ERR across all six decks. Least tuned of the six; nothing is staged.

**2026-09-07: a fifth deck — Shilgengar, Sire of Famine.** Its spreadsheet had
been in the repo since 2026-09-03 with no engine; `edhmc/shilgengar.py` and
`edhmc/decks/shilgengar_v1.py` are new. This is the LEAST TUNED of the five —
a first-pass spreadsheet, not a list that has been through ablation — and its
own docstrings say so at every judgement call (a token-only sacrifice policy,
Elesh Norn's team-buff-only implementation, Avacyn's protection against
opponent-sourced `destroy()` only, Massacre Wurm's ETB approximated against an
opponent board that is a float, not real permanents). Six of the spreadsheet's
mana values were wrong against Scryfall and are corrected in the module, not
the sheet (see `shilgengar_v1.py`'s docstring). `validate.py` is clean
(`blood_made`, `creatures_sacrificed`, `damage`, all `+0.00`) and
`audit_cards.py` is 0 ERR across all five decks. Nothing is staged against it
yet — `python ablation.py shilgengar <n> <turns>` is the next step, same as it
was for the other four when they were new.

**Also fixed while adding it:** `validate.py` never had a Karlov A/A control
block — four decks existed but only three engines were checked. It now checks
all five.

**And a structural fix, in `edhmc/decks/__init__.py`:** `audit_cards.py` and
`tag_flying.py` used to name the four decks by hand in a dict, which is the
exact shape of bug this project has been bitten by twice before (a hand-
written registry that a later deck or card change forgets to update — see
"Hazard: adding a card to a deck is TWO edits" below). `discover_current_decks()`
walks `edhmc/decks/` for any `<name>_v<N>.py` exposing `build()` and resolves
each name to its highest version, so a sixth deck gets Scryfall-checked and
evasion-tagged automatically, with nothing to remember. `ablation.py`'s
`SCRIPTED_*`/`KNOWN_BLIND` sets, `validate.py`'s A/A legs, `pending.py`'s
per-deck candidate catalog, and `cache_manifest.py`'s fingerprints are
deliberately NOT auto-discovered — each needs a real decision a script cannot
make for itself.

**UPDATED 2026-09-06.** Karlov's three changes are COMMITTED on all three legs
— hence `karlov_v2.py` and the v2 `.xlsx`, reconciled card for card. **THREE
changes remain staged** and are held back deliberately for review, with the
ledger as their only leg: Rendmaw's Idol of Oblivion -> Cauldron of Essence,
Lorehold's Scroll Rack -> Sunbird's Invocation, and Lorehold's Penance ->
Caldera Pyremaw. `python -m edhmc.pending` is the check and is the only
trustworthy statement of what is staged; `DECK_CHANGES.md` is the summary.

(This paragraph said TWO until 2026-09-06 and named only the first pair. The
Caldera staging happened on 2026-09-05 and is written up 500 lines further down
this same file, which is exactly how a doc goes stale: the summary at the top and
the session note at the bottom were edited by different sessions.)

Note for the Karlov v2 spreadsheet: the Dashboard's 34 formulas were hard-bounded
to `Decklist!...87`, and the list is now 88 rows. openpyxl does not rewrite
formula ranges on insert, so every metric would have silently dropped the last
card. All 31 affected formulas were rebounded to row 150 — generous on purpose,
so the next deck change cannot break them either.

`validate.py` is clean: `+0.00` on **all nine across three engines**,
`corr(A,B) = 0.9053` as of 2026-09-06 (0.9069 before the Erebos work, 0.9045
before the low-stakes fixes, 0.8927 before evasion, 0.8929 on the retired pod
v1). CRN is worth ~10x the games.

**The correlation used to be 0.9109.** It fell because Rendmaw's commander now
hands every opponent a goaded Bird, which changes when games end. Nothing is
leaking — the A/A control is still exactly `+0.00`. CRN is worth ~9x rather
than ~11x.

### Every card has been checked against oracle text

2026-09-03: all 207 nonland cards across the three decks were checked against
Scryfall. **52 had a wrong cost, power, toughness, type line or name**, and
~22 had behaviour that did not match their text. See `ORACLE_AUDIT_KARLOV.md`,
`ORACLE_AUDIT_RENDMAW.md` and `ORACLE_AUDIT_LOREHOLD.md` — each carries a
STATUS block listing what is fixed and what is still open.

> **RE-VERIFIED 2026-09-05 with `audit_cards.py`: 0 data errors across 289 card
> slots / 269 distinct names.** None of the 52 have regressed. What remains is
> behavioural — see the 2026-09-05 re-verification section below.

Consequences worth carrying forward:

- **Every ablation table predating this is void.** `ablation_karlov.txt`,
  `ablation_rendmaw.txt` and `ablation_lorehold.txt` were all measured against
  the uncorrected engine. Regenerate before reading any of them.
  **All four tables are CURRENT as of 2026-09-06** — lorehold and tivit at the
  deck changes, rendmaw and karlov at the engine fixes, and all four re-measured
  at **N=15,000**. The tivit table is no longer the odd one out at N=2000; every
  deck is now on the same scale and comparable row-for-row. Each table prints
  its own N and its own measured noise floor in the header, so this paragraph is
  no longer the only place that fact lives.
  **REGENERATED A SECOND TIME on 2026-09-06** after the ablation BLANK was
  fixed (`KNOWN_ISSUES.md` §0j) and Ephemerate was fixed (§0k). Every table
  produced before that — including the N=15,000 set from earlier the same day —
  is void. The new caches carry a `_medblank` suffix; the old files keep their
  unsuffixed names and are kept as provenance only. **Do not resume onto one.**
  **REGENERATED A THIRD TIME on 2026-09-06, but only TWO of the four**, for the
  Erebos correction (§0l, rendmaw) and the extra-turn correction (§0m, tivit).
  `engine.py` is in every deck's fingerprint, so **all four fingerprints moved
  and only two decks' numbers did** — and that was CHECKED rather than argued: a
  git worktree at the previous commit ran all four baselines on the same seeds
  at both horizons, and karlov and lorehold came back **bit-identical** on every
  metric while rendmaw and tivit did not. Their caches and tables stand. This is
  the third time "this engine is independent" has had to be settled per change
  rather than once, and the first time the answer was yes for half the decks and
  no for the other half in the same commit.
- **Correcting Karlov made the deck look worse, not better** (win rate
  −0.0163 ±0.0139). The old numbers were inflated by phantom lifegain triggers
  and by Well of Lost Dreams / Dawn of Hope drawing cards for free.
- **A docstring claiming a correction is not evidence of one.** Both
  `lorehold_v15.py` ("where a card's real cost differs, the real cost is
  used") and `karlov_v1.py` ("the spreadsheet already corrected Damn and
  Fracture to MV 3") documented their own errors as deliberate. The first was
  wrong for 20 cards; the second was wrong in both directions.

### All five changes are committed

`pending.py` previously described the five 2026-09-02 changes as staged and
"not yet written to the .xlsx files", which was backwards — the spreadsheets
carried them and the modules did not. All five are now applied to the modules
(hence `lorehold_v16.py` and `rendmaw_v12.py`) and recorded in `COMMITTED`.

Rendmaw's Skullclamp → March of the World Ooze was **re-measured on the
corrected engine before committing**, since its original evidence predated the
oracle audit and both cards were touched by it: 6,000 paired games, damage
+3.02 [+2.57, +3.48] and win rate +0.0077 [+0.0053, +0.0101] at 10 turns;
+2.79 and +0.0018 (inside its bar) at 20. Sign and rank survive the horizon
range and the numbers land within a rounding error of the original. The
`Change` dataclass now has a `reverified` field carrying that.

Note that `validate.py`'s "real comparison" now runs in the other direction —
March is in the deck, so it swaps out to the cut `SKULLCLAMP` constant kept in
`rendmaw_v12.py`. The A/A control moved to March for the same reason.

Lost work from the 2026-09-03 session that still does not exist in any commit:

- `engine.choose_mode` and per-card `prefer`/`fallback` alternative-cost modes
- flying/reach evasion in `opponents.damage_through` — **still missing**, and
  now load-bearing, since Rendmaw's Birds and Karlov's fliers both depend on it
- Storm Herd's X reading the real life total (still `script="storm_herd"`)
- `COMMITTED_CHANGES.md`, `audit_cards.py`, `tag_flying.py`
- `KNOWN_ISSUES.md` items 1a and 1c

(The "five inert Karlov card implementations" are done: Radiant Fountain,
Pristine Talisman, Aetherflux Reservoir, Serra Ascendant and Cosmos Elixir all
work now.)

`README.md` is trustworthy on methodology, stale on file lists and every number
it quotes. `PROJECT_CONTEXT.md` and `PENDING_CHANGES.md` predate all of this
and still name `lorehold_v15.py`.

### Ablation tables are regenerated at two horizons

As of 2026-09-03 all three tables are run at `10,20` rather than a single
`20`. The pod's clock ends games around turn 12, so those two bracket it, and
a second horizon is what turns on the `FLIP` signal — a card whose sign does
not survive the range is flagged rather than ranked. Regenerate with:

```bash
./regen_tables.sh                      # all four decks at N=15000, ~23 min
python ablation.py karlov   15000 10,20   # or one deck at a time
python ablation.py rendmaw  15000 10,20
python ablation.py lorehold 15000 10,20
python ablation.py tivit    15000 10,20
```

**N is part of the identity of a table.** It is in the cache key, it is printed
in the table's header, and `regen_tables.sh` — which overwrites
`ablation_<deck>.txt` — carries it in one variable. Changing it in one place
and not the others silently replaces the committed tables with less precise
ones. See the N=15,000 section below for why that number.

`ABLATE_BUDGET` (seconds, default 240) caps one invocation; the run caches
after every card and resumes, so a small budget just means more invocations.
`ABLATE_PROCS` sets the worker count and defaults to every core.

### 2026-09-04: nineteen candidates measured, and a harness bug

`CANDIDATES_2026-09-04.md` has the full write-up (two batches, nineteen cards).
Three things from it matter beyond the cards themselves:

- **`candidates.py`'s blank did not match `ablation.py`'s blank**, so the two
  tables were not on the same scale — which is the only thing that makes
  "compare the candidate to your weakest card" a valid decision rule.
  `ablation.py` blanks to a single type line; `candidates.py` copied the whole
  one, which for Rendmaw cancels the commander trigger. Fixed. Any candidate
  number produced before 2026-09-04 is on the wrong scale for Rendmaw.
- **`Card.indestructible` now exists** and is priced by `cfg["destroy_share"]`
  (default 0.60, the assumed share of pod interaction that is literally
  "destroy"). It is the first thing in the model that distinguishes kinds of
  removal. No card in any committed list has it, so it is inert; it exists
  because Heliod cannot be evaluated without it.
- Six candidates needed new engine behaviour and the mechanism counters to
  trace it (`sunbird_casts`, `escape_casts`, `heliod_counters`,
  `cauldron_reanimations`, `tenacity_returns`, …). `validate.py` is still
  `+0.00` on all six with `corr = 0.8929`, so the three ablation tables above
  are still valid despite the engine edits.

**Five swaps are STAGED** in `pending.py` (module leg only — the `.xlsx` files
do NOT yet carry them, so `CHANGES` is no longer empty and the three legs no
longer agree):

| deck | out | in | win T10 | win T20 |
|---|---|---|---|---|
| karlov | Swamp | Starscape Cleric | +0.0353 | +0.0480 |
| karlov | Whispersilk Cloak | Enduring Tenacity | (measured as the 2-for-2 above) | |
| rendmaw | Ornithopter of Paradise | Cauldron of Essence | +0.0025 | +0.0158 |
| karlov | Lightning Greaves | Exemplar of Light | +0.0397 | +0.0617 |
| lorehold | Scroll Rack | Sunbird's Invocation | +0.0077 | +0.0215 |

The three Karlov rows were measured together as a 3-for-3. Each was screened against a blank and then re-measured as the REAL swap with
`run_swaps_0904.py`. The other eight candidates were rejected.

**`build_pending()` now returns different lists than `module.build()`.** Any
new ablation run picks the staged changes up; delete the caches first.

### The commander bug is now measured and gated

`opponents.resolve_own_wipe` removed your commander without returning it to the
command zone, so `commander_cast` stayed `True` and it was never recast — every
self-wipe in every deck is over-penalised by roughly 1 damage, and for Karlov's
Damn by most of its win-rate penalty. Now gated behind
`cfg["own_wipe_commander_returns"]`, **defaulting to the old wrong behaviour**
so the three ablation tables stay valid. Flipping the default is one line and
invalidates all three. Numbers in `CANDIDATES_2026-09-04.md`.

### 2026-09-04: LIFE DOES NOT DECIDE GAMES — read this before valuing any lifegain

> **[2026-09-09] REVERSED LATER THE SAME DAY, and the heading is kept as
> written.** Pod v3 (two sections down) made your life total load-bearing:
> the life-share of losses went from 0.00 in all three decks to 0.32 / 0.43 /
> 0.20, and `KNOWN_ISSUES.md` §6b records the reversal. The consequences
> listed below — lifelink buys nothing, Invincible Hymn is a blank — are
> **false under the current default pod**. The section stays because the
> measurement that produced it was correct and the `loss_route` metric it
> added is still how the question is answered.

A `loss_route` metric was added to `opponents.py`. Measured over 2,000-2,500
games per cell:

| deck | loss rate T10 / T20 | ground down on life | opponent's clock |
|---|---|---|---|
| rendmaw | 0.260 / 0.703 | 0.00 | **1.00** |
| lorehold | 0.196 / 0.782 | 0.00 | **1.00** |
| karlov | 0.228 / 0.602 | 0.00 | **1.00** |

**Every loss in all three decks at both horizons is an opponent's clock**, which
is threat-weighted and never reads your life total. This is BY DESIGN and not a
close race: disable the clocks and incidental damage kills you in 0.4%
(rendmaw) / 0.6% (lorehold) / 0.0% (karlov) of games by turn 20, and 2.9% by
turn 30. The opponents' board is a float capped at 7 chipping for
`creatures * 0.45 * your_share`; it was never calibrated to kill anyone, and the
clock is the abstraction standing in for "an opponent actually wins".

(Do not cite mean final life as evidence here — `resolve_clocks` sets
`your_life = 0` when it kills you, so the mean is an artifact of the clock, not
of the grind. An earlier version of this note made that mistake.)

Consequences:

- **Lifelink and lifegain buy nothing defensively.** They are worth something
  only where a card *reads* the life: Karlov's triggers, Serra Ascendant's 30,
  Felidar Sovereign's 40, Aetherflux's 50.
- **Any card whose job is a bigger life total is MODEL-BLIND.** Invincible Hymn
  measured as an exact blank for this reason.
- **Any card whose drawback is losing life gets that drawback for free.** Dark
  Confidant's number is a ceiling, and knowingly so.
- A `Card.lifelink` comment in `engine.py` claimed the opposite before this was
  measured. It has been corrected.

### POD_V2 - opt-in pod where life is load-bearing (2026-09-04)

`edhmc.experiment.POD_V2` = `{"combat_targeting": "open",
"incidental_rate": 1.0, "clock_shift": 2}`. Use as
`dict(DEFAULT_CFG, **POD_V2)`. **Defaulted OFF** - `validate.py` still prints
`+0.00` / `corr 0.8929`, and every existing number reproduces untouched.

Two changes, both in `opponents.py`:

1. **`combat_share()` replaces `your_share()` for COMBAT only.** The old code
   was backwards: combat damage was threat-weighted, so developing a board made
   you take *more* attacks. Creatures swing at whoever cannot block. Removal
   stays threat-weighted, which was always right.
2. **`clock_shift` delays the deus ex machina**, paying back the lethality that
   combat now supplies. Raising `incidental_rate` alone stacks a second kill
   mechanism instead of moving kills between them, and craters every win rate.

Fitted with `fit_pod.py` over a 25-point grid. Its mechanical best is (1.2, 4);
**that was NOT taken** because its target - a 0.65 life-share of losses - is a
number I invented. No survey data on EDH elimination causes exists that I could
find. Game length IS anchored: Command Zone, 100+ games, mean turn 10.29, 70%
between 8 and 12. Both v1 and v2 run ~12-13, a pre-existing gap.

Effect: life-share of losses goes 0.00/0.00/0.00 to 0.31/0.51/0.21
(rendmaw/lorehold/karlov) at near-identical win rates. **It now varies by
deck**, which is the point - Lorehold has 11 creatures and gets attacked.

All five staged swaps were re-measured under it and all five hold; see the
`reverified` fields. One downgrade: Rendmaw's Cauldron swap is now inside its
error bar at 10 turns and stands on the 20-turn result alone.

Payoff: **Invincible Hymn went from an exact blank (-0.0007 win) to +0.0097
+-0.0041.** Cards whose job is a life total are evaluable for the first time.

### POD v3 is the DEFAULT as of 2026-09-04 - every earlier table is void

`DEFAULT_CFG` now carries `combat_targeting="open"`, `incidental_rate=1.0`,
`clock_shift=2`, `archetypes=True`. `experiment.POD_V1` restores the old pod
exactly if you need to reproduce an earlier number.

`validate.py` is still `+0.00` on all six; `corr(A,B)` 0.8929 -> 0.8927, CRN
still worth ~9x. **All three ablation tables were regenerated against this pod
and every table dated before 2026-09-04 is void.**

Three changes, all in `opponents.py`:

1. **`combat_share()` replaces `your_share()` for COMBAT only.** The old code
   was backwards - combat damage was threat-weighted, so developing a board
   made you take *more* attacks. Creatures swing at whoever cannot block.
   Removal stays threat-weighted, which was always right.
2. **`clock_shift`** delays the deus ex machina, paying back the lethality that
   combat now supplies. Raising `incidental_rate` alone stacks a second kill
   mechanism instead of moving kills between them, and craters every win rate.
3. **`ARCHETYPES`** - aggro / midrange / control / combo, one per opponent.
   **Every multiplier is normalised to a weighted mean of exactly 1**, so the
   AVERAGE pod is unchanged by construction and archetypes add variance, not
   difficulty. That is the property that made this adoptable without a second
   recalibration. The raw numbers are judgement (no data on the EDH archetype
   mix was found); `cfg["archetype_weights"]` is the knob.

Effect: life-share of losses goes 0.00/0.00/0.00 to 0.32/0.43/0.20 at
near-identical win rates, and it is now CONDITIONAL - Karlov facing no aggro
decks has a 0.06 life-share, facing three it is 0.79.

**What this changed, and why it was worth doing:** the correct Rendmaw cut. The
Cauldron of Essence swap was staged against Ornithopter of Paradise and decayed
across pod versions (+0.0025 -> +0.0018 -> -0.0015 at ten turns) because
Ornithopter is a 0/2 BODY and Cauldron is not a creature - and blockers now
matter. Controlled test at 20 turns, same card in: cutting noncreature Idol of
Oblivion +0.0135, cutting the 0/2 Ornithopter +0.0088, cutting the 1/2 Dockside
Chef +0.0048. Monotonic. The staging was changed to cut Idol.

### Hazard: adding a card to a deck is TWO edits, not one

`ablation.py`'s `SCRIPTED_RENDMAW` / `SCRIPTED_LOREHOLD` / `SCRIPTED_KARLOV`
are hand-maintained NAME SETS, and membership is a claim that the engine
implements the card's text. They are what splits the output into
MODEL-EVALUATED and MODEL-BLIND. Nothing checks them against the engine.

2026-09-04: all five newly added cards (Starscape Cleric, Enduring Tenacity,
Exemplar of Light, Cauldron of Essence, Sunbird's Invocation) were implemented
in full and then printed under MODEL-BLIND, because the sets were never
updated. The numbers were right; the LABEL was wrong, and the label is the
part that tells you whether a low score means anything. Fixed — but only the
grouping was affected, so re-printing from the cache was enough and no games
were re-simulated.

**So: when you add a card to a deck, update the SCRIPTED set in the same
change.** The reverse also applies — Lightning Greaves and Whispersilk Cloak
were left in `SCRIPTED_KARLOV` after v2 cut them; harmless, but stale.

### The general form: A HAND-MAINTAINED NAME SET IS A CLAIM, AND CLAIMS ROT

This has now bitten three times, in three different files, with the same
shape every time — a list of card names written by hand, and a deck that
moved past it:

| set | what went wrong | when |
|---|---|---|
| `ablation.SCRIPTED_*` | five fully-implemented cards printed as MODEL-BLIND | 2026-09-04 |
| `tag_flying.py`'s deck list | two fliers measured as GROUND creatures | 2026-09-05 |
| `azusa.LAND_ENABLERS` | a landfall card would be deployed AFTER the land drops and score low for no stated reason | caught 2026-09-07 before it bit |

**The fix is not vigilance, it is derivation.** Where the engine itself
already names the cards, derive the set from the engine and check it:

- `ablation.check_scripted_coverage()` raises if a nonland card is in neither
  `SCRIPTED_*` nor `KNOWN_BLIND`.
- `edhmc/decks/__init__.py`'s `discover_current_decks()` removed the
  hand-written deck list from `audit_cards.py` and `tag_flying.py` entirely.
- `azusa.check_land_enabler_coverage()` (2026-09-07) scans the source of
  `land_entered`, `land_drops_for_turn`, `playable_lands` and `land_died` for
  `self.has("...")` / `self.count("...")` and raises at IMPORT if any name it
  finds is missing from `LAND_ENABLERS`. Those four methods ARE the
  definition of "land-relevant", so the set cannot drift from them. It
  currently derives 16 names with no unmatched leftovers, and it was verified
  to actually fail when a name is removed — a check that cannot fail is
  worse than no check, because it reads like assurance.

**When you add a hand-maintained name set, add the check in the same change,
and prove the check fails.** See `KNOWN_ISSUES.md` 0q.

### Evasion and three correctness fixes (2026-09-05)

`validate.py`: `+0.00` on all six, `corr(A,B)` improved 0.8927 -> 0.9045.
**All three ablation tables regenerated again; anything earlier is void.**

1. **FLYING is modelled** (queued item 1, now closed). `damage_through` splits
   attackers into fliers and ground; `flier_block_share` (0.30) is the fraction
   of an abstract board that can catch a flier, and Rendmaw's goaded Birds
   count in full because they demonstrably fly. `goad_block_share` no longer
   has to stand in for evasion.
   **The tags are GENERATED** — `tag_flying.py` reads Scryfall's `keywords`
   array and writes `edhmc/decks/_evasion.py`; the deck `C()` helpers set
   `flying=name in FLYING`, so a card cannot be added untagged. Do NOT match on
   oracle text: reach's reminder text contains the word "flying", and so does
   token-making text. That mistake tagged Longshot, Arasta, The Dawning Archaic
   and Rendmaw itself as fliers. Conditional fliers (Serra Ascendant, Voice of
   the Blessed, Dragon's Rage Channeler) are in `opponents.flying_of()`.
2. **Blood Artist was paid 3x its real drain.** It is "TARGET PLAYER loses 1",
   not "each opponent" — 1 damage and +1 life. The Meathook Massacre gains you
   NO life off your own creatures (that clause is for opponents' creatures).
   Cauldron of Essence was already right.
3. **The own-wipe commander bug is fixed and now default-on.** It was worse
   than first measured: `commander_cast` stayed True, so Lorehold's MIRACLE
   ENGINE kept running with the commander off the battlefield. Baseline
   `mv_cheated` fell 31.0 -> 22.6. `own_wipe_commander_returns=False` restores
   the old behaviour.
4. **`ablation.py` asserts its own classification.** `check_scripted_coverage()`
   raises if a nonland card is in neither `SCRIPTED_*` nor the new explicit
   `KNOWN_BLIND`, and warns on names a cut left behind. This is the guard
   against the labelling bug found earlier the same day.

Evasion reranks rather than uniformly buffing: Starscape Cleric +0.0108 ->
+0.0167 win (joint-best in Karlov), Rendmaw's Bitterblossom to +0.0205 because
its Faeries fly.

### The Library of Leng loop was broken, and two other cards were eating it

Found 2026-09-05 from a question about the deck's actual play pattern. Both
bugs were in `opponent_upkeep_windows`:

1. `set_top()` was called unconditionally right after Library of Leng put a
   card on top, appending ANOTHER card over it — 26% of placements buried. It
   now only fires when Leng placed nothing.
2. `discard_triggers()` resolved BEFORE the miracle window, and Monument to
   Endurance's "draw" mode pops the top of the library — exactly where Leng had
   just put the card. With Monument out, 78% of placements were buried and Leng
   miracles fell 1.98 -> 0.57 a game. Both triggers are yours, so you order
   them: Lorehold's draw resolves first, then Monument's. `discard_triggers()`
   now runs after the miracle window.

Result: burial 26% -> 0%, drawn 73% -> 98%, miracled 31% -> 43% at an average
7.35 MV cheated. Deck mv_cheated 22.6 -> 28.7. Monument to Endurance itself rose
to +2.14 damage / +0.0197 win — it had been competing with what it supports.

**PENANCE AND HIDDEN RETREAT DO NOT HAVE THE BURIAL BUG — they have a worse
one.** 99% of what `set_top` places is drawn, but only 26% can be paid for, so
three quarters of the time the draw step is spent re-drawing a card already in
hand. Penance is the worst card in the deck (-2.95 / -0.0100); adding Hidden
Retreat made the deck worse (win 0.203 -> 0.190). Raising `miracle_reserve`
above 2 makes it worse still — the default is right.

**THE STANDING FINDING: the top-setter package raises mv_cheated AND LOSES
GAMES.** Ablating Library of Leng + Penance + Sensei's Divining Top together is
win rate -0.0190 [-0.0276, -0.0104] with mv_cheated +1.43 [+0.76, +2.10]. This
deck's primary metric and its objective point in opposite directions for these
cards. Follow win rate. Library of Leng itself is the least guilty (mv_cheated
+1.56, win inside its bar) and is not proposed for a cut.

### Top-setter POLICY, not card text, was the problem (2026-09-05, later)

Three more bugs, all in the DECISION to put a card on top rather than in any
card's text. The pilot's objection was the right one: it should be rare to
place a card you cannot miracle, and when you cannot, the correct play is to
not do it and draw normally.

3. **`set_top` gated on the wrong mana pool.** It read the untapped BOARD, but
   the off-turn miracle pays from `float_mana`, which earlier windows have
   already spent. The board reading never drops, so windows 2 and 3 placed
   cards against mana that was gone. `set_top(g, pool=...)` now takes the pool
   that actually pays; `miracle_need(g)` is shared by decision and payment.
4. **Library of Leng had NO affordability gate.** It always redirected the best
   target to the top. The rummage discards either way, so: affordable -> bin
   the best, draw it back, miracle it; NOT affordable -> bin the WORST and draw
   fresh. Redirecting when you cannot pay gets the worst of both.
5. **The value gate skipped free setters.** `set_top_gate` applied only `if
   cost > 0`, and Penance / Hidden Retreat cost a CARD not mana. On your own
   turn nothing forces a discard, so an ungated placement spends the draw step
   re-drawing a card already in hand to cheat as little as one mana.

Library of Leng: miracled 43% -> **80%**, placements 5.34 -> 3.30 (it declines
the bad ones), deck mv_cheated 28.7 -> **31.1**, win 0.205 -> **0.219**.

6. **Galvanoth never saw what the top-setters set up.** It and Radiant
   Scrollwielder read `library[-1]` BEFORE `set_top` ran. The setters are all
   instant-speed, so they now resolve in the opponent's end step, before the
   upkeep triggers — and `set_top` knows Galvanoth casts FREE, so it needs 0
   mana rather than {2} and counts the card's FULL mana value.
   **This did not rescue Galvanoth**: it is cast in only 15.6% of games, on
   turn 9.8, for 0.51 free casts per game it resolves (0.08 overall). Wrong
   ordering AND too slow; only one was fixable.

STANDING RECOMMENDATION: cut Penance (well supported), but find a better
five-drop than Galvanoth. Note the swap got WEAKER after these fixes
(+0.0165 -> +0.0128) because they made Penance less bad.

### 2026-09-05 (later): re-verification — the DATA is clean, the LABELS are not

`validate.py`: `+0.00` on all six, `corr(A,B)` 0.8927 → 0.9045 → **0.9057**.
The three ablation tables are still valid; only Grist's own row moved.

**`audit_cards.py` exists again** (CLAUDE.md listed it as lost). It checks name,
cost, MV, P/T, card types, `is_land`, `tapped`, `produces` and `flying` for all
289 card slots plus every module-level candidate, against Scryfall. It reports
**0 errors**. Run it after any deck edit. The 52 data errors of 2026-09-03 are
fixed and have not regressed; the nine remaining notes are the single-cost
model's known limits, each printing its own reason.

**Card DATA is no longer where the bugs are. The remaining errors are all
CLAIMS ABOUT BEHAVIOUR that nothing checks** — a name in `SCRIPTED_*`, a
generated tag set, a script that reads the wrong zone. Full write-up in
`KNOWN_ISSUES.md` §0. The four that change what to do next:

1. **Grist was a creature on the battlefield.** "As long as Grist ISN'T ON THE
   BATTLEFIELD, it's a 1/1 Insect creature" — so it triggers Rendmaw when
   played and is a bare Planeswalker after. It was attacking, and under March of
   the World Ooze it was a **6/6 attacker**. FIXED via
   `engine.is_battlefield_creature()`, which is the same question `impending` already
   asks for Overlord. Cost: −0.32/−0.39 damage, **win rate unmoved at both
   horizons** (−0.0003, inside its bar). Default-on for that reason.
2. **`tag_flying.py` never tagged candidates.** It walked `build()` only, and
   `flying=name in FLYING` is evaluated at import — so Goldspan Dragon (4/4
   flying haste) and Caldera Pyremaw (3/3 flying) were both **measured as ground
   creatures**. FIXED; no deck card changed, so no table moved. Same shape as the
   2026-09-04 `SCRIPTED_*` bug: a generated set the deck moved past.
3. **Radiant Scrollwielder read the wrong ZONE.** Oracle: "exile an instant or
   sorcery card at random **from your graveyard**"; the engine read
   `library[-1]`. FIXED — and it tripled the card's firings without making it a
   better card, because every one of them is paid for in full. Its number is
   still a floor: "instant and sorcery spells you control have lifelink" is
   unmodelled.
4. **Three cards in `SCRIPTED_LOREHOLD` are not their text**: Apex of Power is
   `draw4` (no exile-and-cast, no "add ten mana of any one color"), Hit the
   Mother Lode is a flat 5 Treasures (no Discover 10), Borrowed Knowledge is
   `draw2` when it is a WHEEL. `check_scripted_coverage()` cannot catch this —
   it verifies every card is CLASSIFIED, not that the classification is TRUE.

### The "lower stakes" fixes — two of the three were not

I filed these as low-stakes. Measured as CFG flips, 6,000 paired games each
(`run_lowstakes.py`), **two of the three move win rate by about a point**:

| fix | deck | win T10 | win T20 |
|---|---|---|---|
| `attack_triggers` | rendmaw | +0.0033 [+0.0018, +0.0050] | **+0.0100 [+0.0067, +0.0135]** |
| `everywhere_enters_tapped` | rendmaw | −0.0008 [−0.0022, +0.0005] | +0.0002 [−0.0020, +0.0025] |
| `another_creature_clause` | karlov | −0.0103 [−0.0133, −0.0073] | **−0.0130 [−0.0178, −0.0085]** |

1. **Grave Titan and Overlord both read "enters OR ATTACKS"** and only the ETB
   half fired. `engine.attack_triggers()` runs in the declare-attackers step.
   +0.47 triggers a game, +0.55 tokens, +1.53 board power, +1.43 damage — and
   +0.048 *Rendmaw* triggers, because Overlord's extra land tokens are extra
   mana and that buys extra spells. **+0.0100 win rate is comparable to the
   staged Cauldron of Essence swap.**
2. **Overlord's Everywhere token entered untapped**; the oracle says tapped.
   This one IS as small as advertised — win rate flat at both horizons, with
   `mana_floated` −0.32 and `stranded_mv` +0.35. Exactly the right shape: the
   mechanism moves and the objective does not.
3. **Suture Priest, Daxos and Elas il-Kor triggered off their own arrival.**
   All three read "whenever ANOTHER creature you control enters";
   `creature_entered` took an `entering` argument and only Guide of Souls used
   it. That is **0.85 phantom lifegain triggers a game**, not the "one per card
   per game" I guessed, and in a deck where the trigger IS the payoff it
   compounds through Karlov's counters, Voice of the Blessed, Cliffhaven
   Vampire, Marauding Blight-Priest and Starscape Cleric.
   **This is the third time correcting Karlov has made it look worse** — the
   2026-09-03 audit was −0.0163, same cause: phantom lifegain triggers.

All three gated, all three default on. `validate.py` `+0.00` on all six,
`corr(A,B)` 0.9057 → 0.9069.

**`ablation_karlov.txt` is therefore void too**, which an earlier version of
`regen_tables.sh` denied in writing. That argument was correct about the Grist
change and wrong about this one — the lesson being that "this engine is
independent" is a claim to check per change, not once.

**And one that pod v3 promoted from harmless to live:** life-loss drawbacks are
still free. That was fine when 100% of losses were an opponent's clock. It is
not fine now that the life-share of losses is 0.32/0.43/0.20. **Bitterblossom
loses 1 life every upkeep and is Rendmaw's #5 card at +0.0205 win — its number
is a ceiling.** Same for Phyrexian Arena, Talisman of Conviction, Dark Confidant.

### The Penance slot: RESOLVED — Caldera Pyremaw, not Galvanoth

The standing recommendation was "cut Penance, but find a better five-drop than
Galvanoth." Two of the three contenders had been measured on a broken
implementation. Both were fixed and all three re-measured against the same cut
with the same seeds (`run_fivedrop.py`, 6,000 paired games each, pod v3):

| card | MV | win T10 | win T20 |
|---|---|---|---|
| **Caldera Pyremaw** | 5 | **+0.0035 [+0.0012, +0.0060]** | **+0.0202 [+0.0150, +0.0257]** |
| Galvanoth | 5 | +0.0020 [−0.0002, +0.0043] | +0.0128 [+0.0078, +0.0180] |
| Radiant Scrollwielder | 4 | +0.0015 [−0.0008, +0.0038] | +0.0125 [+0.0075, +0.0178] |

Caldera is the only one significant at **both** horizons. Three swaps against a
common baseline have overlapping CIs and cannot be ranked against each other,
so the decision rests on the **head to head**, where Penance is absent from both
branches: `-Galvanoth +Caldera Pyremaw` is **+0.0028 [+0.0012, +0.0047]** at ten
turns and **+0.0093 [+0.0057, +0.0133]** at twenty, significant at both.

**`pending.py` re-staged: `-Penance +Caldera Pyremaw`.** Galvanoth's own numbers
reproduced exactly on the new engine (+0.0020 / +0.0128, identical to the
previous staging), so the ranking is a fact about the cards and not about the
same day's engine changes.

**The proxy disagrees with the objective again.** Head to head, `mv_cheated`
goes DOWN 1.35 while win rate goes UP — Caldera cheats no mana at all, it just
deals damage. Same shape as the top-setter finding. Follow win rate.

**Why, mechanically** (`diag_fivedrop.py`, n=4,000, T20). All three arrive in
about the same share of games, so the difference is not castability — it is what
they do once they land:

| card | cast in | on turn | per game it resolves |
|---|---|---|---|
| Galvanoth | 13.9% | 9.6 | 0.68 free casts |
| Caldera Pyremaw | 13.8% | 9.6 | **14.5 pod damage** |
| Radiant Scrollwielder | 18.6% | **8.2** | 2.20 paid casts |

**Fixing Radiant Scrollwielder's zone tripled its firings and did not make it a
better card.** It is MV 4, so it lands a turn and a half earlier and in a third
more games — and it still only ties Galvanoth, because unlike Galvanoth it pays
full price for every cast: its `mv_cheated` gain is +0.61 against Galvanoth's
+1.34. Its number is still a floor (lifelink unmodelled), but it would have to
be worth six points of win rate to matter.

Note the three-way was measured on the v16 list, which still has Scroll Rack
rather than the staged Sunbird's Invocation. That is the same baseline Galvanoth
was measured on, so the comparison is sound — and **the two staged Lorehold
changes were measured together on 2026-09-06; they add.** See the 0b section
below.

Goldspan Dragon was passed at +0.0025 ±0.0045 and was understated by the same
flying bug; **re-measured 2026-09-06** — see the Goldspan section.

### 2026-09-05: a fourth deck — Tivit, Seller of Secrets

`validate.py` now prints `+0.00` on **nine** metrics across three engines. The
Tivit A/A control is clean on `artifacts_made`, `votes_cast` and `damage`.
Baseline over 500 games at T20: **win rate 0.360**, between Rendmaw (0.307) and
Karlov (0.455).

**The vote is the first thing in this project that asks an OPPONENT to decide.**
Everywhere else the opponent model is a clock, a blocker count and a removal
rate — it never chooses. `edhmc/voting.py` holds the mechanic and the
assumption. Read it before trusting any number about a vote card.

Four keywords, and a single "who won the vote" helper would be wrong for most:

| keyword | resolves as |
|---|---|
| will of the council | ONE outcome, most votes wins, ties usually **against** you |
| council's dilemma | PER-VOTE — every vote has its own effect, no winner |
| tempting offer | not a vote; opponents opt in and you match them |
| secret council | simultaneous, so vote control applies but information does not |

`cfg["opp_vote_policy"]` defaults to **`"adversarial"`** — every opponent votes
against you and they agree with each other. That is the pessimistic bound and a
**judgement call**, not a claim about real pods. Any card whose evaluation
swings on it must be reported with the knob said out loud, the same rule
`destroy_share` already carries. `"selfish"` and `"random"` are the
alternatives.

**Why pessimism is safe for the commander and brutal for the vote cards.**
Tivit's dilemma is "for each evidence vote, investigate; for each bribery vote,
create a Treasure" — **both halves make an artifact**. An adversarial pod
cannot reduce the count, only the mix. So the commander is untouched by the
assumption while will-of-the-council cards are hit hard: the baseline wins only
**0.25 of 1.98 councils a game**, because Tivit's own extra vote gives you 2
against 3, and you need BOTH Ballot Broker and Brago's Representative to reach
4 and win outright.

**That threshold is a leave-one-out trap.** Cut either extra-vote creature
alone and the other still ties, so both look weak individually and are worth
far more as a pair — the same shape as Karlov's three Exquisite Blood partners.
**Ablate them as a group.**

**The engine loop, and a claim the measurement corrected.** Deadeye Navigator
soulbound to Tivit is "{1}{U}: dilemma" — two mana in, one dilemma out. Your
votes buy Treasures, an adversarial pod's buy Clues, so the loop pays for
itself exactly when

    (your votes) × (token kinds per vote) > 2

I built the engine believing Academy Manufactor was the only way over that
line, and wrote it into the docstring. **It is not.** Measured directly from a
ten-Treasure pool with no lands (`test_tivit_combo.py`):

| board | votes × kinds | result |
|---|---|---|
| Tivit + Deadeye alone | 2 × 1 = 2 | 1 iteration, 10 → 10. **Exactly break even**, stops |
| + Academy Manufactor | 2 × 3 = 6 | runs to the cap, 10 → 130 |
| + Ballot Broker | **3 × 1 = 3** | **runs to the cap**, 10 → 50 |
| + Ballot Broker + Brago's | 4 × 1 = 4 | 10 → 90 |
| + Manufactor + Ballot Broker | 3 × 3 = 9 | 10 → 170 |

**A single extra-vote creature tips the loop on its own, with no Manufactor.**
So Ballot Broker and Brago's Representative are combo pieces, not just
vote-count cards — worth knowing before cutting either as "just a body", and
on top of the tie-breaking role that already made them a leave-one-out trap.
`test_tivit_combo.py` pins the whole table so the docstring cannot drift from
the behaviour again.

Unconditionally, ablating Academy Manufactor is **−0.0292 [−0.0372, −0.0212]**
win rate, −10.3 artifacts and −5.3 damage, all significant.

The pile then has to CONVERT, and `convert_the_pile()` checks in the order a
pilot would: Revel in Riches at ten Treasures, Mechanized Production at eight,
then the drains, then Time Sieve. `win_route` records HOW the deck won — over
500 games: combat 76, drain 70, mechanized 15, torment 10, revel 5, sieve 3.
Extra turns are real turns and still count against the horizon, so this deck
cannot buy turns the other three engines do not get.

**Classification: 39 SCRIPTED, 25 KNOWN_BLIND**, each with its reason. Half the
blind group is the project's oldest limitation — opponents' boards are a
blocker count, so no removal spell can be evaluated. The rest are blind
*despite* having engine code, which is the distinction this project has got
wrong twice: Expropriate's extra turns land but stealing a permanent needs
permanents to steal; Torment of Hailfire's X is fixed and opponents can only
pay in life, so it is a **ceiling**; Rhystic Study's tax is a social fact the
model cannot see.

**`audit_cards.py` earned its keep immediately**: it caught SIX untagged
fliers in the new list, Tivit itself among them. Regenerating `_evasion.py`
moved the deck's win rate 0.327 → 0.360. That is the "adding a card is TWO
edits" hazard, caught by a tool this time rather than by a later session. All
four decks are now 0 ERR over 377 card slots.

### Reading `ablation_tivit.txt` — two things before the rows

**UPDATED 2026-09-06: this table is now 15,000 paired games, not 2,000.** Point
1 still stands. Point 2 was a statement about N=2000 and has been settled by the
bigger sample — kept below, because how it was settled is the useful part.

1. **The damage column is barely measurable at T20.** Sol Ring was +8.32 ±8.15,
   Deadeye Navigator +7.50 ±7.90, Cyberdrive +8.76 ±7.82. The combo tail makes
   this deck's damage distribution far heavier than the other three, so the
   proxy that works elsewhere mostly does not work here. Win rate is tighter by
   an order of magnitude. "Follow win rate where they disagree" is usually a
   judgement call; **for this deck it is a statistical necessity.** More games
   narrow the bars but do not change the shape: at N=15,000 Sol Ring's damage is
   +3.52 ±2.08 against a win rate of +0.0299 ±0.0043, still an order of
   magnitude looser in relative terms.
2. **The noise floor was ~±0.015 win rate at N=2000, and the four signets
   proved it — twice.** They are functionally interchangeable two-mana rocks and
   they scored +0.0080, +0.0050, +0.0100 and +0.0200. Four cards doing one job
   spread over 0.015 IS the noise floor, and that was the argument for treating
   anything inside it as unranked.
   **At N=15,000 the same four score +0.0131, +0.0131, +0.0131 and +0.0120** —
   a spread of 0.0011 against a noise floor of ±0.0024, and all four now
   significant. The 0.015 spread was entirely sampling noise, exactly as
   claimed. This is the cleanest confirmation in the project that the
   "ignore anything inside its bars" rule is doing real work: four cards that
   looked like a 2.5x range of quality were always the same card.
   `run_tivit_groups.py` still measures the floor deliberately rather than
   leaving it as a coincidence.
   **Reproduced a third time on the 2026-09-06 extra-turn table**: the four
   signets score +0.0168, +0.0151, +0.0167 and +0.0161 — a spread of 0.0017
   against a ±0.0029 bar. The whole table shifted underneath them and the four
   stayed within noise of each other, which is the property you want from a
   noise-floor probe.

### The group ablations, which are the ones to act on

`tivit_groups.txt`, 3,000 paired games. **Sign convention: the figure is what
CUTTING the group costs you.**

**CURRENT TABLE, 2026-09-06 after the extra-turn fix (§0m).** The `was` column
is the figure before it, so the one group that actually moved is visible:

| group | cards | cut costs, win T20 | was | vs sum of the singles |
|---|---|---|---|---|
| **every drain** | 5 | **0.1233** [0.1103, 0.1370] | 0.1427 | — |
| token drains | 3 | 0.0850 [0.0740, 0.0963] | 0.0973 | roughly additive |
| blink package | 6 | 0.0700 [0.0580, 0.0823] | 0.0730 | most were `--` alone |
| **the four signets** | 4 | **0.0583** [0.0470, 0.0700] | 0.0500 | 0.0647, roughly additive — this group is the NOISE-FLOOR probe, not a deckbuilding question |
| **alternate wins** | 3 | **0.0520** [0.0420, 0.0617] | 0.0123 | **4.2x its old figure** |
| artifact drains | 2 | 0.0257 [0.0180, 0.0340] | 0.0327 | — |
| **extra votes** | 2 | **0.0213** [0.0133, 0.0293] | 0.0230 | 0.0119 — **~1.8× the sum** |

Only `alternate wins` moved by more than its own bar. The five drains all came
down 13-21%, which is arithmetic and not a finding: the deck's baseline win rate
rose 0.343 → 0.397, so any one card is a smaller share of it.

The table below this point is the pre-2026-09-06 version, kept because the
reasoning is what matters and one of its three findings is now retracted:

| group | cards | cut costs, win T20 | vs sum of the singles |
|---|---|---|---|
| **every drain** | 5 | **0.1413** [0.1277, 0.1553] | — |
| token drains | 3 | 0.0973 [0.0853, 0.1093] | 0.0835, roughly additive |
| **the four signets** | 4 | **0.0533** [0.0423, 0.0643] | 0.0430, roughly additive |
| blink package | 6 | 0.0570 [0.0453, 0.0687] | most were `--` alone |
| artifact drains | 2 | 0.0317 [0.0237, 0.0397] | — |
| **extra votes** | 2 | **0.0253** [0.0173, 0.0337] | 0.0115 — **2.2× the sum** |
| alternate wins | 3 | 0.0047 [−0.0040, 0.0133] | **inside its bar** |

Three findings worth carrying forward:

- **THE DECK WINS BY DRAINING, NOT BY ASSEMBLING AN ALTERNATE WIN.** All five
  drains together are worth 0.14 win rate. Revel in Riches + Mechanized
  Production + Time Sieve together are **inside their error bar at 20 turns**,
  and cutting them *raises* damage by +5.16 and costs 0.48 extra turns. They
  are three slots buying an outcome the deck reaches more reliably by other
  means. This is the first real deckbuilding question the deck has raised, and
  it wants a controlled test before anything is staged.
  **PARTLY RETRACTED 2026-09-06 (blank fix, `KNOWN_ISSUES.md` §0j).** Re-run at
  the same n=3,000 against a blank that is actually cast, the alternate-win
  package costs **0.0123 [0.0040, 0.0203] — significant**, not zero. The
  ordering survives (the drains are still ~12x bigger) but "three slots buying
  nothing" was an artifact of the old blank. Of the three, Mechanized Production
  is +0.0119 alone and Revel in Riches +0.0025; only Time Sieve is negative
  (−0.0025, no longer significant). ~~Cut Time Sieve, not the package.~~
  > **FULLY RETRACTED, LATER THE SAME DAY (extra-turn fix, §0m). DO NOT CUT TIME
  > SIEVE — it is joint-best in the deck.** The package costs **0.0520 [0.0420,
  > 0.0617]** to cut, 4.2x the blank-fixed figure and the only one of the seven
  > groups that moved materially; it goes from last to fourth, ahead of the
  > extra-vote pair. Time Sieve alone is **+0.0344 ±0.0034**, not −0.0025: an
  > extra turn was running the opponents' whole round at the end of it, and
  > Tivit + Time Sieve is a two-card infinite-turn combo the engine was
  > truncating to one step and then charging a pod round for. **Both retractions
  > pointed the same way and neither went far enough**, which is the argument for
  > taking "cutting this costs nothing" as a question about the engine first.
  > The drains are still the biggest group (0.1233), so only the PRIORITY
  > ordering of the original claim survives.
- **THE EXTRA-VOTE PAIR IS THE PREDICTED REDUNDANCY TRAP, CONFIRMED.** Ballot
  Broker and Brago's Representative are +0.0075 and +0.0040 alone — both inside
  the noise floor, both look cuttable — and **0.0253 together, 2.2× the sum**.
  **The N=15,000 table sharpens this rather than softening it (2026-09-06):**
  individually they are +0.0050 ±0.0025 and +0.0069 ±0.0025, so both are now
  *measurably positive* rather than lost in the noise — and their sum, 0.0119,
  is still only 47% of the pair's 0.0253. The trap was never an artifact of the
  small sample. Note what changed and what did not: the reason to distrust the
  single-card rows went from "you cannot see them" to "you can see them and they
  are still wrong", which is the stronger version of the same warning.
  The mechanism metrics say why: cutting the pair costs 0.95 Tivit triggers and
  0.98 combo iterations, because the third vote is what tips the Deadeye loop
  mana-positive (see `test_tivit_combo.py`) and the fourth is what wins a
  will-of-the-council vote outright. Never read either row alone.
- **The blink package is worth 0.057 and almost invisible card-by-card.** Six
  ways to re-trigger the commander, each covering for the others: cutting all
  six costs 3.12 Tivit triggers and 20.6 artifacts.

### Fixed hazard: ablation cache key

`ablation.py` used to key its cache on deck and horizons but **not on sample
size N**, so resuming a run at a different N silently merged two sample sizes
into one table. Fixed 2026-09-03 — the key now carries `_n{N}`, e.g.
`ablation_cache_karlov_10-20_n6000.json`.

**The caches are TRACKED as of 2026-09-05** (141 KB for all four, against
about six hours of simulation), so a clone can reproduce or extend the tables
without the run. Still delete them after any engine or deck change: the key
covers the parameters of the run, not the version of the code that produced it.

Tracking them removes the safety net that a fresh clone had no cache to go
stale, so `ABLATION_CACHES.md` records a SOURCE FINGERPRINT per deck — a hash
of the modules whose behaviour a cached number depends on. Re-run
`python cache_manifest.py` and compare before resuming; if it differs, delete.
`./regen_tables.sh` deletes by default, `--resume` does not.

### 2026-09-06: a full table takes two minutes, not ninety

Three changes, none of which touches a rule of the game. Every one is pure
scheduling — the same seeds feed the same engines in the same order.

| deck | was | now |
|---|---|---|
| karlov (63 cards, n=6000) | ~90 min | **2m10s** |
| rendmaw (64 cards, n=6000) | ~90 min | **2m01s** |
| lorehold (65 cards, n=6000) | ~90 min | **2m53s** |
| tivit (64 cards, n=2000) | — | **55s** |

1. **THE BASELINE WAS SIMULATED ONCE PER CARD AND IT DOES NOT DEPEND ON THE
   CARD.** `ablate()` measured `metric(real deck) - metric(deck with this slot
   blanked)` by re-running the untouched deck for all 65 cards. Exactly half of
   every run was recomputing one fixed number. It is now measured once per
   horizon and shared. Safe because `simulate` copies the deck it is handed and
   **nothing in edhmc mutates a Card** — checked by grep across every module,
   and the reason `blank_like` can hand the same objects to both branches.
2. **Cards are ablated in parallel.** Each card is a deterministic function of
   (deck, seed) with no shared state, so `imap_unordered` over 16 cores is a
   free ~12x. `ABLATE_PROCS=1` forces the old single-process path — use it when
   debugging; it is verified to produce the identical cache.
3. **`Game.has(name)` was 38% of runtime.** It was a linear scan over the
   battlefield, and almost every static ability in the project is written as
   `g.has("Some Card")` inside a loop — 475,000 calls in 400 Lorehold games.
   `engine.Board` is a `list` subclass carrying a name→count index, so `has`
   and `count` are dict lookups. This one speeds up EVERY entry point, not just
   ablation: 1.5x rendmaw, 1.5x lorehold, 1.4x karlov, 1.2x tivit per game.

**HOW IT WAS VERIFIED, because "it's only a refactor" is exactly the claim this
project has been burned by.** All four caches were deleted and re-derived from
empty on the new code. The result reproduces the committed tables **bit for
bit — 2,560 floating-point values, zero differences, and all four
`ablation_*.txt` byte-identical**. `validate.py` is `+0.00` on all nine with
`corr(A,B)` unchanged at 0.9069. The parallel, serial and
resumed-across-a-budget-cut paths all write byte-identical caches.

The fingerprints in `ABLATION_CACHES.md` MOVED, because `ablation.py` and three
engines changed. That is the check doing its job and not a stale cache: the
re-derivation above is why the caches were kept.

One deliberate behaviour change: **the cache is written in DECK ORDER rather
than completion order**, so the file does not depend on which worker finished
first or on whether the run was resumed. `run_tivit_groups.py` got the same
baseline fix (its A leg is the untouched deck for all seven groups); output is
byte-identical there too. `candidates.py` was left alone — its A leg is a blank
of the CANDIDATE's cost, so there is no shared baseline to hoist.

### 2026-09-06: all four tables re-measured at N=15,000

The speedup was spent on precision. 23 minutes for all four decks.
`./regen_tables.sh` now runs N=15000 and includes tivit.

**WHY 15,000 AND NOT MORE.** CI scales as 1/sqrt(N), so every halving of the
error bar costs FOUR TIMES the games — there is no way to buy out of that.
Measured over all 256 cards, the cards resolved per extra minute of runtime:
3.4 going 6000→10000, 2.0 going 10000→15000, then **0.8** going 15000→24000.
That collapse is the knee. The other half of the argument is the effect size
this project actually argues about: the contested calls (Cauldron +0.0025,
Caldera head-to-head +0.0028, Goldspan +0.0025 ±0.0045) all sit at 0.0025-0.003
win rate, and N=15,000 is the first sample size whose median bar — 0.0026
karlov, 0.0022 rendmaw, 0.0034 lorehold, 0.0024 tivit — is at that scale.
N=24,000 would halve the 6000-era bars outright, at 38 minutes a regeneration
rather than 23; that is the trade to revisit, not a settled question.

| deck | median win CI | unmeasured (`--`) | newly resolved |
|---|---|---|---|
| karlov | 0.0042 → **0.0026** | 8 → 7 | 2 |
| rendmaw | 0.0034 → **0.0022** | 9 → 3 | 7 |
| lorehold | 0.0054 → **0.0034** | 18 → 14 | 8 |
| tivit | 0.0062 → **0.0024** | 26 → 9 | 19 |

**THE CHECK THAT MATTERS: NO CARD THAT WAS ALREADY SIGNIFICANT ON WIN RATE
CHANGED SIGN, in any of the four decks.** Point estimates moved a median of
0.29 old half-widths (max 1.15). So the N=6000 tables were not reporting noise
as findings, and every conclusion in this file that rests on them survives —
each number quoted above was re-checked individually and none moved by more
than its old bar. The variance is also clean 1/sqrt(N) with no floor
underneath: predicted CI ratios 0.63/0.63/0.63/0.37, measured
0.64/0.64/0.63/0.39.

**What DID change is the top-of-table ORDER, and it was never real.** All four
decks reshuffled their top eight by win rate — and **not one** of the cards that
entered or left moved by more than its own old error bar. The rank-1 to rank-8
*gap* is 3-15x the noise floor, so the top eight is a meaningful SET; the order
within it never was. Read the top of these tables as a group, not a ranking.
That is the "do not rank inside the bars" rule catching a mistake that is very
easy to make from a sorted table.

**Nine cards are still `--` in tivit and fourteen in lorehold, and more games
will not fix most of them.** Four tivit cards have a CI of *exactly zero* — An
Offer You Can't Refuse, Path to Exile, Swords to Plowshares, Counterspell
produced bit-identical games to their blanks in all 15,000 pairs. That is not
noise, it is the model: opponents' boards are a blocker count, so a removal
spell has nothing to remove. **A card at exactly ±0.0000 is a MODEL-BLIND card
proved blind, not a card measured as bad** — and it is the sharpest statement of
that limitation the project has produced.

Both the N=6000/2000 caches and the new N=15000 ones are kept. The old ones are
the provenance for every number quoted above them in this file, and
`cache_manifest.py` now keys its notes by CACHE FILE rather than by deck so two
sample sizes for one deck each carry their own honest history — keying by deck
printed one note under two headings, which is the same "a label nothing checks
is just a claim" failure the `SCRIPTED_*` sets have produced twice.

### 2026-09-06: THE TIVIT + TIME SIEVE LOOP WAS NOT BEING PLAYED

Full write-up in `KNOWN_ISSUES.md` §0m; `diag_time_sieve.py` is the evidence.
The short version, because it is the largest single correction in the project:

**Tivit + Time Sieve is a two-card infinite-turn combo in a four-player game.**
Tivit's attack trigger is a council's dilemma; you get two votes and the pod
three; **both halves of the dilemma make an artifact**, so an adversarial pod can
change the mix and not the count. Five artifacts is exactly Time Sieve's cost,
and the Sieve untaps on the turn it just bought. The engine scored the card at
**−0.0025 ±0.0026** — slightly negative — because of three bugs:

1. Time Sieve activated up to ten times a turn; its cost is `{T}`, so once.
2. Extra turns generated during an extra turn were discarded, which truncated
   the chain to one step every time.
3. **Every extra turn ran the opponents' whole round at the end of it**, so each
   extra turn handed the pod a free extra round. `lorehold.take_turn` already
   had this right, so the two engines modelled one concept in opposite ways.

Deck win rate 0.343 → **0.397** (+0.0538 ±0.0062), almost all of it from #3.
**Time Sieve's own row: −0.0025 → +0.0344 ±0.0034**, joint-best in the deck with
Sol Ring. Expropriate went from a proved blank to +0.0127. On a forced board of
just Tivit + Time Sieve + six lands, the old engine took 10 extra turns, gave
the pod 16 rounds and **lost**; the new one gives the pod 2 rounds, chains 14
extra turns and **wins**.

`ablation_tivit.txt` and `tivit_groups.txt` are regenerated. **The standing
"the deck wins by draining, not by assembling an alternate win" finding is now
fully retracted**: cutting Revel + Mechanized + Sieve costs 0.0123 → **0.0520**.
The drains are still the biggest group at 0.1233, so the PRIORITY ordering
survives; the claim that the alternate-win slots buy nothing does not. **Do not
cut Time Sieve.**

### 2026-09-06: Erebos, Bleak-Hearted — three errors, and the fourth correction that cost win rate

`KNOWN_ISSUES.md` §0l, closing queued work item 8. It was a creature regardless
of devotion to black (0.38 creature-turns a game against the 0.05 it is entitled
to), **it had been given Dockside Chef's activated ability instead of its own
death trigger**, and it was never tagged indestructible. Measured at N=15,000:
the body is −0.0047 win at T20, the trigger +0.0023, the indestructibility
+0.0007, **all three together −0.0018 ±0.0024**. All default on.

`ablation_rendmaw.txt` is regenerated, and the check that matters is that **zero
of 64 cards moved by more than their own old CI half-width** — the baseline
shifts, the ranking does not. **Erebos itself went from +0.0054 ±0.0025 (`both`)
to +0.0033 ±0.0026 with NEGATIVE damage at ten turns (`FLIP`), which makes it a
cut candidate it was not before.** It was scoring on a body it is not allowed to
have.

Two things generalise beyond the card:

- **`engine.devotion(g, color)` and `DEVOTION_CONDITIONAL_CREATURES`** answer
  creature-ness conditioned on BOARD STATE, which the `impending` sentinel could
  not: devotion moves as permanents enter and die, so the question is re-asked at
  every call site instead of stamped at ETB. `karlov.is_creature_now` still does
  the white twin for Heliod and is still deliberately a separate function.
- **`indestructible` IS NOW A GENERATED TAG.** Setting it on one card by hand is
  the partial-tag bias this file warns about, and doing so turned up two more
  indestructible cards in the Rendmaw list — both LANDS (Darkmoss Bridge,
  Darksteel Citadel). `tag_flying.py` emits `INDESTRUCTIBLE` over all card types,
  every `C()` and `L()` derives from it, and `audit_cards.py` now checks the
  field. **0 ERR across 377 card slots.** §0n.

### 2026-09-06: item 0b — the two staged Lorehold changes ADD

`KNOWN_ISSUES.md` §0p; `run_lorehold_pair.py` is the harness and
`lorehold_pair.txt` the output. **This clears the stated blocker on writing
either change to the `.xlsx`.**

The doubt was mechanical, not statistical: two additions to the same top-heavy
curve, and **both cuts are top-setters** (Penance and Scroll Rack are both in
`lorehold.TOP_SETTERS`). A difference of two differences needs its own design, so
this is a **2×2 factorial with all four legs shuffled on the same seed**, which
makes the interaction a paired quantity. N=30,000 per cell — twice the tables,
because an interaction carries roughly twice a main effect's variance.

| win rate | T10 | T20 |
|---|---|---|
| Caldera alone | +0.0028 ±0.0011 | +0.0194 ±0.0024 |
| Sunbird's alone | +0.0019 ±0.0012 | +0.0146 ±0.0028 |
| **both** | **+0.0047 ±0.0016** | **+0.0362 ±0.0035** |
| **interaction** | **+0.0000 ±0.0008** | **+0.0022 ±0.0020** |
| Caldera GIVEN Sunbird's | +0.0028 | **+0.0216 ±0.0026** |
| Sunbird's GIVEN Caldera | +0.0019 | **+0.0168 ±0.0029** |

Zero interaction at T10, slightly super-additive at T20 — the opposite of the
worry. **Both predicted costs are real and both are outweighed**, and that is the
part to carry forward rather than the headline: `stranded_mv` compounds (+0.60
±0.18 beyond additive) and the two cards genuinely compete for miracles
(`miracles_cast` −0.018 ±0.008). The mechanism was right; the magnitude was not.

**One staged number reproduced and one did not.** Caldera: +0.0202 → +0.0194
±0.0024. Sunbird's: +0.0215 → **+0.0146 ±0.0028**, and +0.0077 → +0.0019 at T10
with disjoint bars. **The obvious explanation was tested and is wrong** — both
cuts are top-setters and the 2026-09-05 policy fixes made top-setters better, so
the cut should have got dearer, but Scroll Rack still ablates to −0.0093 ±0.0032
against the −0.0100 it was worth on 2026-09-04. The cut is as cheap as it ever
was; the decay is in Sunbird's own contribution and **is not attributed. Do not
invent a mechanism for it.**

And a smaller correction with a general lesson: the ledger justified Sunbird's
with "fires 3.6 times a game for an average free spell of MV 3.8". That was a
**conditional number printed as an unconditional one**. The card is MV 6 and
resolves in **13.0% of games**; conditional on resolving it is 6.06 triggers and
4.00 free casts at MV 3.77, so the old figure was right as a conditional and
read as though 3.6 free spells arrived every game. Unconditionally it is 0.52.
`sunbird_triggers` now exists next to `sunbird_casts` — 34% of firings find
nothing — and `pending.py` says which number is which.

### 2026-09-06: Goldspan Dragon re-measured — closes queued work item 0c

It was passed on 2026-09-04 at +0.0025 ±0.0045, and that number was wrong twice
over: it was measured as a GROUND creature (the candidate flying gap, §0c) and
against the dead blank (§0j). Re-measured at **N=15,000** — the old ±0.0045 could
never have resolved an effect of 0.0025 — with `run_goldspan.py`:

| horizon | win rate | damage | P(deploy) |
|---|---|---|---|
| T10 | **+0.0018 ±0.0010** | +0.94 ±0.16 | 0.088 |
| T14 | **+0.0051 ±0.0022** | +1.31 ±0.31 | 0.137 |
| T20 | **+0.0057 ±0.0027** | +1.30 ±0.39 | 0.154 |

**Significant at all three horizons, where it used to be inside its bar** — the
point estimate at T14 doubled. It is a real card, not the pass it was recorded as.

Against the current Lorehold table its +0.0057 exceeds the two worst
model-evaluated cards in the list (Blasphemous Act −0.0053, Lightning Greaves
−0.0045), which on paper is an ~0.011 swap. **That is not a staging.** Three
swaps against a common baseline have overlapping CIs and cannot be ranked
against each other — the rule that decided the Penance slot — so this needs a
HEAD-TO-HEAD before anything moves, and Blasphemous Act is a sweeper whose value
is entangled with `should_cast_own_wipe`.

**A confound was checked and ruled out.** Goldspan and Caldera Pyremaw are the
same cost, the same threat and the same slot, differing by one hand-set knob:
priority 8 against 8.5. Re-run at a matched 8.5, Goldspan is +0.0020 / +0.0050 /
+0.0055 — unchanged — and P(deploy) moves 0.137 → 0.139. The knob is not the
story.

**And one number was thrown away.** Caldera Pyremaw was run as a control and the
row was meaningless: it is ALREADY in the staged Lorehold list, so the harness
built a 101-card singleton-illegal deck with two copies and measured the
duplicate. `candidates.py` now refuses. §0o.

---
