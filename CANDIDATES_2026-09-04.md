# Candidate evaluation — 2026-09-04

Nineteen candidate additions across the three decks, in two batches. All were
implemented against Scryfall oracle text before being measured; ten needed new
engine behaviour, and three needed a modelling gap closed first.

**Five are STAGED in `edhmc/pending.py`** — see "The staged swaps" below. The
second batch (seven cards) is evaluated at the end and nothing from it is
staged yet.

Method: `candidates.py`. One existing slot is replaced by a neutral blank of the
candidate's cost (leg A) and by the candidate (leg B), 6,000 paired games under
common random numbers, at two horizons. That is the same scale as
`ablation.py`, so a candidate's score can be read directly against the ablation
table for the deck it is going into.

    python candidates.py rendmaw  --turns=10   # and --turns=20
    python candidates.py lorehold --turns=10   # and --turns=20
    python candidates.py karlov   --turns=10   # and --turns=20

`validate.py` is still exactly `+0.00` on all six metrics with `corr(A,B) =
0.8929`, unchanged, so every engine change below is inert on the committed
lists and the three existing ablation tables remain valid.

---

## A harness bug found on the way in

**`candidates.py`'s blank did not match `ablation.py`'s blank**, so the two
tables were not on the same scale — which is the one thing the whole method
depends on. `ablation.py` blanks a card down to a *single* type line;
`candidates.py` copied the candidate's whole type line. For Rendmaw that is not
a detail: an Artifact Creature blank triggers the commander, so Wurmcoil Engine
was being scored against a blank that also made a Bird, while every card in
`ablation_rendmaw.txt` was scored against one that did not.

Fixed; `candidates.py` now uses `ablation.py`'s blank verbatim. Every number
below is from the post-fix run. Wurmcoil Engine moved +0.69 → +0.82 damage at
T20 on that change alone.

---

## Rendmaw, Creaking Nest v12

6,000 paired games, mixed pod. Compare against `ablation_rendmaw.txt`.

| card | MV | damage T10 | damage T20 | win rate T10 | win rate T20 | P(deploy) |
|---|---|---|---|---|---|---|
| Cauldron of Essence | 3 | +0.96 ±0.21 | +1.30 ±0.35 | −0.0002 ±0.0016 | **+0.0113 ±0.0048** | 0.187 |
| Revitalizing Repast | 1 | +0.71 ±0.21 | +0.65 ±0.34 | +0.0012 ±0.0012 | +0.0040 ±0.0034 | 0.086 |
| Wurmcoil Engine | 6 | +0.33 ±0.16 | +0.82 ±0.31 | −0.0003 ±0.0012 | +0.0065 ±0.0040 | 0.153 |

All three are positive on damage at both horizons and all three are inside their
bars on win rate at T10. Read the T20 win rates as the weaker claim: the sign is
stable, but a card that only separates from a blank at twenty turns is being
paid by games this pod usually ends around turn twelve.

**Cauldron of Essence — the real add.** Its drain half is Meathook Massacre's
text word for word ("each opponent loses 1 life and you gain 1 life"), so it is
worth 3 pod life per creature death, and this deck loses a dozen tokens a game:
12.4 drain damage per game it resolves. Its second half is a repeatable sac
outlet *and* recursion — 0.55 reanimations per game — and it is stocked mostly
by the pod's own wraths, which is exactly when you want it. A win rate of
+0.0113 would rank fourth in the deck, alongside March of the World Ooze
(+0.0105).

One caveat that cuts the other way: **the engine models Blood Artist at 3.0 pod
damage per death when its text is 1** (it drains one player, not each). That is
a pre-existing overstatement, not something introduced here. Cauldron's 3.0 *is*
correct. So do not read this result as "another Blood Artist" — Cauldron is the
one of the two that the engine has right.

**Wurmcoil Engine** is an Artifact Creature, so it does trigger the commander,
and it dies into two more bodies 0.40 times per game. Its number is a floor
twice over: deathtouch is unmodelled (the engine only prices it as a blocker
deterrent, for Ohran Frostfang), and its lifelink is now modelled but pays 7.8
life per game it resolves into a model where life does not decide games — see
the correction below. Read its +0.82 / +0.0065 as the body, the death tokens
and the commander trigger; the lifelink is contributing close to nothing.

**Revitalizing Repast** is a land that is sometimes a +1/+1 counter. The land
face is most of what it does — it is played as a spell in only 8.6% of games.
Its indestructible clause is unmodelled (this engine cannot hold up an instant
for removal it does not see coming), so the number is a floor, but the missing
half is protection, and protection is exactly what the model is blindest to.
Note it is a single card type on the front face: **no Rendmaw trigger.**

**Verdict.** Cauldron of Essence clears the bar comfortably — the deck's weakest
model-evaluated slots (Ornithopter of Paradise, Idol of Oblivion, Copper/Leaden
Myr, Dockside Chef) all score inside their own error bars. Wurmcoil is a
defensible add on a floor. Repast is a marginal call I would not make on this
evidence.

---

## Lorehold, the Historian v16

6,000 paired games. `mv_cheated` is this deck's primary metric; damage is the
proxy. Compare against `ablation_lorehold.txt`.

| card | MV | damage T20 | win rate T20 | mv_cheated T10 | mv_cheated T20 | P(deploy) |
|---|---|---|---|---|---|---|
| Sunbird's Invocation | 6 | +1.46 ±0.88 | +0.0095 ±0.0066 | +0.84 ±0.38 | **+2.23 ±0.96** | 0.181 |
| Brass's Bounty | 7 | +0.96 ±0.81 | −0.0018 ±0.0040 | −0.01 ±0.20 | +0.38 ±0.41 | 0.233 |
| Underworld Breach | 2 | +1.77 ±1.05 | +0.0067 ±0.0052 | +0.31 ±0.26 | **+2.03 ±0.79** | 0.257 |

