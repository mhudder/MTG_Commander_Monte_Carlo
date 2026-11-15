# Oracle-text audit — Azusa v1

> **Read 2026-11-15 at `1511c4e`** (queue item 46; `KNOWN_ISSUES.md` §0z209).
> The staged list (`build_pending("azusa")`: -Perilous Forays +Ka-Zar of the
> Savage Land, and two Forests for Fabled Passage and Evolving Wilds): 58
> nonland cards, the commander and the five scripted fetches, 64 entries,
> and the utility lands. Oracle text from Scryfall's `cards/collection` the
> same day; every quoted line is Scryfall's. **Nothing here is measured and
> nothing is fixed** (§0z116's form, as the tivit and shilgengar audits).
> Azusa has no `.xlsx`.

**What is new since §0z116** (2026-10-07; the module diffed against
`98c1132`): Ka-Zar of the Savage Land, Fabled Passage and Evolving Wilds,
all three right -- Zabu and its landfall counter (doubled by Greenwarden
and Chocobo, as a triggered ability should be); `fetch_tapped` and
`fetch_untap4` (untapped at four lands) in `crack_fetch`.

**The data is clean**: `tools.audit_cards` reports nothing for azusa.

**The landfall core is careful**: one hook (`land_entered`), the doublers
stacking as instances, not multiplying (`reps`), the trigger list read
before any trigger resolves (§0z101), Horn of Greed outside the doubled
loop (§0z41), Ashaya's creature-lands entering and dying as lands. The
findings are at the edges of it.

**Bottom line: 5 behaviours contradict their card's text -- two of them,
Genesis Wave (a tutor in place of a dig) and Animist's Awakening (four
lands where the text averages 1.7) by a large margin -- 4 SCRIPTED cards
carry a clause nothing implements, 8 utility lands have no code at all, 5
reasons are no longer true, and 6 piloting choices are unstated policy.**

---

## Tier 1 — the engine contradicts the text

### 1. Genesis Wave tutors the library instead of revealing its top

> **FIXED 2026-11-15 (§0z210)**: the top six revealed, every permanent of
> mana value 6 or less put in, the rest milled; `genesis_wave_reveal=False`
> restores the old rule. What it puts in fires its ETB since §0z212 (item 3).

    "Reveal the top X cards of your library. You may put any number of
    permanent cards with mana value X or less from among them onto the
    battlefield. Then put all cards revealed this way that weren't put onto
    the battlefield into your graveyard."

`AzusaGame.wave(6, count=3)` sorts the WHOLE library's permanents of mana
value 6 or less by mana value and takes the three biggest. The text reveals
six cards and keeps the permanents among THOSE -- in this list 4.6 of six
on average (76 of 99 cards are permanents of mana value 6 or less), 2.1
nonland and 2.5 lands, each land a landfall trigger -- and mills the rest.
So the model is a three-card tutor for the deck's best permanents where
the card is a top-six dig: a CEILING on what comes in, a FLOOR on how many
and on the landfall, and the graveyard half missing. `count=3` is not in
the text at all. And the creatures it puts in fire no ETB (item 3).

### 2. Animist's Awakening takes the first four lands anywhere

> **FIXED 2026-11-15 (§0z211)**: the lands among the top four, the rest
> bottomed on their own stream, untapped with spell mastery;
> `animist_reveal=False` restores the old rule.

    "Reveal the top X cards of your library. Put all land cards from among
    them onto the battlefield tapped and the rest on the bottom of your
    library in a random order. Spell mastery — If there are two or more
    instant and/or sorcery cards in your graveyard, untap those lands."

`wave(4, lands_only=True)` takes `next(c for c in self.library if
c.is_land)` four times -- the first four LANDS, however deep -- so X=4 is
always four lands where the text gives the lands among four cards (1.7 on
average: 41 lands in 99). The nonlands are not put on the bottom, and spell
mastery's untap is not read. A CEILING, by roughly double; fixed X is
§0z197 A7's convention.

### 3. A tutored or Waved creature fires no ETB

