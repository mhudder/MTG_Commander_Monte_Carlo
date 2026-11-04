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
  8-old, 17, 21, 2, 4, 8b, 0b-i, 23, 0c, 25, 26, 27, 20b, 24 and 31 are closed, each in
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
    - **The karlov rebuild is DONE** (the owner, 2026-11-03; §0z169): 0 rows
      moved, the cache CURRENT, the Citadel swap +0.0121 / +0.0088 on the
      clock floor, all three staged swaps standing.
    - **Necropotence with Reliquary Tower is ADOPTED** (the owner,
      2026-11-04, §0z173): `necro_tower_target` 99, re-measured out of
      sample on the cleanup step, +0.0024 / +0.0011.
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

33. **A card on the battlefield AND in the graveyard at once (§0z171's zone
    census).** At a pod round, the same Card object sits in `g.board` (as
    `p.card`) and in `g.graveyard`: azusa 13 games in 1,000, trostani 1-2
    (and once battlefield + hand), the other five decks 0, with or without
    the cleanup step. Many token permanents sharing ONE token Card is by
    design and not this. Likely the shape §0z171 fixed in its own code:
    moving a CHOSEN card with `engine.remove_card` (first EQUAL card, not that
    object) -- `engine.remove_exact` is the identity version. Find the sites,
    fix, prove the census reads 0, measure the shift (§0z30). Trostani is
    SUSPENDED: fix shared code it needs, do not re-measure it.
