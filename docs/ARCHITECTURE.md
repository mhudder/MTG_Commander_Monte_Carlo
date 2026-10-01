# Architecture

How the pieces connect, and the three structural facts that explain most of
the project's recurring bugs. **Durable by design: no counts, no dates, no
numbers** — those live in `docs/STATUS.md`, which is generated. What this file
claims about the tree is checked by `python -m tools.check_docs`: every
module under `edhmc/` and `tools/` must be named here, so a file cannot be
added without this map saying where it sits.

Read `HANDOFF.md` first if you are new; read this when you are about to change
code and want to know what else it touches.

---

## The map

```
   tools/                 entry points, always `python -m tools.<name>` from the repo root
   ─ ablation.py          leave-one-out table for one deck; caches to results/caches/
   ─ candidates.py        value-over-a-blank for ADDITIONS, batches keyed by name
   ─ validate.py          A/A control + CRN audit; must print +0.00 everywhere
   ─ check_unchanged_decks.py  did a shared-code change move a deck's baseline?
   ─ check_docs.py        do the docs still describe the repo? (runs the generators)
   ─ status.py / knobs.py / cache_manifest.py / tag_flying.py   the four GENERATORS (--write)
   ─ removal_census.py    the fifth: classifies every answer and wipe in every list
                          from Scryfall into decks/_removal.py (§0z87)
   ─ audit_cards.py       every card against Scryfall
   ─ card_known.py        is a card already in a list, a catalog, a candidates
                          batch, the ledger or an engine? DERIVED -- candidates.py
                          names constants, so grepping it for a card name cannot
                          work, which is how a measured card was called unmeasured
   ─ triage.py            can the engine SEE a card (tier 0: channels derived from
                          the object, or a clause screen of the oracle text), and
                          does its counter fire (tier 2, --smoke). Its acceptance
                          test is EXACT: a blind card plays identically to a
                          matched blank under CRN (item 23, §0z66)
   ─ compare_decks.py / fit_pod.py / tutor_policy.py / build_tivit_xlsx.py   older one-purpose tools
   ─ regen_tables.sh      every deck's table at the common N, in series
   ─ rebuild_deck.sh      ONE deck's table, as one leg of a parallel rebuild: checks
                          out a commit, rebuilds, stamps a provenance SHARD, pushes
                          its three files. The protocol is .claude/skills/
                          parallel-rebuild (§0z94)
   ─ _generated.py        shared helper: git ref + the provenance mask the checks compare with

   diagnostics/           one-question harnesses: diag_* measure a MECHANISM, run_* measure a CHANGE
   tests/                 tests that pin a claimed mechanism; `python -m tests` runs them all

            │ every one of these asks the registry which engine and files a deck has
            ▼
   edhmc/registry.py      ONE DeckSpec per deck: engine, colour identity, table metrics,
                          fingerprint files. Checked against decks/ at import (§0z32).
            │ and builds a deck through
            ▼
   edhmc/pending.py       the LEDGER and the deck builder
                          build_pending(deck) = decks.<module>.build() + the staged CHANGES
                          states: PROPOSED → MEASURED → STAGED (CHANGES) → COMMITTED, or WITHDRAWN
                          plus the checks that keep those lists honest (check_proposals, …)
            │
            ▼
   edhmc/experiment.py    the paired A/B harness: run_ab, analyse, report, DEFAULT_CFG,
                          POD_V1/V2/V3, repl_priority (the blank's priority — one place, on purpose)
            │  sim=<engine>.simulate(deck, commander, cfg, seed) -> dict of metrics
            ▼
   ┌──────────────────────────────── the seven engines ────────────────────────────────┐
   │ engine.py    Rendmaw's engine AND the shared primitives every other engine imports   │
   │ lorehold.py  miracles / top-of-library      karlov.py   lifegain triggers / drain    │
   │ tivit.py     votes / artifact tokens (+ voting.py)   shilgengar.py  Blood / reanimate │
   │ azusa.py     landfall / extra land drops / animated lands                            │
   │ trostani.py  tokens / populate / Trostani's lifegain off what enters                │
   └───────────────────────────────────────────────────────────────────────────────────┘
            │ each one owns a <Name>Game class and a module-level take_turn() + simulate()
            │ each one imports from engine.py: Card, Permanent, Board, ManaUnits, can_pay,
            │   available_mana, spend, play_land, run_etb, choose_mode, engine_cfg,
            │   CRNStreams, crn_random/crn_randrange/crn_shuffle, make_rng, seal_rng
            ▼
   edhmc/opponents.py     the shared pod: make_pod (every opponent roll PRE-ROLLED into a grid
                          so it cannot break CRN), removal / wipes / counterspells, threat and
                          targeting, blocking, combat_damage (one attack split across defenders),
                          incidental damage, the opponents' clocks, your own wipes
                          — imports engine.py LAZILY (engine imports it first); talks to an
                          engine only through g.* attributes and hasattr() (see "the protocol")

   edhmc/decks/           one module per commander, "<name>_v<N>.py", built by C()/L() factories.
                          discover_current_decks() picks the highest N per name — an old version
                          stays importable and is shadowed, never deleted.
   edhmc/decks/_evasion.py  GENERATED by tools.tag_flying from Scryfall keywords: FLYING,
                          INDESTRUCTIBLE, and the land/creature SUBTYPE sets (FOREST, HUMAN, …)
   edhmc/decks/_removal.py  GENERATED by tools.removal_census: the pod's DESTROY SHARE per kind
                          of answer (spot, wipe, ae), which prices indestructible (§0z87).
                          Both files are in every cache fingerprint and carry a SCANNED set
                          that check_docs compares with the current lists

   results/               every table and harness output; results/caches/ holds the ablation
                          caches and PROVENANCE.json (built-at fingerprints, stamped by ablation.py)
   spreadsheets/          the .xlsx system of record for the decks that have one
   docs/                  STATUS / KNOBS / ABLATION_CACHES (generated), HISTORY, this file,
                          the oracle audits, the comprehensive rules, archive/
```

