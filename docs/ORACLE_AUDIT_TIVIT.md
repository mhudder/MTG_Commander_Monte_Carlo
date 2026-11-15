# Oracle-text audit — Tivit v1

> **Read 2026-11-15 at `1e69b49`** (queue item 46; `KNOWN_ISSUES.md` §0z207).
> The staged list (`build_pending("tivit")`, nothing staged): 64 nonland
> cards, the commander and the two scripted lands, 67 entries. Oracle text
> from Scryfall's `cards/collection` the same day; every quoted line is
> Scryfall's. **Nothing here is measured and nothing is fixed**: this is the
> list, ordered by how much of a card the engine gets wrong, for the owner to
> choose from (§0z116's form).

**Why a second audit.** §0z116 (2026-10-07) read every engine against the
oracle text of all seven lists, and its findings are fixed. Tivit's list has
not changed since (diffed against `98c1132`). What has changed is the engine
around it -- item 24's pod bodies and routes (§0z132-§0z140), POD_V4, and
item 44's combat (§0z198-§0z204) -- and that turned several "the pod is a
count" reasons into statements about a pod that no longer exists. This
audit re-reads the 67 entries against the code as it is.

**The data is clean**: `tools.audit_cards` reports nothing for tivit (costs,
P/T, types, flying, indestructible, haste, lifelink, lands; §0z206).

**Bottom line: 6 behaviours contradict their card's text, 11 SCRIPTED
cards carry a clause nothing implements or a knob their label does not
say, 8 cards' stated reasons are no longer true, and 7 piloting choices
are unstated policy.** The three largest,
by how much of the card they change: Lightning Greaves' shroud coexisting
with five targeted blinks (1), Tempting Contract's extra Treasure every
upkeep (2), and Kambal's first ability (7).

---

## Tier 1 — the engine contradicts the text

### 1. Lightning Greaves' shroud and five TARGETED blinks, both at once

    Lightning Greaves   "Equipped creature has haste and shroud. (It can't
                         be the target of spells or abilities.)"
    Ephemerate          "Exile TARGET creature you control, then return it"
    Soulherder          "you may exile another TARGET creature you control"
    Teleportation Circle "exile up to one TARGET artifact or creature"
    Conjurer's Closet   "you may exile TARGET creature you control"
    Displacer Kitten    "exile up to one TARGET nonland permanent"

`opponents.commander_shrouded` makes Tivit an illegal target for the pod's
removal for as long as Greaves is on the battlefield (`shroud_sources`,
`tivit.TivitGame.__init__`), and `blink_tivit` blinks Tivit for all five
cards regardless. A shrouded Tivit cannot be targeted by YOUR abilities
either. A pilot gets one or the other: Greaves on Tivit (protection, and no
blink but Deadeye Navigator's, whose "{1}{U}: Exile this creature" does not
target), or Greaves moved for {0} at sorcery speed (blinks, no shroud). The
model takes both -- a CEILING on Greaves and on all five blink cards. The
fix is a policy (where Greaves sits), so it is the owner's: say it, then
gate `blink_tivit`'s targeted sources on it.

### 2. Tempting Contract makes one Treasure too many, every upkeep

    "At the beginning of your upkeep, each opponent may create a Treasure
    token. For each opponent who does, you create a Treasure token."

`tivit.upkeep` calls `make_token(g, "Treasure", V.tempting_offer(g))`, and
`voting.tempting_offer` returns `1 + takers` -- the TEMPTING OFFER rule
("you get it once, plus once more per opponent"), which this card is not.
Tempting Contract gives you exactly `takers`. At `tempting_offer_rate` 0.5
that is 2.5 Treasures an upkeep where the text gives 1.5, and with Academy
Manufactor each is three artifacts. A CEILING on the card's row; its
SCRIPTED label claims the text.

### 3. Grudge Keeper's loss lands on one player

    "Whenever players finish voting, each opponent who voted for a choice
    you didn't vote for loses 2 life."

`voting._vote_payoffs` deals `2 * votes_against` with `each=False`, which
is `damage_single`: the whole amount at the opponent closest to dying.
Under the adversarial default all three vote against, so one player loses 6
where the text has three players lose 2. Concentration finishes players the
text would not: a ceiling on kills, a floor on spread damage.

### 4. Converting the pile counts Kambal as a drain

`convert_the_pile` sacrifices the whole pile when any of five "drains" is
out, and Kambal, Profiteering Mayor is one of them. Kambal's triggers are
on tokens ENTERING; `sacrifice_tokens` does not read it. With Kambal the
only one out, the pilot throws the pile away for nothing and returns before
the Time Sieve branch ("`g.extra_turns += 5`"). A policy defect, in the
floor direction.

### 5. The pile is sacrificed for free

