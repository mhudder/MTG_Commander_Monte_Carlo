"""
edhmc.pending — staged deck changes, not yet written to the spreadsheets.

The .xlsx files remain the system of record. This module holds changes that
have been decided but not yet applied to all three legs (deck module, .xlsx,
this ledger), so that:

  1. further A/B tests run against the CURRENT intended list rather than a
     stale baseline, and
  2. there is one place to read off the full pending diff when it is time to
     update the spreadsheets.

Usage:
    from edhmc.pending import build_pending, ledger
    deck, commander = build_pending("rendmaw")     # changes applied
    deck, commander = build_pending("rendmaw", apply_pending=False)  # original
    ledger()                                       # print the diff

    python -m edhmc.pending                  # checks, legality, staged cuts, counts
    python -m edhmc.pending --summary        # one line per entry (the default until 2026-10-11)
    python -m edhmc.pending --card Conqueror # the evidence for entries naming a card
    python -m edhmc.pending --deck karlov    # the evidence for one deck
    python -m edhmc.pending --full           # everything (the default until 2026-10-10)

THE THREE STATES, which HANDOFF.md has always described and this module only
had structures for two of:

    MEASURED   a number and a confidence interval exist. NO decision. Names no
               cut. `MEASURED: list[Candidate]`, added 2026-09-10 -- before
               that this state lived in comments and in `results/` files that
               nothing reads, which is the state most easily lost, because a
               number with no decision attached looks like one somebody forgot
               to act on.
    STAGED     decided, with a cut named, and applied to this ledger only.
               `CHANGES: list[Change]`. `build_pending` applies these.
    COMMITTED  applied to all three legs -- deck module, .xlsx, this ledger --
               in ONE git commit. `COMMITTED: list[Change]`. Azusa has no
               .xlsx and is two legs.

Measured does NOT become staged by being good. It becomes staged by a
head-to-head against a specific cut, because everything in MEASURED shares a
baseline and a common baseline cannot rank two cards against each other (§0e).

To stage a change, append to CHANGES. To commit, update the spreadsheet and
the deck module, then move the entry to COMMITTED.

AND THE FOURTH STATE, added 2026-09-13:

    WITHDRAWN  was STAGED and has been UNSTAGED. `WITHDRAWN: list[Change]`,
               each carrying a `withdrawn` field saying when and why.
               `build_pending` does NOT apply these, so an unstaged change is
               out of every baseline the moment it moves here.

It exists because DELETING the entry was the alternative, and the entry is
where the evidence lives. A swap that was staged and then unstaged is not the
same thing as a swap nobody ever proposed: the next reader needs to know it was
considered, what it measured, and what took it off the list -- otherwise the
same card gets re-measured and re-staged from scratch. This is the ledger's
version of the `-old` entries CLAUDE.md keeps for its superseded findings.

A WITHDRAWN entry is NOT a refutation. Re-staging one is a matter of moving it
back to CHANGES with fresh evidence; the `withdrawn` field says what that
evidence would have to answer.
AND THE SIMULATED/STAGED SPLIT, plus PREPARED (2026-09-29, §0z79), which
`docs/LEDGER_STATES.md` designed and the owner confirmed on 2026-09-22:

    PREPARED   a flag on a Proposal: the engine work is done, and it names
               the test that pins it (`Proposal.prepared`).
    SIMULATED  a head-to-head against a named cut, with NO decision.
               `SIMULATED: list[Simulated]`. A staged Change is a head-to-head
               plus a decision, and its head-to-head half is DERIVED
               (`Change.simulated`); `simulations()` returns both kinds.

`docs/LEDGER_STATES.md` is the vocabulary, and `check_docs` fails if it omits
a state implemented here. The order is PROPOSED -> PREPARED -> MEASURED ->
SIMULATED -> STAGED -> COMMITTED, with WITHDRAWN beside STAGED.
"""

from __future__ import annotations

import re
import sys

from edhmc.experiment import _swap_many
from edhmc.ledger import catalogs, gather
# Re-exported: every importer of the ledger's record types imports them from
# here, and keeps doing so. The DATA is in edhmc/ledger/<deck>.py (2026-10-11).
from edhmc.ledger.records import Candidate, Change, Proposal, Simulated  # noqa: F401
from edhmc.registry import DECKS as REGISTRY


# The commanders' colour identities, fetched from Scryfall 2026-09-16 rather
# than derived from cost pips -- a commander's identity includes its ability
# text, so the cost is not always the whole answer and deriving it would be a
# guess dressed as a derivation.
# From edhmc/registry.py (§0z32), where every other per-deck fact lives.
DECK_IDENTITY = {name: set(spec.identity) for name, spec in REGISTRY.items()}


# THE ENTRIES LIVE IN edhmc/ledger/<deck>.py, one module per deck (2026-10-11).
# Each list below is gathered from them in edhmc/registry.py's deck order, each
# deck's entries in its own file's order -- the order build_pending applies.
# To add, move or edit an entry, edit that deck's file; the comments below say
# what each list means.

# ---------------------------------------------------------------------------
# Committed — reflected in BOTH the deck module and the .xlsx
# ---------------------------------------------------------------------------
COMMITTED: list[Change] = gather("COMMITTED")

# ---------------------------------------------------------------------------
# Measured — a number exists, NO decision has been taken
# ---------------------------------------------------------------------------
# Nothing in this list is staged, and nothing in it names a cut. Read a row as
# "this card was measured at this value in this slot", never as "this card is
# going in". Promotion to CHANGES needs a head-to-head against a specific cut,
# because everything here shares one baseline and therefore cannot be ranked
# against anything else measured the same way (§0e).
# ---------------------------------------------------------------------------
MEASURED: list[Candidate] = gather("MEASURED")

# ---------------------------------------------------------------------------
# Staged — decided, not yet in the spreadsheets
# ---------------------------------------------------------------------------
CHANGES: list[Change] = gather("CHANGES")


# ---------------------------------------------------------------------------
# Withdrawn — was staged, and has been UNSTAGED
# ---------------------------------------------------------------------------
# NOT applied by `build_pending`, so nothing here is in any baseline.
# Kept in full because the entry is where the evidence lives, and a swap
# that was considered and dropped is a different fact from one nobody
# ever proposed. See the module docstring.
WITHDRAWN: list[Change] = gather("WITHDRAWN")


