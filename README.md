# EDH Monte Carlo — paired A/B testing for Commander decklists

> **New here? Read `HANDOFF.md` first.** This file is the methodology writeup and
> parts of it predate the opponent clock and the Karlov deck. Trust it on
> technique; trust `HANDOFF.md` on current state, files and commands.

A simulator plus a statistical harness for answering "is card X better than card
Y in this deck?" with a number and a confidence interval instead of a vibe.

```
edhmc/engine.py             Rendmaw engine (mana, lands, casting, combat, triggers)
edhmc/lorehold.py           Lorehold engine (miracle windows, top-deck manipulation)
edhmc/karlov.py             Karlov engine (lifegain triggers, drain, alt win cons)
edhmc/opponents.py          three opponents: removal, counters, wipes, blocking, CLOCKS
edhmc/experiment.py         paired A/B harness, bootstrap CIs, n-for-n swaps
edhmc/pending.py            staged deck changes + list validation
edhmc/decks/*.py            deck definitions (costs, type lines, card scripts)
ablation.py                 rank every card in a deck; caches and resumes
candidates.py               score possible ADDITIONS without choosing a cut
tutor_policy.py             learn a tutor target policy by randomised experiment
compare_decks.py            cross-deck comparison at matched settings
validate.py                 A/A control + CRN measurement
```

Requires Python 3.10+, numpy, scipy. Run from this directory:

```bash
python -m edhmc.pending            # staged changes; validates all three lists
python validate.py                 # A/A control — must print exactly +0.00
python ablation.py karlov 2500 20  # or rendmaw / lorehold
```

---

## The core problem: signal vs. noise

One card is 1% of a Commander deck, and game-to-game variance is enormous. A
naive simulation needs absurd sample sizes to see a one-card effect. Two
techniques do the heavy lifting.

**Common random numbers.** Deck A and deck B are the *same list* with one slot
swapped, shuffled with the *same* RNG seed. The 98 shared cards land in
identical library positions in both games, and the swapped card sits in the
same slot. Nearly all shuffle variance cancels in the difference.

Opponents get their own RNG stream, pre-rolled into a fixed grid at setup, so
they make the same draws in A and B no matter how the boards diverge and only
*respond* differently. Measured on this comparison: `corr(A, B) = 0.87`, paired
standard error is 2.7x tighter than independent sampling — worth about **7x the sample size**,
for free.

**Paired inference.** The harness analyses `D_i = metric(B_i) - metric(A_i)`
and bootstraps a CI on `mean(D)`. It never compares the two means separately.

`validate.py` runs an A/A control (same deck on both sides) which returns
exactly zero difference on every metric — confirming no randomness leaks
between the two branches.

---

## What the model does and does not know

**Modelled:** shuffling, London mulligans, land drops, tapped/untapped lands,
full colour requirements including `{C}`, mana rocks and dorks, cost reduction
(Foundry Inspector, The Great Henge), a greedy casting policy split into
pre- and post-combat mains, card draw, token generation, `Primal Vigor`
doubling, `Metallic Mimic` counters, static P/T setters, per-turn engine
activations, and combat against a 120-life pod.

**Modelled by `opponents.py`:** three opponents at mixed brackets (2/3/4), each
with spot removal, artifact/enchantment removal (including occasional sweepers),
a finite counterspell budget, and board wipes whose frequency scales with how
wide the table's biggest board has gotten. Removal is *threat-weighted*: the more
board you have relative to the rest of the table, the more of the pod's
interaction points at you. Rendmaw goes to the command zone on a wipe and gets
recast at +2 tax. Heroic Intervention is modelled as real protection. Blocking is
derived from opponents' creature counts against the weakest board at the table,
rather than a flat damage haircut.

**Still not modelled:** politics, stack interaction, tutoring, opponents' combat
against each other, your own decision quality, or graveyard recursion. Your own
removal spells (Assassin's Trophy, Beast Within, Eyeblight's Ending) remove an
opposing blocker rather than protecting you — they are answers, not shields.