The same branch sacrifices every Clue, Food and Powerstone. Clue: "{2},
Sacrifice this artifact: Draw a card." Food: "{2}, {T}, Sacrifice". A
Powerstone has no sacrifice ability at all ("{T}: Add {C}. This mana can't
be spent to cast a nonartifact spell."). Only Treasures sacrifice for free.
A CEILING, but a small one in practice: the branch runs only once the loop
reached `combo_cap`, where the Treasures alone are usually lethal.

### 6. Custodi Squire ignores its own vote

    "Will of the council — ... each player votes for an artifact, creature,
    or enchantment card in your graveyard. Return each card with the most
    votes or tied for most votes to your hand."

`resolve`'s `custodi` branch calls `V.council(g)` and discards the result,
then returns your highest-priority card. Outvoted by the adversarial
default (every opponent votes for your worst card), the text returns THAT
card, and on a tie both. A CEILING under the default `opp_vote_policy`.

---

## Tier 2 — SCRIPTED, with a clause nothing implements

`tools/ablation.py` says of SCRIPTED_TIVIT: "A CLAIM THAT THE ENGINE
IMPLEMENTS THE CARD'S TEXT, so a low score is evidence about the card." For
each card below the claim is false, and the row is a floor read as evidence.

7. **Kambal, Profiteering Mayor** — "Whenever one or more tokens your
   opponents control enter, for each of them, create a tapped token that's a
   copy of it. This ability triggers only once each turn." No code reads
   it (`tools.where --card` finds only the second ability, in
   `on_tokens_created`). Four cards in this list hand the pod tokens --
   Tempting Contract, Tempt with Bunnies, Master of Ceremonies, An Offer
   You Can't Refuse -- and each copy is a token you create (Kambal's second
   ability, Mirkwood Bats, Academy Manufactor and Anointed Procession on a
   Treasure). A floor, possibly a large one.
8. **Nadier's Nightblade, Disciple of the Vault, Marionette Master** -- the
   deaths they never hear. `TivitGame.on_creature_death` is `pass` ("no
   death payoffs in this list"), and `opponents.destroy` reports every
   death of yours through it. So a creature TOKEN that dies in combat (A1,
   A2: §0z198, §0z199), to a wipe or to Promise of Loyalty never reaches
   Nadier's Nightblade ("whenever a token you control leaves the
   battlefield"), and an ARTIFACT creature (Academy Manufactor, Cyberdrive
   Awakener) never reaches Disciple or Marionette. Nor does a noncreature artifact the pod's artifact removal
   destroys (`opponents` A/E removal calls `destroy`; tivit has no
   `artifact_died`). Only tivit's own sacrifices and Coercive Portal's
   carnage call `_artifacts_left`. A floor on all three, and the comment
   is wrong.
9. **Soulherder** — "Whenever a creature is exiled from the battlefield, put
   a +1/+1 counter on this creature." Not implemented: every blink in the
   deck exiles a creature. Only the end-step blink is. A floor.
10. **Tamiyo's Journal** — "{T}, Sacrifice three Clues: Search your library
    for a card". Only the upkeep investigate is implemented (`upkeep`); the
    Clues are cracked for cards instead (`crack_clues`). A floor.
11. **Havengul Laboratory // Havengul Mystery** — its own docstring
    (`havengul_end_step`) says the transform is "NOT MODELLED, so neither is
    the Mystery's '{T}, Pay 1 life: Add {B}'" and the return of a creature
    card. SCRIPTED anyway. A floor.
12. **Cyberdrive Awakener** — "Other artifact creatures you control have
    flying." Not read: `opponents.flying_of` asks the card's tag and named
    conditions, and tivit defines no `flying_granted`. The ETB burst is
    `4 x` the token piles only, so it counts summoning-sick tokens (a
    ceiling, §0z197 C) and skips the real noncreature artifacts the text
    animates (Sol Ring, the signets, Contract, Journal, Portal: a floor).
    Bounded both ways -- PARTLY by this file's own rule.
13. **Model of Unity** — "you and each opponent who voted for a choice you
    voted for may scry 2." `voting._vote_payoffs` increments `unity_scrys`
    and nothing reads it: the comment says "a small draw-quality nudge",
    and there is none. The mana half is modelled. A floor.
14. **Monologue Tax** — a flat `monologue_tax_rate` (2) Treasures a round,
    in the upkeep. That is Rhystic Study's shape -- a social rate this model
    cannot see -- and Rhystic Study is KNOWN_BLIND/BLIND_BUT_LIVE for it
    ("The row is that knob, not the card"). Two cards, one shape, two
    labels (§0u). Say the knob, or move it.