# ---------------------------------------------------------------------------
# SIMULATED (§0z79): head-to-heads with NO staging -- evidence waiting on a
# decision, or evidence a decision went against. Generated on 2026-09-29 from
# every MEASURED entry whose `win_rate` was a REAL SWAP rather than a
# candidate row (their text is copied verbatim), plus three recorded only in
# other entries' prose. The staged ones are not here: `Change.simulated`.
#
# THE §0z74 MYSTERY BOOSTER ROWS ARE THE OWNER'S OPEN DECISIONS. They were
# measured before §0z75-§0z77 moved karlov, shilgengar and rendmaw, and
# RE-MEASURED after it (each record's `notes`): every swap within 0.0008 of
# its first number, no order changed, tivit's identical.
# ---------------------------------------------------------------------------
SIMULATED: list[Simulated] = gather("SIMULATED")


# ---------------------------------------------------------------------------
# PROPOSED, 2026-09-16. Oracle text fetched from api.scryfall.com the same day
# and pasted verbatim. NOTHING HERE IS MEASURED -- these are arguments with
# verified card text attached, and the next step for each is a
# `tools/candidates.py` batch entry, not a staging.
#
# The two rejected entries are KEPT rather than deleted, for WITHDRAWN's
# reason: a proposal that was considered and found illegal is not the same
# thing as one nobody thought of, and without the record the same two cards get
# proposed again. Both were caught by the colour-identity check below, which is
# why that check exists.
# ---------------------------------------------------------------------------
PROPOSED: list[Proposal] = gather("PROPOSED")


DECKS = catalogs()

# The catalog is per deck and hand-written (which candidate cards a Change
# may name); the SET of decks is the registry's, and the two are checked
# against each other at import -- §0q's rule, pointed at this file.
if set(DECKS) != set(REGISTRY):
    raise ImportError(
        f"edhmc/pending.py's DECKS catalog names {sorted(DECKS)} but "
        f"edhmc/registry.py names {sorted(REGISTRY)}; a deck needs an entry "
        f"in both (its catalog may be empty).")


TRIAGE_VERDICTS = ("", "LIVE", "BLIND", "DEFERRED")


def check_triage(pr) -> None:
    """A triage flag must carry what makes it re-checkable (item 23).

    BLIND names at least one clause, and every clause it names is in the
    card's own oracle text (whitespace-normalised) -- so a verdict cannot
    cite text the card does not have. DEFERRED names its machinery.
    """
    if pr.triage not in TRIAGE_VERDICTS:
        raise AssertionError(
            f"edhmc/pending.py: PROPOSED {pr.card!r} has triage "
            f"{pr.triage!r}; it must be one of {TRIAGE_VERDICTS}.")
    oracle = " ".join(pr.oracle.split())
    if pr.triage == "BLIND":
        if not pr.triage_clauses:
            raise AssertionError(
                f"edhmc/pending.py: PROPOSED {pr.card!r} is triaged BLIND but "
                f"names no clause. Quote the clauses the engine cannot see "
                f"(`python -m tools.triage --proposals` lists them).")
        for c in pr.triage_clauses:
            if " ".join(c.split()) not in oracle:
                raise AssertionError(
                    f"edhmc/pending.py: PROPOSED {pr.card!r}'s BLIND clause "
                    f"{c!r} is not in its oracle text.")
    if pr.triage == "DEFERRED" and not pr.triage_note.strip():
        raise AssertionError(
            f"edhmc/pending.py: PROPOSED {pr.card!r} is triaged DEFERRED but "
            f"does not name the machinery it waits for (`triage_note`).")


def check_prepared(pr) -> None:
    """PREPARED names the test that pins the card, and the test exists."""
    if not pr.prepared:
        return
    import os
    import re
    # The note is free text that STARTS with the path ("tests/x.py, 2026-..."),
    # so the path is matched, not split off: a trailing comma once made an
    # existing test look missing (tests/test_ledger_states.py, case E).
    m = re.match(r"(tests/[\w/]+\.py)\b", pr.prepared.strip())
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not (m and os.path.exists(os.path.join(root, m.group(1)))):
        raise AssertionError(
            f"edhmc/pending.py: PROPOSED {pr.card!r} is PREPARED as "
            f"{pr.prepared!r}, which does not start with a test file on disk "
            f"(tests/....py). PREPARED means implemented AND pinned (§0z79).")


def _staged_have_evidence(staged) -> None:
    for ch in staged:
        if not ch.evidence.strip():
            raise AssertionError(
                f"edhmc/pending.py: {ch.deck} -{ch.remove} +{ch.add} is staged "
                f"with no `evidence` -- a STAGED decision needs its SIMULATED "
                f"half, the head-to-head against the named cut (§0z79).")


def _simulated_complete(simulated) -> None:
    for r in simulated:
        if not (r.result.strip() and r.remove.strip() and r.add.strip()):
            raise AssertionError(
                f"edhmc/pending.py: SIMULATED {r.deck} -{r.remove} +{r.add} "
                f"is missing its cut, its add or its result.")


def _not_simulated_and_staged(simulated, staged) -> None:
    keys = {(c.deck, c.remove, c.add) for c in staged}
    for r in simulated:
        if (r.deck, r.remove, r.add) in keys:
            raise AssertionError(
                f"edhmc/pending.py: {r.deck} -{r.remove} +{r.add} is in "
                f"SIMULATED and staged. Staging a head-to-head MOVES it to "
                f"CHANGES; delete the SIMULATED record (§0z79).")


def check_simulated(simulated=None, staged=None) -> None:
    """The SIMULATED/STAGED split holds (§0z79).

    1. Every STAGED or COMMITTED Change carries its head-to-head: `evidence`
       is its SIMULATED half, and a staging with none is a decision with no
       evidence.
    2. A SIMULATED record has a result, and names a cut and an add.
    3. No head-to-head is in SIMULATED AND staged: staging MOVES it.

    One function per rule, so a mutation can switch off exactly one
    (tests/test_ledger_states.py).
    """
    simulated = SIMULATED if simulated is None else simulated
    staged = CHANGES + COMMITTED if staged is None else staged
    _staged_have_evidence(staged)
    _simulated_complete(simulated)
    _not_simulated_and_staged(simulated, staged)


# The funnel's order, furthest first (docs/LEDGER_STATES.md). WITHDRAWN sits
# beside STAGED: it was staged and is not now.
FUNNEL = ("COMMITTED", "STAGED", "WITHDRAWN", "SIMULATED", "MEASURED",
          "PREPARED", "PROPOSED", "REJECTED")


def _further(state: str, than: str) -> bool:
    """Is `state` further along the funnel than `than`? A function so a
    mutation can switch this one rule off (tests/test_ledger_states.py)."""
    return FUNNEL.index(state) < FUNNEL.index(than)


