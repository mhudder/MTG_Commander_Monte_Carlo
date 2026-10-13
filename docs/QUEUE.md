# Queued work

**Open items only**, kept by hand. Each item keeps the number it was given
when it was queued, because `KNOWN_ISSUES.md` and the add-card skill cite
those numbers ("item 18", "queued 0c"). **Never renumber.** When an item
closes, move it verbatim to `docs/HISTORY.md` under a dated "Queued items
closed" heading, as every closed item before it was.

This list moved out of `CLAUDE.md` on 2026-10-10. It changes every few
sessions and carries dated measurements, and `CLAUDE.md` is loaded into every
session and carries neither. What is *staged* is never here: `python -m
edhmc.pending` is the ledger, and `docs/STATUS.md` prints it.

What is closed and where it went:

- 19, 15, 1b/3, 9, 10, 13, 14, 14-old, 14b, 16, 16b, 17-old, 11, 12, 8,
  8-old, 17, 21, 2, 4, 8b, 0b-i, 23 and 0c are closed, each in
  `docs/HISTORY.md` under "Queued items closed …".
- 20, 20-old, 20-old2, 22, 7 and 8c were answered or superseded, and are in
  `docs/HISTORY.md` under "Queued items answered or superseded, moved
  2026-10-10".

---

25. **REBUILD THE SIX ACTIVE TABLES** (queued 2026-10-13). §0z133 made
    eliminated opponents stop acting, as the default, and moved every deck
    at T20 (karlov +0.022, azusa +0.021, rendmaw +0.019, shilgengar +0.014,
    tivit +0.004, lorehold -0.005). The owner chose "default now, rebuild
    later": until the rebuild the six caches read SUSPECT, `check_docs`
    fails on that one check, and every table describes the old pod. Use the
    parallel-rebuild skill. Never clear them with `--verified`: the numbers
    moved. If POD_V4 is adopted first, one rebuild covers both.