## One measurement, end to end

1. `build_pending("karlov")` builds the module's list and applies that deck's
   entries in `pending.CHANGES`, in order, then validates 99 cards, singleton,
   commander distinct.
2. `experiment.run_ab` (or `ablation.columns`, or `candidates.add_value`)
   makes deck B by swapping one slot IN PLACE — `_swap_many` keeps the library
   position, which is what lets common random numbers cancel the other cards.
3. For each seed, both decks go through the same `simulate`: `make_rng(seed)`
   shuffles and mulligans, `seal_rng` forbids any later use of that RNG, and
   every mid-game roll goes through `CRNStreams` (one addressed stream per
   named effect). The pod's rolls were pre-generated in `make_pod` from a
   separate stream seeded identically for both branches.
4. `take_turn` runs the engine's own phase order; at the end of your turn
   `opponents.pod_phase` runs, ONCE for every engine: chip damage
   (`incidental_damage`), then every clock that is due (`resolve_clocks`),
   then — if you are still in the game — the removal round
   (`opponents_act`). An engine with its own model of what opponents do on
   their turns (karlov's `opponent_activity`) passes it as `before_act`.
   Two engines ran removal first until 2026-09-17 (§0z30); the test
   `tests/test_mulligan_and_pod_order.py` fails if an engine calls the
   three parts itself again.
5. `simulate` returns the metrics dict; `analyse` bootstraps the paired
   difference per metric. `won` is the objective; everything else is a proxy.

## The protocol between opponents.py and an engine

`opponents.py` never imports an engine class. It reads these attributes off
the game object and discovers optional behaviour with `hasattr`:

| it reads / calls | meaning |
|---|---|
| `g.board`, `g.hand`, `g.graveyard`, `g.commander`, `g.commander_cast`, `g.commander_tax` | zones and the command-zone state. `g.commander` is also how commander damage finds its attacker -- by IDENTITY, `perm.card is g.commander` (§0z65) -- so an engine that rebuilds the commander's `Card` loses the rule silently |
| `g.turn`, `g.cfg`, `g.m`, `g.opponents`, `g.opp_rolls`, `g.counter_rolls`, `g.your_life`, `g.result` | turn, knobs, metrics, the pod, the pre-rolled grid, the race |
| `make_pod`'s grid, `engine.Snapshots` | the grid has `max(turns, pod_grid_rounds) + 2` rows, so a T10 game is exactly the first ten rounds of the T20 game on its seed; every engine's simulate loop calls `Snapshots.after_round` after each completed round and `attach` at the end, so one run reports every horizon (`snapshot_rounds`, §0z93). A new engine loop that skips either call breaks `tests/test_horizon_prefix.py` |
| `pod_turn(g)` | THE POD'S CLOCK: `g.turn` minus `g.m["extra_turns_taken"]` (§0z86). Every opponent-facing timer reads it -- kill clocks and their re-arm, the grid's row, when wipes, attacks and counters start, threat growth. An engine whose extra turns advance `g.turn` MUST count them in `extra_turns_taken`, or each one brings every kill a round closer; one that does not advance `g.turn` (lorehold) needs nothing |
| `g.has(name)`, `g.power_of(perm)` | the two hot helpers every engine defines |
| `g.on_creature_death(n, perm)` (optional) | aristocrats triggers when the pod kills a creature |
| `g.artifact_died(card)` (optional) | artifact recursion — only the engine that has the cards defines it |
| `g.counts_as_creature(perm)` (optional) | an engine whose lands can be creatures says so here |
| `g.known_win` (optional, read with `getattr`) | the name of a card whose next resolution wins and which the table has seen -- lorehold's Approach of the Second Sun. `known_win_share` floors your share of the pod's attention at `known_win_focus`, and `countered` treats a recast as maximum threat (§0z62) |
| `g.opponent_cast_on_your_turn(i)` (optional) | opponent `i` just cast a spell during your turn -- called from `countered()`, the only such spell the model has. Rendmaw defines it for March of the World Ooze (§0z47); `tests/test_march_elephant.py` fails if another engine grows one |
| `g.combat_hits` (optional, read with `getattr`) | an engine that sets it to `[]` before `combat_damage` gets back the attackers that CONNECTED -- the "deals combat damage to a player" question (§0z74). Shilgengar asks, for Seluma, and tivit asks for its commander's trigger (§0z91, `tivit_trigger_connects`); an engine that never sets it is untouched |
| `g.on_opponent_lost_life(o, loss)` (optional), `lost_life(g, losses)` | "WHENEVER AN OPPONENT LOSES LIFE" (§0z90). Every site that lowers an opponent's life collects `(opponent, loss)` and calls `lost_life` once the event has landed and eliminations are checked; it calls the hook once per opponent. Only karlov defines it (Exquisite Blood, Bloodthirsty Conqueror). A new site that writes `o.life -=` without `lost_life` is a trigger with a hole in it -- the same shape as `life_loss` below |
| `trample_of(g, perm)` | trample RIGHT NOW (§0z92): the generated `TRAMPLE` set, Lord of the Pit by name, the team after Overwhelming Stampede (`stampede_bonus`) or Craterhoof (`craterhoof_bonus`), and an azusa land animated with trample. `chump` then stops only `min(power, blocker_toughness x blockers)` of a blocked trampler |
| `o.cursed`, `life_loss(o, n)` | Selenia's Curse (§0z74). EVERY site where an opponent's life goes down asks `life_loss` -- combat, `damage_each`, `damage_single`, the goaded Birds, shilgengar's Massacre Wurm. A new site that writes `o.life -=` without it is a doubler with a hole in it (§0z4's shape) |
| `g.is_land_creature_now(perm)` (optional) | Autumn Willow's question, asked by `engine.on_mana_tap` and `spend`'s count fallback (§0z74). Only azusa can answer it, so only azusa defines it |
| `g.exiled_instead_of_dying(perm)` (optional) | a replacement effect that turns a death into an exile -- finality counters (§0z75). `destroy` asks it after removing the permanent: yes means no graveyard and NO death trigger. Shilgengar defines it; its own `sacrifice` asks the same question. Rendmaw defines it too, for Gloomshrieker's identical text (§0z83) -- this row said it had no hook until 2026-09-30 (§0z89) |
| `g.on_targeted(perm)` (optional) | the pod's spot removal has picked `perm` as its target -- "becomes the target of a spell" (§0z77). Called before `destroy`, whether or not the spell then kills it; NOT called when `try_protect` blanks the event, because that path names no target. Lorehold defines it, for Goldspan Dragon |
| `g.after_died(perm)` (optional) | called once the dead creature's CARD is in the graveyard -- by `destroy` after its graveyard step, and by shilgengar's own `sacrifice`. `on_creature_death` runs BEFORE the card gets there on the destroy path, so anything that moves the card back out lives here: Twilight Shepherd's persist (§0z84). Only shilgengar defines it |
| `protected_from_creatures(g)` | Serra's Emissary's chosen type, `emissary_type` "Creature" (§0z84): `damage_through` gives the pod no blockers and `incidental_damage` does not reach you. The clocks are untouched -- a roll is not a combat |
| `g.before_wipe()` (optional) | the pod's wrath is about to resolve and `try_protect` (a card from HAND) did not answer it -- a response from the BATTLEFIELD. Trostani defines it, for Selfless Spirit and King Darien's sacrifices |
| `g.indestructible_granted(perm)`, `g.flying_granted(perm)` (optional) | a GRANT, read by `indestructible_of` and `flying_of` beside the generated sets: the until-end-of-turn indestructible `before_wipe` buys, and Elspeth's emblem. Only trostani defines them; a grant that lives anywhere else is a second read site, which `indestructible_of`'s docstring forbids |
| `g.dying`, `simultaneous(g)`, `watching(g, name, perm, another)` | ONE removal event, and the look-back reader (§0z76, CR 603.10a). Both wipe paths open `simultaneous`, and `destroy` appends each casualty to `g.dying`; a death trigger asks `watching` how many of its source were on the battlefield just before the event -- the dying ones and, unless `another=True`, the creature dying itself. Every engine's death handler reads its payoffs this way, so a Blood Artist removed third in a wipe still sees all of it. `death_lookback=False` restores the live-board count |