Consequence: **absolute damage numbers still mean little.** Read the paired
difference, and treat card-draw metrics as more trustworthy than damage metrics.
The runner sweeps pod power level to show whether a conclusion survives.

About 30 cards carry hand-written scripts. The rest are correctly handled as
"a body with a mana cost and a type line" — which, for Rendmaw, is most of what
matters, since the commander only cares about the type line.

---

## Result: Skullclamp -> March of the World Ooze

20,000 paired games, 10 turns, mixed pod (brackets 2/3/4), threat-weighted
interaction. All differences are B - A, so positive favours March.

| metric | Skullclamp | March | diff | 95% CI |
|---|---|---|---|---|
| damage dealt | 25.45 | 28.30 | **+2.85** | [+2.64, +3.06] |
| cards drawn | 12.37 | 11.36 | **-1.01** | [-1.06, -0.96] |
| final board power | 15.63 | 16.66 | +1.03 | [+0.90, +1.16] |
| Rendmaw triggers | 5.92 | 5.75 | -0.17 | [-0.18, -0.16] |
| tokens made | 4.61 | 4.37 | -0.23 | [-0.25, -0.22] |
| mana wasted | 8.32 | 8.53 | +0.21 | [+0.18, +0.23] |

Conditional on drawing the card (18.3% of games): damage +15.55, cards -5.52.

### What interaction did to the answer

Adding removal, counterspells, and wipes cut March's damage margin by **more
than half**, and the margin shrinks monotonically as the pod gets stronger:

| pod | damage B-A | cards drawn B-A |
|---|---|---|
| no interaction (previous model) | +6.41 | -1.57 |
| all bracket 2 | +5.86 | -1.32 |
| mixed 2/3/4 | +3.09 | -1.00 |
| all bracket 3 | +3.16 | -1.08 |
| all bracket 4 | **+1.09** | -0.84 |

The mechanism is visible in the diagnostics. Of the games where you try to
deploy the card:

| | countered | destroyed |
|---|---|---|
| Skullclamp | 0.0% | 14.7% |
| March of the World Ooze | 20.5% | 36.7% |

March is answered roughly **57% of the time you try to deploy it**; Skullclamp
about 15%. A one-mana artifact sits below every opponent's counterspell
threshold and is almost never the best target for their enchantment removal.
A six-mana enchantment that makes your whole board 6/6 is the best target on
the table the moment it resolves.

Castability got worse too. P(March resolves by turn 10) fell from 13.9% without
counterspells to **9.6%** with them, against 18.2% for Skullclamp.

### Reading it

At bracket 2-3, March is clearly the better card. At bracket 4 the damage edge
is +1.09 (about 2% relative) against a card-draw deficit of -0.84, which is
close enough to a wash that the model cannot call it — and everything the model
still omits (rebuilding after a wipe, topdeck quality in long games, the fact
that ten turns is short) points toward the card-advantage plan rather than away
from it.

One structural caveat specific to the 10-turn limit you chose: March resolves on
turn 7.8 on average, so it only gets about two turns of exposure to removal
before the simulation ends. A 14-turn run would punish it considerably harder.
That is the single biggest remaining lever on this comparison, and it is a
one-line change: `run_ab(..., turns=14)`.

The original diagnostic is unchanged and is still the finding I would act on:
Skullclamp finds a legal 1-toughness target on **0.35 turns per game** in this
deck, because Rendmaw Birds are 2/2 and the clamp makes them 3/1. That is a
reason to cut Skullclamp regardless of what replaces it. Whether March is the
right replacement depends on the pod you actually play in.

## Result: the Lorehold 2-for-2

    OUT  Verge Rangers, Triumph of Saint Katherine
    IN   Molecule Man, The Dawning Archaic

12,000 paired games, 14 turns, mixed pod.

| metric | current | after swap | diff | 95% CI |
|---|---|---|---|---|
| **mv_cheated** | 18.08 | 20.88 | **+2.80** | [+2.60, +3.00] |
| total mv cast | 48.22 | 50.13 | +1.91 | [+1.69, +2.13] |
| **damage** | 37.47 | 36.62 | **−0.85** | [−1.28, −0.43] |
| — spell damage | 5.18 | 5.58 | +0.39 | [+0.29, +0.49] |
| — combat damage | 32.29 | 31.04 | −1.25 | [−1.65, −0.85] |
| **P(win by T14)** | 0.082 | 0.081 | **−0.0003** | [−0.0022, +0.0016] |
| free casts (Archaic) | 0.00 | 0.26 | +0.26 | [+0.24, +0.27] |