**Sunbird's Invocation** fires 3.6 times per game it resolves, for an average
free spell of MV 3.8. The X-equals-the-spell's-mana-value clause is what makes
it a Lorehold card rather than a generic one: this deck's curve tops out at
twelve, so a big spell digs deep and can free-cast something big. It triggers on
casts **from hand**, which includes miracles — a miracled card is cast from hand
— but not Galvanoth, Radiant Scrollwielder, The Dawning Archaic, or Bombardment
and Mastery copies. Its +2.23 mv_cheated at T20 is in the same range as The
Dawning Archaic's committed evidence (+2.46).

**Underworld Breach** is the surprise: +2.03 mv_cheated on a two-drop. But read
what it is doing before believing it. It escapes 1.4 spells per game it
resolves, at full mana cost, exiling three cards each time — so none of that is
mana cheated; the mv_cheated it shows comes from the *cost reducers* applying to
the escaped spells. And it sacrifices itself at the beginning of the end step,
which the model implements literally: a hardcast Breach is one turn of
converting leftover mana into graveyard spells, and it is gone before the three
opponent-upkeep miracle windows ever open. Both figures are inside or barely
outside their bars at T10. In a deck with no combo to enable, this is a fair
value card and a mediocre one.

**Brass's Bounty is a blank.** 9.4 Treasures per game it resolves, and
mv_cheated −0.01 at T10 / +0.38 ±0.41 at T20, with a *negative* point estimate
on win rate. The mechanism is clear once you look: seven mana that produces mana
is only good if there is something to spend it on, and by the time this deck can
cast a seven-drop it is already floating four mana a turn. Treasures are not
this deck's bottleneck; live miracle targets are.

**Verdict.** Sunbird's Invocation is the only one of the three I would put in,
and it is a genuine but not dramatic upgrade. There is room for it: Blasphemous
Act (−3.33 damage, −0.0180 win), Penance (−1.91, −0.0117, already slated for a
cut in the queued work) and Scroll Rack (−1.78, −0.0100) are all actively
negative. Underworld Breach is a hold — it is a combo card in a deck with no
combo. Brass's Bounty is a pass.

---

## Karlov of the Ghost Council v1

6,000 paired games. Compare against `ablation_karlov.txt`.

| card | MV | damage T10 | damage T20 | win rate T10 | win rate T20 | P(deploy) |
|---|---|---|---|---|---|---|
| Starscape Cleric | 2 | **+4.13 ±0.46** | **+3.91 ±0.52** | **+0.0118 ±0.0035** | **+0.0153 ±0.0052** | 0.193 |
| Enduring Tenacity | 4 | +2.74 ±0.42 | +2.48 ±0.51 | **+0.0195 ±0.0041** | **+0.0217 ±0.0054** | 0.175 |
| Exemplar of Light | 4 | +1.42 ±0.39 | +2.11 ±0.47 | +0.0040 ±0.0028 | +0.0090 ±0.0046 | 0.166 |
| Heliod, Sun-Crowned | 3 | +0.60 ±0.31 | +1.27 ±0.44 | +0.0008 ±0.0024 | +0.0050 ±0.0045 | 0.183 |
| Guide of Souls | 1 | +0.48 ±0.30 | +0.71 ±0.32 | +0.0013 ±0.0023 | +0.0037 ±0.0037 | 0.197 |
| The Wind Crystal | 4 | +0.18 ±0.24 | +0.47 ±0.35 | +0.0022 ±0.0024 | +0.0022 ±0.0039 | 0.167 |

