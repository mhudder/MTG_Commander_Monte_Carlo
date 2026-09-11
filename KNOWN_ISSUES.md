# Known issues

Numbered findings, each with the evidence that produced it. **The section ids
are load-bearing** — `edhmc/azusa.py`, `tools/cache_manifest.py`,
`diagnostics/diag_azusa_animation.py`, `docs/ABLATION_CACHES.md` and
`CLAUDE.md` all cite them. Reorganise around them; **never renumber**. A new
finding takes the next free letter in the `0*` series.

`python -m edhmc.pending` is the only trustworthy statement of what is staged.
`docs/PENDING_CHANGES.md` is stale and predates `lorehold_v16.py`.

Methodology that used to live at the end of this file is now
`docs/READING_TABLES.md`. Dated session narrative is `docs/HISTORY.md`.

---

## Index

`FIXED` — the defect is corrected and the fix is in the default path.
`OPEN` — a real modelling gap, still live.
`MEASURED` — a question that was asked and answered; nothing to fix.

| § | status | finding |
|---|---|---|
| [0a](#0a) | MEASURED | card DATA is clean — 0 errors across 269 distinct names |
| [0b](#0b) | FIXED | Grist was a creature on the battlefield |
| [0c](#0c) | FIXED | candidates were never flying-tagged, so a flier scored as ground |
| [0d](#0d) | FIXED | Radiant Scrollwielder read the wrong zone — and it did not help |
| [0e](#0e) | MEASURED | the Penance slot, resolved: Caldera Pyremaw |
| [0f](#0f) | **OPEN** | three Lorehold cards are not implemented as their text (now labelled PARTLY MODELLED, §0z4) |
| [0g](#0g) | FIXED | two "or attacks" triggers, and one token entering untapped |
| [0h](#0h) | FIXED | "another creature you control": three cards triggered off themselves |
| [0i](#0i) | **OPEN** | life-loss drawbacks are free, and pod v3 made that matter |
| [0j](#0j) | FIXED | the blank was not replacement level; every table's bottom was taxed |
| [0k](#0k) | FIXED | Ephemerate was a proved blank, its handler dead code |
| [0l](#0l) | FIXED | Erebos, Bleak-Hearted: three errors on one card |
| [0m](#0m) | FIXED | an extra turn gave the opponents an extra round |
| [0n](#0n) | FIXED | hand-tagging one card is the bug CLAUDE.md warns about, and I did it |
| [0o](#0o) | FIXED | `candidates.py` measured a SECOND COPY of a card already in the deck |
| [0p](#0p) | MEASURED | the two staged Lorehold changes ADD |
| [0q](#0q) | FIXED | hand-maintained name sets — the failure mode this repo keeps having |
| [0r](#0r) | FIXED | Shilgengar's own ability fired ZERO times in 3,000 games |
| [0s](#0s) | MEASURED | Azusa's land animation is nearly a blank; the Nissas are not |
| [0t](#0t) | MEASURED | the mana reserve — how much to hold, and what holding it costs |
| [0u](#0u) | FIXED | three copies of "the miracle discount" had drifted apart |
| [0v](#0v) | FIXED | **combat was declared at one player, and the damage metric was unbounded** |
| [0w](#0w) | MEASURED | all three staged swaps survive the combat split unchanged |
| [0x](#0x) | MEASURED | nine Azusa candidates; Ancient Greenwarden's doubler is the find |
| [0y](#0y) | MEASURED | the land-animation genre loses its slots to those candidates |
| [0z](#0z) | **OPEN** | Ashaya's combos are invisible (the MISLABEL is fixed — PARTLY MODELLED, §0z4) |
| [0z1](#0z1) | FIXED | landfall payoffs were booleans; Springheart bestow+copy implemented |
| [0z2](#0z2) | MEASURED | two card-draw candidates; Bane of Progress (mislabel fixed in §0z4) |
| [0z3](#0z3) | MEASURED | four sacrifice-lands: the TAP is the binding constraint, not the mana |
| [0z4](#0z4) | MEASURED | seven more candidates; **every mana card fails and every card card passes** |
| [0z5](#0z5) | FIXED | token copies re-trigger ETBs — and the fix is worth nothing; the RE-RANK is worth it |
| [0z6](#0z6) | FIXED | Shilgengar's Treasures are mana: every mechanism moves, the objective cannot resolve it |
| [0z7](#0z7) | FIXED | two life-loss drawbacks are charged at last — Bitterblossom costs **−0.0049** |
| [0z8](#0z8) | FIXED | the engine proved one payment and made another; **board order decided which land was tapped** |
| [1](#1) | PARTLY RESOLVED | alternative costs and X-spell mana values |
| [1b](#1b) | **OPEN** | cards can only have one cost — structural |
| [2](#2) | RESOLVED | Hagra Mauling is now a proper MDFC |
| [3](#3) | **OPEN** | Ashnod's Altar and Deathreap Ritual remain unresolved |
| [4](#4) | **OPEN** | opponents' boards are a blocker count — the project's oldest limit |
| [5](#5) | RESOLVED | your own board wipes now hit your own board |
| [6](#6) | RESOLVED | life totals are tracked |
| [6b](#6b) | MEASURED | life is tracked — and since pod v3 it DECIDES GAMES |
| [7](#7) | **OPEN** | unmodelled recursion in Lorehold |
| [8](#8) | superseded | re-run both ablations |

The still-live gaps, in one place: **§0f** (three mislabelled Lorehold cards),
**§0i** (free life-loss drawbacks), **§0z** / **§0z2** (Ashaya AND Bane of
Progress mislabelled; every Azusa combo invisible), **§1b** (one cost per card), **§3**
(two unresolved cards), **§4** (opponents' boards are a number), **§7**
(Lorehold recursion). Everything else is either fixed or was a question rather
than a defect.

---

# 0.# 0. Findings, 2026-09-05 onward

> **RETITLED 2026-09-09.** This series began as "the 2026-09-05
> re-verification" — every card re-checked against Scryfall with the rebuilt
> `audit_cards.py`, and every claim in the file re-read against the code
> rather than trusted. It has since run to `0v` and through 2026-09-08, so the
> date in the old heading described the first four sections and none of the
> rest. The series is kept and extended rather than restarted, because the ids
> are cited from code.

The 2026-09-05 conclusion still frames the series: **card DATA is no longer
where the bugs are.** The remaining errors are CLAIMS ABOUT BEHAVIOUR that
nothing checks — a name in `SCRIPTED_*`, a generated tag set, a script that
reads the wrong zone, a policy that asserts a card does nothing.

<a id="0a"></a>

## 0a. Card DATA is clean — 0 errors across 269 distinct names

`audit_cards.py` (rebuilt; CLAUDE.md listed the original as lost) checks name,
mana cost, mana value, power, toughness, card types, `is_land`, `tapped`,
`produces` and `flying` for all 289 card slots in the three decks **plus every
module-level candidate**. It now reports **0 ERR**. The 52 data errors of
2026-09-03 are genuinely fixed and have not regressed.

    python -m tools.audit_cards          # run it after any deck edit

The nine remaining NOTEs are the single-cost model's known limits, each with the
reason printed (hybrid pips on Lurrus and Revitalizing Repast, `{X}` baked into
`gen` on Meathook and Debt, Damn's overload, Daxos's `*` toughness). One WARN:
Fabled Passage is modelled as a tapped dual, which is a fair reading of "put it
onto the battlefield tapped, then untap it if you control four or more lands".

**Two of the audit's own first-pass failures were bugs in the audit, not the
decks**, and are worth remembering because both are easy to repeat:

1. A case-sensitive regex failed to see the shocklands' "**I**f you don't, it
   enters tapped", so Overgrown Tomb, Godless Shrine, Sacred Foundry and
   Necroblossom Snarl were all reported as untapped-when-they-should-be-tapped.
   The tapped clause on those cards is the FALLBACK, not the rule.
2. `cards/collection` does not accept a double-faced card's COMBINED name as a
   `{"name": ...}` identifier, so "Witch Enchanter // Witch-Blessed Meadow" came
   back in `not_found` and read as a nonexistent card. Both scripts now fall
   back to a fuzzy `cards/named` lookup.

<a id="0b"></a>

## 0b. FIXED — Grist was a creature on the battlefield

> As long as Grist **isn't on the battlefield**, it's a 1/1 Insect creature in
> addition to its other types.

So Grist is a Planeswalker Creature *on the stack* — which is what makes it
trigger Rendmaw's "whenever you play a card with two or more card types" — and a
bare Planeswalker afterwards. `Card.types` has to say both and cannot.

The engine read the type line everywhere, so Grist attacked, tapped for Enduring
Vitality, and counted as a body for The Great Henge and Overwhelming Stampede.
**Under March of the World Ooze it was a 6/6 attacker.**

`engine.is_battlefield_creature(g, perm)` now answers "creature on the battlefield",
which is the same question `impending` was already asking for Overlord of the
Hauntwoods, so both go through one function. `STACK_ONLY_CREATURES` carries the
quoted clause. Gated on `cfg["battlefield_creature_types"]`, default **on**.

Measured, 4,000 paired games, flag off vs on:

| horizon | damage | win rate |
|---|---|---|
| T10 | **−0.32** [−0.43, −0.22] | −0.0003 [−0.0008, +0.0000] |
| T20 | **−0.39** [−0.54, −0.26] | −0.0003 [−0.0015, +0.0010] |

**Win rate does not move at either horizon**, which is why the default was
flipped rather than deferred: it is a correctness fix that costs a third of a
point of a proxy and nothing on the objective. `validate.py` is `+0.00` on all
six, `corr(A,B)` 0.9045 → 0.9057. Only Grist's own row in
`ablation_rendmaw.txt` (+1.61 damage / +0.0072 win) is now stale.

<a id="0c"></a>

## 0c. FIXED — candidates were never flying-tagged, so a flier scored as ground

`tag_flying.py` walked `mod.build()` only. Candidates live as module-level
constants, and `flying=name in FLYING` is evaluated at import, so **every
candidate was constructed as a ground creature**. Two were fliers:

| card | measured as | actually |
|---|---|---|
| Goldspan Dragon | 4/4 ground haste | **4/4 flying** haste |
| Caldera Pyremaw | 3/3 ground | **3/3 flying** |

This is the same shape as the 2026-09-04 `SCRIPTED_*` labelling bug: a
hand-maintained or generated set that the deck moved past. `tag_flying.py` now
walks the candidates too; `_evasion.py` gained both names and **no card in any
deck changed**, so every table and `validate.py` are untouched.

Both numbers in `CANDIDATES_2026-09-04.md` are understated as a result, and both
matter — see §0d.

<a id="0d"></a>

## 0d. Radiant Scrollwielder read the WRONG ZONE — FIXED, and it did not help

> At the beginning of your upkeep, exile an instant or sorcery card **at random
> from your graveyard**. You may cast it this turn.

`lorehold.take_turn` reads `g.library[-1]` for it, alongside Galvanoth. For
Galvanoth ("look at the top card of your library") that is right. For
Scrollwielder it is the wrong zone, and the two mechanisms are not close:

- **From the library**, it fires only when the top card happens to be an instant
  or sorcery, and it competes with Galvanoth and the whole top-setter package
  for that one card.
- **From the graveyard**, it fires *every upkeep* as long as one instant or
  sorcery is in the yard — which in a 36-spell Lorehold list is effectively
  from turn 4 onward. It is a guaranteed extra spell per turn (paid for, not
  free) and it does **not** interact with the top-setters at all.

The 2026-09-05 "Galvanoth never saw what the top-setters set up" fix was applied
to both engines. It was right for Galvanoth and irrelevant for Scrollwielder,
whose whole reading is wrong. Its candidate number is a floor of unknown depth.

`lorehold.radiant_scrollwielder()` now reads the graveyard, and models the two
details that make it a real cost as well as a benefit: **the exile is not
optional** (the card leaves the yard whether or not you pay, competing with
Arcane Bombardment, The Dawning Archaic and Mizzix's Mastery for the same pool),
and **you still pay full price**, so it adds nothing to `mv_cheated`.
`scrollwielder_exiles` and `scrollwielder_casts` are separate counters and the
gap between them is the wasted exiles.

**Still not modelled: "instant and sorcery spells you control have lifelink."**
Separating spell damage from creature damage at every `deal_pod_damage` call
site is a bigger change than the zone fix, so **any number for this card is a
floor**. The card comment claiming that clause "does nothing here — life is not
tracked" was stale and has been corrected.

**The fix tripled its firings and did not make it a better card**: 0.68 → 2.20
per game it resolves, and win rate essentially unchanged against Galvanoth. See
§0e.

<a id="0e"></a>

## 0e. The Penance slot, resolved: Caldera Pyremaw

With §0c and §0d fixed, all three contenders were measured against the same cut
with the same seeds (`run_fivedrop.py`, 6,000 paired games each, pod v3):

| card | MV | win T10 | win T20 |
|---|---|---|---|
| **Caldera Pyremaw** | 5 | **+0.0035 [+0.0012, +0.0060]** | **+0.0202 [+0.0150, +0.0257]** |
| Galvanoth | 5 | +0.0020 [−0.0002, +0.0043] | +0.0128 [+0.0078, +0.0180] |
| Radiant Scrollwielder | 4 | +0.0015 [−0.0008, +0.0038] | +0.0125 [+0.0075, +0.0178] |

Caldera is the only one significant at both horizons. Those three CIs overlap,
so they **cannot be ranked against each other** — the decision rests on the head
to head, where Penance is absent from both branches: `-Galvanoth +Caldera
Pyremaw` is **+0.0028 [+0.0012, +0.0047]** at ten turns and **+0.0093 [+0.0057,
+0.0133]** at twenty, significant at both. `pending.py` re-staged accordingly.

Galvanoth's own numbers reproduced EXACTLY on the corrected engine (+0.0020 /
+0.0128, identical to the previous staging), so the ranking is a fact about the
cards, not about the same day's engine changes.

Mechanism (`diag_fivedrop.py`, n=4,000, T20) — all three arrive in about the
same share of games, so the difference is what they do once they land:

| card | cast in | on turn | per game it resolves |
|---|---|---|---|
| Galvanoth | 13.9% | 9.6 | 0.68 free casts |
| Caldera Pyremaw | 13.8% | 9.6 | **14.5 pod damage** |
| Radiant Scrollwielder | 18.6% | **8.2** | 2.20 paid casts |

Scrollwielder is MV 4, so it lands a turn and a half earlier and in a third more
games than the other two — and it still only ties Galvanoth, because every one
of its casts is paid for in full (`mv_cheated` +0.61 against Galvanoth's +1.34).

**The proxy disagrees with the objective again.** Head to head, `mv_cheated`
goes DOWN 1.35 while win rate goes UP: Caldera cheats no mana at all. Same shape
as the top-setter finding. Follow win rate.

Caveat: the three-way ran on the v16 list, which still has Scroll Rack rather
than the staged Sunbird's Invocation. That is the same baseline Galvanoth was
measured on, so the comparison is sound — and **the two staged Lorehold changes
were measured together on 2026-09-06 and they ADD** (§0p). Caldera's own number
reproduced on that run (+0.0202 → +0.0194 ±0.0024); Sunbird's did not.

<a id="0f"></a>

## 0f. Three cards in `SCRIPTED_LOREHOLD` are not implemented as their text

Membership in `SCRIPTED_*` is a claim that the engine implements the card. These
three do not, and `check_scripted_coverage()` cannot catch it — it verifies that
every card is classified, not that the classification is TRUE.

| card | oracle | engine |
|---|---|---|
| Apex of Power | exile top 7 and cast from among them; **"if this spell was cast from your hand, add ten mana of any one color"** | `draw4` |
| Hit the Mother Lode | **Discover 10** (free-cast a nonland of MV ≤ 10), then tapped Treasures equal to 10 − that MV | flat 5 Treasures |
| Borrowed Knowledge | **"Discard your hand, then draw cards equal to…"** — a wheel | `draw2` |

Apex's ten mana is the entire card in a deck holding Rise of the Eldrazi and
Storm Herd, and Discover 10 is a free Rise of the Eldrazi off the top. Borrowed
Knowledge is a wheel, and the engine already has a `wheel` script for Reforge the
Soul. All three **understate**, which is the safe direction, but they are
labelled as if their scores were evidence about the cards.

**THE LABEL IS FIXED AS OF 2026-09-10; THE IMPLEMENTATIONS ARE NOT.** All three
moved out of `SCRIPTED_LOREHOLD` into `PARTLY_MODELLED`, so they now print in
their own table under "a HIGH score is evidence; a LOW score is NOT", each with
its specific gap printed beneath its row (§0z4, queued item 14). This section
stays **OPEN** because that is a change to what the table CLAIMS, not to what
the engine does. Note which way it cuts: Borrowed Knowledge (+0.0143 ±0.0036)
and Apex of Power (+0.0159 ±0.0031) are already significant on a fraction of
their text, so both are FLOORS and both look better than their rows, while Hit
the Mother Lode (+0.0037 ±0.0026) was the one at risk of being read as a cut.

<a id="0g"></a>

## 0g. FIXED — two "or attacks" triggers, and one token entering untapped

| card | missing clause |
|---|---|
| Grave Titan | "Whenever this creature enters **or attacks**, create two 2/2 Zombies" |
| Overlord of the Hauntwoods | "Whenever this permanent enters **or attacks**, create a tapped land token" |

Only the ETB half fired, so both were understated by everything after the turn
they landed. `engine.attack_triggers()` now runs in the declare-attackers step,
after attackers are chosen — the tokens are not themselves attacking, which is
correct. An Overlord deployed for its Impending cost is not a creature yet and
so cannot reach it, which the attacker filter already enforces.

Separately, the Everywhere token entered **untapped** where the oracle says
**tapped** — a turn of mana early, an error in the other direction. Both halves
of Overlord now go through one `make_everywhere()`.

**I filed these as "lower stakes" and was wrong about the first one.** Measured
as CFG flips, 6,000 paired games, `run_lowstakes.py`:

| fix | win T10 | win T20 |
|---|---|---|
| `attack_triggers` | **+0.0033 [+0.0018, +0.0050]** | **+0.0100 [+0.0067, +0.0135]** |
| `everywhere_enters_tapped` | −0.0008 [−0.0022, +0.0005] | +0.0002 [−0.0020, +0.0025] |

**+0.0100 win rate is not a rounding error** — it is comparable to the staged
Cauldron of Essence swap (+0.0135). Mechanism: 0.47 extra attack triggers a
game, +0.55 tokens, +1.53 final board power, +1.43 damage, and +0.048 *Rendmaw*
triggers, because Overlord's extra Everywhere tokens are extra mana and that
buys extra spells.

The Everywhere tapped fix IS as small as advertised: win rate flat at both
horizons, with `mana_floated` −0.32 and `stranded_mv` +0.35 — exactly the shape
you want, the mechanism moving and the objective not.

Both gated (`attack_triggers`, `everywhere_enters_tapped`), default on.

<a id="0h"></a>

## 0h. FIXED — "another creature you control": three cards triggered off
themselves, and it was NOT small

Suture Priest, Daxos and Elas il-Kor all read "whenever **another** creature you
control enters". So do Soul Warden, Soul's Attendant and Auriok Champion,
though theirs is "another creature" with no controller clause. `creature_entered`
took an `entering` argument and **only Guide of Souls used it**, so the other
five each gained a phantom life off their own arrival.

I estimated "one trigger per card per game, small". It is **0.85 phantom
lifegain triggers per game**, and in a deck where the trigger *is* the payoff
that compounds through Karlov's counters, Voice of the Blessed, Cliffhaven
Vampire, Marauding Blight-Priest and Starscape Cleric:

| metric | T10 | T20 |
|---|---|---|
| **win rate** | **−0.0103 [−0.0133, −0.0073]** | **−0.0130 [−0.0178, −0.0085]** |
| lifegain triggers | −0.77 | −0.85 |
| karlov counters | −0.76 | −0.78 |
| damage | −2.15 | −2.08 |

**This is the third time correcting Karlov has made the deck look worse** — the
2026-09-03 audit was −0.0163, and both had the same cause: phantom lifegain
triggers. Gated on `another_creature_clause`, default on.

The identity test matters, not name equality: Starscape Cleric's Offspring makes
a token *copy*, so two permanents can share a name and only the one that just
entered is excluded.

**Consequence: `ablation_karlov.txt` is void**, which an earlier version of
`regen_tables.sh` denied. That reasoning was right about the Grist change and
wrong about this one.

<a id="0i"></a>

## 0i. Life-loss drawbacks are free, and pod v3 made that matter

The 2026-09-04 note "LIFE DOES NOT DECIDE GAMES" was true of pod v1, where 100%
of losses were an opponent's clock. **Pod v3 is the default now**, and the
life-share of losses is 0.32 / 0.43 / 0.20 (rendmaw / lorehold / karlov). Every
card whose drawback is losing life still gets that drawback for free:

| card | uncosted drawback | current score |
|---|---|---|
| Bitterblossom | "you lose 1 life" every upkeep | **+0.0205 win — Rendmaw's #5 card** |
| Phyrexian Arena | "you draw a card and you lose 1 life" | Karlov |
| Talisman of Conviction | 1 damage to you per coloured tap | Lorehold |
| Dark Confidant | life equal to the revealed card's MV | candidate |

Bitterblossom is the one that matters: it is a top-five card in its deck, and it
pays a life every turn from the turn it lands. **Its number is a ceiling, and
now knowingly so.** The same sentence used to be true of Dark Confidant alone.

Storm Herd's X is still `cfg["storm_herd_x"] = 40` rather than your life total,
for the same reason and with the same consequence — but it is already in
`KNOWN_BLIND`, so nothing reads its number.

<a id="0j"></a>

## 0j. THE BLANK IS NOT REPLACEMENT LEVEL — the bottom of every table is taxed

Found 2026-09-06 from a question about why Blood Artist and Smothering Tithe
score the way they do. Neither is a card-data bug — `audit_cards.py` is still
0 ERR and both are correctly costed. The problem is what they are measured
*against*.

`ablation.py:blank_like()` copies the real card's **cost and nothing else**.
Three of the things it drops are load-bearing:

| dropped | blank gets | verdict |
|---|---|---|
| `priority` | `0.5` | **THE BUG.** `main_phase` is greedy on priority, so a 0.5 blank is cast only when nothing else in hand is affordable. Every real nonland card in the four lists sits between 1.0 and 10.0, so 0.5 is *below the minimum of every deck*: this is not a mediocre card, it is a card you never cast, and the real card was charged its full tempo against an opponent that never spends any. **FIXED — see the decision below.** |
| `threat` | `0.0` → `threat_of()` derives `power*0.8` or `mv*0.5` | **NOT a bug, and an earlier draft of this entry said it was.** It feeds `board_threat()` → `your_share()` (the share of removal aimed at you, and the odds a clock picks you) and gates `countered()` at threshold 4.0 — so it is load-bearing. But **13-35 of each deck's ~64 nonland cards also carry `threat=0.0`** and derive it by the identical rule, so the blank gets exactly the treatment an unremarkable real card gets. Swapping a scary card for a nondescript one genuinely does make you less of a target here. Charging the card for that is the right question. **Left alone.** |
| `power`/`toughness` | `1/1` for any creature | Thin at the top of the curve, and Blood Artist is a 0/1 so its own blank is the better body. Fixing it means inventing a vanilla P/T curve. **Left alone and said out loud.** |

`diag_threat_blank.py` re-runs an ablation against blanks that match the real
card on progressively more of that, N=15,000, same seeds and pod as the tables.
Output in `threat_blank.txt`. The `standard` row reproduces the committed table
exactly in all 28 cases, so it is the same measurement, not a different one.

**THE BIAS IS SELECTIVE, AND THAT IS THE USABLE PART.** It is proportional to
how far a card's own `priority` sits above 0.5 and is independent of what the
card does — so it is swamped on a high-output card and can be the whole score
on a low-output one. **It concentrates at the bottom of the table, which is the
half anyone reads when looking for cuts.**

The per-channel numbers below are from the pre-fix diagnostic and are kept
because they are what the decision was made on. Note across all 28 cards that
`+threat` moves the score barely at all while `+priority` moves it a lot —
Smothering Tithe −0.0002 → −0.0009 → **+0.0050**, Teleportation Circle
+0.0032 → +0.0029 → **+0.0075**. Blood Artist is the one card where the threat
channel is comparable to the priority channel, which is why it flipped hardest.

Win rate at T20, `standard` (the then-committed table) → the diagnostic's
best-matched row. **THIS IS THE DIAGNOSTIC, NOT THE OUTCOME** — its
best-matched row also matches `threat` and the body, and the decision below
deliberately fixes only `priority`. For what actually shipped see "What the
regeneration produced" further down; the two differ most for Blood Artist.

| deck | card | table | corrected | verdict |
|---|---|---|---|---|
| lorehold | Blasphemous Act | −0.0057 * | −0.0056 * | **CONFIRMED** — threat 0.0, derived 4.5 on both sides |
| lorehold | Lightning Greaves | −0.0037 * | −0.0037 * | **CONFIRMED** — unmoved |
| tivit | Time Sieve | −0.0040 * | −0.0019 | softened out of significance |
| karlov | Blood Artist | −0.0050 * | **+0.0014 \*** | **SIGN FLIP** |
| rendmaw | Blood Artist | −0.0007 | **+0.0020 \*** | **SIGN FLIP** |
| lorehold | Smothering Tithe | −0.0002 | **+0.0050 \*** | **SIGN FLIP** |
| lorehold | Sensei's Divining Top | −0.0032 | −0.0007 | → zero |
| tivit | Tamiyo's Journal | −0.0020 | −0.0003 | → zero |
| tivit | Teleportation Circle | +0.0032 * | +0.0075 * | more than doubles |
| karlov | Daxos, Blessed by the Sun | +0.0006 | +0.0045 * | hidden positive |
| lorehold | Victory Chimes | +0.0025 | +0.0043 * | hidden positive |
| lorehold | Ruby Medallion | +0.0008 | +0.0031 | hidden positive |
| tivit | Revel in Riches | +0.0007 | +0.0026 * | hidden positive |
| karlov | Mother of Runes | +0.0012 | +0.0022 * | hidden positive |

Unmoved, and therefore readable as printed: every Rendmaw card tested except
Blood Artist (Ornithopter of Paradise, Palladium / Copper / Leaden Myr, Dockside
Chef — **all `threat=0.0`**), plus Swiftfoot Boots, Vizkopa Guildmage, Pristine
Talisman, Boros Signet, lorehold's Mother of Runes, Grudge Keeper, Custodi
Squire.

Consequences:

- **Blood Artist is not worse than nothing; it is a blank.** Matched on threat
  and cast timing it is −0.0001 ±0.0014 in Karlov, which IS explainable —
  creature deaths are rare in a lifegain list, so a death-trigger drain rarely
  fires. Still a defensible cut on "it does nothing here", never on "it is
  actively hurting". Rendmaw is the control: same text, `threat=5.5` instead of
  7.0, a deck where tokens actually die, and a smaller gap.
- **Smothering Tithe is not a zero.** Threat costs it nothing; the whole
  suppression is cast eagerness. Corrected it is +0.0050 ±0.0036 win with damage
  +0.88 → **+1.73 ±0.42**. It is undervalued a second time and independently:
  `lorehold.py:1188` gives a flat +2 Treasures on YOUR upkeep, where the real
  card triggers on each opponent's draw step — 3 a round before any extra draw,
  and opponents only dodge by paying {2} every time.
- **`candidates.py` and `run_tivit_groups.py` carry the same blank.**
  `candidates.py:blank_like` is the same construction, faithfully matched to
  `ablation.py` including this. Its decision rule — "is the candidate's score
  higher than the ablation score of the card you would cut" — only cancels the
  tax when candidate and cut target have SIMILAR threat and priority. Where they
  differ it is biased toward low-threat, low-priority cards, and it reaches the
  staged swaps. `run_tivit_groups.py:blank_like` uses `priority=0.0` and no
  threat, so `tivit_groups.txt` carries the tax multiplied by group size.

### THE DECISION, and what it changed

**A replacement-level card is one you actually cast, at an unremarkable
priority.** `experiment.repl_priority(deck)` returns the median nonland
priority of the deck the blank is going into — 7.0 karlov, 5.0 rendmaw, 5.0
lorehold, 6.5 tivit. Derived from the deck, so no new constant is invented, and
inside the real distribution rather than below all of it.

It deliberately does NOT match the blank to the *tested card's* priority. That
would isolate the card's text, which is a different and narrower question than
"is this slot pulling its weight" — the one the tables exist to answer. A card
you are desperate to cast on turn two and a card you cast when convenient are
genuinely different cards, and the ablation should keep charging for that.

`threat` and the 1/1 body are unchanged, for the reasons in the table above.

Applied in `edhmc/experiment.py` and used by all three blanks that must stay on
one scale — `ablation.py`, `candidates.py`, `run_tivit_groups.py`.
**`BLANK_PRIORITY=dead` restores 0.5 exactly**, and is verified to.

**THE CACHE KEY CARRIES IT** (`_medblank` / `_deadblank`). The pre-change files
have neither suffix, so no run can pick one up and reprint numbers measured
against the old blank — the `_n{N}` lesson applied a second time.
`regen_tables.sh` was updated in the same change; its `rm -f` names the cache
literally and would otherwise have deleted nothing.

**Every table dated before 2026-09-06 (second regeneration) is void**, including
the N=15,000 set from earlier the same day. All four were regenerated.
`CANDIDATES_2026-09-04.md` is on the old scale for this reason on top of the
2026-09-04 type-line one, and `tivit_groups.txt` carried the largest version of
the error, since it scales with group size — it was re-run at the same n=3,000
so the delta is attributable to the blank alone.

### What the regeneration produced

Scores rise almost everywhere, which is the expected direction and worth
stating so it is not mistaken for a finding: the blank now costs mana, so the
blanked deck is worse and the real card scores higher. **52 of 256 cards moved
by more than their own old CI half-width.** Only two cards significant on both
sides changed sign (Bolt Bend, Counterspell), both from ~−0.0003 to ~+0.003 and
both model-blind.

| deck | card | old | new | outcome |
|---|---|---|---|---|
| lorehold | Blasphemous Act | −0.0057 * | −0.0053 * | **still the worst card in any deck** |
| lorehold | Lightning Greaves | −0.0037 * | −0.0045 * | **confirmed, and slightly worse** |
| karlov | Blood Artist | −0.0050 * | **−0.0047 \*** | **still significantly negative** |
| tivit | Time Sieve | −0.0040 * | −0.0025 | out of significance (`dmg` only) |
| rendmaw | Blood Artist | −0.0007 | −0.0001 | a clean blank |
| tivit | Tamiyo's Journal | −0.0020 | +0.0007 | a clean blank (`--`) |
| lorehold | Smothering Tithe | −0.0002 | +0.0017 | positive, still inside its bar |
| tivit | Revel in Riches | +0.0007 | +0.0025 * | now significantly positive |
| tivit | Mechanized Production | +0.0093 * | +0.0119 * | strongly positive |
| tivit | Ephemerate | −0.0011 | +0.0087 * | the §0k fix, not the blank |

**KARLOV'S BLOOD ARTIST DID NOT FLIP, and an earlier draft of this entry
predicted it would.** The diagnostic's `+body` row (+0.0014) also matched
`threat` and the 1/1 body; the shipped blank matches neither. So the card still
pays a top-tier `threat` of 7.0 — equal to Kambal — and still gives up a point
of power against a 1/1 blank, for a death trigger that rarely fires in a
lifegain list with few sacrifice outlets. **That is now a mechanism, which is
what the row was missing before**, and it makes the card a defensible cut. The
open question is no longer a harness one: it is whether `threat=7.0` is the
right number for Blood Artist in THIS list, which is a card-data judgement.

The unmeasured (`--`) count in the evaluated halves collapsed — karlov 7 → 0,
rendmaw 3 → 1, lorehold 14 → 3, tivit 9 → 1 — because a blank that is actually
cast produces a larger and more consistent difference. That is a real gain in
resolving power, not just a rescaling.

**Group ablations moved too, and one finding REVERSED.** `tivit_groups.txt`,
same n=3,000:

| group | old (cut costs) | new | note |
|---|---|---|---|
| alternate wins | 0.0047, **inside its bar** | **0.0123 [0.0040, 0.0203]** | **REVERSED** — the package is worth something after all |
| blink package | 0.0570 | 0.0730 | includes the Ephemerate fix |
| every drain | 0.1413 | 0.1427 | unchanged |
| the four signets | 0.0533 | 0.0500 | unchanged |
| extra votes | 0.0253 | 0.0230 | unchanged |

The standing claim that "the deck wins by draining, not by assembling an
alternate win" **needs revising**: cutting Revel in Riches + Mechanized
Production + Time Sieve now costs a significant 0.0123. The drains are still
worth an order of magnitude more (0.1427), so the priority ordering survives,
but "three slots buying an outcome the deck reaches more reliably by other
means" was an artifact of the blank. The extra-vote redundancy trap is
unaffected and still real: singles +0.0063 and +0.0047, sum 0.0110, against
0.0230 for the pair — still about 2x.

<a id="0k"></a>

## 0k. FIXED — Ephemerate was a proved blank, its handler dead code

Found by the above, and unrelated to it. In the `+priority` arm Ephemerate
produced **bit-identical games to its blank in all 15,000 pairs** — ±0.0000 on
win rate, damage and `removal_eaten`. That is the same signature as the four
Tivit removal spells, but those are `KNOWN_BLIND` and Ephemerate is in
`SCRIPTED_TIVIT`.

It is implemented. The implementation is unreachable:

1. `tivit_v1.py:120` gives it `priority=8` and `script="ephemerate"`.
2. **Nothing anywhere reads `script="ephemerate"`.** There is no branch for it.
3. `take_turn` runs `main_phase` twice (tivit.py:825, 829) BEFORE `activations`
   (832). `main_phase` is greedy on priority, so it casts a priority-8 {W} spell
   almost immediately — as a vanilla no-op, since step 2.
4. That removes it from hand, so `activations()`'s Ephemerate block
   (tivit.py:771) never finds it, and `g.ephemerate_rebound` is never armed, so
   `upkeep()`'s rebound (tivit.py:662) never fires either.

Both hand-written Ephemerate paths are dead. The card is a {W} blank.

This does not invalidate the blink-package group result (0.057 win rate) — the
other five members work — but Ephemerate contributed nothing to it, and its own
row was measuring cast tempo. Same shape as §0f and as the two `SCRIPTED_*`
labelling bugs: **a name in a set is a claim, and `check_scripted_coverage()`
verifies that a card is CLASSIFIED, not that its classification is TRUE.**

**FIXED 2026-09-06**, in two parts, because one alone would not have worked:

1. `resolve()` now has an `ephemerate` branch that blinks and arms the rebound,
   so the card works wherever it is cast. The `activations()` block is deleted —
   it could never fire, and it gated on `commander_cast` rather than on Tivit
   being present, so after a wipe it would have thrown the card away.
2. `main_phase` no longer casts a ONE-SHOT blink with nothing to blink
   (`"blink" in tags and not is_permanent and not g.has(commander)`). Without
   this the greedy policy simply pitched it on turn one. The permanent blinkers
   are engines worth deploying pre-commander and are untouched by the gate.

Effect: from bit-identical-to-a-blank to **+0.0095 ±0.0043 win rate at T20**
(n=4,000). `validate.py` is `+0.00` on all nine with `corr(A,B)` 0.9069
unchanged. **The tivit table was regenerated**; the other three engines are
untouched by this, and that claim is checked rather than assumed — the change is
confined to `edhmc/tivit.py`.

<a id="0l"></a>

## 0l. FIXED — Erebos, Bleak-Hearted: three errors on one card

Queued work item 8 named one of them. Verifying the card against Scryfall found
the other two, so all three were fixed and measured separately.

> Indestructible
> As long as your devotion to black is less than five, Erebos isn't a creature.
> Whenever another creature you control dies, you may pay 2 life. If you do,
>   draw a card.
> {1}{B}, Sacrifice another creature: Target creature gets -2/-1 until end of turn.

1. **It was a creature from the turn it landed.** A {3}{B} 5/6 attacking in the
   early game, and a **6/6 attacker under March of the World Ooze** — the same
   shape as the Grist bug in §0b. Unlike Grist this is conditional on BOARD
   STATE, so the `impending` sentinel could not express it: devotion rises and
   falls as permanents enter and die, and the question has to be re-asked at
   every call site. `engine.devotion(g, color)` and
   `DEVOTION_CONDITIONAL_CREATURES` now do that inside
   `is_battlefield_creature`, so the five places the Grist fix already covered
   (combat, Enduring Vitality, The Great Henge, Overwhelming Stampede, and the
   attacker filter) get it for free.
   **Erebos is legitimately a creature for 0.05 turns a game, against the 0.38
   it was getting** — devotion to black reaches five in this list rarely, so
   seven-eighths of its creature-turns were illegitimate.
2. **THE ENGINE GAVE IT DOCKSIDE CHEF'S ABILITY.** The branch read
   `Erebos / Dockside Chef / Grim Backwoods style sac-for-card, once/turn`.
   That is Dockside Chef's card, verbatim ({1}{B}, Sacrifice an artifact or
   creature: Draw a card) and it is not on Erebos at all. Erebos's draw is a
   TRIGGER off deaths that were going to happen anyway — no sacrifice, no mana,
   no once-per-turn — which in a deck that loses a dozen tokens a game is a
   different card. Its own activated ability is "target creature gets -2/-1",
   model-blind against a blocker count. Gated `erebos_death_draw`.
3. **It was never tagged indestructible**, so it ate removal it cannot eat.
   See §0n: fixing this by hand was itself a mistake.

Measured as cumulative CFG flips, N=15,000 paired games, `run_erebos.py`:

| fix | win T10 | win T20 |
|---|---|---|
| `devotion_creature_types` | **−0.0025 [−0.0033, −0.0016]** | **−0.0047 [−0.0064, −0.0030]** |
| `erebos_death_draw` | +0.0006 ±0.0007 | +0.0023 ±0.0021 |
| `indestructible` | +0.0001 ±0.0002 | +0.0007 ±0.0012 |
| **ALL THREE** | **−0.0018 ±0.0009** | −0.0018 ±0.0024 |

**Two of the three point in opposite directions**, which is why the combined
number is the one to read. Taking the phantom body away costs the deck half a
point of win rate at twenty turns; the death trigger (0.28 draws a game for 0.56
life) and the indestructibility give about half of it back. All three default
on. `validate.py` is `+0.00` on all nine with `corr(A,B)` 0.9069 → 0.9053.

**THIS IS THE FOURTH TIME A CORRECTION HAS MADE A DECK LOOK WORSE** — after the
2026-09-03 Karlov audit (−0.0163), the "another creature" clause (−0.0130) and
Grist. Three of the four were a trigger or a body the deck was never entitled to.

**The card is now a cut candidate, which it was not before.** Its own ablation
row went from +0.61/+0.64 damage and +0.0054 ±0.0025 win (`both`) to
−0.18/+0.05 and +0.0033 ±0.0026, signal `FLIP` — its damage contribution is
now NEGATIVE at ten turns, and its win-rate contribution is barely above the
deck's ±0.0021 noise floor. It was scoring on a body it is not allowed to have.

**`ablation_rendmaw.txt` was regenerated.** The useful part of that: the deck's
baseline moves, but **ZERO of 64 cards moved by more than their own old CI
half-width.** Erebos's own row is the only material change. `erebos_life_paid`
is a cost this model underprices (§0i), so the death-draw arm is a CEILING;
`erebos_life_floor` (10) is the only thing standing in for declining to pay and
it is a judgement call.

<a id="0m"></a>

## 0m. FIXED — AN EXTRA TURN GAVE THE OPPONENTS AN EXTRA ROUND

Found 2026-09-06 from a question about Time Sieve, which the table scored at
**−0.0025 ±0.0026** — slightly negative, and inside its bar. The question was
the right one, and it is the "when a result is surprising, the engine is the
first suspect" rule paying off for the fourth time.

    Time Sieve  {U}{B}  "{T}, Sacrifice five artifacts: Take an extra turn
                        after this one."
    Tivit       "Whenever Tivit enters or DEALS COMBAT DAMAGE TO A PLAYER,
                council's dilemma ... While voting, you may vote an additional
                time."

In a four-player game you cast two votes and the pod casts three, and **both
halves of the dilemma make an artifact**, so an adversarial pod can change the
mix and not the count. One Tivit attack is exactly five artifacts — exactly Time
Sieve's cost, with nothing spare — and the Sieve untaps on the turn it just
bought. `attack → 5 tokens → sacrifice → extra turn → untap → attack` is
unbounded. The pair should be one of the best things this deck does.

Three bugs, in increasing order of how much they mattered:

1. **`sieve_taps`** — the cost is a tap of Time Sieve itself, so the ability is
   ONCE PER TURN. The engine ran it up to `sieve_cap` (10) times in one turn and
   then declared the game won on reaching the cap. Ten activations a turn is
   nine more than the card allows, and the cap needed fifty tokens in one window
   so it almost never fired. (Artifacts have no summoning sickness, so the {T}
   is live the turn it lands; only `tapped` gates it.)
2. **`extra_turns_chain`** — `simulate` zeroed `g.extra_turns` before taking
   them and never re-read it, so an extra turn generated DURING an extra turn
   was silently discarded. One extra turn per real turn is exactly what Time
   Sieve grants, so **the loop was truncated to a single step, every time.**
3. **`extra_turns_skip_opponents`** — `take_turn` ends with the three
   opponents' whole round: they develop a board, cast removal, chip you for
   incidental damage and check their kill clocks. It ran at the end of EXTRA
   turns too, so every extra turn you took handed the pod a free extra round.
   That is the opposite of what an extra turn does. **`lorehold.take_turn`
   already had this right** — its extra turns run untap/miracle/main/combat with
   no opponent block at all — so the two engines modelled one concept in
   opposite directions, and only one of them was wrong.

Cumulative CFG flips, n=6,000, T20, `diag_time_sieve.py` part C:

| fix | win rate | note |
|---|---|---|
| `sieve_taps` | **+0.0028 ±0.0026** | a RESTRICTION that helped, which is the tell |
| `extra_turns_chain` | +0.0000 (chain length only) | worthless until #3 |
| `extra_turns_skip_opponents` | **+0.0510 ±0.0059** | the whole effect |
| **all three** | **+0.0538 ±0.0062** | deck win rate 0.343 → 0.397 |

Read the ordering: making the Sieve **weaker** per turn *helped*, because each
extra turn was a net liability; and chaining more of them was worth nothing
until the pod round was removed, after which it became valuable. That is the
mechanism, stated three ways.

**On the minimum board the claim needs** — Tivit + Time Sieve + six lands,
opponents given unkillable life so the turn structure is visible over twenty
turns (part A):

| engine | turns | extra | pod rounds | sieve activations | longest chain | ended |
|---|---|---|---|---|---|---|
| before | 16 | 10 | **16** | 11 | 3 | **loss** |
| after | 16 | 14 | **2** | 14 | **14** | **win** |

**In real games** (part B, n=6,000, T20), Time Sieve is cast in 20% of games and
activates in 12%. Conditional on activating at least once, win rate was 0.389
against 0.337 when it did not — i.e. the two-card infinite-turn combo was worth
five points. It is now **0.723 against 0.351.**

Consequences:

- **`ablation_tivit.txt` and `tivit_groups.txt` were regenerated.** Ten of 64
  cards moved by more than their own old half-width and **Time Sieve is the only
  sign flip: −0.0025 ±0.0026 (`dmg`) → +0.0344 ±0.0034 (`both`)**, which makes
  it joint-best in the deck with Sol Ring (+0.0379 ±0.0044, CIs overlapping)
  rather than the cut candidate §0j had named.
- **Expropriate went from a proved blank to a real card**: −0.0004 ±0.0008
  (`--`) → +0.0127 ±0.0022 (`both`). It was paying a pod round per turn it
  bought. Plea for Power is +0.0097. Every extra-turn source was affected, not
  just the Sieve.
- **THE STANDING "ALTERNATE WINS ARE WORTH NOTHING" FINDING IS NOW FULLY
  RETRACTED.** Cutting Revel in Riches + Mechanized Production + Time Sieve
  costs 0.0123 → **0.0520 [0.0420, 0.0617]**, a 4.2x move and the only group
  that shifted materially. It goes from last of seven groups to fourth, ahead
  of both the extra-vote pair (0.0213) and the artifact drains (0.0257). The
  drains are still the biggest group (0.1233) so **the deck still wins by
  draining** — but "three slots buying an outcome the deck reaches more reliably
  by other means" is dead, and so is §0j's "cut Time Sieve, not the package".
- The five drains all came DOWN 13-21%. That is arithmetic, not a finding: the
  baseline win rate rose from 0.343 to 0.397, so any one card is a smaller share.

Still deliberately not modelled, and said out loud: **Time Sieve eats only TOKEN
artifacts**, never the real ones `artifact_count()` can see (Sol Ring, the
signets, the artifact lands). Those are legal fuel, and a pilot would not feed
them to a loop that has to run again next turn — but it is the conservative
direction. And extra turns still count against the horizon, which is now the
ONLY bound on the loop; that is a choice, not a bug, and it means a real
infinite-turn lock is truncated at `turns`.

<a id="0n"></a>

## 0n. Hand-tagging one card is the bug CLAUDE.md warns about, and I did it

Fixing Erebos's indestructibility meant setting `indestructible=True` on one
card by hand. CLAUDE.md: *"Do not hand-tag a keyword from memory: ablation
compares each card against a blank in the same list, so a partial tag list
biases the whole table toward whatever got tagged."* Checked against Scryfall,
the four lists hold **four** statically indestructible cards, and two of them
are ones nobody would think of:

| card | deck | note |
|---|---|---|
| Erebos, Bleak-Hearted | rendmaw | the one that prompted this |
| Darkmoss Bridge | rendmaw | a LAND |
| Darksteel Citadel | rendmaw | a LAND |
| Heliod, Sun-Crowned | karlov candidate | the one pre-existing hand-tag, and it was right |

So `tag_flying.py` now generates an `INDESTRUCTIBLE` set alongside `FLYING`,
reading the same `keywords` array, over **all card types rather than creatures
only** — and every `C()` and `L()` in the four deck modules derives the flag
from it. Karlov's `C()` lost its hand-passed `indestructible` argument.
`audit_cards.py` checks the field, which it did not before, so this class of
gap now fails the audit: **0 ERR across 377 card slots.**

Cards that GRANT indestructible (Boros Charm, Heroic Intervention, Dawn's Truce,
Plaza of Heroes) or have it CONDITIONALLY are deliberately absent — a static tag
would be a lie. **Voice of the Blessed has indestructible with ten or more
+1/+1 counters and that is NOT modelled**; ten is reachable in the Karlov list.
Its flying at four counters already lives in `opponents.flying_of()`, so that is
where the rest of it belongs.

The two lands are **provably inert**: `spot_removal` and `ae_removal` both
exclude `is_land`, and `board_wipe` only touches creatures. Verified rather than
argued — stripping the tag from the two lands reproduces the Rendmaw baseline
BIT-IDENTICALLY over 2,000 paired games. Tagged anyway, because
`Card.indestructible` was "inert today" too, right up until Erebos.

<a id="0o"></a>

## 0o. `candidates.py` measured a SECOND COPY of a card already in the deck

Found while re-measuring Goldspan Dragon. `candidates.py` answers "what does
this card add over a replacement-level slot" by putting it in a victim slot of
`build_pending(deck)` — and `build_pending` applies the STAGED changes. Caldera
Pyremaw was a candidate on 2026-09-04 and was staged into the Lorehold list on
2026-09-05, and nothing noticed: running it now builds a **101-card,
singleton-illegal deck with two Caldera Pyremaws** and prints the marginal value
of the duplicate under the heading "value over a blank".

`add_value()` now refuses outright, and `DECKS["lorehold"]` no longer lists it.
Same shape as the `SCRIPTED_*` sets and `tag_flying.py`'s candidate gap: a
hand-maintained list the deck moved past. **One number was produced against this
bug during the 2026-09-06 session and discarded**; no committed number depends
on it, because `CANDIDATES_2026-09-04.md` predates the staging.

<a id="0p"></a>

## 0p. The two staged Lorehold changes ADD — closes queued item 0b

    C = -Penance     +Caldera Pyremaw       staged 2026-09-05
    S = -Scroll Rack +Sunbird's Invocation   staged 2026-09-04

Each was measured against the v16 list and never against the other, and the
reason to doubt they add was MECHANICAL, not statistical: both are additions to
the same top-heavy curve (MV 5 and MV 6, replacing a two-drop and a free spell),
Sunbird's alone already cost +4.28 stranded MV, and **both cuts are top-setters**
— Penance and Scroll Rack are both in `lorehold.TOP_SETTERS` — so cutting two at
once could plausibly have been worth more than the sum in either direction.

A difference of two differences needs its own design, so this is a 2×2 factorial
on common random numbers with all four legs shuffled on the same seed, which
makes the interaction a paired quantity too. `run_lorehold_pair.py`, N=30,000 per
cell (twice the tables: an interaction has roughly twice a main effect's
variance, and 15,000 would have left exactly the one number this exists to
produce ambiguous).

| win rate | T10 | T20 |
|---|---|---|
| C alone | +0.0028 ±0.0011 | +0.0194 ±0.0024 |
| S alone | +0.0019 ±0.0012 | +0.0146 ±0.0028 |
| **BOTH** | **+0.0047 ±0.0016** | **+0.0362 ±0.0035** |
| **INTERACTION** (CS−C−S+A) | **+0.0000 ±0.0008** | **+0.0022 ±0.0020** |
| Caldera GIVEN Sunbird's | +0.0028 ±0.0012 | **+0.0216 ±0.0026** |
| Sunbird's GIVEN Caldera | +0.0019 ±0.0013 | **+0.0168 ±0.0029** |

**They add.** The interaction is exactly zero at ten turns and, if anything,
slightly SUPER-additive at twenty — the opposite of the concern. The marginal
rows are the decision: each change is worth its slot with the other already in.

**Both predicted costs are real and both are outweighed**, which is the part
worth keeping:

- `stranded_mv` **compounds**: +5.40 (C) and +7.72 (S) alone, +13.72 together
  against +13.12 additive, an interaction of **+0.60 ±0.18**. The two-six-drops
  worry was correct about the mechanism.
- The two cards **do compete for miracles**: `miracles_cast` interaction
  **−0.018 ±0.008**, sub-additive, as two top-setter cuts should be.
- They are outweighed by the damage channel (+0.30 ±0.24) and by Sunbird's firing
  slightly more often with Caldera in (`sunbird_casts` +0.020 ±0.010).

### One staged number reproduced and the other did not

**Caldera reproduced**: +0.0202 → +0.0194 ±0.0024 at T20. **Sunbird's did not**:
+0.0215 → +0.0146 ±0.0028 at T20, and +0.0077 → +0.0019 at T10 with disjoint
bars. Its staged measurement is from 2026-09-04 and predates a great deal of
Lorehold engine work; Caldera's is from 2026-09-05 and postdates most of it.

**The obvious explanation was tested and is WRONG.** Both cuts are top-setters,
and the 2026-09-05 top-setter POLICY fixes made top-setters materially better
(Library of Leng: miracled 43% → 80%, deck win 0.205 → 0.219), so cutting one
should have become more expensive. Measured on today's engine against the same
blank the tables use, N=15,000, v16 as printed:

| card | win T10 | win T20 |
|---|---|---|
| Scroll Rack | −0.0007 ±0.0014 | **−0.0093 ±0.0032** |
| Penance | +0.0003 ±0.0014 | **−0.0079 ±0.0033** |

Scroll Rack is still worth −0.0093, essentially the −0.0100 it ablated to on
2026-09-04. **The cut is exactly as cheap as it was**, so the decay is in
Sunbird's Invocation's own contribution and is NOT attributed. Do not invent a
mechanism for it. (Note in passing that Penance at −0.0079 is no longer the
−0.0100-class worst card it was described as either, and that the two are now
within a bar of each other.)

### And a conditional number that was printed as an unconditional one

The ledger justified Sunbird's with "fires 3.6 times a game for an average free
spell of MV 3.8". `sunbird_triggers` now exists alongside `sunbird_casts`, and
the two are very different numbers:

| | per game | conditional on it resolving |
|---|---|---|
| resolves at all | — | **13.0% of games** |
| triggers | 0.79 | 6.06 |
| free casts | **0.52** | **4.00** |
| avg MV of the free spell | — | 3.77 |

So the old figure was the CONDITIONAL one and is roughly right as such (4.00 and
3.77 today), but the entry read as though 3.6 free spells arrived every game,
when the card is MV 6 and lands in one game in eight. Corrected in `pending.py`.
34% of its firings find nothing at all — off a two-drop it reveals two cards and
needs an MV≤2 nonland among them, which is the "worth far more off the top of the
curve" point stated as a metric rather than as prose.

`sunbird_triggers` is metric-only and was verified behaviour-preserving: all four
decks' baselines are bit-identical across it, so no table moved.

---

<a id="0q"></a>

## 0q. HAND-MAINTAINED NAME SETS — the failure mode this repo keeps having

**Status: the third instance was caught before it bit, and is now CHECKED.
The general problem is not solved and cannot be, only detected.**

Three times now, in three files, the same shape: a list of card names written
by hand, and a deck that moved past it. The numbers were never wrong. The
*label* was wrong, and the label is the part that tells you whether a number
means anything.

| set | consequence | when |
|---|---|---|
| `ablation.SCRIPTED_RENDMAW` / `_LOREHOLD` / `_KARLOV` | five fully-implemented cards printed under MODEL-BLIND, where a low score is supposed to mean "the model cannot see this" | 2026-09-04 |
| `tag_flying.py`'s hand-written deck dict | Goldspan Dragon and Caldera Pyremaw measured as GROUND creatures | 2026-09-05 |
| `azusa.LAND_ENABLERS` | a landfall card not in the set is deployed AFTER the land drops, so it does nothing on the turn it lands and quietly scores low — with nothing anywhere saying so | caught 2026-09-07 |

### Why the third one is the nastiest of the three

The first two produce a *visibly* wrong label — a card sitting in the wrong
table, or a flier with no evasion. `LAND_ENABLERS` produces a **plausible
number**. A landfall payoff deployed one step too late still gets cast, still
does something on later turns, and simply scores lower than it should. There
is no artefact to notice. It looks exactly like a mediocre card.

This is the same category as the 2026-09-05 `tag_flying` bug, but without the
tell — and it matters more here than it looks, because the land-sequencing
work of 2026-09-07 measured the cost of exactly this ordering mistake at
**0.074 win rate** when it applied to the whole deck at once.

### What was done

`edhmc/azusa.py:check_land_enabler_coverage()`, which runs **at import**:

- It scans the SOURCE of `land_entered`, `land_drops_for_turn`,
  `playable_lands` and `land_died` for `self.has("...")` / `self.count("...")`.
  Those four methods are the definition of "this card changes how many lands
  I may play, where from, or what happens when one enters" — so they, not a
  human, are the authority.
- Any name found there and missing from `LAND_ENABLERS` raises with the list
  and the reason.
- It currently derives **16 names with no unmatched leftovers**: the set is
  exactly the derived set, not a superset someone stopped pruning.
- **It was verified to fail.** Removing `Lotus Cobra` from the set makes it
  raise. A check that cannot fail is worse than no check, because it reads
  like assurance — and this file already contains one instance of that
  mistake (`check_scripted_coverage` verifies that every card is CLASSIFIED,
  never that the classification is TRUE; see 0f).

### What is still NOT checked, and cannot easily be

- **`LAND_ENABLERS` membership is still a judgement about ORDER.** The check
  proves every land-relevant card is in the set; it cannot prove the set
  should not contain more. Avenger of Zendikar is in it because deploying it
  before the lands beats making one extra Plant — that is a piloting
  decision, argued in the comment at its definition, not a measurement.
- **`SCRIPTED_*` still verifies classification, not truth** (0f).
- **Nothing checks the other five engines for the same ordering hazard.**
  `shilgengar.aristocrats_step` was the obvious next suspect and it was the
  right one — see **0r**, where the same shape of unstated policy decision
  turned out to be worth 0.034 win rate. There is still no coverage check for
  a sacrifice policy, because unlike `LAND_ENABLERS` there is no method whose
  source IS the definition. What there is instead is a diagnostic that was
  verified to fail when the mechanism is removed, which is the weaker but
  available version of the same idea.

**The rule to carry forward: when you add a hand-maintained name set, add the
check in the same change, and prove the check fails.**

---

<a id="0r"></a>

## 0r. FIXED — Shilgengar's own ability fired ZERO times in 3,000 games

**Status: fixed and default-on. `ablation_shilgengar.txt` regenerated; the
first table, published earlier the same day, is void.**

The commander is `Sacrifice another creature: create a Blood token, or Blood
equal to its TOUGHNESS if it was an Angel` plus `{W/B}{W/B}{W/B}, sacrifice
six Blood: return each creature card from your graveyard to the battlefield`.
The deck is half Angels. `blood_made` averaged **0.10 a game** and the
six-Blood ultimate fired **zero times in 3,000 games**.

Two causes, both in the POLICY rather than in any card's text — and the
ablation table could not tell you either of them, because the aristocrats rows
scored negative and read as a verdict on the cards.

1. **The sacrifice policy would only ever eat 1/1 Spirit tokens** — never a
   real card, on the stated grounds that feeding a live Lyra Dawnbringer to
   Shilgengar was a pilot judgement call the model should not attempt. But
   Spirit tokens only exist once an Angel has *already* died (Requiem Angel,
   Bishop of Wings), so the engine was starved by construction. It is another
   instance of a conservative-looking policy turning out to be an assertion
   that a card does nothing.
2. **No mana was ever held back for the ability.** `main_phase` is greedy and
   `activations()` runs after it, so even when six Blood existed the {3} did
   not. Measured separately below, and it is a fifth of the total.

### Why the new policy is arithmetic and not a judgement call

The ultimate returns **the Angel you just sacrificed to pay for it**. A
nontoken sacrifice is a LOAN, not a cost — and `activations()` runs after
combat, so the bodies have already attacked, and `take_turn` clears summoning
sickness at the start of the next turn. So the line is taken only when it
COMPLETES THE ULTIMATE THIS TURN, and REAL CARDS SORT AHEAD OF TOKENS as
fodder, which is the exact reverse of the old policy: the card comes back and
the token does not.

Deliberately still conservative, so the number is a floor: it never banks
Blood across turns (a pilot holding five Blood and a Lyra sometimes would),
and the death triggers the sacrifices set off — Blood Artist, Grim Haruspex,
Pitiless Plunderer — are not counted as part of the case for taking it.

### FINALITY COUNTERS, without which the engine plays a card that is not printed

"Return each creature card ... **with a finality counter on it**" — if such a
creature would die again it is exiled instead of hitting the graveyard.
Without that, sacrifice–return–sacrifice–return is an infinite value loop on
one Angel. `yard_creatures()` is the filtered pool that every recursion effect
in the deck now reads (the ultimate, Reya Dawnbringer, Priest of Fell Rites,
Sun Titan, Emeria Shepherd).

**The first version of that check was vacuous and passed anyway**, which is
worth recording because it is exactly what §0q is about. Casting the ultimate
twice in a row proves nothing: the creatures it returned are on the
BATTLEFIELD and the graveyard is empty, so the second cast has nothing to
return whether finality works or not. The real test feeds the returned card
BACK to Shilgengar first — and then it failed for a second reason, the {3}
being unaffordable, which made a mana check look like a passing finality
check. `diag_shilgengar_ult.py` closes both, and was verified to FAIL when
`yard_creatures` is stubbed out.

### Measured (`diag_shilgengar_ult.py`, 4,000 paired games, T20)

| flip | win rate |
|---|---|
| the fodder policy, with no mana held back | **+0.0267 ±0.0067** |
| the mana reserve on top of it | **+0.0075 ±0.0048** |
| **both** | **+0.0343 ±0.0079** |

Deck win rate **0.208 → 0.242**. The ultimate now fires in **39.5% of games**,
returning 4.23 creatures when it does; `blood_made` 0.13 → 3.20.

**Do not read the "win rate 0.423 when it fires vs 0.124 when it does not"
split in PART B as an effect size.** Firing it needs the commander alive, six
Blood of fodder and {3} to spare, all of which are true in games you were
already winning. The paired flips above are the causal number and they are a
third of that.

### What this does NOT settle

The negative aristocrats rows in the first table were a fact about the policy
at least as much as about the cards. The regenerated table is the first one in
which they are a fact about the cards, so they should be read from scratch
rather than diffed against the old ones.

### `shilgengar_ult_min_gain` is a LOCAL OPTIMUM at its default, not one end of a slope

`KNOWN_ISSUES.md` 0t (below) tested raising it — 2, 3 and 5 are all worse,
monotonically. That is only half the question: `run_mingain_sweep.py` tested
0 and −2, which relax rather than tighten the "must be a net gain" gate.
Relaxing it fires the ultimate MORE (0: +0.45 ults, +0.62 reanimated a game)
and is WORSE (0: **−0.0321 ±0.0044**; −2: −0.0327 ±0.0044, both significant).

So the default of 1 sits at a peak, worse in *either* direction — a shuffle
that returns as many creatures as it sacrifices, or a small net loss, both
cost more in tempo and board than the extra Blood-fed reanimations return.
Both bounds are now measured; the knob is not a candidate for further tuning.

---

<a id="0s"></a>

## 0s. Azusa's land animation: TESTED AT LAST, and the pillar is not the story

**Status: all four effects implemented, each behind its own flag, all
default-on. `ablation_azusa.txt` regenerated; the first table is void.**

The first table scored Sylvan Awakening +0.0017 and Rude Awakening +0.0019,
both inside their bars, and CLAUDE.md recorded the honest reading: "this
pillar of the deck is untested, not disproved." Four things were wrong.

1. **Sylvan Awakening was a turn-scoped flag**, so its lands attacked as
   fabricated 2/2s that were never on the battlefield — which meant attacking
   with them TAPPED NOTHING and the same lands still paid for the postcombat
   main phase. Its real duration is UNTIL YOUR NEXT TURN, so its lands are
   also still creatures during the pod's round and count as blockers.
2. **Rude Awakening was implemented as its untap mode only.** The animate mode
   and the entwine did not exist — and entwining (untap every land, then
   animate them) is how the card actually ends a game.
3. **Nissa, Worldwaker had no abilities**: a five-mana Planeswalker that was a
   0/0 permanent doing nothing at all.
4. **Nissa, Vastwood Seer never transformed.** Only her ETB Forest search was
   modelled, so in a deck that reaches seven lands around turn five she stayed
   a 2/2 for the rest of the game and her entire back face was unreachable.

Also corrected, with no flag because it is unobservable unless a land is a
creature: **lands now enter summoning sick.** Every land call site passed
`sick=False`, which was harmless while no land was ever a creature. The single
visible consequence is that Dryad Arbor can no longer attack the turn it is
played, which it never could.

### THE ANSWER IS THAT THE ANIMATION IS NEARLY A BLANK AND THE NISSAS ARE NOT

`diag_azusa_animation.py`, 4,000 paired games, T20, flips applied cumulatively:

| flip | win rate |
|---|---|
| `land_animation` — a real continuous effect, and attacking taps it | +0.0003 ±0.0008 |
| `animated_lands_block` — Sylvan lasts until your next turn | +0.0013 ±0.0011 |
| `rude_awakening_modes` — the animate mode and the entwine | −0.0008 ±0.0019 |
| **`planeswalker_abilities` — both Nissas** | **+0.0210 ±0.0068** |
| **all four** | **+0.0217 ±0.0071** |

**Essentially all of it is the two Nissas.** The three animation fixes together
are inside their own bars, and that is now a RESULT rather than an absence: the
mechanism is implemented, it is measured, and it is small. The reason is
legible in the counters — the animation is worth **9.24 marginal damage a
game** in a deck whose damage runs into the thousands, because Scute Swarm's
doubling dwarfs it. **This deck does not need more damage. The animation sells
it the one thing it already has most of.**

The Nissas sell it what it is actually short of, and it is the same finding the
land-sequencing work reached from the other direction: **+1.29 landfall
triggers and +0.36 lands played a game.** The 2026-09-07 table already
established that this deck is CARD-limited rather than drop-limited, and Nissa,
Sage Animist's +1 is a card or a free land every single turn.

### Reading the rows honestly

- **The `legacy` row's zeroes in PART B are "not measured", not "never
  happened".** The old engine did attack with its lands; none of these
  counters existed to see it. PART C is the comparison.
- **The damage column here is unusable**, exactly as the table's own header
  says: CIs of ±1,765 against a point estimate of +731.
- **Indestructible and reach are carried and cannot matter.** `spot_removal`
  and `board_wipe` both exclude lands, so nothing the pod does can kill an
  animated land, and this engine never blocks with your creatures. Sylvan
  Awakening's indestructible clause is worth exactly zero here. That is a fact
  about the pod rather than a gap in it — but it does mean the card's row is
  not a measurement of the whole card.
- **Both Nissas are a FLOOR.** No opponent ever attacks a Planeswalker,
  because the pod's combat is a float rather than a set of attackers, so
  loyalty only ever goes up and the ultimates arrive sooner than they would at
  a real table. Pulling the other way, Nissa, Sage Animist's −2 is never taken.
  Spot removal is the only pressure on either.

### Planeswalker loyalty exists now, scoped to this engine

`PLANESWALKERS` holds starting loyalty and `Permanent.counters` holds the
current value, so no field was added to a dataclass five other engines share.
`check_planeswalker_coverage()` raises at import if a Planeswalker in the deck
has no entry — the §0q rule applied in the same change, because a walker
missing from that table enters at zero loyalty and silently does nothing,
which is the exact state both Nissas were in.

**`Nissa, Worldwaker` moved from `KNOWN_BLIND` to `SCRIPTED_AZUSA`** in the
same commit. Her old entry read "planeswalker activated abilities — nothing in
this project tracks loyalty", which stopped being true; leaving it would have
printed an implemented card under MODEL-BLIND, which is §0q's first instance
verbatim.

---

<a id="0t"></a>

## 0t. THE MANA RESERVE — how much to hold, and what holding it actually costs

**Status: both defaults CONFIRMED by measurement rather than by the printed
cost they were copied from. One standing claim is now supported on both sides
instead of one. No default changed.**

Two engines decline to spend mana in their main phase so a later ability is
affordable, and both numbers had been set to match a printed cost rather than
measured:

| engine | knob | held for | exposed to removal? |
|---|---|---|---|
| lorehold | `miracle_reserve` = 2 | three miracle windows on the opponents' upkeeps | **yes** |
| shilgengar | `shilgengar_ult_reserve` = 3 | the six-Blood ultimate in `activations()` | no |

The asymmetry is structural and it is why the question has to be asked per
engine. Shilgengar's reserve is spent or released within the same turn —
`activations()` runs between combat and the postcombat main phase, and that
phase is passed no reserve at all. Lorehold's is held through the whole turn,
and the windows it is held for open only **after** `opponents_act`, so a
commander answered in between takes the windows with it.

CLAUDE.md's standing claim was "raising `miracle_reserve` above 2 makes it
worse — the default is right." That is evidence about RAISING it. Nobody had
lowered it.

### The waste is real, and larger than expected

At the default, per game (N=15,000, `run_reserve_sweep.py` PART A):

    turns the reserve was held             3.73
    mana declined over those turns         7.45
    turns it bought NO off-turn miracle    2.03   (54% of them)
    mana declined for nothing              4.06   (54% of it)
    ...of which the commander was GONE     0.87 turns
    mana held beyond the miracle's cost    0.38

So **more than half the mana Lorehold declines to spend buys nothing**, and on
0.87 turns a game — 23% of the turns it holds — the commander it was holding
for is dead before the window opens. That is the "do not withhold for a play
that gets answered" intuition, measured, and it is correct as a fact.

### And removing it gains NOTHING, for a reason worth knowing

| `miracle_reserve` | win rate | `mv_cheated` |
|---|---|---|
| 0 | −0.0003 ±0.0052 | −1.02 ±0.36 * |
| 1 | −0.0003 ±0.0042 | −0.43 ±0.31 * |
| `"need"` | −0.0001 ±0.0014 | −0.05 ±0.11 |
| **2 (default)** | — | — |
| 3 | **−0.0055 ±0.0042 \*** | −0.34 ±0.31 * |

**THE RESERVE IS NOT COSTING THE DECK SPELLS. IT IS PARKING MANA THE DECK
CANNOT SPEND ANYWAY.** Dropping it to zero moves `spells_cast` by **+0.08**
while `mana_floated` falls **3.0** — the released mana goes almost entirely
back into the float, not into casting. There is nothing to win back, which is
why win rate does not move however wasteful the holding looks.

It IS buying something: `miracles_cast` 2.78 → 3.13 and `mv_cheated` +1.02 at
2 versus 0. It simply does not convert, which is the same shape as the
standing top-setter finding — this deck's stated primary metric and its
objective disagree about the whole miracle plan.

**Three is where it starts costing real spells, and that is exactly where win
rate turns significantly negative**: `spells_cast` −0.31, `stranded_mv` +2.58,
win −0.0055 ±0.0042. Note what it does to the proxy on the way: **it casts
MORE miracles (+0.063) and LOSES games.** That is the sharpest
proxy/objective disagreement in the project so far, because here the proxy is
the very quantity the knob exists to serve.

**The rule that generalises: a reserve is free exactly while it is smaller
than the mana the deck could not spend anyway.** The diagnostic is not "how
often is it wasted" — it is `spells_cast`. That number is flat at 2 and
negative at 3, and win rate follows it and not the waste counter.

### `miracle_reserve="need"` — exact, and a wash

`miracle_need(g)` is 2 off a bare Lorehold, 1 with Artist's Talent and 0 with
Molecule Man, so the constant 2 over-holds whenever either is out.
`miracle_reserve="need"` holds the real number. It removes all 0.38 mana of
over-holding at no measurable cost (win −0.0001 ±0.0014) — and no measurable
gain, so **the default stays at 2** and the option is documented rather than
adopted.

One detail in it is worth keeping, because it is the same mechanism one level
down: holding exactly what you need costs **0.01 miracles a game**, because
the cost-reducer can be answered between your main phase and the window, and
then the need is 2 again and you held 1. Being exactly right about a number
that can change under you is slightly worse than being generous about it.

### Shilgengar: correctly sized, and for a checkable reason

| `shilgengar_ult_reserve` | win rate |
|---|---|
| 0 | −0.0056 ±0.0026 * |
| 1 | −0.0041 ±0.0023 * |
| 2 | −0.0023 ±0.0017 * |
| **3 (default)** | — |
| 4 | −0.0009 ±0.0012 |

Monotone below the ultimate's cost and flat above it, which is what a reserve
whose target has a FIXED price should look like. Four buys marginally more
ultimates (+0.007) and does not pay for the extra mana. Lorehold's is the
soft one because the miracle can happen at several prices and might not happen
at all; Shilgengar's target costs exactly {3} or does not happen.

Its companion knob, `shilgengar_ult_min_gain`, is a LOCAL OPTIMUM rather than
one end of a slope, closed out in `run_mingain_sweep.py`: raising it (2, 3, 5)
is monotonically worse, and *lowering* it (0, −2 — relaxing the "must be a net
gain" gate) is ALSO worse (−0.0321 ±0.0044, −0.0327 ±0.0044), despite firing
the ultimate more often in both directions. See §0r.

### A modelling gap this turned up, not fixed here

**Shilgengar's Treasures are never spent as mana.** They accumulate for Revel
in Riches' alternate win and nothing else reads them. A real pilot holding
four Treasures pays for the ultimate with them and reserves nothing, so the
measured cost of that reserve is an overestimate and Pitiless Plunderer,
Smothering Tithe and Black Market Connections are all understated by however
much that is worth. Left alone deliberately: making Treasures spendable
changes every row in the deck and needs its own regeneration.


---

<a id="0u"></a>

## 0u. FIXED — three copies of "the miracle discount" had drifted apart

**Status: consolidated into one function, all three known reducers applied
everywhere. `ablation_lorehold.txt` regenerated; the first table is void.**

Prompted by checking whether any other card lowers the miracle cost, the way
Molecule Man and Artist's Talent already did. Two more turned out to exist
in the deck — **Ruby Medallion** ("Red spells you cast cost {1} less") and
**Longshot, Rebel Bowman** ("Noncreature spells you cast cost {1} less") —
and neither was consistently applied. This is the same failure shape §0q
names, just with THREE partial copies of one fact instead of a hand-written
name set:

| function | Molecule Man | Artist's Talent | Ruby Medallion | Longshot |
|---|---|---|---|---|
| `miracle_value` (which card is worth holding) | yes | **no** | **no** | **no** |
| `miracle_need` (can we afford it — the gate `set_top` and Library of Leng both check) | yes | yes | **no** | **no** |
| `miracle_window`'s real payment | yes | yes | yes | **no** |

Every card the deck ever miracles is an instant or sorcery — i.e. always
noncreature — so Longshot's discount is not conditional here, it is
unconditional whenever he is on the battlefield, and it was applied to a
HARDCAST (`reduce_cost`) but never once to a miracle. Ruby Medallion was
applied to the real payment but not to either gate that decides whether to
even attempt one, so both `set_top` and Library of Leng's redirect could
decline a miracle they could actually afford.

**All three now read one function, `miracle_reduction(g, card)`.**
`miracle_need` and the two call sites that have a specific card in scope
(`set_top`'s `best`, Library of Leng's `best` — the latter had to be
REORDERED, since the affordability check used to run before `best` existed)
now pass it through for the exact figure. Card-blind call sites — `reserve_for`
from §0t, which runs before any specific top-of-library card is chosen —
keep the conservative worst-case number (Artist's Talent only), which is the
same "never advertise more affordability than guaranteed" rule §0t already
established for the reserve.

### Measured (`run_miracle_reducer_fix.py`, 15,000 paired games, T20)

Windows' `multiprocessing` has no fork, so a monkeypatch of the OLD behaviour
made in the parent process before creating a `Pool` never reaches the spawned
workers — the first cut of this measurement printed an exact `+0.0000` on
every metric, which is what "the patch never ran" looks like and not what "no
effect" looks like. Fixed by patching inside each worker's `_init`.

| metric | old | new | delta |
|---|---|---|---|
| `miracles_cast` | 3.127 | 3.234 | **+0.107 ±0.012** |
| `leng_to_top` | 0.354 | 0.378 | **+0.024 ±0.007** |
| `leng_miracled` | 0.289 | 0.306 | **+0.018 ±0.005** |
| `settop_placed` | 0.889 | 0.899 | **+0.010 ±0.007** |
| win rate | 0.1842 | 0.1830 | −0.0012 ±0.0023 (inside its bar) |

**The mechanism moved and the objective did not**, and the reason is legible
rather than a shrug: Ruby Medallion and Longshot both have to be drawn, kept
on the battlefield, AND line up with a specific card's colour or type at the
moment a miracle is decided. That stacking is rare enough in a 99-card deck
that the aggregate win rate cannot resolve it at this N, even though the
mechanism counters that fire on every relevant turn clearly can. `damage`
(−0.32 ±0.22) and `spells_cast` (−0.047 ±0.043) both moved slightly in the
`*` column too — read as re-sequencing noise from more turns taking the Leng
redirect instead of the "bin worst, draw fresh" alternative, not as a second
finding; win rate is the objective and it did not move.

This is a genuine correctness fix — two cards were not doing what their text
says in a specific situation — worth having regardless of what it does to
the aggregate table, the same standard this project applies to every other
oracle-text correction in it.

**And the regenerated ablation table confirms exactly that scope.** Zero of
the 64 shared rows moved by more than their own OLD win-rate CI half-width,
and zero already-significant rows flipped sign — the check this project
applies to every regeneration. Ruby Medallion's own row moved 0.0009 → 0.0007
and Longshot's 0.0205 → 0.0214, both comfortably inside their bars: individual
values shifted a little (every card's ablation game runs through the same
`set_top`/Leng logic the fix touched, whichever card is under test), but not
far enough to register. Leave-one-out ablation measures cutting a card
entirely; both cards already carried their hardcast discount (and Ruby
Medallion its real miracle payment) in the old code, so their own
presence-or-absence was never what this fix touched. What it touched was the
DECISION of which card to hold and whether the pod's gates believe a miracle
is affordable — visible in the dedicated paired harness above, which holds
everything but the fix itself fixed on the same seeds, well before it would
show up in a per-card table at this N.

**A first version of this check reported "byte-identical" and that was
wrong** — a background wait-loop's `grep -q "MODEL-EVALUATED" ablation_lorehold.txt`
was satisfied by the STALE, not-yet-overwritten file (the string was already
in the pre-existing committed table from the start), so the comparison that
followed it diffed the old file against itself. Caught by re-checking against
a confirmed-stable file (no `python` process running, `mtime` unchanged
across a wait) before writing this section. The substantive finding —
nothing moved outside its own bar — held up; the specific claim that nothing
moved AT ALL did not, and is corrected here rather than left standing.


---

<a id="0v"></a>

## 0v. FIXED — combat was declared at ONE player, and the damage metric was unbounded

Commit `f28ed1e`, 2026-09-08. `diagnostics/run_combat_split.py` is the
harness, `tests/test_combat_split.py` pins the assignment rule, and
`results/combat_split.txt` is the output. **Written up 2026-09-09** — the
commit deliberately left the write-up open, so this section is the record.

**All six ablation tables were regenerated from empty caches for this**, and
every table produced before it is void.

### The defect

Every engine's combat did `damage_single(damage_through(attackers))`, which
sends the entire swing at ONE player. Measured on azusa before the fix: **491
swings of 120+ damage — the pod's whole combined life — and every one of them
killed EXACTLY ONE opponent** while a mean of 1.82 were still alive. The
largest single hit was **933,017 damage and killed one player**.

A board dealing 933,017 was worth precisely as much as one dealing 41. **The
deck's entire payoff — go arbitrarily wide — was capped at one kill a turn
when you need three.** This is the §0r/§0s shape again and the fourth instance
of it: not a card's text, but a policy that quietly asserted a whole strategy
does nothing.

### The fix, and why the assignment rule is a pilot's

`opponents.combat_damage` splits one attack across defenders. **THE
ASSIGNMENT RULE IS A PILOT'S, NOT AN OPTIMISER'S:** a defender is taken on
only when the assignment is still lethal *after they remove its biggest
unblocked attacker*. That insurance term makes it kill fewer players per turn
than perfect information would, which is the point — the model should not
credit the deck with reading the pod's hands.

The rule has an exact closed form, which matters at 5,000 attackers: assign
the k smallest, blockers eat the b biggest, and **"lethal minus its own
largest term" IS the prefix one shorter** — so it is one binary search rather
than an O(n²) scan.

### AND THE DAMAGE METRIC IS NOW BOUNDED AT WHAT COULD HAVE MATTERED

`damage_each` and `damage_single` return the *effective* figure, and every
`m["damage"]` site records that instead of the number it asked for.
`raw_damage` keeps the unbounded total.

Azusa's `validate.py` baseline goes **6826.04 → 52.70**. That is not a heavy
tail being trimmed off a usable metric — **it was a different quantity wearing
the metric's name**: mean 4,379 against a MEDIAN of 67, ten games in three
thousand carrying 69% of the total, and 98.5% of the mean sitting past the
pod's 120 combined life. A drain for 50 into a player on 3 life is worth 3.

### A SECOND BUG FELL OUT OF IT, and it costs more than the split gains

`damage_through` picked `min(g.opponents, ...)` over ALL opponents **including
dead ones**, and a dead opponent has `creatures = 0.0`. So from the first
elimination onward **every deck attacked into NO BLOCKERS AT ALL, while
applying the result to whoever was closest to dying** — two different players.
Each chunk is now blocked by the player it is actually assigned to.

### Measured apart, because one before/after reports them as one number

`run_combat_split.py`, cumulative legs, same seeds, N=6,000:

| deck | split alone | net of both | baseline win T20 |
|---|---|---|---|
| azusa | **+0.0625*** | +0.0182* | 0.3020 → 0.3202 |
| lorehold | +0.0133* | −0.0032 | 0.1828 → 0.1797 |
| shilgengar | +0.0040* | −0.0452* | 0.2432 → 0.1980 |
| rendmaw | +0.0037* | −0.1075* | 0.3042 → 0.1967 |
| tivit | +0.0003 | −0.0183* | 0.3388 → 0.3205 |
| karlov | +0.0000 | −0.1353* | 0.4700 → 0.3347 |

`*` beats its own 95% CI half-width. **The split helps every deck or does
nothing; the drops are the blocker correction**, and they are largest on the
creature decks that used to grind out wins into an empty blocker count after
the first elimination.

**KARLOV'S EXACT +0.0000 IS DEGENERATE, NOT UNWIRED, and that was checked
rather than assumed.** `attack_targets` +2.07 and both damage counters move
significantly, so the code is reached — the split just never changes WHO dies,
because karlov's combat board cannot secure a second kill and its eliminations
come from drains. **An unwired deck reads `attack_targets` 0.000**, which is
exactly what rendmaw and tivit printed before they were wired. Worth knowing
as a general test: a zero that comes with moving mechanism counters is a
finding; a zero that comes with a dead counter is a bug.

### Checks

    validate.py            +0.00 on all 18 metrics across 6 engines
    test_combat_split.py   7/7; --mutate fails exactly the 2 cases that
                           depend on the insurance term and nothing else
    test_time_sieve.py, test_tivit_combo.py    unchanged
    check_unchanged_decks  all six MOVED, as intended -- and with the flags
                           OFF all six were BIT-IDENTICAL on all 8 metrics,
                           which is how the refactor was shown to be
                           behaviour-neutral BEFORE the default was flipped

That last line is the pattern worth copying: a refactor and a behaviour change
in one commit are separable only if you can run the refactor with the new
behaviour disabled and get the old numbers back exactly.

### What the regenerated tables did

Rows moving by more than their own old CI half-width: lorehold 3/65,
shilgengar 10/64, rendmaw 16/64, tivit 23/64, azusa 25/58, karlov 29/63. Five
sign flips, all marginal-to-zero rather than a finding reversing: The Dawning
Archaic, Verdurous Gearhulk, Enduring Vitality, Farewell, Damnation.

**The clearest mechanism read is azusa's Ashaya, Soul of the Wild: +0.0095 →
+0.0011, now a blank.** The engine models it as a SINGLE body whose power
equals your land count, and a single creature can only ever kill one opponent
however large it is. The fix devalues concentrating power into one body and
rewards width. **Scute Swarm +0.0328 → +0.0589 is the same statement from the
other end** — and it is now the top card in that deck by a clear margin.

### What this does NOT settle

The insurance term is one assumption (a defender removes exactly its biggest
unblocked attacker) and it is a judgement call, not a measurement — the same
class as `destroy_share` and `opp_vote_policy`. It is deliberately
pessimistic. No knob exposes it, which means a card whose value swings on it
cannot currently be reported with the knob said out loud. If a decision ever
turns on that, the knob comes first.

---

<a id="0w"></a>

## 0w. MEASURED — all three staged swaps survive the combat split unchanged

2026-09-09, closing queued item 11. `diagnostics/run_swaps_0904.py` and
`diagnostics/run_lorehold_pair.py` are the harnesses;
`results/staged_recheck_rendmaw.txt` and
`results/lorehold_pair_postsplit.txt` are the outputs.

### Why this had to be asked

The combat split (§0v) moved **16 of rendmaw's 64** ablation rows and **3 of
lorehold's 65** by more than their own old CI half-width. All three staged
swaps were measured before it — the Rendmaw one on 2026-09-04, the Lorehold
pair on 2026-09-04/05 and jointly on 2026-09-06 — so their evidence described
a combat model the project no longer uses. This repo's own rule is to
re-measure a staged change when the engine underneath it moved, and it had
been applied twice before (§0p, and the 2026-09-03 March of the World Ooze
recheck).

**The re-runs use the ORIGINAL N AND THE ORIGINAL SEEDS**, not a fresh
design. That is the whole point: hold the sample fixed and the only thing
that can move a number is the engine. A "re-verification" at a different N
confounds the two and answers a different question.

### Rendmaw: −Idol of Oblivion +Cauldron of Essence

N=6,000 paired, seeds as originally run.

| win rate | 2026-09-04 | 2026-09-09 |
|---|---|---|
| T10 | +0.0027 [+0.0007, +0.0048] | **+0.0022 [+0.0007, +0.0038]** |
| T20 | +0.0135 [+0.0088, +0.0182] | **+0.0152 [+0.0107, +0.0198]** |

Both horizons reproduce inside their own bars and both remain significant.
The mechanism counters kept their signs and rough magnitudes — damage +1.55,
`cards_drawn` −0.26, `tokens_made` −0.16, `stranded_mv` +1.15 — so **the two
predicted costs are still real and still outweighed**, which is the part that
matters. This swap trades a draw engine for a drain, and the drain still wins
the trade when combat is declared at the pod rather than at one player.

### Lorehold: the 2×2 factorial, re-run entire

N=30,000 per cell, all four legs on one seed, identical design to §0p.

| win rate, T20 | 2026-09-06 | 2026-09-09 |
|---|---|---|
| Caldera alone | +0.0194 ±0.0024 | **+0.0179 ±0.0023** |
| Sunbird's alone | +0.0146 ±0.0028 | **+0.0152 ±0.0028** |
| both | +0.0362 ±0.0035 | **+0.0366 ±0.0035** |
| interaction | +0.0022 ±0.0020 | +0.0034 ±0.0020 |
| Caldera GIVEN Sunbird's | +0.0216 ±0.0026 | **+0.0214 ±0.0026** |
| Sunbird's GIVEN Caldera | +0.0168 ±0.0029 | **+0.0186 ±0.0029** |

**Every cell landed inside its own previous bar.** The two marginal figures
are the ones the decision rests on — is the second change still worth a slot
once the first is in — and both reproduce.

The cut targets were re-ablated in the same run: Scroll Rack −0.0107 ±0.0032
win at T20 (was −0.0093 ±0.0032) and Penance −0.0079 ±0.0032. Both are still
significantly worse than a blank, so **both cuts are as cheap as they ever
were.**

### Two things worth reading carefully rather than skimming

**The interaction crossed into significance and that is NOT a new finding.**
+0.0022 ±0.0020 → +0.0034 ±0.0020: the point estimate moved by 0.0012, well
under its own half-width, and it was already positive. A quantity that was
marginally inside its bar is now marginally outside it. The conclusion is
unchanged and was always the same one — the two changes are additive to
slightly super-additive, which is the opposite of the concern that motivated
§0p. **Do not report this as "the interaction became real."** It is the same
number with the same sign, and calling a border crossing a discovery is how
the top-eight ordering mistake got made.

**Sunbird's decay did not continue, and that is evidence about the decay.**
Its T20 figure went +0.0215 (2026-09-04) → +0.0146 (2026-09-06) → +0.0152
(2026-09-09). Two engines in a row now put it near +0.015, so the one-off
drop is **not an ongoing trend** — which narrows what could have caused it,
without identifying it. It is still unattributed, it is still queued item
0b-i, and the standing instruction stands: **do not invent a mechanism for
it.** What can be said is that the obvious candidate was ruled out twice now,
because Scroll Rack's own ablation has been stable at roughly −0.010 across
all three engines.

### Consequence

**All three staged swaps are safe to commit on this evidence.** The blocker
recorded on 2026-09-09 is cleared, and each change now carries a `reverified`
entry in `edhmc/pending.py` saying so — run `python -m edhmc.pending` to read
them. What remains before committing is the ordinary three-leg discipline:
the deck module, the `.xlsx`, and the ledger, in one commit.

---

<a id="0x"></a>

## 0x. MEASURED — nine Azusa candidates, and the doubler is the find

2026-09-09. `results/candidates_azusa_T20.txt` and `..._T10.txt` are the
output, `tests/test_azusa_candidates.py` pins the mechanisms,
`edhmc/decks/azusa_v1.py` holds the definitions and the modelling notes.

N=15,000 paired at both horizons — the tables' own sample size, because a
candidate is only comparable to an ablation row measured at the same N, and
that comparison IS the decision rule. Victim slot: Perilous Forays, the one
card in the azusa table whose signal reads `--`, removed in both legs.

### The table, T20 win rate

| card | MV | win T20 | win T10 | signal |
|---|---|---|---|---|
| **Ancient Greenwarden** | 6 | **+0.0290 ±0.0041** | **+0.0269 ±0.0029** | both |
| **Greensleeves, Maro-Sorcerer** | 5 | **+0.0143 ±0.0033** | +0.0102 ±0.0021 | both |
| **Conduit of Worlds** | 4 | **+0.0116 ±0.0030** | +0.0104 ±0.0020 | both |
| Springheart Nantuko *(floor)* | 2 | +0.0105 ±0.0028 | +0.0056 ±0.0017 | both |
| Case of the Locked Hothouse *(floor)* | 4 | +0.0089 ±0.0032 | +0.0026 ±0.0018 | both |
| Walk-In Closet *(floor)* | 3 | +0.0089 ±0.0030 | +0.0114 ±0.0021 | both |
| Cultivator Colossus | 7 | +0.0054 ±0.0030 | +0.0045 ±0.0018 | both |
| Burgeoning | 1 | −0.0009 ±0.0010 | −0.0003 ±0.0006 | MODEL-BLIND |
| Constant Mists | 2 | +0.0005 ±0.0010 | +0.0003 ±0.0006 | MODEL-BLIND |

### THE DOUBLER IS WORTH AS MUCH AS THE GRAVEYARD CLAUSE, and that was measured apart

Ancient Greenwarden does three things, and +0.029 credited to the wrong one is
a wrong deckbuilding conclusion. Measured on the same seeds, N=6,000, T20:

| leg | win rate | mechanism |
|---|---|---|
| graveyard lands + the 5/7 reach body | +0.0170 ±0.0060 | `lands_from_graveyard` +0.68 |
| **the landfall doubler alone** | **+0.0138 ±0.0044** | `cards_drawn` **+1.09** |
| the whole card | +0.0308 ±0.0066 | — |

**Almost exactly additive** (0.0170 + 0.0138 = 0.0308). Both halves are real
and roughly equal, so this is not "a Crucible of Worlds with a body" and it is
not "a landfall doubler" — it is both, and either half alone would still be a
good card in this deck.

The doubler's mechanism is CARD DRAW, not damage: +1.09 cards a game, because
what it mostly doubles is Horn of Greed and Seer's Sundial. That lands exactly
on the deck's standing finding — **this deck is CARD-limited, not
drop-limited** — and it is why the doubler beats a fourth land-supply effect.

Note the counter that did NOT move: `landfall_triggers` is −0.09, essentially
flat. The doubler doubles the ABILITY, not the EVENT, and the engine counts
the event once on purpose. A version that counted twice would have reported a
much larger mechanism move and the same win rate, which is how a
mechanism counter stops being evidence.

### Greensleeves and Springheart score with NEGATIVE land counters

Both have `landfall_triggers`, `lands_played` and `cards_drawn` slightly
negative while win rate and damage are strongly positive. That is the
game-length pattern the azusa table already documents for Avenger of Zendikar
(−6.1 damage at T20, +0.0249 win) and Ulamog: they end games sooner, so fewer
landfalls accumulate. **They are not land cards. They convert landfall into
bodies**, and post-§0v that is worth much more than it was — width beats
concentration now.

### Cultivator Colossus is the weakest of the seven FOR A LEGIBLE REASON

+0.0054 ±0.0030 on a 7-drop, and `lands_played` is −0.29. Its ETB needs LANDS
IN HAND, and this deck does not hoard them — it is allowed roughly three drops
a turn and plays them. By the time a 7-drop resolves the hand is lands-poor,
so the loop that makes the card famous mostly does not run. The mechanism
counter agrees: `colossus_lands` averages well under one a game in the deck,
against six in a forced test with five lands in hand.

This is the same finding as Exploration's, arriving from a third direction:
**cards, not permission, and not lands-in-hand either.**

### The two MODEL-BLIND rows, and a diagnostic worth keeping

Burgeoning and Constant Mists are unimplemented, for the reasons recorded in
`decks/azusa_v1.py`: Burgeoning triggers on an OPPONENT playing a land and
opponents here own no lands; Constant Mists is a fog, and the engine has no
way to spend a card on defence (`incidental_damage` is a flat per-turn life
subtraction, `resolve_clocks` never reads combat).

**Their CIs are ±0.0010 against ±0.0030 for every implemented card, and that
width is itself the diagnostic.** An unimplemented card produces nearly
identical games in both branches, so the paired difference has almost no
variance. **A suspiciously TIGHT bar around zero means unimplemented; a wide
bar around zero means measured and genuinely marginal.** That is a cheaper
tell than reading the SCRIPTED sets, and it would have caught the §0k
Ephemerate case immediately.

### What this does NOT license

**None of these is a staging.** A candidate score minus an ablation score is
not a swap: three swaps against a common baseline have overlapping CIs and
cannot be ranked against each other — the rule that decided the Penance slot
(§0e) and stopped Goldspan Dragon (§0c). Anything moving needs a HEAD-TO-HEAD
against the specific card it would replace.

**And three of the seven are REDUNDANT with each other and with the deck.**
Conduit of Worlds, Walk-In Closet and Ancient Greenwarden all grant "play
lands from your graveyard", and the deck already runs Crucible of Worlds
(+0.0144) and Ramunap Excavator (+0.0157). Leave-one-out understates every
member of an interchangeable group, and these were measured one at a time with
both incumbents present — so **the marginal value of the SECOND one added is
lower than its row, and these rows cannot be summed.** Add at most one, and
prefer Greenwarden because half its value is the doubler, which nothing else
in the list duplicates.

### Engine changes, and the check that they moved nothing

Six cards needed engine code (`edhmc/azusa.py`): the graveyard-land gate now
reads three more names, `top_access` gained the Hothouse solve state,
`land_drops_for_turn` its extra drop, `land_entered` split into
`_landfall_payoffs` so Greenwarden can run it twice, `power_of`/`toughness_of`
read a new `DYNAMIC_PT_LANDS` set, and Cultivator Colossus got its ETB loop.

`check_dynamic_pt_coverage()` was added in the same change and mutation-tested,
per §0q: a `*/*` card is DEFINED 0/0, so a name missing from that set is
silently a 0/0 that dies on arrival — a worse symptom than the usual
mislabelling, because the card never exists at all.

**All six decks came back BIT-IDENTICAL on all 8 metrics** against the
pre-change commit (`check_unchanged_decks.py`), so every ablation table
including azusa's remains valid and nothing needed regenerating. The new code
is gated on cards absent from the deck, and that was checked rather than
argued. `validate.py` is `+0.00` on all 18 metrics; `audit_cards.py` is 0 ERR
across 555 slots / 479 distinct names.

### Two process failures worth recording

**A separate `decks/azusa_candidates.py` was silently unaudited.**
`audit_cards.py` and `tag_flying.py` discover cards by walking the UPPERCASE
attributes of each `<deck>_v<N>.py` module, so a candidate file that is not a
deck module is checked by nothing and tagged by nothing. The card count stayed
at 470 and read as success. **This is §0c exactly** — the bug where two fliers
were measured as ground creatures — and the fix was to follow the existing
convention and put the candidates in the deck module, where 479 names are now
checked.

**`self.m` is a plain dict, and a new counter must be REGISTERED.**
`self.m["colossus_lands"] += 1` is a `KeyError` on an unregistered key, and it
only fires in the games where a 7-drop actually resolves — a minority of them,
inside a worker process, in a harness that would have died twenty minutes into
a run. Caught by reading the initialiser before launching rather than after.

---

<a id="0y"></a>

## 0y. MEASURED — the land-animation genre loses its slots to the §0x candidates

2026-09-09. `diagnostics/run_azusa_animation_swap.py` is the harness,
`results/azusa_animation_swap.txt` the output. N=15,000 paired per leg, every
leg on the same seed, both horizons.

**This is the head-to-head §0x said was required.** A candidate's
value-over-a-blank minus an incumbent's ablation row is not a swap; both are
measured against a common baseline with overlapping CIs. Here the cut card is
absent from one branch and present in the other, which is the comparison the
decision actually rests on.

### ALL TWELVE SWAPS ARE POSITIVE AND SIGNIFICANT AT BOTH HORIZONS

T20 win rate, positive = the swap is an improvement:

| out ↓ / in → | Ancient Greenwarden | Greensleeves | Conduit of Worlds |
|---|---|---|---|
| Sylvan Awakening | **+0.0277 ±0.0043** | +0.0128 ±0.0034 | +0.0082 ±0.0034 |
| Rude Awakening | **+0.0271 ±0.0042** | +0.0121 ±0.0036 | +0.0069 ±0.0034 |
| Ashaya, Soul of the Wild | **+0.0265 ±0.0040** | +0.0109 ±0.0031 | +0.0061 ±0.0034 |
| Nissa, Worldwaker | **+0.0235 ±0.0043** | +0.0092 ±0.0035 | +0.0059 ±0.0035 |

Packages, against the same baseline:

| package | T10 | T20 | interaction |
|---|---|---|---|
| **P2** −Sylvan −Ashaya +Greenwarden +Greensleeves | +0.0321 ±0.0034 | **+0.0393 ±0.0050** | +0.0007, additive |
| **P3** −Sylvan −Rude −Ashaya +Greenwarden +Greensleeves +Conduit | +0.0376 ±0.0039 | **+0.0434 ±0.0057** | −0.0025, sub-additive |

### THE MECHANISM IS §0s CONFIRMED FROM THE REPLACEMENT SIDE

P3 vs baseline at T20, and this is the whole finding in four rows:

    lands_animated        -6.85 +-0.20     (baseline 8.31 -- 82% of it gone)
    animated_damage       -6.42 +-2.18     (baseline 7.83)
    tokens_made          +40.57 +-3.33     (baseline 60.66 -- up 67%)
    landfall_triggers     +1.79 +-0.12
    cards_drawn           +1.14 +-0.14
    lands_from_graveyard  +1.46 +-0.08

**You give up 6.4 animated damage a game and receive 40 tokens, 1.8 landfall
triggers and 1.1 cards.** §0s said the animation "sells this deck the one
thing it already has most of" — 9.24 marginal damage in a deck whose damage
runs into the thousands. This is the same statement measured from the other
end: the damage is real, it is genuinely lost, and it does not matter.

**And §0v is why the replacement is worth so much more than the loss.** Since
combat is declared at the pod, tokens are not damage — they are WIDTH, and
width is extra opponents killed. A deck that concentrates power into animated
lands was being paid for a kind of board the combat model no longer rewards.
The two findings compose: the animation was already nearly a blank, and the
combat split made its replacement materially better.

### ANCIENT GREENWARDEN IS THE CARD, AND THE CUT BARELY MATTERS

Its four rows span +0.0235 to +0.0277 — a range of 0.004 against bars of
±0.004. **The value is the card, not which animation slot it takes.** That is
the cleanest possible statement that the incumbent genre is interchangeable
with a blank: swapping Greenwarden for any of the four buys the same amount.

The four cut targets are likewise NOT distinguishable from each other (all
twelve column-wise differences sit inside their bars), so **do not read a cut
ORDER out of this table.** Their own ablation rows (+0.0011 to +0.0079) are
tighter and are the better guide if one must be picked: Ashaya is cheapest,
Nissa Worldwaker dearest.

### CONDUIT OF WORLDS IS THE REDUNDANT ONE, CONFIRMED

It is the weakest column (+0.0059 to +0.0082) and it is the reason P3 is
sub-additive where P2 is clean. Going from P2 to P3 — cut Rude Awakening as
well, add Conduit — buys **+0.0041**, less than Conduit's own worst 1-for-1,
while spending an extra card. With Ancient Greenwarden, Crucible of Worlds and
Ramunap Excavator all on the battlefield, a fourth "play lands from your
graveyard" has very little left to do. **§0x predicted exactly this and said
its rows could not be summed; this is that prediction measured.**

### What this does and does not establish

It establishes that **P2 is a real, additive, well-supported change**:
−Sylvan Awakening −Ashaya, +Ancient Greenwarden +Greensleeves, worth
+0.0393 ±0.0050 at T20 and +0.0321 ±0.0034 at T10, significant at both.

It does NOT establish that these are the BEST available replacements. The
comparison is against the four animation cards only; no other candidate or
incumbent was in the running, and §0x's remaining four cards were not tested
in these slots. It also inherits §0x's floors — Greensleeves is fully
modelled, but Ancient Greenwarden's row is exact only insofar as the doubler
is, and the doubler was measured apart and found to be half the card.

**Nothing is staged.** This is evidence for a staging, not a staging.

---

<a id="0z"></a>

## 0z. OPEN — ASHAYA IS MISCLASSIFIED, and four Azusa combos are invisible

2026-09-10, raised by a question about combos rather than by a diagnostic.
**This retracted a cut that was one edit away from being staged**, which is
the reason it is written up at length.

> **THE MISCLASSIFICATION IS FIXED (2026-09-10, later the same day).** Ashaya
> is now in `ablation.PARTLY_MODELLED` and prints in the third table, with its
> missing clause named under its own row — the category this section asked for
> and queued item 14b tracked. §0z4. **What remains OPEN is everything below
> the labelling:** the type-changing clause is still unimplemented and the
> combos are still invisible, which is queued item 15. Ashaya's row
> (+0.0019 ±0.0019) is a floor and always was; it is now printed as one.

### The question

Do Ashaya + Quirion Ranger, or Springheart Nantuko + Lotus Cobra / Tireless
Provisioner / Nissa Who Shakes the World, do anything in this model?

**No. Not one of them.** And answering it turned up a labelling error.

### THE LABELLING ERROR: Ashaya is in SCRIPTED_AZUSA and should not be

Oracle text: *"Ashaya's power and toughness are each equal to the number of
lands you control. **Nontoken creatures you control are Forest lands in
addition to their other types.**"*

The engine implements **the first sentence only** — Ashaya appears in
`edhmc/azusa.py` exactly once, in `DYNAMIC_PT_LANDS`. The type-changing clause
does not exist anywhere.

Yet Ashaya sits in `ablation.SCRIPTED_AZUSA`, whose membership **is a claim
that the engine implements the card's text**, and whose output is printed
under the heading *"MODEL-EVALUATED — a low score is evidence about the
card."* Ashaya's row is +0.0011 ±0.0023, and **it is not evidence about the
card.** It is evidence about a 5-mana */* creature, which is half of it.

**This is §0f's shape** (three cards in `SCRIPTED_LOREHOLD` that are not their
text) and §0q's rule (a label nothing checks is a claim), and it is the fourth
instance.

**And the comment that was supposed to cover it points at nothing.**
`ablation.py` says Ashaya's partial implementation "is called out at its
definition in `edhmc/azusa.py`". There is no such call-out, and `git show
HEAD:edhmc/azusa.py` confirms there never was — the pointer was false when it
was written. A note that says "documented elsewhere" and is not is worse than
no note, because it stops the next reader looking.

### THE CONSEQUENCE, and it was nearly expensive

§0y measured a package that CUT Ashaya, on the strength of its +0.0011 row
being the weakest of the four animation cards. **That cut was withdrawn.**
Cutting a card because the engine scores it low, when the engine has made it
low by not implementing it, is precisely the mistake that cost this project
0.074 win rate on Azusa's land sequencing and 0.034 on Shilgengar's ultimate.
CLAUDE.md states the rule: *"A card scoring like a blank usually means the
engine has made it a blank."*

The replacement package (`P3B`, cutting Nissa Worldwaker instead) measures
**+0.0421 ±0.0058** against the Ashaya-cutting one at **+0.0434 ±0.0057** —
inside each other's bars. **Keeping Ashaya costs nothing measurable and
removes the risk entirely.** There was never a trade-off to make.

### The four combos, and what the model sees of each

| combo | in the deck? | modelled? |
|---|---|---|
| Ashaya + **Quirion Ranger** | both, yes | **neither half.** Ashaya's type clause is unimplemented; Quirion Ranger is in `KNOWN_BLIND` and is not mentioned anywhere in `edhmc/azusa.py` |
| Springheart + **Lotus Cobra** | Cobra yes, Springheart is a candidate | Cobra's landfall mana is modelled; **Springheart's bestow-and-copy mode is not** |
| Springheart + **Tireless Provisioner** | Provisioner yes | same — Provisioner's Treasure is modelled, the copy mode is not |
| Springheart + **Nissa, Who Shakes the World** | **not in the deck at all** | n/a |

Two independent reasons each of these is worth zero here, and both are
already-known limits rather than new ones:

1. **Springheart Nantuko is modelled as its unattached mode only** — landfall
   makes a 1/1 Insect. Bestow, and with it "pay {1}{G} to create a token
   copy of the creature this is attached to", need an ATTACHMENT RELATION the
   engine does not have. Documented at its definition in `decks/azusa_v1.py`;
   its §0x row of +0.0105 is explicitly a FLOOR.
2. **Quirion Ranger's reason for being blind is now stale.** It reads
   "untaps a target creature once a turn for no modelled payoff" — true in
   isolation, and false alongside Ashaya, where returning a creature-Forest to
   hand and replaying it is a land drop and therefore a landfall trigger. The
   classification is right (it IS unimplemented); the stated reason is no
   longer the whole reason.

### What this does NOT claim

**It does not claim the combos are good.** Nobody has measured them, because
nothing implements them. A card whose value rests on an unimplemented
interaction is UNMEASURED, not underrated — the MODEL-BLIND rule in both
directions. Implementing Ashaya's type clause would also be genuinely
invasive: it makes every nontoken creature a land, which touches
`available_mana`, `land_drops_for_turn`, `playable_lands`, `land_entered`,
`land_died` and Titania, and it interacts with Scute Swarm's doubling.

### What was actually changed here

- **Nothing was implemented.** This is a classification and a retraction.
- The staged Azusa package cuts **Nissa, Worldwaker** rather than Ashaya.
- Ashaya belongs in the §0f list of cards whose `SCRIPTED_*` membership is
  false. **Moving it to `KNOWN_BLIND` would be wrong too** — its `*/*` body is
  real and it does attack — so the honest fix is a third category the project
  does not have: PARTLY MODELLED, where a low score means nothing and a high
  score means something. Until that exists, the entry here is the record.

---

<a id="0z1"></a>

## 0z1. FIXED — every landfall payoff was a BOOLEAN, and Springheart is implemented

2026-09-10, prompted by "what is Springheart worth now that we know its
combos?" The honest first answer was **nothing had changed** — §0z was a
classification finding and implemented no code, and identifying a combo does
not move a measured number. Implementing it turned up a bigger problem.

### THE PREREQUISITE BUG: `has()` where it needed `count()`

`_landfall_payoffs` keyed **every payoff except Scute Swarm and Nissa** on the
boolean `self.has(name)`. A second Lotus Cobra produced no extra mana. A
second Tireless Provisioner produced no extra Treasure. A second Rampaging
Baloths produced no extra Beast.

This was invisible and harmless for three years of this deck's life, because
the list is singleton and nothing ever made a second copy of a nontoken
creature — `make_tokens` names its output "Beast token", which never collides
with a card name.

**It stopped being harmless the moment Springheart's copy mode was
implemented, because that mode's entire purpose is a second copy of a landfall
payoff.** A naive Springheart would have created the token, the token would
have been inert, and the Lotus Cobra combo would have measured as ZERO — for a
reason having nothing to do with either card. That is the §0k Ephemerate shape
(a handler that is dead code) waiting to happen at one remove.

Converting all of them to `count()` is **behaviour-neutral for every list in
this project**, and that was checked rather than argued: all six decks came
back BIT-IDENTICAL on all 8 metrics via `check_unchanged_decks.py`. No table
needed regenerating.

### Springheart Nantuko, implemented

`springheart_host` is a single `Permanent` reference. It is the only
attachment relation in the project, and building a general Aura framework for
one card would be the wrong trade — if a second bestow card arrives,
generalise then.

Bestow and the creature mode both cost {1}{G}, so there is no mana question at
resolution, only whether a host worth copying is on the battlefield.
`SPRINGHEART_HOSTS` ranks them by what a copy is worth **per landfall** rather
than by body size: Scute Swarm, Lotus Cobra, Tireless Provisioner, Rampaging
Baloths, Greensleeves, Avenger, Courser, Tireless Tracker. If the host dies,
Springheart becomes a creature again.

### The number

| | over a blank, T20 | T10 |
|---|---|---|
| before (unattached 1/1-Insect mode only) | +0.0105 ±0.0028 | +0.0056 ±0.0017 |
| **after (bestow + copy)** | **+0.0141 ±0.0030** | **+0.0095 ±0.0021** |

**A real move, and a modest one — the point estimate rose by about its own
error bar.** The mechanism says why, and it is the useful part:

    springheart_bestowed   0.162     it finds a host in 16.2% of games
    springheart_copies     1.07      copies per game, unconditionally

It resolves in 31% of games and finds a ranked host in about half of those.
**The combo is real, modelled, and uncommon.** That is why implementing a
two-card engine moved the card by +0.004 rather than by +0.04, and it is the
same lesson as Sunbird's Invocation (§0p): a conditional number printed as an
unconditional one reads far better than the card plays.

### It changed a staged decision within a day

Springheart at +0.0141 now beats **Conduit of Worlds** at +0.0116, which had
been staged into the third Azusa slot hours earlier. Measured head-to-head in
the identical swap on the same seeds:

| swap | T10 | T20 |
|---|---|---|
| −Nissa Worldwaker +Conduit | +0.0061 ±0.0023 | +0.0059 ±0.0035 |
| **−Nissa Worldwaker +Springheart** | **+0.0060 ±0.0022** | **+0.0118 ±0.0035** |

and as packages: `P3B` (Conduit) +0.0421 ±0.0058 → `P3C` (Springheart)
**+0.0499 ±0.0058** at T20, damage +3.55 → +5.81. **The ledger was updated.**
Conduit's own entry had said "if one of the three is dropped, drop this one",
naming Springheart as the leading alternative and noting it was unmeasured in
the slot. It was measured, and it won.

### THE NUMBER IS STILL A FLOOR, in two known ways

1. **The engine bestows only onto a ranked list of landfall payoffs**, never
   onto an arbitrary body. A pilot with no payoff out might still bestow on a
   creature; this one stays a creature and makes Insects. Defensible — paying
   {1}{G} a turn to copy a vanilla body against a free 1/1 is close — but it
   is a policy, and this project's largest corrections have all been policies.
2. **A token copy does NOT re-trigger the host's ETB.** `make_permanent` does
   not run the ETB dispatch that `resolve` does. So copying Avenger of
   Zendikar, Craterhoof Behemoth, Woodland Bellower, Eternal Witness or
   Titania is scored as a bare body, and those are exactly the copies a real
   pilot most wants. **This is the single largest remaining understatement of
   the card** and it is why Avenger sits at rank 6 in the host list rather
   than rank 1.

Both are conservative, so the card cannot be worse than measured.

---

<a id="0z2"></a>

## 0z2. MEASURED — two card-draw candidates, and a THIRD misclassified card

2026-09-10. `diagnostics/run_azusa_draw.py`, `results/azusa_draw.txt`.
N=15,000 paired, both horizons, **measured against the STAGED list**
(`build_pending("azusa")`) rather than the printed v1 — the question was what
to add to the deck as it will be, not as it was.

Chosen off a Scryfall sweep for land-synergy card draw, against the deck's one
measured weakness: it is CARD-limited, not drop-limited (2.77 drops granted a
turn against 1.33 used; 57.9% of turns end with an unused drop and no land to
play).

### The numbers, T20 (baseline 0.3593)

| swap | win rate | cards drawn |
|---|---|---|
| Forest → **Cryptic Caves** | +0.0068 ±0.0032 | **+0.26 ±0.09** |
| Perilous Forays → **Ka-Zar** | +0.0153 ±0.0034 | +0.08 ±0.09 |
| *Bane of Progress → Ka-Zar* | *+0.0253 ±0.0040* | *see below* |
| **both (Forays→Ka-Zar, Forest→Caves)** | **+0.0218 ±0.0044** | +0.33 ±0.12 |

Additive: interaction −0.0003 ±0.0044.

### THE WINNER DOES NOT ADDRESS THE WEAKNESS, and the loser does

**Ka-Zar's `cards_drawn` is +0.08 ±0.09 — flat, inside its own bar.** It is
not a card-draw card in this deck. What it actually does:

    lands_from_library   +0.34 +-0.02      top-of-library land access
    damage               +2.53 +-0.24      Zabu, growing on every landfall

**The redundancy prediction was right.** `top_access()` is a BOOLEAN and
Courser, Augur and Oracle are already in the list, so a fourth enabler adds
only the 0.34 lands the other three were missing. Ka-Zar is a good card here
for reasons that have nothing to do with why it was picked — it is a body that
grows, in a deck that §0v made reward width.

**Cryptic Caves is the one that does the intended job** — the largest
`cards_drawn` delta of the two, plus +0.17 landfall triggers and +0.10 lands
from the graveyard, exactly the recur-and-replay loop it was chosen for. It is
simply too rare to matter much: `caves_cracked` averages **0.21 a game**,
because it is ONE land in a 41-land deck and has to be drawn before it can do
anything. A second and third copy would scale it, and singleton forbids that.

**So the honest read is the opposite of the hypothesis.** The card that
attacks the weakness works and is small; the card that scores was not
attacking the weakness at all.

### THE CUT MATTERS MORE THAN THE CARD — and here that is a TRAP

The same Ka-Zar is worth +0.0153 in the Perilous Forays slot and +0.0253 in
the Bane of Progress slot. A full point of win rate, from the cut alone.

**DO NOT TAKE THE BANE CUT.** `Bane of Progress` is in `SCRIPTED_AZUSA`,
printed under MODEL-EVALUATED, and its implementation is:

    # ETB destroys ALL artifacts/enchantments -- including yours.
    # Opponents' are not tracked as objects, so only your own side is
    # represented

**The engine models the card's COST and none of its BENEFIT.** Its −0.0041 is
not a bad card; it is a one-sided board wipe with the sided-ness removed. It
is the only model-evaluated card in this deck with a significantly negative
win rate, which makes it look like the obvious cut, which makes it **the most
dangerous instance of this failure so far** — §0z's Ashaya at least measured
near zero rather than actively negative.

**This is the third card found in two days sitting under a label that is
false** (Ashaya §0z, the three Lorehold cards §0f, now Bane). The pattern is
no longer a series of accidents: `SCRIPTED_*` is BINARY, and a card whose text
is half-implemented has nowhere honest to go. See CLAUDE.md queued item 14.

### POSTSCRIPT 2026-09-10: Bane of Progress is no longer negative

The four swaps were committed and azusa's table regenerated from an empty
cache. **Bane of Progress moved −0.0041 ±0.0024 (signal `win`) to −0.0013
±0.0022 (signal `--`)** — inside its own bars, no longer a significantly
negative card. The warning above stands on its own merits (the engine still
models only its cost), but the specific trap is now less inviting: it no longer
reads as the obvious cut. The deck got stronger around it, which is the same
arithmetic that shrank the drains in §0m — a fixed effect is a smaller share of
a higher baseline.

### The recommendation

**−Perilous Forays +Ka-Zar of the Savage Land, and −Forest +Cryptic Caves:
+0.0218 ±0.0044 at T20, +0.0097 ±0.0028 at T10**, additive, both legs
significant at both horizons. Perilous Forays is signal `--` (+0.0012 ±0.0016)
and is fully implemented in `activations()`, so cutting it is safe in the way
cutting Bane is not.

That takes the staged deck from **35.9% → 38.1%** at T20.

The `+0.0299` package in the output file is the Bane version. **It is recorded
and must not be acted on** until Bane of Progress is either implemented
against real opponent permanents (§4, which is the project's oldest
limitation) or reclassified.

---

<a id="0z3"></a>

## 0z3. MEASURED — four sacrifice-lands, and THE TAP IS THE BINDING CONSTRAINT

2026-09-10. `diagnostics/run_azusa_draw.py`, `results/azusa_draw.txt`. All
four measured **in the same Forest slot, on the same seeds**, N=15,000 paired,
so they are directly rankable against each other rather than each against its
own baseline.

### The result, T20 win rate (baseline 0.3593)

| land | cost to draw | enters | win rate | cracks/game | cards |
|---|---|---|---|---|---|
| **Scene of the Crime** | `{2}`, **no {T}** | tapped | **+0.0096 ±0.0038** | **0.39** | **+0.53** |
| Horizon of Progress | `{1},{T}` | untapped | +0.0081 ±0.0030 | 0.21 | +0.28 |
| Cryptic Caves | `{1},{T}`, 5+ lands | untapped | +0.0068 ±0.0032 | 0.21 | +0.26 |
| The Hunter Maze | `{1}{G},{T}` | tapped | +0.0039 ±0.0032 | 0.16 | +0.15 |

All four significant at both horizons.

### WHY SCENE WINS IS NOT THE MANA COST — IT IS THE TAP

Scene of the Crime is the **dearest** of the four to activate (`{2}` against
`{1}`) **and** it enters tapped, and it still wins, because **its sacrifice
ability has no `{T}` in the cost.** Every other one must be untapped to crack,
and in this deck lands are tapped for mana during the main phase — so by the
time `activations()` runs after combat, they usually cannot be cracked at all.

It cracks **0.39 times a game against 0.21**, nearly double, and every
mechanism counter follows: cards +0.53 against +0.26, landfall triggers +0.33
against +0.17, lands from the graveyard +0.20 against +0.10. Those gaps are
far outside their own bars even where the win-rate gap is not.

**The Hunter Maze is worst for the same reason, compounded**: `{1}{G}` AND
`{T}` AND enters tapped — taxed three ways. It is the only one of the four
that taps for `{G}` rather than `{C}`, which is worth something in a deck
running 13 colourless-only utility lands, and it is not worth this much.

**THE GENERAL RULE, worth carrying to any future activated-ability land: the
binding constraint is the TAP, not the mana.** This deck floats mana it cannot
spend (`mana_floated` is a standing metric) and taps its lands for the main
phase. An ability competing with its own land's tap is competing with the
whole deck.

### The honest limit on the ranking

**Scene's win-rate margin over Cryptic Caves is +0.0028 against a ±0.0038 bar
— INSIDE it.** On win rate alone these four are not cleanly ordered; only
Scene-over-Hunter-Maze clears both bars. The mechanism counters are decisive
and unanimous, and they point the same way rather than against, which is why
the pick is Scene — but this is a case where the objective could not resolve
what the mechanism could, and saying so is the point. Raising N would settle
it; the effect sizes here (0.004–0.010) sit near the deck's ±0.0028 noise
floor by construction.

Real costs, both recorded: entering tapped shows up as `stranded_mv` +3.22,
the highest of the four; and Scene is an ARTIFACT land, which the engine's own
Bane of Progress wipe spares because that wipe excludes lands — legally it
should die to it.

### AND A BUG THAT INVALIDATED THE PREVIOUS KA-ZAR NUMBERS

**Ka-Zar of the Savage Land was measured as a `*/*` equal to the land count —
a 16/16 instead of a 3/2.** A patch adding it to `LAND_ENABLERS` used a `sed`
anchor (`"Cultivator Colossus",\n})`) that matched **both** that set and
`DYNAMIC_PT_LANDS`, and it landed in the wrong one. `power_of` then discarded
its printed 3/2.

Corrected figures: **+0.0141 ±0.0034** at T20 against the +0.0153 first
reported, and +0.0243 against +0.0253 in the Bane slot. **The inflation was
about +0.001 and the decision survives**, but the numbers are restated rather
than quietly kept.

**`check_dynamic_pt_coverage()` did not catch it, and now does.** It verified
that every name in the set resolves to a real card and that no 0/0 candidate
was missing from it — Ka-Zar passed both, because it IS a real card and it is
NOT 0/0. The new third assertion is the one that matters: **a card in
`DYNAMIC_PT_LANDS` that is not defined 0/0 is an error**, because `*/*` cards
in this project are defined 0/0 by convention and anything else is having its
real P/T silently thrown away. Mutation-tested against this exact bug.

Two process notes worth keeping:

- **The Pool HUNG rather than reporting.** The workers died inside
  `_init`, and `pool.map` waited forever, so a crash presented as a slow run
  and burned a 600-second timeout before anyone looked at stderr. If a
  harness stalls, read the worker traceback before assuming it is slow.
- **The baseline moved underneath the harness.** `run_azusa_draw.py` built its
  baseline from `build_pending("azusa")`, and once Ka-Zar and the draw land
  were themselves staged, that baseline CONTAINED THE CARDS UNDER TEST — so
  every leg tried to add a second copy. That is §0o from the other direction:
  not a stale hand-written list, but a baseline that moved because the
  harness's own results had been staged. The baseline is now pinned explicitly
  to the three swaps that are not under review.

---

<a id="0z4"></a>

## 0z4. MEASURED — seven more candidates, and the deck says the same thing again

2026-09-10. `tools/candidates.py azusa3`,
`results/candidates_azusa_batch3_T20.txt`, mechanisms in
`results/azusa_batch3_mechanisms.txt`, engine work in `edhmc/azusa.py`,
mechanisms pinned by `tests/test_azusa_batch3.py`.

N=15,000 paired, T20, measured as value over a replacement-level slot in the
Sylvan Library slot — the deck's most neutral row (−0.0002 ±0.0017, signal
`--`, and the one enchantment with no script at all, so removing it from both
legs removes nothing the engine was modelling). Deck noise floor ±0.0029.

### The result

| card | MV | damage T20 | win rate T20 | signal |
|---|---|---|---|---|
| **The Great Henge** | 9 → ~4 | +1.85 ±0.21 | **+0.0217 ±0.0034** | both |
| **Nissa, Who Shakes the World** | 5 | +2.40 ±0.25 | **+0.0215 ±0.0036** | both |
| **Return of the Wildspeaker** | 5 | +1.83 ±0.20 | **+0.0197 ±0.0033** | both |
| **Sapling Nursery** | 8 → ~3 | +2.14 ±0.23 | **+0.0170 ±0.0034** | both |
| Finale of Devastation | 8 (X=6) | +0.76 ±0.14 | +0.0073 ±0.0025 | both |
| War Room | land | +0.51 ±0.18 | +0.0052 ±0.0031 | both |
| Castle Garenbrig | land | +0.03 ±0.19 | **−0.0029 ±0.0032** | `--` |

**THE TOP FOUR ARE A SET, NOT A RANKING.** +0.0217, +0.0215, +0.0197 and
+0.0170 all sit inside each other's bars, and they share a baseline, so they
cannot be ordered against each other — §0c's standing point. Placed against
the deck's own table they land around Oracle of Mul Daya (+0.0221), Harmonize
(+0.0220) and Courser of Kruphix (+0.0197): top-fifteen cards, not top-five.

### THE FINDING, WHICH IS THE SAME ONE AS LAST TIME

**Every card that attacks the CARD constraint passed, and every card that adds
MANA failed.** The draw batch's measurement was that this deck is granted 2.77
land drops a turn and uses 1.33, and that everything scoring well attacks
cards rather than mana (§0z2). Four new data points, all agreeing:

- The Great Henge draws **7.65 cards per resolution** and gains 1.46 life.
- Return of the Wildspeaker draws **7.8**.
- Nissa is the exception that proves it — she is a mana card, **+19.95 mana
  spent per resolution**, and what she actually converts it into is landfall
  (+3.59 triggers) and an ultimate that fires in **41% of the games she
  resolves in**, putting every Forest left in the library onto the battlefield.
- **Castle Garenbrig, pure mana, is the only card of the seven inside its own
  bar** — and its `mana_spent` goes DOWN 9.68 per resolution. It activates 0.81
  times a game and spends 3.72 of the six {G} it makes; the rest evaporates.
  A deck that already floats mana it cannot spend gains nothing from more.

### Sapling Nursery COMPETES WITH THE ENGINE ALREADY THERE

Worth its own note, because the win rate (+0.0170) and the mechanism counters
point in opposite directions and the mechanism is the interesting half.
Sapling Nursery has the **second-highest damage of the seven** (+2.14) and adds
+2,449 board power per resolution — and it makes the deck's landfall engine
**worse**: `landfall_triggers` −0.87 and `tokens_made` **−11.55** per
resolution. Its own 3/4 Treefolk are counted in that figure, so Scute Swarm is
making ~14 fewer Insects.

The mechanism is sequencing. Even at its affinity-reduced cost the Nursery
takes mana and a turn, and in a deck whose payoff is **exponential** — Scute
Swarm copies itself on every landfall — a small delay compounds. It is still a
good card here. It is a good card that makes the best card slightly worse, and
a leave-one-out table cannot see that at all.

### THE CEILING ON RETURN OF THE WILDSPEAKER, said out loud

The draw mode is chosen essentially always: **0.10 pumps per resolution**, so
the `auto` policy in `azusa.return_of_the_wildspeaker` almost never finds a
pump that kills somebody the raw attack would not. Fine, and honest.

What is not free is the draw. **It asks for 30.0 cards a resolution and
receives 7.8** (total `cards_drawn` rises 8.2 — the extra 0.4 is knock-on, the
cards it drew finding Horn of Greed and Seer's Sundial draws of their own),
because "the greatest power among non-Human creatures" on a
Craterhoof-pumped Scute Swarm board runs into the hundreds — Ashaya and
Greensleeves are `*/*` on the land count, Zabu takes a counter on every
doubled landfall, and `craterhoof_bonus` is added on top. Measured directly:
median 9, mean 40, and 9% of resolutions ask for 50 or more.

**`draw()` stops at an empty library and NOTHING IN THIS PROJECT LOSES TO
DECKING.** The tail is therefore free in a way it is not at a table, where
drawing 30 means winning that turn or dying to the next draw step. Its
+0.0197 is a CEILING. The card is still good on the median case — nine cards
for five mana at instant speed is good on its own — but the tail is not
priced. This has never mattered before because nothing in any list drew more
than three at once; it is live now, and it would be live for any future
draw-X card. NOT fixed, because a decking rule is an engine-wide decision.

### Finale of Devastation and the fixed-X convention

+0.0073 ±0.0025, the weakest of the five nonlands, and the number that most
depends on a modelling choice. X is fixed at 6, the convention Genesis Wave
(6) and Animist's Awakening (4) already use, so this is an approximation
rather than a floor or a ceiling: a real pilot scales X to the mana, and this
deck has a lot of it. The graveyard half IS modelled and earns its keep —
**35% of its targets come from the graveyard** rather than the library.

The likelier reason it scores where it does is REDUNDANCY, the
Conduit-of-Worlds shape: Green Sun's Zenith (+0.0166), Chord of Calling
(+0.0097) and Woodland Bellower (+0.0119) already tutor creatures in this
list, and a fourth tutor finds what the first three did.

### War Room against the sac-lands it competes with

+0.0052 ±0.0031, measured against a Forest, which is exactly how §0z3 measured
the four sacrifice-lands — so these five are directly comparable:

| land | win rate T20 |
|---|---|
| Scene of the Crime (committed) | +0.0096 ±0.0038 |
| Horizon of Progress | +0.0081 ±0.0030 |
| Cryptic Caves | +0.0068 ±0.0032 |
| **War Room** | **+0.0052 ±0.0031** |
| The Hunter Maze | +0.0039 ±0.0032 |

It draws 0.91 cards a game and is **repeatable**, where the other four are
one-shot — and it still lands mid-pack, for §0z3's reason: **the tap is the
binding constraint.** {3} AND a tap is the most expensive draw of the five, so
it fires least. Its life payment is real and charged (one life, mono-green),
which makes it one of the few life costs in this project that is not free
(§0i) — and `final_life` still goes UP +0.74, because drawing cards ends games
sooner than the life costs.

### Engine work this required, and what is still a floor

Seven cards, five of which needed mechanisms the engine did not have. Full
detail in `edhmc/azusa.py`; the limits, in one place:

- **Two dynamic costs**, in `cost_of` and checked by
  `check_dynamic_cost_coverage()`: The Great Henge at {7}{G}{G} minus the
  greatest power you control, Sapling Nursery's Affinity for Forests. Both
  cards are unplayable at their printed cost and the reduction IS the card —
  the Henge resolves in 28.1% of games, the rate of a four-drop.
- **A mana doubler needs saying twice.** Nissa's Forest doubler is in
  `azusa.available_mana` (the pool) AND in `engine.spend` (one Forest covers
  two units). With only the first, paying {2} taps two Forests to make the two
  mana one of them made and the doubler is worth nothing. The `spend` change
  is the Crypt Ghast branch already there, guarded on a card in no other list;
  `tools/check_unchanged_decks.py` reports all six decks BIT-IDENTICAL.
- **Subtypes are now generated**, not hand-written: `HUMAN` and `FOREST` in
  `decks/_evasion.py`, from Scryfall's type line via `tag_flying.py`, for the
  §0q reason. This immediately caught two things a by-hand set gets wrong:
  **Dryad Arbor is a Forest** (so Nissa's −8 fetches 21 cards, not 20, and it
  pays affinity), and the shocklands in other lists are Forests too.
- **The Great Henge's ETB is hooked in `make_permanent`, not `resolve`**,
  which is queued item 16 from the other side: a creature enters from six
  zones in this engine and only one of them is `resolve`. A hook in `resolve`
  would miss every tutored creature.
- FLOORS, all stated: Return of the Wildspeaker is an INSTANT cast at sorcery
  speed; Sapling Nursery's {1}{G} exile-for-indestructible is not modelled and
  is real wipe protection; Finale's X≥10 team pump is not modelled; Nissa's
  emblem cannot matter (nothing in this pod kills lands) and her +1 grants
  vigilance, which this engine has no use for.

### Two bugs found on the way, both in the harness rather than the engine

1. **`candidates.py` measured land candidates against a NONLAND.** Its
   `blank_like` had an `is_land` branch that copied the type line and never
   set `is_land` or `produces`, so a land candidate was scored against a
   zero-cost spell that sat in hand. Dead code until now — `ablation.py`
   blanks only nonlands, and §0z3's lands were run as real swaps by
   `run_azusa_draw.py`. The replacement is `filler_land()`: the land the deck
   runs most copies of, derived rather than invented, which for this list is a
   Forest and is the slot a land candidate actually takes.
2. **A land never set the watch counters**, because they are set in `resolve`
   and a land is played in `land_step`. Every land candidate reported
   P(deploy) = 0.000 and `test_card_resolved` = 0 — "the card never arrived"
   for a card that arrived in 28% of games.

And one that was already there and is worth recording: **the `azusa` entry in
`candidates.py` can no longer run at all.** Its victim slot, Perilous Forays,
is cut by the staged Ka-Zar swap, and three of its nine candidates were
committed to the deck on 2026-09-10, so `add_value`'s §0o guard raises on
them. Both failures are loud, which is the guard working. The entry is kept as
provenance for §0x; `azusa3` is the live one.

---

<a id="0z5"></a>

## 0z5. FIXED — a token copy re-triggers the host's ETB, and it was worth nothing

2026-09-10, closing queued item 16. `diagnostics/run_springheart_etb.py`,
`results/springheart_etb.txt`, mechanisms pinned in
`tests/test_azusa_candidates.py`.

**The queued item called this "the largest remaining understatement of
Springheart". It is worth +0.0001 ±0.0002 and that is the finding.**

### What was wrong

`azusa.make_permanent` does not run the ETB dispatch that `resolve` does — the
dispatch was inline in `resolve`, so the ONLY way to trigger an ETB was to cast
the card from hand. Springheart Nantuko's "create a token that's a copy of that
creature" therefore produced a bare body: a copy of Avenger of Zendikar made no
Plants, a copy of Craterhoof Behemoth pumped nothing. The dispatch is now
`AzusaGame.etb(card, perm, is_copy=False)` and the copy path calls it.

### The measurement, N=15,000 paired, T20, same seeds in every leg

| leg | win rate | copies | ETBs | legend deaths |
|---|---|---|---|---|
| A baseline (bare body) | 0.3874 | 1.07 | 0.00 | 0.00 |
| B + copy ETB | 0.3875 | 1.07 | 1.07 | 0.00 |
| C + legend rule | 0.3875 | 1.07 | 1.07 | 0.00 |
| D + re-ranked hosts (shipped) | 0.3898 | 1.11 | 1.11 | 0.03 |

| step | win rate | |
|---|---|---|
| A → B, the fix itself | **+0.0001, p=0.16** | inside its bar |
| B → C, the legend rule | **0.0000, p=1** | never fires under the old host list |
| C → D, the re-rank | **+0.0023, p=4.8e-05** | significant |
| A → D, everything | **+0.0024, p=2.2e-05** | significant |

### WHY THE FIX IS WORTH NOTHING AND THE RE-RANK IS WORTH EVERYTHING

**Springheart makes 1.07 copies a game**, and under the old host ranking the
host was almost always Scute Swarm, Lotus Cobra or Tireless Provisioner —
**none of which has an ETB at all.** Their value is a LANDFALL trigger, which
the copy already got (§0z1). So the fix repaired a path that the policy almost
never walked.

**The host list was the real defect, and it is a `SCRIPTED_*`-shaped one.**
`SPRINGHEART_HOSTS` is a hand-written ranking, and Craterhoof Behemoth,
Woodland Bellower, Eternal Witness and Titania — the four the queued item names
as "exactly the copies a pilot most wants" — **were not in it.** They were
absent *because their ETBs did nothing*, so the list had encoded an engine
limitation as a judgement about cards, and fixing the engine did not fix the
list. That is §0q with a new disguise: not a stale name set, but a POLICY
calibrated against a bug.

### AND A SECOND BUG THE FIX EXPOSED: the legend rule

A token copy of a LEGENDARY creature is put into the graveyard immediately as a
state-based action. The engine kept it. Greensleeves, Maro-Sorcerer was rank 5
in the host list, so copying her left a permanent, illegal second Badger-maker
on the battlefield — **and `count()`-based landfall payoffs doubled off it**,
which is the §0z1 change making an older bug visible rather than causing one.

The rule is now applied, with the consequence that a legendary host is worth
**its ETB and nothing else**. That reverses two entries: Titania stays (her ETB
returns a land, and the land is the point), Greensleeves is **removed** (her
value is a landfall trigger her copy never lives to see).

It also **cascades, correctly**: Titania's ETB puts a land onto the
battlefield, that land entering IS another landfall, Springheart triggers
again. With two lands in the graveyard the chain runs three deep and stops
because the graveyard is empty — a real resource bound, not a recursion guard.
Pinned as a test; the check expected one copy and the engine was right.

### What this cost

`results/ablation_azusa.txt` regenerated: baseline win rate 0.3874 → 0.3898,
damage +0.09, tokens_made +2.09, final_board_power +1,159. Small, real, and
the table is keyed on it.

<a id="0z6"></a>

## 0z6. FIXED — Shilgengar's Treasures are mana, and the objective cannot see it

2026-09-10, closing queued item 13. `diagnostics/run_shilgengar_treasures.py`,
`results/shilgengar_treasures.txt`.

`self.treasures` was a counter that **only Revel in Riches read**. Pitiless
Plunderer, Smothering Tithe, Black Market Connections and Wayfarer's Bauble all
made Treasures and **nothing ever spent one**, so three of this deck's mana
sources were scored as producing no mana — and `ult_reserve()` held three mana
back through every main phase for an ultimate the Treasures could often have
paid for, a cost §0t measured and charged to the reserve policy.

`ShilgengarGame.pay()` now spends them, **real mana first** (a land is
repeatable and a Treasure is not), at every payment site in the engine; and
`ult_reserve()` returns 0 when the Treasures alone already cover the ultimate.

### The measurement, N=15,000 paired, T20, same seeds

| metric | inert | spendable | diff |
|---|---|---|---|
| treasures_spent | 0.00 | 1.45 | **+1.45** |
| shilgengar_ults | 0.446 | 0.488 | **+0.04 (+9.4%)** |
| blood_made | 3.19 | 3.47 | **+0.29 (+9.1%)** |
| damage | 52.04 | 53.73 | **+1.69 (+3.3%)** |
| mana_spent | 108.6 | 110.4 | +1.79 |
| **win rate** | 0.1972 | 0.1993 | **+0.0021 [−0.0007, +0.0049], p=0.15** |

**EVERY MECHANISM COUNTER MOVES DECISIVELY AND THE OBJECTIVE DOES NOT RESOLVE
IT.** Damage at p≈1e-96, ultimates at p≈3e-75, and win rate inside its bar.
This is the §0u shape exactly: a change that is unambiguously more correct,
visible in every counter that fires on a relevant turn, and below the
resolution of a per-deck win rate at this N. It ships because a Treasure IS
mana, not because the win rate asked for it.

### THE ASSUMPTION THIS PROMOTES, and it is the thing to watch

Smothering Tithe is modelled as **one Treasure per living opponent per round,
no roll** — written when a Treasure was inert, on the grounds that "opponents
nearly always have a better use for two mana early". That is now **three real
mana a turn in a model where the opponents never pay the {2}**. The assumption
has gone from harmless to load-bearing, and it is the first thing to suspect if
that card's row looks too good in the regenerated table. Treasures made per
game is only 1.92, so the exposure is bounded by how rarely these cards are
drawn, not by the assumption being cheap.

A second tension, now real: **a Treasure spent on mana is a Treasure not
counted toward Revel in Riches' ten.** That is the choice a pilot actually
faces and the engine now resolves it greedily in favour of mana.

`treasures_as_mana=False` restores the old behaviour exactly.
`results/ablation_shilgengar.txt` is regenerated against the new baseline.

---

<a id="0z7"></a>

## 0z7. FIXED — two life-loss drawbacks are charged, and one of them mattered

2026-09-10, closing the live half of §0i and queued item 10.
`diagnostics/run_life_costs.py`, `results/life_costs.txt`.

§0i has been a standing finding since pod v3 made your life total decide
roughly a third of losses: **cards whose drawback is losing life were not
paying it.** Two were live in committed lists.

| card | deck | oracle | was |
|---|---|---|---|
| Bitterblossom | rendmaw | "create a 1/1 Faerie, **and you lose 1 life**", every upkeep | free |
| Phyrexian Arena | karlov | "you draw a card **and you lose 1 life**" | free |

### AND THE SECOND ONE WAS ALREADY CHARGED SOMEWHERE ELSE

`edhmc/shilgengar.py` runs Phyrexian Arena too, and **it charged the life.**
`edhmc/karlov.py` did not. The identical card, two engines, two behaviours,
with nothing anywhere saying so — the §0u shape (three copies of the miracle
discount that had drifted apart) in a new place. This is now the fourth
instance of "the same rule implemented more than once and not the same way",
and it is worth taking as a standing hazard rather than four coincidences.

### The measurement, N=15,000 paired, T20, same seeds, `charge_life_costs`

| deck | free | charged | diff | |
|---|---|---|---|---|
| **rendmaw** (Bitterblossom) | 0.2081 | 0.2032 | **−0.0049 [−0.0061, −0.0038]** | p=1.2e-16 |
| **karlov** (Phyrexian Arena) | 0.3357 | 0.3343 | **−0.0015 [−0.0022, −0.0007]** | p=1.0e-04 |

**Both significant, and Bitterblossom's is large for one card's drawback.**
The mechanism is not the size of the payment but WHERE rendmaw's life total
sits: the deck finishes on a mean of 3.01 life, so it is at death's door in a
large share of its games, and 3.32 life — what Bitterblossom costs in the games
it resolves in — is most of that margin. It resolves in 19.5% of games on turn
6.9 against a mean game length of 12.4 turns.

§0i predicted "its +0.0205 is a CEILING, and now knowingly so". That is
confirmed: the ceiling was about a quarter of the card's measured value.

### NOT FIXED, and it is the one that cannot be

**Talisman of Conviction** (lorehold) deals 1 damage to you per COLOURED tap.
`spend()` taps a source without recording which colour it produced, so the
engine cannot tell a coloured tap from a colourless one. Charging every tap
would overcharge it and charging none is what happens now. Left free, said out
loud, and it would need the mana model to carry the colour actually spent —
which is a larger change than this card is worth.

Dark Confidant (a karlov candidate) was ALREADY charged, correctly,
`your_life -= float(top.mv)`.

`charge_life_costs=False` restores the old behaviour. `results/ablation_rendmaw.txt`
and `results/ablation_karlov.txt` are regenerated against the new baselines.

---

<a id="0z8"></a>

## 0z8. FIXED — the engine proved one payment and then made a different one

2026-09-11, raised by a question about how multicoloured costs are handled
rather than by a diagnostic. `diagnostics/run_mana_colour.py`,
`results/mana_colour.txt`, pinned by `tests/test_mana_colour.py`.

### What was wrong

`can_pay` has always been colour-correct and careful: coloured pips first,
each taking the most constrained source that works; generic last, from the
least flexible leftovers so duals survive. **It returns the exact indices it
assigned.**

`spend` took those indices and used `len(pay_idx)`. Nothing else. It then
tapped that many permanents in cheapest-to-lose order, so **which land was
actually tapped was decided by the order the lands happened to be played.**

    one Plains, two Mountains, pay {2}
      can_pay assigned  Mountain + Mountain
      spend tapped      Plains + Mountain      -> a {W} card in hand: dead

    the SAME position, Plains played last
      spend tapped      Mountain + Mountain    -> the {W} card: castable

The affordability question ("can I cast this {1}{W}{B}?") was therefore
answered correctly all along, and the consequence of the answer was not.

### THE CORRECT IMPLEMENTATION WAS ALREADY IN THE REPO

`edhmc/tivit.py` does not use `engine.spend`. Its own `pay()` walks the board
positionally and maps `can_pay`'s indices back to the permanents that produced
them — which is exactly the fix — and it was written that way for the Esper
deck, the one where colour bites hardest. **Five engines shared a rule that one
engine had already found wrong and quietly worked around.** That is the FIFTH
instance of the same-rule-implemented-twice hazard (§0u, §0z7, §0z4's mana
doubler, §0z4's two `blank_like`s) and the strongest one yet, because here the
correct version was sitting in the same package the whole time.

### The fix

`available_mana` now returns a `ManaUnits` — a `list[frozenset]` to every
caller, so all six engines' call sites are untouched — carrying the OWNER of
each unit and a per-unit `tap_reluctance`. `spend` taps the owners of the
indices it was given. Three further pieces were needed:

1. **THE TAP ORDER HAD TO MOVE, NOT DIE.** `spend`'s ordering encoded a real
   policy — lands before rocks before mana creatures, so a dork can still
   attack — and honouring the assignment would have silently discarded it. It
   is now a tie-break inside `can_pay`, so the assignment is made in that order
   and the property is preserved. Pinned as a test.
2. **SCARCITY.** "Least flexible leftovers" treats a Plains and an Island as
   interchangeable, so the tie fell to board order and a lone white source got
   spent on a generic cost. Generic is now paid from the MOST PLENTIFUL colour
   first.
3. **THE HAND BREAKS A TRUE TIE.** With one Plains and two Mountains, paying
   {1}{R} leaves one of each and scarcity cannot choose. `available_mana` has
   the game, so it scores each source by how many coloured pips the cards in
   HAND still want, and the Plains is kept only when something actually needs
   white. Verified both ways.

`lorehold.pay` needed a matching correction: it passed `list(range(n))` to
`spend` rather than the chosen indices — harmless while `spend` counted, and
wrong the moment it stopped.

### WHAT IT IS WORTH: NOTHING MEASURABLE, AND THAT IS THE RESULT

Colour is the binding constraint — enough mana, wrong colours — on 1.1% to
8.1% of all payment attempts depending on the deck (karlov worst, azusa and
lorehold least). But across all six lists at N=6,000 per cell the win-rate
difference is **indistinguishable from zero**, and it does not grow as the
mana base is degraded. The numbers are in `results/mana_colour.txt`.

**THE FIRST EXPERIMENT TESTED THE WRONG VARIABLE**, and that is worth keeping.
Cutting lands was the obvious way to model a greedy build, and it found
nothing — because a deck short of lands fails by being SHORT, which is exactly
the failure population this fix cannot touch. The second variant holds the
mana COUNT constant and replaces fixing with basics, which is the condition
that actually produces colour screw. It is the right test and it also finds
nothing.

### AND THEN KARLOV WENT NEGATIVE, WHICH TOOK THREE WRONG GUESSES TO EXPLAIN

On a deliberately colour-starved Karlov the fix measured **−0.0118 ±0.0076** at
six lands skewed — worse, significantly, and getting worse as the mana base
degraded. A fix that is provably more correct and measurably harmful is not
shippable until the mechanism is known, so it was chased rather than argued:

* **"It wastes multi-unit sources."** Crypt Ghast makes a Swamp produce two
  units and the old count-based `spend` packed them implicitly. Plausible,
  and WRONG: mana per tap was 1.004 legacy against 1.009 fixed. An
  owner-packing preference was added anyway — a second unit off an
  already-tapped permanent is genuinely free — and changed nothing, because
  units of one owner are adjacent and ties already broke that way.
* **"It is the hand-demand heuristic."** Disabling it left the loss intact.
* **"Scarcity is backwards."** This one was half right. Ranking by scarcity
  alone preserves the RAREST colour, which is wrong when the rare colour is
  not the one the deck needs — on a Swamp-heavy Karlov it hoarded the odd
  Plains. Replaced by SURPLUS, supply minus what the hand wants. It helped
  and did not close the gap.

The answer came from bisecting a single game to the one turn where the two
diverged (seed 98108, turn 12). Both hold the same four cards — Farewell
`{4}{W}{W}`, Lurrus `{1}{W}{B}`, Sanguine Bond `{3}{B}{B}`, Voice of the
Blessed `{W}{W}` — and both cast Sanguine Bond first. Then:

    LEGACY  burned a Plains paying generic, leaving ONE white source.
            Voice {W}{W} was therefore unaffordable, so it fell through and
            cast LURRUS -- the better card.
    FIXED   correctly preserved BOTH white sources. Voice {W}{W} became
            affordable, Voice has the higher `priority`, so it was cast --
            and LURRUS was locked out for the rest of the game.

**THE MANA CODE DID EXACTLY ITS JOB AND THE CASTING POLICY SPENT THE PROCEEDS
BADLY.** `main_phase` is greedy on `priority` and never asks whether casting
the cheaper card now makes the better one uncastable. The colour fix hands
that policy more options and it sometimes uses them worse.

That is §0z5's lesson for the second time in two days: **a policy calibrated
while a bug was open does not become right when the bug is fixed.** These
decks' `priority` numbers were tuned in a world where which land got tapped
was effectively arbitrary. The loss is NOT evidence against the mana fix; it
is evidence that `priority` is now the weakest link in the casting policy, and
it is only visible at all on a mana base far worse than any real list's.

So this ships as a CORRECTNESS change, on the same footing as §0z6:

* the engine no longer proves one payment and makes another;
* **board order is no longer a hidden input** to whether a spell is castable,
  which was the part that could have produced a result nobody could trace;
* and the owner mapping is the thing §0z7 needed and did not have — Talisman
  of Conviction's "1 damage per COLOURED tap" is now expressible, because the
  engine finally knows which permanent produced which colour.

`mana_colour_legacy=True` restores the old rule — BOTH halves of it, the
count-based tapping and the flexibility-only sort — and reproduces every
number published before 2026-09-11.

---

<a id="1"></a>

## 1. PARTLY RESOLVED — alternative costs and X-spell mana values

`Card` now carries `alt_costs`, a tuple of `(cost_dict, tag)` alternatives, and
the casting policy tries them when the printed cost is unaffordable. First user:
**Overlord of the Hauntwoods**, which can now be deployed via **Impending 4** for
{1}{G}{G} instead of {3}{G}{G}, entering as a noncreature enchantment (excluded
from combat) until turn+4. It fires in 8.7% of games; the card's ablation moved
from **-0.14 ±0.76 damage** to **+1.48 ±0.39**, i.e. from unmeasured to
significantly positive. The single-cost assumption had been hiding a real card.

`Card.x_pips` records how much of a cost stands in for {X}, and `free_mv` returns
`mv - x_pips` — the mana value a card has anywhere but the stack. Used by every
place that copies or free-casts: Arcane Bombardment, Mizzix's Mastery, The
Dawning Archaic, Galvanoth, Double Vision.

| card | cast MV | MV in graveyard |
|---|---|---|
| The Meathook Massacre `{X}{B}{B}` | 4 (at X=2) | **2** |
| Debt to the Deathless `{X}{W}{W}{B}{B}` | 6 (at X=2) | **4** |
| Toxic Deluge `{2}{B}` | 3 | **3** |
| Culling Ritual `{2}{B}{G}` | 4 | **4** |

Two mistakes were made and corrected here, both worth remembering:

1. **Toxic Deluge and Culling Ritual are not X spells.** Toxic Deluge's X is a
   life payment ("as an additional cost, pay X life") and Culling Ritual's is a
   count of permanents destroyed. Neither has {X} in its mana cost, so their
   mana values are fixed at 3 and 4. Scryfall states it directly: "you'll still
   choose a value for X and pay X life. This is because it doesn't have {X} in
   its mana cost." A card reading "X" in its text box is not an X spell.
2. **A real X spell's graveyard MV is the fixed portion, not zero.** `{X}{B}{B}`
   is MV 2 in the graveyard, not 0. The first implementation returned 0 for all
   of them, which was wrong in the opposite direction.

Debt to the Deathless was also under-costed in the Karlov deck file at
`{gen 2}{W}{B}`; corrected to `{gen 2}{W}{W}{B}{B}`.

**Still open:** the mechanism is only wired into the Rendmaw engine's casting
loop, and nothing uses it for overload, evoke, escape, or kicker. Mizzix's
Mastery remains a hand-written special case in `lorehold.py` rather than an
`alt_costs` entry.

> **Re-checked 2026-09-05: accurate.** `grep -rn alt_costs edhmc/` hits
> `engine.py` and the deck modules and nothing else — neither `lorehold.py` nor
> `karlov.py` reads it. Overlord of the Hauntwoods is still the only user.

<a id="1b"></a>

## 1b. (original entry) Cards can only have one cost — structural

The engine gives every card exactly one mana cost and one mana value. Every error
found in the audit was a violation of that single assumption:

- **Mizzix's Mastery** — overload is a second alternative cost, and it cannot be
  combined with miracle. *Fixed*, but only as a special case in `main_phase`.
- **Overlord of the Hauntwoods** (Rendmaw) — Impending 4 lets you cast it for
  {1}{G}{G} instead of {3}{G}{G}, entering as a noncreature enchantment for four
  turns. Not modelled. Understates the card's early flexibility.
- **X spells** — Toxic Deluge, The Meathook Massacre, Culling Ritual all have
  **MV 0 in the graveyard**. The engine stores 3, 4 and 4. Harmless in Rendmaw
  today, but the Lorehold engine reads graveyard MV constantly (Bombardment
  copies ~1.6/game, Archaic free casts ~0.4, Mastery ~0.3), so any X spell added
  to that deck would silently inflate `mv_cheated`.

The real fix is to let `Card` carry a list of castable modes rather than a single
cost, and have the casting policy choose among them. That closes the whole
category instead of patching instances, and it is worth doing before many more
modal cards get added.

<a id="2"></a>

## 2. RESOLVED — Hagra Mauling is now a proper MDFC

Defined with `land_face=("B", True)` and a {2}{B} instant front face, like the
Lorehold three. Rendmaw now reads as 35 true lands plus one MDFC land face, and
the engine plays whichever face it needs. Baseline effect was negligible, which
is the expected result for one flexible card.

<a id="3"></a>

## 3. Ashnod's Altar and Deathreap Ritual remain unresolved

Both still ablate slightly negative (−0.28, −0.19) and neither result should be
trusted. The Altar's mana arrives after the main phase in the engine's turn
structure, so it cannot be spent — modelling the cost without the benefit. Valuing
it properly needs sacrifice mana to feed back into casting, which is an engine
change, not a card script.

> **Re-checked 2026-09-05: still true, numbers refreshed.** On the current table
> Ashnod's Altar is −0.26/−0.36 damage and −0.0013 win, Deathreap Ritual is
> −0.40/−0.45 and −0.0008 — both **inside their win-rate bars**, i.e. unmeasured
> rather than bad. The Altar is now gated to fire only alongside Blood Artist or
> The Meathook Massacre, so it no longer pays a cost for nothing, but its mana
> is still unspendable.

<a id="4"></a>

## 4. Opponents' boards are a blocker count

This is the deepest limitation. Swords to Plowshares, Path to Exile, Chaos Warp,
Generous Gift, Assassin's Trophy, Beast Within, Toxic Deluge and Culling Ritual
cannot be evaluated at all, because there are no opposing permanents to remove.
About 28 of 63 Rendmaw cards and a similar share of Lorehold sit in this bucket.
They ablate to ~0.00 and **that is a fact about the model, not the cards.**

<a id="5"></a>

## 5. RESOLVED — your own board wipes now hit your own board

Wipes carry a `wipe` tag (`onesided` for Massacre Wurm and Orlorin's Searing
Light, which spare your side). On resolution they clear the opponents' boards and
your own, and deaths route through `on_creature_death` so aristocrats drains
still fire.

The casting policy needed the more careful work: a greedy engine will happily
wrath its own winning board. `should_cast_own_wipe()` gates it on board state —
only sweep when the table's creature count meaningfully exceeds yours
(`wipe_threshold`, default 1.4).

Effect on baselines (5,000 games, T20):

| deck | win before | win after | own wipes cast |
|---|---|---|---|
| Rendmaw | 0.309 | 0.299 | 0.12 |
| Lorehold | 0.258 | **0.186** | 1.38 |
| Karlov | 0.455 | **0.378** | 0.52 |

Lorehold casts 1.38 of its own sweepers a game, and paying for them properly
costs it seven points of win rate. Every Lorehold number from before this change
is optimistic.

<a id="6"></a>

## 6. RESOLVED — life totals are tracked

Resolved as a side effect of the opponent clock. `your_life` starts at 40, is
reduced by threat-weighted incidental damage each turn, and is read by Storm
Herd's X, Felidar Sovereign, Aetherflux Reservoir and Serra Ascendant. This entry
sat stale for several sessions claiming otherwise — worth re-auditing the rest of
this file against the code rather than trusting it.

<a id="7"></a>

## 7. Unmodelled recursion in Lorehold

Copy-from-graveyard is modelled (Bombardment, Mastery, Dawning Archaic). True
recursion is not: Invoke Calamity's free graveyard cast, Volcanic Vision's return
to hand, Apex of Power's "add 10 red mana if cast from hand", Scrap Trawler / Myr
Retriever / Junk Diver in Rendmaw. All of these **understate** their cards, which
is the safer direction to be wrong.

> **Re-checked 2026-09-05: accurate, and one correction.** Apex of Power's clause
> is "add ten mana of **any one color**", not ten red, and it is the same card
> §0e flags as mislabelled — Apex is in `SCRIPTED_LOREHOLD` while implemented as
> `draw4`. Invoke Calamity, Volcanic Vision, Scrap Trawler, Myr Retriever and
> Junk Diver are all correctly in `KNOWN_BLIND`; Apex is not.
>
> Add to the list: **Goliath Daydreamer** is not merely unmodelled, it is
> anti-synergistic in a way nothing in the engine can see. It exiles your
> instants and sorceries with dream counters *instead of* putting them in the
> graveyard — which starves Arcane Bombardment, Mizzix's Mastery, The Dawning
> Archaic and Radiant Scrollwielder, all of which feed on that graveyard. It is
> correctly in `KNOWN_BLIND`, but a future measurement of it must not be read as
> "an unmodelled upside" — the unmodelled part cuts both ways.

## RESOLVED — opponents now have a win condition

Each opponent draws a kill turn from a bracket-calibrated range, pre-rolled from
the dedicated opponent RNG stream so common random numbers survive. When a clock
comes due the target is **threat-weighted** — the biggest board at the table
draws the kill, so being ahead now carries a real cost. If the clock misses you
it eliminates a rival and **re-arms**, because a deck that just killed someone
has not stopped being a problem.

Clock ranges, calibrated from bracket descriptions and then corrected against
the pod actually being played (the top seat behaves like a 3.5, not a true
bracket 4):

| bracket | threatens lethal |
|---|---|
| 2 | turns 13-18 |
| 3 | turns 10-14 |
| 4 | turns 8-12 |

Resulting four-player win rates against a mixed 2/3/4 pod, 5,000 games:
Rendmaw **0.307**, Lorehold **0.253**, mean game length 12.1 and 12.9 turns.
Both sit near the 0.25 baseline a four-player race should produce.

**The horizon parameter is gone.** Win rate is flat from a turn cap of 16 to 30
(0.280 / 0.298 / 0.298 / 0.277) because games now end on their own at ~12 turns.
Set the cap to 20 and forget it. `turns` is now a safety valve, not a modelling
choice.

Life totals are live as a consequence, so Storm Herd's X, lifelink and
Witch-Blessed Meadow's pay-3-life all mean something now (item 6 is partly
resolved).

## RESOLVED — error bars restored, all three decks re-run

`ablation.py` now prints 95% CIs on every figure plus a `signal` column
(both / dmg / win / --). All three tables regenerated at 2,500 paired games
against the current model, single horizon T20.

| deck | evaluated | significant on both | inside error bars |
|---|---|---|---|
| Rendmaw | 36 | 7 | 8 |
| Lorehold | 35 | 11 | 13 |
| Karlov | 45 | 15 | 11 |

**Roughly a quarter to a third of every evaluated card is statistically
unmeasured at this sample size.** Those rows carry a real point estimate and a
sign, and under the old format they looked rankable. They are not. Raise `N` if
a specific one matters.

<a id="6b"></a>

## 6b. Life is tracked — and since pod v3 it DECIDES GAMES

> **Added 2026-09-05.** Item 6 says life totals are tracked. Since pod v3 became
> the default they are also load-bearing: the life-share of losses is
> 0.32 / 0.43 / 0.20 rather than 0.00 / 0.00 / 0.00. Any note in this repo that
> says "life buys nothing" is describing pod v1. See §0i for the four cards
> whose life-loss drawback is still free.

<a id="8"></a>

## 8. (superseded) Re-run both ablations

**Now doubly stale — the opponent clock changes every number.** Every ranking in
`ablation_lorehold.txt` and `ablation_rendmaw.txt` predates the clock, the
mana-rock fix, the drain implementation, the nine model-blind implementations and
the Mizzix correction. The caches are cleared, so a fresh pass will pick up the
new baselines.

    python -m tools.ablation rendmaw 2000 20
    python -m tools.ablation lorehold 2000 20

With the clock in place a single turn cap is correct again, so the multi-horizon
reporting is now belt-and-braces rather than necessary.

---


## How to read an ablation table

Moved to **`docs/READING_TABLES.md`** on 2026-09-09 — it is methodology, not
an issue, and it was the only section of this file nobody could cite by
number. `CLAUDE.md`'s "Standing findings" is the short version.
