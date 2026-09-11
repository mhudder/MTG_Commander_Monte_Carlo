# Oracle-text audit — Lorehold v16

> **STATUS 2026-09-03 — module reconciled to v16, tiers 1 and 3 FIXED.**
> `lorehold_v15.py` is now `lorehold_v16.py` with the four staged changes
> applied, and `pending.py` records them as COMMITTED; the module and the v16
> `.xlsx` now agree card-for-card.
>
> Longshot, Rebel Bowman is rebuilt: correct name, `{3}{R}` 3/3, the {1}
> noncreature cost reduction in `reduce_cost`, and 2-damage-to-each-opponent
> on every noncreature cast. Olórin's Searing Light is no longer tagged as a
> wipe and resolves as an edict with spell-mastery damage. Storm-Kiln Artist
> scales with your artifacts and Treasures. All 20 cost errors corrected on
> both legs.
>
> Effect: Lorehold's A/A damage rose from **37.98 to 43.81**. (It had already
> risen 34.52 → 37.98 on the v16 reconciliation alone.)
>
> Still open, and all of it is Artist's Talent-shaped: the Class still grants
> its Level 2 discount free and instantly, with Level 1's rummage and Level
> 3's +2 noncombat damage unmodelled. Also open: Storm Herd's X still reads
> `cfg["storm_herd_x"]`=40 rather than a real life total (this engine does not
> track life at all), and Approach of the Second Sun still cannot get its
> second cast because the card is not put seventh from the top.

Every nonland card in `edhmc/decks/lorehold_v15.py` checked against Scryfall
oracle text (fetched 2026-09-03), and the scripted behaviour in
`edhmc/lorehold.py` read against the text it claims to implement.

**23 of 75 cards have a wrong mana cost, power, toughness or name — the worst
of the three decks.** One card is a different card entirely, one is a
misspelling, and one of the deck's best engine pieces is modelled as a vanilla
body.

The good news first: the Lorehold engine is the most faithful of the three.
Miracle windows, the commander's off-turn rummage, Monument to Endurance's
once-per-turn mode selection, Penance and Hidden Retreat costing a *card* and
not mana, Guttersnipe's 2-to-each-opponent, Urabrask's damage **and** its `{R}`
mana ability, Double Vision not triggering cast-triggers on its copy — all
correct, and several are subtle. The errors below are concentrated in card
data, not in the simulation logic.

---

## Tier 1 — Longshot is a completely different card

Module:

    C("Longshot Rebel Bowman", "Creature", {"gen": 1, "W": 1}, 2, 2, priority=3)

Oracle — note the comma; the module's name does not resolve on Scryfall:

> **Longshot, Rebel Bowman**  {3}{R}  Legendary Creature — Human Rebel Ally  3/3
> Reach
> **Noncreature spells you cast cost {1} less to cast.**
> **Whenever you cast a noncreature spell, Longshot deals 2 damage to each
> opponent.**

This is a second Guttersnipe that *also* reduces every noncreature spell by
{1}, in a deck that is ~50 noncreature spells. It is modelled as a vanilla 2/2
for `{1}{W}` with `priority=3` and no script, so it is cast late, does nothing
when it lands, and its two abilities do not exist in the engine. Nothing in
`lorehold.py` references it.

Wrong colour (W vs R), wrong MV (2 vs 4), wrong stats (2/2 vs 3/3), and both
abilities missing. If any single fix in this repo is worth doing first, it is
this one.

---

## Tier 2 — engine behaviour that does not match the text

### Artist's Talent — a three-level Class collapsed into one free level

> (Level 1) Whenever you cast a noncreature spell, you may **discard a card. If
> you do, draw a card.**
> `{2}{R}`: **Level 2** — Noncreature spells you cast cost {1} less.
> `{2}{R}`: **Level 3** — If a source you control would deal noncombat damage
> to an opponent…, it deals that much damage **plus 2** instead.

The engine grants the Level 2 cost reduction the moment it resolves
(`lorehold.py:209, 343`), for free, and models nothing else. So:

- **Level 1's rummage is missing.** It discards on every noncreature spell,
  which triggers Monument to Endurance and feeds the graveyard that The Dawning
  Archaic and Arcane Bombardment read.
- **Levelling costs `{2}{R}` twice and is never paid.** The cost reduction
  should arrive several turns later than it does.
- **Level 3 is missing, and it is large.** +2 noncombat damage per source turns
  Guttersnipe from 6 to 12 a spell, doubles Longshot, and scales every point of
  Soulfire Eruption and Boros Charm.

Net direction is genuinely unclear — free Level 2 flatters it, missing Levels 1
and 3 penalise it — so this card's ablation number means very little today.

### Storm-Kiln Artist — missing its own power

> This creature gets **+1/+0 for each artifact you control**.
> Magecraft — Whenever you cast **or copy** an instant or sorcery, create a
> Treasure.

The Treasure half is implemented (`lorehold.py:644`). The power-scaling half is
not, and this deck makes Treasures — each of which is an artifact — so the
Artist grows with its own output. Module also has it as 2/3; it is 2/2.

### Reforge the Soul's miracle cost is a mana too cheap

Module `miracle={"R": 1}` → `{R}`. Oracle: **miracle `{1}{R}`**. Since the
whole deck is built to hit miracle windows, this discount is load-bearing.

### Storm Herd's X is still hardcoded

> Create X 1/1 white Pegasus tokens with flying, where **X is your life total**.

`lorehold.py:543` uses `g.cfg.get("storm_herd_x", 40)`. Life is not tracked in
this engine, so 40 is an assumption that only holds if you have taken no damage
by the turn you cast a 10-mana sorcery. This is the item CLAUDE.md lists as
lost work; it is still open. The Pegasi's flying is also not modelled.