### The headline is the last row

`mv_cheated` rises 15.5%, and **win rate does not move at all**. At n=20,000 the
confidence interval rules out any win-rate change larger than about 0.6
percentage points in either direction.

This is the important result, and it is a correction to an earlier version of
this analysis that reported the swap as a clear improvement on the strength of
`mv_cheated` alone. Mana advantage is a proxy for winning, not a substitute for
it, and in this deck at this horizon the proxy and the outcome disagree.

The decomposition shows why. The Dawning Archaic's free casts do convert into
real damage (+0.39 spell damage), but cutting Verge Rangers costs more combat
damage than that (−1.25), because a 3/3 first striker attacking from turn 4
contributes more over fourteen turns than a 7/7 that arrives around turn 10 and
immediately draws removal.

### Attribution: still almost entirely The Dawning Archaic

| swap | mv_cheated B−A | damage B−A |
|---|---|---|
| Dawning Archaic only (for Verge Rangers) | **+2.46** | −0.52 |
| Molecule Man only (for Triumph) | +0.36 | −0.44 |
| both together | +2.80 | −0.85 |

The Archaic delivers ~88% of the mana advantage. Its cost reduction is why: by
turn 14 this deck averages **8.5 instants and sorceries in the graveyard**, so a
nominal {10} card actually costs about {2.45}.

Molecule Man reads like the stronger card — miracle {0} on every nonland beats
Lorehold's miracle {2} on instants and sorceries only — but it costs {6},
resolves on turn 10 on average, and is on the battlefield in only about 3% of
games by turn 14. It is close to a blank in the games where it does not resolve,
and it usually does not.

### Reading it

The honest summary is that this swap makes the deck **cast bigger things without
killing anyone faster**. If the goal is raw power and spectacle, take The Dawning
Archaic; the mana-cheat case for it is strong and robust across pod power and
game length. If the goal is winning, the model cannot find a difference.

The narrower change is better supported than the full one: cut Triumph of Saint
Katherine — a 5/5 lifelink body is the weakest miracle hit in a deck whose
payoffs are seven- to twelve-mana spells, and its death trigger shuffles the top
six cards of your library, which is precisely where this deck stores its
resources. Cutting Verge Rangers is the more questionable half, for a reason the
metrics do not name directly: it plays lands off the top when you are behind,
which **strips lands out of your top-deck**, and about 31% of miracle windows
fail simply because the card drawn was a land. It is a consistency card here,
not a ramp card.

### Caveats specific to this deck

**Damage is extremely skewed.** Mean damage is 37.5 but the median is 16 and the
90th percentile is 96. Storm Herd alone accounts for most of the top decile —
forty 1/1 fliers in one card. Read the median alongside the mean; the mean
describes a game this deck rarely has.

**Win rate is a low-power metric.** At 8% it takes large samples to resolve small
effects. The interval above is tight enough to be useful, but a change of a
quarter of a percentage point would be invisible.

**Horizon.** Run at 14 turns rather than the 10 used for Rendmaw, because
Lorehold resolves on turn 7.0 on average and a 10-turn window gives the deck
only about three turns of engine. The mana-cheat advantage grows with game
length (+1.02 at 10 turns, +3.90 at 16) and shrinks as the pod gets stronger
(+4.04 with no interaction, +1.84 against all bracket 4).

## Extending this

**Change the pod:**

```python
run_ab(deck, cmd, "Skullclamp", card, n=20000,
       cfg={"pod_brackets": (4, 4, 4)})     # or (2,2,2), or opponents=False
```

Other knobs in `DEFAULT_CFG`: `first_wipe_turn`, `block_share`, `hold_up_rate`
(how often you hold up Heroic Intervention), `counter_threshold` (how scary a
spell has to be before anyone counters it). Per-bracket removal, wipe, and
counterspell rates live in `BRACKETS` at the top of `opponents.py`.

