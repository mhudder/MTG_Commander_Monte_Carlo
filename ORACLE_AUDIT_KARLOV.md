# Oracle-text audit — Karlov v1

> **STATUS 2026-09-03 — tiers 1–3 FIXED**, in `karlov_v1.py`, `karlov.py` and
> the `.xlsx`. Measured effect of the whole correction, paired CRN, N=4000:
> damage **+1.89 ±1.59**, lifegain triggers **−3.12 ±0.30**, Karlov counters
> **−2.08 ±0.48**, cards drawn **−2.03 ±0.26**, win rate **−0.0163 ±0.0139**.
> The deck is measurably *worse* than the old model claimed: the phantom
> lifegain triggers and the free card draw were flattering it. A/A control is
> clean (+0.00 on every metric).
>
> Still open: Necropotence modelled as `draw2`; Benevolent Offering's three
> Spirit tokens and per-creature scaling; Ranger of Eos tutoring two specific
> one-drops; Karlov's own six-counter exile ability; Daxos's toughness fixed
> at 4 rather than tracking devotion; Lurrus's hybrid pips.

Every nonland card in `edhmc/decks/karlov_v1.py` checked against Scryfall
oracle text (fetched 2026-09-03), and every scripted behaviour in
`edhmc/karlov.py` read against the text it claims to implement.

**Bottom line: 11 of 63 cards have a wrong mana cost, power, toughness or type
line, and 22 have a behaviour that does not match their oracle text.** The
ablation table in `ablation_karlov.txt` was generated against this baseline and
should not be trusted card-by-card until at least tier 1 is fixed.

Method: `cards/collection` with a `User-Agent` header, compared field by field.
Nothing below is from memory; every quoted line is Scryfall's.

---

## Tier 1 — the engine is materially wrong

### 1. The commander costs one mana too much

    module   {1}{W}{B}   MV 3
    oracle   {W}{B}      MV 2

Karlov lands a turn late in every game. Measured, paired, CRN, N=4000:

| metric | module (MV3) | oracle (MV2) | diff |
|---|---|---|---|
| damage | 59.64 | 63.70 | **+4.06 ±1.43** |
| karlov_counters | 28.82 | 30.46 | +1.63 ±0.36 |
| won | 0.3930 | 0.3962 | +0.0032 ±0.0107 |

+4.06 damage would place second on the whole ablation table, above Kambal. Win
rate does not move outside its error bar — so this is a correction to the
*proxy baseline*, not a demonstrated change to the objective. Fix it because it
is wrong, and regenerate the table because every card was measured against it.

### 2. Cliffhaven Vampire — wrong target and wrong amount

> Whenever you gain life, each opponent loses 1 life.

`karlov.py:186` does `OPP.damage_single(g, amount)`. Two errors compounding:
it hits one opponent instead of each, and it scales with the life gained
instead of being a flat 1. On a 1-life soul-sister trigger it understates pod
damage 3x; on a large gain it overstates badly. Should be `damage_each(g, 1)`.

Also flying (`2/4`, module has `2/3`) — see tier 5.

### 3. Aetherflux Reservoir is missing its actual engine

> Whenever you cast a spell, you gain 1 life for each spell you've cast this
> turn.
> Pay 50 life: This artifact deals 50 damage to any target.

Only the second line is modelled (`karlov.py:269`). The first line is the
reason the card is in a lifegain deck — it is a per-spell, storm-scaled
lifegain trigger, i.e. a Karlov trigger engine. Currently contributes zero
until life ≥ 51.

### 4. Serra Ascendant is a vanilla 1/1

> Lifelink. As long as you have 30 or more life, this creature gets +5/+5 and
> has flying.

Modelled as a 1/1 lifelink with no conditional buff. In a deck whose mean
final life is ~36, this is a 6/6 flying lifelink for {W} most of the game. Its
ablation score (`+0.14 ±0.51`, "unmeasured") is a fact about this omission.

### 5. Drana's Emissary hits one opponent instead of three

> At the beginning of your upkeep, each opponent loses 1 life and you gain 1
> life.

`upkeep()` calls `drain(g, 1)`, and `drain` is `damage_single` + `gain_life`.
Understates its pod damage 3x. Should be `damage_each(g, 1)` plus one
`gain_life(g, 1)`.

