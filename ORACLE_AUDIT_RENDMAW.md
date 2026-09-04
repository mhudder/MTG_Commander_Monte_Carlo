# Oracle-text audit — Rendmaw v11

> **STATUS 2026-09-03 — tiers 1–3 FIXED**, in `rendmaw_v11.py`, `engine.py`,
> `opponents.py` and the `.xlsx`.
>
> The commander now gives a Bird to **each player** and those Birds are
> **goaded**: `Opponent.goaded_birds` tracks them, they add to the blocker
> count in `damage_through`, and `opponents.goaded_combat()` forces them to
> swing at each other rather than at you. Coat of Arms and Primal Vigor are
> now symmetric, and the trigger no longer fires while Rendmaw is off the
> battlefield. Tendershoot Dryad makes one Saproling per player per round with
> the ascend anthem instead of doubling its own count.
>
> Effect: Rendmaw's A/A damage fell from **39.85 to 31.78** — the opponents'
> new blockers cost more than the goad damage returns on that metric. Games
> still end around turn 12 and opponents killed rose to ~1.67, so the goad
> half is doing real work on the objective even where damage drops.
>
> **Two knock-on effects worth knowing:** `corr(A,B)` fell from 0.9109 to
> 0.8929, so CRN is now worth ~9x rather than ~11x; and the Birds' **flying**
> is still unmodelled — `damage_through` has no evasion term for any deck, so
> `goad_block_share` (default 0.30) is standing in for it.
>
> Still open: March of the World Ooze's Elephant trigger (KNOWN_ISSUES 1a);
> Twitching Doll's sacrifice-for-Spiders; Bitterblossom's 1 life per Faerie;
> Rendmaw's own reach and menace.

Every nonland card in `edhmc/decks/rendmaw_v11.py` checked against Scryfall
oracle text (fetched 2026-09-03), and the scripted behaviour in
`edhmc/engine.py` read against the text it claims to implement.

**18 of 69 cards have a wrong mana cost, power, toughness or type line.** The
commander's own ability is missing half its text, and that half changes the
opponents' board every time it triggers.

---

## Tier 1 — the commander is missing half its ability

> When Rendmaw enters and whenever you play a card with two or more card types,
> **each player** creates a tapped 2/2 black Bird creature token with flying.
> **The tokens are goaded for the rest of the game.**

`Game.play_card_trigger` (`engine.py:311`) and the ETB at `engine.py:435` both
call `self.make_tokens(...)` — **you** get a Bird, nobody else does. Three
separate things are unmodelled:

1. **Each player creates one.** Every trigger should also add a Bird to each of
   the three opponents' boards. `opponents.damage_through` chump-blocks off
   `o.creatures`, so their board size directly gates your damage.
2. **The tokens are goaded.** You are the goader, so *every* Bird on the table
   — including the opponents' — must attack each combat and must attack someone
   other than you. The opponents' Birds are therefore forced into each other,
   and your own Birds lose the option not to attack.
3. **The Birds fly.** `damage_through` has no evasion term at all.

**The sign of this error is not obvious and I am not going to guess it.** More
opponent blockers cuts your damage; three goaded 2/2 fliers per trigger
swinging into each other accelerates the pod killing itself, which helps you.
It needs implementing and measuring, not estimating. What is certain is that
the current numbers do not describe the card that is printed.

Rendmaw also has **reach and menace**, neither modelled.

Same latent bug as Karlov: `commander_cast` is set once and never cleared, so
triggers keep firing after Rendmaw leaves the battlefield. `rendmaw_triggers`
is also incremented even when `commander_cast` is False, so the metric counts
triggers that produced nothing.

---

## Tier 2 — cards whose text the engine gets wrong

### Tendershoot Dryad — wrong trigger frequency and wrong ascend

> At the beginning of **each** upkeep, create a 1/1 green Saproling.
> Saprolings you control get **+2/+2** as long as you have the city's blessing.

`engine.py:601` makes `2 if len(g.board) >= 10 else 1` tokens on **your** upkeep
only. Two errors: "each upkeep" is four triggers a round in a four-player game,
not one; and the city's blessing pumps Saprolings +2/+2, it does not double the
token count. Currently a 1-token-per-round engine that should be four, with the
anthem missing entirely.

Cost is also wrong: module `{4}{G}{G}` (MV 6), oracle `{4}{G}` (MV 5), and it is
a 2/2, not a 1/1.

### Primal Vigor is symmetric and the engine treats it as one-sided

> **If one or more tokens would be created**, twice that many of those tokens
> are created instead.

`make_tokens` doubles only your tokens (`engine.py:238`). The real card doubles
tokens for **every** player. Combined with the missing "each player creates a
Bird" clause above, the engine is one-sided about a card that is famously not.

### Coat of Arms counts the whole battlefield

> Each creature gets +1/+1 for each other creature **on the battlefield** that
> shares at least one creature type with it.