> **FIXED 2026-11-15 (§0z212)**: `tutor_creature` and `wave_enter` queue
> the ETB, fired once the spell has left the stack; `tutor_etb=False`
> restores the old rule. A tutored Springheart is not bestowed.

`AzusaGame.etb`'s docstring: split out of `resolve` "to close queued item
16", because "`make_permanent` is reached from six other places
(Springheart's token copy, Genesis Wave, Finale of Devastation, Green Sun's
Zenith, Chord of Calling, Woodland Bellower, Titania, Nissa's ultimates)".
Only two call it: `resolve` (a cast) and Springheart's copy -- item 16 was
the copy alone (HISTORY, "item 16"). `tutor_creature` (Green Sun's Zenith,
Chord of Calling, Woodland Bellower) and `wave` (Genesis Wave) put the
creature in with `make_permanent` and nothing else. In the list: Eternal
Witness and Nissa, Vastwood Seer within Zenith's and Chord's reach (Nissa
is legendary, so not Bellower's); Titania, Ka-Zar, Bane of Progress and
Woodland Bellower besides within the Wave's. A
FLOOR on the four tutors, and a docstring that says otherwise.

### 4. Craterhoof's pump reaches creatures that enter after it

"Creatures you control gain trample and get +X/+X until end of turn": the
creatures you control as it resolves. `craterhoof_bonus` is read by
`_pump` for every permanent for the rest of the turn, so a Beast, Badger
or Insect made by a later land drop gets it too. A small CEILING.

### 5. Bane of Progress spares your tokens

"Destroy all artifacts and enchantments": the ETB removes your artifact
and enchantment PERMANENTS, but not the Treasures (`TreasureMana` in
`bonus_mana`), Clues (`self.clues`) or Food that the engine keeps off the
board. They are artifacts and die too. A small CEILING on the card's own
cost.

---

## Tier 2 — SCRIPTED, with a clause nothing implements

> **LABELS FIXED 2026-11-15**: items 6, 7 and 9 are PARTLY_MODELLED in
> `tools/ablation.py`, each reason citing its item; item 8 is fixed
> (§0z213). Tier 3's reasons 10-14 are corrected the same day.

6. **Journey of Discovery** -- modelled as its first mode, two basics to
   hand. NOT: "You may play up to two additional lands this turn", nor
   entwine {2}{G} -- in a deck whose whole engine is land drops, the second
   mode is the one an Azusa pilot casts it for. A floor.
7. **Nylea's Intervention** -- three Forests to hand (fixed X=3, §0z197
   A7). The text is "up to X LAND cards" (a utility land is one), and the
   other mode, "deals twice X damage to each creature with flying", is
   MODELABLE against the pod's flier bodies (A1, A2) and not modelled.
8. **FIXED 2026-11-15 (§0z213)**: the shared rule, `engine.convoke_pool`
   and `engine.x_plan`, as trostani. Was: **Chord of Calling** -- convoke and its X (fixed at 4, a flat
   {4}{G}{G}{G}): §0z197 A7's named defect, the same card under
   trostani's convoke and X plan. Plus item 3.
9. **Sylvan Awakening** -- reach and indestructible are carried in
   `animate_lands` and read by nothing but `trample_of` (§0z206 floor 2).
   The 2/2s, haste and the duration through the pod's round are modelled.

---

## Tier 2b — utility lands with no code

Lands carry no SCRIPTED/PARTLY label, so no table row says this. Eight of
the list's lands have an activated ability no code reads; each is a land
that taps for mana and nothing else here:

| land | its ability | why it matters here |
|---|---|---|
| Strip Mine, Wasteland, Ghost Quarter, Tectonic Edge | "{T}, Sacrifice: destroy target (nonbasic) land" | the pod has no lands (§4), but the SACRIFICE is a land death: Titania's 5/3, and a replay through Crucible, Ramunap or Greenwarden -- the deck's own loop. Ghost Quarter on your own land also fetches a basic: two landfall triggers |
| Dust Bowl | "{3}, {T}, Sacrifice a land: destroy target nonbasic land" | the same outlet, any land |
| Buried Ruin | "{2}, {T}, Sacrifice: return target artifact card" | Sol Ring, Horn of Greed, Crucible back |
| Homeward Path, Scavenger Grounds | creatures home; exile graveyards | nothing here, rightly |

Wired, for contrast: the fetches, Crystal Vein, Petrified Field, Eye of
Ugin, Eldrazi Temple, Nykthos, Temple of the False God, Scene of the Crime
(`land_died` is called on each of their deaths). Crop Rotation's and Sylvan
Scrying's PARTLY reasons name Strip Mine and Wasteland as blind "for the
pod's lands"; the self-sacrifice half is not the pod's.

---

## Tier 3 — reasons that are no longer true

10. **Ulamog, the Infinite Gyre** -- "the cast trigger 'destroy target
    permanent' (an opponent's permanent, BLIND under §4)". Vindicate's text,
    and the pod's route pieces have been permanents since POD_V4: MODELABLE,
    as shilgengar's Angel of Despair (§0z208).