There is also a dead `if g.has("Drana's Emissary"): pass` stub at
`karlov.py:241` inside `opponent_activity` — leftover, does nothing.

### 6. Cosmos Elixir — wrong trigger, wrong timing, missing half the card

> At the beginning of your end step, draw a card if your life total is greater
> than your starting life total. Otherwise, you gain 2 life.

`karlov.py:256` fires in **upkeep**, conditions on
`lifegain_triggers > 0` instead of `life > 40`, and drops the "otherwise gain 2
life" branch entirely — which is itself a Karlov trigger.

### 7. Debt to the Deathless — three triggers where the card makes one

> Each opponent loses two times X life. You gain life equal to the life lost
> this way.

`resolve()` loops `for _ in range(len(living)): drain(g, 6)` — three separate
`gain_life` events, so three Karlov triggers, three Voice counters, three Well
of Lost Dreams draws. The card gains life **once**, for the total. Also X is
inconsistent: the module bakes `{2}` into the cost (X=2) while the script
drains 6 per opponent (X=3), and the real cost is `{X}{W}{W}{B}{B}`.

---

## Tier 2 — phantom lifegain triggers (these inflate Karlov directly)

`drain()` gains you life. Three cards use it where the real card causes life
loss with **no** gain, so each one manufactures Karlov triggers that do not
exist.

| card | oracle | engine | error |
|---|---|---|---|
| Suture Priest | "Whenever a creature an opponent controls enters, you may have that player lose 1 life" | `drain(g,1)` | you gain 1 life you should not |
| Elas il-Kor | "Whenever another creature you control dies, each opponent loses 1 life" | `drain(g,1)` | false lifegain **and** single instead of each |
| Daxos, Blessed by the Sun | "Whenever another creature **you control** enters or dies, you gain 1 life" | counted in `creature_entered` regardless of `mine` | triggers on opponents' creatures too |

Daxos is the worst of the three: `creature_entered` is called for every
opponent creature (`opponent_activity`, ~0.7 per opponent per turn), and Daxos
is summed in alongside Soul Warden / Soul's Attendant / Auriok Champion, which
*do* correctly see every creature.

---

## Tier 3 — free effects that should cost mana or have a condition

| card | oracle | engine |
|---|---|---|
| Well of Lost Dreams | "you may pay {X} … draw X" | draws `min(2, amount)` free |
| Dawn of Hope | "you may pay {2} … draw a card"; also `{3}{W}`: 1/1 lifelink token | free 50% coin-flip draw; token ability absent |
| Land Tax | "**if an opponent controls more lands than you**" | fetches 3 basics every upkeep, unconditionally |
| Blind Obedience | Extort: per spell **you** cast, pay {W/B} | free `drain(1)` once per turn |
| Vizkopa Guildmage | `{1}{W}{B}`: "whenever you gain life this turn, each opponent loses that much" | counts as an assembled combo with no activation |

Well of Lost Dreams (+0.0247 win) and Dawn of Hope (+0.0195 win) are both top-10
on the ablation table and both are getting their effect for free. Treat those
two numbers as ceilings.

Vizkopa Guildmage matters for `check_combo`: it is in `COMBO_B`, so its mere
presence alongside Exquisite Blood is scored as a win. The real loop needs
`{1}{W}{B}` available and a lifegain event in the same turn.

---

## Tier 4 — dead data and stubs

- **Radiant Fountain** carries `lifegain=2`, and it never fires. Lands are put
  onto the battlefield by `engine.play_land` → `run_etb`, which dispatches on
  `card.script` only and never reads `card.lifegain`. Only `karlov.resolve()`
  honours that field, and lands never reach it. The 2 life is silently dropped.
- **Pristine Talisman** has `lifegain=0` (already flagged in CLAUDE.md). Even
  set to 1 it would be wrong — `resolve()` applies `lifegain` once on cast,
  whereas the card gains 1 life *per tap for mana*. There is no hook for
  lifegain on a mana ability at all.
- **Necropotence** is `script="draw2"`. The real card skips your draw step and
  exiles cards for 1 life each. It should be a life-for-cards pump that
  *reduces* life — which interacts with Felidar Sovereign's 40 and Aetherflux's
  50 thresholds.
- **Benevolent Offering** is a flat `lifegain=4`. Real: "you gain 2 life for
  each creature you control" (scales, often far more than 4) **and** you create
  three 1/1 fliers — three creature ETBs the soul sisters should see.