### Approach of the Second Sun never gets its second cast

> …put Approach of the Second Sun into its owner's library **seventh from the
> top** and you gain 7 life.

`apply_spell_effects` counts casts and wins on the second, but the card is put
in the graveyard like any other spell, so it can only be recast off recursion —
and copies are explicitly excluded (`not is_copy`, correctly, since a copy is
not cast from hand). The real card reliably returns to your hand within a few
draws. Its win route is being under-counted.

### Olórin's Searing Light is not a wipe

Module tags it `("wipe", "onesided")`.

> Each opponent **exiles a creature with the greatest power** among creatures
> that player controls.
> Spell mastery — …deals damage to each opponent equal to the power of the
> creature they exiled.

That is one creature per opponent — an edict, not a board wipe — plus
conditional damage that is not modelled at all. Tagging it `wipe` routes it
through `OPP.resolve_own_wipe`, which is the wrong effect entirely. Also
`{5}{W}` MV6 in the module against `{2}{R}{W}` MV4 real, and the module
misspells the name (`Orlorin's`).

### Victory Chimes taps for colourless, and can give the mana away

> {T}: **A player of your choice** adds {C}.

Module has `mana=(1, "RWC")` — it can pay red or white pips it cannot actually
produce. Bender's Waterskin *is* "any color" and is fine. Both correctly carry
the "untap during each other player's untap step" idea via the `cross_turn`
tag, which is right and is the reason they are in the deck.

---

## Tier 3 — cost, stat and name errors

MV changes marked in bold; the rest are colour-pip errors, which still matter
because the deck is two-coloured and the module docstring claims "where a
card's real cost differs, the real cost is used." **That claim is false for 20
cards.**

| card | module | oracle |
|---|---|---|
| Longshot, Rebel Bowman | `{1}{W}` 2/2 | `{3}{R}` **MV4** 3/3 |
| Pinnacle Monk | `{2}{W}` 3/3 | `{3}{R}{R}` **MV5** 2/2 (MDFC `// Mystic Peak`) |
| Goliath Daydreamer | `{5}{R}` MV6 6/6 | `{2}{R}{R}` **MV4** 4/4 |
| Hexing Squelcher | `{2}{R}` MV3 | `{1}{R}` **MV2** |
| Olórin's Searing Light | `{5}{W}` MV6 | `{2}{R}{W}` **MV4** |
| Invoke Calamity | `{3}{R}{R}` | `{1}{R}{R}{R}{R}` |
| Unexpected Windfall | `{3}{R}` | `{2}{R}{R}` |
| Borrowed Knowledge | `{3}{R}` | `{2}{R}{W}` |
| Perch Protection | `{5}{W}` | `{4}{W}{W}` |
| Promise of Loyalty | `{3}{W}{W}` | `{4}{W}` |
| Ultima | `{3}{R}{W}` | `{3}{W}{W}` |
| Approach of the Second Sun | `{5}{W}{W}` | `{6}{W}` |
| Emeria's Call | `{5}{W}{W}` | `{4}{W}{W}{W}` |
| Hit the Mother Lode | `{5}{R}{R}` | `{4}{R}{R}{R}` |
| Improvisation Capstone | `{5}{R}{W}` | `{5}{R}{R}` |
| Restoration Seminar | `{5}{R}{W}` | `{5}{W}{W}` |
| Call Forth the Tempest | `{6}{R}{R}` | `{5}{R}{R}{R}` |
| Rise of the Eldrazi | `{10}{R}{R}` | `{9}{C}{C}{C}` |
| Monastery Mentor *(pending)* | `{1}{W}{W}` | `{2}{W}` |
| Storm-Kiln Artist | 2/3 | 2/2 |
| Radiant Scrollwielder *(candidate)* | 2/5 | 2/4 |

**Rise of the Eldrazi is the sharp one.** `{9}{C}{C}{C}` needs three *true
colourless* sources; a Boros deck has only a handful (Geier Reach Sanitarium,
Mikokoro, Reliquary Tower, Slayers' Stronghold, Sunhome, Battlefield Forge).
The module's `{10}{R}{R}` is trivially castable off Mountains by comparison, so
a 12-mana spell is being cast in games where it should be stranded. Also note
the real card destroys a permanent and draws four **for a target player** on
top of the extra turn; the script only draws 4 and queues the turn.

Name fixes needed for lookup as well as correctness: `Longshot Rebel Bowman` →
`Longshot, Rebel Bowman`; `Orlorin's Searing Light` → `Olórin's Searing Light`.
`Pinnacle Monk`, `Sejiri Shelter`, `Emeria's Call` and `Ondu Inversion` are all
MDFCs whose full names are `A // B`; only the front face is stored, which is
fine for the engine but means an automated Scryfall check needs the alias.

---

## What to fix, in order

1. **Longshot, Rebel Bowman** — new card data plus two abilities.
2. Artist's Talent's levels (or, at minimum, charge for Level 2).
3. Olórin's Searing Light: drop the `wipe`/`onesided` tags, model the edict.
4. Reforge the Soul's miracle cost; Storm-Kiln Artist's power scaling.
5. The cost table — mechanical, but Rise of the Eldrazi and Pinnacle Monk
   change castability materially.

Note that the module and the v16 spreadsheet already disagree by the four
staged Lorehold changes (`pending.py`), and `pending.py`'s own docstring is
backwards about which side is ahead. Reconcile that before committing any of
the above, or the cost fixes will land in a module that is about to be
rewritten anyway.