def funnel() -> dict[str, list[tuple[str, str]]]:
    """Each CARD once, in the furthest state any record of it has reached.

    A record is never deleted when its card moves on -- the Proposal stays
    after the card is measured, the Candidate after it is staged -- and that
    is right, because each record holds different evidence. But counting
    RECORDS said ten cards were "proposed" when all ten had long been
    measured and two were staged (§0z80). So the funnel is derived per card:
    (deck, card) -> the furthest state, the card being a Change's or a
    Simulated's `add`, a Candidate's or a Proposal's `card`. A REJECTED
    proposal counts as rejected only if nothing else has taken it further.
    """
    reached: dict[tuple[str, str], str] = {}

    def mark(deck, card, state):
        key = (deck, card)
        if key not in reached or _further(state, reached[key]):
            reached[key] = state

    for c in COMMITTED:
        mark(c.deck, c.add, "COMMITTED")
    for c in CHANGES:
        mark(c.deck, c.add, "STAGED")
    for c in WITHDRAWN:
        mark(c.deck, c.add, "WITHDRAWN")
    for r in SIMULATED:
        mark(r.deck, r.add, "SIMULATED")
    for c in MEASURED:
        mark(c.deck, c.card, "MEASURED")
    for pr in PROPOSED:
        mark(pr.deck, pr.card, "REJECTED" if pr.rejected else
             "PREPARED" if pr.prepared else "PROPOSED")
    out: dict[str, list[tuple[str, str]]] = {st: [] for st in FUNNEL}
    for key, st in reached.items():
        out[st].append(key)
    return out


def simulations() -> list[Simulated]:
    """Every head-to-head the ledger holds: the unstaged ones, and the
    derived halves of every staged, committed and withdrawn Change."""
    return list(SIMULATED) + [c.simulated
                              for c in CHANGES + COMMITTED + WITHDRAWN]


def check_proposals(strict: bool = True):
    """Every live PROPOSED entry is colour-legal, verified, and not already in.

    THREE CHECKS, AND THE FIRST ONE HAS ALREADY FIRED IN ANGER. Two azusa
    proposals -- Felidar Retreat (W) and Omnath, Locus of Rage (GR) -- were
    written from memory into a MONO-GREEN deck. They are kept in PROPOSED with
    `rejected` set, which is what this check demands of a dead entry.

      1. COLOUR IDENTITY must fit the commander's. A proposal that cannot be
         cast is not a weak idea, it is not an idea.
      2. ORACLE TEXT AND A VERIFIED DATE must be present. `CLAUDE.md` forbids
         guessing oracle text, and a proposal made from memory is that failure
         one step earlier. No Scryfall, no Proposal.
      3. NOT ALREADY IN THE DECK -- §0o in the ledger rather than the harness.
      4. A TRIAGE FLAG CARRIES ITS EVIDENCE -- `check_triage`, item 23.

    A rejected entry is exempt from 1 and 3 and still bound by 2: the record of
    WHY it was rejected is worth nothing if the text it was rejected on is not
    there to check.
    """
    for pr in PROPOSED:
        if not pr.oracle.strip() or not pr.verified.strip():
            raise AssertionError(
                f"edhmc/pending.py: PROPOSED {pr.card!r} has no verified "
                f"oracle text. Fetch it from api.scryfall.com and set "
                f"`verified`; do not write card text from memory.")
        check_triage(pr)
        check_prepared(pr)
        if pr.rejected:
            continue
        ident = set(pr.identity)
        allowed = DECK_IDENTITY[pr.deck]
        if not ident <= allowed:
            raise AssertionError(
                f"edhmc/pending.py: PROPOSED {pr.card!r} has colour identity "
                f"{''.join(sorted(ident)) or 'C'} but {pr.deck} is "
                f"{''.join(sorted(allowed))}. It cannot be cast in that deck. "
                f"Either remove it or set `rejected` with the reason.")
        if strict:
            module, _catalog = DECKS[pr.deck]
            deck, _ = module.build()
            if any(card.name == pr.card for card in deck):
                raise AssertionError(
                    f"edhmc/pending.py: PROPOSED {pr.card!r} is ALREADY IN "
                    f"{pr.deck}, so it describes an addition that cannot "
                    f"happen (§0o).")


def check_measured_are_promotable():
    """Every MEASURED card must be in its deck's catalog, and must NOT already
    be in the deck.

    Both halves are the §0q rule applied to this file. A Candidate naming a
    card the catalog does not hold cannot be promoted to a Change without an
    edit nobody will remember is needed -- the row would sit here looking
    actionable and fail the moment it was acted on. And a Candidate naming a
    card that has since been COMMITTED is the §0o failure in the ledger rather
    than in the harness: a measured row for a card already in the list reads
    as an available add and is not one.
    """
    for c in MEASURED:
        module, catalog = DECKS[c.deck]
        if c.card not in catalog:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is MEASURED for {c.deck} but is "
                f"not in DECKS[{c.deck!r}]'s catalog, so no Change could name "
                f"it. Add the Card to the catalog.")
        deck, _ = module.build()
        if any(card.name == c.card for card in deck):
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is MEASURED for {c.deck} but is "
                f"ALREADY IN the list, so the row describes an addition that "
                f"cannot happen. Move it out of MEASURED -- it is committed.")


def check_shortlist_is_answerable():
    """A shortlisted Candidate names a cut, and that cut is really in the deck.

    The flag exists to survive being read months later, so the two ways it can
    silently stop meaning anything are both checked:

      * SHORTLISTED WITH NO CUT NAMED is the state this flag was invented to
        replace. "These are the good ones" without a cut is exactly the
        conversation that gets lost, and §0e is why naming the cut matters: a
        candidate row and an ablation row share a baseline, so the pair CANNOT
        be subtracted to get the swap -- somebody has to run it.
      * A CUT THAT LEFT THE DECK. Proposed cuts age badly: the list moves
        (four azusa cards were committed on 2026-09-10 and Perilous Forays is
        cut by a staged change), and a proposal naming a card that is no longer
        there reads as actionable and is not. Same shape as §0o.

    Whether the cut is MODEL-BLIND or PARTLY MODELLED -- the trap that cost
    this project two withdrawn swaps (§0z, §0z2) -- is `check_cuts_are_measured`
    below, which could not exist while `tools/ablation.py` read `sys.argv` at
    import (until 2026-09-17, §0z31).
    """
    for c in MEASURED:
        if not c.shortlist:
            if c.proposed_cut:
                raise AssertionError(
                    f"edhmc/pending.py: {c.card!r} names a proposed cut but is "
                    f"not shortlisted, so nothing prints it and the proposal "
                    f"is invisible. Set `shortlist`, or drop `proposed_cut`.")
            continue
        if not c.proposed_cut:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} is SHORTLISTED for {c.deck} "
                f"with no `proposed_cut`. A shortlist without a named cut is "
                f"the conversation this flag exists to replace -- name the cut "
                f"the head-to-head should run, or clear the flag.")
        module, _ = DECKS[c.deck]
        deck, _cmd = module.build()
        staged_out = {ch.remove for ch in CHANGES if ch.deck == c.deck}
        if not any(card.name == c.proposed_cut for card in deck):
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} proposes cutting "
                f"{c.proposed_cut!r}, which is NOT IN the {c.deck} list, so "
                f"the head-to-head could not be run as written.")
        if c.proposed_cut in staged_out:
            raise AssertionError(
                f"edhmc/pending.py: {c.card!r} proposes cutting "
                f"{c.proposed_cut!r}, which a STAGED change already removes. "
                f"Two changes cannot cut the same card; pick another target.")


