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
  8-old, 17, 21, 2, 4, 8b, 0b-i, 23, 0c, 25, 26, 27, 20b, 24, 31, 35, 36, 38, 39, 40, 41, 42, 43, 37, 44, 46, 47, 48 and 51 are closed, each in
  `docs/HISTORY.md` under "Queued items closed …".
- 20, 20-old, 20-old2, 22, 7 and 8c were answered or superseded, and are in
  `docs/HISTORY.md` under "Queued items answered or superseded, moved
  2026-10-10".

## Order of work

**Start here.** Set on 2026-11-15, when the owner asked for both reviews
(§0z192, §0z197) to be checked against the work since and the rest put in
priority order. It replaces "item 44 first" (the owner, 2026-11-12): item
44's batch is flipped, re-fitted and re-read (§0z204, §0z205), and only
its rebuild is left. **The order is a recommendation the owner asked to
have written down; each step that is the owner's to call says so.** The
items below this section are in the order they were queued, not this one.

1. **Item 47: the behaviour fixes that move a baseline, BEFORE the
   rebuild.** The only step with a deadline: after the rebuild each one
   costs its deck a second rebuild. **DONE 2026-11-15** for azusa
   (§0z210-§0z213), tivit (§0z214) and shilgengar (§0z215); what is left of
   item 47 is step 2's question.