**Swap several cards at once** (n-for-n, positions preserved so CRN still holds):

```python
run_ab(deck, cmd, ["Card A", "Card B"], [new_a, new_b], n=12000,
       cfg={"turns": 14}, sim=lh_sim)     # sim= picks the engine
```

**A different swap in the same deck:**

```python
from edhmc.decks.rendmaw_v11 import build, C
from edhmc.experiment import run_ab, analyse, report

deck, cmd = build()
new = C("Bala Ged Recovery", "Sorcery", {"gen": 2, "G": 1}, priority=3)
a, b, cfg = run_ab(deck, cmd, out_card="Pygmy Kavu", in_card=new, n=20000)
report(a, b, "Pygmy Kavu", "Bala Ged Recovery", cfg, analyse(a, b))
```

**A new deck** — copy `decks/rendmaw_v11.py` and rewrite the card lists. The
`C()` and `L()` helpers are the whole interface. Three things need care:

1. **Costs, not mana values.** The spreadsheets only store MV, which cannot
   express colour screw — and colour screw is exactly what a Monte Carlo run is
   good at surfacing. Costs in the deck file are hand-authored.
2. **`priority`** drives the greedy casting policy. If the sim is making
   obviously wrong plays, this is usually the knob.
3. **`script`** hooks into `run_etb` / `upkeep` / `activations` in `engine.py`.
   Only write one when the card's effect would change the *comparison*.
4. **`threat`** decides what eats the pod's removal. Anything that would make a
   table say "we have to deal with that" belongs above ~7. This is now one of
   the most load-bearing numbers in the whole model, and it is a judgement call
   rather than a measurement — worth sanity-checking before trusting a result.

**Commander-specific triggers** live in `Game.play_card_trigger`. For a
non-Rendmaw deck, replace that method — it is the only place the commander's
identity is baked into the engine.

### Two notes on the spreadsheet

- `Nameless Inversion` is listed at MV 3; its actual cost is `{1}{B}`, MV 2.
- `Darkmoss Bridge` is an Artifact Land and therefore **is** a Rendmaw trigger,
  but its "Rendmaw Trigger?" column is blank. The sim treats it as a trigger.

### Sample sizes

At 20,000 paired games (~40 seconds) the CI on the damage delta is about ±0.4
damage, which resolves effects down to roughly 1% of baseline. For coarse
"is this obviously better" checks, 2,000 games is plenty. Anything below ~500 is
not worth reading.

### Two engines

`engine.py` models decks that win by putting power on the board. `lorehold.py`
models a miracle/top-deck deck and has its own turn loop, because the archetype
is structurally different: its value comes from miracle windows, not combat.
Both share `opponents.py`, `can_pay`, and the mana model, and both plug into the
same A/B harness via `sim=`.

The Lorehold engine models damage from spells and tokens as well as combat —
Guttersnipe (2 to each opponent per instant or sorcery, so 6 a pop, which in a
fifteen-spell deck is the real clock), Soulfire Eruption (exile the top card per
target, damage equal to its mana value), Storm Herd, Emeria's Call, Boros Charm,
and Approach of the Second Sun as an alternate win condition. An earlier version
counted combat damage only, which in an eleven-creature deck captured roughly a
quarter of the deck's output and made the damage column close to meaningless.

Beyond damage, the Lorehold engine models: miracle windows (one on your draw step, three more
from Lorehold's rummage at each opponent's upkeep), the Library of Leng loop
(discard your bomb, it goes on top, draw it, miracle it), top-of-library
manipulation, Treasures, mana held up across turns for off-turn miracles, and
cost reduction that scales with the graveyard.

A policy note worth knowing about, because it was worth several points of
`mv_cheated` when it was wrong: a greedy "cast the biggest thing you can afford"
policy is actively bad in this deck. Hardcasting a seven-drop for seven when you
could miracle it for {2} is the single biggest mistake available. `hold_for_miracle`
declines to hardcast expensive instants and sorceries — but only when you
actually control a way to put them back on top, since otherwise they rot in hand.