If you add an engine, this table is the contract. If you add a method to one
engine that `opponents.py` will call, it must be optional (`hasattr`) or added
to all seven.

## Three structural facts

**1. Seven engines, one thin base class.** The shared code is module-level FUNCTIONS in
`engine.py` that take the game as an argument (`can_pay`, `spend`,
`play_land`, …). Anything written as a METHOD on a `<Name>Game` class has one
copy per engine. **Since §0z32 there is a base class**, `engine.BaseGame`, and the
methods whose six copies were identical or differed only by omission live on
it once: `has`, `count`, `draw` (karlov overrides for Alhammarret's
Archive), `deal_pod_damage`, `opening_hand`; and `engine.finish(g)` is the
tail of `simulate()` that assembled the output dict six times. What is still
per engine and meant to be: `__init__`, `power_of`/`toughness_of`,
`on_creature_death`, `make_permanent`, `gain_life`, and `take_turn`. **A rule that lives in a method drifts; a rule that lives in a function
does not.** Every §0u finding in `KNOWN_ISSUES.md` is an instance. Known
drift today, said here so nobody rediscovers it:

| rule | where it is written | how the copies differ |
|---|---|---|
| ~~the fourth failed mulligan~~ | CLOSED 2026-09-17, `engine.london_mulligan` ×1 | was: `engine.py` redrew seven; `lorehold.py` kept an EMPTY hand; the other four left the seven cards in hand AND back in the library. §0z30, pinned by `tests/test_mulligan_and_pod_order.py` |
| ~~end-of-turn pod order~~ | CLOSED 2026-09-17, `opponents.pod_phase` ×1 | was: four engines ran damage → clocks → removal; `karlov.py` and `tivit.py` ran removal → damage → clocks. Worth +0.0647 win rate to tivit's baseline, §0z30 |
| the `turns` default when no cfg supplies one | `simulate` ×6, `make_pod` | 10 in three places, 20 in four (acknowledged in `docs/KNOBS.md`; every harness passes it explicitly) |