**Starscape Cleric is the best card in this list, and it is not close on
damage.** +4.13 at T10 beats every single card in the existing Karlov ablation
table — the current top is Kambal at +3.64. It is Marauding Blight-Priest
(+3.42, one of the deck's best cards) at half the mana, on a two-power flier,
and this deck produces sixteen-plus lifegain *events* per game, each of which is
three pod life. Both signals at both horizons. Its number is a floor in two
places: flying is unmodelled anywhere in the engine (queued work item 1), and
its Offspring cost is paid in only 25% of casts because the greedy main phase
has usually spent the mana already.

**Enduring Tenacity is a fourth Exquisite Blood combo piece**, and that is the
larger half of its value. Its trigger is Sanguine Bond's word for word
("whenever you gain life, target opponent loses that much life"), so it loops
with Exquisite Blood on its own with no mana — `COMBO_LOOP` in `karlov.py` was
updated to reflect that. It assembles the loop in 8.8% of the games it resolves.
Its win rate of +0.0217 would rank **fourth in the whole deck**, behind only
Felidar Sovereign, Exquisite Blood and Vito. And note this is the *addition*
measurement, so the redundancy with Sanguine Bond and Vito is already priced in
— unlike leave-one-out, which understates every member of an interchangeable
group. Its death trigger fires 0.60 times per game; it comes back as a
noncreature enchantment and keeps draining through a wrath.

**Exemplar of Light** is a real but second-tier add: +2.11 damage and +0.0090
win at T20, driven by 16.3 lifegain events a game each putting a counter on it,
and the once-per-turn draw. Comparable to Cosmos Elixir or Phyrexian Arena.

**Heliod, Sun-Crowned underperforms its reputation here, for a reason you should
check against the real list.** He is animated on only 1.3 turns of a 12.5-turn
game — this deck's white permanents are almost all single-pip, so devotion
rarely reaches five. He distributes 9.1 counters and grants lifelink 0.76 times
per game. In paper, Heliod is played for Walking Ballista, which is not in this
deck. Two further caveats: **indestructible had to be newly modelled to evaluate
him at all** (see below), and the victim slot used for the measurement is
Soulmender, a white one-drop, so both legs run one white pip short of the real
list — a small handicap that is specific to him.

**Guide of Souls scores low, and the mechanism is the card, not the model.** It
reads "whenever *another creature you control* enters" — it does not see the
opponents' board the way Soul Warden (+1.68) does. This deck plays 25 creatures
and makes no tokens, so it triggers 2.3 times per game and banks enough energy
to fire its attack trigger 0.48 times. Like Heliod, its real-world case is
Walking Ballista. In this list it is a worse Soul Warden.

**The Wind Crystal is a blank.** Inside its own error bars on win rate at both
horizons — unmeasured rather than bad, but nothing points to it being good here.
It doubles 24.6 life per game, which sounds large until you remember the central
modelling fact of this deck: **it counts triggers, not life.** Doubling the
amount does not create a second Karlov trigger, a second Voice of the Blessed
counter, or a second Blight-Priest drain. It helps only the payoffs that read
the *amount* — Sanguine Bond, Vito, Aetherflux, Felidar — and its six-mana
team-lifelink activation fires 0.11 times a game.

**Verdict.** Starscape Cleric and Enduring Tenacity are clear adds on this
evidence; Exemplar of Light is a reasonable third. The deck has the room:
Lightning Greaves (−0.33 damage, −0.0040 win, significant on both), Blood Artist
(−0.64, −0.0037), Whispersilk Cloak, Swiftfoot Boots and Soulmender all score at
or below zero. Heliod, Guide of Souls and The Wind Crystal do not clear the bar
in *this* list — all three are cards whose paper case rests on a piece this deck
does not run.

---

## The four staged swaps

Screening a candidate against a blank answers "is this better than a
replacement-level slot". It is not the change you actually make, so each swap
was then re-measured as the *real* swap — specific cards in against specific
cards out — with `run_swaps_0904.py`. 6,000 paired games, both horizons.

| deck | out | in | win T10 | win T20 |
|---|---|---|---|---|
| karlov | Swamp + Whispersilk Cloak | Starscape Cleric + Enduring Tenacity | **+0.0353** [+0.0297, +0.0413] | **+0.0480** [+0.0400, +0.0558] |
| rendmaw | Ornithopter of Paradise | Cauldron of Essence | +0.0025 [+0.0005, +0.0045] | +0.0158 [+0.0110, +0.0210] |
| lorehold | Scroll Rack | Sunbird's Invocation | +0.0077 [+0.0047, +0.0108] | +0.0215 [+0.0142, +0.0288] |

Every one is significant on win rate at both horizons. Costs that came with
them, all measured rather than assumed:

- **Karlov strands more mana** (+1.85 stranded_mv at T10) — that is the Swamp,
  37 lands to 36. Worth watching if the deck starts stumbling on drops.
- **Rendmaw's margin at T10 is thin** (CI low +0.0005). The swap loses a
  commander trigger, because Cauldron is one card type and Ornithopter is two
  (−0.064 rendmaw_triggers). It is carried by the long horizon.
- **Lorehold trades a two-drop for a six-drop** (+4.28 stranded_mv at T10). The
  alternative cut of Improvisation Capstone strands *less* (−0.98) but wins
  less (+0.0045 / +0.0128), so Scroll Rack is the better of the two measured.

### Considered and not taken

**A third Karlov swap — Lightning Greaves → Exemplar of Light — measures
better still**: +0.0397 at T10 and **+0.0617** at T20 for the 3-for-3, against
+0.0353 / +0.0480 for the 2-for-2. Greaves is the worst card in the deck by win
rate (−0.0040, signal "both") and cutting it still leaves Swiftfoot Boots and
Mother of Runes as shroud sources. Not staged, because it was not asked for and
it strands considerably more mana (+5.56 stranded_mv at T10 against +1.85). It
is a live option.

**Blasphemous Act is Lorehold's worst card by some distance** (−3.33 damage,
−0.0180 win) and is the obvious next cut. It was not used here because every
self-wipe in every deck is penalised by the commander bug below — but see the
measurement: it stays bad when the bug is corrected.

## The commander bug, now quantified

`opponents.resolve_own_wipe` removes your commander from the battlefield
without returning it to the command zone: `commander_cast` stays `True`, so it
is never recast. `destroy()` gets this right; this path never did. It is now
gated behind `cfg["own_wipe_commander_returns"]`, **defaulting to the existing
(wrong) behaviour** so the three committed ablation tables stay valid.

Value of the card over a blank, 4,000 paired games at 20 turns:

| card | current (bug) | commander returns |
|---|---|---|
| Blasphemous Act (lorehold) | −3.74 dmg, −0.0217 win | −2.95 dmg, −0.0213 win |
| Farewell (lorehold) | −2.05 dmg, −0.0065 win | −0.98 dmg, −0.0065 win |
| Damn (karlov) | −2.42 dmg, −0.0107 win | −1.56 dmg, −0.0032 win |

So the bug is worth roughly **1 damage on every self-wipe**, and for Damn it is
most of the win-rate penalty. It hits Lorehold hardest in principle — the
commander *is* the engine there, supplying three of four miracle windows a
round — but note Blasphemous Act is bad either way. Every wrath in
`ablation_karlov.txt` and `ablation_lorehold.txt` is somewhat over-penalised;
none of the four staged swaps depends on those numbers.

Flipping the default is a one-line change and invalidates all three ablation
tables, so it is left as a decision rather than taken.

## Engine changes made to support this

All inert on the committed lists; `validate.py` confirms `+0.00` on six metrics
and `corr(A,B) = 0.8929` unchanged.

