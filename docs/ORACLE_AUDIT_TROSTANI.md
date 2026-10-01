# Oracle-text audit — Trostani v1

> **STATUS 2026-10-01 — written with the deck.** Every card in
> `edhmc/decks/trostani_v1.py` was fetched from Scryfall
> (`cards/named?fuzzy=`, with a `User-Agent`) and the module was checked
> against it field by field: **100 of 100 names resolve, 0 cost / P/T / card
> type mismatches.** Every clause of every card is sorted below into what
> `edhmc/trostani.py` MODELS, what it models in PART, and what is BLIND
> (§4: the pod's permanents are a number). The classification in
> `tools/ablation.py` (`SCRIPTED_TROSTANI`, `PARTLY_MODELLED["trostani"]`,
> `KNOWN_BLIND["trostani"]`) is this table's verdict column; the measurement
> is `KNOWN_ISSUES.md` §0z96.
>
> Open gaps, all named in the table: Elspeth's −3; Mondrak's indestructible
> counter; Lightning Greaves' haste; Greater Good at instant speed; Mimic
> Vat imprinting the pod's creatures; Luminarch's per-opponent-turn counter
> check; the destroy halves of Sundering Growth, Aura Shards, Acidic Slime,
> Beast Within; Swords, Path, Angel of Sanctions' ETB, Archon's lock; Cavern
> of Souls' coloured mode; Yavimaya Hollow's regeneration.

## The spreadsheet's spellings

Four entries in the owner's list did not match a card name exactly. Each was
resolved by Scryfall's fuzzy match and then checked by eye against the card's
text; the stored `.xlsx` carries the correction and a note on its row.

| submitted | card |
|---|---|
| Angle of Sanctions | Angel of Sanctions |
| Sylvain Caryatid | Sylvan Caryatid |
| Luminarch Ascention | Luminarch Ascension |
| `Beast Within ` (trailing space) | Beast Within |

## The commander

**Trostani, Selesnya's Voice** {G}{G}{W}{W} 2/5 — both clauses MODELLED.
"Whenever another creature you control enters, you gain life equal to that
creature's toughness": `TrostaniGame.creature_entered`, toughness read when
each trigger RESOLVES (so two Soul of Eternity tokens take 40 life to 80 to
160, `tests/test_trostani.py` A). "{1}{G}{W}, {T}: Populate": a sink after
combat and, under Seedborn Muse, on each opponent's turn. Policy: she does not
attack while a creature token is on the battlefield (`trostani_attacks`).

## Every other card

M = modelled, P = partly (the row is a FLOOR unless it says otherwise),
B = blind. "Body" means power, toughness, flying and trample from the
generated sets, attacking into the pod's blockers.

| card | | what is modelled | what is not |
|---|---|---|---|
| Soul of Eternity | M | */* = your life total (CDA, kept by every copy that does not name a P/T); encore {7}{W}{W}: one hasty copy per opponent, sacrificed at the end step | the copies attack the pod's one declared attack, not each its own opponent (§0v) |
| Bramble Sovereign | M | pays {1}{G} to copy YOUR nontoken creatures as they enter; declines legendary ones (704.5j) | the pod's creatures entering (they are a count) |
| Seedborn Muse | M | untaps everything on each opponent's turn; every instant-speed ability runs again, before the pod's removal round | untapped blockers (your creatures never block) |
| Elspeth, Sun's Champion | P | +1 three Soldiers; −7 emblem (+2/+2, flying via `flying_granted`) at 7+ loyalty and 5+ creatures | −3; the pod never attacks walkers |
| Growing Ranks | M | upkeep populate | — |
| Nesting Dovehawk | M | beginning-of-combat populate; +1/+1 counter per creature token entering (doubled by Primal Vigor) | — |
| Selesnya Eulogist | P | {2}{G} populate as often as mana and a target allow | the pod's graveyards: assumed to hold one creature card a round from pod turn 4 (`eulogist_opp_yard_turn`) |
| Luminarch Ascension | P | {1}{W} 4/4 flying Angel at 4+ counters | counters per opponent turn: a round with any life loss earns none |
| Dawn of Hope | M | {2} draw per lifegain trigger (banked, paid from left-over mana, 4 a turn); {3}{W} lifelink Soldier | paid at the next sink, not at the trigger |
| Caretaker's Talent | M | draw once each turn (opponents' turns included) on tokens entering; level 2 copies a token; level 3 +2/+2 to creature tokens | — |
| Phyrexian Processor | M | pays `processor_life` (8) on entering, never below 20 life; {4},{T} X/X Minion | — |
| Mimic Vat | P | imprints your nontoken creatures as they die; {3},{T} hasty copy, exiled at the end step | the pod's creatures dying |
| God-Pharaoh's Gift | M | beginning of combat: a 4/4 black Zombie hasty copy of a graveyard creature (CDA overridden, 707.9d) | — |
| Blade of Selves | P | equip {4}; myriad copies enter (Trostani, doublers and Caretaker see them), exiled at end of combat | each copy forced at its own opponent |
| King Darien XLVIII | M | +1/+1 to others; {3}{G}{W} counter and Soldier; sacrificed before a pod wrath for the tokens' indestructible | hexproof (tokens are not spot targets here anyway) |
| Queen Allenal of Ruadach | M | */* = creatures you control; +1 Soldier per creature-token event, applied before the doublers (616.1) | — |
| Wurmcoil Engine | M | lifelink; dies into the two Wurms | deathtouch (inert against chump blocks) |
| Sundering Growth | P | populate, held until there is a token | destroy target artifact or enchantment |
| Anointed Procession | M | doubles every token, on the one token path | — |
| Parallel Lives | M | doubles every token | — |
| Mondrak, Glory Dominus | P | 4/4; doubles every token | the indestructible-counter activation |
| Primal Vigor | M | doubles your tokens and +1/+1 counters | the OPPONENTS' doubled tokens (their board is a growth rate, §4) |
| Sun Titan | M | enters or attacks: returns a permanent card with mana value 3 or less (a fetchland comes back and cracks again) | vigilance (inert) |
| Karmic Guide | M | ETB reanimates the best creature card; echo DECLINED (`karmic_echo`) | protection from black (the pod is colourless) |
| Eternal Witness | M | ETB regrows the best card | — |
| Timeless Witness | M | ETB regrows; eternalize {5}{G}{G} as a 4/4 black Zombie | — |
| Archon of Valor's Reach | P | 5/6 flying trample | "players can't cast spells of the chosen type"; vigilance (inert) |
| Angel of Sanctions | P | 3/4 flier; embalm {5}{W} | the ETB exile |
| Acidic Slime | B | 2/2 body only | the ETB destroy; deathtouch (inert) |
| Selfless Spirit | M | 2/1 flier; sacrificed before a pod wrath, the team is indestructible (`before_wipe`, `indestructible_granted`) | the grant lasts the pod's whole round |
| Ulvenwald Hydra | M | */* = lands you control; ETB land onto the battlefield tapped | reach (inert) |
| Mirari's Wake | M | +1/+1 anthem; one extra mana per land tapped (same owner, one tap) | — |
| Sylvan Library | M | draws two more; keeps them for 4 life while that leaves 25 (`library_life_floor`), else puts them back | — |
| Alhammarret's Archive | M | doubles lifegain and every draw outside the first of the draw step | — |
| Aetherflux Reservoir | M | gains per spell cast this turn; 50 damage for 50 life while that leaves 15 (`reservoir_floor`) | — |
| Greater Good | P | sacrifice a body (power 3-12, affordable to draw), draw, discard 3 -- once a turn with ≤2 cards in hand | the instant-speed sacrifice in response to removal |
| Defense of the Heart | M | upkeep: an opponent with 3+ creatures (the pod's count) puts your two best creatures onto the battlefield | — |
| Lightning Greaves | P | shroud on Trostani | haste (never moved) |
| Aura Shards | B | — | destroy target artifact or enchantment (the pod's) |
| Chord of Calling | M | X = the best affordable creature; convoke from sick creatures precombat, any untapped after | — |
| Green Sun's Zenith | M | X = the best affordable green creature; shuffles itself back | — |
| Worldly Tutor, Enlightened Tutor, Eladamri's Call, Congregation at Dawn | M | the highest-priority target(s), to the top (best drawn first) or to hand | — |
| Sol Ring, Arcane Signet, Talisman of Unity | M | mana; the Talisman's coloured tap costs 1 life (`PAIN_ON_COLOURED_TAP`) | — |
| Birds, Elvish Mystic, Avacyn's Pilgrim, Sylvan Caryatid | M | mana creatures; Caryatid never attacks (defender) | hexproof (inert) |
| Sakura-Tribe Elder, Wood Elves, Farhaven Elf, Solemn Simulacrum, Skyshroud Claim | M | the land each fetches (Wood Elves and Claim find FOREST-typed duals, untapped); Solemn draws when it dies | — |
| Swords to Plowshares, Path to Exile, Beast Within | B | — | removal aimed at the pod |
| Wrath of God | P | symmetric wipe: your half through `destroy`, the pod's count zeroed | — (derived from the `wipe` tag) |

## Lands

Every land is modelled by its tags in the deck module. Fetchlands crack on
entering, pay 1 life and find a Forest- or Plains-typed card (the generated
FOREST / PLAINS sets); Temple Garden pays 2 life unless that would leave
less than 15 (`shock_life_floor`); Sunpetal Grove, Canopy Vista and Fortified
Village check their conditions; Selesnya Sanctuary returns a land; Blossoming
Sands gains 1 (a lifegain event); Temple of Plenty scries 1; Scattered Groves
cycles for {2} once six lands are out; Mosswort Bridge hides away the most
expensive of four cards and plays it free at total power 10. Exotic Orchard
and Reflecting Pool are WG sources and Sungrass Prairie a WG land (its {1}
filter cost is not charged). Cavern of Souls is {C} only — its coloured mode
for creature spells is a floor — and Yavimaya Hollow's regeneration is not
modelled.