The per-game metrics dict is an `engine.Metrics` (§0z31): it reads 0 for a
name nothing has written, so a `+=` on a metric missing from an engine's
literal is a count, not a `KeyError` in a worker. The literals are still the
documented set; the class is the net under them.

**2. Behaviour attaches BY NAME at least as often as by `script=`.** A card
with no `script` can still be fully implemented, dispatched by `g.has("…")`
or `card.name == "…"` inside an engine, `opponents.py`
(`GRANTS_INDESTRUCTIBLE`, `WIPE_*`), or `engine.py`'s own tables
(`DEVOTION_CONDITIONAL_CREATURES`, `PAIN_ON_COLOURED_TAP`, …). Before calling
a card unimplemented, **grep every engine for its name** (§0z25). And every
such name set is a claim that rots, so each carries a coverage check —
`check_scripted_coverage`, `check_wipe_coverage`, `check_land_enabler_coverage`,
`check_planeswalker_coverage`, `check_dynamic_pt_coverage`,
`check_dynamic_cost_coverage`, `check_alt_cost_coverage`, `check_proposals` —
and a new one needs its check in the same change (§0q).

**3. A deck is registered ONCE, in `edhmc/registry.py`** (§0z32; until
2026-09-17 it was registered in eleven places by hand). `DECKS[name]` is a
`DeckSpec` — engine, colour identity, the table's metric columns, extra
fingerprint files — and it is checked against `decks/` discovery at import,
so a module without a spec or a spec without a module refuses to import.
`ablation.py`'s `SIMS`/`METRIC_SETS`, `cache_manifest.py`'s `PER_DECK`,
`check_unchanged_decks.py`, `status.py`, `pending.py`'s `DECK_IDENTITY` and
the tests all derive from it. What is still hand-written per deck, because
it is a decision and not a fact: `ablation.py`'s classification sets,
`pending.py`'s candidate catalog, and `validate.py`'s CRN audit case — and
`validate.py` now refuses to run with a deck missing from that list.
`HANDOFF.md` carries the checklist.

## Where a card's behaviour can live