| change | file | why |
|---|---|---|
| `on_creature_death(n, perm)` now receives the permanent that died | `engine.py`, `karlov.py`, `opponents.py` | Wurmcoil's and Enduring Tenacity's death triggers need to know *what* died |
| Cauldron of Essence drain + sac/reanimate activation | `engine.py` | its two halves |
| Wurmcoil lifelink; `Card.lifelink` now read in Rendmaw combat | `engine.py` | completeness — but see the correction below: it buys almost nothing |
| `repast` script (+1/+1 counter) | `engine.py` | Revitalizing Repast's front face |
| your own wrath now puts creatures in your graveyard | `opponents.py` | Cauldron needs a reanimation pool; nothing else reads it |
| `sunbird()`, `from_hand` flag on `resolve_spell` | `lorehold.py` | Sunbird triggers on casts from hand only |
| `brass_bounty` script | `lorehold.py` | one line |
| `underworld_breach()` + end-step sacrifice | `lorehold.py` | escape casting, and the self-sacrifice that makes it one turn |
| `devotion_white()`, `is_creature_now()` | `karlov.py` | Heliod is not a creature below devotion 5 |
| Heliod / Exemplar / Starscape branches in `gain_life` | `karlov.py` | their triggers |
| Wind Crystal: lifegain doubling, white cost reduction, activation | `karlov.py` | all three abilities |
| Guide of Souls: energy, "another creature", attack trigger | `karlov.py` | its triggers |
| `COMBO_LOOP` now includes Enduring Tenacity | `karlov.py` | it loops with Exquisite Blood unaided |
| Starscape Cleric Offspring | `karlov.py` | the token copy shares the name so `gain_life` counts both |
| **NEW: `Card.indestructible`, priced at `destroy_share`** | `engine.py`, `opponents.py` | see below |
| mechanism counters (`sunbird_casts`, `escape_casts`, `heliod_counters`, …) | all three engines | so every number above traces to a card's text |

### The one new modelling assumption

The opponent model does not distinguish a Swords to Plowshares from a Doom
Blade — everything is a generic "answer" — so **indestructible had no meaning at
all** until now. It is priced statistically: `cfg["destroy_share"]`, default
0.60, is the fraction of an EDH pod's interaction that is literally "destroy
target permanent" as opposed to exile, bounce, −X/−X or an edict. Heliod
survives 67% of the answers aimed at him under that number.

**0.60 is an assumption, not a measurement.** Heliod is the only card in any of
the three decks it touches, and his evaluation moves on it (+0.24 → +0.60
damage at T10 when it was switched on). If you want to stress that, it is one
`cfg` key.

## CORRECTION, and a limit on the whole model: life does not decide games

When Wurmcoil's lifelink was added above, the justification given was that "this
engine tracks `your_life` and loses the game on it". **That is wrong, and it was
worth checking rather than assuming.** A `loss_route` metric was added to
`opponents.py` and the answer is unambiguous:

| deck | horizon | loss rate | ground down on life | opponent's clock |
|---|---|---|---|---|
| rendmaw | T10 / T20 | 0.260 / 0.703 | 0.00 | **1.00** |
| lorehold | T10 / T20 | 0.196 / 0.782 | 0.00 | **1.00** |
| karlov | T10 / T20 | 0.228 / 0.602 | 0.00 | **1.00** |

**Every single loss, in all three decks, at both horizons, is an opponent's
clock** — which is threat-weighted and never reads your life total.

**FURTHER CORRECTION.** This was first written up as though the clock were
merely winning a close race, citing Rendmaw's mean final life of 7.6 at T20 as
evidence that incidental damage nearly got there. That was wrong, and the 7.6 is
an artifact: `resolve_clocks` SETS `your_life = 0` when it kills you, so those
games drag the mean down. The counterfactual is the honest test — disable the
clocks and change nothing else:

| deck | loss-by-life T20 | loss-by-life T30 | mean final life, clocks off |
|---|---|---|---|
| rendmaw | 0.004 | 0.014 | 21.5 |
| lorehold | 0.006 | 0.029 | 26.3 |
| karlov | 0.000 | 0.001 | 101.0 |

So there is **no race**. Incidental damage on its own would essentially never
kill you, even given thirty turns. The opponents' board is a float capped at 7
chipping for `creatures * 0.45 * your_share`, and it was never calibrated to
kill anybody — **the clock is the abstraction that stands in for "an opponent
actually wins".** 0% is the designed behaviour, not a surprise.

Consequences, and they are not small:

- **A bigger life total buys nothing defensively in this model.** Any card whose
  job is survival is MODEL-BLIND here, and a low score is evidence about the
  model, not the card.
- Lifelink is worth having only where something *reads* the life gained — Karlov
  triggers, Serra Ascendant's threshold, Felidar Sovereign's 40, Aetherflux's
  50. As damage prevention it is inert.
- This does not disturb any staged swap. Karlov's lifegain matters because it is
  a *trigger count* and a *drain*, not because it keeps you alive, which is what
  the engine docstring has said all along.

## Known gaps that bound these numbers

1. **Flying is still unmodelled anywhere** (queued work item 1). Starscape
   Cleric, Exemplar of Light, Wurmcoil's evasion-less bodies and Guide of Souls'
   flying counter are all floors.
2. **Deathtouch is unmodelled** except as an Ohran Frostfang blocker deterrent —
   Wurmcoil floor.
3. **Blood Artist is modelled at 3× its actual drain** in the Rendmaw engine.
   Pre-existing, not touched here, but it inflates the baseline Cauldron of
   Essence is measured alongside.
4. **`resolve_own_wipe` removes your commander without returning it to the
   command zone** — `commander_cast` stays `True`, so after casting your own
   sweeper the commander is neither on the battlefield nor recastable. Also
   pre-existing, and it slightly depresses everything measured in games where
   you fire your own wrath.
5. Revitalizing Repast's indestructible, Heliod's exile ability, Karlov's own
   exile ability and Umezawa's Jitte remain unmodelled.


