# Known issues — deferred, not blocking

> **RE-VERIFIED 2026-09-05.** Every card was re-checked against Scryfall with the
> rebuilt `audit_cards.py`, and every claim in this file was re-read against the
> code rather than trusted. See **§0** for what that turned up; items below it
> carry their original text with a dated verdict where one changed.
>
> `PENDING_CHANGES.md` is stale — it predates `lorehold_v16.py` and names four
> changes that no longer describe the ledger. `python -m edhmc.pending` is the
> only trustworthy statement of what is staged.

Ordered by how much they could distort a future result.

---

# 0. The 2026-09-05 re-verification

## 0a. Card DATA is clean — 0 errors across 269 distinct names

`audit_cards.py` (rebuilt; CLAUDE.md listed the original as lost) checks name,
mana cost, mana value, power, toughness, card types, `is_land`, `tapped`,
`produces` and `flying` for all 289 card slots in the three decks **plus every
module-level candidate**. It now reports **0 ERR**. The 52 data errors of
2026-09-03 are genuinely fixed and have not regressed.

    python audit_cards.py          # run it after any deck edit

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
  `shilgengar.aristocrats_step` is the obvious next suspect: its sacrifice
  policy is the reason the commander's ultimate fires zero times in 3,000
  games, and no equivalent coverage check exists there.

**The rule to carry forward: when you add a hand-maintained name set, add the
check in the same change, and prove the check fails.**

---

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

## 2. RESOLVED — Hagra Mauling is now a proper MDFC

Defined with `land_face=("B", True)` and a {2}{B} instant front face, like the
Lorehold three. Rendmaw now reads as 35 true lands plus one MDFC land face, and
the engine plays whichever face it needs. Baseline effect was negligible, which
is the expected result for one flexible card.

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

## 4. Opponents' boards are a blocker count

This is the deepest limitation. Swords to Plowshares, Path to Exile, Chaos Warp,
Generous Gift, Assassin's Trophy, Beast Within, Toxic Deluge and Culling Ritual
cannot be evaluated at all, because there are no opposing permanents to remove.
About 28 of 63 Rendmaw cards and a similar share of Lorehold sit in this bucket.
They ablate to ~0.00 and **that is a fact about the model, not the cards.**

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

## 6. RESOLVED — life totals are tracked

Resolved as a side effect of the opponent clock. `your_life` starts at 40, is
reduced by threat-weighted incidental damage each turn, and is read by Storm
Herd's X, Felidar Sovereign, Aetherflux Reservoir and Serra Ascendant. This entry
sat stale for several sessions claiming otherwise — worth re-auditing the rest of
this file against the code rather than trusting it.

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

## 6b. Life is tracked — and since pod v3 it DECIDES GAMES

> **Added 2026-09-05.** Item 6 says life totals are tracked. Since pod v3 became
> the default they are also load-bearing: the life-share of losses is
> 0.32 / 0.43 / 0.20 rather than 0.00 / 0.00 / 0.00. Any note in this repo that
> says "life buys nothing" is describing pod v1. See §0i for the four cards
> whose life-loss drawback is still free.

## 8. (superseded) Re-run both ablations

**Now doubly stale — the opponent clock changes every number.** Every ranking in
`ablation_lorehold.txt` and `ablation_rendmaw.txt` predates the clock, the
mana-rock fix, the drain implementation, the nine model-blind implementations and
the Mizzix correction. The caches are cleared, so a fresh pass will pick up the
new baselines.

    python ablation.py rendmaw 2000 20
    python ablation.py lorehold 2000 20

With the clock in place a single turn cap is correct again, so the multi-horizon
reporting is now belt-and-braces rather than necessary.

---

# How to read an ablation table

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
