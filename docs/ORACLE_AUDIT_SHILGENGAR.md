# Oracle-text audit — Shilgengar v1

> **Read 2026-11-15 at `18be5f6`** (queue item 46; `KNOWN_ISSUES.md` §0z208).
> The staged list (`build_pending("shilgengar")`: one swap staged, -Vampiric
> Rites +Lyra, Archangel of Dawn): 64 nonland cards and the commander, 65
> entries, and the lands the engine names (Vault of the Archangel, Castle
> Locthwain, Castle Ardenvale, High Market, Phyrexian Tower). Oracle text from
> Scryfall's `cards/collection` the same day; every quoted line is
> Scryfall's. **Nothing here is measured and nothing is fixed** (§0z116's
> form, as `ORACLE_AUDIT_TIVIT.md`).
>
> **Tier 2's thirteen labels, Revel in Riches' and Tier 3's reasons were
> fixed the same day** (the owner: "fix the labels"; §0z208). The `label`
> column below is the label as audited. Tiers 1 and 4 are open.

**What is new since §0z116** (2026-10-07; the module diffed against
`98c1132`): one card, Lyra, Archangel of Dawn, and it is right -- "Whenever
you gain life, put a +1/+1 counter on each Angel you control", one counter
per lifegain event (`gain_life`). Its SCRIPTED note still says "PREVIEW
TEXT"; Scryfall's printed text is the same. The rest of the findings are
the engine's surroundings moving (item 24, POD_V4, item 44's combat).

**The data is clean**: `tools.audit_cards` reports nothing for shilgengar.

**Bottom line: 3 behaviours contradict their card's text, 13 SCRIPTED cards
carry a clause nothing implements, 9 PARTLY reasons are no longer true, and
5 piloting choices are unstated policy.** None of the three contradictions
is as large as tivit's two; the largest single gap is a stale reason --
Serra's Emissary's protection from creatures could now stop the pod's
combat kills and does not (16).

---

## Tier 1 — the engine contradicts the text

### 1. Requiem Angel sees Spirits die

> **FIXED 2026-11-15 (§0z215)**: `requiem_subtypes`=False restores the old rule; a null on this list.

    "Whenever another NON-SPIRIT creature you control dies, create a 1/1
    white Spirit creature token with flying."

