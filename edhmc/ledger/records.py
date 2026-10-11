"""The ledger's record types: one dataclass per kind of entry.

Moved out of `edhmc/pending.py` on 2026-10-11 with the data, so that the
per-deck modules in this package can build records without importing
`pending.py` (which imports them). `pending.py` re-exports all four.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Change:
    deck: str
    remove: str
    add: str
    staged: str                 # date staged
    rationale: str
    evidence: str = ""
    notes: str = ""
    reverified: str = ""        # re-measured after an engine change
    withdrawn: str = ""         # set only on WITHDRAWN: when, and why
    # Set ONLY when the cut is MODEL-BLIND or PARTLY MODELLED in its deck:
    # why the swap is staged anyway, said out loud. `check_cuts_are_measured`
    # refuses a staged blind cut without it (§0z31's follow-up), because a
    # blind card's row is not evidence and the head-to-head that stages the
    # swap is then a CEILING -- the cut's real value is whatever the engine
    # does not model.
    cut_unmeasured: str = ""

    @property
    def simulated(self) -> "Simulated":
        """This Change's evidence half (§0z79): a staged swap IS a
        head-to-head plus a decision, and the head-to-head is its
        `evidence`. Derived, so it cannot drift from the entry."""
        return Simulated(deck=self.deck, remove=self.remove, add=self.add,
                         measured=self.staged, result=self.evidence)


@dataclass
class Candidate:
    """A card that has been MEASURED and NOT decided on.

    HANDOFF.md has always described three states -- measured, staged,
    committed -- and this module only had structures for the last two, so the
    first one lived in comments and in `results/` files that nothing reads.
    That is the state most likely to be lost: a number with nobody's decision
    attached to it looks exactly like a number somebody forgot to act on.

    A Candidate is deliberately WEAKER than a Change. It names no cut, because
    choosing one is the decision this state has not taken; `ablation.py` scores
    the cut side and `candidates.py` scores the add side, and pairing them is a
    head-to-head run, not an inference (§0e). Promoting one means writing a
    Change with a `remove`, and that needs its own evidence.
    """
    deck: str
    card: str
    measured: str               # date measured
    win_rate: str               # the number, WITH its bar and its horizon
    signal: str                 # both / dmg / win / --
    rationale: str
    evidence: str = ""
    limits: str = ""            # floors, ceilings and modelling caveats
    verdict: str = ""           # what the number supports, and what it does not

    # --- SHORTLISTED: a REVIEW FLAG, and deliberately not a fourth state ----
    # "These three are worth a head-to-head" is a different claim from "this is
    # going in", and the whole point of the measured/staged split is that the
    # second one needs evidence the first does not have. A shortlisted
    # Candidate is still a Candidate: `build_pending` does not apply it, no
    # table contains it, and no deck list moves. What the flag buys is that the
    # shortlist stops living in a conversation -- the state this class was
    # written to rescue (see the docstring above).
    #
    # `proposed_cut` NAMES THE CUT THE HEAD-TO-HEAD SHOULD RUN, which a plain
    # Candidate deliberately does not. It is a PROPOSAL and the number attached
    # to this row is NOT evidence for it: an ablation row and a candidate row
    # share a baseline and therefore cannot be subtracted from one another
    # (§0e). `check_shortlist_is_answerable()` enforces what can be enforced --
    # that the named cut is really in the deck.
    shortlist: str = ""         # why it is shortlisted; empty = it is not
    proposed_cut: str = ""      # the cut a head-to-head should test it against
    cut_unmeasured: str = ""    # as on Change: why a blind/partly cut is proposed


@dataclass
class Simulated:
    """A HEAD-TO-HEAD: the real swap, against a named cut, paired on common
    seeds -- and NO decision (docs/LEDGER_STATES.md, §0z79).

    `Change` used to carry two claims at once: "we ran the swap" (evidence)
    and "we are putting it in" (decision). The owner confirmed the split on
    2026-09-22. A head-to-head that did not stage had nowhere to live except
    a Candidate's `win_rate` string, which is a MEASURED record and says so
    -- so the evidence for the twelve decisions §0z74 left with the owner was
    filed under the one state this ledger says is never decision evidence.

    SIMULATED holds only the head-to-heads with no STAGED partner. A staged,
    committed or withdrawn Change IS a head-to-head with a decision attached;
    its SIMULATED half is derived (`Change.simulated`), not written twice.
    Staging one of these means moving it to CHANGES as a Change -- and
    `check_simulated` fails while both lists hold it.

    `result` is the number a decision would rest on: both horizons, with
    bars, verbatim from the run. `source` is the results file.
    """
    deck: str
    remove: str
    add: str
    measured: str               # date of the run
    result: str                 # T10 and T20, with bars
    source: str = ""            # results/ file the numbers came from
    notes: str = ""


@dataclass
class Proposal:
    """A card PROPOSED for testing: oracle text verified, nothing measured yet.

    THE FIFTH STATE, added 2026-09-16, and it exists for the same reason
    WITHDRAWN does -- the alternative was a chat message, and a chat message is
    the state most easily lost. A Proposal is WEAKER than a Candidate: a
    Candidate has a number and a confidence interval, a Proposal has only
    verified card text and an argument.

    WHY IT CARRIES THE ORACLE TEXT. `CLAUDE.md` forbids guessing oracle text,
    and this project's largest corrections all came from a card whose text the
    engine had wrong. A proposal made from memory is exactly that failure
    staged one step earlier, so the text here is copied from
    `api.scryfall.com` on `verified`, and `check_proposals` refuses an entry
    without it. If you cannot reach Scryfall, you cannot add a Proposal -- that
    is deliberate.

    `implement` is the honest estimate of ENGINE work, which is the real cost.
    The measurement is minutes; making the card behave like its text is not.
    """
    deck: str
    card: str
    cost: str                   # verified mana cost
    identity: str               # verified colour identity, "" for colourless
    type_line: str
    oracle: str                 # VERBATIM from Scryfall
    verified: str               # date the text above was fetched
    rationale: str              # why THIS deck, tied to a measured weakness
    implement: str              # engine work needed, and what it would move
    rejected: str = ""          # set if the proposal is dead, and why
    # TRIAGE (queued item 23, docs/TRIAGE.md, docs/LEDGER_STATES.md): a FLAG
    # on the Proposal, not a state. "" = not triaged (every entry before the
    # screen existed). LIVE = survived, escalate to a candidate row. BLIND =
    # the engine cannot see enough of the text -- `triage_clauses` MUST quote
    # the clauses, verbatim from `oracle`, so the verdict can be re-run when a
    # gap closes (§0z13: an infeasibility note is a claim with a date on it).
    # DEFERRED = needs machinery that does not exist -- `triage_note` MUST
    # name it. `check_triage` enforces both. REJECTED stays on `rejected`.
    # `python -m tools.triage --proposals` is the screen that proposes these.
    triage: str = ""
    triage_clauses: tuple = ()
    triage_note: str = ""
    # PREPARED (docs/LEDGER_STATES.md, §0z79): the engine work is done and
    # pinned. "" = not prepared. Otherwise it NAMES THE TEST that pins the
    # card -- a path under tests/ -- and `check_prepared` refuses a path that
    # is not on disk, because "implemented" with no test is §0z28's shape (a
    # test that is not run does not exist; one that is not written, less so).
    # A flag rather than a list, like `triage`: the card is still a Proposal
    # until it has a number, and then it is a Candidate.
    prepared: str = ""