2. **Item 47's owner decision: where Lightning Greaves sits in tivit.**
   Ask; do not choose. It moves tivit's baseline, so it is asked before
   step 3.
   **ASKED 2026-11-15 AND HELD BY THE OWNER ("hold off on that, write it
   to the known issues")**: written down as §0z216, nothing measured.
   **DECIDED BY THE OWNER LATER THE SAME DAY AND BUILT (§0z216)**: "greaves
   should be equipped to tivit only when the deck has no blink abilities in
   play or in hand" -- `greaves_blink_policy`, the default.
3. **Item 44's one rebuild** (`parallel-rebuild`). **HELD BY THE OWNER
   since 2026-11-14; CALLED BY THE OWNER 2026-11-15, AND DONE (§0z219)**:
   six tables on the flipped pod, every active cache CURRENT, `check_docs`
   green. Items 44 and 47 are closed, in `docs/HISTORY.md`. Until it runs the six
   caches are SUSPECT and `check_docs` fails on that one check, which is
   expected and is said in each commit. Never `--verified`.
4. **Item 48: re-measure what was decided on the old pod**, on the
   rebuilt tables. **DONE (§0z220)**; tivit's §0z44 priorities, a null now,
   KEPT by the owner 2026-11-16. Item 48 is closed.
5. **Item 45: decide A3, then A6 and A5.** A3 is the largest limit left.
   **DECIDED 2026-11-16 (§0z221)**: A3 first, then A5, then A6. **BUILT,
   MEASURED AND FLIPPED (§0z222)**, A6 reworked to hold only to gain; the
   pod re-fitted (`incidental_rate` 1.94); the rebuild follows.
6. **Card work that does not move a decision already made** (item 46's
   list, item 37's Memory Jar and Bloodbat Summoner): tivit's ward {3}
   first, since it guards the commander. **WARD DONE 2026-11-16 (§0z224)**,
   all three ward cards. Any time; after step 3 each
   staged card rebuilds its own deck (§0z27).
7. **Item 49: the small cleanups.**
7b. **Item 50: a real mana model for the pod** -- written down 2026-11-17;
   **STARTED BY THE OWNER 2026-11-20**, reviewed and decided (§0z234);
   item-44 scale. Item 52 is what it left for later. **FLIPPED (§0z243)
   AND REBUILT (§0z244, 2026-11-22)**; the staged swaps' re-measure is
   left.
8. **When the owner picks them back up**: item 28 (paused), item 29's
   leftovers, item 32. Item 34's deletes are the owner's, on github.com.
   Items 18 and 5 wait on trostani (SUSPENDED).

**Before starting any step**, run the gates and compare with the last
session's: `python -m tests` and `--mutate`, `python -m tools.validate`
(`+0.00` on every metric; `pip install -r requirements.txt` first, a fresh
cloud container has no scipy), `python -m edhmc.pending`, and
`python -m tools.check_docs` (the cache check alone failing, see step 3).

---

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
    owner, like the two above. **RE-MEASURED ON POD_V4 (§0z150,
    2026-10-22)**: +0.0225 ±0.0034 at T10 and **+0.0064 ±0.0034 at T20**,
    still significant at both and smaller at T20, as POD_V4's sooner kill
    made every slow engine. **ADOPTED 2026-10-22.** **Trostani, the seventh deck, is swept too
    (§0z110)**: five moves, every one raising a token or populate engine,
    joint +0.0129 / +0.0519 -- tivit's shape, **ADOPTED 2026-10-05**,
    except Bramble Sovereign, which loses at T10 given the other four
    (§0z111) and is back at 8.5. **Trostani's rebuild is deferred**, and
    is all that is left of this item.

5.  Remaining per-deck gaps are in the STATUS block of each
    `docs/ORACLE_AUDIT_*.md`. **§0z116's list is done** (§0z151, §0z153,
    2026-10-22) but for trostani's Sylvan Library, which waits with the
    deck (SUSPENDED). **Karlov's own "{W}{B}, Remove six +1/+1 counters:
    Exile target creature" is IMPLEMENTED** (§0z155, 2026-10-23) on the
    owner's policy: at the end of the pod's round, on {W}{B} the turn left
    untapped, at a creature route piece. What is left: trostani's open
    gaps, SUSPENDED with the deck -- all that remains of this item.

28. **PAUSED BY THE OWNER, 2026-10-31: the five Reality Fracture / Star
    Trek candidates** (§0z157, §0z159). Done: each implemented, pinned
    (`tests/test_star_trek_batch.py`), smoked, and measured as a candidate
    row at N=15,000, T10 and T20 -- a Candidate in each deck's MEASURED,
    its Proposal closed. **Nothing is staged and no list moved**; every
    cache is VERIFIED. Left, in order, when the owner picks it back up:
    - **A head-to-head against a named cut** for the four whose rows read
      `both`: Dr. Beverly Crusher (karlov; Swiftfoot Boots, which the owner
      kept on 2026-09-26 for shroud), Avacyn, Angel of Horror (shilgengar;
      Skullclamp or Dark Prophecy), Mr. Spock (tivit; Tamiyo's Journal) and
      Join the Collective (lorehold; Pinnacle Monk). The cuts are
      PROPOSALS, not decisions; the owner names them. One paired `run_ab`
      each, N=15,000, both horizons, in the shape of
      `diagnostics/run_karlov_conqueror.py`.
    - **Captain Pike (azusa): a package ablation first.** His T20 row is
      inside its bar because four cards already grant the top (Courser of
      Kruphix, Augur of Autumn, Oracle of Mul Daya, Ka-Zar), so
      `ablate([...])` the five grants together before any swap (§0z27).
    - **At staging**: Join the Collective goes into
      `opponents.WIPE_DESTROYS` with its clause (`test_wipe_coverage`
      requires it), and a staged deck's table is rebuilt (§0z27).
    - **Knobs each row carries**, to say out loud at the decision:
      `avacyn_feed`, `wipe_gate_refund`, and Spock's `spock_draw_safe`.
    - **Not done, and not part of this item**: the other cards §0z157's
      review read as promising (Bio-Asset Allocator, Traxos, Captain
      Janeway for rendmaw; Hexhaven Battalion, Currency Converter, Tomik for
      lorehold; Yoshimaru, Niv-Mizzet, Ob Nixilis for karlov; Constable
      Odo, Flickering Hound for tivit; Overlord of the Mistmoors, Khan for
      shilgengar; Benjamin Sisko, Omnath, Marwyn, Fblthp for azusa) are
      unrecorded ideas, not Proposals: none has verified text in a ledger.

29. **Bolas's Citadel, after §0z160 and §0z161.** The dig follows the
    card's text (§0z160); digging to 1 for the win measured worse at T20 at
    every policy tried. **The clock floor is ADOPTED** (§0z161, the owner,
    2026-11-01): the dig stops at the chip damage the pod can visibly deal
    next round + 1 (`citadel_floor_mode` "clock", `citadel_clock_pad` 1),
    +0.0018 / +0.0007 at T10 / T20 over floor 10, N=60,000. Left, in order:
    - **The karlov rebuild is DONE** (the owner, 2026-11-03; §0z169): 0 rows
      moved, the cache CURRENT, the Citadel swap +0.0121 / +0.0088 on the
      clock floor, all three staged swaps standing.
    - **Necropotence with Reliquary Tower is ADOPTED** (the owner,
      2026-11-04, §0z173): `necro_tower_target` 99, re-measured out of
      sample on the cleanup step, +0.0024 / +0.0011.
    - **The pad re-fork on the corrected crack-back is DONE** (§0z190): pad 1
      is still the top; 0-1.5 a plateau, 3 and 4 lose. Nothing changed.
    - **Hold Enlightened Tutor while the Citadel is out** (its skip fired 0
      times: the main phase casts it first), and use Ranger of Eos's and
      Land Tax's shuffles on a land on top. Two thirds of digs stop at one.

32. **The deferral protocol (the owner, 2026-11-02; §0z165).** A deferral is
    a bet: the pilot acts unless a measured payoff says wait. Done, read-only:
    the inventory (`python -m tools.deferrals`, 38 main-phase sites in seven
    engines, derived and classified, `--check` and `tests/test_deferrals.py`
    hold it) and the census (`diagnostics/run_deferral_census.py`: how often
    each site changes what is cast, and what became of the card held; every
    traced game identical to its untraced twin). Nothing moved. Left, in order:
    - **Lorehold's two holds are gone**: ADOPTED by the owner 2026-11-03
      with the float fix (item 31, closed; §0z168).
    - **Fork shilgengar's ultimate reserve on POD_V4** by §0z160's method
      (`shilgengar_ult_reserve` through `turn_knob`, a `turns`-replay
      diagnostic, bit-identity first). §0t confirmed 3 before pod v3; half the
      cards it holds are never cast.
    - **Extend the inventory to what it is blind to**: activated abilities a
      knob holds back (`altar_keep`, `karlov_exile_keep`, `gingerbrute_keep`,
      `zuran_keep`, `vault_hold`) and casts outside the main phases'
      option loops (`engine.altar_enable`, tutors). Derived, as the first part
      is, with its check.
    - **Then the CLAUDE.md lesson**, once a second deck's hold is measured:
      a deferral is a bet, and the default is to act.

34. **Archive, then delete, the five pre-restart branches (the owner,
    2026-11-06).** `main`'s history was restarted on 2026-10-09 (root
    `5bc742a`). These five branches predate that and have a different root
    (`35f58f4`), so they share no history with `main`. They were found
    because the owner suspected an agent had pulled one of them, and they are
    still there to be pulled. Every one is superseded: its `KNOWN_ISSUES.md`
    stops at §0z15 or earlier.

    | branch | tip | tag to create |
    |---|---|---|
    | `combat-split-and-bounded-damage` | `d158724` | `archive/combat-split-and-bounded-damage` |
    | `fix/engine-batch-0z9-0z15` | `fe9d4af` | `archive/fix/engine-batch-0z9-0z15` |
    | `perf/ablation-runtime-and-n15000` | `9a33cba` | `archive/perf/ablation-runtime-and-n15000` |
    | `pod-model-v3-and-candidate-evaluation` | `d6a40bd` | `archive/pod-model-v3-and-candidate-evaluation` |
    | `reverify-oracle-2026-09-05` | `a207dad` | `archive/reverify-oracle-2026-09-05` |

    The session that found them made the tags and could not push them: its
    git proxy allowed pushes to its own branch only (HTTP 403 from the
    proxy, not from GitHub). The owner has since widened the permissions,
    which reach new sessions. The owner has no machine of their own to run
    git on, so a session does this. **Order matters: a deleted branch whose
    tag never reached GitHub is gone.**
    - Check first that each tip in the table is still the branch's tip
      (`git rev-parse origin/<branch>`). If one moved, stop and ask the owner.
    - Create each tag as an annotated tag (`git tag -a archive/<branch>
      origin/<branch>`) and push them (`git push origin
      'refs/tags/archive/*:refs/tags/archive/*'`).
    - Confirm all five tags are on GitHub and point at the tips in the table
      (`git ls-remote --tags origin 'archive/*'`; read the `^{}` lines).
    - Only then delete the branches (`git push origin --delete <branch> ...`)
      and confirm with `git ls-remote --heads origin` that only `main` and
      the working branch are left.
    - Close this item to `docs/HISTORY.md`.

    If the push is refused again, the permissions still have not reached
    the session. Leave the branches and tell the owner.

    **Second attempt, 2026-11-06: the archive is done; the deletes are the
    owner's.** The five tips still matched the table. The tag push was
    refused by the session's git proxy (HTTP 403, `ERR push contains a ref
    outside refs/heads/*; only branch updates are permitted.`), so the owner
    chose to archive them as branches instead. Each is now on GitHub as
    `archive/<branch>` (for example `archive/fix/engine-batch-0z9-0z15`),
    checked with `git ls-remote --heads origin` to point at the tip in the
    table. The local annotated tags were not pushed and are not needed.
    Deleting the five originals was then refused too (`ERR branch deletion
    is not allowed.`), and the GitHub tools in a session have no branch
    delete. **What is left is the owner's, on github.com**: open the
    repository's Branches page and delete the five ORIGINAL names in the
    table, NOT the `archive/...` ones. After that, `git ls-remote --heads
    origin` should list `main`, the working branch and the five `archive/`
    branches only, and this item closes to `docs/HISTORY.md`. Agents can
    still pull an `archive/` branch, but the name says what it is.

45. **A3-A7 of §0z197: write down, then decide.** **A3, A6 AND A5 ARE
    WRITTEN DOWN AND DECIDED (§0z221, 2026-11-16)**: route-aware kills
    (A3), held answers (A6, after A3), the pod attacks walkers (A5). Built
    the item-44 way -- each behind a switch, OFF until measured, the
    defaults flipped together, the pod re-fitted, one rebuild. None is a bug to fix in
    passing; each is a model decision nobody wrote down or made. **A4 is
    BUILT, in item 44's batch (§0z200, `rival_combat`, OFF).** A3 (the kill ignores your life and blockers) and A6 (the pod acts only
    in its own main phase) bound every lifegain and every haste/ETB row.
    A5 (walkers never attacked) follows A2 naturally -- the pod's declared
    attack can name one. A7 has a concrete defect inside it: azusa's Chord
    of Calling (fixed X=4, no convoke) against trostani's convoke and X
    plan, the same card under two rules. After item 44. **Chord is in
    item 47's batch; A3, A6 and A5 are step 5 of the order of work.**
    **CHECKED 2026-11-22: ALL BUT A7's REMAINDER IS DONE.** A3, A5 and A6
    are on by default (§0z222), A4 too (§0z200, `rival_combat`), and
    Chord of Calling is one rule (§0z213). **Left: X spells still have a
    fixed X** -- Genesis Wave at 6 (azusa) and Torment of Hailfire at 6
    (tivit); §0z210 notes a pilot with the mana would cast the Wave
    bigger. A model decision for the owner, and it moves both decks'
    baselines (§0z197's status note).
    **THE OWNER, 2026-11-22: "each of these need at least a small logic
    build around them, since they mostly do different things."** So not one
    shared X rule: each fixed-X card gets its own X logic, behind its own
    switch, measured, then flipped. The cards, from the staged lists'
    `x_pips`: Genesis Wave (6) and Animist's Awakening (4), Green Sun's
    Zenith (3), Nylea's Intervention (3) in azusa; Torment of Hailfire (6)
    in tivit; Debt to the Deathless (3) in karlov; The Meathook Massacre
    (2) in rendmaw; Agadeem's Awakening (2) in shilgengar. Chord of
    Calling already plans its X (§0z213). Not started; queued behind item
    52 (the owner: "let's move on to item 52 instead").
    **BUILT AND MEASURED 2026-11-22 (§0z248)**, the owner: "Start the
    X-spell logic, item 45". Eight switches, all OFF: `genesis_wave_x`,
    `animist_x`, `nylea_x`, `gsz_x_plan` (azusa), `torment_x` (tivit),
    `debt_x` (karlov), and, by the owner's choice the same day, The
    Meathook Massacre's -X/-X ETB with its X (`meathook_x`, rendmaw) and
    Agadeem's Awakening's front face (`agadeem_x`, shilgengar -- it was
    cast as a blank). At T20, N=15,000: Genesis Wave +0.0062, Torment
    +0.0030 (a ceiling), Meathook +0.0061 (the cheaper cast, not the ETB),
    Debt +0.0021, Agadeem +0.0013, each significant; Animist's, Nylea's
    and Green Sun's inside their bars. **FLIPPED BY THE OWNER THE SAME
    DAY**: "flip genesis wave, torment, meathook and debt, but do not
    rebuild" -- those four ON (`experiment.PRE_ITEM45` restores them),
    Agadeem, Animist, Nylea and Green Sun's OFF. **REBUILT 2026-11-23
    (§0z250)**: the four decks' tables at `80cb14f`, the owner's call.
    **ALL EIGHT FLIPPED 2026-11-23** (the owner: "flip the switch on ALL X
    cards"; `experiment.PRE_ITEM45_REST` restores the last four, §0z248).
    **Left**: the fresh-seed re-measure (§0z170) of the eight, and azusa's,
    lorehold's and shilgengar's rebuild (azusa SUSPECT again with this
    flip; the other two since §0z246-§0z247).

49. **SMALL CLEANUPS (order of work, step 7)**, all from §0z205.
    **DONE 2026-11-17 (§0z225)** but for the last bullet, which waits on a
    proposal: the goaded Birds fight as bodies, and the nine knobs are
    confirmed dead at 12,000 games and marked in `tools/knobs.py`.
    - `goad_block_share` is still a count share for rendmaw's goaded
      Birds although rivals block with bodies since §0z200: the same
      combat under two rules. Rendmaw only; moves its baseline, so it
      joins item 47 if a session has room, else it costs a rebuild.
    - Six knobs moved 0 games on both pods at N=300 (`block_rate`,
      `monarch_loss_scale`, `monarch_attack_floor`, `crown_loss_ends_chip`,
      `gingerbrute_keep`, `zuran_keep`) and three were retired by the flip
      (`blocker_toughness`, `pod_block_policy`, `pod_blocker_deaths`).
      300 games is not a proof (§0z126): confirm at 2,000+, then either
      delete the dead branch or mark the knob in `docs/KNOBS.md`'s source.
    - Azusa's `counter_target` is unreached by its list: re-measure when
      Bristly Bill or Dancing from Dark to Dawn is proposed, not before.

50. **A REAL MANA MODEL FOR THE POD (the owner, 2026-11-17; §0z224).** The
    pod has no mana. An `Opponent` is a life total, a creature count and its
    bodies, a kill route and counterspells left -- no lands, no pool, no
    hand. Its removal is a per-turn probability (`BRACKETS` `spot`, 0.10 to
    0.24) from its turn 3; its counterspells are scaled by `(pod turn - 2) /
    4`, a ramp; and ward is paid when its turn covers the removal's cost plus
    the ward (`opponents.ward_payable`, from the same one-land-a-turn
    reading, §0z224). Each is an assumption about mana standing in for mana.
    **What it would take**, each a judgement to say out loud:
    - Lands per opponent per turn, pre-rolled at `make_pod` (CRN, §0z17):
      a land drop most turns and ramp by bracket and archetype.
    - Mana SPENT, each turn, on what the pod already does: its bodies (they
      carry a mana value), its route pieces, its removal and wipes (costs
      from the census, `_removal`), and mana HELD open for instants -- the
      counterspells and A6's held answers would then read held mana, not a
      ramp or a roll.
    - Then ward, counterspells, held answers and removal itself gate on real
      spare mana: a pod that tapped out to develop cannot answer, and one
      that held up mana developed less.
    - **The cost**: the removal and counter rates are calibrated with no
      mana limit, so gating them by mana changes how much interaction the
      pod casts. The pod must be re-fitted (§0z195) and every table rebuilt
      -- item 44's scale. Build it the item-44 way: every rule behind a
      switch, OFF until measured, flipped together, one re-fit, one rebuild.
    Not started. The owner's to schedule.
    **STARTED AND WRITTEN DOWN 2026-11-20 (§0z234)**: reviewed against the
    comprehensive rules (the `.docx`), the six decisions made by the owner --
    a library generated from the decklists; rocks and land ramp only;
    development charged, not gated; route piece, removal, bodies, the rest
    held; the rates scaled back and the pod re-fitted; Ghostly Prison and
    Propaganda weighed against the damage they buy. What the owner left for
    later is item 52. **THE CENSUS IS DONE (§0z235, 2026-11-20)**:
    `edhmc/decks/_pod_mana.py`, generated -- 35 lands of 99, 4 rocks, 1 land
    ramp; wipes 4.5, A/E 3.0, counterspells 2.0 (thin). Read by no engine
    yet, so in no fingerprint: the change that first reads it adds it to
    `tools/cache_manifest`'s shared files. Your removal that ramps the pod
    (`POD_GIFTS`: Path to Exile, Assassin's Trophy, An Offer You Can't
    Refuse) is a cost to charge. **THE LIBRARY IS BUILT (§0z236,
    2026-11-20)**, `pod_mana` off: land drops pre-rolled per opponent from
    its own stream, the owner's mulligan rule, ramp first; read by nothing
    yet, every deck bit-identical on and off. **THE SPENDING IS BUILT
    (§0z237)**, charged not gated: about 61 mana a game, 11 of it beyond the
    pod's library, mostly bodies on turns 1-4. Next: the first gate that
    reads `mana_left`: **the attack taxes first (the owner, 2026-11-20)**,
    a kill that cannot pay for its lethal attackers deflected ("deflect is
    fine") -- **BUILT (§0z238)**, `pod_tax_mana` off; tivit a null at bar
    1.0, the bar deciding the sign. **THE ANSWERS ON YOUR TURN ARE BUILT
    (§0z239)**, `pod_answer_mana` off: counterspells, held answers and ward
    read the mana left untapped; four decks gain, azusa loses at T10 to
    counterspells that come earlier. **THE OWN-TURN REMOVAL GATE IS BUILT
    (§0z240)**, `pod_removal_mana` off: every deck gains +0.011 to +0.036 at
    T10 because the pod casts a third fewer wipes -- the double-counted
    mana decision 5 rescales. **YOUR REMOVAL THAT RAMPS THE POD IS BUILT
    (§0z241)**, `pod_gifts` off: tivit -0.0013 at T20, three more decks
    -0.0001 to -0.0006. **The interaction is measured (§0z242)** and the
    owner chose the rescale's target: TODAY'S counts (spot 3.0, A/E 1.1,
    wipes 0.34, counterspells 0.72 a game in pod turns 3-10). **FITTED**:
    `pod_rate_scale` spot 1.15, A/E 1.41, wipes 1.44, counterspells 1.05
    restores them (§0z242).
    **FLIPPED, RE-FITTED AND READ (§0z243, 2026-11-21)**: every switch on
    with the rescale; `incidental_rate` 1.80 (out of sample +0.0063 against
    the old pod); `attack_tax_deflect` and `ward_pay_share` stranded,
    marked. **Left: the rebuild, the owner's call** ("make sure you tell me
    before rebuilding"), then the staged swaps re-measured.
    **REBUILT (§0z244, 2026-11-22)**, the owner: "Yes, go ahead with the
    parallel rebuild" -- six tables at `120cc9a`, every active cache
    CURRENT, `check_docs` green; every baseline up +0.002 to +0.011, 37 of
    379 rows moved beyond their bars, no sign flips. **Left: the staged
    swaps re-measured** on the rebuilt tables, the owner's to call.
    The plan as it was written:
    every item-50 switch on together, decision 5's rescale to the
    documented interaction counts, the re-fit (§0z195), the stranded knobs
    (`run_knob_liveness`, §0z205), one rebuild (`parallel-rebuild`), the
    staged swaps re-measured.

52. **AFTER ITEM 50: THE DECISIONS RECORDED TO REVISIT (the owner,
    2026-11-20; §0z234).** Each was left out of item 50's batch on purpose:
    - **Mana creatures** ("leave those for later but record that decision
      to revisit"): a pod body that taps for mana from its controller's next
      turn (302.6), dies to wipes and to your removal, and so ties the
      pod's mana to its board.
    - **Development gated by mana** ("also record this decision to
      revisit"): the full budget, where holding mana up delays bodies and
      route pieces, and so moves the kill turns -- a second re-fit.
    - **Rhystic Study, Smothering Tithe, Monologue Tax** ("low priority"):
      each pays or not from the pod's spare mana instead of a flat rate.
      **BUILT 2026-11-22 (§0z246)**, with Mind's Eye (the owner: "please
      add minds eye"), on the owner's payment rule -- an opponent pays only
      from what it has left over. Rhystic +0.0083, Monologue Tax -0.0141,
      Tithe -0.0033 (lorehold) / -0.0044 (shilgengar), Mind's Eye +0.0069
      at T20; four caches SUSPECT until the rebuild, the owner's call.
    - **Found and FIXED 2026-11-22 (§0z245)**, the owner: "fix the
      treasures, then push to main, do not rebuild": Tempting Contract and
      Master of Ceremonies hand the pod its Treasure. Tivit's cache is
      SUSPECT until the next rebuild.
    None starts before item 50 is flipped and rebuilt.
    **BOTH BUILT 2026-11-22 (§0z247)**, the owner: "go ahead with 1 and 2
    fixes, but do not rebuild". **Mana creatures are the default** (the
    owner: "mana creatures only"; -0.0032, no re-fit; `POD_PRE_ITEM52`
    restores). **Development gated by mana is built and OFF**: it weakens
    the pod +0.114 on the mean, the usual lever (`incidental_rate`)
    saturates short of it, and `threat_clock_shift` 4.985 (kills 2.7 rounds
    sooner) holds it unevenly. **Left, the owner's call**: that re-fit, or
    first a look at why the calibrated boards outrun the pod's mana.

53. **BEFORE THE NEXT REBUILD: TWO DECISIONS THAT MOVE EVERY DECK (the
    owner, 2026-11-25).** "decisions before the rebuild: fix the removal
    census pattern, and turn on Item 52. Make a note of these decisions but
    we will make other fixes before rebuilding." Both are DECIDED and NOT
    STARTED; the owner's other fixes (§0z257 on) come first, then these,
    then one rebuild of every active deck -- each moves all of them, so
    doing either after the rebuild would cost a second one.
    - **DONE 2026-11-26 (§0z263)**, the owner: "go ahead with the
      removal census pattern fix". One card newly read (Angel of
      Serenity), the spot share 0.46 -> 0.451, rendmaw's baseline moved.
      **The census pattern** (§0z255): `tools/removal_census.py`'s spot
      exile rule reads "(another )?target" and misses "other target" --
      Angel of Serenity, read by hand since (`shilgengar.SERENITY_REACH`).
      Fixing it regenerates `decks/_removal.py`, so `DESTROY_SHARE_SPOT`
      moves for every deck. First list every card the fixed rule newly
      reads (not checked yet); delete `SERENITY_REACH` and its hook once
      the census reads the card (`check_serenity_reach` raises until then)
      and give Serenity an `ETB_RETURN_KNOBS` switch instead.
    - **Item 52's development gated by mana** (`pod_develop_gated`, §0z247):
      ON. Still open inside it, the owner's to choose: the re-fit -- alone
      it weakens the pod +0.114 on the mean, `incidental_rate` saturates
      short of it, and `threat_clock_shift` 4.985 holds it unevenly -- or
      first the look at why the calibrated boards outrun the pod's mana.
      Ask before building the re-fit.