`on_creature_death` tests `perm.card.name != "Spirit token"`. Two cards in
the list are Spirits by type line -- **Bloodghast** (Vampire Spirit) and
**Kokusho, the Evening Star** (Dragon Spirit) -- and each makes a Spirit
when it dies. Bloodghast is the deck's recurring fodder (`bloodghast_fodder`,
back on every landfall), so the overcount repeats. A CEILING on Requiem
Angel and on Bloodghast. The generated `_evasion.CREATURE_SUBTYPES` already
holds the answer (§0z4's rule: subtypes are data).

### 2. Emeria Shepherd and Bloodghast read landfall two ways

> **FIXED 2026-11-15 (§0z215)**: `landfall_each`=False restores the old rule; a null on this list.

`land_step` fires Bloodghast when ANY new land entered ("not the count,
which a karoo's bounce or a cracked fetch leaves unchanged", item 24) and,
twenty lines on, Emeria Shepherd only when the land COUNT rose -- the rule
the Bloodghast comment calls wrong. Emeria ("Whenever a land you control
enters") so misses the basic a cracked fetch puts in (Bloodstained Mire,
Marsh Flats), and fires once however many lands entered. Neither sees the
basic Wayfarer's Bauble puts in, which `activations` places with
`make_permanent` and no landfall. §0u's shape, inside one method. A floor
on both.

### 3. Combat lifelink is read after the counters it causes

> **FIXED 2026-11-15 (§0z215)**: `lifelink_snapshot`=False restores the old rule; a null on this list.

`combat` deals the damage, then gains life once per lifelinking attacker
at `power_of(p)` -- read AFTER each earlier gain has put Archangel of
Thune's (every creature) and Lyra, Archangel of Dawn's (every Angel)
counters on. Combat damage is simultaneous, so every lifelinker gains its
power as it was. One event per lifelinker is right (Thune's ruling: two
lifelinkers, two triggers); the amounts after the first are high by one
per earlier trigger. A small CEILING on Thune, both Lyras and the
lifelinkers.

---

## Tier 2 — SCRIPTED, with a clause nothing implements

"A CLAIM THAT THE ENGINE IMPLEMENTS THE CARD'S TEXT, so a low score is
evidence about the card." For each below the claim is false and the row is
a floor read as evidence -- §0z206's Woe Strider, thirteen times.

4. **Viscera Seer** -- "Sacrifice a creature: Scry 1." Read as a free
   outlet only; the scry is not modelled. Woe Strider's exact gap.
5. **Cartel Aristocrat** -- "Sacrifice another creature: This creature
   gains protection from the color of your choice until end of turn." An
   outlet only; the protection (from removal, from a blocker's colour) is
   not modelled.
6. **Priest of Fell Rites** -- unearth {3}{W}{B} is not modelled
   (`activations` says so; §0z197 C lists it).
7. **Resplendent Angel** -- "{3}{W}{W}{W}: Until end of turn, this creature
   gets +2/+2 and gains lifelink." No code reads it. The end-step Angel
   is modelled, at each end step (§0z153).
8. **Giada, Font of Hope** -- "{T}: Add {W}. Spend this mana only to cast an
   Angel spell." The deck module gives her no mana ability. The counters
   are modelled (`giada_counters`).
9. **Mind Stone** -- "{1}, {T}, Sacrifice this artifact: Draw a card." A
   rock only.
10. **Black Market Connections** -- "choose one or more" is always Buy
    Information alone (`upkeep`: "this undercounts the card's ceiling"), at
    the upkeep, not "your first main phase" (§0z184 finding 7, item 37).
11. **Voldaren Bloodcaster // Bloodbat Summoner** -- the transform at five
    Blood and the back face's Bat are not modelled (§0z184 finding 8, item
    37). The Blood on a nontoken death is.
12. **Elesh Norn, Grand Cenobite** -- "Creatures your opponents control get
    -2/-2": `minus_two_pod` kills the bodies of toughness 2 or less, as she
    enters and at each upkeep, and "the survivors' smaller toughness is not
    modelled" (its docstring) -- nor their power. Since A1 and A2 a body's
    power and toughness are read in every block and every attack at you.
13. **Teferi's Protection** -- modelled as one blanked event (`PROTECTION`:
    spot, A/E, wipe). "Until your next turn, your life total can't change
    and you gain protection from everything" -- the pod's whole round of
    combat, drains and kills -- is not.
14. **Flawless Maneuver** -- "If you control a commander, you may cast this
    spell without paying its mana cost." Always paid at {2}{W}
    (`_cast_response`, no `alt_costs`). A floor on when it can be held up.
15. **Massacre Wurm, Sun Titan** -- their ETBs fire on a CAST only (in
    `resolve`), so the deck's many returns -- Reya Dawnbringer, Priest of
    Fell Rites, Sun Titan, Emeria Shepherd, Seluma, the ultimate -- bring
    them back without them. Said in Avacyn of Horror's PARTLY note ("the
    floor every return path in this engine shares"), not under either
    card. Elesh Norn's static is the exception, rightly: it lives in
    `make_permanent`.

---

## Tier 3 — PARTLY reasons that are no longer true

16. **Serra's Emissary** -- "NOT: the pod's kill clocks, which are rolls
    rather than combats (§4) -- the model cannot tell which clock is one."
    It can since POD_V4: a kill comes down a route, and a COMBAT route is
    one Angel of Suffering already prevents (`angel_prevents_kill`). With
    `emissary_type` "Creature", protection would stop that kill too, and
    does not. MODELABLE, and possibly the largest floor in this file.
17. **Revel in Riches** -- "MISSING: 'whenever a creature an opponent
    controls dies, create a Treasure' -- the pod's creatures are a count,
    not deaths." It is implemented: `on_pod_creature_deaths` makes the
    Treasure (`revel_treasures`), rival-on-rival deaths included under A4.
    Tivit labels the same card SCRIPTED. Every clause is modelled; the row
    reads Smothering Tithe's knob, which is Tithe's.
18. **Angel of Despair** -- "destroy target permanent": "no opposing
    permanent (§4)". Vindicate's text, and Vindicate is a route answer
    (`ANSWERS`) in this list. MODELABLE.
19. **Angel of Serenity** -- "no opposing creature to exile": the pod's
    creatures are bodies (§0z132) and creature route pieces. MODELABLE.
20. **Angel of the Ruins** -- its ETB exile of artifacts and enchantments:
    the pod's artifact and enchantment route pieces exist. MODELABLE.
    Plainscycling was NOT; it IS since §0z226 (`engine.cycle_step`).
21. **Angelic Arbiter** -- "the pod's attacks and spells are rates": under
    A2 each seat declares its attacks (`seat_attack`). The spell half is
    still a rate.
22. **Malakir Rebirth** -- "there is no removal-in-response window": there
    is one since §0z134 (`respond_to_event`, held mana on the pod's turn).
    MODELABLE.
23. **Damn, Wrath of God** -- the derived symmetric-wipe reason says the
    pod's half "zeroes a count"; under `pod_bodies` it kills the bodies
    (`own_wipe_pod_kill`). Derived text, shared with every deck's wipes.
24. **The route answers' shared reason** (`ROUTE_ANSWER_REASON`: Path,
    Swords, Anguished Unmaking, Generous Gift, Despark, Vindicate, Mortify,
    Utter End) -- "NOT: the pod's other permanents, which are a count". The
    creatures are bodies now; the noncreature non-route permanents are
    still not objects. Half true.

---

## Tier 4 — policies the code makes and does not argue

25. **Every return picks the highest mana value** -- Reya Dawnbringer,
    Priest of Fell Rites, Emeria Shepherd, Seluma (`max(pool, key=mv)`).
    Not the best body for the board (an Angel for Shilgengar's toughness
    Blood, a death-trigger payoff before a fatty).
26. **The aristocrats step feeds at most three tokens of power 1 or less a
    turn** (`aristocrats_step`), never a real card but Bloodghast.
27. **Skullclamp equips only to toughness-1 tokens**, at most three a
    turn; Phyrexian Tower's {B}{B} is not modelled ("this engine floats no
    mana") -- a land, so no row says it.
28. **Black Market Connections' one mode** (10) is a policy as much as a
    gap: the mode choice with the life floor is the decision.
29. **Priest of Fell Rites fires above 10 life** (`your_life > 10`), a
    floor nobody derived (§0z161's lesson: a life floor is a margin over
    what the pod takes before the life comes back).

Already on record and not repeated: Vault of the Archangel's deathtouch
(§0z206 floor 1; read since §0z230); Black Market Connections' timing and
Bloodcaster's back face (§0z184, item 37; the back face modelled since
§0z229); Angel of Suffering against drain and combo kills.