20b. **TWO ARE NOW STAGED, ON HEAD-TO-HEAD EVIDENCE** (2026-09-16).
    `-Soulmender +Bloodthirsty Conqueror` (karlov, **+0.0257 ±0.0028 at T10
    and +0.0247 ±0.0035 at T20**) and `-Plains +Anointed Procession` (tivit,
    **+0.0113 ±0.0026 / +0.0145 ±0.0040**), both significant at BOTH horizons.
    **The real swap is SMALLER than the candidate row in both cases** — the
    candidate number is value over a blank in a freed slot, the swap also pays
    for what it cut, and §0e says the swap is the number a decision rests on.
    Tivit's numbers were re-measured on the post-§0z30 baseline (§0z33:
    +0.0133 / +0.0157, up inside their bars; the staging stands). Tivit's
    cut is a basic Plains (36 lands → 35) because that deck has no
    weak nonland row; **a land cut is the kind of change this harness
    flatters**, so read it with that in mind. **And karlov's cut is
    MODEL-BLIND** (§0z31's cut check, 2026-09-17): Soulmender's tap ability
    is not modelled, so the head-to-head is a ceiling and the staging rests
    on the `cut_unmeasured` judgement written into the Change. **AND THAT
    JUDGEMENT IS NOW MEASURED AND WRONG** (§0z36, 2026-09-20): the same card
    against the MODEL-EVALUATED cut item 22 established is **+0.0401 ±0.0037
    at T20 against +0.0254**, and the gap between the two cuts is +0.0125
    ±0.0049 measured directly. **THE OWNER DECIDED (2026-09-26): SOULMENDER
    STAYS THE CUT.** The Boots remain in the list because in an
    interaction-heavy pod the shroud does real work -- work this model
    cannot fully see, since the pod's removal is a roll against an abstract
    board (§4). That is a judgement about the owner's table outranking a
    +0.0075 ±0.0047 T20 edge that is inside its bar at T10, and it is
    recorded on the Change. **SOULMENDER IS MODELLED SINCE §0z129** and the
    swap was re-measured with its tap live: +0.0471 / +0.0421 at T10 / T20,
    the cut MODEL-EVALUATED now. Two more are explicitly HELD:
    Alhammarret's Archive on the owner's playtest experience — which the
    model's own counter corroborates, 0.40 extra draws a game — and Parallel
    Lives as too expensive for what it does.


18. **BOTH HALVES ARE MEASURED; WHAT IS LEFT IS AN ADOPTION DECISION**
    (§0z43, §0z44). The ORDER half is a null: the one-card lookahead
    (`engine.lookahead_pick`, `cast_lookahead`, OFF) moves win rate inside
    its bar in all twelve cells. The NUMBERS half is swept
    (`diagnostics/run_priority_sweep.py`, four tiers, three disjoint seed
    blocks): the tables matter — flattening one costs up to 0.045 — and
    **four decks' numbers survive every ±2 move**, including §0z8's own
    Voice-over-Lurrus case. **Two do not.** Karlov wants Felidar Sovereign
    and Sorin, Solemn Visitor higher (joint +0.0099 / +0.0091); tivit ranked
    card draw above its token engines (joint +0.0225 / +0.0211, four moves).
    **BOTH ARE ADOPTED (2026-09-25), and the batched rebuild the owner
    deferred them to has RUN** (§0z60): all six tables at N=15,000, every
    cache CURRENT, `check_docs` green. The staged swaps the rebuild left on
    the old priorities have since been re-measured on the current engine,
    all eight inside their bars (§0z81). **Time Sieve's sign flip is
    EXPLAINED (§0z86)**: it was the horizon, which counted tivit's extra
    turns and not lorehold's. With the horizon in rounds, Sieve 9 → 11 is
    +0.0218 / +0.0151, significant at both -- an adoption decision for the
    owner, like the two above. **Trostani, the seventh deck, is swept too
    (§0z110)**: five moves, every one raising a token or populate engine,
    joint +0.0129 / +0.0519 -- tivit's shape, **ADOPTED 2026-10-05**,
    except Bramble Sovereign, which loses at T10 given the other four
    (§0z111) and is back at 8.5. **Trostani's rebuild is deferred.**

5.  Remaining per-deck gaps are in the STATUS block of each
    `docs/ORACLE_AUDIT_*.md`.

24. **WHAT WOULD LET THE MODEL SEE ITS BLIND CARDS** (queued 2026-10-13, at
    the owner's request after a look at simulating Riku of Many Paths). The
    75 cards in the seven `KNOWN_BLIND` sets in `tools/ablation.py`, sorted
    by what each is missing (one session's reading of each card's note --
    a judgement, not derived):

    | missing | cards | e.g. |
    |---|---|---|
    | opponent permanents worth removing | 36 | Swords, Path, Beast Within, Vindicate, Krosan Grip |
    | nothing: YOUR side's text, unimplemented | 19 | Sun Titan, Bloodghast, Jitte, Sylvan Library, Top |
    | the pod's spells, hands and draws | 10 | Counterspell, Dovin's Veto, Rhystic Study, Mind's Eye |
    | the pod's creatures as bodies that die | 5 | Massacre Wurm, Pygmy Kavu, Deathreap Ritual |
    | a response window | 3 | Greater Good, Perch Protection, Sejiri Shelter |
    | attack taxes (the clocks are not combats) | 2 | Ghostly Prison, Propaganda |

    **The root is that an opponent's win is a ROLL** (`make_pod`'s
    `kill_turn`, fired by `opponents.resolve_clocks`), so nothing you do to a
    board can delay it. Giving the pod permanents to target does nothing
    unless removing one moves the clock. The changes, in the order proposed:

    - **0. Implement the own-side cards.** No model change; each moves only
      its own deck. Sun Titan works in shilgengar and trostani and is blind
      in karlov; Midnight Reaper works in shilgengar and is blind in rendmaw
      (§0u's shape). Bloodghast, Phyrexian Reclamation, Umezawa's Jitte,
      Soulmender, Restoration Seminar and Improvisation Capstone had no code
      anywhere. **FIRST PASS DONE (§0z129)**: those nine, plus Quirion
      Ranger and the two Lorehold Lessons. Storm Cauldron and Hall of
      Gemstone stay blind (reasons in `tools/ablation.py`); Angel of
      Suffering waits for change 2 (is a clock damage?); the selection
      cards are change 4.
    - **1. The pod's creatures as bodies** -- **BUILT, OFF (§0z130);
      ITS GAPS CLOSED (§0z132)**: chump blockers die, the pod blocks only
      when it matters (`pod_chump_floor`), deathtouch is read, Deathreap
      Ritual and Pygmy Kavu read the bodies. Before that:
      `pod_bodies`, bit-identical off; switching it on is a POD_V4 call for
      the owner, with every table rebuilt. Originally: a pre-rolled power/toughness list
      per opponent instead of `Opponent.creatures`. Unlocks -X/-X and damage
      wipes (Gyre's `gyre_full_x` knob goes away), deathtouch in blocking,
      and "whenever a creature an opponent controls dies". Homogeneous bodies
      should reproduce today's numbers, so `check_unchanged_decks` can prove
      the refactor before anything moves.
    - **2. Opponent threats as objects that carry the clock** -- **BUILT,
      OFF (§0z131)**: `pod_threats`, bit-identical off; 27 answers derived
      from the census clause, held until something they hit is out. ON
      lifts every deck +0.038 to +0.082 at T20, all of it fewer clock
      losses, and `threat_rebuild_max` (1 / 3 / 5) moves that by a third
      either way: a judgement with no data, said with every result.
      **THE KILL TIMING IS RE-FITTED (§0z132)**, at the owner's request:
      `threat_clock_shift` 1.9 holds the mean T20 win rate with bodies and
      threats both on, and every deck's answers are then worth +0.04 to
      +0.11. That pod is `experiment.POD_V4`, a candidate: adopting it is
      the owner's call, with a rebuild of every table, `KNOWN_BLIND`
      re-read and `tools.triage` taught `ANSWERS`. Its shift is 2.0 since §0z133 (re-fitted on the fixed pod). Not done: attack taxes,
      Damn's single-target mode, the voting answers, the wipe gate
      reading routes. Originally: each kill
      route is pre-rolled pieces (type, landing turn) and a route kind
      (combat, combo, drain); removing a piece pushes `kill_turn` back by a
      pre-rolled rebuild delay; the route kind decides which answers work
      (wipes and Propaganda against combat, a counterspell against a combo).
      About half the blind list. **The rebuild delay is a number nobody has
      data for**: it ships as a swept knob, said out loud with every result
      it moves.
    - **3. Holding mana up through the pod's turn**: a response window in
      `pod_phase` and an end-step cast for whatever was held. Counterspells
      (with 2), protection in response (`try_protect` is the seed), flash.
      It charges a counterspell its real cost: tempo.
    - **4. A shared "which card do I want next"** for selection and tutors
      (Sylvan Library, Sensei's Divining Top, Abundance, Enlightened Tutor,
      Gamble, Sylvan Scrying, Crop Rotation). Your side only.

    Not proposed: opponent hands and graveyards (Rhystic Study is a social
    knob however it is built). **Changes 1-3 touch `opponents.py`, which is
    in every fingerprint**: each goes in behind a knob that reproduces the
    current pod bit-for-bit, and is switched on as a POD_V4
    (`experiment.py`) with one parallel rebuild of every table.