### Ablation: ranking every card in a deck

`ablation.py` replaces each nonland card in turn with a neutral blank of the
same cost and measures the paired difference, giving a ranked contribution for
all 65 slots. It caches to `ablation_cache.json` and resumes, since a full pass
is about fifteen minutes on one core.

    python ablation.py rendmaw 3000 10   # or: lorehold 3000 14
    # rerun until it reports no cards left; it caches and resumes

The output is deliberately split in two. Roughly half the deck — every removal,
protection and wipe spell — is modelled as an inert body with a mana cost,
because opponents' boards are abstracted to a blocker count. Those cards all
ablate to about zero, and **that is a fact about the model, not the cards**. The
MODEL-BLIND table is not a cut list. Keep `SCRIPTED` at the top of the file in
sync when you script a new card.

Findings from the Rendmaw pass (3,000 paired games, 10 turns, mixed pod):

| tier | cards |
|---|---|
| strongest | Beastmaster Ascension (+3.75 dmg, **+0.021 win rate** — the largest win-rate contributor in the deck), Sol Ring (+3.54), **March of the World Ooze (+2.23, +0.008)**, Bitterblossom (+2.18), Ohran Frostfang (+1.81) |
| does nothing measurable | Primal Vigor (0.00), Idol of Oblivion (+0.09), Dockside Chef (+0.05), Leaden Myr (+0.05), The Great Henge (+0.16) |
| tests negative | Ornithopter of Paradise (−0.64), Coat of Arms (−0.16), Copper Myr (−0.10) |

Two notes on reading it. **The Great Henge and Primal Vigor score low because they
barely resolve**, not because the effects are weak — 9.8% and 11.3% of games
respectively, around turn 7.8. That is a curve problem, not a card-quality
problem, and the fix is ramp rather than a cut. Compare Beastmaster Ascension at
16.3% and turn 4.4.

And the negative scores in the MODEL-BLIND table are **pure artifacts**: those
cards cost mana in the simulation and do nothing, so the engine wastes mana
casting them. Overwhelming Stampede at −1.10 is the clearest case — it carries a
"pump" tag that makes the policy jam it precombat for no effect. Do not read that
as a cut.

Findings from the Lorehold pass (3,000 paired games, 14 turns):

| tier | cards |
|---|---|
| strongest | Storm Herd (+21.4 damage), Reforge the Soul (+1.78 mv), Rise of the Eldrazi (+1.73), Big Score (+1.28), Thrill of Possibility (+1.23) |
| dead weight | Approach of the Second Sun (−0.09 mv, −0.03 damage) |
| tests negative | Hidden Retreat (−1.68), Penance (−1.06), Scroll Rack (−0.78) |

The top of the ranking is almost entirely cheap card flow, which matches the
bottleneck diagnostic: the hand empties, which starves Lorehold's rummage, which
is the source of three of the four miracle windows per round.

The negative result on the paid top-setters splits cleanly on cost — the free
ones (Library of Leng +0.87, Sensei's Divining Top +0.29) test positive, the ones
charging 1-2 mana test negative. It survived two stress tests: disabling the
hold-for-miracle policy changed nothing, and making activation selective rather
than every-turn halved the penalty without flipping the sign. Treat it as
provisional rather than a cut list; Scroll Rack in particular does bulk
hand-to-library swapping that this engine cannot represent.

That second stress test was worth keeping: `set_top_gate` (default 4.0) now
requires a paid top-setter to save at least that much mana before firing, rather
than activating every turn. That is a play-policy fix, not a deck change, and it
raised the Lorehold baseline on its own — mv_cheated 19.98 to 21.35, damage 37.29
to 40.22.

### Where to be careful

The greedy casting policy is the largest source of model error, and it is not
neutral between cards — it systematically underrates cards that reward holding
mana or sequencing cleverly (instants, modal spells, X spells) and overrates
cards you just jam on curve. Before trusting a close result, check that the sim
is casting both cards at a sensible rate and turn; `run_swap.py` prints exactly
that in its diagnostics block for this reason.
