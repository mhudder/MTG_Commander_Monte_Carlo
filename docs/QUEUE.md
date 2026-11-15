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
  8-old, 17, 21, 2, 4, 8b, 0b-i, 23, 0c, 25, 26, 27, 20b, 24, 31, 35, 36, 38, 39, 40, 41, 42 and 43 are closed, each in
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
   costs its deck a second rebuild.
2. **Item 47's owner decision: where Lightning Greaves sits in tivit.**
   Ask; do not choose. It moves tivit's baseline, so it is asked before
   step 3.
3. **Item 44's one rebuild** (`parallel-rebuild`). **HELD BY THE OWNER
   since 2026-11-14: do not start it unasked.** Until it runs the six
   caches are SUSPECT and `check_docs` fails on that one check, which is
   expected and is said in each commit. Never `--verified`.
4. **Item 48: re-measure what was decided on the old pod**, on the
   rebuilt tables.
5. **Item 45: decide A3, then A6 and A5.** A3 is the largest limit left.
6. **Card work that does not move a decision already made** (item 46's
   list, item 37's Memory Jar and Bloodbat Summoner): tivit's ward {3}
   first, since it guards the commander. Any time; after step 3 each
   staged card rebuilds its own deck (§0z27).
7. **Item 49: the small cleanups.**
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

37. **The smaller turn-structure findings of §0z184 (6-9; 3-5 are fixed,
    §0z185; 2 and 10, §0z187)**, none of
    them urgent. In the order a session would take them:
    Memory Jar and Bloodbat Summoner (8); shilgengar's `activations` inside
    main 2 and Black Market Connections at the first main phase (7); first
    and double strike, with Sunhome (6), which waits on attackers that can
    die to blockers and so moved into item 44 (§0z197); the seat you take (9), which is a model decision to
    write down, not a bug. **Shilgengar's timing pair (7) is in item 47's
    batch**, since it moves the baseline.

44. **A1 AND A2 OF §0z197, FIRST (the owner, 2026-11-12): your attackers
    can die to blockers, and you block.**

    **STATUS 2026-11-14, LATER: THE POLICY RE-READ IS DONE (§0z205); ONLY
    THE REBUILD IS LEFT.** No default changed: every pilot policy's
    incumbent wins on the new pod (`hold_back_pad` 10, `your_chump_floor`
    10, `pilot_life_value` 0, `attack_safety` and `hold_back` on, rendmaw's
    Doll nest); the flip retired `blocker_toughness`, `pod_block_policy`
    and `pod_blocker_deaths`; the split plan keeps the formula's blocker
    count (`split_blockers`). Azusa's `counter_target` is unreached by its
    list -- re-measure when Bristly Bill or Dancing from Dark to Dawn is
    proposed. **Next: the one rebuild (`parallel-rebuild`) -- HELD BY
    THE OWNER, 2026-11-14 ("lets hold on the rebuild for now").** Until it
    runs the six caches stay SUSPECT and `check_docs` fails on them.

    **STATUS 2026-11-14: FLIPPED AND RE-FITTED (§0z204).** A1, A2, A4 and
    the pod's hold-back are the default (`opponents.POD_DEFAULTS`;
    `experiment.POD_PRE_COMBAT` restores the old pod exactly), and
    `incidental_rate` is re-fitted 0.78 -> 1.45 (crossing 1.453; out of
    sample mean T20 0.4616 against 0.4612, game length held). At N=15,000
    the mean T20 is 0.4702 -> 0.4680; T10, not fitted, 0.229 -> 0.213. The
    CRN factor fell (~15x -> ~7x; paired SE +10%). **All six caches are
    SUSPECT for a real reason -- never `--verified`.** Left, in order:
    (1) re-read the policies written while the gap was open (§0z5; the list
    is in §0z204) and re-sweep `pilot_life_value`; (2) the one rebuild, the
    owner's call.

    **STATUS 2026-11-13: A1, A2 AND A4 BUILT, ALL OFF** (A4: §0z200,
    `rival_combat` -- rivals lose life to each other; it came out of item
    45 into this batch, the owner's call). A1 (§0z198):
    `attacker_deaths`, evaluated blocks, first and double strike, the
    pilot's `safe_attackers`. A2 (§0z199): `you_block`, the pod's combat
    step a combat of bodies (the rate a bridge to the formula), the pod's
    read of your blocks (`pod_safe_attack`), your blocks by the same rule,
    tapped attackers that do not block, the crown an event. OFF proved
    identical both times and the caches VERIFIED; ON measured per deck,
    alone and together. **What is left before the defaults flip**, each the
    owner's to call: the flip, the re-fit (§0z195) and one rebuild -- the
    pre-flip list is DONE (`predicted_chip` reads the bodies under A2,
    §0z203). The
    lifelink pilot was MEASURED and is a null (§0z201, `pilot_life_value`
    stays 0; re-sweep after the flip). The pod's hold-back is BUILT
    (§0z202, `pod_hold_back`, OFF), worth at most 0.002 to you, and
    recommended for the flip at pad 10.

    **TEST EACH CHANGE; DO NOT REBUILD THE TABLES DURING IT** -- not one
    deck, not at the end of a step. "There is no point when there is so
    much to do." The tables stay as built at `63d20e7` until the batch is
    done and the owner calls a single rebuild. The protocol:

    - Every rule lands behind a cfg switch that restores the old rule
      exactly (every fix since §0z42 has), and **lands default OFF**. Off
      is bit-identical by construction, so each deck's moved fingerprint is
      cleared the usual way -- `check_unchanged_decks` against a worktree
      at the cache's `built_commit`, then `cache_manifest --verified` -- and
      `check_docs` stays green.
    - Each step is TESTED, not tabled: a pinned mechanism test with its
      mutation mode (written before it is run, §0z11), `python -m tests`
      and `--mutate`, `tools.validate` +0.00, and a paired on/off run per
      deck (N 6,000 or more, both horizons) reporting win rate, the baseline,
      every output key that moved (§0z32) and the new mechanism counters
      (attackers lost, blocks made, blockers lost, kills by block).
    - The defaults flip TOGETHER at the end of the batch. Then the pod is
      re-fitted once (the fit rule, §0z195; `incidental_rate` as in
      §0z186), the policies written while the gap was open are re-read
      (§0z5), and the owner calls one rebuild (`parallel-rebuild`).
    - If a default is flipped mid-batch anyway, the caches it moves are
      SUSPECT for a real reason: **never clear them with `--verified`**;
      `check_docs` fails on them and each commit says so.

    **THE OWNER'S DECISIONS (2026-11-13)**, asked on 2026-11-12:

    1. *The pod's block rule*: each defender **evaluates the situation**
       rather than following one fixed rule -- chump, trade or decline.
    2. *Your block rule*: the same. "Utility creatures do not block
       normally unless under large pressure."
    3. *Which bodies attack, and how well the pod plays*: **the opponents
       play as close to optimally as possible.**
    4. *A roll or an expectation*: left to the session ("your call"). The
       recommendation, adopted unless the owner overrides it: **the attack
       becomes discrete by construction** -- real bodies attack, real
       blocks, real damage -- rather than a lognormal spread laid over the
       formula (§0z170's test device). Every new random draw is CRN-addressed
       (§0z17), the old formula stays behind the switch, and the PILOT keeps
       reading an expectation of the pod's next swing, never the swing
       itself (§0z170: "a pilot who knows the next swing to the point is
       not a pilot"). The cost to check: a wider noise floor, read off
       `tools.validate`'s CRN factor before and after.

    **What "optimal" means here, so it can be built and tested.** A
    one-decision evaluation by each player, from the information that
    player has -- the visible boards, life totals, commander damage and
    each creature's value -- and never from hidden or pre-rolled state
    (your hand and library, the kill turns, the CRN streams). Not a game
    tree: azusa's boards reach thousands of creatures, so every decision
    stays greedy or closed-form, O(n log n) at worst. A defender blocks
    first to survive (lethal, commander damage included) at the least
    value lost; otherwise only where the block is free (the blocker
    lives) or a trade it wins on value; a utility creature blocks only
    under pressure. An attacker is sent where it is not blocked at a loss
    and its absence does not open its owner to a lethal crack-back. Any
    tuned piece of either policy is re-measured on fresh seeds before its
    size is quoted (§0z170).

    **What the decisions require, each a new judgement to say out loud**:
    the bodies need a POWER (they carry toughness, mana value and colour
    today, `PodBody`) and a ROLE or value (utility vs combat), and so
    distributions nobody has data for. Your side needs the same value per
    creature (an engine, a mana creature, the commander). **Your pilot is
    upgraded in the same work**: an optimal pod against a pilot that
    attacks by a fixed rule measures the pilot's errors, not the cards
    (§0z184's hold-back lesson, §0v). Expect the mean win rate to fall
    and the pod to be re-fitted (§0z195: a stronger pod shrank every row
    to ~0.4 and flipped none). And A4 sits inside A2: once the pod
    declares attacks, an attack at a rival either takes that rival's life
    (A4 resolved) or goes nowhere as today -- decide it there, not later.

    **Knobs re-derived or retired by it**: `block_share`,
    `flier_block_share`, `blocker_toughness`, `goad_block_share`,
    `incidental_rate`, `combat_share`'s `1/(1+blockers)`, `hold_back` and
    `hold_back_pad` (§0z186, §0z191), `attack_tax_deflect`.

    **Text it makes live, to be pinned as it does**: first and double strike
    (Lyra Dawnbringer, Sunhome -- §0z184 finding 6, which item 37 hands
    here), an attacker's toughness and indestructibility, protection
    (Auriok Champion, Greensleeves), reach (Arasta of the Endless Web,
    Rendmaw, Ancient Greenwarden, Longshot, The Dawning Archaic),
    deathtouch and lifelink on a block, Bloodghast's "can't block",
    Sakura-Tribe Elder's chump-then-sacrifice, Ghostly Prison and
    Propaganda as taxes on declared attackers, Mother of Runes' protection
    on a blocker.

45. **A3-A7 of §0z197: write down, then decide.** None is a bug to fix in
    passing; each is a model decision nobody wrote down or made. **A4 is
    BUILT, in item 44's batch (§0z200, `rival_combat`, OFF).** A3 (the kill ignores your life and blockers) and A6 (the pod acts only
    in its own main phase) bound every lifegain and every haste/ETB row.
    A5 (walkers never attacked) follows A2 naturally -- the pod's declared
    attack can name one. A7 has a concrete defect inside it: azusa's Chord
    of Calling (fixed X=4, no convoke) against trostani's convoke and X
    plan, the same card under two rules. After item 44. **Chord is in
    item 47's batch; A3, A6 and A5 are step 5 of the order of work.**

46. **C-E of §0z197: the cheap ones, no rebuild. THE CHEAP HALF IS DONE
    (§0z206, 2026-11-14)**: Woe Strider is PARTLY_MODELLED; D's stale
    statements are corrected, with the ones the flip added ("your creatures
    never block"), and Bloodthirsty Conqueror and South Wind Avatar are
    SCRIPTED; `audit_cards` checks `haste` and `lifelink`, proved to fail
    (`tests/test_audit_keywords.py`). Every deck bit-identical at 2,000
    seeds. **THE THREE ORACLE AUDITS ARE DONE (2026-11-15)**: tivit §0z207,
    shilgengar §0z208, azusa §0z209 (`docs/ORACLE_AUDIT_*.md`); tivit's and
    shilgengar's labels are fixed. **Left, the owner's to choose from**:
    the audits' behaviour findings (each moves its deck's baseline, so
    before the rebuild is cheapest) -- tivit's Greaves-and-blinks, Tempting
    Contract, Grudge Keeper; shilgengar's Requiem Angel and landfall rule;
    azusa's Genesis Wave, Animist's Awakening and tutored ETBs first --
    azusa's labels; and card work for
    the add-card skill: ward, cycling, Woe Strider's sacrifice and escape,
    Memory Jar (C and item 37), and §0z206's five new floors (the Vault's
    deathtouch, an animated land's reach and indestructible, Nissa's
    emblem, a token's reach, The Swarmweaver's delirium deathtouch). Any
    time; none waits on item 44.
    **The behaviour findings are collected, in order, in item 47**
    (2026-11-15), with azusa's labels; the card work stays here.

47. **THE PRE-REBUILD BEHAVIOUR BATCH (order of work, step 1).** The
    findings of the three oracle re-audits (§0z207, §0z208, §0z209) and of
    §0z184 and §0z197 where the engine plays a card AGAINST its text and
    the fix moves the deck's baseline. Collected from items 46, 37 and 45
    so that one session can take them; those items keep the rest. The
    numbers in brackets are each audit file's own
    (`docs/ORACLE_AUDIT_<DECK>.md`), which has the code site and the text.
    **Nothing here is measured**: a size below is the audit's reading of
    the text, not a win rate.

    In this order (largest reading of the text first, per deck):

    - **azusa**: ~~Genesis Wave tutors the three biggest permanents in the
      whole library where the text reveals the top X (1)~~ **DONE
      2026-11-15 (§0z210)**: -0.0034 / -0.0039 at T10 / T20, the old
      rule's tutor for the mana-value-6 creatures; the mill costs nothing
      measurable. ~~Animist's
      Awakening takes the first four lands anywhere where the text
      averages 1.7 from the top four (2)~~ **DONE 2026-11-15 (§0z211)**:
      -0.0059 / -0.0051, 1.3 lands a cast where the old rule took 4;
      ~~a tutored or Waved creature fires no ETB -- `AzusaGame.etb` is
      called by `resolve` and Springheart's copy only (3)~~ **DONE
      2026-11-15 (§0z212)**: +0.0017 / +0.0042; Chord of Calling at a fixed X=4 with no
      convoke, against trostani's `convoke_pool` and `x_plan` for the same
      card (8, §0z197 A7; grep both engines, §0u). Then azusa's four
      labels (6-9), a rendering change: tivit's and shilgengar's are done.
    - **tivit**: Tempting Contract makes `1 + takers` Treasures where the
      card gives `takers` (2); Grudge Keeper puts all its damage on one
      opponent where each voter loses 2 (3); `on_creature_death` is a
      no-op, so Nadier's Nightblade, Disciple of the Vault and Marionette
      Master never hear a creature die -- and creatures die in combat
      since item 44 (8); `convert_the_pile` and Custodi Squire (4-6).
    - **shilgengar**: Requiem Angel tests the token's name, so Bloodghast
      and Kokusho, both Spirits, each make a Spirit
      (1; `_evasion.CREATURE_SUBTYPES` has the answer); the two landfall
      rules in `land_step` (2); combat lifelink read after the counters
      land (3); and item 37's timing pair -- Black Market Connections at
      the first main phase, `activations` inside main 2.
    - **THE OWNER'S, ask first**: tivit's Lightning Greaves (1). Shroud
      protects Tivit while five targeted blinks still target it. Whether
      Greaves stays on Tivit (and the blinks lose their best target) or
      comes off is a piloting policy; measure both and bring the numbers.

    **How each fix lands** -- the form every fix since §0z42 has taken:

    - Read the oracle text from Scryfall again; the audit is dated.
    - A cfg switch that restores the old rule exactly, and the new rule
      the default: the caches are already SUSPECT for a real reason, so
      there is nothing to keep bit-identical for. Prove the switch OFF
      plays the commit before it, every output key hashed (§0z32).
    - A pinned mechanism test with its mutation mode, the expected set
      written before the run (§0z11); `python -m tests` and `--mutate`.
    - `tools.validate` at `+0.00`, before and after.
    - A paired on/off run on the one deck, N 6,000 or more, T10 and T20:
      win rate with its bar, every output key that moved, and the
      mechanism counter that should move (§0z172). A fix that makes a new
      outcome possible gets the naive pilot measured too (§0z42).
    - A new `§` in `KNOWN_ISSUES.md` per deck with the numbers; the
      audit file's STATUS block updated; `tools.knobs --write`.
    - **No table is rebuilt** (item 44's protocol still holds), and no
      cache is cleared with `--verified`.

    Blind to (§0z15): rendmaw, lorehold and karlov were last audited on
    2026-09-03, before POD_V4 and item 44. Tivit's list had not changed
    either and its audit found 29 items. Re-auditing those three before
    the rebuild is the owner's call; it is not in this batch.

48. **AFTER THE REBUILD: what was decided on the old pod (order of work,
    step 4).** Every decision below was measured before item 44's flip
    (§0z204), on a pod where attacking was free and nobody blocked.
    - The eleven staged swaps (`python -m edhmc.pending`): one paired
      `run_ab` each on the new default, N=15,000, both horizons, as §0z81
      did after the last engine change of this size. A swap inside its
      bar goes to the owner as that, not as a withdrawal.
    - The adopted priority moves of item 18 (karlov, tivit, Time Sieve):
      swept on the formula pod (§0z205 says so). Re-run
      `diagnostics/run_priority_sweep.py` on fresh seeds (§0z170).
    - Read the rebuilt tables for the cards item 44 made live (its "text
      it makes live" list): a row that did not move is the tell of a
      mechanism that does not fire (check the counters first).
    - The noise floors: the CRN factor fell from ~15x to ~7x at the flip
      (§0z204), so expect wider bars at the same N. If the floors are too
      wide to read, that is a finding for the owner, not a reason to
      change N in one place.

49. **SMALL CLEANUPS (order of work, step 7)**, all from §0z205:
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