---

# Second batch — 2026-09-04

Seven more cards: three for Karlov, four for Lorehold. Nothing was proposed for
Rendmaw this round. Measured against the **post-swap lists** — `build_pending()`
now applies the five staged changes, so these are scored alongside Starscape
Cleric, Enduring Tenacity, Exemplar of Light, Cauldron of Essence and Sunbird's
Invocation rather than against the old ones.

## Karlov — all three are playable, but read the third one carefully

| card | MV | damage T10 | damage T20 | win rate T10 | win rate T20 | P(deploy) |
|---|---|---|---|---|---|---|
| Dark Confidant | 2 | +1.81 ±0.44 | **+2.26 ±0.58** | +0.0073 ±0.0035 | +0.0090 ±0.0053 | 0.155 |
| Enlightened Confidant | 2 | +1.69 ±0.40 | +1.80 ±0.52 | **+0.0087 ±0.0034** | +0.0097 ±0.0049 | 0.154 |
| Crypt Ghast | 4 | +1.21 ±0.33 | +1.39 ±0.43 | +0.0040 ±0.0030 | +0.0058 ±0.0044 | 0.141 |

All three beat their bars on damage at both horizons. On win rate the two
two-drops clear at T10; Crypt Ghast only barely does. For scale, that puts all
three in the Cosmos Elixir / Phyrexian Arena / Well of Lost Dreams band of
`ablation_karlov.txt` — respectable, not top-tier, and none of them near
Starscape Cleric or Enduring Tenacity.

**Enlightened Confidant is the one I would actually play, and it is not because
of the numbers — they are a near tie.** Its value splits cleanly: +0.36 cards
drawn and +0.42 lifegain triggers (hence +0.53 Karlov counters). The lifelink is
doing real work *because this deck reads lifegain as a trigger*, which is the
only place lifelink is worth anything in this model. Its own end-step ability
gives 2.6 extra cards a game. Both halves are modelled conservatively: the
surveil declines to bin a card it cannot pick up, since this engine has no
top-deck payoff to bin for. **Its number is a floor.**

**Dark Confidant's number is a CEILING, and by more than the gap between it and
Enlightened Confidant.** Bob costs 5.7 life per game here and the model charges
you almost nothing for it — `final_life` moves +0.76 ±0.72, i.e. not at all.
That is not a quirk; it follows directly from the loss-route finding above:
**nothing in this model ever kills you on life.** The single real risk of
playing Dark Confidant — that it kills you off the top of a deck with Debt to
the Deathless and Felidar Sovereign in it — is invisible here. The only cost the
engine *does* see is the Felidar (40 life) and Aetherflux (50 life) thresholds,
and Karlov's average final life is 40.3, right on the Felidar line. I would take
Enlightened Confidant over it on identical numbers.

**Crypt Ghast** works: 2.8 extort triggers a game, and the Swamp doubling is
implemented against the real subtype (twelve Swamp-typed lands in this list —
the eleven basics plus Godless Shrine, and *not* Tainted Field, Caves of Koilos,
Fetid Heath or the other black-producing non-Swamps). It is the weakest of the
three because the deck's curve does not want the mana: Karlov tops out at six
and already floats. Ramp is not this deck's bottleneck.

## Lorehold — one good card, one strange one, two passes

| card | MV | damage T20 | win rate T10 | win rate T20 | mv_cheated T20 | P(deploy) |
|---|---|---|---|---|---|---|
| Caldera Pyremaw | 5 | **+1.21 ±0.58** | +0.0033 ±0.0018 | **+0.0123 ±0.0048** | −1.09 ±0.48 | 0.190 |
| Reverse the Sands | 8 | +0.39 ±0.31 | +0.0017 ±0.0013 | **+0.0130 ±0.0041** | +0.14 ±0.33 | 0.241 |
| Goldspan Dragon | 5 | +0.60 ±0.60 | +0.0012 ±0.0016 | +0.0025 ±0.0045 | −0.36 ±0.44 | 0.190 |
| Invincible Hymn | 8 | −0.02 ±0.23 | +0.0003 ±0.0008 | −0.0007 ±0.0017 | −0.17 ±0.16 | 0.242 |

**Caldera Pyremaw is the add.** 13.4 damage from its own trigger per game it
resolves, and +1.82 spell_damage over a blank. The counter resolves before the
damage, so the first trigger already hits for 4 and it climbs from there, and it
keys off CAST — so Arcane Bombardment and Mizzix's Mastery copies set it off
(they are genuinely cast) while Double Vision copies do not (put on the stack).
Note the honest trade: **mv_cheated goes DOWN by 1.09**, because a creature in a
slot is a slot that is not a miracle target. You are buying damage and win rate
with the deck's primary metric.

**Reverse the Sands is the strange one, and worth understanding before
believing.** +0.0130 win rate at T20 with damage flat at +0.39 ±0.31. It is not
dealing damage — it is redistributing. The implementation takes the largest life
total for you and hands the smallest to whoever the opponent model ranks as the
biggest threat, and the measured consequence is +0.016 ±0.007 opponents killed:
your ordinary damage then finishes somebody it otherwise would not have. That is
a real reading of the card. But note the half that does nothing: your own life
total going to 60 is worth exactly zero here, per the loss-route finding. So
this is a card being carried entirely by one narrow clause, and I would call it
speculative rather than proven.

**Invincible Hymn is a blank, and cleanly so.** Every metric is inside its bar
at both horizons. The reason is worth stating because it validates the harness:
the blank of the same cost is *also* an 8-MV sorcery, so it is *also* a miracle
target worth 6 cheated mana — the mv_cheated cancels exactly, leaving −0.17
±0.16. Everything Invincible Hymn does beyond occupying an 8-drop sorcery slot
is a life total, and life decides nothing. **MODEL-BLIND: a low score here is
evidence about the model, not the card.** If you want it for the "I cannot be
burned out" case, this simulation cannot tell you anything about that.

