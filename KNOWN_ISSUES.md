# Known issues

Numbered findings, each with the evidence that produced it. **The section ids
are load-bearing** — `edhmc/azusa.py`, `tools/cache_manifest.py`,
`diagnostics/diag_azusa_animation.py`, `docs/ABLATION_CACHES.md` and
`CLAUDE.md` all cite them. Reorganise around them; **never renumber**. A new
finding takes the next free letter in the `0*` series.

`python -m edhmc.pending` is the only trustworthy statement of what is staged.
`docs/archive/PENDING_CHANGES.md` is stale, predates `lorehold_v16.py`, and is
archived for that reason. `docs/STATUS.md` carries the live ledger counts.

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
| [0f](#0f) | **CLOSED** | three Lorehold cards were not their text — all three implemented (§0z14) |
| [0g](#0g) | FIXED | two "or attacks" triggers, and one token entering untapped |
| [0h](#0h) | FIXED | "another creature you control": three cards triggered off themselves |
| [0i](#0i) | **CLOSED** | life-loss drawbacks are charged; Talisman was the last one (§0z13) |
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
| [0z](#0z) | **CLOSED** | Ashaya's clause implemented 2026-09-13 (§0z18); Quirion Ranger's ability still blind |
| [0z1](#0z1) | FIXED | landfall payoffs were booleans; Springheart bestow+copy implemented |
| [0z2](#0z2) | MEASURED | two card-draw candidates; Bane of Progress (mislabel fixed in §0z4) |
| [0z3](#0z3) | MEASURED | four sacrifice-lands: the TAP is the binding constraint, not the mana |
| [0z4](#0z4) | MEASURED | seven more candidates; **every mana card fails and every card card passes** |
| [0z5](#0z5) | FIXED | token copies re-trigger ETBs — and the fix is worth nothing; the RE-RANK is worth it |
| [0z6](#0z6) | FIXED | Shilgengar's Treasures are mana: every mechanism moves, the objective cannot resolve it |
| [0z7](#0z7) | FIXED | two life-loss drawbacks are charged at last — Bitterblossom costs **−0.0049** |
| [0z8](#0z8) | FIXED | the engine proved one payment and made another; **board order decided which land was tapped** |
| [0z9](#0z9) | FIXED | **"each opponent loses N" dealt up to 3N once the pod thinned** — six copies, five compensating call sites |
| [0z10](#0z10) | FIXED | your own sweeper ignored indestructible; the pod's did not. Sweepers classified from oracle text |
| [0z11](#0z11) | FIXED | `opponents.py` read the TYPE LINE, so a Planeswalker Grist died to every wrath |
| [0z12](#0z12) | FIXED | **tivit cast board wipes that did nothing** — and the policy held them until it was losing |
| [0z13](#0z13) | FIXED | §0i closed. **Its stated blocker had been false since §0z8, one day earlier** |
| [0z14](#0z14) | FIXED | §0f closed. **§0f's own prescription would have overstated the card** |
| [0z15](#0z15) | FIXED | four checks that could not fail, and one proposed fix that was a regression |
| [0z16](#0z16) | FIXED | **the same card, two decks, two contradictory labels** — and the checker is per-deck |
| [0z17](#0z17) | FIXED | **CRN leaked mid-game in eleven places; the A/A control could not see it.** No precision gained |
| [0z18](#0z18) | FIXED | **Ashaya's second clause implemented, +0.0140 win rate** — and the rules note said the opposite |
| [0z19](#0z19) | FIXED | **§7 closed — six recursion cards.** Lorehold +0.0220; the same stale-pool bug in both engines |
| [0z20](#0z20) | FIXED | **§3 and §1b closed.** The Altar's mana is spendable; alternative costs have a PREFERENCE and six readers |
| [0z21](#0z21) | MEASURED | **six Azusa candidates; two of them land in the deck's top ten** — and a land creature was tapping for mana on arrival |
| [0z22](#0z22) | FIXED | **the tables got slower; `can_pay` was most of it.** 1.22x per game, 1.45x on an azusa table, bit-identical |
| [0z23](#0z23) | **CLOSED** | the cache manifest described ten files that no longer existed, and "delete any cache whose fingerprint differs" was too expensive to obey. **Replaced by BUILT-AT provenance and a seconds-long evidence check** |
| [0z24](#0z24) | FIXED | **`FLIP` is assigned on an unguarded sign and overrides `--`** — 11 of 22 FLIP rows across six tables would read "unmeasured" on their own merits |
| [0z25](#0z25) | MEASURED | **three azusa proposals implemented and measured** — and one proposal's own rationale was backwards. **Guardian Project's +0.0481 was measured on a doubled draw and is corrected to +0.0279 in §0z28** |
| [0z28](#0z28) | FIXED | **The Great Henge's draw was swallowed into Guardian Project's branch, so one drew never and the other drew twice** — and the test that pinned it had been failing for three commits with nothing running it |
| [0z26](#0z26) | MEASURED | **the remaining ten proposals implemented and measured across four engines** — two are blanks for legible reasons, three are floors |
| [0z27](#0z27) | MEASURED | **two swaps staged on head-to-head evidence, and the karlov regeneration shows redundancy rewriting five rows at once** |
| [0z29](#0z29) | FIXED | **Bloodthirsty Conqueror was measured as a GROUND creature** — `_evasion.py` had not been regenerated since the card was added, and no fingerprint could see it. Flying is worth nothing to the card (its value is the trigger), the karlov table is rebuilt anyway, and `check_docs` now fails on a card the generator never scanned |
| [0z30](#0z30) | FIXED | **One opening hand and one pod-phase order for six engines.** Three mulligan fallbacks (a fifth hand; an empty hand; 106-card games) and two pod orders were six copies of two blocks. Unifying them moves tivit's baseline +0.0647 and karlov's +0.0205 at T20 — the two engines had let the opponents' creatures grow BEFORE dealing chip damage — and moves lorehold and azusa on 3 and 2 seeds of 15,000 |
| [0z31](#0z31) | FIXED | **`engine.Metrics` and an importable `ablation.py`.** The metrics dict reads 0 for a name nothing wrote (35 defensive `m.get(k, 0) + 1` spellings folded into `+=`); ablation's run parameters are a `Run` object passed down instead of `sys.argv` read at import, and its table renderer is a pure function — so "the committed table IS the committed cache" is a test now, over all six decks |
| [0z32](#0z32) | FIXED | **A thin base class and one deck registry.** `engine.BaseGame` holds `has`/`count`/`draw`/`deal_pod_damage`/`opening_hand` once and `engine.finish()` the `simulate()` tail; `edhmc/registry.py` holds one `DeckSpec` per deck, checked against `decks/` at import, and eleven per-deck dicts derive from it. Bit-identical on every baseline metric; the only output key that moved is karlov's `turn_lethal` |
| [0z33](#0z33) | MEASURED | **Anointed Procession restated on the post-§0z30 tivit baseline: +0.0157 ±0.0043 at T20 (was +0.0145), the staging stands** — with the review's L2–L5 housekeeping: main guards, notes as data, a legacy-switch policy, and a dead duplicate card definition found on the way |
| [0z34](#0z34) | FIXED | **The procedure for adding a card is written down** — `.claude/skills/add-card/SKILL.md`, from Scryfall to a committed swap, each step naming the check that catches the mistake made at it. And `check_docs` now verifies the §ids cited from live DOCS, not only from code: 194 citations, the pointers that make the procedure traceable |
| [0z35](#0z35) | MEASURED | **Queued items 21 and 22 answered.** Azusa's top two candidates are measured EQUAL in the same slot (+0.0001 ±0.0040 at T20, directly paired — the ranking §0c says a common baseline cannot give), so the choice is the owner's and one rebuild. Karlov: Blood Artist's negative row is entirely §0j's two constants (text alone +0.0024 ±0.0011, POSITIVE); Swiftfoot Boots and Mother of Runes are real, and **the Boots are the cut** because `protection_cards` holds Mother of Runes alone. And `diag_threat_blank`'s blank had drifted a digit from ablation's since §0j — arm 1 reproduces the committed table now, on all ten rows |
| [0z36](#0z36) | MEASURED | **Karlov's staged cut is the wrong one, and the MODEL-BLIND card was the one to keep.** The Conqueror is +0.0401 ±0.0037 on Swiftfoot Boots against +0.0254 on Soulmender, and the gap is measured twice independently (+0.0125 ±0.0049 directly, +0.0147 by subtraction). The Boots' shroud is redundant with Mother of Runes — §0z27 pointed at a cut — while the blind card is still a one-mana body worth +0.34 lifegain triggers. And a swap whose cut is significantly negative is LARGER than its candidate row, not smaller: the Archive prices at +0.0168 against its own +0.0129 |
| [0z37](#0z37) | FIXED | **Floating landfall mana was paid with and never consumed** — `engine.spend` consumes a unit by tapping its owner and azusa's Lotus Cobra / Tireless Provisioner / Nissa mana had none, so one trigger funded every spell that turn. Worth **−0.0201 ±0.0036 win rate at T20** on azusa's baseline, 741 of 15,000 seeds ending differently: the second-largest baseline correction after §0z30. Fixed by giving the mana an owner (`FloatingMana`) rather than a fourth spelling of deduct-at-the-call-site |
| [0z38](#0z38) | FIXED | **Flashback did not exile.** `past_in_flames` removed the card before resolving it and `resolve_spell` filed it straight back, so with `flashback_cap` 6 and the pool recomputed per iteration one Past in Flames could cast the SAME spell six times — its +0.0102 ±0.0038 is inflated and needs restating. 702.34a says exile; the fix is `lorehold.exile_flashback`, a function so a mutation can switch it off. And two of that test's five mutations set flags no code read, so they broke nothing: when a mutation breaks nothing, suspect the mutation |
| [0z39](#0z39) | MEASURED | **The monarch is implemented. The +0.10 it first measured was the HARNESS**: `monarch_start` grants the crown on turn 1 and `first_attack_turn` is 3, so two of its three held turns were immunity no card can buy. Granted when a card could arrive it is +0.02 to +0.04. The owner's attack-threat correction is in (a FLOOR on `combat_share`, which deters a wide board and should not for the monarch) and does NOT counterbalance -- tripling the share costs 0.002. The crown is lost on the path that already models their creatures connecting (`incidental_damage`), because §4 leaves no creature to connect. Zero movement PROVED on all six decks across 425 numeric output keys, since nothing grants it and the roll is never consumed. **Its numbers are CEILINGS**: you are paid for your draws and charged nothing when an opponent holds it, because the pod does not draw cards. `monarch_loss_scale` decides the whole value and has NOT been swept |
| [0z40](#0z40) | MEASURED | **Ginger, Queen of Sweets: the first card to use the monarch, and it behaves like a six-drop.** The real swap against the cut item 22 named is **+0.0186 ±0.0033 at T20**, level with Alhammarret's Archive and well under Bloodthirsty Conqueror — and Conqueror → Ginger IN THE SAME SLOT is **−0.0210 ±0.0034**, so the ranking is measured and not inferred. P(resolves) 0.152, the crown held 1.03 turns, 2.96 Gingerbrutes a resolution. **The sacrifice clause fires 0.0000 times and is correctly implemented**: haste means combat taps the token before its own `{T}` cost can be paid |
| [0z41](#0z41) | FIXED | **Horn of Greed was tripled.** Its draw sat inside `_landfall_payoffs`, which Ancient Greenwarden and Traveling Chocobo run once per rep, so one land drop drew three. Greenwarden's own ruling: "an ability that triggers whenever you play a land won't trigger an additional time." Moved out of the loop; worth **−0.0049 / −0.0033** to azusa's baseline, and it flattered both doublers, so the Chocobo's staging was re-measured |
| [0z42](#0z42) | FIXED | **Decking loses (queued item 17), and the pilot had to be taught not to.** `engine.drew_from_empty` is 704.5b in the three draw paths. The rule ALONE decked azusa in 3.3% of games at T20, in the turns it had lethal on board -- a naive pilot cost it **0.022**. `engine.draw_is_safe` declines only OPTIONAL draws; at the swept reserve of 5 the rule costs azusa −0.0006 / −0.0012 and lorehold −0.0003 / −0.0021. Rendmaw, karlov, tivit and shilgengar are identical game for game -- **including karlov with Bolas's Citadel, whose number was never a decking ceiling** |
| [0z43](#0z43) | MEASURED | **The one-card cast lookahead is a measured NULL.** `engine.lookahead_pick` (queued item 18) reorders a cast when the greedy pick would strand a card that casting first would have kept; wired into all six `main_phase`s, it fires in 4-12% of games and moves win rate inside its bar in all twelve deck-horizon cells (largest +0.0010 ±0.0020). §0z8's SURPLUS rule already handles the ordering. `cast_lookahead` stays OFF; what is left of item 18 is the `priority` numbers themselves |
| [0z44](#0z44) | MEASURED | **The `priority` numbers: right in four decks, wrong in two.** Flattening each table costs 0.015–0.045 win rate, so the numbers matter; a ±2 sweep of every nonland card (760 arms, three disjoint seed blocks) confirms **no move at all** in rendmaw, lorehold, shilgengar or azusa, two in karlov (Felidar Sovereign up, Sorin, Solemn Visitor up: joint **+0.0099 / +0.0091**) and four in tivit, which ranked card draw above its token engines (joint **+0.0225 / +0.0211**). Mechanisms read off the win routes. **Measured, not adopted**: adopting moves two baselines and a staged card's own priority **ADOPTED 2026-09-25 for both decks; the karlov and tivit tables are stale until the owner's batched rebuild.** |
| [0z45](#0z45) | MEASURED | **Eight Reality Fracture numbers enter the ledger, each saying whether it still describes its deck.** Two are CURRENT (Proft, Lyra -- their decks are bit-identical since measurement); six are STALE because lorehold, tivit, karlov and azusa have all moved since, and azusa's two were measured against a cut that is no longer in the list |
| [0z46](#0z46) | FIXED | **Voice of the Blessed is indestructible at ten counters** (queued 8b). §0n kept it out of the static INDESTRUCTIBLE set, correctly, but that left the clause nowhere to live, so it was never indestructible at all. `opponents.indestructible_of`, beside `flying_of`; it saves Voice 0.016 times a game |
| [0z47](#0z47) | FIXED | **March of the World Ooze's Elephant** (queued 4), on the one opponent spell the model puts on your turn -- a counterspell -- through a new optional hook in `opponents.countered`. Writing it found **Arasta of the Endless Web** reading the same event a second way: a counterspell is an instant and made no Spider. Both read the hook now. Elephant +0.0014 ±0.0008 at T20; the hook +0.0017 ±0.0010; a floor |
| [0z48](#0z48) | FIXED | **Artist's Talent, all three levels** (queued 2). Level 2 was granted free on resolution and discounted CREATURE spells; levels 1 and 3 did not exist. Now bought with `{2}{R}` by a stated policy. The row barely moves (+0.0043 ±0.0040 vs the table's +0.0052) because the errors cancelled: **level 3 alone is +0.0031 ±0.0010**, level 2 alone is inside its bar, and the level-1 rummage is worth nothing measurable |
| [0z49](#0z49) | FIXED | **Storm Herd's X was a constant 40, and the largest row in lorehold's table sat on it.** X is your life total at resolution -- about 21 on average. The fix costs lorehold's baseline **−0.0271 ±0.0031** at T20 and takes the row from +0.0713 to **+0.0442 ±0.0039**. The blocker the audit cited ("this engine does not track life at all") had been false since pod v3 |
| [0z50](#0z50) | FIXED | **Radiant Scrollwielder's lifelink.** `deal_pod_damage` takes a required `spell` argument beside §0z48's `hits`. +0.0017 ±0.0007 at T20; against Caldera in the same slot the card still loses, −0.0085 ±0.0034 |
| [0z51](#0z51) | FIXED | **Ranger of Eos tutors two one-drops** instead of drawing two. Row +0.0091 ±0.0033 at T20 (+0.0067 as `draw2`); the difference between the two is inside its bar. SCRIPTED now |
| [0z52](#0z52) | FIXED | **Lurrus's hybrid pips**, paid and counted: `alt_costs` for {W}{W}/{B}{B}, and `engine.hybrid_pips` makes devotion read {W/B} as white (CR 107.4e). 1.3% of karlov games change; win rate inside its bar. Daxos's devotion toughness is left unimplemented because nothing reads toughness |
| [0z53](#0z53) | MEASURED | **Goldspan Dragon's head-to-heads** (queued 0c). It loses the Penance slot to Caldera (−0.0108 ±0.0027) and beats both named cuts at T20: **−Blasphemous Act +Goldspan +0.0162 ±0.0044** (significant at both horizons) and −Lightning Greaves +Goldspan +0.0084 ±0.0034. Staging is the owner's call, and the Blasphemous Act cut is a partly-modelled wipe |
| [0z54](#0z54) | FIXED | **One path for every free cast.** The Dawning Archaic, Invoke Calamity, Goliath's dream casts and Galvanoth each wrote their own subset of `resolve_spell`: an Archaic cast triggered Guttersnipe and nothing else, an Invoke cast from HAND triggered nothing, Galvanoth counted `mv_cheated` twice, Scrollwielder's card went back to the graveyard. `cast_free` is the one path. Worth **+0.0135 ±0.0031** to lorehold at T20; the Archaic's row +0.0006 → +0.0089 |
| [0z55](#0z55) | FIXED | **Approach of the Second Sun could never be cast twice**, so its win did not exist. Its "otherwise" -- seventh from the top, 7 life -- is in, and a second cast from hand wins, 0.09 games a game. **+0.0667 ±0.0043 at T20**, the largest single correction this project has made to one card; the row goes −0.0003 → +0.0666. A ceiling in one respect, named: the pod does not react to a known win in your library |
| [0z56](#0z56) | FIXED | **Benevolent Offering does both its sentences** -- three flying Spirits each way, then 2 life per creature -- where it was a flat 4 life. The test caught the first version choosing the lifegain opponent BEFORE the Spirits existed. +0.0035 ±0.0021; row +0.0089 |
| [0z57](#0z57) | FIXED | **Necropotence** skips the draw step and pays life for cards at the end step, where it was `draw2`. +0.0053 ±0.0028; row +0.0146. The amount is a POLICY, confirmed by the owner 2026-09-26: fill to 7 cards, down to 10 life (10 measured +0.0023 ±0.0011 better than the 20 first assumed) |
| [0z58](#0z58) | FIXED | **Twitching Doll was classified SCRIPTED with neither clause implemented**, and when the nest counters went in they fired 0.03 times a game -- the pilot attacked with it and tapped mana creatures last. Policy `doll_policy="nest"`: it stays home and taps for a counter each turn. +0.0090 ±0.0025; row +0.0023 → +0.0111 |
| [0z59](#0z59) | MEASURED | **Sunbird's decay (queued 0b-i) has no single cause.** Measured at all 22 commits since 2026-09-09 on the same seeds: −0.0019 at §0z8, −0.0027 at §0z9, +0.0010 at §0z17, −0.0011 at §0z42, +0.0016 at §0z49, each inside or near its bar. Net −0.0034 ±0.0035 at 6b4546e, inside its bar |
| [0z60](#0z60) | MEASURED | **The six-deck rebuild, 2026-09-26: 3h09m on four cores, and it moved exactly the decks the checks said it would.** Every cache CURRENT and `check_docs` green for the first time since §0z44. Shilgengar and azusa came back BYTE-IDENTICAL (0 of 122 rows moved), confirming their VERIFIED records; rendmaw moved one row (Twitching Doll); karlov 10, tivit 10, lorehold 17 -- all traceable to §0z44 and §0z47-§0z58 |
| [0z61](#0z61) | FIXED | **Menace.** Rendmaw has it and the blocking model did not: a chump-blocking defender spent one blocker on any attacker. MENACE is generated from Scryfall's keywords, and `chump` prices a menace attacker at two blockers, stopping the most power per blocker -- the old rule exactly when nothing has menace (a 400-board property test). +0.0123 ±0.0033 to rendmaw at T20 |
| [0z62](#0z62) | FIXED | **The pod reacts to a win it can see.** Once Approach has resolved and gone seventh from the top, `known_win_focus` (1.0) floors your share of the pod's removal and kills, and its recast is countered at the cap. Approach's row +0.0666 → **+0.0265 ±0.0041**; lorehold −0.0401. The counterspell half alone is worth −0.0008: the kills are the reaction. The knob is a judgement, put to the owner |
| [0z63](#0z63) | MEASURED | **Every staged swap re-measured on the rebuilt baseline**, and all six stand, significant at T20. Karlov's cut still favours Swiftfoot Boots over Soulmender, by less: +0.0075 ±0.0047 at T20 (was +0.0125). Goldspan for Blasphemous Act +0.0143 / +0.0119 |
| [0z64](#0z64) | FIXED | **Rendmaw has Treasures, and Pitiless Plunderer is measured**: a blank, +0.0014 ±0.0017 at T20. It does not rescue Ashnod's Altar (−0.0017 → −0.0012, sacrifices unmoved). The engine costs the committed list nothing (bit-identical) |
| [0z65](#0z65) | FIXED | **Commander damage (CR 104.3j) is modelled, for your commander**: lorehold +0.0137 ±0.0036 at T20 and 0.49 commander-damage kills a game; shilgengar +0.0071; karlov and tivit kill more opponents and win no more; azusa bit-identical |
| [0z66](#0z66) | FIXED | **Triage tiers 0 and 2 built** (item 23): 56 cards the screen calls blind play IDENTICALLY to a matched blank, and that exact test replaced the significance one, which failed 32 times on §0j's constants. **33 KNOWN_BLIND cards are acted on by the engine** -- the label is too strong |
| [1](#1) | PARTLY RESOLVED | alternative costs and X-spell mana values |
| [1b](#1b) | **CLOSED** | modes carry a preference; all six engines read them (§0z20) |
| [2](#2) | RESOLVED | Hagra Mauling is now a proper MDFC |
| [3](#3) | **CLOSED** | the Altar's mana is spendable (§0z20); fixing it did not rescue the card |
| [4](#4) | **OPEN** | opponents' boards are a blocker count — the project's oldest limit |
| [5](#5) | RESOLVED | your own board wipes now hit your own board |
| [6](#6) | RESOLVED | life totals are tracked |
| [6b](#6b) | MEASURED | life is tracked — and since pod v3 it DECIDES GAMES |
| [7](#7) | **CLOSED** | all six recursion cards implemented 2026-09-13 (§0z19) |
| [8](#8) | superseded | re-run both ablations |

The still-live gaps, in one place — **updated 2026-09-12, when §0f and §0i
were closed**:

| § | what is still missing |
|---|---|
| §0z2 | Bane of Progress is a one-sided wipe with the sidedness removed (§4). **Ashaya is CLOSED — §0z18**; Quirion Ranger's activated ability is still unimplemented |
| §0z11 | the BROADENING half: an animated land is a creature and should die to a wrath. Inert today, deliberate |
| §0z14 | Borrowed Knowledge's mode 1 counts an opponent's HAND, which the pod does not have — §4, not an omission |
| §4 | **opponents' boards are a blocker count.** The project's deepest limit; a third of every list sits here |

**§0f and §0i are CLOSED** (§0z14, §0z13). Everything else is either fixed or
was a question rather than a defect.

**If you are an agent picking this up:** read §0z9–§0z16 first. They are the
most recent batch and they changed five of six engines. **All six tables WERE
regenerated against them on 2026-09-12** — 19 of 378 rows moved beyond their
own old bar, one already-significant row flipped sign, and karlov and azusa
came back byte-identical. §0z15 and §0z16 carry the lessons most likely to save
you a wasted day: a check is blind exactly where it does not range — over
categories in §0z15, over the other five decks in §0z16 — and one "obvious" fix
in §0z15 is a regression with the measurement attached.

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

## 0f. CLOSED 2026-09-12 — three Lorehold cards were not their text

> **CLOSED BY §0z14.** All three are implemented. Apex of Power and Hit the
> Mother Lode moved to `SCRIPTED_LOREHOLD`; Borrowed Knowledge stays
> `PARTLY_MODELLED` because its mode 1 counts an opponent's HAND and this
> pod has none (§4) — unmodelable, not unimplemented. Worth **+0.0080 win
> rate, p=0.029.**
>
> **AND THIS SECTION'S OWN PRESCRIPTION WAS WRONG.** It tells the reader to
> reuse the `wheel` script for Borrowed Knowledge. A wheel draws a flat
> SEVEN; the card draws only what it discarded, so that would have
> OVERSTATED it — the opposite of the claim below that all three
> understate. The text below is kept as written. §0z14.

### The original entry

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

## 0i. CLOSED 2026-09-12 — life-loss drawbacks are charged

> **CLOSED BY §0z13.** §0z7 charged Bitterblossom and Phyrexian Arena;
> Talisman of Conviction was charged on 2026-09-12 (**−0.0015 win rate,
> p=0.014** on lorehold). Dark Confidant is a karlov CANDIDATE and has no
> row in any table, so it was never live.
>
> **THE BLOCKER THIS SECTION STATES HAD BEEN FALSE FOR A DAY.** It says
> Talisman "cannot easily" be charged because `spend()` does not record
> which colour a source produced — true of the count-based payment, and
> untrue since §0z8. A note saying something is infeasible is a claim with
> a date on it. §0z13.

### The original entry

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

<a id="0z9"></a>

## 0z9. FIXED — "each opponent loses N" dealt up to 3N once the pod thinned

`deal_pod_damage(amount, each=True)` takes a POD TOTAL and divides it to get
the per-opponent figure. It divided by the number of opponents still LIVING,
while every caller writes its total for a FULL pod — `9.0` with the comment
"each of 3 opponents loses 3", `6.0` for Guttersnipe's 2 apiece. The divisor
shrank as the pod did and the numerator did not:

| opponents alive | The Meathook Massacre, one death | oracle text |
|---|---|---|
| 3 | 1.0 each | 1.0 |
| 2 | **1.5 each** | 1.0 |
| 1 | **3.0** | 1.0 |

**The bias runs one way and it runs in the endgame**, which is exactly where
drain converts into a win. It hit Meathook and Cauldron of Essence
(`engine.on_creature_death`), Baba Lysaga, Guttersnipe, Longshot and Tyrant's
Choice.

**SIX COPIES OF ONE FUNCTION, AND TIVIT WAS THE ONLY ENGINE THAT CAME OUT
RIGHT.** Its two call sites multiplied by `len(living(g))` before calling,
cancelling a divisor the other five were being wronged by. That is the §0u
drift shape for the sixth time, with a twist worth keeping: **the engine that
was correct is the one the fix forced to change.**

The hazard was wider than the first grep found. FIVE call sites compensated,
and three of them (`tivit.py` x2, `lorehold.py` x1) built the numerator on a
DIFFERENT LINE from the call, so a one-line grep missed them. All five now
multiply by `OPP.pod_size(g)` — the same quantity the divisor uses — so
numerator and divisor move together under either setting of the knob. Writing
`len(g.opponents)` there instead produced a third behaviour that never
shipped, and the first blast-radius measurement was measuring that artifact.

`opponents.pod_size` divides by `len(g.opponents)`, which is DERIVED rather
than a literal 3: elimination sets `alive`, it never removes the opponent, so
the count stays correct if `pod_brackets` is ever given a different length.

`pod_damage_full_pod=False` restores the living-count divisor.
Pinned by `tests/test_pod_damage_and_wipes.py`.

---

<a id="0z10"></a>

## 0z10. FIXED — your own sweeper ignored indestructible; the pod's did not

`resolve_own_wipe` called `g.board.remove(p)` directly while `board_wipe` went
through `destroy()`, which honours `card.indestructible` and Avacyn's grant.
**The same effect obeyed two different rules depending on which side of the
table cast it.** §0u again, in the one place where the asymmetry favours
nobody.

Live in **two of the six BUILT lists** — and the count matters, because the
first version of this note said three. `karlov_v2.HELIOD_SUN_CROWNED` is a
module-level CANDIDATE, not a deck member, and a grep of the module reads the
same as membership. Counted from `build()`:

| deck | indestructible | destroy-wipes |
|---|---|---|
| shilgengar | Avacyn, Angel of Hope | Damn, Wrath of God |
| rendmaw | Erebos, Bleak-Hearted | Culling Ritual |

Avacyn is the sharp case: she grants indestructible to everything you control,
and your own Wrath was ignoring the grant outright.

**THE BRANCH IS TAKEN FROM THE SWEEPER'S ORACLE TEXT, NOT FROM A COIN FLIP.**
The pod's interaction is an anonymous "answer" and is priced statistically by
`destroy_share`, because the model cannot know whether an opponent held a Doom
Blade or a Swords. Your own wipe is a NAMED CARD whose text the deck list
states, so pricing it the same way would be modelling as unknown something
that is written down. `destroy()` gained a `destroys=` parameter:
True = indestructible always saves, False = never, None = the old roll.

Every classification in `WIPE_IGNORES_INDESTRUCTIBLE` / `WIPE_DESTROYS` was
read from api.scryfall.com on 2026-09-11 and is quoted beside the name. The
split is not obvious and two entries are worth stating:

* **Blasphemous Act DOES NOT get around it.** It deals 13 damage, and
  indestructible survives damage exactly as it survives "destroy".
* **Promise of Loyalty DOES.** "Sacrifices the rest" is a sacrifice, which no
  indestructible permanent survives.

`check_wipe_coverage()` raises if a `wipe`-tagged card in any live deck is in
neither set — §0q's rule applied in the same change that introduces the set.

**WHAT THIS MAKES TRUE, because it reads like a regression and is not:** with
Avacyn out, shilgengar's Damn and Wrath of God are now blanks. That is the
card doing its job. `main_phase` is greedy and will still cast one, which is a
POLICY gap (queued item 18), not this one.

`own_wipe_indestructible=False` restores the kill-everything path.

---

<a id="0z11"></a>

## 0z11. FIXED — `opponents.py` read the type line, not the battlefield

`engine.is_battlefield_creature` exists because a card's TYPE LINE AS PLAYED
is not its creature-ness on the battlefield (§0b). The engine's combat step
has used it since 2026-09-05. **`opponents.py` never adopted it** and asked
`perm.card.is_creature` at seven sites, so a permanent could be too-not-a-
creature to attack and creature enough to die to a board wipe.

All three affected cards sit in the rendmaw list **alongside its two
sweepers**:

| card | clause | what happened |
|---|---|---|
| Grist, the Hunger Tide | "As long as Grist ISN'T ON THE BATTLEFIELD, it's a 1/1 Insect creature" | a bare Planeswalker, dying to every Wrath |
| Overlord of the Hauntwoods | Impending: "isn't a creature until the last time counter is removed" | wrathed during the four turns it is an enchantment |
| Erebos, Bleak-Hearted | not a creature below devotion 5 | same |

`opponents.is_creature_now` is now the single predicate for the question, used
by both wipe paths, the wrath-width count, `should_cast_own_wipe`,
`board_threat`, `your_creatures`, `destroy`'s death trigger and (since the
same day) `final_board_power` in all six engines.

**IT NARROWS AND NEVER BROADENS, ON PURPOSE.** The `card.is_creature` guard
comes first, so it can only REMOVE a permanent from a victim list. That is
deliberate: `azusa.py`'s module docstring states as a fact that
`spot_removal` and `board_wipe` "both exclude lands, so nothing the pod does
can kill an animated land". An animated land really is a creature and really
should die to a Wrath — `azusa.counts_as_creature` already knows it — but
that is the BROADENING half of the same question, it is inert today (all
three of azusa's animation cards were cut on 2026-09-10, §0y), and folding it
in here would have silently reversed a documented decision.
**That half is still open.**

Measured on rendmaw (N=4,000, T20): `final_board_power` **+0.93** (p=9e-08),
damage **+0.48** (p=2e-06), `tokens_made` +0.24, `wipes_suffered` −0.012 (a
board that no longer counts non-creatures looks narrower and draws fewer
wraths). Win rate **+0.0027, p=0.20 — unresolved**.

`pod_reads_battlefield_creatures=False` restores the type-line reading. It is
a NEW knob rather than a reuse of `battlefield_creature_types`, which was
tempting and wrong: that one gates only the NEVER *stamp* applied at ETB and
does not gate the impending or devotion clauses, so it would have restored
some of the old behaviour and not the rest — **a mutation run that passes
while claiming to restore the old rule.** The mutation check caught exactly
that before the knob was changed.

---

<a id="0z12"></a>

## 0z12. FIXED — tivit cast board wipes that did nothing, and waited to do it

`tivit.resolve()` had **no `wipe` branch at all**. `main_phase` already gated
casting on `OPP.should_cast_own_wipe`, so the tag was half-wired: the engine
HELD Damn, Farewell and Promise of Loyalty back until it was behind on board
and then cast them for zero effect. **That is worse than a blank — a blank
does not wait for the worst moment to do nothing.** The other four engines
have carried the one line since §5.

`own_wipes_cast` goes from **0 to 0.88 a game**. Measured (N=4,000, T20):
`turns_played` **+0.54** (p=6e-113), `opponents_killed` **+0.057** (p=3e-08),
damage flat (a symmetric wipe kills your board too — the gain is survival),
win rate **+0.0055, p=0.25 — unresolved**.

**TWO OF THE FIVE CARDS HAD TO BE FIXED, NOT JUST SWITCHED ON.** Their tags
were harmless while nothing read them and would have become real
overstatements the moment the branch worked:

* **Sadistic Shell Game** — "each player chooses a creature you don't
  control" is ONE KILL PER PLAYER. As `("wipe", "onesided")` it would have
  zeroed all three opponents' boards: up to 21 creature-equivalents against
  the 4 the card kills. Now a bounded 1-per-player off the biggest board,
  measured at 0.29 kills a game.
* **Magister of Worth** — its wipe is CONDITIONAL on the council vote and
  spares only itself; `onesided` would have fired unconditionally and spared
  your whole board. It previously shared a dispatch branch with four cards
  whose entire text is the vote, so it voted and threw the result away —
  neither mode existed. It now resolves BEFORE the permanent enters, which is
  what makes "all creatures other than this creature" exact rather than
  approximate. 0.072 wipes / 0.066 graveyard returns a game.

Condemnation needs vote control to land at all (1–2 votes against three
adversarial opponents never wins a council) — that is the documented
pessimistic `opp_vote_policy` default, not a defect. Grace's "EACH PLAYER
returns each creature card from their graveyard" is modelled for you and
invisible for the pod (§4), so that mode understates.

Consequence for the labels: all five left `KNOWN_BLIND`, where they sat under
"nothing that removes a permanent can be evaluated". That was true of Path to
Exile and never quite true of a board wipe — a wipe against an abstract
creature COUNT is expressible, you set it to zero. Damn, Farewell and Sadistic
Shell Game are now `SCRIPTED_TIVIT`; Promise of Loyalty and Magister of Worth
are the first entries in `PARTLY_MODELLED["tivit"]`.

`tivit_sweepers=False` restores the whole pre-fix state.

---

<a id="0z13"></a>

## 0z13. FIXED — §0i is closed, and its stated blocker had been stale for a day

§0i listed four cards whose life-loss drawback was free. §0z7 charged
Bitterblossom and Phyrexian Arena. Of the remaining two, **Dark Confidant is a
karlov CANDIDATE and has no row in any table** (the same misread as §0z10's
Heliod), so **Talisman of Conviction was the only one still live.**

§0i said it "cannot easily not be: `spend()` does not record which colour a
source produced". **That was true of the count-based payment and stopped being
true at §0z8**, one day earlier, which nobody went back and re-read.
`available_mana` now records each unit's OWNER and `can_pay` returns the exact
indices it assigned, so the owner and the pip are both in hand at every
payment site.

`engine.pip_assignment` recovers the pip POSITIONALLY from `can_pay`'s
existing return value — coloured pips are taken first, in `COLORS` order, then
generic, in all three of its branches — so it needs no signature change and
makes no second copy of the assignment. Talisman is charged only when it was
assigned to an `{R}` or `{W}` pip; one spent on generic was tapped for `{C}`
and is free, which is both correct and what the pilot would do.

Measured on lorehold (N=4,000, T20): win rate **−0.0015, p=0.014** — small and
significant. 0.109 coloured taps a game. The chain is visible:
`final_life` −0.036 → `turns_played` −0.007 → `cards_drawn` −0.032 →
`miracles_cast` −0.0035. A tenth of a life buying 0.0015 win rate reads steep
until you see that **lorehold ends on 1.73 life** with the highest life-share
of losses of the three decks (0.43).

**THE GENERAL LESSON, and it is 16b pointed the other way.** Standing finding
16b says a POLICY written while a bug was open does not fix itself when the
bug closes. This is the same thing about a KNOWN ISSUE: **a note saying
something is infeasible is a claim with a date on it, and closing an engine
gap can silently make it false.** After any §0z8-sized change, re-read the
issues that said "cannot".

Behind `talisman_coloured_tap` (its own switch) AND `charge_life_costs` (the
§0z7 family flag, which overrides). Two knobs because reverting through the
family flag alone would revert Bitterblossom and Phyrexian Arena with it, and
then no measurement of this change by itself is possible.

---

<a id="0z14"></a>

## 0z14. FIXED — §0f's three Lorehold cards, and §0f's own prescription was wrong

All three are implemented. **§0f is closed except for one clause that is
unmodelable rather than unimplemented.**

### Borrowed Knowledge — and §0f told the next reader to break it

§0f says: *"Borrowed Knowledge is a wheel, and the engine already has a
`wheel` script for Reforge the Soul."* **It is not a wheel.** Oracle:

> Choose one — • Discard your hand, then draw cards equal to the number of
> cards in target opponent's hand. • Discard your hand, then draw cards equal
> to the number of cards discarded this way.

`wheel` draws a flat SEVEN; this draws only what it discarded. Following §0f's
prescription would have **overstated** the card — the opposite of that
section's own claim that all three of its cards understate. And the stand-in
it replaced, `draw2`, overstated it too: **two free cards is better than a
net-zero self-wheel.**

Mode 2 is implemented; **mode 1 has no opponent hand to count (§4)**, which is
why the card stays in `PARTLY_MODELLED` and its row is a FLOOR.

**The draw was never the missing half — the DISCARD was.** `draw2` put nothing
in the graveyard, and this is the deck where the graveyard feeds Arcane
Bombardment, Mizzix's Mastery, The Dawning Archaic and Radiant Scrollwielder.

The mutation check earned its keep here: the prediction was seven failing
cases and it was eight. **`draw2` drew two cards off an EMPTY hand**, which is
the one board state where Borrowed Knowledge does nothing at all — the old
script was not a weak approximation of this card, it was a different card.

### Apex of Power — the ten mana is the card

Was `draw4`. "Exile the top seven cards of your library. Until end of turn,
you may cast spells from among them. If this spell was cast FROM YOUR HAND,
add ten mana of any one color."

Two real costs came with implementing it, and `draw4` charged neither: cards
exiled and not cast are **GONE**, not drawn; and a **COPY gets no mana**,
which is most of why copying this card is worse than casting it.
`mana_units`/`pay` now carry three blocks — board, Apex, Treasures — with both
boundaries measured from the END of the list, because only the board block has
permanents behind it and only it may reach `spend`.

### Hit the Mother Lode — Discover 10

Was a flat 5 Treasures. Now exiles until a nonland of MV ≤ 10, free-casts it,
and makes 10 − MV Treasures that enter **TAPPED** and are not mana until the
next untap step. Structurally `sunbird` with two differences that matter: it
digs UNTIL it hits rather than looking at a fixed window, and at N=10 the hit
is effectively guaranteed.

**One deliberate departure from the reminder text:** the leftovers go to the
bottom **in order, not shuffled**. `sunbird` shuffles its leftovers with
`g.rng.shuffle`, which is a mid-game draw on the GAME rng and one of the CRN
leaks below. The order of cards on the bottom of a library can only matter to
a game that reaches them, and these games end around turn 12.

### Measured together (N=4,000, T20)

| metric | before | after | |
|---|---|---|---|
| **won** | 0.1492 | 0.1573 | **+0.0080**, p=0.029 |
| mv_cheated | 24.60 | 26.06 | **+1.46**, p=3e-07 |
| total_mv_cast | 55.05 | 57.51 | +2.45, p=6e-12 |
| free_casts | 0.150 | 0.374 | +0.224, p=5e-104 |
| cards_drawn | 28.71 | 27.90 | −0.82, p=5e-20 |

**The only win-rate-positive result in the whole batch.** 91% of the Apex mana
generated is spent (1.38 of 1.515 a game), which is the evidence that the ten
mana is the card. `cards_drawn` falling is the honest cost of Apex exiling
where `draw4` drew.

Knobs: `borrowed_knowledge_discard`, `apex_ten_mana`, `mother_lode_discover`.

---

<a id="0z15"></a>

## 0z15. FIXED — four checks that could not fail, and one "fix" that was a regression

A cluster found by sweeping for the failure shapes this project keeps having,
rather than by a diagnostic. **Three of the four changed no number at all**,
which is the point: they are checks and labels, and a check that cannot fail
reads like assurance and is worse than none.

### The engines stamped their defaults into the CALLER'S cfg

Five engines open with `cfg.setdefault(...)` — `shroud_sources`,
`protection_cards`, their own knobs — run against the dict they were handed.
A caller that built one cfg and passed it to several engines got the **FIRST
engine's** defaults applied to all of them: construct a Lorehold game and then
a Karlov one on the same dict and **Karlov silently ran with Lorehold's
shroud sources and protection cards.**

Nothing committed is affected, and that was luck rather than design:
`compare_decks.run()`, `fit_pod.evaluate()` and `experiment.run_ab` all happen
to build a fresh cfg per deck. **A convention was holding a latent bug still.**
Found when a verification script shared one cfg across all six engines and got
a different Karlov out of it. `engine.engine_cfg()` now hands each engine a
private copy.

### `opponents_killed` was two quantities under one name

`combat_damage` maintained `m["opponents_killed"]` as *kills your attack
made*; every engine's `simulate()` then overwrote that key with *opponents not
alive from ANY cause*, which includes the ones eliminated by another
opponent's clock. The in-game counter was dead weight and the reported metric
— in `experiment.METRICS`, on every A/B — has always been the any-cause one.

Renamed to `m["combat_kills"]`. **No number moved**; nothing reads either key
as a decision input. The gap is worth knowing: **karlov shows 0.46 combat
kills against 1.45 `opponents_killed`** — two-thirds of what that metric
reported was the pod killing itself.

### `check_scripted_coverage` skipped every land

`names = {c.name for c in deck if not c.is_land}`. A basic Forest needs no
classification, but **a `script` on a land IS a claim**, and that claim went
unchecked: **Rogue's Passage** sat in tivit with `script="rogues_passage"`
that nothing dispatched, nothing implemented, and that was in none of the
three categories. §0q's shape in the checker itself.

Widened to `if not c.is_land or c.script`, which immediately demanded
classification for five more scripted lands — Khalni Garden, Havengul
Laboratory and the three azusa fetches, all implemented, now `SCRIPTED_*`.
Rogue's Passage is `KNOWN_BLIND` with its reason: **the thing it buys is
already assumed.** Tivit's second trigger fires on `dmg > 0 and Tivit
attacked` and never asks whether TIVIT connected, so the model already
behaves as though the commander is unblockable; the {4} activation is
uncharged too, so both halves are missing and point opposite ways.

### A mutation check that raised KeyError instead of checking anything

`diagnostics/diag_azusa_animation --mutate` — a command CLAUDE.md tells the
reader to run — died with `KeyError: 'Sylvan Awakening'`. §0y cut the whole
land-animation pillar on 2026-09-10 and `BY_NAME` was built from the deck.
**The cards left; the engine did not**: `sylvan_awakening`,
`rude_awakening` and Nissa's loyalty abilities are all still live
default-path code. The three definitions are restored in the diagnostic
verbatim from `d158724^`, the deck wins on any name it still carries, and a
`REQUIRED` check now fails at import with a sentence instead of a KeyError
forty lines into a case. Back to 8/8 clean and **7 of 8 failing under
`--mutate`**, as documented.

### AND ONE PROPOSED FIX THAT WAS A REGRESSION, kept here because it will be re-proposed

`can_pay`'s `supply` dict is built once before the generic loop and NOT
decremented as picks are taken, so from the second pick on it counts units
already spent. The docstring said "how many REMAINING units can still produce
it". **It reads like an oversight. It is not, and decrementing it is wrong.**

One Plains and three Mountains, paying {3}:

| rule | picks | result |
|---|---|---|
| snapshot | W=1 R=3, W=1 R=3, W=1 R=3 | Mountain x3 — **the Plains survives** |
| running | W=1 R=3, W=1 R=2, W=1 **R=1** | Mountain, Mountain, **TIE** |

The running count degrades exactly as the payment eats the plentiful colour,
so the last pip of a big generic cost always falls through `-surplus`,
`len(units)` and the weight to **board order** — the §0z8 defect, coming back
in the one function §0z8 exists to fix. `tests/test_mana_colour.py` failed two
cases within a minute of the change.

**The code was right and the docstring was wrong.** The comment now carries
the counter-example so the next reader does not repeat it.

---

<a id="0z16"></a>

## 0z16. FIXED — the same card, two decks, two contradictory labels

Found by READING THE 2026-09-12 REGENERATION rather than by a diagnostic, which
is the point of doing the read-through at all: the numbers were right and the
headings over them were not.

**`Farewell` was `SCRIPTED_TIVIT` and `KNOWN_BLIND["lorehold"]` at the same
time.** So the same card's row printed under *"a low score is evidence about
the card"* in one table and *"a low score is evidence about the MODEL, not the
card"* in the other — through the **identical shared code path**, because all
six engines route their own sweepers through `opponents.resolve_own_wipe`. The
difference was not that one deck modelled the card more deeply. Neither does.

Three cards were affected, across seven deck-instances:

| card | SCRIPTED / PARTLY in | KNOWN_BLIND in |
|---|---|---|
| Farewell | tivit | lorehold, karlov |
| Damn | tivit, shilgengar | karlov |
| Promise of Loyalty | tivit (PARTLY) | lorehold |

### Why nothing caught it

`check_scripted_coverage(deck)` enforces that a card is in **exactly one** of
the three categories — and it takes ONE DECK. Each deck's sets were internally
consistent, so every deck passed. **The blind spot is the dimension the check
does not range over.** That is §0z15's lesson (a check that skips a category is
blind exactly there) with a new axis: §0z15's checker skipped lands, this one
skips *the other five decks*.

### The fix: derive the category from the tag

Listing the seven instances by hand would have been the §0q failure mode
applied to its own cure. A symmetric wipe is **partly modelled by
construction**: `resolve_own_wipe` destroys YOUR real board through
`destroy()`, honouring indestructible from the sweeper's own oracle text
(§0z10) — faithful — and sets each living opponent's `creatures` float to 0.0,
which is §4 with no card behind it. The cost is modelled and the benefit is an
estimate, so a HIGH score is evidence and a LOW one is not. That is
`PARTLY_MODELLED`'s definition, and it is true of every symmetric wipe in every
deck.

`ablation.symmetric_wipes()` now derives the set from the `wipe` tag, and
`partly_for()` merges it into `PARTLY_MODELLED` — a hand-written entry wins,
so Promise of Loyalty and Magister of Worth keep the specific reasons naming
their missing clause. **17 instances across five decks.** Two exclusions, both
claims rather than conveniences:

* **`onesided` wipes stay `KNOWN_BLIND`.** `spare_own=True` skips the half that
  is faithful, so a one-sided wipe is ALL abstraction and a high score means no
  more than a low one. Massacre Wurm (rendmaw) is the only one.
* **Sadistic Shell Game stays `SCRIPTED`**, in `WIPE_NOT_SYMMETRIC` with its
  reason: one kill per player off the biggest board is exactly what the text
  says and exactly what the `creatures` float can carry — it needs no knowledge
  of WHICH creature dies. It is not a board wipe.

The invariant is enforced by the check that already existed: a derived wipe is
in `PARTLY`, so re-adding one to `SCRIPTED` or `KNOWN_BLIND` by hand trips the
existing overlap check, whose message now says so.

### It changed no number, and that was demonstrated

All six tables were re-rendered from their existing caches and compared field
by field: **0 of 378 rows changed a number; 16 rows changed category.** The
same demonstration item 14 used, for the same reason — a classification change
that quietly moved a measurement would be the worst of both.

### Why it mattered right then

The regeneration had just moved lorehold's `Ultima` to **−0.0063 ±0.0033** and
`Farewell` to **−0.0055 ±0.0033**, both crossing from inside their bars into
significantly negative, both printing under MODEL-BLIND. Mechanically that is
correct — a symmetric wipe in the deck whose commander IS its engine costs you
the engine, and the pod's half is a float — but **two significantly negative
rows are the §0z2 Bane of Progress trap, which has already cost this project
two withdrawn swaps.** They now print under a heading that says NEVER CUT ON
ONE.

The mirror image is the tell that the old labels were incoherent: **the same
card scores +0.0073 in tivit and −0.0055 in lorehold**, and that divergence is
real — tivit rebuilds from artifact tokens, lorehold's commander leaves for the
command zone with tax. A card genuinely can be good in one list and bad in
another. What cannot be right is one table calling that number evidence and the
other calling it noise.

---

<a id="0z17"></a>

## 0z17. FIXED — CRN leaked mid-game in eleven places, and the self-check could not see it

2026-09-13. CLAUDE.md queued item 19, which had no section id of its own
despite being described there as the largest open problem in the project.

### The defect

Common random numbers are why this project can resolve 0.003 win rate at all.
Deck A and deck B are the same list with one slot swapped and the same shuffle
seed, so the other ~97 cards land identically and nearly all variance cancels
in the difference. **That holds only while both branches consume the same
random numbers in the same order.**

Eleven call sites in five files drew mid-game from the single game RNG:
`engine.py` (Arasta, Deathreap Ritual), `karlov.py` (Kambal), `lorehold.py`
(the gated top-setter, Arcane Bombardment, Radiant Scrollwielder, the tutor,
Sunbird's Invocation's shuffle), `tivit.py` (Master of Ceremonies) and
`voting.py` (three). The moment two branches' boards diverged they took a
DIFFERENT NUMBER of draws, and every later draw in both games then read a
different slot of the same sequence. Measured before the fix: 17 of 400 seeds
(4.2%) on one rendmaw swap; **46 of 300 (15.3%)** on one lorehold swap, whose
Sunbird's Invocation took 1,100 mid-game draws against the other branch's 132.

### The fix: ADDRESSING, not ordering

`engine.CRNStreams` gives every effect its own stream, and the Nth firing of
that effect reads index N of it. Nothing another effect does can shift it, so a
divergence stays contained to the effect that diverged. This is
`azusa.shuffle_library`'s pre-rolled pattern -- the project's only correct
implementation -- generalised from shuffles to every draw and SHARED, rather
than reimplemented per engine (§0u, six instances). Azusa's private
`shuffle_seeds` list is deleted in favour of it.

What it does not fix, because nothing can: if an effect fires three times in A
and four in B, the fourth read is a value A never saw. That is the decks
genuinely differing, and it is confined to that one effect's stream.

`crn_streams=False` restores the old behaviour and **reproduces HEAD
bit-identically on all six engines**, verified against a worktree. Azusa's
legacy branch is its own old seed list rather than `g.rng`, because routing it
to the game RNG would introduce a leak this engine never had.

### The check, and why the old one could not fail

`tools/validate.py`'s A/A control swaps a card for ITSELF, so the branches
never diverge, the call sequence is identical by construction, and all eleven
leaks passed it for months while it printed `+0.00` on eighteen metrics. §0z15,
arriving in the place it cost most.

What replaces it asserts a STRUCTURAL INVARIANT that needs no second branch:
**after the opening hand is decided, `g.rng` is never touched again.**
`engine.AuditRandom` counts violations under `crn_audit`; `tests/test_crn_streams.py`
runs it over all six decks and carries the mutation check.

**THE AUDIT'S OWN FIRST VERSION HAD THE BUG IT WAS WRITTEN TO CATCH.** Built
from the deck MODULES, lorehold's `sunbird()` never executes -- Sunbird's
Invocation is STAGED, not committed -- so the audit ran clean over the single
worst leak in the project, and a mutation restoring that leak was NOT detected
because the code was never reached. It now ranges over `build_pending`, which
is what `ablation.py` and `candidates.py` actually measure. §0z15's rule
applied to the new check on its first day.

**One of the eleven sites is DEAD CODE.** `lorehold.py`'s gated-setter draw is
guarded by `GATED_SETTERS = {"Hidden Retreat"}`, and Hidden Retreat was
committed out of the deck on 2026-09-01. Its mutation is expected not to be
detected and the test says so. A fifth instance of §0q -- a hand-maintained
name set naming a card the deck moved past.

### AND THE HONEST PART: closing it bought no measurable precision

The leak was real, is closed, and is now structurally prevented. **It did not
improve the pairing.** Measured on the two swaps above, N=1,500, before against
after:

| swap | metric | corr before | corr after |
|---|---|---|---|
| rendmaw, March -> Skullclamp | damage | 0.9387 | 0.9382 |
| rendmaw, March -> Skullclamp | win | 0.8528 | 0.8567 |
| lorehold, Scroll Rack -> Sunbird's | damage | 0.8979 | **0.9017** |
| lorehold, Scroll Rack -> Sunbird's | win | 0.7952 | **0.7901** |

Every one of those differences is inside the noise at that sample, and the win
rate correlation on the worst-affected swap moved DOWN. **"15.3% of seeds
diverged" is not "15.3% of the pairing was lost"**: the dominant shared
randomness is the opening shuffle, which was never broken, and the mid-game
draws the leak disturbed are second-order next to what you drew. HANDOFF.md's
"it makes them noisier than the error bars claim" is therefore an
OVERSTATEMENT, and is corrected there.

This ships as **correctness and as a guarantee that can now fail loudly**, not
as a precision win -- the §0u / §0z6 shape for the seventh time.

### What it costs

Five engines' numbers move, because their mid-game random values now come from
different streams. **Shilgengar is bit-identical** (it has no mid-game draws at
all), which is the same kind of confirmation the byte-identical decks gave in
the 2026-09-12 regeneration. All six ablation tables need regenerating; the
fingerprint moves for all six on `engine.py` alone.

---

<a id="0z18"></a>

## 0z18. FIXED — Ashaya's second clause, and the design note pointed the wrong way

2026-09-13. Queued item 15, open since 2026-09-10, and the half of §0z that the
PARTLY_MODELLED label was holding open.

Ashaya, Soul of the Wild, re-verified against Scryfall 2026-09-13:

> Ashaya's power and toughness are each equal to the number of lands you
> control. **Nontoken creatures you control are Forest lands in addition to
> their other types.** (They're still affected by summoning sickness.)

Only the first sentence existed. The second is now implemented in
`ashaya_lands` / `is_creature_land` / `creature_lands` / `creature_land_mana` /
`land_count`, behind `ashaya_lands`, defaulting to the corrected behaviour.

### WHAT IT IS WORTH: +0.0140 win rate, and this one IS the objective

Paired on the same seeds, N=2,500, T20, against azusa's ±0.0030 noise floor:

| metric | paired difference |
|---|---|
| **win rate** | **+0.0140 ±0.0077** |
| tokens_made | +62.77 ±11.69 |
| mana_spent | +23.92 ±4.23 |
| landfall_triggers | +2.00 ±0.20 |
| damage | +0.75 ±0.44 |

Ashaya resolves in **28.4%** of games; conditional on resolving, win rate is
**+0.0493 ±0.0270** and the clause fires **6.65 creature-ETB landfall triggers
and 1.11 land-deaths per resolution**. The token explosion is Scute Swarm:
every nontoken creature entering is a land entering, and past six lands the
Swarm copies itself instead of making an Insect.

This is only the second win-rate-positive correctness result in the project
(§0z14 was the first). Everything else has been the §0u shape.

### THE DESIGN NOTE WAS WRONG, AND WRONG IN THE EXPENSIVE DIRECTION

`docs/COMP_RULES.md` had already researched this and concluded, of 603.6a:
**"it must not fire landfall."** That is true of creatures already on the
battlefield when Ashaya resolves — they gain the type with no ETB event — and
**false of every creature that enters afterwards.** The official ruling
(2020-09-25) is explicit:

> "You can't play creature cards as lands; you'll still have to cast them as
> spells, and **they'll enter the battlefield as lands** (in addition to their
> other types)."

In a 28-creature landfall list that branch is the larger half of the card.
Implementing the note as written would have shipped Ashaya understated and
called it done — and the note's own framing ("a naive implementation would
trigger every payoff off every creature and the error would be enormous") reads
as a warning against the correct behaviour. **A rules note is evidence about
the game and still has to be checked against the rulings.** §0z13's shape
pointed at research rather than at a blocker.

§0z's Quirion Ranger claim is wrong for the same reason and is corrected here:
returning a creature-Forest to hand and replaying it is **not a land drop** —
the same ruling says you cannot play creature cards as lands. Recasting it is
a creature spell, which fires landfall as it enters, so the conclusion (a
landfall trigger) survives and the stated mechanism does not.

### The mutation caught a defect in the fix, one hour after documenting it

The first mutation set was written before the run, as CLAUDE.md requires, and
**two of nine entries were wrong** — cases 5 and 6 assert an ABSENCE, and a
wholesale off-switch cannot distinguish those from the trivial case. Splitting
into three targeted mutations then caught something real: the one-`{T}` rule
("a mana dork gains Forest's ability but has one tap to spend") was written
**twice** — in `creature_land_mana` and in `available_mana`'s `elif` chain,
which short-circuited before the predicate was ever consulted. §0u's shape,
committed in the same session that re-documented §0u. The predicate is now the
only place the rule is written and the `elif` is an `if`.

### What is still open

**Quirion Ranger's activated ability is still unimplemented** and stays in
`KNOWN_BLIND`. Its blindness reason in §0z is now stale in the other
direction: it reads "no modelled payoff", and the payoff now exists.

### Classification

Ashaya moves **out of `PARTLY_MODELLED` and back into `SCRIPTED_AZUSA`** — the
category working exactly as designed: the label named the missing clause, the
clause got written, the label moved back. `PARTLY_MODELLED["azusa"]` is now
Bane of Progress alone. **Azusa's table needs regenerating** and its row is
evidence again.

---

<a id="0z19"></a>

## 0z19. FIXED — §7 closed. Six recursion cards, two engines, one repeated bug

2026-09-13. §7 ("Unmodelled recursion in Lorehold") has been open since the
project's early days. All six cards are implemented, all oracle text verified
against Scryfall the same day, behind `lorehold_recursion` and
`artifact_recursion`, both defaulting to the corrected behaviour.

### What each card is worth

**Lorehold, paired on the same seeds, N=2,500, T20** — the engine correction,
all three cards at once, against a ±0.0032 noise floor:

| metric | paired difference |
|---|---|
| **win rate** | **+0.0220 ±0.0097** |
| mv_cheated | +3.40 ±0.64 |
| damage | +1.50 ±0.46 |
| free_casts | +0.61 ±0.06 |

Ablated individually on the new engine (card vs blank, N=3,000, T20), which is
the different and smaller question of whether each earns its slot:

| card | win rate | signal |
|---|---|---|
| Volcanic Vision | +0.0110 ±0.0076 | `*` |
| Invoke Calamity | +0.0073 ±0.0085 | `--` |
| Goliath Daydreamer | +0.0033 ±0.0057 | `--` |

**Rendmaw**, `artifact_recursion` on/off, N=3,000, T20: win rate
**+0.0040 ±0.0035**, damage +0.29 ±0.13, firing 0.19 times a game. Small, and
real: artifacts only die to wipes here.

### GOLIATH DAYDREAMER IS NOT THE TRAP §7 PREDICTED

§7's re-check warned that Goliath "is not merely unmodelled, it is
anti-synergistic in a way nothing in the engine can see" — it exiles your
instants and sorceries with dream counters instead of letting them reach the
graveyard, starving Arcane Bombardment, Mizzix's Mastery, The Dawning Archaic
and Radiant Scrollwielder, which is this deck's entire engine. **Both halves
are now implemented and the card is +0.0033 ±0.0057 — inside its own bar.** It
exiles 0.231 cards a game and gives back 0.142 free casts, so the drawback is
real, is counted (`dream_starved`), and does not dominate. The warning was
right to demand the drawback be modelled and wrong about the sign.

### THE SAME BUG, TWICE, IN TWO ENGINES, ON THE SAME DAY

Both implementations crashed on the identical defect: **a selection is a
snapshot and the zone is live.**

* `invoke_calamity` picked the best pair, cast the first, and the first one's
  resolution triggered Arcane Bombardment, which exiled the second pick out of
  the graveyard. `remove` then raised. Fixed by re-checking membership per
  pick; the counter `invoke_lost_target` records it and it fires about once in
  a thousand games, so it was a real race and not a theoretical one.
* `artifact_died` built its candidate pool once and called `take` twice — a
  Myr Retriever dying while Scrap Trawler is on the battlefield is two
  separate triggers — so the second selected a card the first had already
  moved to hand. Fixed by recomputing the pool per trigger.

**Anywhere one effect can cause another, a pool computed before the first is
wrong by the time the second reads it.** Both fixes are three lines; finding
the second one took no time at all because the first had just been found,
which is the argument for writing these up rather than just fixing them.

### The clauses that a from-memory implementation gets wrong

* **Invoke Calamity is TOTAL mana value 6, not 6 each** — a two-threes card,
  not a two-sixes card. It also reads **graveyard AND hand**, so it is live
  with an empty yard. And it is an INSTANT that this engine casts at sorcery
  speed: a floor.
* **It is not a legal target for itself.** In the miracle path it is still
  sitting in `hand` when it resolves, and nothing else excluded it. Left in, it
  selected itself and recursed.
* **Both spells exile themselves**, so neither can be re-bought by
  Bombardment, Archaic, Scrollwielder or Mastery. In a deck built on re-buying
  its own graveyard that is a real cost, and it is the half a naive
  implementation drops.
* **Scrap Trawler is LESSER, not lesser-or-equal** — the whole of the
  loop prevention.
* Invoke's free casts pass `is_copy=True` only for GRAVEYARD casts, because
  `apex_of_power` reads that flag to decide whether its "add ten mana" fires,
  and Apex's clause is worded "if you cast it from your hand". Invoke can do
  either.

### Classification

* `SCRIPTED_LOREHOLD` gains **Invoke Calamity** and **Goliath Daydreamer**.
* `SCRIPTED_RENDMAW` gains **Myr Retriever** and **Junk Diver**.
* `PARTLY_MODELLED` gains two, both for §4 reasons, both floors:
  **Volcanic Vision** (its "damage equal to that card's mana value to each
  creature your opponents control" has no creatures with toughness to hit) and
  **Scrap Trawler** (its second clause only ever sees artifact CREATURES die,
  because `opponents.destroy` kills nothing that is not a creature right now —
  no Sol Ring, no signet, no Idol of Oblivion, and no tokens).

All six leave `KNOWN_BLIND`. **Lorehold's and rendmaw's tables both need
regenerating.**

### What §7 leaves behind

Nothing on the Lorehold or Rendmaw side. §7's Apex of Power item was already
closed by §0z14.

---

<a id="0z20"></a>

## 0z20. FIXED — §3 and §1b. The Altar's mana, and what "one cost per card" really was

2026-09-13.

### §3 — Ashnod's Altar's mana arrives too late to spend

"Sacrifice a creature: Add {C}{C}" was activated in `activations()`, which runs
AFTER every casting decision has been taken. The engine therefore modelled the
COST of sacrificing and none of the benefit, and §3 was right to refuse to read
the card's slightly negative row as a finding about the card.

`main_phase` now offers the Altar when — and only when — **nothing else in hand
is castable**, sacrificing the fewest bodies that make the highest-priority
stranded card castable. It will not eat a token speculatively, and
`altar_fodder` is one shared definition of "expendable" used by both the mana
path and the older deaths-for-Blood-Artist path, so the two cannot drift (§0u).
It never eats a creature the current payment is counting on, which matters
exactly when Enduring Vitality is out and every untapped creature taps for mana.

**AND FIXING IT DOES NOT RESCUE THE CARD.** Paired, N=3,000, T20:

| metric | paired difference |
|---|---|
| win rate | +0.0007 ±0.0009 — **inside its bar** |
| mana_spent | +0.067 ±0.034 |
| spells_cast | +0.026 ±0.010 |
| tokens_made | +0.034 ±0.015 |

The mechanism counters move and the objective does not: the §0u / §0z6 shape
for the eighth time. **The Altar's own ablation row goes −0.0030 ±0.0033 →
−0.0023 ±0.0034** — still inside its bar, still faintly negative.

**`altar_keep` IS NOT LOAD-BEARING, and that is said out loud because
CLAUDE.md requires it.** Sweeping it 6 → 3 → 1 → 0 quadruples the sacrifices
(0.052 → 0.233 a game) and leaves win rate inside its bar at every setting
(+0.0007, +0.0003, +0.0013, +0.0017). What limits the card is not the
conservatism: it is that "more than six spare tokens AND nothing castable" is a
rare board.

**BOTH §3 CARDS WERE IN `KNOWN_BLIND` WHILE BEING IMPLEMENTED.** Deathreap
Ritual's "at the beginning of EACH end step" was never unimplemented at all —
`activations()` has drawn for your end step plus the pod's three, each gated on
`opp_death_rate`, for as long as the entry has existed. Both move to
`SCRIPTED_RENDMAW`. §0q's shape again, and the reason §3 read as two
unexplained negative rows.

### §1b — it was TWO problems, and `alt_costs` only ever solved one

A card's alternative costs are not all of a kind:

| kind | example | what the policy should do |
|---|---|---|
| cheaper AND worse | Overlord of the Hauntwoods, Impending 4 | take it only if you must |
| a different route | Revitalizing Repast's hybrid {B}/{G} | take whichever is payable |
| **dearer AND better** | **Mizzix's Mastery, overload {5}{R}{R}{R}** | **take it whenever the mana is there** |

`alt_costs` was consulted **only when the printed cost was unaffordable** —
right for the first two kinds and exactly backwards for the third. So overload
could not be expressed at all and lived instead as a hand-written
`if card.script == "mastery"` inside `lorehold.main_phase`, **with its cost
typed out a second time**. §1b predicted this in its own words: "that closes
the whole category instead of patching instances".

`engine.castable_modes` gives every mode a **preference**: printed is 0.0, a
two-tuple alternative defaults to −1.0 (today's fallback, so nothing existing
moves), and a dearer-and-better mode declares a positive one. Ties break toward
the cheapest, which is what makes a hybrid pip work with no preference at all.
`engine.choose_mode` is the single place the choice is made.

**AND IT WAS ONE READER FOR SIX ENGINES.** `engine.main_phase` was the only
consumer of `alt_costs`, so the identical field on a card in Karlov, Tivit,
Shilgengar or Azusa would have been ignored silently — cast at its printed
cost, no error. All six now route through `choose_mode`, and
`pending.check_alt_cost_coverage` raises if one stops: the reader set is
**derived from the engines' own source**, not hand-maintained (§0q). It is
mutation-tested against both failures.

**The one behavioural change** is that Mastery's overload now respects the mana
reserve like every other cost, where the old special case was applied after the
reserve check and could spend through it. Worth **+0.0013 ±0.0026 — inside its
bar** (N=3,000, T20), so the overload mode as a whole is not currently
measurable, and the change ships as structure rather than as a number.

**What §1b leaves open:** the entry also names evoke, escape and kicker, none
of which any card in these six lists has. `Card` still carries one printed
cost plus a mode list rather than a list of modes outright, which is the
smaller refactor and the one that does not touch every deck file.

---

<a id="0z21"></a>

## 0z21. MEASURED — six Azusa candidates, and a land creature that tapped for mana on arrival

2026-09-13. Six cards submitted for review: Nissa, Resurgent Animist; Traveling
Chocobo; Archdruid's Charm; Awaken the Woods; Expedition Map; Zuran Orb. All
six implemented, all six measured at **N=15,000, T20, in the Sylvan Library
slot** — the SAME victim as the §0z4 batch, so the two batches are measured
against the same 98 cards and can be read against each other.

`results/candidates_azusa_batch4_T20.txt`,
`results/azusa_batch4_mechanisms.txt`, `results/azusa_batch4_knob_sweeps.txt`.

### The rows

| card | MV | win rate T20 | damage | signal | rank it would take |
|---|---|---|---|---|---|
| Traveling Chocobo | 3 | **+0.0291 ±0.0040** | +2.64 ±0.26 | both | **8th of 44** |
| Nissa, Resurgent Animist | 3 | **+0.0285 ±0.0041** | +2.65 ±0.28 | both | **8th of 44** |
| Awaken the Woods | 8 | +0.0188 ±0.0029 | +1.71 ±0.18 | both | 14th |
| Expedition Map | 1 | +0.0133 ±0.0033 | +1.44 ±0.23 | both | 25th |
| Zuran Orb | 0 | +0.0124 ±0.0025 | +1.11 ±0.16 | both | 26th |
| Archdruid's Charm | 3 | +0.0082 ±0.0035 | +0.87 ±0.23 | both | 37th |

**ALL SIX CLEAR THE DECK'S REALISTIC CUT BAR**, which on the current table is
Yavimaya Elder +0.0023 ±0.0023, Wayward Swordtooth +0.0038 ±0.0029, Titania
+0.0050 ±0.0031 and Exploration +0.0053 ±0.0029. That is a statement about the
bottom of this list as much as about these cards, and it is the same shape §0z4
found: **the top two are a SET, not a ranking** — Chocobo and Nissa are 0.0006
apart against bars of 0.0040, and both sit inside the bars of Rampaging
Baloths, Tireless Tracker, Ancient Greenwarden and Nissa, Vastwood Seer. §0c.

### Why the top two win, in one sentence each

**TRAVELING CHOCOBO IS A SECOND ANCIENT GREENWARDEN** for the half this deck
cares about — "if a land or Bird you control entering causes a triggered
ability of a permanent you control to trigger, that ability triggers an
additional time" is Greenwarden's sentence with Bird added — and the two
STACK: `landfall_ability_resolutions` (a new counter, and the one that
separates a doubler from a payoff) goes **+13.84 per resolution** against
`landfall_triggers` **+0.90**. One land, three resolutions of everything. In a
list with Scute Swarm that is exponential: tokens_made **+243 per resolution**.

**NISSA, RESURGENT ANIMIST IS A RITUAL THAT ALSO DRAWS**, and the reveal is
narrower than it reads: "if this is the SECOND TIME this ability has resolved
this turn" is the second and only the second, so an Azusa turn making three
land drops gets three mana and ONE card. Measured: **+19.75 mana and +1.52
cards per resolution**, with 0.17 whiffs — the deck holds ten Elf or Elemental
cards, generated into `decks/_evasion.py` as `ELF_ELEMENTAL` rather than typed
by hand (§0z4: subtypes are data). Note the interaction the rules give for
free: with a doubler out the ability resolves twice on the FIRST land, so the
card arrives a land earlier.

### The three whose number rests on a policy, said out loud

**AWAKEN THE WOODS' X IS THE CARD**, so it is swept rather than asserted — and
THE FIRST SWEEP WAS WRONG IN A WAY WORTH RECORDING. It set a cfg knob that
changed the token count while the card's cost stayed {6}{G}{G}, i.e. it
measured eight tokens for the price of six. **The tell was in the output and
not in the code**: `deploy` came back identical at every X, which cannot happen
if X is in the cost. X now comes from `card.x_pips` and there is no knob at
all — cost and effect are one number, and a knob for half of it is §0u's shape
waiting to happen. The sweep varies the whole card.

Swept properly (n=4,000, T20), **X IS NOT LOAD-BEARING BETWEEN 4 AND 6**, which
is the opposite of what "X is the whole card" suggests and is the more useful
answer:

| X | cost | win rate | tokens/game | deploy |
|---|---|---|---|---|
| 3 | {3}{G}{G} | +0.0163 ±0.0062 | 0.96 | 29.9% |
| 4 | {4}{G}{G} | +0.0222 ±0.0062 | 1.25 | 28.9% |
| 6 | {6}{G}{G} | +0.0215 ±0.0058 | 1.90 | 27.4% |

The two effects cancel: a bigger X buys more landfall and costs deploy rate.
Only X=3 is measurably worse, and the committed figure is quoted at X=6, the
project's existing convention.

**ARCHDRUID'S CHARM IS A FLOOR, NOT A MEASUREMENT.** Two of its three modes
(fight-removal, exile an artifact or enchantment) are MODEL-BLIND under §4, so
only mode 1 exists here — and mode 1 itself fetches a FOREST rather than the
Strip Mine or Homeward Path a pilot would want, because those are blind too.
It belongs in `PARTLY_MODELLED` if it is ever added to the list.

**AND ITS HEADLINE NUMBER RESTS ON A POLICY I CHOSE, WHICH BOTH SWEEPS SAY IS
THE WRONG ONE.** `archdruid_mode` (n=4,000): `creature` **+0.0130 ±0.0072**,
`auto` +0.0077 ±0.0071, `land` +0.0057 ±0.0072. The bars overlap and the
question is NOT resolved — but the creature mode came out ahead at n=1,500 and
again at n=4,000, and `auto` takes the land on essentially every board in this
deck, so the reported +0.0082 is close to the LAND mode's value. **If this card
is ever staged, re-measure the mode first**: the gap between the two pure
strategies is about as large as the card's whole score.

**ZURAN ORB IS ALSO A FLOOR**, and for the reason that makes the card: it is a
free instant-speed outlet held up against land destruction and lethal damage,
and this engine has no instant speed, no opponent land destruction and no stack
to respond on. What IS modelled is the half this deck wants — tapped lands
sacrificed for Titania's Elementals and for a recursion loop, plus two life —
and that half alone is worth +0.0124.

**NEITHER OF ITS KNOBS IS LOAD-BEARING**, said out loud because CLAUDE.md
requires it and because a card whose entire content is a policy is exactly
where that matters. n=4,000, T20: `zuran_keep` 4 / 6 / 8 gives +0.0143 /
+0.0112 / +0.0118, and `zuran_life_floor` 1 / 8 / 15 gives +0.0092 / +0.0112 /
+0.0097 — every setting inside every other setting's bar, and the sacrifice
count barely moves with them (1.00 to 1.33 a game). What limits the card is how
often a payoff is on the battlefield at all, not how greedy the pilot is.

### AND THE BATCH TURNED UP A DEFECT IN A CARD ALREADY IN THE DECK

Awaken the Woods makes **land creature** tokens, which forced the question "can
a land creature tap for mana the turn it arrives". 302.6 says no — the rule
gates "a creature's activated ability with the tap symbol" and says nothing
about what else the permanent is — and the engine said yes, because
`available_mana` read `c.is_land` and never looked at `sick`.

**DRYAD ARBOR HAS THEREFORE BEEN TAPPING FOR {G} ON THE TURN IT WAS PLAYED
SINCE 2026-09-07**, for the life of this deck. `land_mana_live()` is the fix,
`land_creature_sick=False` restores the old behaviour exactly, and
`tests/test_azusa_batch4.py` pins both halves (no mana this turn, mana next).

Measured on its own, N=6,000, same seeds, knob off vs on
(`results/azusa_dryad_arbor_302_6.txt`):

| horizon | win rate | damage |
|---|---|---|
| T10 | **−0.0045 ±0.0022** | −0.49 ±0.19 |
| T20 | −0.0020 ±0.0030 — inside its bar | −0.37 ±0.21 |

6.5% of games differ. **THE TABLE WAS REGENERATED FROM AN EMPTY CACHE AND
0 OF 58 ROWS MOVED BEYOND THEIR OWN OLD BAR**, with no sign flipped — so the
deck's own win rate moved and not one card's ranking did, which is what says
the cut bar above is safe to quote against either version of the table. Five
decks were checked against a HEAD worktree and are **bit-identical**; only
azusa touches this code.

**What is deliberately still blind**, written down rather than left to be
found (§0z15): an ANIMATED land. `land_mana_live` reads `card.is_creature`, a
fact about the card, so a plain land animated this turn is not covered —
Sylvan Awakening and Nissa, Who Shakes the World both grant haste (702.10b), so
the only unmodelled case is Rude Awakening's hasteless mode on a land played
the same turn, and all three cards were cut from the list on 2026-09-10.

### THREE SHORTLISTED 2026-09-14, and what a shortlist is NOT

`Candidate` now carries `shortlist` and `proposed_cut`, and
`python -m edhmc.pending` prints those rows first and marked. **This is a
review flag, not a fourth state**: `build_pending` does not apply them, no
table contains them, and no deck list moves. It exists because "these three
are worth a head-to-head" is exactly the kind of statement that lived in a
conversation and was lost, which is the same gap the `Candidate` class itself
was written to close.

| shortlisted | proposed cut | its row | why this cut |
|---|---|---|---|
| Traveling Chocobo +0.0291 | Yavimaya Elder | **+0.0023 ±0.0023** | the weakest evaluated row in the deck, and its payoff is MORE LANDS |
| Nissa, Resurgent Animist +0.0285 | Wayward Swordtooth | +0.0038 ±0.0029 | its whole function is a FOURTH land drop |
| Awaken the Woods +0.0188 | Kozilek, Butcher of Truth | +0.0056 ±0.0022 | top-end for top-end; Ulamog stays, so Eye of Ugin keeps a target |

**All three cuts share one mechanism and it is the deck's own standing
finding**: this list is CARD-limited, not mana-limited — 2.77 land drops
granted a turn against 1.33 used (§0z4) — so the cards that supply more lands
or more land drops are the ones whose rows sit at the bottom, and they sit
there for a reason that is explainable rather than statistical.

**NONE OF THIS IS EVIDENCE FOR THE SWAP, and the arithmetic that looks like it
is is the §0c error.** A candidate row and an ablation row share a baseline;
subtracting them does not give the swap. Each pair needs its own paired run
before anything is staged.

**Three cards that look like better cuts and are not:**

* **Sylvan Library** (−0.0003 ±0.0018) is the most inviting row in the table
  and is the trap: it is MODEL-BLIND — the module gives it no script at all,
  which is precisely why it was chosen as the victim slot these six were
  measured in. Its row says the model has no eyes there, not that the card
  does nothing.
* **Bane of Progress** (−0.0007 ±0.0023) is `PARTLY_MODELLED` and has already
  cost this project two withdrawn swaps (§0z2).
* **Quirion Ranger** (−0.0013 ±0.0012) is the only negative row in MODEL-BLIND
  and its activated ability is unimplemented (§0z18 left it open).

### A PERFORMANCE CLIFF IN SHARED CODE, found by the one input that reaches it

Sweeping Awaken the Woods to **X=8** produced a game that does not finish: the
first attempt at the sweep sat on **seed 80683 for 5.7 HOURS** and was killed
with nothing written. X = 3, 4 and 6 each run 4,000 games in about 75 seconds,
and 683 of the first 684 games at X=8 complete normally, so this is one game in
several hundred rather than a slow configuration.

**It is not this card, this engine, or unbounded tokens — it is
`engine.can_pay`.** Profiled over 90 seconds of that seed:

| | calls | internal time |
|---|---|---|
| `can_pay` | 11,299 | — |
| `generic_key` (inside it) | **17,299,692** | 112s of 180s profiled |
| `min` over those keys | 17,336,664 | 18s |

That is ~1,500 key evaluations per `can_pay`. Each generic pip is assigned by a
`min` over every available mana unit, so one call costs about
(mana units × generic pips) — and this deck drives both factors up at once:
**Ashaya makes every nontoken creature a Forest**, Awaken adds eight more land
tokens, and Kozilek and Ulamog ask for {11}. A big-board game makes ~11,000
such calls.

**All six engines share `can_pay`**, and this is a performance property rather
than a wrong answer, so it is recorded rather than fixed here — the same
reasoning queued item 17 gives for not changing an engine-wide rule inside a
candidate evaluation. It is also why the X sweep stops at 6.

### One more check that could not fail

`tools/audit_cards.py` raised an ERR on Zuran Orb reading **"cost {0}, oracle
{0}"** — two identical strings and a failure. `parse_cost` turned the Scryfall
string `{0}` into `{"gen": 0}` while every deck module writes the same cost as
`{}`, and the comparison is a dict equality. Zuran Orb is this project's first
zero-cost card; the same false ERR was waiting for any Mox or Ornithopter.
Fixed in the parser. **A check that reports a false failure teaches you to
ignore failures**, which is the same argument `KNOWN_MODEL_LIMITS` exists for.

---

<a id="0z22"></a>

## 0z22. FIXED — the tables got slower; `can_pay` was most of it. 1.22x, bit-identical

2026-09-14. Ablation runs had been getting longer. Profiled rather than
guessed, optimised, and **proved to change nothing**: all six decks come back
BIT-IDENTICAL against a pre-optimisation tree at n=1,200, `validate.py` is
`+0.00` on all 18 metrics, and all thirteen test suites and twelve mutation
checks still pass.

### Where the time went

`engine.can_pay` — shared by all six engines, called ~213 times per azusa game,
because `main_phase` asks every card in hand on every pass of its casting loop.
Four changes, all of them hoisting or memoising work that was already being
recomputed:

| change | what it was doing |
|---|---|
| **early bail** on `sum(cost.values()) > len(units)` | an eight-drop on turn three was answered by building a candidate list per pip and discovering it at the generic check. One comparison now. |
| **the generic key is built once per unit**, not once per unit per pip | `supply` is a snapshot, `len(units[i])` and `w(i)` are fixed for the call — only `owner_free` varies, and it is 0 or 1 |
| **memoise the rarest-colour scan** on the colour SET | a green deck's twenty Forests are all `frozenset({"G"})` |
| **hoist `(len, w)`** out of both pip loops | the same tuples, built once |

Plus two in `azusa` alone, which was the slowest deck by 4x: `ashaya_lands`
reads its knob once at construction (626,800 calls a run), and
`available_mana` guards the Ashaya branch and memoises `want` per colour set.

**ORDERING IS UNCHANGED AND THAT IS THE WHOLE RISK.** `(owner_free, static)`
compares identically to the old `(owner_free, -surplus, len, w)`, and a stable
sort plus "first un-taken entry, preferring `owner_free == 0`" selects exactly
what repeated `min(remaining, key=...)` selected, tie-break included: `min`
returns the first minimal element in iteration order, `remaining` is in
increasing index order, and `sorted` is stable.

### What it bought

Interleaved A/B, 6 reps of 200 games, medians:

| deck | before | after | |
|---|---|---|---|
| azusa | 100.5 | 132.5 games/sec | **1.32x** |
| tivit | 331.0 | 428.7 | 1.30x |
| lorehold | 290.5 | 338.9 | 1.17x |
| shilgengar | 424.7 | 477.2 | 1.12x |
| rendmaw | 425.4 | 464.5 | 1.09x |
| karlov | 459.8 | 492.1 | 1.07x |
| **six-deck** | 23.30 | 19.11 ms/game | **1.22x** |

End to end, a full azusa table at N=1,500 on 8 processes: **6m00s → 4m08s,
1.45x** — better than the per-game figure, because the harness's own per-card
overhead shrinks with it.

### A CHANGE THAT LOOKED OBVIOUSLY RIGHT AND MEASURED AT NOTHING

`azusa.creature_lands` is O(board) and three callers ask it on paths that run
per permanent — 842,029 calls to `is_creature_land` in 120 games. Caching it
behind a `Board.version` stamp is the obvious fix and it measured **1.01x on
azusa and 0.99x on rendmaw**. It was REMOVED, not kept: it put an invariant on
every `Board` mutator and an invalidation obligation on a shared class, to buy
noise.

The reason is the guard already on the line above it: Ashaya is on the
battlefield in a minority of games, so the expensive branch was already being
skipped in most of them and the call count was concentrated in the few games
where it is out. **A call count is not a cost profile**, which is the
transferable half of this.

### AND A MEASUREMENT FINDING THAT OUTLIVES THIS SECTION

**WALL-CLOCK TIMINGS TAKEN AT DIFFERENT MOMENTS ARE NOT COMPARABLE ON THIS
MACHINE.** The same unmodified code, benchmarked twice a few minutes apart,
gave azusa 86.5 and then 102.1 games/sec — an 18% drift, larger than most of
the individual wins above, and a copy of the tree in a different directory ran
15% slower than the original for no reason in the code. Two conclusions were
nearly drawn from that noise: that the round-four changes were a regression
(they were not), and that the memo was worth 1.17x (it is worth nothing).

The fix is to **interleave A and B inside ONE process**: load both trees under
`sys.path` manipulation, alternate reps, take medians. That cancels drift the
way common random numbers cancel shuffle variance — the same idea this project
already rests on, pointed at the clock instead of at the deck. Any future
performance claim here should be measured that way.

### An operational footgun worth knowing

`tools/ablation.py` stops at `ABLATE_BUDGET` seconds, **default 240**, and
prints "N cards still to do — rerun to resume". `regen_tables.sh` sets its own
budget and retries in a loop, so it is unaffected — but the command CLAUDE.md
documents for a single deck does not, and redirecting its stdout over a
committed table truncates that table to the partial run. Hit for real on
2026-09-13, recovered with `git checkout`. Pass `ABLATE_BUDGET` when running
one deck by hand.

---

<a id="0z23"></a>

## 0z23. CLOSED — the cache rule was unobeyable, so the caches went untracked; provenance replaces deletion

**Found 2026-09-15 by `tools/check_docs.py` on its first run**, which is the
only reason this entry exists: nothing else in the repo compares the manifest
against the directory it describes.

### What is true on disk

`results/caches/` holds **four** cache files — the `n6000` ones for rendmaw,
lorehold and karlov, and tivit's `n2000`. `docs/ABLATION_CACHES.md` describes
**fourteen**. The missing ten include **every `_medblank` cache at N=15,000**,
which is to say every cache that produced a table now committed in `results/`.

They were added in `d158724` and deleted in `b09055c`, whose message says
"Regenerates all ablation caches and tables against the new engine fingerprint;
deletes the ones now stale". The deletion happened; the regenerated caches were
never added back, and `python -m tools.cache_manifest --write` was not re-run in
that commit, so the manifest went on describing files that no longer exist.

`.gitignore` still carries a comment block explaining that the caches are
tracked and that there are "TWELVE, not four".

### And the four survivors are stale by the repo's own rule

Every one of them disagrees with its live fingerprint:

| cache | recorded | live |
|---|---|---|
| `ablation_cache_rendmaw_10-20_n6000.json` | `2420c73d1c5c6702` | `0ac5ad66a8f9fff1` |
| `ablation_cache_lorehold_10-20_n6000.json` | `e24bde4734dbe087` | `fbc552aea5d15b19` |
| `ablation_cache_karlov_10-20_n6000.json` | `4fbd678bca7abb97` | `431e2b18fdea7711` |
| `ablation_cache_tivit_10-20_n2000.json` | `21c9ed8c8db77c8e` | `d55ddbf4fa5ff163` |

The rule this file and `cache_manifest.py` both state is **"if the fingerprint
differs, DELETE the cache"**, so all four are already condemned by it.

### What this does and does not cost

**It does NOT invalidate any committed table.** The tables in `results/` are
the artefact; the caches are the intermediate that lets a run resume. Every
table is still the output of the run that produced it, and the azusa table
was verified to reflect the current ledger — it carries an Idol of Oblivion
row and no Cauldron of Essence row, which is correct after the 2026-09-13
withdrawal.

**What it costs is the resume.** Any regeneration now starts from empty, at
full cost, on all six decks. That is the thing tracking the caches was for.

**And it makes one paragraph of the manifest actively misleading.** The
manifest warns at length that "RENDMAW IS THE EXCEPTION AND ITS THREE CACHES
ARE STALE" and that `results/ablation_rendmaw.txt` "still carries a Cauldron of
Essence row for a card the deck no longer contains". The rendmaw caches it
names are gone, and the table was regenerated — there is no Cauldron row in it.
The warning is now about a state that no longer exists, in the file whose whole
job is to be believed about staleness.

### RESOLVED 2026-09-16 — PROVENANCE REPLACES DELETION

The first resolution was **delete the four survivors and regenerate the
manifest**, and it was carried out: `results/caches/` went empty and all the
checks passed. **It was the right cleanup and the wrong policy**, and the
policy is what this entry is now about.

**The rule it left in place was "if the fingerprint differs, DELETE the
cache", and that rule cannot be obeyed.** `engine.py`, `opponents.py`,
`experiment.py` and `ablation.py` are in EVERY deck's fingerprint. So a
comment, a docstring, a bookkeeping call — anything at all in a shared file —
condemns all six caches and demands a six-deck regeneration. **That
regeneration was then measured: it takes about four hours** (2026-09-16,
N=15,000, four workers), **and it moved 0 of 379 rows beyond their own old
bar, with 0 sign flips and 0 category changes.** Four hours to confirm nothing.

A rule that expensive is not followed, and the record shows it was not: that
is exactly how `b09055c` came to delete ten caches without re-running the
generator. **The defect was never really the stale manifest. It was a rule
whose only compliant action was unaffordable, so the honest options were to
ignore it or to go permanently cacheless.**

### THE REPLACEMENT: BUILT-AT, AND THREE STATES

A cache now records the fingerprint it was **built at** —
`results/caches/PROVENANCE.json`, stamped by `ablation.py`'s `save()` at the
moment the numbers are written, and **never rewritten afterwards**.

**That immutability is the whole mechanism.** The old manifest recorded the
fingerprint computed when the MANIFEST was generated and printed it beside each
cache, which reads as "this cache was built by this code" and is not what it
meant. So regenerating the manifest certified whatever happened to be on disk —
**the one command that made the staleness check pass was also the command that
destroyed the evidence.** A built-at stamp cannot do that; nothing later can
forge it.

Comparing built-at against live gives four states, rendered per cache in
`docs/ABLATION_CACHES.md`:

| state | meaning | what to do |
|---|---|---|
| **CURRENT** | built-at equals live | resume freely |
| **VERIFIED** | they differ, and a recorded check says the deck's NUMBERS did not move | resume freely; the evidence is recorded |
| **SUSPECT** | they differ and nothing has checked | check before resuming |
| **UNRECORDED** | no provenance | do not resume onto it |

**SUSPECT is not condemned.** It is resolved by EVIDENCE, and the evidence is
cheap: `tools/check_unchanged_decks.py` runs the BASELINES ONLY against a
worktree at the cache's `built_commit`. A bit-identical result means the cache
is still good; `python -m tools.cache_manifest --verified <deck> "<evidence>"`
records that, with the evidence string mandatory — an unevidenced "trust me" is
what this scheme replaced. Only a deck whose baseline actually moved needs its
table rebuilt, **and only that deck.**

### IT WAS EXERCISED ON ITSELF, WHICH IS THE ONLY REASON TO BELIEVE IT

Adding the stamping call to `ablation.py` put a bookkeeping line in a file that
is in the fingerprint set, so all six caches immediately went **SUSPECT** — the
exact trivial-change-condemns-everything scenario, produced by accident while
building the fix for it.

Resolving it took **26 seconds**: baselines at HEAD, baselines in a worktree at
`3234bee`, diffed. **BIT-IDENTICAL on all 8 metrics for all six decks, 0 decks
moved.** All six are now VERIFIED with that evidence attached.

**26 seconds against four hours, for the same conclusion.** That ratio is the
finding, and it is why the old rule was the defect rather than the safeguard.

### WHAT THIS DOES NOT CHANGE

**The underlying hazard is real and the guard still stands.** `ablation.py`
keys its cache on deck, horizons, N and blank mode — not on the code — so a
full cache makes `todo` empty and a run REPRINTS OLD NUMBERS while looking like
it measured. Nothing here softens that. What changed is the response: from
"delete on any difference" to "prove it, cheaply, and record the proof".

**A SUSPECT cache is still not resumable.** The difference is that clearing it
costs seconds of evidence rather than hours of recomputation.

### THE LESSON

§0q says a hand-maintained set is a claim, and claims rot; the fix is
derivation plus a check. §0z23's first half added the missing half of that —
**a generated file is only as current as the last time someone ran the
generator** — and this second half adds the one after it:

**A CHECK WHOSE ONLY REMEDY IS UNAFFORDABLE IS NOT A SAFEGUARD, IT IS A
FUTURE VIOLATION.** It will be skipped, and the skipping will be silent,
because the alternative is hours of compute for a result nobody expects to
differ. When you write a check, cost its remedy. If the remedy is expensive,
the check needs a cheap way to establish the thing it actually cares about —
here, "did the NUMBERS move", which is answerable in seconds, rather than "did
the fingerprint move", which is answerable instantly and is the wrong question.


---

<a id="0z25"></a>

## 0z25. MEASURED — three azusa cards implemented and measured, and the biggest number came with the biggest caveat

> **CORRECTED 2026-09-17, §0z28.** The Guardian Project row below was measured
> on code where The Great Henge's `draw(1)` had been swallowed into Guardian
> Project's `if`, so the card drew TWICE per nontoken creature. Re-measured on
> the same slot, N and horizon after the fix: **+0.0279 ±0.0036**, not +0.0481.
> The "upper bound" argument below read `guardian_project_draws`, and the extra
> draw was credited to `henge_draws`, which is why it held with equality and
> certified nothing. Zendikar's Roil and Splendid Reclamation are unaffected —
> the swallowed lines fire only with Guardian Project on the battlefield.

Batch 5, 2026-09-16. Oracle text verified from `api.scryfall.com` the same day
(access to it had just been restored — see `CLAUDE.md`'s network note). Same
**Sylvan Library** victim slot as batches 3 and 4, so all sixteen candidate
rows sit on one scale. N=15,000 paired, T20.
`python -m tools.candidates azusa5 --n=15000 --turns=20`.

| card | win rate T20 | signal | would rank |
|---|---|---|---|
| **Guardian Project** | **+0.0481 ±0.0042** | both | **1st of 16 candidates; ~2nd in the deck** |
| Zendikar's Roil | +0.0133 ±0.0029 | both | mid-table, around Springheart |
| Splendid Reclamation | −0.0013 ±0.0022 | `--` | a blank |

### GUARDIAN PROJECT, AND WHY THE NUMBER WAS CHECKED RATHER THAN BELIEVED

+0.0481 is larger than Traveling Chocobo (+0.0291) and Nissa, Resurgent
Animist (+0.0285), and sits just under **Scute Swarm's own ablation row
(+0.0518)**. A newly implemented card scoring near the best card in the deck is
exactly where an over-implementation hides, so the upper bound was measured
rather than argued:

* nontoken creature ETBs with the enchantment out: **3.60/game**
* `guardian_project_draws`: **3.60/game** — *equal*, so it never double-fires
* token creature ETBs: **224.87/game**, and it fires off **none** of them

The name clause can only ever SUPPRESS a draw, so draws ≤ eligible ETBs is a
hard bound, and it holds with equality.

**THE EQUALITY IS ITSELF THE FINDING.** "If it doesn't have the same name as
another creature you control or a creature card in your graveyard" **never
bites in a singleton list** — every creature name is unique and every copy in
this deck is a TOKEN. The card here is simply *"draw a card whenever a nontoken
creature enters"*, and the row must be read as that. In a list with nontoken
copies or repeated names it is worth strictly less.

Supporting metrics: damage +3.73 ±0.29, cards_drawn +5.30 ±0.22 (more than the
3.60 draws — the rest is the cascade into lands and landfall), landfall
+1.53 ±0.10, P(deploy) 0.315, so about **11 draws per resolution** in a deck
whose standing finding is that it is CARD-constrained rather than
mana-constrained (§0z4, §0z21). The mechanism and the size agree.

**A CEILING** for queued item 17's reason, though not a tight one: ~26 cards
drawn from a 99-card library is nowhere near decking.

### SPLENDID RECLAMATION — A BLANK, AND THE PROPOSAL'S RATIONALE WAS BACKWARDS

It was proposed on the argument that it "reads the deck's OWN graveyard-land
package: Life from the Loam, Ramunap Excavator, Crucible of Worlds and Titania
are all already in the list." **That is exactly why it fails.** Measured:

* fetches cracked 3.09/game, `lands_from_graveyard` 2.97/game
* **maximum lands in the graveyard at any point in a whole game: 1.11**
* lands the card actually returned: **0.217/game**

Those four cards do not FEED the graveyard, they DRAIN it. They are competing
consumers of the same resource and they win the race, because they act every
turn while this acts once. The §0z4 Sapling Nursery shape — a card that makes
the engine already there measurably worse — pointed at a resource rather than
at a combo.

**Not refuted as a card, refuted as a fit for THIS list.** In a deck that
discards or sacrifices lands it is a different row entirely.

### A CORRECTION MADE THE SAME SESSION, worth more than either number

Two of the fifteen proposals — Heliod, Sun-Crowned (karlov) and Underworld
Breach (lorehold) — were **already measured**, in the `karlov1` and `lorehold1`
batches, both inside their own bars at N=6,000. Proposing them was a miss: the
deck lists were checked and `tools/candidates.py`'s batch history was not.

They were then briefly reported as *unimplemented vanilla stand-ins*, on the
evidence that their `C(...)` constructors carry no `script=`. **That was
wrong.** Behaviour attaches BY NAME at least as often as by script: `karlov.py`
carries Heliod's devotion gate, lifegain trigger and lifelink activation, and
`lorehold.py` has a whole `underworld_breach()` escape loop bounded by the
`breach_cap` knob. Traveling Chocobo is the same shape — no script, fully
implemented, dispatched by name in three places.

**`script=` IS NOT THE IMPLEMENTATION SURFACE, AND ITS ABSENCE IS NOT EVIDENCE
OF A BLANK.** Before calling a card unimplemented, grep the engine for its
NAME. And before proposing a card at all, grep `tools/candidates.py` as well as
the deck list — that check is cheaper than either.


---

<a id="0z26"></a>

## 0z26. MEASURED — the remaining ten proposals, implemented across four engines

2026-09-16, following §0z25's three. N=15,000 paired, T20, each in its deck's
established victim slot. `tools/candidates.py` batches `rendmaw2`, `karlov2`,
`lorehold2`, `tivit1`.

| deck | card | win rate T20 | signal |
|---|---|---|---|
| karlov | **Bloodthirsty Conqueror** | **+0.0328 ±0.0033** | both |
| tivit | **Anointed Procession** | **+0.0291 ±0.0034** | both |
| rendmaw | Parallel Lives | +0.0157 ±0.0026 | both |
| karlov | Alhammarret's Archive | +0.0129 ±0.0024 | both |
| lorehold | Past in Flames | +0.0102 ±0.0038 | both |
| lorehold | Jeska's Will | +0.0074 ±0.0043 | both, **hard floor** |
| rendmaw | Mycoloth | +0.0069 ±0.0023 | both |
| tivit | Urza, Lord High Artificer | +0.0034 ±0.0025 | `--`, **floor** |
| tivit | Sai, Master Thopterist | +0.0003 ±0.0022 | `--` |

**Pitiless Plunderer was NOT measured** — see below.

### THE TWO BLANKS ARE THE MOST USEFUL ROWS

**Sai, Master Thopterist makes 0.155 Thopters a game** in a deck that produces
**51 artifacts a game**. It triggers on CASTING AN ARTIFACT SPELL, and almost
every artifact tivit produces is a TOKEN it creates rather than a spell it
casts. The deck's artifact density is an illusion from this card's point of
view. It is fully implemented, so this IS evidence about the card in this list.

**Urza, Lord High Artificer is a FLOOR and the row should not be read as the
card.** Only the Construct is modelled — with a DYNAMIC P/T read live, which is
§0z3's trap handled rather than repeated. The two abilities left out are the
big ones: "Tap an untapped artifact you control: Add {U}" in a deck making 51
artifact tokens a game, and "{5}: exile the top card, play it free". Both are
real and large. `PARTLY_MODELLED`.

### BLOODTHIRSTY CONQUEROR, AND WHY IT IS MODELLED AS A COMBO PIECE

Its oracle text is **word for word Exquisite Blood's**, on a 5/5 flying
deathtouch body. This engine models Exquisite Blood as a COMBO DETECTOR — the
loop with Sanguine Bond / Vito / Enduring Tenacity — and not as the continuous
"gain life whenever an opponent loses life" it actually is.

So the new card was given the identical treatment and `COMBO_A` became a SET.
**Implementing the general trigger for the new card and not the old one would
have made a strictly-worse card measure strictly better** — §0u's shape, the
same rule implemented twice and implemented two different ways. Both cards are
now floors for the same reason, which is the honest state.

The **damage is −2.20** while win rate is +0.0328, and that is the mechanism
rather than a defect: the extra wins arrive by the combo route, which ends the
game before the board deals damage. Combo wins move 0.312 → 0.375.

### PITILESS PLUNDERER WAS ABANDONED MID-IMPLEMENTATION, AND WHY

Its entire value in rendmaw is Treasures-as-mana. `Game.treasures` has been a
field on the rendmaw engine since the beginning and **nothing in `engine.py`
has ever read or written it** — a dead field, §0z12's loaded gun.

Making it live means appending Treasure units to the mana pool and DECREMENTING
them when spent. Lorehold does this with its own `pay()`, which knows where the
treasure block starts by index. The shared `engine.spend()` does not, and its
ownerless-unit path is already used by azusa's Castle Garenbrig and
shilgengar's Treasures — so a `g.treasures` decrement threaded through it would
change a primitive **five engines share**.

Without the decrement the Treasures are infinite. **A card measured on infinite
mana is not a measurement**, so the work was backed out rather than shipped.
Treasures-as-mana for rendmaw is a real engine feature that deserves its own
change, its own mutation test and its own before/after — not a ride-along in a
candidate batch.

### MYCOLOTH'S DEVOUR IS A POLICY, SAID OUT LOUD

`mycoloth_devour` (4) eats only TOKENS, never a real card. **That is the same
shape that cost 0.034 win rate on shilgengar**, where "would only ever sacrifice
1/1 tokens" was written as conservatism and amounted to asserting the
commander's ability does nothing. The knob exists so the next reader can sweep
it; the default is not claimed to be optimal, and eating tokens in a deck whose
payoffs COUNT tokens is a real cost this policy pays.

### WHAT WAS VERIFIED

* `tools/validate.py` **+0.00 on all 18 metrics** across all six engines after
  changes to `engine.py`, `karlov.py`, `lorehold.py`, `tivit.py` and
  `azusa.py`.
* `check_unchanged_decks` against a worktree at `3234bee`: **BIT-IDENTICAL on
  all 8 metrics for all six decks**, because every new path is guarded on a
  card not in any committed list. All six caches re-verified rather than
  rebuilt.
* Every card's MECHANISM counter was read before its win rate was trusted —
  which is how both blanks were explained rather than merely reported.


---

<a id="0z27"></a>

## 0z27. MEASURED — two swaps staged, and the karlov table proves the redundancy finding live

2026-09-16. `-Soulmender +Bloodthirsty Conqueror` (karlov) and `-Plains
+Anointed Procession` (tivit), both staged on the REAL swap rather than on
§0z26's candidate-vs-blank rows.

| swap | T10 | T20 |
|---|---|---|
| karlov `−Soulmender +Bloodthirsty Conqueror` | +0.0257 ±0.0028 | +0.0247 ±0.0035 |
| tivit `−Plains +Anointed Procession` | +0.0113 ±0.0026 | +0.0145 ±0.0040 |

**Both real swaps are SMALLER than their candidate rows** — Conqueror +0.0328 →
+0.0247, Procession +0.0291 → +0.0145 — because the candidate number is value
over a blank in a FREED slot and the swap also pays for what it cut.
Procession loses half, and that half is the land. §0c is the rule; this is what
it costs in practice.

Soulmender is the cheapest cut in the karlov list, checked rather than assumed:
**−0.0011 ±0.0011, signal `win`** — significantly negative.

> **RESTATED 2026-09-17 (§0z33).** The tivit row was measured before
> §0z30 moved that deck's baseline by +0.0647. Re-measured on the new
> baseline, same N and seeds: +0.0133 ±0.0027 at T10 and +0.0157 ±0.0043 at
> T20 (candidate row +0.0325 ±0.0037). Up, inside its bars; the staging
> stands.

> **RESTATED 2026-09-17 (§0z31's cut check).** That row is in the
> MODEL-BLIND section: Soulmender is `KNOWN_BLIND` in karlov, its tap
> ability is not implemented, and a blind row is "not measured", never a cut
> list — the sentence above read it as evidence. The head-to-head therefore
> measures the Conqueror against a vanilla 1/1, and its +0.0254 is a
> CEILING. The staging stands on an acknowledgement written into the Change
> (`cut_unmeasured`), which is a judgement and says so.

> **RESTATED 2026-09-17 (§0z29).** Both karlov rows above were measured
> with Bloodthirsty Conqueror as a GROUND creature (`_evasion.py` had not
> been regenerated after the card was added). Re-measured with flying:
> +0.0259 ±0.0027 at T10 and +0.0254 ±0.0037 at T20 — inside a
> ten-thousandth of these. The staging stands; the karlov table below was
> rebuilt with the tag on, and §0z29 carries the comparison.

### THE KARLOV REGENERATION IS THE RESULT WORTH KEEPING

Staging changed `build_pending`, so the table was rebuilt. **Six rows moved
beyond their own old bar and FIVE OF THEM ARE THE COMBO PACKAGE**, moving in a
pattern that is entirely predicted:

| card | before | after | move |
|---|---|---|---|
| **Exquisite Blood** | +0.0367 ±0.0036 | **+0.0292** | **−0.0075** |
| Enduring Tenacity | +0.0303 ±0.0036 | +0.0378 | +0.0075 |
| Vito, Thorn of the Dusk Rose | +0.0193 ±0.0033 | +0.0252 | +0.0059 |
| Sanguine Bond | +0.0209 ±0.0032 | +0.0255 | +0.0046 |
| Vizkopa Guildmage | +0.0043 ±0.0023 | +0.0079 | +0.0036 |

**Exquisite Blood got WORSE and every loop partner got BETTER, and that is one
mechanism seen from both sides.** Bloodthirsty Conqueror is a second COMBO_A
half, so ablating Exquisite Blood no longer breaks the loop — Conqueror still
closes it — and a leave-one-out score is exactly the quantity redundancy
destroys. Symmetrically, each partner now has TWO ways to close rather than
one, so removing a partner costs more.

**This is the standing "leave-one-out is blind to redundancy" finding happening
live in a table, rather than being recalled from Karlov's original +0.02-each
/ +0.0513-as-a-group measurement.** The practical consequence: **Exquisite
Blood's new row is not evidence that the card got worse.** Ablate the package
together — Exquisite Blood, Bloodthirsty Conqueror and the four partners — or
the table will keep understating all six.

New rows, both consistent with their candidate measurements: Bloodthirsty
Conqueror **+0.0305 ±0.0032** (`PARTLY MODELLED`, against +0.0328 as a
candidate) and Anointed Procession **+0.0284 ±0.0034** (`MODEL-EVALUATED`,
against +0.0291).

### TIVIT MOVED THREE ROWS AND ONLY TWO ARE EXPLAINED

Azorius Signet +0.0032 and Tempting Contract +0.0031 both ROSE, which is what
cutting a land should do: at 35 lands the remaining mana sources carry more.
**Rhystic Study FELL −0.0067 and that is NOT attributed.** It is plausibly the
same mechanism — a three-mana enchantment that does nothing the turn it lands
is worse in a land-light list — but that is a guess, and this project's rule is
to say so rather than invent one. Worth watching if tivit is regenerated again.

**Tivit went 64 → 65 ablation rows**: cutting a basic converts a land into a
nonland slot.

### TWO CHECKS FIRED, AND THE SECOND ONE WAS THE INTERESTING ONE

**`check_scripted_coverage` refused to run the regeneration at all** until both
newly staged cards were deliberately classified. Staging a card puts it in
`build_pending`'s list, and §0q's rule is that the split is a CLAIM. The first
launch spent its retries busy-failing on this before it was noticed.

**Then all six caches went SUSPECT for TWO DIFFERENT REASONS, and only one of
them was resolvable the usual way.**

* karlov and tivit were **genuinely stale**: staging changes `build_pending`,
  which is the baseline every cached number was measured against. This is
  precisely what the fingerprint's `staged:<deck>` component exists to catch.
  **`--verified` would have been forgery here** — `check_unchanged_decks`
  compares SIMULATION baselines, which are computed from the deck MODULE and
  not from the staged list, so a bit-identical result would have certified
  nothing at all. They were deleted and rebuilt.
* azusa, lorehold, rendmaw and shilgengar moved only because
  `tools/ablation.py` — in every deck's fingerprint — gained two CLASSIFICATION
  entries. Those decide which table SECTION a card prints in and touch no
  number. The right evidence is §0z4's, not `check_unchanged_decks`:
  **re-render each table from its existing cache and diff. All four came back
  BYTE-IDENTICAL.**

**THE LESSON: "IS THIS CACHE STILL GOOD" HAS MORE THAN ONE RIGHT CHECK, AND
PICKING THE WRONG ONE CERTIFIES NOTHING.** `check_unchanged_decks` answers "did
the SIMULATION move"; re-rendering from cache answers "did the TABLE move"; and
neither answers "did the BASELINE LIST move", which only a rebuild can settle.
Match the check to what actually changed — a fingerprint moving does not tell
you which of the three it was.


---

<a id="0z28"></a>

## 0z28. FIXED — two cards on one hook, one indentation apart; and a failing test nobody ran

**The defect.** `azusa.make_permanent` hooks "a nontoken creature you control
enters" for The Great Henge (counter + draw) and, since §0z25, for Guardian
Project (draw, gated on the name clause). The §0z25 commit (`527d7da`)
inserted the Guardian Project block BETWEEN the Henge's `perm.counters += 1`
and its `self.draw(1)`, so the Henge's draw and its `henge_draws` counter
landed inside `if … self.has("Guardian Project")`. Net effect, from
`527d7da` to the fix:

* **The Great Henge drew nothing.** Counter yes, card no.
* **Guardian Project drew twice per eligible creature** — once under its own
  name clause, once as the Henge's orphaned line — and was measured in that
  same commit.

**How it was found.** Not by a number. `tests/test_azusa_batch3.py` pins the
Henge's draw ("draws off a nontoken creature, not off tokens", "draws off a
TUTORED creature too") and had been failing since `527d7da` — checked by
running it at `5dc60f5` (15/15) and `1d7298a` (13/15). Every test module in
`tests/` was honest about its exit code; **nothing ran them.** No runner, no
CI, and the session-close protocol listed `check_docs`, `pending` and
`validate` and not the tests. `python -m tests` exists now and is in the
protocol.

**Why §0z25's own check did not catch it.** It compared
`guardian_project_draws` (3.60/game) to eligible nontoken ETBs (3.60/game)
and read the equality as a proved bound. The extra draw was credited to
`henge_draws`, a counter nobody read for a card that was not in the list.
`cards_drawn` (+5.30) against `guardian_project_draws` (3.60) was the visible
gap, and it was explained away as cascade. **A mechanism counter certifies
only what it counts; check `cards_drawn` against the SUM of every draw
counter.**

**Corrected measurement.** `python -m diagnostics.run_guardian_henge`,
`results/guardian_henge.txt` — same method as §0z25 (`candidates.add_value`,
Sylvan Library slot, T20, N=15,000 paired), so the rows sit on the same scale:

| card | win rate T20 | damage | cards_drawn | own draw counter | other card's counter |
|---|---|---|---|---|---|
| Guardian Project | **+0.0279 ±0.0036** (was +0.0481 ±0.0042) | +2.13 ±0.23 | +2.53 ±0.14 | 2.76 | 0.00 |
| The Great Henge | **+0.0242 ±0.0034** (2026-09-10: +0.0217 ±0.0034) | +1.95 ±0.22 | +1.99 ±0.13 | 2.30 | 0.00 |

Guardian Project loses 42% of its number and lands **inside the bars of
Traveling Chocobo (+0.0291 ±0.0040) and Nissa, Resurgent Animist (+0.0285
±0.0041)**: a member of the deck's top candidate SET, not its first. The
Henge's corrected row agrees with its pre-bug row within a third of a bar,
which is the fix restoring the card rather than changing it. Each card's
counter is zero when the other is under test, which is the cross-check that
would have failed before.

**What did NOT move.** Neither card is in the built azusa list, so the
committed table, the cache and every other candidate row are unaffected —
`tools/check_unchanged_decks.py` against a worktree at `3234bee`: BIT-IDENTICAL
on all 8 metrics for all six decks, recorded on the azusa cache. **That check
answers "did the deck move", not "is the card right"** — a broken candidate
implementation is invisible to it by construction, which is why the card's
own test is the only guard.

**The lessons, promoted to `CLAUDE.md` without their dates:** a test that is
not run does not exist; two cards on one hook are one indentation apart;
read `$?` only from an unpiped command.


<a id="1"></a>

## 0z29. FIXED — a generated name set is only as current as its last generation, and it was in no fingerprint

2026-09-17. Found by the L1 sweep, which fixed `tag_flying.py`'s stale
docstring and re-ran it to prove the header change: the regeneration also
added **Bloodthirsty Conqueror to `FLYING`**, and Sai and Urza to `HUMAN`.
The Conqueror is `{3}{B}{B}` 5/5 **flying, deathtouch** (Scryfall
`keywords: ['Deathtouch', 'Flying']`, re-fetched today). It was added to
`decks/karlov_v2.py` on 2026-09-16 and measured the same day — the §0z26
candidate row, the §0z27 head-to-head that STAGED it, and every row of the
regenerated karlov table — with `flying=False`, because `Card.flying` is read
from the generated `_evasion.py` at construction and nobody regenerated it.
The ledger's own rationale calls the card "a 5/5 FLYING DEATHTOUCH body" in
the sentence that stages it.

**Three things went wrong, and only the first is the card.**

1. **The generator was not re-run when the deck moved.** This is the
   `tag_flying.py` gap of 2026-09-05 (Goldspan Dragon and Caldera Pyremaw
   scored as ground creatures) in its second form: that fix widened the walk
   to module-level candidates, and nothing made re-running it part of adding
   a card. §0q's rule — derive, and CHECK that the derivation was run — had
   been applied to `STATUS.md`, `KNOBS.md` and the cache manifest and not to
   the one generated file that changes combat.
2. **No fingerprint could see it.** `_evasion.py` was in neither `SHARED` nor
   any `PER_DECK` list in `cache_manifest.py`, so regenerating it moved no
   fingerprint, and every cache read CURRENT while the karlov baseline had
   changed. It is in `SHARED` now.
3. **The standing check certified the wrong list.** `check_unchanged_decks`
   came back BIT-IDENTICAL on all six decks after the regeneration, because
   it builds from the deck MODULE and the Conqueror is STAGED, not committed.
   That is exactly the trap CLAUDE.md's "more than one right check" table
   names; the STAGED karlov baseline, measured the same way on
   `build_pending("karlov")` over the same 400 seeds, moved:

   | metric | ground | flying | shift |
   |---|---|---|---|
   | damage | 57.508 | 57.950 | +0.443 |
   | final_life | 30.798 | 30.779 | −0.020 |
   | won / lost / turns_played / cards_drawn / mana_spent / stranded_mv | — | — | 0 |

   Real, small, and invisible to the module-level check. Every other deck is
   unaffected by construction: the regeneration changed four names, and the
   other three (Sai, Urza, Witch Enchanter) are candidates in no staged list.

**What flying is worth to the card: nothing measurable.**
`diagnostics/run_karlov_conqueror.py` (→ `results/karlov_conqueror.txt`)
re-measures both §0z26 and §0z27 with the tag on, at the table's N=15,000:

| measurement | ground (§0z26 / §0z27) | flying (today) |
|---|---|---|
| value over a blank, Soulmender slot, T20 | +0.0328 ±0.0033 | +0.0331 ±0.0033 |
| value over a blank, T10 | — | +0.0295 ±0.0028 |
| real swap −Soulmender +Conqueror, T10 | +0.0257 ±0.0028 | **+0.0259 ±0.0027** |
| real swap −Soulmender +Conqueror, T20 | +0.0247 ±0.0035 | **+0.0254 ±0.0037** |

Every number reproduces inside a ten-thousandth of its bar. The card's value is the
trigger — a second Exquisite Blood — and the games it wins end by the drain
loop, which is why its damage and `lifegain_triggers` columns against a blank
are NEGATIVE (−1.91 ±0.21 and −0.65 ±0.06 at T20): the games are shorter. A
5/5 flier that attacks is not what the deck is buying. **The staging
survives; the numbers it rests on are restated below, not kept.**

**The fix is a check, not vigilance.** `tag_flying.py` now writes
`SCANNED`, the set of every card name it fetched, into `_evasion.py`, and
`check_docs` compares it with the cards the deck modules construct TODAY —
deck members and module-level candidates, the same walk the generator uses —
and fails on any difference, with `--mutate` proving it fires when a card is
added. It cannot check the TAGS without Scryfall; it checks that the
generator saw every card, which is the failure that actually happened. The
closing checklist gains `python -m tools.tag_flying --write` for any session
that adds a card.

**The karlov table is rebuilt** from an empty cache with the tag on, at
N=15,000 — the third rebuild of that deck in two days, and the only one of the
six that the regeneration could have moved. Against the 2026-09-16 table:
**0 of 64 rows moved beyond their own old bar, 0 sign flips among signalled
rows, 0 category changes.** The card's own row went +0.0305 ±0.0032 →
+0.0314 ±0.0033 and the loop partners sat still (Exquisite Blood +0.0292 →
+0.0291, Sanguine Bond +0.0255 → +0.0251, Vito +0.0252 → +0.0251). The table
was right for the wrong reason, which is the §0z23 result again — a rebuild
that moved nothing — and the reason it was run anyway is that "nothing" is
only known after the run. `results/karlov_conqueror.txt` and the rebuilt
`results/ablation_karlov.txt` are the evidence; the 2026-09-16 table is at
commit `dadc7f2`.

**The lesson, promoted to CLAUDE.md:** a generated file is only as current as
its last generation, so check the GENERATION — and when a check comes back
clean, ask which list it built from.

## 0z30. FIXED — one opening hand and one pod-phase order for six engines; the order was worth 0.065 to tivit

2026-09-17. M1 and M2 of the 2026-09-17 review, done as one shared-code
change because both move every baseline. Pinned by
`tests/test_mulligan_and_pod_order.py` (seven cases over every engine's
STAGED list, five mutations with exact sets).

**M1, the opening hand.** Six `opening_hand` methods, three behaviours when
the fourth hand also failed the 2–5-land keep rule:

| engine | what it did on the fourth failure | how often |
|---|---|---|
| `engine.py` | drew a FIFTH hand, bottomed three | — |
| `lorehold.py` | cleared the hand and never redrew: **a game with no cards** | 0.11% of games |
| karlov, tivit, shilgengar, azusa | neither cleared nor redrew: the seven cards in hand AND shuffled back into the library — **a 106-card deck** | 0.1–0.4% of games |

And only lorehold counted a modal double-faced card's land face for the
keep decision, while rendmaw (4 MDFCs), shilgengar (6) and tivit (2) did
not. All six now call `engine.london_mulligan`: draw seven, keep on 2–5
lands with MDFC backs counted, otherwise reshuffle and try again, **the
fourth hand is kept whatever it holds**, and `mulls` cards go to the bottom.
`g.rng` is still the only randomness and `seal_rng` still follows it.

**M2, the pod phase.** Six copies of the end-of-turn block. Four ran
`incidental_damage → resolve_clocks → opponents_act`; karlov and tivit ran
`opponents_act → incidental_damage → resolve_clocks`. Nobody chose that.
The consequence was not the one the review guessed at. The guess was that
removal landing before the clock's threat read would matter; the mechanism
that actually moved the numbers is that **`opponents_act` grows each
opponent's creature count (`+0.7 × board` a turn, capped at 7) and
`incidental_damage` reads that count**, so in karlov and tivit the
creatures grew and THEN hit, every turn, and in the other four they hit and
then grew. Two engines were being chipped by next turn's board. All six now
call `opponents.pod_phase`: damage, clocks, then — if you are still in the
game — removal, with an engine's own opponent model (karlov's
`opponent_activity`) passed as `before_act` so it keeps its place just
before the removal round.

**What it moved, measured at the tables' N and not argued**
(`diagnostics/run_shared_code_shift.py`, new for this: the same staged list
on the old and new CODE, N=15,000 paired on the tables' own seeds, written
to `results/shared_code_shift_0z30.txt`):

| deck | win rate, T10 | win rate, T20 | final_life, T20 | stranded_mv, T20 | seeds whose result changed, T20 |
|---|---|---|---|---|---|
| **tivit** | **+0.0154 ±0.0020** | **+0.0647 ±0.0044** | +3.05 | +7.96 | 1,201 of 15,000 |
| **karlov** | **+0.0094 ±0.0018** | **+0.0205 ±0.0040** | +2.67 | +2.37 | 908 |
| rendmaw | +0.0000 | +0.0015 ±0.0011 | −0.00 | +2.02 | 72 |
| shilgengar | +0.0003 | +0.0015 ±0.0019 | +0.10 | +6.00 | 215 |
| lorehold | +0.0000 | +0.0001 ±0.0003 | +0.00 | +0.03 | 3 |
| azusa | +0.0001 | +0.0001 ±0.0002 | +0.02 | −0.06 | 2 |

Tivit and karlov are M2: three to five points of life a game that the old
order took off them, and in tivit a fifth of all games at T20 ending
differently. Rendmaw and shilgengar are M1's MDFC rule: hands with a land
face are kept now, which is more kept hands and more stranded mana
(+2.0 and +6.0 a game) for a win-rate shift at the edge of the noise floor.
Lorehold and azusa are M1's fallback alone: a handful of seeds.

**A/A control still `+0.00` on all eighteen metrics** (corr 0.9106) — the
shared block draws nothing mid-game — and every pinned test passes.

**The tables.** Four decks moved and four were rebuilt from empty caches
with the change in: karlov, tivit (M2, necessarily) and rendmaw,
shilgengar (M1, whose baselines moved significantly on one metric each).
Lorehold and azusa are VERIFIED on the evidence above — 3 and 2 seeds of
15,000 changed result, win rate +0.0001 — which is the `check_unchanged_decks`
standard met at the tables' own N. The rebuilt tables against their
predecessors at `af016c1`, row by row:

| deck | rows moved beyond their old bar | sign flips among signalled rows | category changes | noise floor |
|---|---|---|---|---|
| karlov | 1 — Felidar Sovereign +0.0284 ±0.0028 → **+0.0355 ±0.0031** | 1 nominal: Toxic Deluge, win rate −0.0020 → +0.0009 (±0.0029, inside its bar both times; its signal is `dmg`) | 0 | ±0.0025 → ±0.0025 |
| tivit | 3 — Mirkwood Bats +0.0327 → **+0.0373 ±0.0036**; Mechanized Production +0.0179 → **+0.0227 ±0.0030**; Brago's Representative +0.0070 → **+0.0101 ±0.0028** (`FLIP` → `win`) | 0 | 0 | ±0.0027 → ±0.0029 |
| rendmaw | 0 | 0 | 0 | ±0.0019 → ±0.0019 |
| shilgengar | 0 | 1 nominal: Cartel Aristocrat +0.0001 → +0.0000 (±0.0012, a `FLIP` row that §0z24 says should read `--`) | 0 | ±0.0020 → ±0.0020 |

Every row that moved, moved UP, and each is a card that gets better when
the pod chips less life: Felidar Sovereign's 40-life win fires more often
with five more life a game; tivit's three are the deck's long-game payoffs
in a deck whose games now run 0.6 turns longer (turns_played +0.62 at T20)
and whose noise floor widened for the same reason. **The two M1-only
rebuilds moved nothing**, which is the §0z23 result once more and the
reason lorehold and azusa were not rebuilt on 3 and 2 seeds' evidence.

**What is still six copies.** `draw`, `deal_pod_damage`, `power_of`,
`on_creature_death` and the tail of `simulate()` — M5 of the review, the
base class. The two blocks unified here were the ones where the copies had
already changed numbers; the rest are the same shape waiting.

## 0z31. FIXED — the metrics dict cannot KeyError, and ablation.py no longer reads argv at import

2026-09-17. M3 and M4 of the review, both zero-behaviour refactors, verified
as such: `check_unchanged_decks` against a worktree at `9f226af` came back
BIT-IDENTICAL on all eight metrics for all six decks after M3, and every
committed table re-rendered BYTE-IDENTICAL from its committed cache through
the refactored renderer after M4. The A/A control is `+0.00` on all eighteen
metrics. Pinned by `tests/test_metrics_and_render.py` (two mutations, exact
sets).

**M3.** Each engine seeded `self.m` with a ~50-key literal and incremented
about 350 sites with `+=`; a site whose key was missing from the literal
raised `KeyError` in a worker, twenty minutes into an ablation, on the one
seed where the card fired. Four comments in `azusa.__init__` describe that
failure, and 35 sites in three files had grown a defensive
`m.get(k, 0) + 1` instead — the same operation spelt two ways (§0u's shape
in miniature). `engine.Metrics` is a `dict` whose `__missing__` returns 0
without inserting, every engine seeds its literal into one, every
`simulate()` returns one, and the 35 defensive spellings are `+=` again.
The literals stay: they are the documented metric set and the reason
`experiment.analyse` finds every `METRICS` key on both branches.

**M4.** `tools/ablation.py` read `DECK`, `N` and `HORIZONS` from `sys.argv`
at import and rebound them, with `SIM`, `SCRIPTED`, `PARTLY` and `METRICS`,
inside `_worker_init`. Three docs described working around it
(`experiment.repl_priority`'s docstring, `pending.check_measured…`'s, and
the test runner's), and it blocked testing the classification checker and
the table renderer. Now `parse_args` builds a frozen `Run(deck, n,
horizons, blank_keeps_types)` with `sim`/`metrics`/`scripted`/`cache`
properties; `main()` passes it down, workers receive the same object in
their initializer, and `render_table(run, results, nonlands, partly)` is a
pure function returning the table's text. The `CACHE` global and the second
copy of the SIM/SCRIPTED dicts are gone.

**What that bought, immediately.** The §0z4 rendering check — re-render the
committed table from the committed cache and diff — used to be a shell
one-liner run by hand when someone remembered. It is case C of the new test,
over every deck with a cache: **the table on disk IS the cache on disk, byte
for byte.** It fails when a cache is regenerated and the table is not, when a
classification moves a row between sections without a re-render, and when
the renderer changes what it prints; its mutation moves one rendmaw card to
KNOWN_BLIND and exactly rendmaw's row fails.

**The follow-up is closed (later on 2026-09-17).** `pending.py`'s
`check_cuts_are_measured` classifies every STAGED and PROPOSED cut with
`ablation.py`'s sets, in the deck's MODULE list — a staged cut has already
left the staged list, which is precisely why `check_scripted_coverage`
never saw one. A MODEL-BLIND or PARTLY MODELLED cut is refused unless the
Change or Candidate carries `cut_unmeasured`, the reason it is cut anyway;
a cut in no category is refused outright; a land cut passes with the note
that the harness flatters land cuts. Pinned by `tests/test_pending_cuts.py`
(four mutations, exact sets), printed by `python -m edhmc.pending`. Its
first run found two things:

- **The staged karlov cut is blind.** Soulmender is `KNOWN_BLIND` in karlov
  (its tap ability is not modelled), and §0z27 had called its row "the
  cheapest cut, checked rather than assumed" — a blind row read as
  evidence, the exact shape of §0z and §0z2. The head-to-head that stages
  `-Soulmender +Bloodthirsty Conqueror` compares the Conqueror with a
  vanilla 1/1, so its +0.0254 is a CEILING. The staging stands on an
  acknowledgement now written into the Change, and §0z27 says so.
- **Two staged lorehold cuts were in no category at all.** Penance and
  Scroll Rack were dropped from `SCRIPTED_LOREHOLD` when they were staged
  out on 2026-09-05, so the only lorehold cards with no classification were
  the two whose rows justified cuts. Both are implemented (the top-setter
  table prices them) and are back in `SCRIPTED_LOREHOLD`, where a name not
  in the measured list is a note by design.

One caller was found by the suite rather than by grep: `tests/test_combat_split.py`'s stub game built
`self.m = {}` and hit the first `+=` in `opponents.combat_damage` — the 35
defensive spellings had been carrying exactly that stub. It builds a
`Metrics()` now; a stub game's `m` must, and the suite says so.
And `pending.py` can now import
the classification sets, which its own docstring names as the open
follow-up: checking that a proposed cut is not MODEL-BLIND, the trap behind
two withdrawn swaps.

## 0z32. FIXED — a thin base class for the six engines, and one registry of decks

2026-09-17. M5 and M6 of the review, the structural pass. Both verified as
zero-behaviour the way §0z31 was: `check_unchanged_decks` against a worktree
at `774b8ef` BIT-IDENTICAL on all eight metrics for all six decks; every
committed table re-rendered BYTE-IDENTICAL from its committed cache; the A/A
control `+0.00` on all eighteen metrics; and, because M5 takes the UNION
where six copies differed, a stricter check as well — every numeric key of
`simulate()`'s output, summed over 400 staged-list games per deck, compared
old against new.

**M5, `engine.BaseGame`.** Structural fact 1 in ARCHITECTURE.md was "six
engines, no base class", and it was the reason §0u, §0z7, §0z8 and §0z30
happened: a rule that lives in a method has six copies. The copies of
`has` and `count` were byte-identical; `draw` was identical in four engines
and overridden in karlov (Alhammarret's Archive) with lorehold using its own
`draw_card`; `deal_pod_damage` differed by omission — azusa did not record
`drain_damage`, and karlov, shilgengar and azusa did not stamp
`turn_lethal` on a drain win; and the six `simulate()` tails assembled the
same eleven output keys in two different orders, with lorehold adding
`miracle_rate` and `tutor_log` and tivit `final_treasures` and
`final_artifacts`. `BaseGame` holds the first four and `opening_hand`;
`engine.finish(g)` is the tail, and each engine's `simulate` adds its own
keys after it. About 250 lines gone. **The union was measured, not
argued:** across every numeric output key the one difference is karlov's
`turn_lethal`, which a drain win now stamps at the drain (as engine.py and
tivit always did) instead of at the next `not living` check — 39,600 →
39,249 summed over 400 games, i.e. some games record the lethal turn where
they recorded 99. azusa's copy skipped `drain_damage` but azusa has no
pod-drain source, so nothing moved. No table reads either key.

Still per engine, and meant to be: `__init__`, `power_of`/`toughness_of`
(Angels, Urza's Construct, dynamic lands), `on_creature_death`,
`make_permanent`, `gain_life`, `take_turn`.

**M6, `edhmc/registry.py`.** A deck was registered in eleven places by hand
— `ablation.py`'s `SIMS` and `METRIC_SETS`, `cache_manifest.py`'s
`PER_DECK`, `check_unchanged_decks.py`, `run_shared_code_shift.py`,
`status.py`, `pending.py`'s `DECK_IDENTITY`, `candidates.py`'s sims,
`validate.py`'s CRN cases, and the tests' `ENGINES` maps. One `DeckSpec`
per deck now carries the engine, the colour identity, the table's metric
columns and the extra fingerprint files; the deck module comes from
`discover_current_decks()`, and the registry is checked against it at
import, so a module without a spec or a spec without a module refuses to
import (§0q, pointed at the registry itself). `cache_manifest.PER_DECK` is
DERIVED from it and was proved to spell every path exactly as it had been
typed, so no fingerprint moved for that reason. `validate.py` now refuses to
run with a deck missing from its CRN audit cases instead of skipping it
(§0z15). What is still hand-written per deck is a decision, not a fact:
`ablation.py`'s SCRIPTED/PARTLY/KNOWN_BLIND classification, `pending.py`'s
candidate catalog, `validate.py`'s one real swap per deck.

**Found on the way.** `check_architecture_names_modules` accepted the bare
word "registry" in the sentence "until a single registry exists" as naming
`edhmc/registry.py`. It matches the file name with its extension now, which
immediately found ten tools the map had named without one. A prose word is
not a module mention — §0z15's shape in the doc checker.

## 0z33. MEASURED — Anointed Procession on the post-§0z30 baseline, and the review's L2–L5

2026-09-17. §0z30 moved tivit's baseline by more than any other deck's
(+0.0647 win rate at T20), and the staging of `-Plains +Anointed
Procession` (§0z27) rested on numbers measured before it. A swap's number
is a difference on a baseline, so it was re-measured rather than kept
(`diagnostics/run_tivit_procession.py` → `results/tivit_procession.txt`,
N=15,000 paired, same seeds, the module list as the A leg):

| measurement | before §0z30 (§0z26/§0z27) | on the new baseline |
|---|---|---|
| candidate row, Plains slot, T20 | +0.0291 ±0.0034 | **+0.0325 ±0.0037** |
| real swap, T10 | +0.0113 ±0.0026 | **+0.0133 ±0.0027** |
| real swap, T20 | +0.0145 ±0.0040 | **+0.0157 ±0.0043** |
| baseline win rate, T10 / T20 | 0.1083 / 0.3265 | 0.1236 / 0.3915 |

Every number moved up and every move is inside its own bar. The mechanism
is unchanged — artifacts_made +13.7 and treasures_made +7.0 a game at T20 —
and the costs are the same shape (damage −0.94, cards_drawn −0.45: games
end by the token routes, not by combat). **The staging stands.** The one
thing the new baseline changes is the reading: the deck now wins 39% of
T20 games instead of 33%, so the same +0.016 is a smaller share of what
there is to win.

**Found on the way: a dead duplicate card.** `decks/tivit_v1.py` defined
`ANOINTED_PROCESSION` twice — a first version with a misremembered oracle
text (priority 8.5, threat 7.5) and the 2026-09-16 one (8.0, 3.0) that
rebound the name. Every measurement used the second; the first was dead
from the day it was written, the exact §0u shape the L1 sweep removed from
`lorehold_v16.py`. Deleted; the two trees' card objects compare equal and
the baseline check is bit-identical, so tivit's cache is VERIFIED rather
than rebuilt.

**The review's L2–L5, shipped with it.**

- **L2.** `tools/validate.py` and `tools/compare_decks.py` ran their whole
  body at import; both have a `main()` and a guard now, and behave
  identically when run. `compare_decks.py` and `fit_pod.py` are marked
  HISTORICAL in their docstrings: two and three decks, a metric from before
  the pod had a win condition, baselines typed in from 2026-09-04. They
  still run; they are provenance, not tools.
- **L3.** Already closed before this pass — `status.first_doc_line` strips
  the leading newline and no tool lists blank. Verified, not redone.
- **L4.** `tools/cache_manifest.py` carried ~700 lines of string constants
  describing how each cache was produced: documentation in code. They are
  data now, `results/caches/NOTES.json` beside `PROVENANCE.json`, keyed by
  cache file name, and `--note <cache|deck> "<text>"` appends to one the way
  `--verified` appends evidence. The file is 552 lines; the generated
  manifest is unchanged but for the sentence that says where the notes are.
- **L5.** Fifteen knobs exist only to reproduce a rule the project has since
  corrected. `tools/knobs.py` names them in `LEGACY` with what each
  restores, `docs/KNOBS.md` renders them under "Legacy switches" with the
  policy (kept while a committed number or a diagnostic cites the
  comparison; a removal candidate once every table that could see the
  difference is rebuilt), and the generator refuses to run if a `LEGACY`
  name is no longer read by any engine. The first render reported all
  fifteen as "swept" — because the generator's own registry named them and
  it was scanning itself. It excludes itself now; two have never been
  flipped by any run.

## 0z34. FIXED — the card-import procedure is a skill, and doc citations are checked

2026-09-17. Every step of adding a card had been learned the expensive way
and written down in a different place: the oracle-text rule in CLAUDE.md,
the hooks in `docs/ARCHITECTURE.md`, the three-category classification in
`tools/ablation.py`, the staging rule in `edhmc/pending.py`, the closing
checklist in its own skill. A session adding a card had to know all five
existed. **`.claude/skills/add-card/SKILL.md`** is the procedure end to end
— import, review, define, implement, pin, measure, stage, commit — with the
check that catches the mistake at the step where it is made, and it is
linked from CLAUDE.md, HANDOFF.md and `docs/ARCHITECTURE.md`.

It is a guide, not a catalogue of interactions. Its content is the mistakes
this project has actually made: text typed from memory (§0z26's two dead
proposals), a card already measured (§0z26 again), behaviour that attaches
by NAME rather than by `script=` (§0z25), a doubler said in one token path
of two (§0z4), a generated evasion file never regenerated (§0z29), a draw
inserted one indentation from its neighbour (§0z28), a mutation set written
after the run, a candidate row read as a swap (§0c), and a cut whose row was
never evidence (§0z31).

**Writing it added 22 §-pointers to a document, which is 22 more things that
can rot.** So `check_docs` gained `check_doc_sections_resolve`: every §id
cited from a LIVE doc must resolve to a heading, the way the code check has
always worked. It passes on **194 citations** across thirteen documents
today, with `docs/HISTORY.md` exempt as it is from the other doc checks (it
names the issues file with a bare sigil and no section number) — and the
exemption is written into the docstring, per §0z15. Its mutation cites an
id that no heading carries and must break exactly that check; ten mutations
now, all exact.

**The check caught its own write-up on the first run.** This section quoted
both unresolvable ids while describing them, and a quoted id is
indistinguishable from a cited one — which is the ambiguity that rots.
Naming them in words instead is the fix, and the fact that the check fired
on the document announcing it is the evidence that it fires.

**Two things the skill deliberately does NOT do.** It does not try to
enumerate card interactions — the engine is half-blind by construction (§4)
and a list of interactions would rot faster than the code. And it does not
replace the ledger: the skill says how to reach a `Change`, and
`python -m edhmc.pending` remains the only trustworthy statement of what is
pending.

## 0z35. MEASURED — queued items 21 and 22 answered: azusa's top two are EQUAL, and only one of karlov's three negative rows is an artefact

2026-09-20. Two queued items had the same shape — a table row being read as a
decision it cannot support — and both are now measured rather than argued.

### Item 21: a shared baseline cannot rank two cards, but one paired run can

Thirteen azusa cards sat in `MEASURED` with no cut named, two of them
0.0006 apart: Traveling Chocobo +0.0291 ±0.0040 and Nissa, Resurgent Animist
+0.0285 ±0.0041 (§0z21 called them a SET, not a ranking, which was correct).
The cut is the owner's choice: **Yavimaya Elder**, +0.0023 ±0.0023 — inside
its own bar — and MODEL-EVALUATED, so its row is evidence (§0z31).

`diagnostics/run_azusa_head2head.py`, N=15,000 paired, base
`build_pending("azusa")`, `results/azusa_head2head.txt`:

| run | win T10 | win T20 |
|---|---|---|
| −Yavimaya Elder +Traveling Chocobo | +0.0253 [+0.0223, +0.0283] | +0.0265 [+0.0223, +0.0306] |
| −Yavimaya Elder +Nissa, Resurgent Animist | +0.0280 [+0.0249, +0.0312] | +0.0266 [+0.0223, +0.0309] |
| Chocobo → Nissa in that slot | +0.0027 [−0.0005, +0.0060] | **+0.0001 [−0.0039, +0.0041]** |

**Run 3 is the one that settles it, and it is the measurement §0c says a
common baseline cannot give**: both legs play the same 99 other cards on the
same seeds, so the difference between the two candidates is PAIRED and their
CIs do not have to overlap-by-construction. It is the same measurement that
ranked Caldera Pyremaw over Galvanoth. The answer is that **the two cards are
measured equal** — the point estimate is 1/40th of the bar at T20 — so the
ranking question item 21 asked has a negative answer rather than a winner.

**They are equal while buying different things**, which is why neither
dominates:

| per game, Nissa − Chocobo at T20 | |
|---|---|
| `landfall_triggers` | +0.27 |
| `lands_played` | −0.19 |
| `cards_drawn` | −0.57 |
| `final_life` | −9.0 |
| `stranded_mv` | −6.5 |

Nissa converts mana into triggers (her Landfall reads the top of the library
for an Elf and the deck's mana is otherwise stranded); the Chocobo draws and
gains life off the same land drops. Both routes arrive at the same win rate
against this pod. **Either swap is worth taking and the deck can only take
one**, because the two share the Yavimaya slot.

**NOTHING IS STAGED, and the reason is compute rather than doubt.** Staging
changes `build_pending("azusa")`, which is the list every cached azusa number
was measured against — the third row of §0z27's table, the one that
**nothing but a rebuild can clear**. Staging the wrong one of two equal cards
costs a second rebuild. One question to the owner, one rebuild. Both
Candidates now carry these figures and this verdict in the ledger.

### Item 22: the diagnostic that decides this question did not reproduce the table

Item 22 asked whether karlov's three significantly-negative MODEL-EVALUATED
rows are cuts or §0j artefacts — all three carry an explicit `threat`, which
§0j says can be the whole score on a weak card. `diag_threat_blank.py` is the
tool for that question, and **it was measuring the wrong thing**.

`std_blank()`'s docstring said it was `ablation.py:blank_like()` "exactly".
It hardcoded `priority=0.5`. That WAS ablation's blank, until §0j moved it to
the deck's median nonland priority via `experiment.repl_priority()` — 7.0 for
karlov — and the diagnostic never followed. **This is §0z13 pointed at a
diagnostic**: a claim about another module's behaviour, true when written,
made false by a fix elsewhere, and nothing re-read it. The consequence was
specific: arm 1 was not the table's number, so the priority gap was being
attributed to the CARD. The `+priority` and `+body` arms set priority
explicitly and were never affected, which is why the text-alone endpoint
survived the defect — and why the old `results/threat_blank.txt` was
misleading rather than useless.

**Arm 1 is now a check on the other three, and it passes.** On all ten karlov
rows measured (N=15,000, same seeds as the committed table) the `standard`
arm reproduces the committed table to four decimals on win rate at both
horizons and on both damage columns. A decomposition whose first arm does not
reproduce the number it is decomposing is not evidence.

The case list also got the §0q treatment: it held the six cards that were the
bottom of the 2026-09-10 table, and by now four others had moved into that
region (the Conqueror staging rewrote five rows, §0z27; §0z30 moved the whole
baseline). It is ten cards now. Deriving it from the committed table is the
real fix and is NOT done — nothing parses a table back into names and values,
and writing a second row parser is §0u's shape.

### The answer: one artefact, two real, and the tie-break is mechanism

`results/threat_blank_karlov_2026-09-20.txt`, win rate at T20:

| card | standard (the table) | +threat | +priority | +body — TEXT ALONE |
|---|---|---|---|---|
| Blood Artist | −0.0036 ±0.0021 | −0.0015 ±0.0019 | +0.0013 ±0.0013 | **+0.0024 ±0.0011** |
| Mother of Runes | −0.0081 ±0.0025 | −0.0059 ±0.0024 | −0.0053 ±0.0021 | **−0.0053 ±0.0021** |
| Swiftfoot Boots | −0.0036 ±0.0022 | −0.0037 ±0.0022 | −0.0044 ±0.0020 | n/a (0/0) |

**Blood Artist is the artefact item 22 suspected, and it is a clean one.** Its
whole negative row is the two constants: give the blank Blood Artist's
`threat` of 7.0 and the row halves, cast it at the same point in the curve and
the sign flips, match the 0/1 body and the card is **significantly POSITIVE**
at both horizons (+0.0009 ±0.0005 at T10, +0.0024 ±0.0011 at T20). Its damage
goes the same way, −0.22 becoming +0.37. **It is not a cut candidate**, and
the table row says nothing about the card.

**Swiftfoot Boots and Mother of Runes are real.** Both stay significantly
negative through every arm, so the threat tax is at most a third of Mother of
Runes' row and none of the Boots'. That is the answer item 22 wanted, and it
is the answer the item did not expect: two of three survive.

**Which of the two is the cut is not a number question — their bars overlap**
(−0.0044 ±0.0020 against −0.0053 ±0.0021 at the text-alone endpoint, a
difference of 0.0009 inside either bar). §0c's rule applies to them as much as
to two candidates: these are two leave-one-out rows against a common baseline
and they cannot be ranked against each other. So the tie-break is MECHANISM,
and it is one-sided:

```python
cfg.setdefault("shroud_sources", ("Lightning Greaves", "Swiftfoot Boots",
                                  "Whispersilk Cloak", "Mother of Runes"))
cfg.setdefault("protection_cards", ("Mother of Runes",))
```

`shroud_sources` names four cards and **the staged karlov list contains two of
them** — Lightning Greaves and Whispersilk Cloak are both already staged OUT
(the 2026-09-04 3-for-3, whose own rationale reads "cutting it still leaves
Swiftfoot Boots and Mother of Runes as shroud sources for the commander").
And `protection_cards` is a one-element tuple holding Mother of Runes alone.

So **cutting Swiftfoot Boots leaves both modelled channels intact**: Mother of
Runes still shrouds the commander through `commander_shrouded()` and still
feeds `try_protect()`. **Cutting Mother of Runes closes `try_protect()`
entirely** — no card in the list would be in the deck, so the function returns
False forever — and takes `shroud_sources` to one. That is a bigger change to
the model than either row measures, and it is not what a −0.0053 row is
evidence for.

**SWIFTFOOT BOOTS IS THE ESTABLISHED CUT FOR KARLOV.** It is not staged,
because a cut is half a swap and karlov has no waiting add: its only unstaged
MEASURED card is Alhammarret's Archive, HELD on the owner's playtest evidence.
The next karlov candidate has its victim slot named and measured.

**Read the Boots' row for what it is.** Its `removal_eaten` is +0.02 in every
arm, including the arms where the blank carries the same threat — the card
costs two mana and a card to equip, and the pod's removal lands on the rest of
the board while it does. The engine models the Boots as shroud and nothing
else, which is faithful enough for a cut decision here precisely because the
alternative cut is the card that carries the SAME ability plus a second one.

**A by-product worth keeping: seven rows were decomposed that nobody asked
about**, and the four added by the §0q fix all behave the ordinary way — the
`+priority` arm moves them up by 0.0001–0.0032 and no sign flips. Vizkopa
Guildmage is the useful one: its DAMAGE is negative at both horizons while its
win rate is +0.0081 — the shape Felidar Sovereign and Exquisite Blood also
have in this deck, and all three are drain rather than board — and the
decomposition leaves both facts standing (+0.0103 ±0.0016 win, −0.61 damage at
the text-alone endpoint). It is a drain card and the drain does not read as
damage. Not an artefact, not a cut.

## 0z36. MEASURED — karlov's staged cut is the wrong one, and the MODEL-BLIND card was the card to keep

2026-09-20, `diagnostics/run_karlov_boots.py`, `results/karlov_boots.txt`.
§0z35 named Swiftfoot Boots as karlov's cut and left it unattached, because a
cut is half a swap. This is the other half, and it changes a staged decision.

Three paired runs, N=15,000, same seeds, base `build_pending("karlov")` so
Bolas's Citadel is IN on every leg exactly as it was for the staged
measurement:

| run | win T10 | win T20 |
|---|---|---|
| 1. both legs play the Conqueror; A cuts Soulmender, B cuts the Boots | +0.0028 ±0.0039 | **+0.0125 ±0.0049** |
| 2. `−Swiftfoot Boots +Bloodthirsty Conqueror`, pre-swap baseline | **+0.0299 ±0.0029** | **+0.0401 ±0.0037** |
| 3. `−Swiftfoot Boots +Alhammarret's Archive`, given the staging | **+0.0055 ±0.0016** | **+0.0168 ±0.0030** |

**The Conqueror is worth half again as much on the Boots as on Soulmender** —
+0.0401 ±0.0037 against the ledger's +0.0254 ±0.0035 — and the cut it would
use is MODEL-EVALUATED, so the swap stops being the ceiling §0z31 flagged.

**THE GAP IS MEASURED TWICE, INDEPENDENTLY, AND THAT IS WHY IT IS BELIEVABLE.**
Run 1 measures the difference between the two cuts directly, both legs playing
the Conqueror: +0.0125 ±0.0049 at T20. Subtracting the two swap values gives
+0.0147 at T20 and +0.0040 against run 1's +0.0028 at T10. Two separately-run
measurements of one quantity, agreeing inside a single bar. Run 1 is the
significant one only at T20; at T10 it is the same sign inside its bar, so the
*direction* is consistent at both horizons and the *size* is proved at one.

### Why the blind card was the one to keep

§0z31's cut check exists because a MODEL-BLIND row is not evidence, and the
standing suspicion is that a blind cut FLATTERS a swap — you cut a card the
engine cannot see, so you pay nothing for it. **Here it did the opposite.**
Soulmender's tap ability is unmodelled, but the card is still a one-mana white
BODY, and run 1 says what that body is worth: `lifegain_triggers` +0.34 and
damage +0.71 in the leg that keeps it. It attacks, it blocks, and it carries
this deck's lifelink grants.

**And the Boots' modelled value is nearly all redundant, which is §0z27
pointed at a cut instead of an addition.** `opponents.commander_shrouded()` is
a boolean OR over `shroud_sources`, and Mother of Runes is in the deck on BOTH
legs — so the Boots pay `{2}` and a card for a flag another card already sets.
That is the mechanism behind the negative row §0z35 decomposed, and it is the
reason the row is negative rather than merely small: the card is not weak, it
is duplicated.

So the lesson is not "blind cuts are safe" and not "blind cuts flatter". It is
that **a blind row tells you nothing in EITHER direction**, and the only way to
find out is to run the same card against a cut whose row is evidence. That run
costs one `run_ab` call.

**ONE NUMBER IS NOT EXPLAINED AND IS RECORDED AS UNEXPLAINED.** Run 1's
`removal_eaten` is −0.0087 ±0.0080: the leg WITHOUT a shroud source eats
slightly less removal, which is backwards on the face of it. It is a fifth the
size of the effects above and nothing in the decision rests on it. Do not
invent a mechanism for it — the two candidates (a permanent that is itself a
removal target, and shroud changing what `your_share()` aims at) are both
plausible and neither is measured.

### Alhammarret's Archive, priced against a cut instead of a blank

+0.0168 ±0.0030 at T20 — **LARGER than its own candidate row of +0.0129
±0.0024**, and the inversion is the point. A real swap is normally SMALLER
than the candidate row because it also pays for what it cut (§0c, and every
staged swap in the ledger). It is larger here because the cut is worth LESS
than a blank: removing the Boots adds value on its own. **When the cut is a
significantly-negative row, the swap is the candidate row PLUS the cut, not
minus it** — and that is the first case in this project where it happened.

**The owner's hold stands and this run does not reopen it.** The hold is
playtest evidence the model cannot see (a five-mana artifact that has to be
high-impact), and the model agrees about the cost where it can measure it:
`stranded_mv` +6.3 at T20, the largest in this batch. What the run buys is that
the card is now priced against a real cut rather than against a blank, which is
the number the hold never had.

### What is NOT staged, and the two reasons

**Nothing here is staged.** Re-staging the Conqueror onto the Boots rewrites
`build_pending("karlov")` — the third row of §0z27's table, the one **nothing
but a rebuild can clear** — so it costs a karlov rebuild, and that is the
owner's call and not a free consequence of a measurement.

**And the Boots are ONE SLOT that two cards now want.** Run 3 was measured
GIVEN the current staging (Conqueror in Soulmender's slot), so taking both
changes is a CHAIN of marginal measurements worth about +0.0422, not two
independent wins. Taking the Conqueror on the Boots instead leaves Soulmender
in the list and the Archive with no cut again. The three options are:

| option | what it does | worth |
|---|---|---|
| A, the live staging | `−Soulmender +Conqueror` | +0.0254 ±0.0035, a ceiling |
| B | `−Boots +Conqueror` | +0.0401 ±0.0037, MODEL-EVALUATED cut |
| C | A, then `−Boots +Archive` on top | ≈ +0.0422 as a chain, and the Archive is HELD |

Option C's total is a chain and not a factorial: the interaction has not been
measured, and §0p is the finding that says two staged changes in one deck can
interact. If both are ever staged, the 2x2 is the check.

## 0z37. FIXED — floating landfall mana was paid with and never consumed, and it was worth 0.02 win rate to azusa's baseline

Found 2026-09-21 while diagnosing an eleven-hour hang; fixed the same day.
**This is an engine defect, not a card, and it invalidated azusa's committed
table and both of the cards in the pending azusa decision.** Measured at the
tables' own N, it was worth **−0.0201 ±0.0036 win rate at T20** — the
second-largest baseline correction in this project after §0z30's pod order.

### The five-line proof

```
bonus_mana before      : 1 unit(s)
available_mana         : 1 unit(s)
  paid {G} #1: bonus_mana now 1, available_mana now 1
  paid {G} #2: bonus_mana now 1, available_mana now 1
  paid {G} #3: bonus_mana now 1, available_mana now 1
```

`engine.spend` taps the permanent that owns each unit it was told to pay with:

```python
for i in pay_idx:
    if i < len(owners) and owners[i] is not None:
        owners[i].tapped = True
    return
```

**A unit with no owner has no permanent to tap, and nothing else deducts it.**
In azusa those units are `bonus_mana`, the floating mana three landfall cards
make — **Lotus Cobra**, **Tireless Provisioner** and **Nissa, Resurgent
Animist**. It is cleared once per turn in `take_turn` and is otherwise
reusable without limit: one trigger pays for every spell cast that turn.

### It is §0u's shape, and the other two copies are right

The rule "a floating unit must be deducted, because there is nothing to tap"
is implemented three times in this repo:

| pool | where | deducted? |
|---|---|---|
| lorehold's Treasures | `lorehold.pay()`, by index arithmetic off `first_treasure` | **yes** |
| azusa's Castle Garenbrig `creature_mana` | `azusa.main_phase`, `del self.creature_mana[:from_castle]` | **yes** |
| azusa's `bonus_mana` (landfall mana) | nowhere | **NO** |

And the reason the third is the broken one is structural rather than careless:
the other two pools are appended **by the caller**, which therefore knows the
boundary between real and floating units and can do the arithmetic.
`bonus_mana` is appended **inside `available_mana` itself**, so by the time any
payment site sees the pool the floating units are indistinguishable from real
ones. A fix that adds the deduction at azusa's payment sites would be the same
mistake a fourth time; it belongs in one place.

### What the hang was

`diagnostics/run_azusa_slot.py` put Awaken the Woods in Yavimaya Elder's slot.
Two of four worker processes spun at 100% CPU for **eleven hours** on their
first job while the other two completed all 26 remaining jobs at a mean of
364s. Deterministic at **seed 6328**, reproduced in seconds.

With mana effectively free, `main_phase`'s greedy loop ran this cycle inside a
single turn:

1. cast Awaken the Woods, X=6 -> six Forest Dryad land creature tokens
2. six landfall triggers -> six floating mana that never leave the pool, and
   six Springheart Nantuko copies of Eternal Witness at `{1}{G}` each
3. each Witness copy's ETB returns a card from the graveyard, Awaken among them
4. recast it

**258 casts of Awaken the Woods in one turn**: 1,549 land tokens, 1,571
Springheart copies, 6,397 Insect tokens, a board of 29,632 permanents, and
`bonus_mana` climbing one unit per landfall and never falling. Every other part
of that cycle is faithful to the cards; only the mana is wrong, and it is what
makes the loop self-funding. At a real table the cycle is mana-NEGATIVE and a
pilot stops.

### What it invalidates

* **azusa's committed table.** Lotus Cobra and Tireless Provisioner are both in
  the list, so every row is measured with a turn's floating mana reusable.
* **Nissa, Resurgent Animist, whose ritual half IS this bug.** She is one of
  the two cards §0z35 measured as EQUAL for the Yavimaya slot (+0.0001
  [-0.0039, +0.0041]), and Traveling Chocobo — the other — doubles landfall
  triggers and therefore multiplies the same broken mana. **That tie is not
  trustworthy and the owner's choice is on hold until this is fixed.**
* **the 26 completed rows of `results/azusa_slot.txt`**, kept as provenance and
  marked, not read as results.

Karlov, lorehold, tivit, shilgengar and rendmaw are NOT affected: only
`engine.ManaUnits.append`/`__add__` and `azusa.available_mana` create ownerless
units, and lorehold deducts its own before calling `spend`. That claim is a grep
over five engines, not an argument, and the fix should carry a check that makes
it mechanical.

### The fix: an owner, not a deduction at the call site

```python
class FloatingMana:
    __slots__ = ("colours", "tapped")
```

`engine.spend` consumes a unit BY TAPPING ITS OWNER, so the smallest correct
fix is to give the mana an owner that is not a permanent but does have a
`tapped` flag. **No change to `spend`, and no change to any of azusa's payment
sites.** That matters: the two pools that were already right — lorehold's
Treasures and this engine's own Castle Garenbrig `creature_mana` — each deduct
by index arithmetic AT THEIR CALL SITE, and writing a third spelling of that
rule would have been §0u's shape for the fourth time. `available_mana` simply
does not offer a point already spent this turn, and `take_turn` clears the pool
as it always did.

`tests/test_floating_mana.py` pins it: five cases, three mutations, exact sets.
One mutation is the OPPOSITE failure — every payment consuming an extra point —
because a fix that over-consumes would pass every other case in the file.

### What it was worth, measured rather than argued

`diagnostics/run_shared_code_shift.py`, azusa, N=15,000 paired on the same
seeds, old code against new (`results/azusa_0z37_shift.txt`). Batch 2's changes
sat in the same diff and were separately proved bit-identical on every deck, so
all of this is §0z37:

| metric | T10 | T20 |
|---|---|---|
| **won** | **−0.0212 [−0.0240, −0.0184]** | **−0.0201 [−0.0236, −0.0165]** |
| damage | −2.13 | −1.68 |
| final_life | −10.95 | −18.62 |
| cards_drawn | −1.37 | −1.55 |
| stranded_mv | +8.60 | +13.99 |
| seeds whose result changed | 480 of 15,000 | 741 of 15,000 |

**Five per cent of seeds ended differently.** The deck spent 22% less mana per
game (216 → 170 at the 400-seat check), drew a card and a half fewer, and
stranded fourteen more mana value — which is what it looks like when a deck
stops being handed a turn's worth of free mana every landfall.

**EVERY AZUSA NUMBER MEASURED BEFORE 2026-09-21 IS ON THE WRONG ENGINE**, by
about two points of win rate on the baseline alone. `results/azusa_slot.txt`
keeps its banner, and every azusa row in the ledger's `MEASURED` list was
measured on the defect.

### The rebuilt table, and the cards that WERE the bug

The azusa cache was moved aside and rebuilt at N=15,000 (a moved simulation is
the one cache state no evidence check can clear — §0z27's first row). **9 of 58
rows moved beyond their own old bar and 5 changed signal label**, and the
movement lands exactly where the mechanism says it should:

| card | before | after |
|---|---|---|
| **Lotus Cobra** | +0.0168 ±0.0034 | **+0.0071 ±0.0031** |
| **Tireless Provisioner** | +0.0139 ±0.0035 | **+0.0060 ±0.0032** |
| Seer's Sundial | +0.0281 ±0.0038 | +0.0193 ±0.0037 |
| Horn of Greed | +0.0421 ±0.0040 | +0.0365 ±0.0039 |
| Tireless Tracker | +0.0303 ±0.0039 | +0.0251 ±0.0038 |

**The two cards whose text PRODUCED the floating mana lost about half their
measured worth**, which is the cleanest confirmation available that the fix
removed what it was aimed at rather than something else. The rest of the list
moved down by the amount a deck loses when its spare mana stops being free.

**The cut the pending azusa decision rests on survives**: Yavimaya Elder is
+0.0019 ±0.0023 against +0.0023 ±0.0023, still inside its own bar. Its label
moved `both` → `dmg`, which is a classification changing under §0z24's
unguarded sign and not a fact about the card.

### And a lesson about watching a run

**A JOB COUNT IS NOT PROGRESS.** `results/azusa_slot.txt` grew steadily to 26 of
28 while two workers were dead in a loop, and it looked slow rather than broken
for ten hours. What distinguished them was `ps -o etimes=,times=`: a healthy
worker's CPU time is a fraction of its elapsed time between jobs, a hung one's
CPU time EQUALS its elapsed time. That check costs one command and would have
saved ten hours of two cores.
## 0z38. FIXED — flashback did not exile, so one Past in Flames could cast the same spell six times

Found 2026-09-21 while implementing Stingcaster Mage, whose whole text is
"target instant or sorcery card in your graveyard gains flashback until end of
turn". Implementing it as `past_in_flames(cap=1)` — the same function, not a
second copy of the rule (§0u) — put a test on the shared path, and the test
found the shared path wrong.

### What the code did, against what its own docstring claimed

`past_in_flames` removed the card from the graveyard before resolving it, and
its docstring said "Exiled after resolution, as flashback demands, so each card
is used once". **`resolve_spell` then filed it straight back**, because its
closing branch is

```python
    else:
        g.graveyard.append(card)
```

which every non-permanent it resolves goes through. So the card was in the
graveyard again the moment it finished resolving.

**702.34a is explicit**, and it is in this repo:

> "If the flashback cost was paid, EXILE this card instead of putting it
> anywhere else any time it would leave the stack."

### The cost was not one card, it was the cap

`flashback_cap` is 6 and **the pool is recomputed per iteration** (§0z19, and
correctly so — resolving a spell can exile another out of the graveyard). A
card that returned to the yard was therefore affordable and highest-priority
*again* on the next pass. One Past in Flames could cast **the same spell up to
six times**, paying its cost each time, with `flashback_casts` counting six
honest-looking casts of one card.

Reproduced directly on a six-source board with three cheap spells in the yard:
before the fix, `cap=6` emptied a three-card yard **and left the cards in it**;
after, the yard empties and stays empty, and `flashback_exiled` counts each one.

**PAST IN FLAMES' MEASURED ROW WAS RESTATED, AND IT DID NOT MOVE.** It was
+0.0102 ±0.0038 at T20 with the defect live (2026-09-16, §0z26); re-running the
same `lorehold2` batch at the same N on the fixed engine gives **+0.0102
±0.0038** — the same number. Its MECHANISM counters did move, in the predicted
direction: damage +0.28 → +0.19 and mv_cheated +1.02 → +0.81, which is what
losing the repeat casts looks like. So the inflation was real and it was not
worth win rate; the row stands as measured. `results/candidates_lorehold2_0z38.txt`.

**That is worth reading carefully rather than as good news.** "The counters
moved and the objective did not" is the same shape as §0t and the top-setter
finding: a mechanism can change materially while win rate does not notice. It
does NOT mean the defect was harmless in general — it means this card's edge
did not depend on it. A card that leaned harder on repeat casts would have
moved.

### The fix, and why it is a function

```python
def exile_flashback(g, card):
    if card in g.graveyard:
        g.graveyard.remove(card)
        g.m["flashback_exiled"] += 1
```

Two reasons it is not a bare `if` inside the loop. The rule needs saying once,
where both callers reach it; and **a mutation check has to be able to switch it
off**, which an inline condition did not allow. `tests/test_fra_batch2.py`
pins it with case I (the card is exiled, not re-filed) and the mutation "the
flashback exile is removed" must break exactly C and I.

### And the lesson that cost the most time here

**TWO OF THAT FILE'S FIVE MUTATIONS WERE NEVER INSTALLED.** They set module
flags — `PROFT_GATE_OFF`, `LOREHOLD_NO_EXILE` — that no production code reads,
so they broke NOTHING and the run reported "broke nothing, expected {A}". Read
carelessly that looks like the checks not depending on the rules; read
correctly it means the mutation did not happen. The fix was in the engine rather
than the test: the Threshold count is now the named constant
`engine.PROFT_THRESHOLD` and the exile is now `lorehold.exile_flashback`, both
reachable from a test. **A mutation that cannot change behaviour is §0z15's
failure arrived at from the other direction — not a check with a blind spot, but
a check whose knife was never picked up.** When a mutation breaks nothing, the
first suspect is the mutation.

Three further expectations in that file were wrong for substantive reasons and
are kept in its docstring with the reasoning, per the standing rule that a set
edited to match the output is a transcript rather than a test.
## 0z24. FIXED — `FLIP` is assigned on an unguarded sign, and it overrides the label that says "unmeasured"

**Found 2026-09-16 during the six-deck regeneration**, from the only three
label changes in the rendmaw table. All three turned out to be the same
defect, and none of them was a fact about a card.

### The mechanism

`tools/ablation.py:1175-1179` classifies a row, then overrides it:

```python
sig = ("both" if d_sig and w_sig else
       "dmg" if d_sig else "win" if w_sig else "--")
if len(HORIZONS) > 1 and len({np.sign(results[n][h]["damage"][0])
                              for h in hz}) > 1:
    sig = "FLIP"
```

The first statement is significance-tested — `d_sig` and `w_sig` compare a
point estimate against its own CI half-width. **The override is not.** It reads
`np.sign()` of the raw damage point estimate at each horizon and fires whenever
the two disagree, however small either is. For a card whose damage is
statistically zero, that sign is a coin flip.

### The demonstration

Three rows changed label between two runs of the SAME code on the SAME seeds:

| card | what moved | label |
|---|---|---|
| Toxic Deluge | damage T10 `-0.00` -> `+0.00` | `FLIP` -> `both` |
| Culling Ritual | damage T20 `+0.09` -> `+0.09` | `win` -> `both` |
| Biotransference | damage T20 `+0.00` -> `-0.00` | `--` -> `FLIP` |

**Biotransference is the clean case.** Its win rate is IDENTICAL across the two
runs — `+0.0005 +-0.0010` both times — and its damage T20 displays as zero in
both. The only thing that changed is the sign of a number that rounds to
`0.00`, and the row's label changed with it.

### The survey

Across all 379 rows in the six committed tables, 22 carry `FLIP`:

- **9 of 22** have damage inside its own error bar at BOTH horizons, so the
  sign the override reads is noise for every one of them;
- **11 of 22** would be labelled `--` on their own merits.

**That last number is why this is OPEN rather than cosmetic.** `--` means "the
card is indistinguishable from a blank — not a weak card, an unmeasured one",
and the whole discipline of this project's tables is that an unmeasured row is
never read as a verdict. `FLIP` overrides that label with something that reads
as a *stronger* claim — the card's effect reverses with the horizon — on
exactly the rows with the least evidence behind them.

**INSTABILITY IS HOW THIS WAS NOTICED, NOT WHAT IS WRONG WITH IT** (added
2026-09-16, from the tivit leg of the same run). All five of tivit's FLIP rows
held their label across the regeneration, **including Propaganda, which is one
of the nine rows above whose damage is inside its own bar at both horizons**. A
noise-FLIP therefore does not necessarily move between runs; rendmaw happened
to show three that did.

The defect is that the label is UNSUPPORTED on those rows, not that it changes
run to run. A row whose damage is statistically zero is handed a claim that its
effect reverses with the horizon whether or not the sign happens to flip on the
next regeneration, and there is no evidence behind that claim either way. The
fix is unchanged: gate the override on significance.

### What `FLIP` gets right, and must keep doing

The other half of the rows are real and are what the signal exists for. Damn,
Wrath of God, Promise of Loyalty and Mechanized Production all have damage
significant at BOTH horizons with opposite signs — a board wipe costs damage
early and pays it back late, which is a genuine horizon-dependent effect and
worth its own label. **The fix is to gate the override, not to remove it.**

### And it is in no legend

`FLIP` appears in neither the legend `ablation.py` prints at the top of every
table (which defines four signals: `both`, `dmg`, `win`, `--`) nor `CLAUDE.md`'s
reporting rule, which names the same four. `tools/status.py:56` knows it exists
and `docs/HISTORY.md` explains it, but the legend a reader actually sees does
not. 22 rows across six tables print a signal their own table never defines.

### Not fixed here

Gating the override on significance is a change to `tools/ablation.py`, which
is in `cache_manifest.SHARED` and therefore in all six decks' source
fingerprints. Making it during the regeneration that produced this finding
would have marked every cache that run produced stale on arrival. Sequencing,
not doubt: the fix is a one-line condition plus the legend, and the row it
changes is a LABEL, not a measurement — no committed number moves.


### FIXED 2026-09-25

**The override is now gated exactly as specified above**: `tools/ablation.py`
has `flips(res, hz)` -- damage SIGNIFICANT at every horizon AND the signs
disagree -- and `signal(res, hz)`, which only lets FLIP override the
significance-based label when `flips` is true. Both are functions rather than
an inline condition so a mutation can switch the rule off alone (§0z38).
**`FLIP` is in the legend** every table prints, and in CLAUDE.md's reporting
rule, so no row prints a signal its own table fails to define.

**All six committed tables were re-rendered from their caches and diffed.**
**0 rows changed any number in any column** -- a pure relabel, as predicted.
FLIP rows went **20 → 4**: ten to `--`, five to `win`, one to `both`.

**Four real flips survive**, each significant at both horizons with opposite
signs: The Great Henge (rendmaw), Damn and Wrath of God (shilgengar), and
Mechanized Production (tivit).

**One named "real flip" no longer is, and the gate is right about it.** This
section listed Promise of Loyalty with Damn, Wrath and Mechanized Production.
On the CURRENT tables Promise of Loyalty, tivit's Damn and Farewell all show
damage significant at T10 only (tivit's Damn: −1.46 ±0.18, then +0.08 ±0.22):
a cost that FADES rather than one that REVERSES. That is not a horizon flip
by this section's own criterion, so they now read `win`. Damn keeps FLIP in
shilgengar and loses it in tivit -- the same card, two decks, two different
effects, each measured in its own list.

**It was caught live before it was fixed.** On 2026-09-22 a comparison script
counted Sylvan Library (−0.0007 ±0.0018 → +0.0001 ±0.0019, a blank twice) as a
sign flip between significant rows, because it trusted this column. It now
reads `--`.

`tests/test_flip_signal.py` pins the rule with six synthetic rows -- including
the fading-cost case and the noise case -- and three mutations, exact sets,
written before the run: removing the gate breaks C, D and F; gating on ANY
significant horizon breaks C alone; removing FLIP breaks A. `ablation.py` is in
every deck's fingerprint, so all six caches moved and the rendering-only
evidence is recorded on each; karlov and tivit remain stale for the separate
reason in §0z44.

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


## 0z39. MEASURED — the monarch, built before a card asks for it, and it is worth a tenth of a win rate

Asked for by the owner on 2026-09-22 as a common mechanic. `docs/TRIAGE.md`
had recorded it as the blocker behind Ginger, Queen of Sweets, and the verdict
moved from BLIND to DEFERRED on the grounds that the machinery is wanted for
its own sake rather than to justify one card.

### The modelling decision, which is the whole of it

"A creature deals combat damage to you" has no object-level answer here.
`Opponent.creatures` is a `float` (§4) — there is no creature to connect and
no combat step in which it could. So the crown is lost **on the path that
already models their creatures getting through**: inside
`opponents.incidental_damage`, off the same threat-weighted `share` that
decides how much of their swing is aimed at you. Three options were put up and
this was chosen (option 2 of three) over a standalone per-turn probability,
because a second model of the pod's offence is §0u's shape — the same rule,
implemented twice, implemented two different ways.

`monarch_loss_scale` defaults to `incidental_rate` **itself** rather than to a
new constant, because that knob already means "how much of a swing lands".
Per living opponent with creatures, `P(lose) = min(1, share × scale)`; you keep
the crown only if none of them connects.

### What it is worth, and why that is a warning rather than good news

`monarch_start=True` against `False`, same seeds, N=400, T20 — a mechanism
smoke test (TRIAGE tier 2), not a card:

| deck | won | cards drawn | crown held |
|---|---|---|---|
| karlov | 0.3425 → 0.4450 (**+0.1025**) | 15.65 → 18.83 (+3.18) | 3.57 end steps, lost 1.00× |
| rendmaw | 0.1800 → 0.3025 (**+0.1225**) | 15.21 → 19.12 (+3.91) | 3.54 end steps, lost 1.00× |

**That is roughly 0.03 win rate per extra card, which is far above anything
this project measures for a real card,** and it is the number to distrust
rather than to celebrate. Two reasons, both structural:

1. **THE MODEL PAYS YOU AND CHARGES YOU NOTHING.** You draw while you hold the
   crown; when it passes, the opponent who took it draws *in reality* and draws
   nothing here, because the pod has no hand and no card draw at all. Every
   monarch number this engine produces is therefore a **CEILING**, and by an
   amount the engine cannot see.
2. **`monarch_loss_scale` decides the entire value and HAS NOT BEEN SWEPT.**
   The crown is held ~3.5 end steps at the default and is never regained,
   since nothing re-grants it. Halve the scale and the card doubles.

`monarch_start` is not a card. It hands you the crown on turn one for free,
which no real card does, so the table above is the mechanism's ceiling on top
of the model's.

### Zero movement, proved rather than argued

This is a shared-code change — `engine.py` and `opponents.py` are in every
deck's fingerprint — so all six fingerprints moved. No deck's numbers did:

  * `check_unchanged_decks`: **BIT-IDENTICAL on all 8 metrics, 0 of 6 decks
    moved.**
  * and §0z32's wider check, because the eight metrics are not all the numbers
    the engine records: **every numeric output key identical on all six decks**
    — 87 azusa, 106 lorehold, 67 tivit, 60 karlov, 54 rendmaw, 51 shilgengar.
  * `tools.validate`: `+0.00` on all eighteen metrics, corr 0.9101, unchanged.

The reason is structural rather than lucky. Nothing grants the crown, so
`g.monarch` is False in every measured game and the roll is **never consumed** —
`tests/test_monarch.py` case H asserts exactly that, and it is the case that
makes "this moves no deck" checkable instead of arguable. `crn_random` is
index-addressed per name (§0z17), so even once a card does grant it, the new
stream cannot shift an old one.

### Why the read side was built first

§0z12 — a tag nothing reads is not inert, it is a loaded gun. Five `wipe` tags
sat dormant and looked harmless, and wiring the branch up made two of them
instantly WRONG. The monarch is that shape in advance: the mechanism is built
and pinned with ten cases and four mutation sets *before* a card depends on it,
so the first monarch card arrives at a tested mechanism instead of making one
live. The one thing with no mutation behind it is written down in the test's own
docstring (§0z15): case E's `first_attack_turn` guard is shared with the damage
path and cannot be switched off without reimplementing that function.

### THE +0.10 WAS THE HARNESS, NOT THE CROWN (owner's challenge, 2026-09-22)

The owner's objection: the pod's attack share is weighted on an existing
value, and at a real table **anyone who can profitably swing at the monarch
does**, because the crown is worth too much to pass up — so the model should
be charging the monarch far more damage than it does, and that should
counterbalance the cards. Chasing it produced three results, and the third is
the one that matters.

**FIRST, TWO CORRECTIONS TO THIS SECTION'S OWN CLAIMS.** The text above named
`your_share` as the attack weighting. It is not: `DEFAULT_CFG` sets
`combat_targeting="open"`, so the attack path uses **`combat_share`**, weighted
by how OPEN each player is (`1/(1+blockers)`) rather than by threat — §0v
already established that threat-weighting combat was backwards. And
`incidental_rate` is **1.0** in `DEFAULT_CFG`, not the 0.45 fallback written at
the `cfg.get`, so `monarch_loss_scale`'s default is 1.0 and the crown passes in
about one turn once the pod can attack.

**SECOND, THE OBJECTION IS RIGHT, BUT FOR A DEVELOPED BOARD.** `combat_share`
at `creatures=4` each: **0.714 on an empty board, 0.385 at three creatures,
0.238 at seven.** A wide board DETERS the pod, which is right for ordinary
combat and wrong for the monarch, where the crown is the prize. So
`monarch_attack_floor` (0.75) is a **floor, not a multiplier** — a multiplier
scales the very deterrence being overridden — and it barely moves an empty
board while roughly tripling a developed one.

**AND IT DOES NOT COUNTERBALANCE.** Swept at N=500, `monarch_start`:

| floor | karlov won | rendmaw won | crown held |
|---|---|---|---|
| 0.00 (as first built) | +0.1040 | +0.1200 | 3.54 |
| 0.50 | +0.1000 | +0.1140 | 3.13 |
| 0.75 | +0.1040 | +0.1100 | 3.02 |
| 1.00 | +0.1020 | +0.1020 | 3.01 |

Tripling the share costs about **0.002 win rate**. What it actually does is
shorten the reign (3.54 → 3.01 turns) and remove about half a card. **The
counterweight cannot work in this model**: the crown's cost is chip damage, and
chip damage over a three-turn reign is worth a point or two of life against
three cards.

**THIRD, AND THIS IS THE REAL OVERSTATEMENT.** Losing 0.56 cards cost only
0.002 win rate, which cannot be reconciled with 3.3 cards being worth 0.104 —
so the value is NOT linear in cards, and the non-linearity names its own cause.
`monarch_start` grants the crown on **turn 1**, and `first_attack_turn` is
**3**: turns 1 and 2 are free, because nobody can attack yet. **Two of the
three held turns were immunity no real card can buy.** Granting it at a turn a
card could actually arrive (`monarch_start_turn`), floor 0.75, N=500:

| granted | karlov | rendmaw |
|---|---|---|
| turn 1 | **+0.1040** | **+0.1100** |
| turn 3 | +0.0240 | +0.0400 |
| turn 5 | +0.0220 | +0.0220 |
| turn 7 | +0.0400 | +0.0040 |
| turn 9 | +0.0460 | +0.0040 |

**A monarch card that arrives on turn 3-5 is worth roughly +0.02 to +0.04, not
+0.10** — three to five times smaller, and squarely in the range this project
measures for a good card. The crown is held ~1 turn once the pod can attack,
against ~3 when granted into the immune window.

**READ THE SECOND TABLE FOR ITS SHAPE, NOT ITS ROWS.** These are UNPAIRED runs
at N=500; the spread across turns 3/5/7/9 is inside the noise and karlov's
turn-7/9 figures reading above turn 5 should not be taken as "later is better".
What is far outside the noise is turn 1 against everything after it.

### What is owed before a monarch card ships

1. ~~**Sweep `monarch_loss_scale`.**~~ DONE above, along with
   `monarch_attack_floor`: win rate is INSENSITIVE to both, which is the more
   useful result and the one nobody would have believed unmeasured. What the
   value actually turns on is WHEN the crown arrives.
1b. **Measure the real card paired, not `monarch_start_turn` unpaired.** The
   +0.02 to +0.04 above is a point estimate at N=500; a card gets a `run_ab`
   against a named cut like anything else.
2. **Decide whether the pod's crown is worth modelling** — the ceiling in the
   table above is the opponents drawing cards, which is §4 again.
3. Ginger, Queen of Sweets still needs its oracle text verified on release
   (Reality Fracture, 2026-10-02); nothing in this section depends on that card.

## 0z40. MEASURED — Ginger, Queen of Sweets: a six-drop first, a monarch card second

The first card in this project that uses the monarch, imported on 2026-09-22
against the mechanism §0z39 had already built and pinned. Preview text
(Scryfall, set `frc`, releases 2026-10-02), so every number here is provisional
on the text not changing.

### Why karlov, when the colour identity is empty

Ginger is colourless and legal in all six lists, so the deck was a choice. It
is NOT in tivit, which is the stronger raw fit and is the reason: a Gingerbrute
is a **Food**, so in tivit it would trigger Academy Manufactor, be doubled by
the staged Anointed Procession and feed Time Sieve (§0m) — three interactions
at once, and §0z27 is the finding that redundancy rewrites every row around it.
The number would have been larger and unattributable. In karlov it decomposes
into things the engine counts separately: the crown's card, 1/1 haste bodies
(§0v made width worth something), and a lifegain EVENT per sacrifice.

### The numbers

Real swap `-Swiftfoot Boots +Ginger`, N=15,000 paired, same seeds, base =
`build_pending("karlov")`:

| | T10 | T20 |
|---|---|---|
| **win rate** | **+0.0052 ±0.0017** | **+0.0186 ±0.0033** |
| damage | +1.51 | +1.48 |
| lifegain_triggers | +0.70 | +0.67 |
| stranded_mv | +7.35 | +7.13 |

Candidate row against a blank in the same slot: +0.0059 ±0.0027.

**AND THE RANKING, which §0c says a common baseline cannot give.** Bloodthirsty
Conqueror → Ginger in that one slot, paired on the same seeds, built the way
§0z36 built the Conqueror's own +0.0401 (Soulmender restored to get the
pre-swap list): **−0.0247 ±0.0029 at T10 and −0.0210 ±0.0034 at T20**,
significant at both and the same size both times. That is consistent with the
two standalone figures (+0.0401 against ~+0.019) without relying on
subtracting them. **The Boots are one slot and the Conqueror wants it more.**

### The mechanism, which is where the card actually is

P(Ginger resolves) is **0.152** — one game in six, the Bolas's Citadel shape
(14.4%) — and `stranded_mv` +7.1 is what a `{6}` costs a list that curves
lower. Conditional on resolving: **2.96 Gingerbrutes, 1.03 monarch turns, 1.03
monarch draws.**

**The crown is held ONE turn, which is §0z39's prediction arriving on a real
card.** `first_attack_turn` is 3, so a card cast around turn 6 gets none of the
free early window that made `monarch_start` measure +0.10. The tokens are the
bigger half of this card, not the crown.

### The sacrifice clause fires ZERO times, and it is correct

`gingerbrute_sacs` is **0.0000** — not near zero, zero. The ability is
implemented and the implementation is right: a Gingerbrute has **haste**, so
`karlov.combat` attacks with it the turn it arrives and sets `tapped = True`,
and a tapped token cannot pay the `{T}` in its own sacrifice cost. The rules
agree.

**But read what decided it.** The engine attacks with everything it has, and
that POLICY is what makes the card's second channel worth nothing — the same
shape as all four rows in CLAUDE.md's policy table, where a piloting decision
written as conservatism amounted to asserting a card does nothing. Here the
policy is aggression rather than conservatism and the effect is identical. A
pilot who held one Gingerbrute back would convert it to a lifegain event in a
deck whose payoffs count events. `gingerbrute_keep` therefore does nothing at
any setting and was NOT swept, because there is nothing for it to decide.

### What the row is bounded by, in both directions

**FLOOR** — two clauses unmodelled. The Gingerbrute's `{1}: can't be blocked
except by creatures with haste` is blind (§4: the opponents' blockers are an
abstract count with no haste to check), so an evasive attacker scores as a
ground one. Ginger's own `{2}, {T}, Sacrifice: gain 6 life` is a deliberate
policy omission — a pilot who sacrifices her ends the engine and the crown that
feeds it.

**CEILING** — the pod's three upkeeps are taken before `pod_phase` can take the
crown, because an opponent's upkeep is not a real step in this engine (§0z30).
At a table the crown passes partway through the round and the opponents who act
after that make no token. Generous by at most two tokens in the one round the
crown changes hands.

Neither bound is tight, and the card is not staged.

## 0z41. FIXED — Horn of Greed was doubled by Ancient Greenwarden and Traveling Chocobo

Found 2026-09-22 while attributing azusa's decking losses (§0z42), which is
the only reason anyone looked: the fatal draws traced to `_landfall_payoffs`,
and Horn of Greed's draw was inside it.

### The defect

`azusa.land_entered` runs `_landfall_payoffs` once per REP, and the reps are
`1 + count(Ancient Greenwarden) + count(Traveling Chocobo)` -- correctly, for
landfall. But Horn of Greed's draw sat inside the payoffs too, so with both
doublers out one land drop drew THREE cards. Horn is not a landfall card:
"Whenever a player PLAYS a land" triggers on the special action, not on the
land entering. Scryfall's ruling on Ancient Greenwarden (2020-09-25) says so
in as many words:

> An ability that triggers whenever you play a land won't trigger an
> additional time.

Traveling Chocobo's clause is the same sentence ("a land or Bird you control
entering causes a triggered ability ... to trigger"), so the same holds.

### The fix, and what it was worth

The draw moved out of the doubled loop into `land_entered`, once per PLAY.
`horn_doubled_legacy=True` restores the old placement exactly, so the
correction is measured on the same seeds (`diagnostics/run_shared_code_shift`
with `--cfg`, the staged list, N=15,000 paired, decking_loss off both legs):

| azusa | win rate | cards_drawn | seeds whose result changed |
|---|---|---|---|
| T10 | **−0.0049** [−0.0065, −0.0034] | −0.60 | 136 of 15,000 |
| T20 | **−0.0033** [−0.0050, −0.0015] | −0.88 | 185 of 15,000 |

Lorehold, which has no Horn, is 0 of 15,000 at both horizons.

### Who it flattered

**Both doublers.** A Greenwarden or a Chocobo in play turned every Horn
trigger into two or three draws, in a deck whose measured constraint is
CARDS (§0z4, §0z21). The Chocobo's staged swap was measured with this in
(`cards_drawn` +1.07 at T20), so it was re-measured on the fixed engine
before the staging was allowed to stand -- `results/azusa_head2head_0z41.txt`.
Greenwarden's committed row carries the same inflation and is restated only
by the azusa rebuild.

**AND IT UNDID A RANKING THAT WAS ONE DAY OLD.** Re-measured on the fixed
engine, same N, seeds and base: the Chocobo swap is **+0.0173 [+0.0145,
+0.0201] at T10 and +0.0222 [+0.0181, +0.0263] at T20** (was +0.0213 /
+0.0257) -- still significant, but ~40% of its extra cards were the Horn
(`cards_drawn` +0.62, was +1.07). Nissa, Resurgent Animist's swap barely moved
(+0.0155 / +0.0195). And the direct comparison §0z37 had made significant --
Chocobo → Nissa in one slot, −0.0056 at both horizons -- is now **−0.0017
[−0.0046, +0.0013] and −0.0027 [−0.0069, +0.0013], inside the bar at both.**
§0z37 broke a tie that a defect had made; this breaks the tie §0z37 made, with
a second defect. The two cards are MEASURED EQUAL again, and the Chocobo is
staged on the owner's instruction rather than on a measured edge.

**That is the same lesson twice in two days, and it is worth saying once in
the general form:** a head-to-head between two cards is exact about the
harness it ran on, and each card's number carries every defect on the hooks
it touches. When a fix lands on a hook one of two ranked cards uses, the
ranking is stale even if its own bar was tight.

The lesson is §0z28's shape one hook over: **a hook that runs N times for one
kind of trigger will run N times for anything placed inside it.** When a
payoff is added to a multiplied loop, check the card's trigger EVENT against
the multiplier's rulings, not just its word "land".

## 0z42. FIXED — decking loses (queued item 17), and the pilot had to learn not to do it

Queued item 17, closed 2026-09-22. 704.5b: "If a player attempted to draw a
card from a library with no cards in it since the last time state-based
actions were checked, that player loses the game." Until this change every
`draw` in six engines stopped silently at an empty library.

### The rule, in one place

`engine.drew_from_empty(g)` is the whole rule, called by the three draw paths
the engines have: `BaseGame.draw`, karlov's Alhammarret's Archive override
("draw two instead" is two draws, and the second can lose), and lorehold's
`draw_card`. It records `loss_route` 3 and counts `drew_from_empty`. Anything
that pops the library WITHOUT drawing -- exile, mill, reveal, "put it into
your hand", a Citadel cast off the top -- does not call it, because 704.5b is
about drawing.

**One case it gets wrong, on purpose.** The rule is an SBA, and a resolution
that decks you AND kills the last opponent is a DRAW at a table (104.4a).
Here the first result recorded wins, so it is a loss. It needs an empty
library and a lethal inside one resolution; it is written down in the
docstring and in `docs/COMP_RULES.md` rather than modelled.

### The rule alone was a POLICY bug waiting to happen

Measured before any guard, N=1,500 per horizon, staged lists: **azusa decked
in 3.3% of games at T20 and lorehold in 1.6%; the other four never did.** And
the decked games were the ones they were WINNING. Azusa's had drawn 68 cards
against 20 and held a board with six-figure power, dying on turn ~10 in the
main phase before its own combat; lorehold's had cast 54 spells against 19 in
a chain. A pilot does not draw its last card on the turn it has lethal on
board. Asserting that it does is the shape of every row in CLAUDE.md's policy
table: a piloting decision written as conservatism that says a card kills you.

So the pilot learned the rule. `engine.draw_is_safe(g, n)` is one predicate --
would this draw leave fewer than `decking_reserve` cards? -- and it is asked
**only where the card text gives a choice**:

| deck | site | why it is a choice |
|---|---|---|
| azusa | Seer's Sundial | "you may pay {2}" |
| azusa | Tireless Tracker's Clues, Cryptic Caves, War Room | activations |
| azusa | Return of the Wildspeaker | modal: pump when the draw would deck |
| azusa | Momentous Fall, draw3 spells | casting is optional (`draws_on_resolve`) |
| azusa | a land drop with Horn of Greed out | the land drop is optional; Horn is not |
| lorehold | the commander's upkeep rummage | "you may discard. If you do, draw" |
| lorehold | Monument to Endurance | modal: another mode is taken |
| lorehold | main phase, miracle, Sunbird, Invoke Calamity, Bombardment and Mastery copies | "you may cast" (`pilot_may_cast`, `SPELL_DRAWS`) |

A MANDATORY draw -- the draw step, Horn of Greed's trigger, Double Vision's
copy, a spell already on the stack -- is never guarded. After the guards the
only decking losses left are the draw step and one Double Vision copy.

Found on the way and fixed separately: Horn of Greed was TRIPLED (§0z41).

### What it was worth

N=15,000 paired, staged lists, same seeds (`run_shared_code_shift --cfg`):

| win rate | no rule (Horn fixed) | rule, NAIVE pilot | rule + guard, reserve 1 | rule + guard, reserve 5 (shipped) |
|---|---|---|---|---|
| azusa T10 | 0.1742 | −0.0074 [−0.0088, −0.0060] | −0.0018 [−0.0025, −0.0011] | **−0.0006** [−0.0010, −0.0002] |
| azusa T20 | 0.3997 | **−0.0223** [−0.0246, −0.0199] | −0.0047 [−0.0058, −0.0035] | **−0.0012** [−0.0019, −0.0005] |
| lorehold T10 | 0.0498 | −0.0005 [−0.0008, −0.0001] | −0.0002 [−0.0004, +0.0000] | **−0.0003** [−0.0006, −0.0000] |
| lorehold T20 | 0.2093 | −0.0073 [−0.0087, −0.0060] | −0.0035 [−0.0045, −0.0025] | **−0.0021** [−0.0030, −0.0011] |

**The naive reading of item 17 would have cost azusa 0.022 at T20** -- a
Chocobo-sized swap, charged for a piloting error. The guard at the shipped
reserve recovers ~95% of it; what remains, −0.0012, is the genuine cost of the
rule: draw-step decking in a game the deck could not close in time. Lorehold
keeps a larger residue (−0.0021) because more of its draws are mandatory --
the draw step and Double Vision's copy in a deck built to chain. Together with
§0z41 the azusa baseline moved **−0.0055 / −0.0045** and lorehold's
**−0.0003 / −0.0021**; both tables are rebuilt.

**Four decks did not move at all.** Rendmaw, karlov, tivit and shilgengar are
IDENTICAL GAME FOR GAME on every metric at N=15,000 at both horizons, staged
lists -- including karlov with Bolas's Citadel in, which was the card item 17
was written about. The Citadel's +0.0163 was called a ceiling for this reason
and is not one: the dig stops at an unplayable land or at the life floor long
before the library runs out.

### The knobs, said out loud

`decking_loss` (default True) is the rule; False restores the old code and
is BIT-IDENTICAL to the pre-change commit on all six decks with
`horn_doubled_legacy=True` (check_unchanged_decks, 400 seeds, T20).
`decking_pilot` (default True) is the caution; False is the naive pilot.
`decking_reserve` (default 1) is how many cards the pilot keeps back:

| reserve, vs 1 (T20) | 0 | 1 | 3 | 5 | 8 |
|---|---|---|---|---|---|
| azusa | −0.0029 | 0 | +0.0022 | **+0.0035** | +0.0039 |
| lorehold | −0.0020 | 0 | +0.0013 | **+0.0015** | +0.0010 |

Every nonzero cell is significant (N=15,000 paired; bars ±0.0007-0.0010).
**IT WAS 1 AND IS NOW 5**, and the knob is load-bearing: "enough for the
next draw step" is too few, because the draws that come AFTER a declined
optional one -- Horn of Greed, the draw step, a mandatory copy -- are not the
pilot's to decline. 5 is on the plateau in both decks and the best or tied
at every horizon. T10 is the same shape, smaller. Said out loud because it is
a judgement: a real pilot's buffer depends on what is on the board, and this
is one number for all of it.

`tests/test_decking.py` pins the rule, the pilot's arithmetic and the Horn
fix; `--mutate` runs five mutations, exact sets, and one of them was wrong on
the first run in the way that mutation lists usually are (it changed two
rules and reported on one).

### The rebuild, and what it moved (2026-09-22)

This change moves two baselines -- lorehold and azusa, the two decks whose
pilots now hold a decking reserve -- and azusa's staged list also changed
when Traveling Chocobo was staged in Yavimaya Elder's slot. **A staging-induced
SUSPECT cannot be cleared with `--verified`**, so both tables were rebuilt at
N=15,000 rather than certified. The first rebuild was killed by a container
restart after both caches had been deleted; the second ran 125 minutes. Every
row was then compared with the table it replaced:

| | rows | beyond its own old bar | sign flips | category changes |
|---|---|---|---|---|
| lorehold | 65 | **0** | 0 | 0 |
| azusa | 58 (57 in common) | **3** | 0 | 0 |

**Lorehold did not move**, which is what the reserve sweep above predicted for
a net cost of −0.0003/−0.0021. Two cards crossed the DAMAGE-significance line
(Hexing Squelcher `--`→`dmg`, Sensei's Divining Top `dmg`→`--`) with win rate
unchanged to the fourth decimal: the margin, not a change.

**Azusa moved in ONE coherent direction, and the mechanism is the staged card.**
Yavimaya Elder left and Traveling Chocobo arrived, as staged. The three rows
beyond their bars all ROSE and by nearly the same amount:

| card | old | new | move |
|---|---|---|---|
| Rampaging Baloths | +0.0316 ±0.0040 | +0.0361 ±0.0040 | +0.0045 |
| Avenger of Zendikar | +0.0329 ±0.0039 | +0.0371 ±0.0040 | +0.0042 |
| Green Sun's Zenith | +0.0108 ±0.0029 | +0.0149 ±0.0029 | +0.0041 |

Traveling Chocobo is a landfall DOUBLER -- `reps = 1 + count("Ancient
Greenwarden") + count("Traveling Chocobo")` -- so with it in the list every
landfall payoff fires once more per land. Rampaging Baloths and Avenger of
Zendikar are both in `_landfall_payoffs`, so each got more valuable to remove
and its leave-one-out row rose. **Green Sun's Zenith is NOT a landfall payoff
and its rise is INFERRED, not traced**: it tutors creatures, and the creatures
it would find got better. That is the obvious reading and it has not been
checked against what GSZ actually fetches.

**This is §0z27's rule pointed the other way.** Adding a REDUNDANT card
understates the rows of the cards it duplicates; adding a MULTIPLIER raises
the rows of the cards it multiplies. Neither is evidence about those cards.
Baloths and Avenger are not better cards than they were yesterday -- they are
the same cards in a list that doubles them.

**AND ONE "FLIP" THAT IS NOT ONE, which is §0z24 caught live.** Sylvan Library
went −0.0007 ±0.0018 → +0.0001 ±0.0019: inside its bar both times, a blank
measured twice. Its signal column reads `FLIP` rather than `--`, because FLIP
is assigned on an unguarded sign and overrides `--`, so the comparison script
that produced the table above counted it as a sign flip between significant
rows until the bars were read. A tool trusting the column was fooled exactly
as §0z24 says a reader will be.

## 0z43. MEASURED — the one-card cast lookahead (queued item 18): built, wired into six engines, a measured null, and OFF

Queued item 18 says `main_phase` is greedy on `priority` and never asks
whether casting the greedy pick strands something. This is the first half of
it, built behind `cast_lookahead` (default False) and measured, not adopted.

### What it does, and what it cannot do

`engine.lookahead_pick` is ONE function; every engine's `main_phase` calls it
where it used to call `max(options, key=rank)`. With the knob on, before the
greedy pick G is cast it asks of each other affordable option O: is O
stranded once G is paid, and is G still affordable once O is paid? If so O
goes first and both are cast. It never drops G -- it only reorders.
`engine.pool_after` is the prediction: `spend` taps each paid unit's OWNER, so
a two-unit source paying one unit takes both with it.

**It does not settle §0z8's own case, and cannot.** There, Voice of the
Blessed `{W}{W}` and Lurrus `{1}{W}{B}` could not both be cast from the mana on
the table, and `priority` ranks Voice higher; any policy that trusts
`priority` casts Voice. Whether Lurrus is the better card is item 18's SECOND
half -- every deck's priorities were tuned while which land got tapped was
arbitrary -- and that is a question about the numbers, not about ordering.

**And the ordering half is mostly already handled.** The test's motivating
hand -- a Plains and a colourless rock, a `{1}` card and a `{W}` card -- is
stranded by bare `can_pay` (it taps lands before rocks), but NOT by the live
engine: §0z8's SURPLUS rule makes `available_mana` read the hand's colour
demand and keep the Plains. The test pins the wiring with `mana_surplus=False`
for exactly that reason. What the lookahead catches in real games is the
residue the surplus rule misses.

### What it was worth

Wired into all six engines (azusa falls back to greedy while Castle
Garenbrig's creature-only mana is floating, because one pool cannot price
both kinds of option; tivit's own `pay` makes the payment, so the lookahead
reads the payment `choose_mode` proved). N=15,000 paired, staged lists, same
seeds, knob on against off:

| deck | T10 win rate | T20 win rate | games changed, T10 / T20 |
|---|---|---|---|
| rendmaw | +0.0005 ±0.0006 | −0.0003 ±0.0012 | 21 / 78 |
| lorehold | −0.0005 ±0.0006 | −0.0009 ±0.0013 | 23 / 101 |
| karlov | −0.0004 ±0.0008 | −0.0001 ±0.0013 | 34 / 101 |
| tivit | −0.0003 ±0.0011 | +0.0010 ±0.0020 | 70 / 243 |
| shilgengar | +0.0001 ±0.0003 | +0.0007 ±0.0012 | 4 / 81 |
| azusa | +0.0003 ±0.0007 | −0.0006 ±0.0011 | 29 / 77 |

(N=1,000 smoke first: it fires in 4-12% of games in every deck, so the
wiring is live everywhere -- `lookahead_reorders`.)

**ALL TWELVE CELLS ARE INSIDE THEIR BARS, and the signs split five up, seven down.**
It changes the result of up to 243 games in 15,000 and those changes cancel.
That is a MEASURED NULL, not an unmeasured one: the ordering half of item 18
is worth nothing this harness can see, at the tables' N, in any deck. It stays
OFF -- turning it on would move all six baselines, and six rebuilds, for a
policy that buys nothing.

**What that leaves of item 18 is the priority numbers**, which is where §0z8
pointed in the first place. The lookahead proves the casting ORDER is not the
leak; if Lurrus is the better card, the only lever is `priority`, and
re-tuning priorities is a per-deck judgement with its own measurement, not a
code change. A per-card priority sweep through `run_ab` is the obvious next
step and has not been tried.

`tests/test_cast_lookahead.py` pins `pool_after`, the rescue rule and the
rendmaw wiring; `--mutate` runs four mutations, exact sets, all right first
time.

## 0z44. MEASURED — the `priority` numbers (queued item 18's second half): right in four decks, wrong in two, and the two are worth +0.009 and +0.021

§0z43 left item 18 with one claim: every deck's `priority` numbers were
tuned while which land got tapped was effectively arbitrary (§0z8), and the
casting ORDER was not the leak. This measures the numbers themselves.
`diagnostics/run_priority_sweep.py` is the harness; every table below is in
`results/priority_{lever,screen,confirm,joint,mechanism}.txt`.

**What a priority move changes, said first.** `priority` is not only the cast
order in `main_phase`. The same number ranks lorehold's recursion picks,
tivit's pool picks and the sacrifice-to-cast chooser in `engine.py`, so every
row below moves every decision that reads it. The commander is never moved,
and rendmaw's `+3` ramp bonus is left alone.

### The harness, and the three checks on it

Four tiers, cheapest first, because the naive sweep (every card, both
directions, N=15,000, both horizons) prices at ~40 CPU-hours:

| tier | what | N, horizons | seeds |
|---|---|---|---|
| lever | the whole table replaced: FLAT (every nonland card at the median, so the MV tie-break decides) and REVERSED | 15,000, T10+T20 | 1234.. |
| screen | every nonland card ±2, one at a time — 760 arms | 5,000, T20 | 1234.. |
| confirm | the 74 screen survivors | 15,000, T10+T20 | 6234.. (disjoint) |
| joint | every move confirmed POSITIVE at both horizons, together | 15,000, T10+T20 | 21234.. (disjoint from both) |

The A leg is simulated once per deck, horizon and seed block instead of once
per arm, which halves the cost. That is sound only if nothing in a game reads
`cfg["watch"]` except a counter, so the tool checks it three ways: a **NOOP**
arm that watches every nonland card must change ZERO games (it did, in every
phase, all 26 deck-horizon-block cells); **`--mutate`** makes NOOP a real move
and the gate fired on all twelve lever cells, as written down before running;
and one arm (karlov, Voice of the Blessed −2, N=400) reproduces `run_ab`'s
numbers exactly, A legs identical game for game. `validate` was `+0.00` on
all eighteen metrics before the run. **The seed blocks do not overlap**, so
neither selection step can bias the number the next one reports.

Δ = 2 is a judgement, said out loud: on a 1–10 scale with 10–14 distinct
levels per deck it crosses a few tiers without sending a card to the top or
bottom outright.

### The lever: the tables carry real information

| deck | FLAT T10 | FLAT T20 | REVERSED T10 | REVERSED T20 |
|---|---|---|---|---|
| rendmaw | −0.0033 ±0.0023 | **+0.0031 ±0.0055** | −0.0198 ±0.0027 | −0.0279 ±0.0065 |
| lorehold | −0.0135 ±0.0031 | −0.0147 ±0.0069 | −0.0226 ±0.0034 | −0.0496 ±0.0073 |
| karlov | −0.0280 ±0.0049 | −0.0173 ±0.0073 | −0.0863 ±0.0058 | −0.0626 ±0.0083 |
| tivit | −0.0447 ±0.0050 | −0.0367 ±0.0077 | −0.0713 ±0.0052 | −0.0715 ±0.0081 |
| shilgengar | −0.0022 ±0.0011 | −0.0213 ±0.0056 | −0.0059 ±0.0014 | −0.0496 ±0.0064 |
| azusa | −0.0203 ±0.0044 | −0.0310 ±0.0065 | −0.0493 ±0.0050 | −0.0707 ±0.0079 |

Written down before the run: FLAT costs every deck, REVERSED costs more. True
in 11 of 12 cells. **Rendmaw at T20 is the exception** — its table is
indistinguishable from "cast the biggest affordable card" at the long
horizon, plausibly because the ramp bonus FLAT keeps is most of its ordering.

### The screen: two thirds of the survivors are LOSSES

74 of 760 rows excluded zero, against ~38 expected by chance. The excess sat
in tivit (20 of 130) and rendmaw (14 of 128); **azusa was exactly chance** (5
of 116). About two thirds of survivors were negative — moving the card
either way LOSES — which is the table's own evidence that the numbers are
mostly locally right.

### The confirmation, on seeds the screen never saw

Positive at BOTH horizons, the project's staging bar:

| deck | move | T10 | T20 |
|---|---|---|---|
| tivit | Mirkwood Bats 8 → 10 | +0.0130 ±0.0024 | +0.0085 ±0.0030 |
| tivit | Anointed Procession 8 → 10 | +0.0097 ±0.0026 | +0.0079 ±0.0038 |
| tivit | Rhystic Study 9.5 → 7.5 | +0.0076 ±0.0023 | +0.0075 ±0.0034 |
| tivit | Tempting Contract 6.5 → 8.5 | +0.0037 ±0.0017 | +0.0027 ±0.0025 |
| karlov | Felidar Sovereign 7 → 9 | +0.0055 ±0.0017 | +0.0047 ±0.0023 |
| karlov | Sorin, Solemn Visitor 6 → 8 | +0.0018 ±0.0016 | +0.0024 ±0.0023 |

**Rendmaw, lorehold, shilgengar and azusa have no confirmed move**; the
current number beats or ties every alternative tried. Three rows are worth
knowing and are NOT confirmed: **Time Sieve 9 → 11 flips sign** (−0.0043
±0.0022 at T10, +0.0121 ±0.0039 at T20) — extra turns count against the
horizon (§0m, queued 8c), so an earlier Sieve spends T10's short budget;
**Tendershoot Dryad 6 → 8** (rendmaw, +0.0027 ±0.0010 / +0.0013 ±0.0018)
and **Monument to Endurance 6 → 8** (lorehold, +0.0003 / +0.0038 ±0.0019)
have a gradient in both directions but a bar at one horizon only.
**§0z8's own case did not survive**: Voice of the Blessed −2 was inside its
bar at the screen, so Voice over Lurrus stands.

### The joint, on a third seed block

| deck | moves | T10 | T20 |
|---|---|---|---|
| karlov | Felidar 7 → 9; Sorin, Solemn Visitor 6 → 8 | **+0.0099 ±0.0023** | **+0.0091 ±0.0031** |
| tivit | Procession 8 → 10; Bats 8 → 10; Rhystic 9.5 → 7.5; Contract 6.5 → 8.5 | **+0.0225 ±0.0036** | **+0.0211 ±0.0052** |

Tivit's joint is well under the sum of its four singles (+0.034 at T10), and
that is expected rather than worrying: lowering Rhystic Study and raising the
two 8s are partly THE SAME reordering, since both put the token engines ahead
of the draw engine.

### The mechanism, in each deck's own counters

`run_ab`, N=3,000, T20 (`priority_mechanism.txt`). Win route = share of games
won that way.

- **Felidar Sovereign 7 → 9**: Felidar-route wins **+0.0130** [+0.0077,
  +0.0183]; combo-route wins −0.0030, damage −0.68, life gained −0.78. The
  alternate win condition checks more upkeeps. Every proxy falls while the
  objective rises — §0t's shape again.
- **Sorin, Solemn Visitor 6 → 8**: life gained +1.36, lifegain triggers
  +0.12 — the team-lifelink clause fires more. Its +0.002 does not resolve at
  this N.
- **Anointed Procession up / Rhystic Study down**: artifacts +8.2 / +10.3,
  Treasures +4.2 / +4.6, **Revel in Riches wins +0.0077 / +0.0057**, cards
  drawn −0.34 / −0.36.
- **Mirkwood Bats 8 → 10**: **drain-route wins +0.0157** [+0.0083, +0.0230],
  bought at −6.2 artifacts and −3.2 votes because Bats now displaces an engine
  piece. Net positive.
- **Tempting Contract 6.5 → 8.5**: nothing resolves at N=3,000. Its confirm
  row is the most marginal of the six, and **no mechanism is claimed for it**.

**The tivit story is one story**: its numbers ranked card draw above the
token engines, and the objective wants the reverse. `cards_drawn` falls in
every tivit move while win rate rises.

### ADOPTED 2026-09-25 -- and the rebuild is deliberately DEFERRED

**The owner adopted both joints, exactly as measured**: karlov's two moves
and tivit's four, and nothing else. Time Sieve 9 → 11 is NOT among them -- it
flips sign between horizons and was never confirmed -- and neither are the two
single-horizon rows. Adopting fewer than a joint's moves would have committed a
configuration nobody measured.

`check_unchanged_decks` against the pre-adoption commit: **rendmaw, lorehold,
shilgengar and azusa BIT-IDENTICAL on all 8 metrics; karlov and tivit MOVED**,
as they must. That check builds from the deck MODULE, so it cannot see the
staged Anointed Procession's move; `build_pending` confirms all six moves live.

**THE KARLOV AND TIVIT TABLES ARE NOW STALE, AND SAY SO.** The owner chose to
batch this rebuild with other pending work rather than run it now. Their
caches are left SUSPECT on purpose -- it is the true state, and it is the one
that stops harm: `ablation.py` keys its cache on deck, horizons and N rather
than on code, so resuming onto a full stale cache would silently REPRINT the
old numbers. Each carries a `--note` saying why. Clearing either with
`--verified` would be false (the numbers moved), and deleting either would turn
`check_docs` green over a stale table, which is the trap this repo has written
down most often. **`check_docs` therefore fails on exactly these two caches
until the batched rebuild**, and that failure is the signal, not a defect.
`./tools/regen_tables.sh` deletes each cache before it runs, so the rebuild
itself is safe.

**Every staged swap in both decks was measured on the old priorities** and
says so in its Change: karlov's Bloodthirsty Conqueror and Bolas's Citadel,
and tivit's Anointed Procession, whose own priority is one of the moves.

### What was not done, originally

**Nothing was adopted at measurement time.** Changing a priority in `karlov_v2.py` or
`tivit_v1.py` moves that deck's baseline, which forces its ablation table to
be rebuilt (§0z27: a changed baseline has no check but a rebuild), and it
changes the list every staged swap in those decks was measured against.
**Anointed Procession is itself a staged card whose priority is one of the
moves**, so its staged +0.0113 / +0.0145 was measured at a priority now shown
to be worth ~0.008 less than the better one. That is the owner's call.

## 0z45. MEASURED — eight Reality Fracture numbers enter the ledger, and each says whether it is still true

Nine Reality Fracture cards were implemented, pinned and measured on
2026-09-20/21. Until 2026-09-25 only Ginger's number was in the ledger; the
other eight lived only in `results/*.txt` -- the "number with nobody's
decision attached" that the `Candidate` class exists to prevent. They are now
`Candidate`s in `MEASURED`, and the four that also sat in `PROPOSED` are closed
there with a pointer rather than deleted, so their verified oracle text stays.

**A ledger entry that does not say whether its number is current would be
worse than none**, so that was checked, not assumed. `check_unchanged_decks`
between 246b148 (where batch 2 was measured) and 2026-09-25:

| deck | since measurement | cards | status |
|---|---|---|---|
| rendmaw | **BIT-IDENTICAL** | Proft, Sinister Mastermind | **CURRENT** |
| shilgengar | **BIT-IDENTICAL** | Lyra, Archangel of Dawn | **CURRENT** |
| lorehold | MOVED (§0z42 decking) | Stingcaster Mage | stale |
| tivit | MOVED (§0z44 priorities) | Memnarch, the Warden | stale |
| karlov | MOVED (§0z44, §0z46) | Liliana the Faultless, Edgar | stale |
| azusa | MOVED (§0z41, §0z42, Chocobo) | Verdant Kraken, Simulacrum Shaper | stale |

Neither CURRENT deck has a staged change, so its module IS its measured list
and the module-based check covers it fully. **Later the same day §0z47 moved
rendmaw** (counterspells now make Elephants and Spiders), so Proft is STALE as
well and says so in its Candidate; Lyra is the one CURRENT number left.

**Azusa's two are stale in a sharper way.** They were measured against
`-Yavimaya Elder`, and on 2026-09-22 the Chocobo was COMMITTED into exactly
that slot -- so the cut no longer exists, and the live comparison is the one
against the Chocobo: Verdant Kraken loses at T10 (−0.0049 ±0.0029) and ties at
T20 (+0.0007 ±0.0042); Simulacrum Shaper loses at both. The committed card
holds the slot on the evidence that exists.

**Karlov's two lose their slot**: both beat Swiftfoot Boots and both lose to
Bloodthirsty Conqueror in that same slot by −0.024 to −0.030, significant at
both horizons.

The cleanest of the eight is **Lyra**: significant at both horizons, CURRENT,
and against the only batch-2 cut whose own row is genuinely negative (Vampiric
Rites −0.0014 ±0.0011). No rival has been measured for that slot, so it is a
candidate for a head-to-head rather than a staging.

## 0z46. FIXED — Voice of the Blessed's ten-counter indestructible (queued 8b)

"As long as this creature has ten or more +1/+1 counters on it, it has
indestructible." (Scryfall, verified 2026-09-25.) §0n deliberately kept Voice
OUT of the generated `INDESTRUCTIBLE` set, because a static tag would make it
indestructible at zero counters. That was right, and it left the clause with
nowhere to live, so the card was never indestructible at all -- in a deck
whose engine is lifegain events and where ten counters is reachable.

**It lives in `opponents.indestructible_of(g, perm)`, beside `flying_of`**,
which already carried Voice's four-counter flying off the same `counters`
field. `destroy()` is the ONLY place indestructible is read, so routing that
one read covers spot removal, the pod's wipes and your own wipes together; a
second read site written as `perm.card.indestructible` would silently skip it,
and the function's docstring says so.

**It fires**: over 2,000 karlov games at T20, removal asked about Voice 134
times and the ten-counter clause saved it **32 times (0.016 a game)**. Small,
and real.

`tests/test_voice_of_the_blessed.py` pins it: nine counters dies to a destroy,
ten survives, ten still dies to exile, your own known destroy and exile both
honoured, a non-Voice creature at ten is not protected, and the four-counter
flying neighbour re-checked per §0z28. Three mutations, exact sets, correct on
the first run. Only karlov holds Voice, so only karlov's baseline moves, and
karlov is already stale pending the owner's batched rebuild (§0z44).

## 0z47. FIXED — March of the World Ooze's Elephant, and Arasta reading the same event a second way (queued 4)

"Whenever an opponent casts a spell, if it's not their turn, you create a 3/3
green Elephant creature token." (Scryfall, verified 2026-09-25.) The P/T
half was in `power_of` from the start; this half was `KNOWN_ISSUES` item 1a in
the oracle audit and queued item 4 in `CLAUDE.md`, and the committed numbers
were called a floor for it.

**The model has exactly one opponent spell on your turn: a counterspell.**
Removal and wipes land in `opponents_act`, which is the opponents' own turns;
karlov's `opponent_activity` spells are the same. So `opponents.countered`
now calls `g.opponent_cast_on_your_turn(i)` when the engine defines it -- the
`hasattr` protocol, one new row in `docs/ARCHITECTURE.md` -- and only rendmaw's
`Game` does. It runs `engine.march_elephant`, which goes through
`make_tokens`, the one token path, so Primal Vigor and Parallel Lives double
the Elephant and March's own first clause makes it 6/6.

**Writing it found the rule written twice.** Arasta of the Endless Web is in
the same deck: "Whenever an opponent casts an instant or sorcery spell, create
a 1/2 green Spider creature token with reach." It was modelled as one per-round
roll (`opp_instant_rate`, 0.8), and a counterspell -- an instant, cast at you,
a real event in this model -- made no Spider. `engine.arasta_spider` is now
called from both: the roll, which stands for the pod's instants in general,
and the hook. §0u's shape, caught on the day the second reader was written
rather than months later.

**What March still does not see, and why it stays a floor.** Instant-speed
removal, flash creatures, cantrips, and every spell an opponent casts on
ANOTHER opponent's turn (which also triggers March -- "if it's not THEIR
turn"). Arasta's roll exists and March does NOT read it: it does not say whose
turn the spell was cast on, and routing March through it would put an
uncalibrated knob (0.8) under a second card. At a real table this card makes
far more Elephants than 0.03 a game.

**Measured**, N=15,000 paired, seeds 5000+, `build_pending("rendmaw")`:

| comparison | T10 win | T20 win | T20 damage | mechanism |
|---|---|---|---|---|
| Elephant on − off | +0.0003 ±0.0003 | **+0.0014 ±0.0008** | +0.14 ±0.03 | 0.033 Elephants a game |
| Arasta on counterspells, on − off | +0.0003 ±0.0003 | +0.0003 ±0.0006 | +0.04 ±0.02 | +0.03 tokens a game |
| the whole hook, on − off | +0.0006 ±0.0004 | **+0.0017 ±0.0010** | +0.18 ±0.04 | +0.064 tokens a game |
| March's row (card − blank), new engine | +0.0052 ±0.0014 | +0.0145 ±0.0028 | +1.89 ±0.15 | the table has +0.0131 ±0.0028 |

A 6/6 body 0.033 times a game is worth 0.0014 -- about four points of win rate
per Elephant, which is what a 6/6 on turn 8 should be. The row moves inside its
bar. `tests/test_march_elephant.py` pins it: seven cases, four mutations,
exact sets. The first plain run failed case C on a TEST defect, not an engine
one -- with the counter chance forced to 1.0, a roll of 0.999 still counters
(`rolls[i] < p`); the harness uses 1.0. Only rendmaw's baseline moves
(`check_unchanged_decks`: the other five bit-identical). Its table is stale
and joins the owner's batched rebuild.

## 0z48. FIXED — Artist's Talent, all three levels (queued 2)

    {1}{R} Enchantment — Class  (Scryfall, verified 2026-09-25)
    Whenever you cast a noncreature spell, you may discard a card. If you do,
    draw a card.
    {2}{R}: Level 2 -- Noncreature spells you cast cost {1} less to cast.
    {2}{R}: Level 3 -- If a source you control would deal noncombat damage to
    an opponent or a permanent an opponent controls, it deals that much
    damage plus 2 instead.

**What it was**: one line in `reduce_cost`, `if g.has("Artist's Talent")`.
Level 2 arrived free the moment the Class resolved, it discounted CREATURE
spells as well (the text says noncreature), and levels 1 and 3 did not exist.
`tools/ablation.py` rightly held it MODEL-BLIND. The oracle audit called the net
direction "genuinely unclear", and that turned out to be the finding.

**What it is now** (`edhmc/lorehold.py`, one function per clause, so a
mutation can remove each alone):

* **The level is on the permanent** -- `Permanent.level`, default 1 per CR
  716.2d, so a Class that leaves and comes back is level 1 again.
* **`artist_level_up`, a POLICY said out loud**: after the post-combat main
  phase, spend `{2}{R}` per level with mana nothing in hand could use, and
  never out of the miracle reserve -- the rule every spell in `main_phase`
  obeys. Then the main phase looks again, because level 2 can make a spell
  affordable. Greedy and late: a pilot would sometimes level BEFORE casting to
  buy the discount. `artist_max_level` (3) caps it, which is how the levels
  were measured apart.
* **Level 1, `artist_rummage`**, from `on_cast_triggers`, so Bombardment and
  Mastery copies trigger it and Double Vision's does not. The discard pick is
  Lorehold's own, factored into `rummage_discard_choice` so the two rummages
  are one policy (§0z30). It triggers Monument to Endurance. **Declined before
  your draw step**: an upkeep Galvanoth or Scrollwielder cast would make its
  draw the turn's first -- a miracle-eligible draw the function opens no
  window for -- and demote the draw step's arranged card to second.
* **Level 2, `artist_discount`**, noncreature only, read by BOTH `reduce_cost`
  and `miracle_reduction` -- one function, because the discount written twice
  is §0u.
* **Level 3, `artist_bonus`**, +2 per HIT at `deal_pod_damage`, the one
  noncombat chokepoint. **`hits` is now a required argument with no default**,
  so all eleven call sites had to decide and a new one cannot be written
  without deciding: Guttersnipe and Longshot are one hit per opponent, Urabrask,
  Pyremaw, Boros Charm and each Soulfire target one, Olórin's Searing Light one
  per opponent, **and Monument's "each opponent LOSES 3" zero -- life loss is
  not damage.** Boros Charm's `hits=1` rests on every `pod_damage` card in the
  lorehold pool being single-target damage; the test pins that census.

**Measured**, N=15,000 paired, seeds 5000+, `build_pending("lorehold")`:

| comparison | T10 win | T20 win | T20 damage |
|---|---|---|---|
| the card's row (card − blank), new engine | +0.0016 ±0.0019 | +0.0043 ±0.0040 | +0.44 ±0.22 |
| the committed table's row, old engine | | +0.0052 ±0.0036 | +0.43 ±0.19 |
| levels 2 and 3 (cap 3 − cap 1) | +0.0010 ±0.0009 | **+0.0040 ±0.0020** | +0.29 ±0.10 |
| level 2 alone (cap 2 − cap 1) | +0.0002 ±0.0008 | +0.0009 ±0.0019 | +0.15 ±0.10 |
| **level 3 (cap 3 − cap 2)** | **+0.0008 ±0.0005** | **+0.0031 ±0.0010** | +0.14 ±0.03 |
| level 1 alone (cap 1 − blank, from the arm means) | | ≈ +0.0003 | |

Mechanism: 1.60 rummages and 0.32 levels a game over all games (the card is
not out in most of them).

**The row barely moved because the errors cancelled**, which is the audit's
"unclear direction" resolved rather than confirmed. The free level 2 was
flattering the card; the missing level 3 was costing it about as much. **Level
3 is the whole card**: significant at both horizons, three times its own bar at T20,
because it turns every Guttersnipe and Longshot trigger from 2 into 4. The
level-2 discount -- the only thing the old engine modelled -- is inside its bar
on its own. The level-1 rummage is worth nothing measurable in win rate: 1.6
card swaps a game in a deck that already rummages three times a round.

**Both staged lorehold swaps were re-measured across the change**, because
Caldera Pyremaw is exactly the kind of source level 3 boosts: the same 2x2
factorial (`diagnostics/run_lorehold_pair.py`, N=30,000, same seeds) at HEAD
6a0e786 and after. Caldera GIVEN Sunbird's +0.0240 ±0.0027 → +0.0217 ±0.0027;
Sunbird's GIVEN Caldera +0.0161 ±0.0030 → +0.0150 ±0.0031. Both inside their
bars, both still significant; the stagings stand
(`results/lorehold_pair_artist.txt`). The run also showed Sunbird's ALONE at
+0.0109 at HEAD, down from +0.0152 on 2026-09-09 -- a drop that predates this
change, filed under queued item 0b-i and not attributed.

**Not modelled, and named.** The Dawning Archaic's attack trigger casts a
spell through its own inline block, not `resolve_spell`, so the spell it casts
triggers Guttersnipe but not Longshot, Urabrask, Pyremaw, Mentor or this
card's rummage -- a pre-existing §0u divergence this change did not widen and
did not fix. The level-up policy never levels before casting.

`tests/test_artists_talent.py`: eighteen cases, six mutations, exact sets,
correct on the first run -- with one expectation defect caught ON PAPER
before it: the level-up cases read the level through `artist_level`, which
the first mutation replaces, and would have charged that mutation to the
policy. They read the permanent's own level now. Only lorehold's baseline
moves. Its table is stale and joins the owner's batched rebuild; the card
moves from `KNOWN_BLIND` to `SCRIPTED_LOREHOLD`.

## 0z49. FIXED — Storm Herd's X was a constant 40, and the largest row in lorehold's table sat on it

"Create X 1/1 white Pegasus creature tokens with flying, where X is your life
total." (Scryfall, verified 2026-09-25.) The engine had `cfg["storm_herd_x"]`,
40, and the oracle audit's reason was "this engine does not track life at
all". **That stopped being true at pod v3 (2026-09-04)**, three weeks before
anyone re-read it -- §0z13's shape: a note saying something cannot be done is
a claim with a date on it. `lorehold.storm_herd_x` reads `g.your_life` at
resolution (a copy resolving later reads the total then); setting the knob
still forces a constant, which is how the old number is reproduced.

**Measured**, N=15,000 paired, seeds 5000+, `build_pending("lorehold")`:

| comparison | T10 win | T20 win | T20 damage |
|---|---|---|---|
| **the fix: X = life − X = 40** | −0.0121 ±0.0018 | **−0.0271 ±0.0031** | −1.39 ±0.11 |
| Storm Herd's row (card − blank), new | +0.0175 ±0.0022 | **+0.0442 ±0.0039** | +3.61 ±0.21 |
| the same row at X = 40 | +0.0296 ±0.0028 | +0.0713 ±0.0046 | +5.00 ±0.26 |

The X = 40 arm reproduces the committed table's +0.0715 ±0.0046, which is the
check on the harness (§0z35). Mechanism: 5.53 Pegasi a game against 10.71 at
X = 40, so the card resolves about 0.27 times a game at **about 21 life**, not
40. **It is still the deck's largest row, at five-eighths of what it was.**
The card moves from `KNOWN_BLIND` to `SCRIPTED_LOREHOLD`: its only
approximation was X. Lorehold's baseline moves by a quarter of the deck's
largest card, so its table is stale on top of §0z48, and both staged lorehold
swaps were re-measured after it (below, §0z48's factorial).

## 0z50. FIXED — Radiant Scrollwielder's lifelink

"Instant and sorcery spells you control have lifelink." Its docstring said
separating spell damage from creature damage at every `deal_pod_damage` call
site was "a bigger change than this fix". §0z48 had already made every call
site state its `hits`; `spell` is the second required argument, and eleven
call sites answered it -- Boros Charm, Soulfire Eruption and Olórin's Searing
Light are spells, Guttersnipe, Longshot, Pyremaw and Urabrask are permanents,
Monument's drain is life loss. `scrollwielder_lifelink` gains what was DEALT
(702.15b), not the bounded figure the damage metric records.

Scrollwielder is a CANDIDATE, not in the list, so no baseline moves. Measured
in the Penance slot on the staged list: lifelink on − off **+0.0017 ±0.0007**
at T20 (+0.0003 ±0.0003 at T10), 0.36 life a game. **Against Caldera Pyremaw
in the same slot it still loses, −0.0033 ±0.0015 / −0.0085 ±0.0034**, so the
2026-09-05 decision that took Caldera over it stands with the clause in.

## 0z51. FIXED — Ranger of Eos tutors, it does not draw

"When this creature enters, you may search your library for up to two creature
cards with mana value 1 or less, reveal them, put them into your hand, then
shuffle." It was `script="draw2"`. `karlov.ranger_of_eos_etb` takes the two
highest-`priority` one-drops left in the library, recomputed at the search
(§0z19), and shuffles through `crn_shuffle` -- it matters here, because Bolas's
Citadel plays off the top. In the staged list the targets are Soul Warden,
Soul's Attendant, Mother of Runes and Serra Ascendant.

N=15,000 paired: the row is **+0.0041 ±0.0017 / +0.0091 ±0.0033** at T10 /
T20 against +0.0045 / +0.0067 as `draw2` on the same blank; tutor − draw2 is
−0.0003 ±0.0016 / +0.0023 ±0.0030, inside its bar at both. 0.26 cards found a
game. Two specific one-drops are worth about what two random cards were, which
is the answer, and the card moves to `SCRIPTED_KARLOV`.

## 0z52. FIXED — Lurrus's hybrid pips, paid AND counted

{1}{W/B}{W/B} was flattened to {1}{W}{B}. Paying it is `alt_costs` tagged
"hybrid" -- the convention Revitalizing Repast set -- so {W}{W} or {B}{B} can
cast it. **But a flattened cost is also wrong for anything that READS the
cost**: "a hybrid mana symbol is all of its component colors" (107.4e), so
Lurrus is two devotion to white (700.5), and karlov's `devotion_white` gates
Heliod. `engine.hybrid_pips` reads the most of a colour any hybrid spelling
carries, and devotion reads it. The pay half alone would have been §0u's shape
inside one card.

N=15,000 paired: **+0.0003 ±0.0004 / +0.0003 ±0.0007**, 1.3% of games change,
lifegain triggers +0.03 a game. Correct, and small.

**Daxos's toughness is left unimplemented, on purpose.** "Daxos's toughness is
equal to your devotion to white" is one line now that devotion is right, and it
would move nothing: no code in `karlov.py` or `opponents.py` reads toughness.
Written down so that the day something does, this is found (§0z12: a value
nothing reads is a loaded gun).

## 0z53. MEASURED — Goldspan Dragon's head-to-heads (queued 0c)

§0c said its significant row was not a staging. The paired runs it asked for,
N=15,000, on the staged list after §0z49 and §0z50:

| swap | T10 win | T20 win | T20 damage |
|---|---|---|---|
| Goldspan in Caldera's slot (Goldspan − Caldera) | −0.0039 ±0.0012 | **−0.0108 ±0.0027** | −0.35 ±0.11 |
| **−Blasphemous Act +Goldspan** | **+0.0106 ±0.0020** | **+0.0162 ±0.0044** | +1.81 ±0.22 |
| −Lightning Greaves +Goldspan | +0.0005 ±0.0014 | +0.0084 ±0.0034 | +1.00 ±0.17 |

**It does not take the Penance slot from Caldera.** The Blasphemous Act swap
is significant at both horizons; the Greaves one only at T20. **Read the Act
row with its cut's category**: Blasphemous Act is a symmetric wipe in
`PARTLY_MODELLED` -- your half faithful, the opponents' half an abstract
creature count, "the COST is modelled and the BENEFIT is an estimate" -- so
this swap removes a card whose upside the model estimates. §0z36 says that
can err either way. Staging it is the owner's decision, and the ledger records
it as a Candidate.

## 0z54. FIXED — one path for every free cast

The Dawning Archaic: "Whenever The Dawning Archaic attacks, you may cast
target instant or sorcery card from your graveyard without paying its mana
cost. If that spell would be put into your graveyard, exile it instead."
(Scryfall, verified 2026-09-25.) Its handler was an inlined SUBSET of
`resolve_spell` -- treasures, Soulfire, tokens, pod damage, Guttersnipe --
and Goliath Daydreamer's docstring had already named it "§0u's shape sitting
in this file". Fixing it found three more copies of the same shape:

| path | what it did | what it does now |
|---|---|---|
| The Dawning Archaic | a subset; no Longshot, Pyremaw, Mentor, Artist's Talent, Bombardment | `cast_free`, exiled after |
| Invoke Calamity, from HAND | `apply_spell_effects` as a non-copy: **no cast trigger at all** | `cast_free(from_hand=True)`, exiled |
| Goliath's dream cast | treated the card as a copy: discards skipped, went nowhere | `cast_free`, then the graveyard |
| Galvanoth | `mv_cheated` added by hand AND inside `resolve_spell` | `cast_free`, counted once |
| Radiant Scrollwielder | its "exile it instead" ignored: the card returned to the graveyard | `resolve_spell(exile=True)` |

`cast_free` is `resolve_spell` with `exile` and an explicit `cheated=free_mv`.
Two policy choices are said out loud: the Archaic does not cast a WIPE off its
own attack trigger (it would destroy the attackers, itself included), and it
respects `pilot_may_cast`. Invoke's hand casts are FROM HAND, which Approach and
Sunbird's Invocation both read.

N=15,000 paired: the path is worth **+0.0038 ±0.0016 / +0.0135 ±0.0031** to
lorehold's baseline at T10 / T20; the Archaic's row goes +0.0006 → **+0.0089
±0.0030**. Galvanoth and Scrollwielder are candidates, not in the list.
`tests/test_free_casts_and_approach.py` pins it.

## 0z55. FIXED — Approach of the Second Sun could never be cast twice

"If this spell was cast from your hand and you've cast another spell named
Approach of the Second Sun this game, you win the game. Otherwise, put
Approach of the Second Sun into its owner's library seventh from the top and
you gain 7 life." The engine counted casts and declared a win at two, and
had no "otherwise": the card went to the graveyard, so a second cast needed a
copy, and the win essentially did not exist. `ablation.py` held it BLIND and
its row was −0.0003.

`approach_resolves`: seventh from the top (the bottom of a shorter library) and
7 life; a later cast FROM HAND wins. A miracle is cast from hand, and Lorehold
gives it miracle {2}, so the deck's own engine digs to it and recasts it
cheaply. A cast copy (Bombardment) counts as a spell named Approach that was
cast; a copy put on the stack (Double Vision) does not; neither is cast from
hand.

**Measured**, N=15,000 paired: the fix is **+0.0338 ±0.0030 / +0.0667 ±0.0043**
at T10 / T20, and the row **+0.0341 / +0.0666 ±0.0044**. Approach wins 0.092
games a game. That is the largest correction ever made to a single card here,
bigger than Storm Herd's whole row, and it moves lorehold's win rate from about
0.19 to 0.26.

**Read it as a CEILING in one respect, named rather than priced.** The pod
does not know what is in your library. A real table that saw Approach resolve
knows a win is seven cards away, and holds its counterspell and points its
attacks accordingly; this pod counters by the spell's `threat` (8.0, already
near the cap) and targets by board state. No knob covers it. The mechanism is
otherwise exactly the card's.

## 0z56. FIXED — Benevolent Offering does both its sentences

"Choose an opponent. You and that player each create three 1/1 white Spirit
creature tokens with flying. Choose an opponent. You gain 2 life for each
creature you control and that player gains 2 life for each creature they
control." NOT modal: both happen, the tokens first. It was `lifegain=4`.

`benevolent_offering`: three flying Spirits (Spirit added to the generated
`FLYING_TOKENS`, verified from this card; karlov's `make_tokens` had never set
`flying` because nothing had ever called it), +3 to the chosen opponent's
board, every Spirit a creature entering for the soul sisters on both sides,
then 2 life per creature you control as ONE event. The two choices are a
policy: the Spirits go to the least threatening opponent, the lifegain to the
one with the fewest creatures. **The test caught the first version choosing
the lifegain opponent before the Spirits existed**: the second choice is made
when the second sentence resolves, and the first choice's three Spirits can
change it. The first mutation expectation was rewritten for the corrected
function before it was re-run.

N=15,000 paired: **+0.0032 ±0.0011 / +0.0035 ±0.0021**; the row goes +0.0075
→ **+0.0089 ±0.0027**. SCRIPTED now.

## 0z57. FIXED — Necropotence, and a policy the owner is asked to confirm

"Skip your draw step. Whenever you discard a card, exile that card from your
graveyard. Pay 1 life: Exile the top card of your library face down. Put that
card into your hand at the beginning of your next end step." It was
`script="draw2"`: two cards once, and the draw step kept.

`necropotence_step`: the draw step is skipped; after your last main phase you
pay life for cards that reach your hand at THIS turn's end step, too late to
cast this turn. The life is always charged (a cost, as Bolas's Citadel's is).
The cards are not drawn, so Alhammarret's Archive does not double them. The
discard clause is INERT: this engine has no maximum hand size.

**The amount is a POLICY, and the owner was asked to confirm it:** fill the
hand to `necro_hand_target` (7), never paying below `necro_life_floor` (20).

| setting | T10 win | T20 win |
|---|---|---|
| the fix (new − `draw2`) | +0.0014 ±0.0016 | **+0.0053 ±0.0028** |
| the card's row (card − blank) | +0.0054 ±0.0017 | **+0.0146 ±0.0031** (table: +0.0076) |
| floor 10 − floor 20 | +0.0009 ±0.0005 | **+0.0023 ±0.0011** |
| floor 30 − floor 20 | −0.0017 ±0.0008 | −0.0055 ±0.0016 |
| hand target 5 − 7 | −0.0047 ±0.0014 | −0.0073 ±0.0023 |

**Lower floors and fuller hands both win more**, which fits the standing finding
that life decides only 20% of karlov's losses: here life is a resource.

**CONFIRMED AND ADOPTED 2026-09-26: a 10-life floor and a 7-card hand.** The
owner's reasoning is the card's, not the table's: "similar to Bolas's
Citadel, the card is at its best when played to the extremes" -- which the
measurement agrees with in sign at both ends of the sweep. The numbers in the
table above were measured at the 20-life default; the rebuilt karlov table
carries the adopted one.

## 0z58. FIXED — Twitching Doll was SCRIPTED with neither clause in the engine

"{T}: Add one mana of any color. Put a nest counter on this creature. {T},
Sacrifice this creature: Create a 2/2 green Spider creature token with reach
for each counter on this creature. Activate only as a sorcery." It was in
`SCRIPTED_RENDMAW` -- a claim the engine implemented it -- with neither
clause anywhere. §0q's label-rot pointed at a card.

`Permanent.nest` (not `counters`, which are +1/+1 and read by `power_of`);
`on_mana_tap`, called from BOTH of `spend`'s tap paths (§0z4); and
`twitching_doll_sacrifice`, routed like `opponents.destroy` (the death, the
graveyard, artifact recursion), Spiders through `make_tokens` so Primal Vigor
doubles them and March makes them 6/6.

**Then the counters fired 0.03 times a game.** The POLICY made the card a blank
-- the table in CLAUDE.md, again: combat swung every untapped creature and
`tap_reluctance` taps mana creatures last, so the Doll attacked and never
tapped. `doll_policy="nest"`: it stays home and, still untapped at the end of
your turn, taps for mana nobody spends, for the counter. `"attack"` is the old
behaviour. **`on_mana_tap` crashed every azusa game** that spent floating mana,
because azusa's owners include `FloatingMana` objects with no card;
`check_unchanged_decks`, which runs all six decks, caught it before anything
was measured on azusa.

N=15,000 paired: nest − attack **+0.0041 ±0.0013 / +0.0090 ±0.0025**; the row
+0.0023 → **+0.0111 ±0.0027**. `doll_sac_at` 3 stays: 2 is worse (−0.0029
±0.0018), 4 and 5 inside their bars. 0.10 sacrifices and 0.31 Spiders a game.

## 0z59. MEASURED — Sunbird's decay (queued 0b-i): no single cause, and not significant today

§0p/§0w left it "worth finding, and worth NOT guessing at". Measured rather
than guessed: `diagnostics/run_sunbird_bisect.py` at all 22 commits from
d158724 (2026-09-09, which reproduces +0.0152 ±0.0028 exactly) to 6b4546e, on
the same seeds, so each step between commits PAIRS (`results/sunbird_bisect.txt`):

| commit | change | step |
|---|---|---|
| 5cdc015 | §0z8, the colour-payment rule ({5}{R}{R} is harder to pay honestly) | −0.0019 ±0.0024 |
| fe9d4af | §0z9, drain divided by the whole pod | −0.0027 ±0.0029 |
| 682a1c8 | §0z17, the CRN leak closed | +0.0010 ±0.0025 |
| ef641ae | §0z42, decking loses | **−0.0011 ±0.0008** |
| 6b4546e | §0z49, Storm Herd's X | **+0.0016 ±0.0016** |
| c9e83a1 | the decking reserve swept | +0.0003 ±0.0006 |
| f5ccbbb | §0z48, Artist's Talent's levels | −0.0007 ±0.0021 |
| the other 14 | | 0.0000 to the digit |

**No step is the decay.** Two correct engine corrections a day apart account
for most of it, neither resolvable alone, and later ones move it both ways.
Net since 2026-09-09: **−0.0034 ±0.0035, inside its bar at today's HEAD.** Paired
across commits the step bars are barely tighter than a single measurement --
an engine change reshuffles many games -- which is why the individual steps do
not resolve. The earlier drop (+0.0215 → +0.0146, 09-04 → 09-06) predates the
repo's reorganisation and is not covered. Queued item 0b-i is closed.

## 0z60. MEASURED — the six-deck rebuild, 2026-09-26

The owner deferred the karlov and tivit rebuilds on 2026-09-25 (§0z44) to
batch them; lorehold, rendmaw and karlov then moved again (§0z47-§0z58), and on
2026-09-26 the owner asked for all six. `./tools/regen_tables.sh` from empty
caches at dc4f20c: **03:16 to 06:25 UTC, 3 hours 9 minutes on four cores** --
the first end-to-end timing since §0z22 (CLAUDE.md had quoted a ~35 minute
figure it said was never re-timed). Committed deck by deck to the feature
branch as it ran, so no half-built cache was ever pushed.

**It moved exactly what the checks predicted** (`results/rebuild_20260926_diff.txt`;
"moved" means beyond the OLD row's own bar):

| deck | rows | moved | why |
|---|---|---|---|
| shilgengar | 64 | **0** (byte-identical table and cache) | nothing in its simulation changed; its VERIFIED record said so |
| azusa | 58 | **0** (byte-identical) | the same |
| rendmaw | 64 | 1 | Twitching Doll, +0.0023 → +0.0111 (§0z58). March (§0z47) stayed inside its bar |
| karlov | 64 | 10 | Necropotence +0.0076 → +0.0169 (§0z57, at the adopted 10-life floor); Felidar Sovereign and Sorin up (§0z44's priority moves); Ranger of Eos and the soul sisters up (Ranger now tutors the sisters, §0z51, and Benevolent Offering's Spirits trigger them, §0z56 -- the two are not separated); Exquisite Blood down |
| tivit | 65 | 10 | §0z44's re-rank read straight off the table: Rhystic Study +0.0049 → +0.0138, the tutors and Tempting Contract up, Sol Ring and Time Sieve down |
| lorehold | 65 | 17 | Approach −0.0003 → **+0.0666** (§0z55); Storm Herd +0.0715 → +0.0389 (§0z49, and the rest of the deck moving under it); the Archaic +0.0006 → +0.0089 (§0z54) |

**Two byte-identical decks are the result worth keeping**: two days of
shared-code changes certified by `check_unchanged_decks` in minutes, and three
hours of rebuild agreed with every one of them. That is §0z23's point measured
again, from the other side.

**One row to look at, not to act on:** Storm-Kiln Artist is now significantly
negative on win rate in lorehold (−0.0033 ±0.0027, from +0.0023 inside its
bar). It is the only MODEL-EVALUATED row in the rebuild to cross zero into
significance, and nothing done this week touches its text. **What the rebuild
did NOT do** is re-measure any staged swap or Candidate: those numbers still
carry their own dates, and the ledger says so per entry.

## 0z61. FIXED — menace

Rendmaw, Creaking Nest has "Reach, menace" (Scryfall keywords, verified
2026-09-25) and the blocking model had no menace: `damage_through`
chump-blocks your biggest attackers one blocker each. "A creature with menace
can't be blocked except by two or more creatures" (702.111b).

**MENACE is generated, not typed**: `tag_flying` reads it from the same
keywords array as FLYING, creatures only, and excludes a card whose text only
GRANTS it (Edgar's "he gains menace" is conditional). In the current lists:
Rendmaw and Gloomshrieker; Proft and Noxious Gearhulk are candidates.
`opponents.menace_of` reads it; `opponents.chump` prices each attacker at one
blocker or two and stops the most power per blocker first, the biggest first on
a tie -- which with every cost 1 IS the old rule, proved over 400 random
boards to the digit (`tests/test_menace.py`, case A). A menace flier takes two
flying-capable blockers. `combat_damage`'s assignment PLAN ignores menace, as it
already ignored the fly/ground split -- said in its docstring; resolution is
exact.

N=15,000 paired (`diagnostics/run_menace_approach.py`): **+0.0051 ±0.0014 /
+0.0123 ±0.0033** to rendmaw at T10 / T20, a commander that is harder to chump.
Only rendmaw moves (`check_unchanged_decks`). Reach stays unmodelled and
irrelevant: this model has no blockers of yours.

## 0z62. FIXED — the pod reacts to a win it can see coming

§0z55 named it: once Approach of the Second Sun has resolved and gone seventh
from the top, a real table KNOWS a win is a few draws away, and this pod did
not -- it went on weighing boards. That made Approach's +0.0666 a ceiling.

`g.known_win` (set by lorehold when Approach returns to the library; read by
`opponents.py` with `getattr`, an ARCHITECTURE protocol row) does two things:
`known_win_share` floors your share of the pod's removal AND of every opponent's
kill at `known_win_focus`, and `counter_threat` raises that card's recast to the
cap. Measured, N=15,000 paired, with the no-reaction arm reproducing §0z55's
+0.0666 exactly:

| setting | lorehold, T20 | Approach's row T10 | Approach's row T20 |
|---|---|---|---|
| no reaction | -- | +0.0341 ±0.0030 | +0.0666 ±0.0044 |
| counterspells held for it only (focus 0) | −0.0008 ±0.0005 | +0.0337 | +0.0658 |
| focus 0.5 | −0.0113 ±0.0021 | +0.0318 | +0.0553 |
| **focus 1.0 (default)** | **−0.0401 ±0.0035** | +0.0259 ±0.0028 | **+0.0265 ±0.0041** |

**The counterspell half is nearly nothing** -- Approach's threat was already
8.0, near the cap -- so the reaction is the KILLS: an opponent whose clock
comes due takes the player about to win. Approach wins 0.062 games a game at
focus 1.0 against 0.092 without the reaction. **The default, 1.0, is a
judgement -- "the whole table knows and acts on it" -- not a calibration, and
it is put to the owner.** The card is still significant at both horizons under
the harshest setting, so the finding that Approach is a real card in this deck
survives; its size depends on the pod.

## 0z63. MEASURED — every staged swap, re-measured on the rebuilt baseline

The rebuild (§0z60) refreshed the tables, not the staged swaps. Measured in
context -- each swap undone alone, the deck's other staged changes present on
both sides -- N=15,000 paired (`diagnostics/run_restage.py`,
`results/restage_20260926.txt`), on the engine at b6f957b:

| swap | T10 | T20 |
|---|---|---|
| karlov −Soulmender +Bloodthirsty Conqueror (staged) | +0.0255 ±0.0028 | +0.0266 ±0.0035 |
| karlov −Swamp +Bolas's Citadel (staged) | +0.0013 ±0.0029 | +0.0147 ±0.0042 |
| karlov −Swiftfoot Boots +Conqueror (the alternative) | +0.0278 ±0.0029 | +0.0341 ±0.0036 |
| karlov, Boots cut − Soulmender cut, same card | +0.0023 ±0.0038 | **+0.0075 ±0.0047** |
| tivit −Plains +Anointed Procession (staged) | +0.0145 ±0.0036 | +0.0191 ±0.0052 |
| azusa −Perilous Forays +Ka-Zar (staged) | +0.0033 ±0.0022 | +0.0133 ±0.0035 |
| lorehold −Blasphemous Act +Goldspan | +0.0143 ±0.0026 | +0.0119 ±0.0047 |
| lorehold −Lightning Greaves +Goldspan | +0.0011 ±0.0018 | +0.0064 ±0.0037 |
| lorehold Goldspan in Caldera's slot | −0.0030 ±0.0013 | −0.0087 ±0.0027 |

**All six staged swaps stand**, each significant at T20. The karlov cut
question (§0z36) is still answered the same way and by less: the Boots are the
better cut by +0.0075 at T20, inside the bar at T10, where it was +0.0125 on
the old baseline. **Re-measured again after §0z62** (d603578): −Blasphemous Act
+Goldspan **+0.0135 ±0.0025 / +0.0165 ±0.0045**, still significant at both;
−Greaves +0.0002 / +0.0048; Caldera still holds the five-drop slot (−0.0091);
and lorehold's two stagings, Caldera GIVEN Sunbird's +0.0226 ±0.0027 and
Sunbird's GIVEN Caldera +0.0153 ±0.0031 at T20, both stand.

## 0z64. FIXED — rendmaw has Treasures; Pitiless Plunderer measured

Rendmaw had no Treasure anywhere -- no maker in the list, and Treasure Vault's
activation unimplemented -- so Pitiless Plunderer, proposed as a diagnostic
for Ashnod's Altar, was abandoned in §0z26. Its Proposal's `implement` note
said "Treasures have been real mana since §0z6"; §0z6 is SHILGENGAR's.

**Built** (`engine.py`): `Game.treasures` is a pile, `Game.make_treasures`
fills it through `token_doublings` -- Primal Vigor and Parallel Lives, the one
function `make_tokens` now reads too, so the doubling cannot be said in one
token path and not the other (§0z4) -- and `rendmaw_mana` appends one
any-colour unit per Treasure whose owner is a `TreasureMana`: `spend` taps it
and tapping it sacrifices the token. Skullclamp's loop pops its units instead
of spending them, so it taps its Treasures itself (`tap_treasures`). The
Plunderer's trigger is in `Game.on_creature_death`; its own death is excluded
because it has left the board (the Scrap Trawler shape), and a wipe that
removes permanents one at a time makes it a FLOOR.

**Pinned** by `tests/test_treasures.py`, 11 cases and 6 mutations, exact sets.
One expectation, written before the run, was WRONG and is kept in the file:
setting the Treasure units' weight to 0 was expected to spend them before a
land and changed nothing, because `can_pay` spends the least flexible source
first and a five-colour unit loses every tie to a land before the weight is
read. `rendmaw_mana`'s docstring said the weight did it; it now says what does.

**Costs the committed list nothing**: with commander damage off,
`check_unchanged_decks` against 4591d8a is BIT-IDENTICAL on all six decks.

**Measured** (`diagnostics/run_treasures_cmdr.py`, N=15,000 paired,
`results/treasures_cmdr_20260926.txt`, with §0z65 live):

| | T10 | T20 |
|---|---|---|
| Plunderer, candidate row (Pygmy Kavu's slot) | +0.0003 ±0.0006 | +0.0014 ±0.0017 |
| −Pygmy Kavu +Plunderer, real swap | +0.0000 ±0.0006 | +0.0012 ±0.0019 |
| Ashnod's Altar row, no Plunderer | +0.0000 ±0.0005 | **−0.0017 ±0.0012** |
| Ashnod's Altar row, Plunderer in | +0.0000 ±0.0004 | −0.0012 ±0.0012 |

0.40 Treasures made and 0.32 spent a game at T20; Altar sacrifices 0.061 ->
0.059. **The Plunderer is a blank row, and the diagnostic question is
answered "not by this card"**: it makes too few Treasures to feed anything,
and the Altar's usage does not move with it. A Candidate, signal `--`.

## 0z65. FIXED — commander damage (CR 104.3j), for your commander

> 104.3j Any player who's been dealt 21 or more combat damage by the same
> commander over the course of the game loses the game.

`docs/COMP_RULES.md` recorded this as a loss condition the project did not
model at all. **Built** (`opponents.py`): `chump` takes items with a key and
reports which it blocked; `damage_through(..., unblocked=[])` returns the
attackers that got through, from the SAME blocking decision the damage total
comes from; `commander_hit` reads the commander's power among them -- by
identity, `perm.card is g.commander` -- and both of `combat_damage`'s paths add
it to the defender's `Opponent.cmdr_damage`. `_check_eliminations` removes a
player at 21, and counts `commander_damage_kills` only where life alone had
not already killed them. `commander_damage=False` restores every earlier
table.

Two choices said out loud. **Unscaled power**: `combat_damage`'s `scale`
spreads bonuses that belong to other attackers (Coat of Arms pumps Birds,
Cyberdrive animates artifacts) and lorehold's prowess is a lump, so the
commander is credited its own `power_of` -- a floor where a scale is live.
**The plan does not aim the commander**: the assignment rule (§0v) puts it
wherever its power sorts, so a pilot sending it at the player on 16 is not
modelled; the rule's value is a floor. Only YOUR commander is tracked: the
pod's commanders are folded into their clocks.

**Pinned** by `tests/test_commander_damage.py`, 10 cases and 5 mutations,
exact sets; one expectation was wrong (the attacker-blind count also broke
E, whose 1/1 partner connects) and is kept in the file. `test_menace`'s two
replacement `chump`s were updated to the keyed contract with their expected
sets unchanged.

**Measured**, rule on − rule off, same file:

| deck | won T10 | won T20 | commander kills a game (T20) |
|---|---|---|---|
| lorehold | +0.0019 ±0.0008 | **+0.0137 ±0.0036** | 0.490 |
| shilgengar | +0.0005 ±0.0003 | **+0.0071 ±0.0025** | 0.192 |
| rendmaw | +0.0001 ±0.0001 | +0.0007 ±0.0006 | 0.005 |
| karlov | +0.0001 ±0.0006 | −0.0001 ±0.0012 | 0.074 |
| tivit | +0.0005 ±0.0005 | +0.0005 ±0.0014 | 0.065 |
| azusa | bit-identical (a 0/3 commander) | | |

`opponents_killed` rises significantly in all five. **The prediction on file
was wrong about which deck**: COMP_RULES named Karlov "the sharp case",
because it grows on counters; Karlov kills 0.07 players a game this way and
wins no more. Lorehold's commander is a 5/5 FLIER, and at a
`flier_block_share` of 0.30 it connects nearly every turn -- the evasion, not
the growth, is what racks up 21. That rests on the knob, so say it with the
number. Karlov's and tivit's extra kills convert to nothing measurable: a
player killed a turn early by commander damage was, in those decks, a player
the board was about to kill anyway.

Five decks' baselines moved, so their tables were rebuilt; azusa's cache was
recorded VERIFIED on the bit-identical check. **The rebuild moved ONE row of
322 beyond its old bar** -- lorehold's Storm Herd, +0.0415 -> +0.0371, a deck
with a second way to kill a player needing its Pegasi a little less -- with 0
sign flips (`results/rebuild_20260926b_diff.txt`).

## 0z66. FIXED — triage, tiers 0 and 2; and what its back-test found

Queued item 23. `docs/TRIAGE.md` designed a cheap screen to run BEFORE a card
is implemented; `tools/triage.py` builds tiers 0 and 2 of it, `Proposal`
carries the verdict (`triage`, `triage_clauses`, `triage_note`, enforced by
`pending.check_triage`), and the `add-card` skill's step 2 is now a gate.
Pinned by `tests/test_triage.py`, 12 cases and 6 mutations, exact sets, each
written before its run and none wrong.

**Tier 0, structural.** For an implemented card, the channels through which
its deck's engine can act on it are DERIVED: a body, a land, a mana ability,
a script, any effect field off its default, its name in the engine files that
deck's fingerprint names, a multi-type line. None is BLIND; a body alone is
BODY. The first version searched every engine for the name and called
Midnight Reaper "named" in rendmaw because `shilgengar.py` dispatches on it.
**Tier 0, text**: for a Proposal, each sentence is matched against the §4
limits; BLIND only if every clause matches and the card has no body, REVIEW
otherwise. All ten live proposals read REVIEW.

**THE ACCEPTANCE TEST THE DESIGN PROPOSED WAS WRONG, and was replaced.** It
said: fail if the screen calls BLIND a card whose row is significant. Run over
the rebuilt tables it failed **32 times** (33 after the named-channel fix),
and every one was a cheap removal spell or counterspell with a POSITIVE row at
priority 1-2 -- Counterspell +0.0017 in tivit, Return to Dust +0.0040 in
karlov, Utter End +0.0023 in shilgengar. Ablation's blank is cast at the
deck's MEDIAN priority (§0j), so a dead card the pilot casts late costs less
than a blank cast on curve. **Those rows are real and measure the constants,
not the card.** The test that was built is exact instead: under CRN, a card
whose text the engine cannot see plays IDENTICALLY, seed for seed, on every
output key, to a blank matching its cost, types, body, priority and threat
(`matched_blank`). **All 56 cards called BLIND or BODY do, over 40 seeds.** A
MODEL-BLIND row that is significant is now demonstrated, 33 times, not to be
evidence about the card -- CLAUDE.md said so already; this is the check.

**Tier 2, `--smoke`**: the card against a blank in the candidates slot at
N=1000, every counter that moved, sorted by |z|, with P(cast). Sai in tivit,
seven seconds: cast in 22% of games, 0.21 Thopters a game (§0z26 had 0.155 on
an older engine). The design expected tier 0 to kill Sai and Splendid
Reclamation; it cannot and should not -- both are implemented, and they are
blanks by MECHANISM, which is tier 2's question. **The first smoke run
dropped `sai_thopters`**: a counter only the card's arm touches is absent from
the blank arm's dict, and the two arms' keys were intersected. Case H pins it.

**WHAT THE BACK-TEST FOUND ABOUT THE LABELS** (`results/triage_backtest_20260926.txt`).
The same exact test, pointed at every card `ablation.KNOWN_BLIND` lists but
the derivation finds a channel for, splits them in two:

- **33 the engine ACTS ON** -- they play differently from their matched
  blank. `KNOWN_BLIND` renders a card under MODEL-BLIND, whose header says
  "the engine does not implement the card at all", and for these that is too
  strong: tivit's six vote cards change `votes_cast`; Rhystic Study moves a
  seed's damage 72 -> 117; Enlightened Tutor, Land Tax, Dawn's Truce,
  Lurrus; shilgengar's eight Angels fly. The consequence is the one CLAUDE.md
  warns about in the other direction: a HIGH row printed under MODEL-BLIND is
  read as "not measured" when part of it is. **Not reclassified here** --
  each needs the clause that is missing named, which is PARTLY's contract,
  and that is a card-by-card judgement and a re-render of five tables.
- **13 whose channel never fired** in 40 seeds -- mostly rendmaw's
  multi-type cards (Bow of Nylea, Lignify) and name-dispatched cards whose
  branch is elsewhere in the file. Consistent with their label; not proof.

Not built, and still proposals in `docs/LEDGER_STATES.md`: PREPARED, and
splitting `Change` into SIMULATED + STAGED.

## How to read an ablation table

Moved to **`docs/READING_TABLES.md`** on 2026-09-09 — it is methodology, not
an issue, and it was the only section of this file nobody could cite by
number. `CLAUDE.md`'s "Standing findings" is the short version.
