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
measured on, so the comparison is sound — but **the two staged Lorehold changes
have never been measured together**, and that is the next thing to do before
either is written to the `.xlsx`.

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

## The rule, restated

1. Ignore anything inside its own error bars.
2. Where damage and win rate disagree, follow win rate.
3. Before cutting, ask whether another card in the deck does the same job — and
   if so, ablate them together.