def classify_cut(deck_name: str, card_name: str) -> str:
    """How `tools/ablation.py` classifies `card_name` in `deck_name`'s MODULE
    list: 'evaluated', 'partly', 'blind', 'land', 'unclassified' or 'absent'.

    The module list, not the staged one: a staged cut has already left the
    staged list, which is exactly why `check_scripted_coverage` never sees
    it -- that check classifies what is measured, and a cut card is not.
    Imported lazily: ablation.py imports this module, so the import cannot
    be at the top of this file.
    """
    import tools.ablation as AB
    module, _ = DECKS[deck_name]
    deck, _cmd = module.build()
    card = next((c for c in deck if c.name == card_name), None)
    if card is None:
        return "absent"
    if card.is_land and not card.script:
        return "land"
    if card_name in AB.SCRIPTED_BY_DECK[deck_name]:
        return "evaluated"
    if card_name in AB.partly_for(deck_name, deck):
        return "partly"
    if card_name in AB.KNOWN_BLIND[deck_name]:
        return "blind"
    return "unclassified"


def check_cuts_are_measured(changes=None, candidates=None) -> list[str]:
    """Every STAGED cut and every PROPOSED cut is a card whose ablation row
    meant something -- or says why it is being cut anyway.

    A MODEL-BLIND row is "not measured", never a cut list (CLAUDE.md), and a
    PARTLY MODELLED row is a floor. A swap staged on either is the trap that
    produced §0z and §0z2, two withdrawn swaps. The head-to-head that stages
    a swap does not rescue it: the cut side of that comparison is the card
    AS THE ENGINE MODELS IT, so against a blind cut the swap's number is a
    CEILING. `cut_unmeasured` on the Change or Candidate is the required
    acknowledgement, and the first run of this check found one to write:
    Soulmender, the cut behind `-Soulmender +Bloodthirsty Conqueror`, is
    KNOWN_BLIND in karlov, and §0z27 had read its row as evidence.

    A cut in NO category is refused outright -- classify it in ablation.py.
    The first run found two: Penance and Scroll Rack, staged out of lorehold
    on 2026-09-05 and dropped from SCRIPTED_LOREHOLD for that reason, so the
    cards whose rows justified the cuts were the only lorehold cards with no
    classification at all.

    A LAND cut passes with a note: lands are unclassified by design, and a
    land cut is the kind of change the harness flatters (CLAUDE.md, 20b).

    Not run at import: `tools.ablation` imports this module, so this runs
    from `ledger()` (`python -m edhmc.pending`) and from
    `tests/test_pending_cuts.py`, both of which the closing checklist runs.
    Returns the report lines; raises on a violation.
    """
    changes = CHANGES if changes is None else changes
    candidates = MEASURED if candidates is None else candidates
    lines, bad = [], []
    items = [("STAGED", c.deck, c.remove, c.add, c.cut_unmeasured)
             for c in changes]
    items += [("PROPOSED", c.deck, c.proposed_cut, c.card, c.cut_unmeasured)
              for c in candidates if c.proposed_cut]
    for kind, deck, cut, add, ack in items:
        cls = classify_cut(deck, cut)
        tag = f"{kind:<8} {deck:<11} -{cut} +{add}"
        if cls == "land":
            lines.append(f"  {tag}: a LAND cut -- the harness flatters these")
        elif cls == "evaluated":
            lines.append(f"  {tag}: MODEL-EVALUATED cut")
        elif cls in ("blind", "partly"):
            label = "MODEL-BLIND" if cls == "blind" else "PARTLY MODELLED"
            if ack.strip():
                lines.append(f"  {tag}: {label} cut, acknowledged -- {ack}")
            else:
                bad.append(f"{tag}: {cut!r} is {label} in {deck}, so its row "
                           f"is not evidence and the head-to-head is a "
                           f"CEILING. Say why it is cut anyway in "
                           f"`cut_unmeasured`, or pick a MODEL-EVALUATED cut.")
        elif cls == "unclassified":
            bad.append(f"{tag}: {cut!r} is in NONE of SCRIPTED_{deck.upper()}, "
                       f"PARTLY_MODELLED or KNOWN_BLIND -- a staged cut leaves "
                       f"the measured list, so check_scripted_coverage never "
                       f"sees it. Classify it in tools/ablation.py.")
        else:
            bad.append(f"{tag}: {cut!r} is not in the {deck} module list.")
    if bad:
        raise AssertionError("edhmc/pending.py: a cut whose row is not "
                             "evidence:\n" + "".join(f"    {b}\n" for b in bad))
    return lines


def check_withdrawn_are_explained():
    """Every WITHDRAWN entry states WHY, and is in exactly one of the lists.

    Written in the same change that added the list, and mutation-checked, for
    the reason §0q gives: a state with no check is a claim nobody verifies.
    The two failures it exists to catch are the two this state makes possible.

    An UNEXPLAINED withdrawal is the worse of them. The entry keeps its full
    original evidence -- rationale, data, every recheck -- so an entry with an
    empty `withdrawn` reads exactly like a well-supported staged change that
    somebody moved by accident, and the next reader's correct response to it
    would be to move it back. The reason is the only field that distinguishes
    "we decided against this" from "this fell out of the list".

    A card in BOTH lists is the §0z16 shape pointed at the ledger: one card,
    two states, and each list internally consistent. `build_pending` would
    apply it and this file would simultaneously say it applies to nothing.
    """
    for c in WITHDRAWN:
        if not c.withdrawn.strip():
            raise AssertionError(
                f"edhmc/pending.py: -{c.remove} +{c.add} ({c.deck}) is "
                f"WITHDRAWN with no `withdrawn` reason. An entry that keeps "
                f"its evidence and drops its reason is indistinguishable from "
                f"one unstaged by mistake. Say when, and why.")
        clash = [s for s in CHANGES
                 if s.deck == c.deck and s.add == c.add and s.remove == c.remove]
        if clash:
            raise AssertionError(
                f"edhmc/pending.py: -{c.remove} +{c.add} ({c.deck}) is in "
                f"CHANGES and WITHDRAWN at once, so the ledger both applies it "
                f"to every baseline and says it is in none. Delete one.")