- **Sunscorch Regent** gains the life but never gets its `+1/+1` counter, so a
  4/4 that should grow every opponent spell stays a 4/4.
- **Ranger of Eos** is `draw2`. Real: tutors two MV≤1 creatures to hand. This
  deck runs five (Soul Warden, Soul's Attendant, Soulmender, Serra Ascendant,
  Mother of Runes) — strictly better than two random cards.
- **Karlov's own removal ability** ("Remove six +1/+1 counters: exile target
  creature") is never modelled. Counters only accumulate.
- `gain_life`'s `_depth` guard is dead: `_depth` is never propagated to
  recursive calls, so `_depth > 3` can never fire.
- `karlov_counters` keeps accruing while Karlov is off the battlefield
  (`commander_cast` is set once and never cleared). Reset on recast, so the
  effect is limited, but the counters are wrong in the window between.

---

## Tier 5 — cost, stat and type-line errors

Same MV unless noted. Colour-pip errors still change castability under the
mana model.

| card | module | oracle |
|---|---|---|
| Karlov of the Ghost Council | `{1}{W}{B}` MV3 | `{W}{B}` **MV2** |
| Fracture | `{1}{W}{B}` MV3 | `{W}{B}` **MV2** |
| Damn | `{1}{B}{B}` MV3 | `{B}{B}` **MV2** (overload `{2}{W}{W}` = MV4) |
| Debt to the Deathless | `{2}{W}{W}{B}{B}` | `{X}{W}{W}{B}{B}` |
| Voice of the Blessed | `{1}{W}` | `{W}{W}` |
| Kambal, Consul of Allocation | `{2}{W}` | `{1}{W}{B}` |
| Phyrexian Arena | `{2}{B}` | `{1}{B}{B}` |
| Sunscorch Regent | `{4}{W}`, 4/4 | `{3}{W}{W}`, **4/3** |
| Cliffhaven Vampire | 2/3 | **2/4** |
| Lurrus of the Dream-Den | `{1}{W}{B}` | `{1}{W/B}{W/B}` (hybrid) |
| Daxos, Blessed by the Sun | 2/1, Creature | 2/**\***, Enchantment Creature |

**The docstring's "corrections" are the errors.** `karlov_v1.py` says the
spreadsheet "already corrected Damn to MV 3 and Fracture to MV 3, and those
corrections are carried here." Both are MV 2. Damn is a two-mana spot removal
whose wrath mode costs `{2}{W}{W}`; MV 3 is right for neither half. This needs
fixing in the `.xlsx` as well as the module, or it will be re-applied.

Daxos's toughness is his devotion to white — in a mono-W-heavy list that is
routinely 4+, not 1.

### Evasion is unmodelled

Cliffhaven Vampire, Drana's Emissary and Sunscorch Regent all have flying, and
Serra Ascendant gains it at 30 life. `opponents.damage_through` has no evasion
term at all — it chump-blocks the largest attackers with no regard to flying.
This is the work CLAUDE.md lists as lost and needing a rewrite; it is still
missing, and it under-rates four of this deck's creatures.

---

## What this means for `ablation_karlov.txt`

Do not act on the current table:

- Every score is against a baseline where the commander is a turn slow.
- Well of Lost Dreams and Dawn of Hope are top-10 on free effects (ceilings).
- Serra Ascendant, Aetherflux Reservoir, Pristine Talisman, Necropotence,
  Benevolent Offering and Radiant Fountain are all measuring the engine's
  omissions, not the cards — they belong in the MODEL-BLIND group as written,
  yet three of them are listed as MODEL-EVALUATED.
- `SCRIPTED_KARLOV` in `ablation.py` is therefore wrong: it lists Pristine
  Talisman, Necropotence, Benevolent Offering, Ranger of Eos, Land Tax,
  Aetherflux Reservoir, Serra Ascendant and Radiant Fountain as
  model-evaluated. On the evidence above they are effectively blind.
  Soulmender (`{W}`, "{T}: gain 1 life") is *not* in the list and is
  unimplemented — correctly blind, but worth noting it has no tap ability
  modelled either.

Suggested order: tier 1 → re-run `validate.py` (must stay `+0.00` on all six)
→ tier 2 → regenerate the table. Tiers 3–5 change magnitudes, not signs, and
can follow.