15. **Mechanized Production** — "create a token that's a copy of enchanted
    artifact. Then if you control eight or more artifacts with the same
    name as one another, you win." Modelled as a Treasure each upkeep and
    a win at eight Treasures. The enchanted artifact is assumed to be a
    Treasure that is never spent (if it were, the Aura would fall off), and
    eight Clues or eight Food -- which Academy Manufactor makes in step with
    the Treasures -- do not win. Bounded both ways; the target is a policy
    (§ Tier 4).

---

## Tier 3 — PARTLY reasons that are no longer true

Each card is correctly PARTLY; the stated reason is the pod before item 24
or item 44. Each is now MODELABLE, which is a different claim from modelled.

16. **Bite of the Black Rose** — "the pod's creatures are a count with no
    toughness". They are bodies with toughness since §0z132; sickness
    (-2/-2) is Massacre Wurm's `minus_2` shape.
17. **Capital Punishment** — "the pod has no creature objects". Tyrant's
    Choice already sacrifices them (`kill_pod_count`, §0z153); a death vote
    is the same call. And `resolve`'s comment says the same.
18. **Trial of a Time Lord** — chapters I-III "exile target nontoken
    creature an opponent controls": "the pod's creatures are a count". A
    body can be exiled now.
19. **Promise of Loyalty** — "their creatures are a count and chip damage
    still reads it". Under A2 the pod declares attacks with bodies, so a
    vow ("can't attack you") on each opponent's kept creature is a filter on
    a declaration.
20. **Ghostly Prison, Propaganda** — "NOT: declared attacks -- the pod's
    combat is a damage share". The pod declares attacks under A2. What is
    still true is §0z205's reason: the pod has no mana to pay with, so
    `attack_tax_deflect` stands in.
21. **Expropriate** — the reason is right; `resolve`'s comment says "which
    is why it is in KNOWN_BLIND". It is PARTLY.
22. **Trap the Trespassers** (KNOWN_BLIND) — stun counters on creatures you
    don't control. Blind is right; it is modelable since the pod's bodies
    attack (A2).

---

## Tier 4 — policies the code makes and does not argue

Each is a piloting choice. None is wrong by the text; each decides a row.

23. **Lieutenants of the Guard** — you vote strength (+1/+1 counters) and
    the adversarial pod votes numbers (Soldier tokens). In this deck tokens
    are the better outcome (Kambal, Mirkwood Bats, Anointed Procession), so
    "against you" hands you the better half: with fewer votes than the pod
    (one or two), the model gives more tokens than a pod voting against you
    would. Messenger Jays has the same mapping (feather vs a loot); there
    the better half is not obvious.
24. **Marionette Master** — fabricate 3 is always counters (`run_etb`),
    and its power is a constant 4.0 in `artifact_left_drain`. Three Servos
    are three artifacts and three tokens to every payoff above.
25. **Disciple of the Vault spreads, Marionette Master focuses** — both say
    "target opponent". Disciple is a 1/living share of every opponent
    (`disciple_share`), Marionette all at the opponent closest to dying.
    Two rules for one targeting (§0u).
26. **Master of Ceremonies** — each opponent's choice is a uniform roll
    (`ceremonies{i}`), not `opp_vote_policy`. The pod's matching Treasure,
    Citizen or card is not given to it (a ceiling), and Kambal does not
    copy its Citizen (item 7, a floor).
27. **Tempt with Bunnies** — the opponents who accept get a Rabbit and a
    card that the pod never receives (a ceiling) and Kambal never copies
    (a floor). `tempting_offer_rate` (0.5).
28. **Illusion of Choice** with Grudge Keeper — under vote control every
    vote is yours and `against` is 0, so Grudge Keeper never fires. A pilot
    choosing the pod's votes can vote them against themselves, the card
    pair's known line. A floor.
29. **A blinked Tivit still attacks** — `blink_tivit` keeps the same
    Permanent, so a Tivit blinked in the first main phase (Ephemerate,
    Displacer Kitten) is not summoning sick and keeps Greaves. A returned
    object is new, sick unless Greaves is re-equipped. A small ceiling.

Already on record and not repeated: Tivit's ward {3} (§0z197 C), Torment of
Hailfire's fixed X and life branch (§0z197 A7, BLIND_BUT_LIVE), Rhystic
Study's rate, Expropriate's money votes, Magister of Worth's grace for the
pod.

---

## Every card

`label` is `tools/ablation.py`'s. `verdict`: **OK** the code does what the
text says, bounded as its label says; a number is the finding above.