---

## Every card

`label` as audited. `verdict`: **OK** the code does what the text says,
bounded as its label says; a number is the finding above.

| card | label | verdict |
|---|---|---|
| Shilgengar, Sire of Famine | commander | OK -- Blood per sacrifice, an Angel's toughness; the ultimate with finality (§0z75) |
| Agadeem's Awakening // Agadeem, the Undercrypt | PARTLY | OK as labelled |
| Angel of Despair | PARTLY | 18 |
| Angel of Serenity | PARTLY | 19 |
| Angel of Suffering | PARTLY | OK as labelled |
| Angel of the Ruins | PARTLY | 20 |
| Angelic Arbiter | PARTLY | 21 |
| Anguished Unmaking | PARTLY | 24 |
| Arcane Signet | SCRIPTED | OK |
| Archangel of Thune | SCRIPTED | OK -- a counter on each creature per lifegain event; 3 |
| Avacyn, Angel of Hope | SCRIPTED | OK -- `GRANTS_INDESTRUCTIBLE`, `is_hardy` |
| Bishop of Wings | SCRIPTED | OK -- 4 life per Angel entering, a Spirit per Angel dying |
| Black Market Connections | SCRIPTED | 10, 28 |
| Blood Artist | SCRIPTED | OK -- every death, yours (look-back, §0z76) and the pod's |
| Bloodghast | SCRIPTED | OK -- landfall return, haste at 10, can't block (§0z206); 1, 2 |
| Cartel Aristocrat | SCRIPTED | 5 |
| Damn | PARTLY | 23 |
| Dark Prophecy | SCRIPTED | OK |
| Despark | PARTLY | 24 |
| Elesh Norn, Grand Cenobite | SCRIPTED | 12 |
| Emeria Shepherd | SCRIPTED | 2, 25 |
| Emeria's Call // Emeria, Shattered Skyclave | SCRIPTED | OK -- two 4/4 Angels; the indestructible clause for non-Angels is not read (a small floor) |
| Fellwar Stone | SCRIPTED | OK -- W or B |
| Flawless Maneuver | SCRIPTED | 14 |
| Generous Gift | PARTLY | 24 |
| Giada, Font of Hope | SCRIPTED | 8 |
| Grim Haruspex | SCRIPTED | OK -- another nontoken; morph not used |
| Herald of War | SCRIPTED | OK -- attack counter, Angel and Human discount (§0z84) |
| Kokusho, the Evening Star | SCRIPTED | OK -- 5 from each, gain what was lost (§0z117); 1 |
| Lyra Dawnbringer | SCRIPTED | OK -- first strike is read in combat since §0z198; +1/+1 and lifelink to other Angels; 3 |
| Lyra, Archangel of Dawn | SCRIPTED | OK (new since §0z116); 3 |
| Malakir Rebirth // Malakir Mire | PARTLY | 22 |
| Marble Diamond | SCRIPTED | OK -- enters tapped |
| Massacre Wurm | SCRIPTED | OK cast; 15 |
| Midnight Reaper | SCRIPTED | OK -- the shared rule (§0z135) |
| Mind Stone | SCRIPTED | 9 |
| Mortify | PARTLY | 24 |
| Orzhov Signet | SCRIPTED | OK |
| Path to Exile | PARTLY | 24 |
| Phyrexian Arena | SCRIPTED | OK |
| Pitiless Plunderer | SCRIPTED | OK |
| Priest of Fell Rites | SCRIPTED | 6, 25, 29 |
| Requiem Angel | SCRIPTED | 1 |
| Resplendent Angel | SCRIPTED | 7 |
| Revel in Riches | PARTLY | 17 |
| Reya Dawnbringer | SCRIPTED | OK -- an upkeep return; 25 |
| Righteous Valkyrie | SCRIPTED | OK -- life per Angel or Cleric, +2/+2 at 47 |
| Serra's Emissary | PARTLY | 16 |
| Skullclamp | SCRIPTED | OK -- 27 |
| Smothering Tithe | SCRIPTED | OK -- the shared rule (§0z151), a knob |
| Sol Ring | SCRIPTED | OK |
| Speaker of the Heavens | SCRIPTED | OK -- sorcery-speed tap at 47 life (§0z153) |
| Sun Titan | SCRIPTED | OK cast and attacking; 15 |
| Swords to Plowshares | PARTLY | 24 |
| Talisman of Hierarchy | SCRIPTED | OK -- its 1 damage charged (§0z115) |
| Teferi's Protection | SCRIPTED | 13 |
| Twilight Shepherd | SCRIPTED | OK -- regrowth and persist (§0z84) |
| Utter End | PARTLY | 24 |
| Vindicate | PARTLY | 24 |
| Viscera Seer | SCRIPTED | 4 |
| Voldaren Bloodcaster // Bloodbat Summoner | SCRIPTED | 11 |
| Wayfarer's Bauble | SCRIPTED | OK; its land fires no landfall, 2 |
| Wrath of God | PARTLY | 23 |
| Youthful Valkyrie | SCRIPTED | OK |
| Zulaport Cutthroat | SCRIPTED | OK -- yours only |
