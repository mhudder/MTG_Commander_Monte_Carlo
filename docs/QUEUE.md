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
  8-old, 17, 21, 2, 4, 8b, 0b-i, 23, 0c, 25, 26, 27, 20b and 24 are closed, each in
  `docs/HISTORY.md` under "Queued items closed …".
- 20, 20-old, 20-old2, 22, 7 and 8c were answered or superseded, and are in
  `docs/HISTORY.md` under "Queued items answered or superseded, moved
  2026-10-10".

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
    - **THE KARLOV REBUILD, DEFERRED BY THE OWNER** ("keep the rebuild as a
      queued item, dont do it quite yet"; still held 2026-11-02). The adoption moved karlov's
      baseline, so its cache is STALE BY DESIGN and `check_docs` fails on
      it until this runs. `DECKS=karlov ./tools/regen_tables.sh` on Python
      3.13.16 / numpy 2.4.6 (the parallel-rebuild skill's venv recipe),
      about 7 minutes; then `repro_row` a row, `--note` the cache, and
      re-measure the -Swamp +Citadel swap on the clock floor
      (`diagnostics/run_citadel_allin.py policies 15000 ... new noCit`)
      into its ledger entry. Never clear it with `--verified`.
    - **Necropotence with Reliquary Tower (§0z162), an owner call to batch
      with the rebuild above, HELD by the owner 2026-11-02** ("hold the
      decision for now"): buy past seven while the Tower is out
      (`necro_tower_target` 99, bounded by the floor and the decking
      reserve; 20 is the same): +0.0017 / +0.0013 at T10 / T20, N=60,000.
      The clock floor adds nothing for this card over a game.
    - **Hold Enlightened Tutor while the Citadel is out** (its skip fired 0
      times: the main phase casts it first), and use Ranger of Eos's and
      Land Tax's shuffles on a land on top. Two thirds of digs stop at one.

30. **Maximum hand size is unmodelled in every engine** (CR 402.2, 514.1;
    found in §0z162). Nothing discards to seven at cleanup, so every draw
    engine and every "draw more" policy is flattered: 7.9% of karlov's end
    steps without Reliquary Tower hold more than seven, 3.5 over on average.
    A shared cleanup step in each engine's turn (which cards to discard is a
    pilot's choice: the want order's worst), Reliquary Tower and its kin
    lifting it, Necropotence's exile clause live. Measure the shift per deck
    at the tables' N before deciding (§0z30: its size is not guessable); it
    moves every baseline, so it is a batched rebuild.

31. **Lorehold's miracle policy (§0z164), an owner call, HELD by the owner
    2026-11-02** ("hold the decision for now"). Nothing is adopted and
    lorehold's cache is VERIFIED; adopting is what moves it. Measured at
    N=60,000: hold NO miracle mana (`miracle_reserve` 0) and NEVER decline a
    hardcast to wait for a miracle (`hold_min_value` 99) -- together +0.0166
    ±0.0028 / +0.0109 ±0.0032 at T10 / T20; each alone significant at both.
    Sensei's Top is already played right. Adopting moves lorehold's baseline:
    rebuild its table with it (`DECKS=lorehold ./tools/regen_tables.sh` on
    Python 3.13.16 / numpy 2.4.6), and re-measure lorehold's four staged
    swaps (`diagnostics/run_restage.py`), several of which are miracle cards.
    **What the holds buy, counted (§0z165)**: of the cards `hold_for_miracle`
    keeps, about half are still in hand when the game ends and a fifth are
    miracled; the reserve's keep Furygale Flocking and Approach of the
    Second Sun first.
    **Two more for the same batch (§0z166)**, both moving lorehold's
    baseline: the off-turn float counts every Treasure twice and carries
    Apex / Explosive Welcome mana past CR 106.4 (an engine defect; §0z164's
    change survives its fix, +0.0163 / +0.0108); and the rummage discards by
    miracle value, so it pitches non-miracle engines first -- discarding by
    cast priority is +0.0155 ±0.0043 at T10, level at T20, N=30,000.
    **Forked (§0z167)**: no rule wins at both horizons -- the permanents the
    rummage pitches feed Restoration Seminar and Profound Journey -- and
    under §0z164's no-hold policy priority and guard LOSE at T20 (-0.0058,
    -0.0043, N=60,000). Keep the default unless the owner wants the T10
    trade; `rummage_pick` "mv" is the only rule never negative (+0.0032 /
    +0.0054 at T10, level at T20).


32. **The deferral protocol (the owner, 2026-11-02; §0z165).** A deferral is
    a bet: the pilot acts unless a measured payoff says wait. Done, read-only:
    the inventory (`python -m tools.deferrals`, 38 main-phase sites in seven
    engines, derived and classified, `--check` and `tests/test_deferrals.py`
    hold it) and the census (`diagnostics/run_deferral_census.py`: how often
    each site changes what is cast, and what became of the card held; every
    traced game identical to its untraced twin). Nothing moved. Left, in order:
    - **Lorehold's two holds are queue item 31**, the owner's decision; the
      census is evidence for it (most cards the miracle hold keeps die in hand).
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
