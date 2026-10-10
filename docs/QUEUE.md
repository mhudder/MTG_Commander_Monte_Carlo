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

20b. **TWO ARE NOW STAGED, ON HEAD-TO-HEAD EVIDENCE** (2026-09-16).
    `-Soulmender +Bloodthirsty Conqueror` (karlov, **+0.0257 ±0.0028 at T10
    and +0.0247 ±0.0035 at T20**) and `-Plains +Anointed Procession` (tivit,
    **+0.0113 ±0.0026 / +0.0145 ±0.0040**), both significant at BOTH horizons.
    **The real swap is SMALLER than the candidate row in both cases** — the
    candidate number is value over a blank in a freed slot, the swap also pays
    for what it cut, and §0c says the swap is the number a decision rests on.
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
    recorded on the Change. Two more are explicitly HELD:
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
