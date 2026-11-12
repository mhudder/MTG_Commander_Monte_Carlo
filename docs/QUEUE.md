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

**Order of work (the owner, 2026-11-12): item 44 first** -- §0z197's A1 and
A2, tested step by step, with **no table rebuilt until that batch is done**.

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
    write down, not a bug.

44. **A1 AND A2 OF §0z197, FIRST (the owner, 2026-11-12): your attackers
    can die to blockers, and you block.** The combat half of §4, and the
    largest revision since pod v3. One piece of work, A1 then A2, through
    one combat resolution both directions share -- not two copies (§0u).

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

    **Decisions that are the owner's, to be asked, not assumed**: the pod's
    block rule once a block can trade (chump, trade or decline -- `chump`
    is chump-only); YOUR block rule, a pilot's not an optimiser's (§0v);
    which of the pod's bodies attack you and which the formula still
    stands for (`chip_amount` covers opponents without bodies); and
    whether the pod's attack becomes rolled rather than an expectation
    (§0z170's spread).

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
    passing; each is a model decision nobody wrote down or made. A4 (rivals
    never lose life to each other) was written down nowhere before §0z197.
    A3 (the kill ignores your life and blockers) and A6 (the pod acts only
    in its own main phase) bound every lifegain and every haste/ETB row.
    A5 (walkers never attacked) follows A2 naturally -- the pod's declared
    attack can name one. A7 has a concrete defect inside it: azusa's Chord
    of Calling (fixed X=4, no convoke) against trostani's convoke and X
    plan, the same card under two rules. After item 44.

46. **C-E of §0z197: the cheap ones, no rebuild.** Woe Strider from
    SCRIPTED to PARTLY_MODELLED in `tools/ablation.py` (a rendering change:
    re-render from the cache and diff, CLAUDE.md "Match the check to what
    moved"); the stale statements of D (`engine.py`'s docstring and its
    combat lifelink comment, the deathtouch note under Bloodthirsty
    Conqueror and South Wind Avatar, Guide of Souls); `haste` and
    `lifelink` checked against Scryfall's keywords by `audit_cards` or
    generated by `tag_flying` (E, with the check proved to fail, §0q); and
    oracle audits for tivit, shilgengar and azusa. Ward, cycling, Woe
    Strider's escape and Memory Jar (C and item 37) are card work for the
    add-card skill. Any time; none waits on item 44.