**Adding a card follows a procedure, and it is written down:**
`.claude/skills/add-card/SKILL.md`. This section is the map it points at —
read it when a card "does nothing" in a table, and read the skill when you
are putting one in.

When a card "does nothing" in a table, look in this order:

1. `decks/<deck>.py` — is it in the list at all? (`build_pending` applies staged
   swaps; the module's list is not the measured list.)
2. `tools/ablation.py` — is it `SCRIPTED`, `PARTLY_MODELLED` or `KNOWN_BLIND`?
   The category is a claim; the table prints the row under it.
3. the engine — `script=` dispatch in `run_etb`/`resolve`/`upkeep`/`activations`,
   or by NAME anywhere. Then `engine.py`'s shared tables, then `opponents.py`.
4. the mechanism counter in `g.m` — a counter at zero is unmistakable where a
   low win rate is not. **Check `cards_drawn` against the sum of every draw
   counter**: a draw credited to the wrong counter looks like a correct
   implementation from the counter it was supposed to hit.

## Pitfalls, written down by the sessions that hit them

These are the traps a new agent walks into on this repo. Each has a check or a
command; use it rather than remembering.

- **A test that is not run does not exist.** The pinned tests live in `tests/`
  and nothing ran them automatically; a mechanism regression survived three
  commits with its own test failing the whole time. `python -m tests` runs
  every module and fails if any fails. It is in the closing protocol now.
- **`$?` after a pipe is the exit code of the LAST command in the pipe.**
  `python -m tests.test_ashaya | tail; echo $?` reports `tail`. Use `python -m tests`,
  or `set -o pipefail`.
- **Two cards hooked at one site are one indentation away from being one
  card.** The Great Henge and Guardian Project share the "nontoken creature
  entered" hook in `azusa.make_permanent`; inserting the second swallowed the
  first's draw into the new `if`. When you add to a shared hook, re-run the
  test that pins its neighbour, and read the mechanism counters of BOTH cards.
- **`check_unchanged_decks` compares BASELINES.** A card that is not in the
  built list is invisible to it, so it can certify a cache while a candidate's
  implementation is broken. It answers "did the deck move", not "is the card
  right". The card's own test answers that.
- **Generated docs are only as current as their last `--write`.**
  `python -m tools.check_docs` runs every generator and diffs; run it before
  every commit, and regenerate `docs/STATUS.md` in the SAME commit as whatever
  moved it. A hand-typed count anywhere in prose (knobs, sections, lines) is
  already wrong.
- **`ablation.py` USED TO read `sys.argv` at import** -- fixed in M4
  (2026-09-17), when its parameters became a `Run` object. It is safe to
  import now (`tools/triage.py`, two tests and `pending.py` do), and
  `experiment.repl_priority` is where it is for the older reason.
- **The metrics dict is a plain dict.** `g.m["new_counter"] += 1` on a key not
  registered in `__init__` is a `KeyError` in a worker, in the minority of
  games where the card resolves, twenty minutes into a run. Register the key.
- **A draw off an empty library is a LOSS (§0z42), and whether a draw is a
  choice is the CARD's to say.** Every draw goes through `BaseGame.draw`,
  karlov's Archive override or lorehold's `draw_card`, and each calls
  `engine.drew_from_empty`. A new draw that the card text makes optional (a
  "may", an activation, a mode, a spell the pilot need not cast) must ask
  `engine.draw_is_safe` first -- or the pilot decks itself in the games it
  is winning, which is what the rule alone did to azusa and lorehold. A
  mandatory draw must NOT ask. Popping the library without drawing (exile,
  mill, reveal, "put it into your hand") is not a draw and does not lose.
- **A mana unit that is POPPED rather than passed to `spend` is never
  tapped.** Rendmaw's Treasures (§0z64) are units whose owner, a
  `TreasureMana`, sacrifices the token when `spend` taps it. Skullclamp's
  loop in `engine.activations` pops the units it uses and pays through
  `spend`'s count fallback, which taps a board permanent instead -- so a
  Treasure it used stayed on the pile until `tap_treasures` was added. Any new
  loop that pops units must tap their owners itself.
- **`chump`'s items carry a KEY now** (`(power, cost, key)`), and its optional
  `blocked` list collects the keys it blocked -- that is how
  `damage_through(..., unblocked=[])` reports which attackers got through,
  for commander damage (§0z65). A replacement `chump` (a mutation, a
  diagnostic) must keep both, or commander damage reads a different block
  than the damage total did.
- **`engine_cfg` copies the cfg** because five engines `setdefault` their own
  knobs into it; construct games on a fresh `dict(DEFAULT_CFG, …)` and never
  share one dict across engines.