def check_alt_cost_coverage():
    """Every card with a second cost sits in a deck whose engine reads them.

    §1b, closed 2026-09-13 (§0z20). `Card.alt_costs` existed for a year and
    `engine.main_phase` was the ONLY reader, so Overlord of the Hauntwoods'
    Impending worked in Rendmaw and the identical field on a card put into
    Karlov, Tivit, Shilgengar or Azusa would have been silently ignored --
    cast at its printed cost, no error, no way to notice. That is §0q's
    failure mode with the claim living in a DATA FIELD instead of a name set:
    setting `alt_costs` looks like it does something everywhere.

    All six engines now go through `engine.choose_mode`, and this is the check
    that says so. It is derived, not hand-maintained: the reader set is read
    off the engines' source, so an engine that stops calling `choose_mode`
    fails here rather than quietly dropping a cost.
    """
    import inspect
    # DERIVED from the registry (2026-10-01): the hand-written six-engine
    # dict this replaced refused the seventh deck's first hybrid card.
    engines = {name: spec.engine_module for name, spec in REGISTRY.items()}
    # `choose_mode_cost` is the same choice without the payment (§0z147),
    # and reads `alt_costs` through the same `castable_modes`.
    readers = {name for name, mod in engines.items()
               if re.search(r"\bchoose_mode(_cost)?\(",
                            inspect.getsource(mod))}
    missing = set(engines) - readers
    if missing:
        raise AssertionError(
            f"edhmc/pending.py: {sorted(missing)} do not call "
            f"engine.choose_mode (or choose_mode_cost), so any card with "
            f"`alt_costs` in those decks "
            f"would be cast at its printed cost silently. §1b / §0z20.")

    for deck_name, (module, _catalog) in DECKS.items():
        deck, commander = module.build()
        for card in list(deck) + [commander]:
            if card.alt_costs and deck_name not in readers:
                raise AssertionError(
                    f"edhmc/pending.py: {card.name!r} declares alt_costs but "
                    f"the {deck_name} engine does not read them.")
            for entry in card.alt_costs:
                if len(entry) not in (2, 3):
                    raise AssertionError(
                        f"edhmc/pending.py: {card.name!r} has a malformed "
                        f"alt_costs entry {entry!r}; expected (cost, tag) or "
                        f"(cost, tag, preference).")


# Planeswalkers modelled BY NAME, as statics, with no loyalty (§0z74). Each
# was found by the first run of `check_loyalty_coverage`; each is a FLOOR or an
# approximation for the reason given, and none was listed anywhere before.
WALKERS_WITHOUT_LOYALTY = {
    "Grist, the Hunger Tide": (
        "rendmaw: a 1/1 Insect creature everywhere but the battlefield "
        "(engine.STACK_ONLY_CREATURES); its upkeep Insect is scripted; its "
        "loyalty abilities are not modelled."),
    "Sorin, Vengeful Bloodlord": (
        "karlov: its static ('during your turn, creatures and planeswalkers "
        "you control have lifelink') is read by name in karlov.combat; its +2 "
        "and -X are not modelled, a floor."),
    "Sorin, Solemn Visitor": (
        "karlov: its +1's team lifelink is read by name in karlov.combat as "
        "though it stood every turn; the +1/+0 and the -2 Vampire token are "
        "not modelled."),
}


def check_loyalty_coverage():
    """Every Planeswalker outside azusa enters with loyalty AND is activated.

    §0q, pointed at `engine.PLANESWALKER_LOYALTY` (§0z74), which is a
    hand-written name set. A walker missing from it enters with zero loyalty;
    a walker in it whose deck engine never activates it enters with loyalty and
    does nothing. Either way it scores as a blank and looks like a weak card,
    which is the failure `azusa.check_planeswalker_coverage` was written for
    one engine earlier. Checked over every deck list AND every catalog, since
    a catalog card is one `Change` away from a list.

    AZUSA IS EXEMPT -- it has its own table and its own check. So are the
    walkers in `WALKERS_WITHOUT_LOYALTY` below, each with the reason: they
    predate this table and are modelled BY NAME as statics, with no loyalty
    tracked. That is a blind spot and it is written down (§0z15): the first
    run of this check found all three, which nobody had listed.
    """
    import inspect
    from edhmc.engine import PLANESWALKER_LOYALTY, WALKER_READERS
    if set(PLANESWALKER_LOYALTY) != set(WALKER_READERS):
        raise AssertionError(
            "edhmc/engine.py: PLANESWALKER_LOYALTY and WALKER_READERS name "
            f"different walkers: {sorted(set(PLANESWALKER_LOYALTY) ^ set(WALKER_READERS))}.")
    # DERIVED from the registry (2026-10-01), as check_alt_cost_coverage is.
    sources = {name: inspect.getsource(spec.engine_module)
               for name, spec in REGISTRY.items() if name != "azusa"}
    seen = set()
    for deck_name, (module, catalog) in DECKS.items():
        if deck_name == "azusa":
            continue
        deck, commander = module.build()
        for card in list(deck) + [commander] + list(catalog.values()):
            if "Planeswalker" not in card.types:
                continue
            if card.name in WALKERS_WITHOUT_LOYALTY:
                seen.add(card.name)
                continue
            if card.name not in PLANESWALKER_LOYALTY:
                raise AssertionError(
                    f"edhmc/pending.py: {card.name!r} is a Planeswalker in "
                    f"{deck_name} with no entry in engine.PLANESWALKER_LOYALTY, "
                    f"so it would enter with zero loyalty and never activate.")
            if WALKER_READERS[card.name] not in sources[deck_name]:
                raise AssertionError(
                    f"edhmc/pending.py: {card.name!r} is in {deck_name}, whose "
                    f"engine never activates it (no {WALKER_READERS[card.name]!r} "
                    f"in its source) -- it would have loyalty and do nothing.")
    stale = set(WALKERS_WITHOUT_LOYALTY) - seen
    if stale:
        raise AssertionError(
            f"edhmc/pending.py: WALKERS_WITHOUT_LOYALTY names {sorted(stale)}, "
            f"which no deck list or catalog outside azusa holds. An exemption "
            f"for a card that is not there is a claim that has rotted (§0q).")


check_proposals()


check_measured_are_promotable()
check_shortlist_is_answerable()
check_withdrawn_are_explained()
check_simulated()
check_alt_cost_coverage()
check_loyalty_coverage()