11. **Bane of Progress** -- "opponents own no permanent objects in this
    project (§4)". Their artifact and enchantment route pieces do; MODELABLE,
    as Angel of the Ruins (§0z208). The sidedness the reason says is
    "removed" is now expressible.
12. **Kozilek, Butcher of Truth** -- "Annihilator is an abstract-count
    approximation": under `pod_bodies` it sacrifices the defender's four
    smallest bodies, each a death (`kill_pod_count`). Ulamog's reason says
    the same. What is still approximate: the defender is the opponent on
    the least life, not the one Kozilek attacked, and its route pieces are
    never among the four.
13. **`crack_fetch`'s docstring** -- "the two true fetches (paying 1 life,
    unmodelled)": the life is charged (`LAND_RULES` "fetch", §0z115).
14. **Mind's Eye** (KNOWN_BLIND, no reason printed) -- "Whenever an
    opponent draws a card, you may pay {1}": the same shape as Smothering
    Tithe, which `tithe_treasures` models as a rate (§0z151). Blind is
    honest; it is MODELABLE by Tithe's rule.

---

## Tier 4 — policies the code makes and does not argue

15. **Eternal Witness and Regrowth take the highest mana value** in the
    graveyard -- a land only if nothing else is there, which in a deck
    that bins lands on purpose (Realms Uncharted) is a choice.
16. **Tireless Provisioner always makes a Treasure** (`provisioner_
    treasure`), never Food.
17. **Annihilator's victim** is the opponent on the least life (item 12).
18. **Nissa, Sage Animist never uses her -2** (said in her docstring).
19. **Quirion Ranger never untaps an attacker to block** (§0z206).
20. **Horn of Greed's "that player draws"** is given to you only; the
    pod has no hand to draw into (§4), so the symmetric half -- the cost
    -- is not charged. A small ceiling.

Already on record and not repeated: Memory Jar (BLIND, item 37); Chord's X
(§0z197 A7); Storm Cauldron's pod half; Kozilek's and Ulamog's graveyard
shuffle.

---

## Every card

`label` as audited. `verdict`: **OK** the code does what the text says,
bounded as its label says; a number is the finding above.