`engine.py:722` counts only your own Birds. If opponents had their Rendmaw
Birds — which they should — Coat of Arms would pump those too. Both halves of
this are missing together, so the card is being scored in a world that does not
exist either way.

### Enduring Vitality, Twitching Doll, Bitterblossom

- **Enduring Vitality** is implemented (creatures tap for mana, `engine.py:348`)
  and is correct. Worth noting only because it is the deck's largest mana
  engine and depends on the token count being right.
- **Twitching Doll** taps for **one mana of any colour** and accumulates nest
  counters; sacrificing makes a 2/2 Spider **per counter**. Module has
  `mana=(1, "C")` — colourless only — and no sacrifice outlet. Also `{1}{G}`
  and 2/2, not `{2}` and 1/1.
- **Bitterblossom** costs **1 life** per Faerie. Not modelled (nor is the
  Faerie's flying).

### Steel Overseer is correct, and that is the finding

> {T}: Put a +1/+1 counter on each **artifact** creature you control.

`engine.py:641` correctly checks `"Artifact" in p.card.types`. Rendmaw's Birds
are plain black Bird tokens, **not** artifact creatures, so Overseer does
nothing for the token engine — it only pumps the Myr package. The
implementation is right; the card is just narrower here than its
`SCRIPTED_RENDMAW` membership suggests.

### March of the World Ooze — the known gap, still open

> Creatures you control have base power and toughness **6/6** and are Oozes.
> Whenever an opponent casts a spell, **if it's not their turn**, you create a
> 3/3 green Elephant token.

The P/T setter is implemented in `power_of`/`toughness_of`. The Elephant
trigger is still missing — this is `KNOWN_ISSUES.md` item 1a, and it means the
committed +2.85 damage for the Skullclamp swap is a floor, as documented.

---

## Tier 3 — cost, stat and type errors

MV changes are marked; the rest are colour-pip errors that still change
castability.

| card | module | oracle | note |
|---|---|---|---|
| Dryad of the Ilysian Grove | `{1}{G}` MV2 | `{2}{G}` **MV3** | ramp lands a turn early |
| Dockside Chef | `{1}{B}` MV2 | `{B}` **MV1** | module a mana too expensive |
| Lignify | `{2}{G}` MV3 | `{1}{G}` **MV2** | module a mana too expensive |
| Beastmaster Ascension | `{1}{G}` MV2 | `{2}{G}` **MV3** | module a mana too cheap |
| Deathreap Ritual | `{1}{B}{G}` MV3 | `{2}{B}{G}` **MV4** | module a mana too cheap |
| Tendershoot Dryad | `{4}{G}{G}` MV6 | `{4}{G}` **MV5** | module a mana too expensive |
| Ezuri's Predation *(candidate)* | `{5}{G}{G}` MV7 | `{5}{G}{G}{G}` **MV8** | |
| Twitching Doll | `{2}`, 1/1 | `{1}{G}`, **2/2** | |
| Woe Strider | `{1}{B}{B}`, 3/3 | `{2}{B}`, **3/2** | |
| Roaming Throne | `{3}{C}` | `{4}` | the `{C}` pip is not real |
| The Meathook Massacre | `{2}{B}{B}` | `{X}{B}{B}` | X baked in as 2 |
| Arasta of the Endless Web | 1/5 | **3/5** | |
| Shigeki, Jukai Visionary | 2/2 | **1/3** | |
| Pygmy Kavu | 2/2 | **1/2** | |
| Haywire Mite | 0/2 | **1/1** | |
| Eyeblight's Ending | Instant | **Kindred** Instant | **2 card types → triggers Rendmaw** |
| Grist, the Hunger Tide | Planeswalker/Creature 0/0 | Planeswalker (creature only off-battlefield) | see below |

**Eyeblight's Ending is the one that matters.** It is a *Kindred* Instant —
two card types — so playing it triggers Rendmaw. The module types it as a plain
Instant, so the deck is losing a Bird trigger it should get. Check the rest of
the list for the same class of error against the spreadsheet; `Nameless
Inversion` and `Lignify` are already correctly tagged `Kindred`.

**Grist** is a Planeswalker on the battlefield and a 1/1 Insect creature only
while it is *not* there. Typing it `Planeswalker/Creature` in the module
happens to give the right answer for the Rendmaw trigger (the card on the stack
does have two types), but it also puts a 0/0 creature on your board that
`combat()` counts as an attacker. Harmless to the damage total today, but it is
right for the wrong reason.

---

## What to fix, in order

1. The commander's "each player" + goad + flying clauses. Everything else in
   this deck is downstream of the token count.
2. Tendershoot Dryad's per-upkeep frequency and the +2/+2 anthem.
3. Primal Vigor and Coat of Arms symmetry — only meaningful after (1).
4. Eyeblight's Ending's Kindred type.
5. The cost/stat table, which is mechanical.

`validate.py` must still print `+0.00` on all six after each step.