def pending_for(deck_name: str) -> list[Change]:
    return [c for c in CHANGES if c.deck == deck_name]


def build_pending(deck_name: str, apply_pending: bool = True, up_to: int = None):
    """Build a deck with staged changes applied.

    apply_pending=False gives the original spreadsheet list. `up_to=n` applies
    only the first n staged changes, which is how an experiment run earlier in
    the sequence can be reproduced after later changes are staged on top.
    """
    module, catalog = DECKS[deck_name]
    deck, commander = module.build()
    if not apply_pending:
        return deck, commander
    changes = pending_for(deck_name)
    if up_to is not None:
        changes = changes[:up_to]
    if not changes:
        validate(deck, commander)    # a deck with nothing staged is still a list
        return deck, commander
    outs = [c.remove for c in changes]
    ins = []
    for c in changes:
        if c.add not in catalog:
            raise KeyError(f"{c.add} has no card definition in {deck_name}")
        ins.append(catalog[c.add])
    deck = _swap_many(deck, outs, ins)
    validate(deck, commander)
    return deck, commander


BASICS = {"Mountain", "Plains", "Forest", "Swamp", "Island", "Wastes"}


def validate(deck, commander) -> None:
    """Singleton and size checks. Basic lands are the legal exception."""
    assert len(deck) == 99, f"deck is {len(deck)} cards, expected 99"
    seen = {}
    for card in deck:
        if card.name in BASICS:
            continue
        seen[card.name] = seen.get(card.name, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    assert not dupes, f"singleton violation: {dupes}"
    # ONE OBJECT PER COPY (§0z112). `[L("Forest", "G")] * 7` is seven
    # references to ONE Card, and every rule that compares cards by identity
    # then treats two copies as one card: Shigeki put two revealed Forests onto
    # the battlefield, and trostani's hideaway dropped the picked card's
    # duplicate from the game. Basics are where copies live, so basics are
    # where this was -- in all seven lists.
    ids, aliased = set(), set()
    for card in deck:
        if id(card) in ids:
            aliased.add(card.name)
        ids.add(id(card))
    assert not aliased, (
        f"one Card object appears more than once in the list: {sorted(aliased)} "
        f"-- build copies with [L(...) for _ in range(n)], not [L(...)] * n")
    assert commander.name not in seen, (
        f"{commander.name} appears in the 99 as well as the command zone")


def print_proposals(keep=None) -> None:
    """PROPOSED, grouped by deck. Printed last because it is the weakest state:
    verified card text and an argument, with no number attached to any of it."""
    # Only the proposals still AT the proposed state (§0z80): a Proposal whose
    # card has been measured, simulated or staged keeps its record, but is
    # listed where its card is now rather than as "nothing measured".
    keep = keep or (lambda *_: True)
    where = {k: st for st, ks in funnel().items() for k in ks}
    mine = [p for p in PROPOSED if keep(p.deck, p.card)]
    moved = [p for p in mine
             if where[(p.deck, p.card)] not in ("PROPOSED", "PREPARED",
                                                "REJECTED")]
    live = [p for p in mine if not p.rejected and p not in moved]
    dead = [p for p in mine if p.rejected and p not in moved]
    print("\n" + "=" * 78)
    print(f"PROPOSED — oracle text verified, NOTHING MEASURED ({len(live)} live)")
    if moved:
        from collections import Counter
        by = Counter(where[(p.deck, p.card)] for p in moved)
        print(f"  {len(moved)} more proposal record(s) whose card has moved on "
              f"and is listed there: "
              + ", ".join(f"{n} {st}" for st, n in sorted(by.items())) + ".")
    print("=" * 78)
    print("  Next step for each is a tools/candidates.py batch entry, not a")
    print("  staging. A Proposal has no confidence interval; a Candidate does.")
    for deck_name in sorted({p.deck for p in live}):
        rows = [p for p in live if p.deck == deck_name]
        print(f"\n{deck_name.upper()}  ({len(rows)})")
        for pr in rows:
            print(f"  + {pr.card}  {pr.cost}  [{pr.identity or 'C'}]")
            print(f"    {pr.type_line}")
            for line in pr.oracle.split("\n"):
                print(f"    | {line}")
            print(f"    why    {pr.rationale}")
            print(f"    build  {pr.implement}")
            print(f"    text verified {pr.verified} from api.scryfall.com")
    if dead:
        print(f"\nREJECTED ({len(dead)}) — kept so they are not proposed again")
        for pr in dead:
            print(f"  x {pr.card} ({pr.deck}): {pr.rejected}")


def check_staged_are_classified() -> None:
    """Every card in every STAGED list is classified in tools/ablation.py.

    `ablation.check_scripted_coverage` refuses to build a table containing an
    unclassified card, and it used to be the FIRST thing to notice: staging
    -Blasphemous Act +Goldspan Dragon and -Vampiric Rites +Lyra (§0z69) put
    two unclassified cards into `build_pending`, and the table rebuild exited
    on the first try of every attempt until it was stopped. The ledger is
    where a card is staged, so the ledger is where the claim about it has to
    be made. §0q: the check moves to where the mistake is made.
    """
    import tools.ablation as AB
    for deck_name in DECKS:
        deck, _ = build_pending(deck_name)
        AB.check_scripted_coverage(deck_name, deck,
                                   AB.partly_for(deck_name, deck))


def ledger(verbose: bool = True, keep=None) -> None:
    """The whole ledger, with the evidence behind every entry.

    `keep(deck, *card_names)` limits the ENTRIES printed (`--deck`, `--card`);
    the checks and the legality of every deck staged against still run in
    full, because a filter that skipped a check would be a check that skips a
    category (§0z15).
    """
    keep = keep or (lambda *_: True)
    print("=" * 78)
    print("PENDING DECK CHANGES — not yet written to the .xlsx files")
    print("=" * 78)
    print("Every staged and proposed cut, against tools/ablation.py's "
          "classification (§0z31):")
    for line in check_cuts_are_measured():
        print(line)
    check_staged_are_classified()
    print()
    if not CHANGES:
        print("  (none — every decided change is applied on all three legs)")
        for deck_name in sorted(DECKS):
            deck, cmd = build_pending(deck_name)
            print(f"  {deck_name:<10} -> {len(deck) + 1} cards, "
                  f"singleton-legal, commander distinct")
    for deck_name in sorted({c.deck for c in CHANGES}):
        rows = [c for c in pending_for(deck_name)
                if keep(c.deck, c.remove, c.add)]
        if not rows:
            build_pending(deck_name)          # still validated, not printed
            continue
        print(f"\n{deck_name.upper()}  ({len(rows)} change"
              f"{'s' if len(rows) != 1 else ''})")
        for c in rows:
            print(f"  - OUT  {c.remove}")
            print(f"  + IN   {c.add}")
            print(f"    staged {c.staged}")
            if verbose:
                print(f"    why    {c.rationale}")
                print(f"    data   {c.evidence}")
                if c.notes:
                    print(f"    note   {c.notes}")
                # PRINTED FOR STAGED ENTRIES SINCE 2026-09-13, and it was the
                # only field of a Change this function did not show. A
                # `reverified` is written precisely when an engine change has
                # re-run the swap, so it is the field most likely to CONTRADICT
                # the `data` line above it -- and the rendmaw entry proved the
                # cost: its 2026-09-12 recheck said the evidence had collapsed
                # to a third, and `python -m edhmc.pending`, which HANDOFF.md
                # calls the only trustworthy statement of what is staged,
                # printed the original figures and not the retraction.
                if c.reverified:
                    print(f"    recheck {c.reverified}")
        deck, cmd = build_pending(deck_name)
        print(f"    -> {len(deck) + 1} cards, singleton-legal, commander distinct")
    simulated = [r for r in SIMULATED if keep(r.deck, r.remove, r.add)]
    if simulated:
        # BETWEEN THE STAGED AND THE MEASURED, which is where it sits in the
        # funnel (§0z79): real evidence, and no decision yet taken on it.
        print("\n" + "=" * 78)
        print("SIMULATED — a head-to-head against a named cut, NO decision")
        print("=" * 78)
        print("  Decision evidence, unlike MEASURED below: each row is the real "
              "swap, paired on\n  common seeds. Staging one MOVES it to "
              "CHANGES. A row measured before an\n  engine change is only as "
              "current as that engine -- check `measured`.")
        for deck_name in sorted({r.deck for r in simulated}):
            print(f"\n{deck_name.upper()}")
            for r in [r for r in simulated if r.deck == deck_name]:
                print(f"  -{r.remove} +{r.add}   ({r.measured}"
                      + (f", {r.source}" if r.source else "") + ")")
                print(f"     {r.result}")
                if verbose and r.notes:
                    print(f"     note {r.notes}")
    measured = [c for c in MEASURED if keep(c.deck, c.card)]
    if measured:
        # PRINTED UNDER ITS OWN HEADING AND BELOW THE STAGED ONES, because the
        # single most useful thing this section can do is not be mistaken for
        # the section above it. A measured card is a number; a staged card is
        # a decision.
        print("\n" + "=" * 78)
        print("MEASURED — a number exists, NOTHING HAS BEEN DECIDED")
        print("=" * 78)
        print("  Not staged. No cut named. Promoting one of these needs a "
              "head-to-head\n  against a specific cut: everything here shares "
              "one baseline, so these\n  rows cannot be ranked against each "
              "other or against anything else (§0e).")
        for deck_name in sorted({c.deck for c in measured}):
            rows = [c for c in measured if c.deck == deck_name]
            # DERIVED: this used to print a literal "0 staged", which went
            # false the day the first measured card was staged.
            staged_adds = {ch.add for ch in CHANGES if ch.deck == deck_name}
            n_staged = sum(c.card in staged_adds for c in rows)
            print(f"\n{deck_name.upper()}  ({len(rows)} measured, "
                  f"{n_staged} staged from this batch)")
            # SHORTLISTED ROWS FIRST, and marked, because the one thing a
            # reader wants from this section is which of thirteen numbers
            # somebody has actually looked at. Still Candidates: the marker
            # says a head-to-head is proposed, not that anything is staged.
            rows.sort(key=lambda c: (not c.shortlist, c.card))
            for c in rows:
                staged = c.card in staged_adds
                print(f"  {'>>' if c.shortlist else ('=>' if staged else ' ?')}"
                      f"  {c.card}"
                      + ("   [SHORTLISTED — head-to-head proposed, NOT staged]"
                         if c.shortlist else
                         "   [STAGED — see the change above]" if staged
                         else ""))
                print(f"     win    {c.win_rate}   signal {c.signal}")
                print(f"     measured {c.measured}")
                if c.shortlist:
                    print(f"     cut?   proposed head-to-head: "
                          f"-{c.proposed_cut} +{c.card}")
                    print(f"     why it {c.shortlist}")
                if verbose:
                    print(f"     why    {c.rationale}")
                    print(f"     data   {c.evidence}")
                    if c.limits:
                        print(f"     limits {c.limits}")
                    if c.verdict:
                        print(f"     read   {c.verdict}")

    withdrawn = [c for c in WITHDRAWN if keep(c.deck, c.remove, c.add)]
    if withdrawn:
        # PRINTED, not silently dropped. The whole reason this list exists is
        # that an unstaged change leaves no trace anywhere else: it is out of
        # CHANGES, so `build_pending` ignores it, so no run and no table can
        # ever mention it again. A reader who does not see it here will
        # re-measure the card from scratch, which is the cost this heading
        # exists to avoid.
        print("\n" + "=" * 78)
        print("WITHDRAWN — was staged, has been UNSTAGED, is in NO baseline")
        print("=" * 78)
        print("  Not refuted unless the entry says so. `build_pending` does "
              "not apply these,\n  so nothing below is in any deck, any run "
              "or any table. Each entry's\n  `why not` says what re-staging "
              "it would have to answer.")
        for c in withdrawn:
            print(f"\n{c.deck.upper()}")
            print(f"  - OUT  {c.remove}")
            print(f"  + IN   {c.add}")
            print(f"    staged {c.staged}, then unstaged")
            if verbose:
                print(f"    why    {c.rationale}")
                print(f"    data   {c.evidence}")
                if c.notes:
                    print(f"    note   {c.notes}")
                if c.reverified:
                    print(f"    recheck {c.reverified}")
            print(f"    why not {c.withdrawn}")

    committed = [c for c in COMMITTED if keep(c.deck, c.remove, c.add)]
    if committed:
        # Azusa has NO .xlsx, so for that deck "committed" is two legs -- the
        # module and this ledger -- and the module alone is the system of
        # record. Said in the output rather than only in CLAUDE.md, because
        # this print is what someone checks before believing a change is done.
        print("\nCOMMITTED (in the deck module AND the .xlsx -- except azusa, "
              "which has\n           no .xlsx: its module alone is the system "
              "of record)")
        for c in committed:
            print(f"  {c.deck}: -{c.remove} +{c.add} ({c.staged})")
            if verbose and c.reverified:
                print(f"    recheck {c.reverified}")


def _clip(text: str, n: int) -> str:
    """One line of at most n characters, keeping any leading indent."""
    text = text or ""
    indent = text[: len(text) - len(text.lstrip(" "))]
    line = indent + " ".join(text.split())
    return line if len(line) <= n else line[: n - 3] + "..."


def _number(text: str) -> str:
    """A result without its "REAL SWAP -X +Y, N=15,000 paired:" preamble,
    which repeats the line above it and pushes the T20 figure off the end."""
    import re
    return re.sub(r"^\s*REAL SWAP[^:]*:\s*", "", text or "")


def _checks_and_legality() -> None:
    """Every check `summary()` and `check_view()` share, and their output:
    the cut classification of every staged and proposed swap (§0z31), the
    import-time classification check, and `build_pending` -- which runs
    `validate()` -- on EVERY deck, printed as one legality line each."""
    print("Every staged and proposed cut, against tools/ablation.py's "
          "classification (§0z31):")
    for line in check_cuts_are_measured():
        print(_clip(line, 150))
    check_staged_are_classified()

    print("\nLEGALITY, every deck with its staged changes applied")
    for deck_name in sorted(DECKS):
        deck, _cmd = build_pending(deck_name)
        n = len(pending_for(deck_name))
        print(f"  {deck_name:<10} -> {len(deck) + 1} cards, singleton-legal, "
              f"commander distinct   ({n} staged)")


def _live_proposed() -> list:
    where = {k: st for st, ks in funnel().items() for k in ks}
    return [p for p in PROPOSED if not p.rejected
            and where[(p.deck, p.card)] in ("PROPOSED", "PREPARED")]


def check_view() -> None:
    """Every check, every legality line and every staged cut -- and the rest
    of the ledger as COUNTS.

    THE DEFAULT SINCE 2026-10-11. `summary()` was the default for a day and
    printed 19 KB, about five thousand tokens, three-quarters of it the
    MEASURED and SIMULATED rows; CLAUDE.md sends every commit here for the
    seven legality lines, and the session transcripts showed it run hundreds
    of times in one session. This view runs exactly the checks `summary()`
    runs (`_checks_and_legality`) and names every staged swap in the
    classification block; what it drops is the per-entry listing of the
    other states, one flag away (`--summary`).
    """
    print("LEDGER CHECK -- checks, legality, staged cuts. One line per entry:")
    print("  python -m edhmc.pending --summary   (evidence: --card NAME, "
          "--deck DECK, --full)")
    print()
    _checks_and_legality()
    print(f"\nSTAGED {len(CHANGES)} · SIMULATED {len(SIMULATED)} · "
          f"MEASURED {len(MEASURED)} · WITHDRAWN {len(WITHDRAWN)} · "
          f"COMMITTED {len(COMMITTED)} · PROPOSED, still unmeasured "
          f"{len(_live_proposed())}")


def summary() -> None:
    """One line per entry, and every check and legality line in full.

    THE DEFAULT FROM 2026-10-10 TO 2026-10-11, now `--summary`
    (`check_view()` replaced it). The full ledger printed 165 KB, half of it
    the evidence behind seventy-odd MEASURED rows, and CLAUDE.md sends every
    session here to check legality -- so every session paid about forty
    thousand tokens to read three lines. The evidence is one flag away
    (`--full`, `--deck`, `--card`); what this view drops is the prose, never
    a check: the import-time checks, the cut classification and
    `validate()` on EVERY deck run exactly as in `ledger()`. It is stricter
    than `ledger()` in one place: that function prints legality only for
    decks with something staged, and this one prints all of them.
    """
    print("LEDGER SUMMARY -- one line per entry. The evidence behind each:")
    print("  python -m edhmc.pending --card NAME   (or --deck DECK, or --full)")
    print()
    _checks_and_legality()

    print(f"\nSTAGED ({len(CHANGES)}) -- in build_pending, not yet on all legs")
    for c in sorted(CHANGES, key=lambda c: c.deck):
        print(f"  {c.deck:<10} -{c.remove} +{c.add}   staged {c.staged}"
              + ("; rechecked" if c.reverified else ""))

    print(f"\nSIMULATED ({len(SIMULATED)}) -- a head-to-head, NO decision")
    for r in sorted(SIMULATED, key=lambda r: r.deck):
        print(f"  {r.deck:<10} -{r.remove} +{r.add}")
        print(f"             {_clip(_number(r.result), 140)}")

    staged_adds = {(c.deck, c.add) for c in CHANGES}
    print(f"\nMEASURED ({len(MEASURED)}) -- a number, NOTHING decided "
          f"(>> shortlisted, => staged)")
    for c in sorted(MEASURED, key=lambda c: (c.deck, not c.shortlist, c.card)):
        mark = (">>" if c.shortlist else
                "=>" if (c.deck, c.card) in staged_adds else "  ")
        print(f"  {mark} {c.deck:<10} {c.card:<34} "
              f"{_clip(_number(c.win_rate), 70)}  [{c.signal}]")

    if WITHDRAWN:
        print(f"\nWITHDRAWN ({len(WITHDRAWN)}) -- unstaged, in no baseline")
        for c in WITHDRAWN:
            print(f"  {c.deck:<10} -{c.remove} +{c.add}   "
                  f"{_clip(c.withdrawn, 70)}")

    by_deck: dict[str, int] = {}
    for c in COMMITTED:
        by_deck[c.deck] = by_deck.get(c.deck, 0) + 1
    print(f"\nCOMMITTED ({len(COMMITTED)}): "
          + ", ".join(f"{d} {n}" for d, n in sorted(by_deck.items())))

    live = _live_proposed()
    print(f"PROPOSED, still unmeasured ({len(live)}): "
          + (", ".join(f"{p.card} ({p.deck})" for p in live) or "none"))


def _filter(args: list[str]):
    """`--deck D` and `--card NAME` (case-insensitive substring), ANDed."""
    deck = args[args.index("--deck") + 1].lower() if "--deck" in args else ""
    card = args[args.index("--card") + 1].lower() if "--card" in args else ""
    if deck and deck not in DECKS:
        raise SystemExit(f"no deck {deck!r}; decks are {', '.join(sorted(DECKS))}")

    def keep(d: str, *names: str) -> bool:
        return ((not deck or d == deck)
                and (not card or any(card in n.lower() for n in names)))
    return keep


def main(args: list[str]) -> None:
    """The command line. Names are looked up at call time, so a test can
    swap `check_view` or `summary` for a mutation."""
    if "--full" in args or "--deck" in args or "--card" in args:
        keep = _filter(args)
        ledger(keep=keep)
        print_proposals(keep=keep)
    elif "--summary" in args:
        summary()
    else:
        check_view()


if __name__ == "__main__":
    main(sys.argv[1:])