| card | label | verdict |
|---|---|---|
| Azusa, Lost but Seeking | commander | OK -- two more land drops (`land_drops_for_turn`) |
| Abundance | SCRIPTED | OK -- every draw replaced (`engine.abundance_draw`) |
| Ancient Greenwarden | SCRIPTED | OK -- lands from the yard, every landfall ability one more time, reach as a blocker |
| Animist's Awakening | SCRIPTED | 2 |
| Ashaya, Soul of the Wild | SCRIPTED | OK -- creature-lands enter and die as lands |
| Augur of Autumn | SCRIPTED | OK -- lands from the top, coven creature casts |
| Avenger of Zendikar | SCRIPTED | OK cast; Plant counters on landfall; 3 |
| Bane of Progress | PARTLY | 5; 11 reason fixed |
| Beast Within | PARTLY | OK (a route answer) |
| Chord of Calling | SCRIPTED | 3, 8 fixed (§0z212, §0z213) |
| Courser of Kruphix | SCRIPTED | OK |
| Craterhoof Behemoth | SCRIPTED | 4 |
| Crop Rotation | PARTLY | OK as labelled; Tier 2b |
| Crucible of Worlds | SCRIPTED | OK |
| Cultivate | SCRIPTED | OK |
| Eternal Witness | SCRIPTED | OK cast; 3, 15 |
| Evolving Wilds | SCRIPTED | OK (new) |
| Exploration | SCRIPTED | OK |
| Fabled Passage | SCRIPTED | OK (new) -- untapped at four lands |
| Genesis Wave | SCRIPTED | 1, 3 |
| Greater Good | BLIND | OK as labelled |
| Green Sun's Zenith | SCRIPTED | OK -- fixed X 3, shuffled back (§0z118); 3 |
| Greensleeves, Maro-Sorcerer | SCRIPTED | OK |
| Hall of Gemstone | BLIND | OK as labelled |
| Harmonize | SCRIPTED | OK |
| Horn of Greed | SCRIPTED | OK -- on a land PLAYED, outside the doubled loop (§0z41); 20 |
| Journey of Discovery | PARTLY (was SCRIPTED) | 6 |
| Ka-Zar of the Savage Land | SCRIPTED | OK (new) -- lands from the top, Zabu |
| Kodama's Reach | SCRIPTED | OK |
| Kozilek, Butcher of Truth | PARTLY | 17; 12 reason fixed |
| Krosan Grip | PARTLY | OK (a route answer) |
| Lotus Cobra | SCRIPTED | OK |
| Memory Jar | BLIND | OK as labelled (item 37) |
| Mind's Eye | BLIND | 14 noted in its comment |
| Mole Man, Moloid Master | SCRIPTED | OK -- lands from the yard, Moloids, the mill a policy (§0z101) |
| Momentous Fall | SCRIPTED | OK |
| Mossborn Hydra | SCRIPTED | OK -- doubled last (`_landfall_last`) |
| Nissa, Vastwood Seer // Nissa, Sage Animist | SCRIPTED | OK cast; flips at seven lands; 3, 18 |
| Nylea's Intervention | PARTLY (was SCRIPTED) | 7 |
| Oracle of Mul Daya | SCRIPTED | OK |
| Quirion Ranger | SCRIPTED | OK -- 19 |
| Ramunap Excavator | SCRIPTED | OK |
| Rampaging Baloths | SCRIPTED | OK |
| Realms Uncharted | SCRIPTED | OK -- the pod bins your best two (the owner, §0z153) |
| Regrowth | SCRIPTED | OK -- 15 |
| Scute Swarm | SCRIPTED | OK -- copies at six lands, snapshotted |
| Seek the Horizon | SCRIPTED | OK |
| Seer's Sundial | SCRIPTED | OK |
| Sol Ring | SCRIPTED | OK |
| Springheart Nantuko | SCRIPTED | OK -- bestow and copies, the copy's ETB (item 16) |
| Storm Cauldron | PARTLY | OK as labelled |
| Sylvan Awakening | PARTLY (was SCRIPTED) | 9 |
| Sylvan Library | SCRIPTED | OK -- the shared rule |
| Sylvan Scrying | PARTLY | OK as labelled; Tier 2b |
| Terastodon | PARTLY | OK (a route answer) |
| Terramorphic Expanse | SCRIPTED | OK; 13 |
| Tireless Provisioner | SCRIPTED | OK -- 16 |
| Tireless Tracker | SCRIPTED | OK -- a counter per Clue cracked |
| Titania, Protector of Argoth | SCRIPTED | OK cast; every `land_died` a 5/3; 3; Tier 2b |
| Traveling Chocobo | SCRIPTED | OK |
| Ulamog, the Infinite Gyre | PARTLY | 10, 12 reasons fixed |
| Windswept Heath | SCRIPTED | OK; 13 |
| Wooded Foothills | SCRIPTED | OK; 13 |
| Woodland Bellower | SCRIPTED | OK cast; its find fires its ETB since §0z212 (was 3) |