| card | label | verdict |
|---|---|---|
| Tivit, Seller of Secrets | commander | OK -- dilemma on ETB and on connecting (§0z91); extra vote. Ward {3} not modelled (§0z197 C). 1, 29 |
| Academy Manufactor | SCRIPTED | OK -- one of each, per token (`make_token`) |
| An Offer You Can't Refuse | PARTLY | OK; its two Treasures go to the pod -- Kambal, 7 |
| Arcane Signet | SCRIPTED | OK |
| Azorius Signet | SCRIPTED | OK |
| Ballot Broker | SCRIPTED | OK -- `voting.my_votes` |
| Bite of the Black Rose | PARTLY | 16 |
| Brago's Representative | SCRIPTED | OK -- `voting.my_votes` |
| Capital Punishment | PARTLY | 17 |
| Coercive Portal | SCRIPTED | OK -- homage takes ties; carnage per §0z117, every pile and artifact heard |
| Conjurer's Closet | SCRIPTED | 1 |
| Council's Judgment | PARTLY | OK -- `voting.judgment` (§0z138) |
| Counterspell | PARTLY | OK -- held up on the pod's turn (§0z134) |
| Custodi Squire | SCRIPTED | 6 |
| Cyberdrive Awakener | SCRIPTED | 12 |
| Damn | PARTLY | OK |
| Deadeye Navigator | SCRIPTED | OK -- untargeted, so the one blink Greaves does not stop |
| Demonic Tutor | SCRIPTED | OK -- highest priority |
| Dimir Signet | SCRIPTED | OK |
| Disciple of the Vault | SCRIPTED | 8, 25 |
| Displacer Kitten | SCRIPTED | 1; on cast, countered or not (§0z151) |
| Dovin's Veto | PARTLY | OK |
| Ephemerate | SCRIPTED | 1; rebound at the next upkeep |
| Expropriate | PARTLY | 21 |
| Farewell | PARTLY | OK -- creatures mode; your token piles stay (a mode choice) |
| Ghostly Prison | PARTLY | 20 |
| Grudge Keeper | SCRIPTED | 3, 28 |
| Havengul Laboratory // Havengul Mystery | SCRIPTED | 11 |
| Idyllic Tutor | SCRIPTED | OK |
| Illusion of Choice | SCRIPTED | OK -- vote control for the turn, draw; 28 |
| Kambal, Profiteering Mayor | SCRIPTED | 7; its second ability once per batch (§0z118) |
| Lieutenants of the Guard | SCRIPTED | 23 |
| Lightning Greaves | SCRIPTED | 1 |
| Magister of Worth | PARTLY | OK -- condemnation takes ties; grace returns fire no ETB |
| Marionette Master | SCRIPTED | 8, 24, 25 |
| Master of Ceremonies | SCRIPTED | 26 |
| Mechanized Production | SCRIPTED | 15 |
| Messenger Jays | SCRIPTED | OK -- counters, draw and discard (§0z153); 23 |
| Mirkwood Bats | SCRIPTED | OK on the piles and creature tokens made; a sacrificed creature token (Promise of Loyalty) is missed, 8 |
| Model of Unity | SCRIPTED | 13 |
| Monologue Tax | SCRIPTED | 14 |
| Muddle the Mixture | PARTLY | OK; transmute not used |
| Nadier's Nightblade | SCRIPTED | 8 |
| Orzhov Signet | SCRIPTED | OK |
| Path to Exile | PARTLY | OK |
| Plea for Power | SCRIPTED | OK -- time loses ties |
| Promise of Loyalty | PARTLY | 19 |
| Propaganda | PARTLY | 20 |
| Revel in Riches | SCRIPTED | OK -- every pod body that dies, rival combat included (§0z200); a win at your upkeep |
| Rhystic Study | BLIND (live) | OK as labelled |
| Rogue's Passage | SCRIPTED | OK -- `opponents.rogues_passage` |
| Sadistic Shell Game | SCRIPTED | OK -- one kill per player, biggest board |
| Sol Ring | SCRIPTED | OK |
| Soulherder | SCRIPTED | 1, 9 |
| Split Decision | PARTLY | OK as labelled |
| Swords to Plowshares | PARTLY | OK |
| Tamiyo's Journal | SCRIPTED | 10 |
| Teleportation Circle | SCRIPTED | 1 |
| Tempt with Bunnies | SCRIPTED | 27 |
| Tempting Contract | SCRIPTED | 2 |
| Time Sieve | SCRIPTED | OK -- once a turn, five artifacts (piles first, then `sieve_real_fuel`) |
| Torment of Hailfire | BLIND (live) | OK as labelled |
| Trap the Trespassers | BLIND | 22 |
| Trial of a Time Lord | PARTLY | 18 |
| Tyrant's Choice | SCRIPTED | OK -- the owner's vote rule (§0z153) |
| Vault 11: Voter's Dilemma | PARTLY | OK -- `voting.dilemma_vault` (§0z138) |
| Void Rend | PARTLY | OK |