**Goldspan Dragon** is the same finding as Brass's Bounty in the first batch:
9.7 Treasures a game, and treasures are not this deck's bottleneck. It now gets
its haste modelled (the engine previously special-cased only the commander's),
and it still does not clear. Its "becomes the target of a spell" Treasure is
unmodelled — the opponent model has no spell-level targeting — so it is a mild
floor, but not by enough to change the verdict.

## Verdict on the second batch

- **Karlov: Enlightened Confidant** — take it over Dark Confidant despite the
  near-identical numbers, because one is a floor and the other is a ceiling.
- **Lorehold: Caldera Pyremaw** — clearest add of the seven, at a measured cost
  in mv_cheated.
- **Hold:** Reverse the Sands (real but narrow), Crypt Ghast (ramp a low-curve
  deck does not need).
- **Pass:** Goldspan Dragon, Invincible Hymn.

Nothing here is staged. The Karlov list has already absorbed three changes this
session and a fourth two-drop plus another land-light draw engine is worth
playing before adding.


---

# POD v2 - making life a real resource (2026-09-04)

Built in response to the finding above that life decides nothing. **Opt-in and
defaulted off**: `dict(DEFAULT_CFG, **POD_V2)`. `validate.py` still prints
`+0.00` on all six with `corr = 0.8929`, so every existing number reproduces
exactly until a run asks for the new pod.

    POD_V2 = {"combat_targeting": "open", "incidental_rate": 1.0, "clock_shift": 2}

## Step 2 first: the targeting rule was backwards

`incidental_damage` used `your_share` - threat-weighted - so **the better your
board, the more combat damage you took.** That is right for removal and exactly
wrong for combat: creatures swing at the player who cannot block, and a wide
board is a deterrent, not a magnet. `opponents.combat_share` replaces it with a
normalised inverse - each attacker picks among the three other players weighted
by `1 / (1 + blockers)`. Empty board against opponents holding five each: you
eat ~75% of the pod's attacks. Board of seven: ~27%, just under the neutral 1/3.

This is the change that lets the model express deterrence at all, and it is
correct independent of any calibration.

## Step 1: two knobs, because pressure and lethality were the same dial

Raising `incidental_rate` alone does not move kills from the clock to combat -
it stacks a second kill mechanism on the first. At rate 2.0 Rendmaw's loss rate
goes 0.691 -> 0.965 and its win rate collapses to 0.035. So `clock_shift` was
added to pay the lethality back: the clock is a deus ex machina that eliminates
a player regardless of the board, and it is the thing you give up when combat
starts doing real work.

`fit_pod.py` sweeps the 25-point grid. Its mechanical best is **(1.2, 4)**,
which reaches a 0.65 life-share - but costs Rendmaw and Lorehold ~25% of their
win rate, i.e. a full re-baseline of the project.

**I did not take it, because the 0.65 target is invented.** I searched for data
on how Commander players are actually eliminated and found none - the available
material is anecdote and rules explanations, not survey data. Fitting the whole
model to a number I made up would be the exact failure mode this project's notes
warn about. What *is* anchored is game length: the Command Zone's 100+ game
sample puts the average game at turn 10.29 with 70% between rounds 8 and 12.

So the setting chosen is **(1.0, 2)** - the point that preserves the existing
calibration while making life non-inert:

| metric | baseline (v1) | POD_V2 | fit's best (1.2, 4) |
|---|---|---|---|
| win r/l/k | 0.295 / 0.220 / 0.428 | **0.290 / 0.188 / 0.454** | 0.281 / 0.173 / 0.498 |
| turns r/l/k | 12.1 / 13.5 / 11.7 | 12.9 / 13.3 / 12.6 | 13.1 / 13.1 / 13.0 |
| life-share of losses | 0.00 / 0.00 / 0.00 | **0.31 / 0.51 / 0.21** | 0.65 / 0.72 / 0.45 |

**The life-share now varies by deck, and that is the whole point.** Lorehold
runs eleven creatures and gets attacked (0.51); Karlov is creature-dense and
gains life and does not (0.21). The old model could not express that difference
at all - it was 0.00 for everyone.

Both v1 and v2 run long against the 10.29 anchor. That is a **pre-existing**
calibration gap, not one introduced here, and it should not be fixed by
shortening clocks - that would undo the change.

## Does it change any decision? Mostly no, with one honest downgrade

All five staged swaps re-measured under POD_V2, 6,000 paired games. The
`reverified` field on each `Change` carries the detail.

| swap | win T10 (v1 -> v2) | win T20 (v1 -> v2) |
|---|---|---|
| karlov 3-for-3 | +0.0397 -> **+0.0483** | +0.0617 -> **+0.0773** |
| rendmaw Cauldron | +0.0025 -> **+0.0018 (now inside its bar)** | +0.0158 -> +0.0155 |
| lorehold Sunbird | +0.0077 -> +0.0060 | +0.0215 -> +0.0108 |

- **Karlov's package gets better**, which is the expected direction: it adds two
  blockers and a lifelinker to a deck that is now taking real attacks.
- **Rendmaw's Cauldron loses significance at 10 turns** - CI `[-0.0002, +0.0038]`
  where it previously just cleared. It was always the thinnest of the five. The
  decision stands on the 20-turn result and on damage, but it is now explicitly
  a long-horizon call and is the first of the five to revisit.
- **Lorehold's Sunbird halves at 20 turns** but stays significant at both.
  Lorehold is the deck POD_V2 punishes hardest.

## The payoff: cards the old pod could not price

Re-measured under POD_V2, T20, n=3,000, value over a same-cost blank:

| card | old pod | POD_V2 |
|---|---|---|
| **Invincible Hymn** | -0.02 dmg, -0.0007 win (an exact blank) | **+1.36 +-0.48 dmg, +0.0097 +-0.0041 win**, final life +2.96 |
| Enlightened Confidant | +1.80 dmg, +0.0097 win | **+3.77 +-1.05 dmg, +0.0170 +-0.0081 win** |
| Dark Confidant | +2.26 dmg, +0.0090 win | +2.35 +-1.04 dmg, +0.0097 +-0.0079 win |

**Invincible Hymn went from provably unmeasurable to a real card.** That is the
validation that the change did what it was built for.

And the judgement call from the second batch is now a measurement rather than an
argument: under v1, Enlightened Confidant and Dark Confidant were a near tie
(+0.0097 vs +0.0090) and I recommended the former on the grounds that one number
was a floor and the other a ceiling. Under v2 the gap opens to **+0.0170 vs
+0.0097** - lifelink is worth something once combat is real, and Bob is not.

Dark Confidant's own drawback is *still* barely priced (final life +0.50 +-0.81):
Karlov has the lowest life-share of the three decks at 0.21, so even the new pod
does not punish it much. That caveat survives.


---

# POD v3 - archetypes, and it is now the DEFAULT (2026-09-04)

A bracket says how POWERFUL an opponent is. It says nothing about what KIND of
deck they are, and that is what decides whether your life total is under
pressure. Three bracket-3 control decks and three bracket-3 aggro decks were
the same pod to the old model and are completely different games to play.

`opponents.ARCHETYPES` adds aggro / midrange / control / combo, each a set of
multipliers on the existing bracket parameters - creature development, damage
per creature, spot/sweeper/counter density, and a clock offset. One archetype
is drawn per opponent from the dedicated pre-rolled stream, so CRN survives.

## The discipline that makes this safe

**Every multiplier is normalised so its weighted mean across archetypes is
exactly 1** (and the clock offset exactly 0), verified in code. The average pod
is therefore identical to the no-archetype pod *by construction*, so archetypes
add VARIANCE BETWEEN PODS rather than quietly making the game harder or easier.
That is what lets them be adopted without re-baselining the calibration
everything else rests on:

| | POD_V2 (no archetypes) | POD_V3 (archetypes) |
|---|---|---|
| win r/l/k | 0.295 / 0.182 / 0.444 | 0.286 / 0.181 / 0.445 |
| turns r/l/k | 12.9 / 13.3 / 12.8 | 12.3 / 12.7 / 11.9 |
| life-share of losses | 0.33 / 0.50 / 0.21 | 0.32 / 0.43 / 0.20 |

The raw multipliers are judgement, not measurement - no data on the EDH
archetype mix was found, and `cfg["archetype_weights"]` is the knob. What is
*not* a judgement call is the normalisation.

## It does what it was built to do

Karlov, 6,000 games, split by how many aggro decks the pod happened to contain:

| aggro opponents | n | win rate | final life | life-share of losses |
|---|---|---|---|---|
| 0 | 2524 | 0.435 | 34.6 | **0.06** |
| 1 | 2582 | 0.466 | 35.7 | 0.23 |
| 2 | 798 | 0.470 | 35.7 | 0.52 |
| 3 | 96 | 0.312 | 21.9 | **0.79** |

Facing no aggro decks your life is nearly irrelevant; facing three it decides
four losses in five. **That conditionality is the thing the model could not
express before**, and it is what makes "is lifegain good?" a question with a
real answer rather than a single global number.

## Made the default

`DEFAULT_CFG` now carries `combat_targeting="open"`, `incidental_rate=1.0`,
`clock_shift=2`, `archetypes=True`. `POD_V1` in `experiment.py` restores the
previous pod exactly, so any earlier number in the project can be reproduced.

`validate.py` still prints **`+0.00` on all six metrics**; `corr(A,B)` moved
0.8929 -> 0.8927 and CRN is still worth ~9x.

All three ablation tables were regenerated against this pod. Every table dated
before 2026-09-04 is void.

## The result that justifies the whole exercise

**The new pod changed which cut is correct in Rendmaw, and the mechanism is
confirmed by a controlled test.**

Cauldron of Essence was staged against Ornithopter of Paradise. That measured
fine on the old pod and then decayed as the model improved:

| pod | win T10 | win T20 |
|---|---|---|
| v1 | +0.0025 [+0.0005, +0.0045] | +0.0158 |
| v2 | +0.0018 [-0.0002, +0.0038] | +0.0155 |
| v3 | **-0.0015 [-0.0037, +0.0007]** | +0.0088 |

Ornithopter of Paradise is a 0/2 BODY as well as a mana dork; Cauldron is not a
creature. Under pod v3, creatures attack whoever cannot block, so a spare
blocker is worth something the old pod priced at exactly zero.

Same card in, three different cuts, pod v3, 20 turns:

| cut | what it is | win rate |
|---|---|---|
| Idol of Oblivion | noncreature artifact | **+0.0135 [+0.0088, +0.0182]** |
| Ornithopter of Paradise | 0/2 body | +0.0088 [+0.0038, +0.0138] |
| Dockside Chef | 1/2 body | +0.0048 [+0.0000, +0.0097] |

Monotonic in whether the cut was a body. **The Rendmaw staging was changed to
cut Idol of Oblivion instead**, which restores significance at both horizons.

The other four staged swaps hold under pod v3:

| swap | win T10 | win T20 |
|---|---|---|
| karlov 3-for-3 | +0.0362 [+0.0300, +0.0425] | +0.0638 [+0.0550, +0.0727] |
| lorehold Sunbird | +0.0032 [+0.0005, +0.0058] | +0.0167 [+0.0103, +0.0228] |


---

# Evasion, and three correctness fixes (2026-09-05)

Queued work item 1 was "flying/reach evasion in `opponents.damage_through` —
still missing, and now load-bearing". It was load-bearing twice over by the
end: Rendmaw's Birds fly, and two of the three cards just committed to Karlov
(Starscape Cleric, Exemplar of Light) are fliers whose numbers were floors
because of it.

## 1. Evasion

Until now there was no evasion term of any kind — a 2/2 flier and a 2/2 ground
creature were identical to the model. `damage_through` now splits attackers and
blockers:

* `flier_block_share` (0.30) is the fraction of an abstract opponent board
  assumed able to catch a flier — fliers plus reach.
* Rendmaw's goaded Birds count in FULL rather than by that share, because they
  demonstrably fly: the card says "2/2 black Bird creature token with flying".
  CLAUDE.md noted `goad_block_share` was "standing in for" evasion; it no
  longer has to.
* A defender spends flying-capable blockers on the biggest fliers first, then
  anything spare on the ground. Ground-only blockers can never touch a flier.

Sanity check, six-creature opponent board, four 3/3 attackers of 12 power:
ground gets 3 through, fliers get 9.

### The tags are generated, not remembered

`tag_flying.py` reads Scryfall and writes `edhmc/decks/_evasion.py`; the deck
modules set `flying=name in FLYING` in their `C()` helper, so a card cannot be
added untagged. This matters more than it sounds, because **a first pass that
matched the word "flying" in oracle text got it wrong in both directions**:

* **Reach's reminder text contains "flying"** — "Reach (This creature can block
  creatures with flying.)" — so Longshot, Arasta, The Dawning Archaic and
  Rendmaw itself were all tagged as fliers. None of them fly.
* **Token-making text contains it too.** Rendmaw makes flying Birds and
  Bitterblossom makes flying Faeries; neither card flies.

Scryfall's `keywords` array carries only what a card unconditionally has, which
is exactly the question. Result: **9 unconditional fliers** across the three
decks, not the 14 the text match claimed.

Three fliers are CONDITIONAL and cannot be a static tag. They live in
`opponents.flying_of()`: Serra Ascendant (30+ life), Voice of the Blessed (4+
counters), Dragon's Rage Channeler (delirium — four card types in the yard,
now computed). Flying tokens are verified the same way: Bird, Faerie, Pegasus
and Angel fly; Saproling, Zombie, Snake, Monk, Goat, Spider, Plant and Wurm do
not.

## 2. Blood Artist was being paid 3x its real drain

Checked against oracle text, and all three "aristocrat" effects turned out to
be different cards:

| card | text | was | now |
|---|---|---|---|
| Blood Artist | "**target player** loses 1 life and you gain 1" | 3 pod dmg, no life | **1 dmg to one opponent, +1 life** |
| The Meathook Massacre | "each opponent loses 1 life" (the life-gain clause is for OPPONENTS' creatures dying) | 3 pod dmg, no life | 3 pod dmg, **still no life** |
| Cauldron of Essence | "each opponent loses 1 life and you gain 1" | 3 pod dmg, +1 life | unchanged |

This was flagged when Cauldron was first measured and is now fixed. It cuts
against Cauldron — it deflates the aristocrats baseline that card is measured
alongside — and Cauldron survived it.

## 3. The own-wipe commander bug is fixed, and it was worse than measured

`resolve_own_wipe` removed your commander without returning it to the command
zone. It was measured at roughly a point of damage per self-wipe and gated
behind `own_wipe_commander_returns`, defaulted to the old behaviour. Now
default-on, and the earlier measurement **understated it for Lorehold**:
`commander_cast` stayed True, so the MIRACLE ENGINE KEPT RUNNING with Lorehold
off the battlefield. Correcting it cut the deck's baseline `mv_cheated` from
31.0 to 22.6.

## 4. `ablation.py` now asserts its own classification

The bug from earlier today — five implemented cards printed as MODEL-BLIND
because the hand-maintained `SCRIPTED_*` sets were never updated — can no
longer happen silently. `check_scripted_coverage()` raises if any nonland card
is in neither `SCRIPTED_*` nor a new explicit `KNOWN_BLIND` set, and warns on
names left behind by a cut. `KNOWN_BLIND` was populated with exactly the cards
that were already blind, so no classification changed: "blind by default"
became "blind by declaration".

## What it did to the tables

`validate.py`: `+0.00` on all six, and `corr(A,B)` **improved 0.8927 → 0.9045**
(CRN now worth ~10x). All three tables regenerated; every earlier one is void.

Evasion is not a uniform buff — it reranks:

* **Karlov's fliers rose.** Starscape Cleric's win rate went +0.0108 →
  **+0.0167**, now the joint-best in the deck. Archangel of Thune holds the top
  damage slot at +4.81. Serra Ascendant leads T10 damage at +3.60, its
  conditional flying doing real work.
* **Rendmaw's Bitterblossom rose to +0.0205 win**, the second-best in the deck,
  because its Faeries fly and nothing in the pod blocks them.

Both staged swaps were re-measured and both hold:

| swap | win T10 | win T20 |
|---|---|---|
| rendmaw −Idol +Cauldron | +0.0030 [+0.0008, +0.0053] | +0.0108 [+0.0060, +0.0157] |
| lorehold −Scroll Rack +Sunbird | +0.0008 [−0.0017, +0.0033] | +0.0173 [+0.0112, +0.0232] |

Lorehold's ten-turn margin is now inside its bar — the own-wipe fix compressed
every miracle payoff in that deck — so it is a long-horizon call. Rendmaw's is
stable, which answers the earlier worry that it decays as the model improves:
it decayed against Ornithopter because that cut was a BODY, and it is steady
against Idol, which is not.
