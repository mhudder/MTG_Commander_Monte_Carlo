"""
edhmc.voting — the council mechanic, and an honest model of how a pod votes.

Nothing else in this project has to model an OPPONENT'S CHOICE. The opponent
model everywhere else is a clock, a blocker count and a removal rate: it never
decides anything. A vote does, and the answer changes the value of a third of
the Tivit deck, so the assumption has to be stated rather than buried.

WHAT THE MECHANIC ACTUALLY IS. Four keywords, and they resolve differently
enough that a single "who won the vote" helper would be wrong for most of them:

  will of the council   ONE outcome. The choice with the most votes happens;
                        ties go to the second-listed choice on most cards.
                        This is the one where being outvoted 3-1 hurts.
  council's dilemma     PER-VOTE. Every vote contributes its own effect, so
                        there is no winner and no tie. Tivit is this.
  tempting offer        Not a vote at all: you get the effect, then each
                        opponent MAY take a copy, and for each who does you
                        get the effect again. Model the acceptance rate.
  secret council        A simultaneous vote, so vote-control effects that read
                        "you choose how each player votes" still apply but
                        information does not.

WHY TIVIT DOES NOT CARE HOW THE POD VOTES. "For each evidence vote,
investigate. For each bribery vote, create a Treasure token." Both halves make
an artifact. An adversarial pod choosing every opponent vote cannot reduce the
COUNT — only the mix. That is a fact about the card, and it is why the
pessimistic default below costs the commander nothing while costing the
will-of-the-council cards a great deal. If a model makes Tivit look bad, the
model is wrong.

HOW OPPONENTS VOTE HERE, and why. `cfg["opp_vote_policy"]`:

  "adversarial"  (DEFAULT) every opponent votes for whichever choice is worse
                 for you, and they agree with each other. This is the
                 PESSIMISTIC bound, not a claim about real pods.
  "selfish"      each opponent votes for what is best for that opponent,
                 which for most symmetric cards is not the same as what is
                 worst for you. `opp_vote_selfish_agree` is how often that
                 coincides with the adversarial choice.
  "random"       an independent coin per opponent.

THE DEFAULT IS A JUDGEMENT CALL AND IS DELIBERATELY THE UNFAVOURABLE ONE.
Three opponents voting as a bloc is close to a worst case: real tables are not
coordinated, players vote for what benefits them, and a table that has not
identified you as the threat often votes with you. Any card whose evaluation
swings on this knob must be reported with the knob said out loud -- the same
rule `Card.indestructible` and `destroy_share` already carry.

VOTE COUNTS. You get one vote, plus one for each source of an extra:

    Tivit, Seller of Secrets   "While voting, you may vote an additional time"
    Ballot Broker              "While voting, you may vote an additional time"
    Brago's Representative     "While voting, you get an additional vote"

All three are cumulative, and all three are on the battlefield or they do
nothing. With Tivit plus one other, you have three votes against three
opponents and TIE every will-of-the-council card -- which most of them resolve
in the second choice's favour, so a tie is not a win. With Tivit plus both,
you have four and win outright. That threshold is the reason Ballot Broker and
Brago's Representative are in the deck at all, and it is exactly the kind of
thing leave-one-out ablation gets wrong: cut either one alone and the other
still ties, so both look weak. ABLATE THEM AS A GROUP.
"""

from __future__ import annotations

from edhmc import opponents as OPP

# Cards that grant you an extra vote while on the battlefield.
EXTRA_VOTE = ("Tivit, Seller of Secrets", "Ballot Broker",
              "Brago's Representative")


def my_votes(g) -> int:
    """Your vote count: one, plus one per extra-vote permanent on the board."""
    n = 1
    for name in EXTRA_VOTE:
        n += g.count(name)
    return n


def opp_votes(g) -> int:
    return len(OPP.living(g))


def vote_control(g) -> bool:
    """Illusion of Choice: "You choose how each player votes this turn."

    Set for the turn it resolves. While it is up, every vote is yours.
    """
    return getattr(g, "illusion_active", False)


def _opp_picks_against(g) -> bool:
    """Does a given opponent vote for the choice that is worse for you?"""
    policy = g.cfg.get("opp_vote_policy", "adversarial")
    if policy == "adversarial":
        return True
    if policy == "random":
        return g.rng.random() < 0.5
    # "selfish": an opponent optimises for themselves, which lands on the
    # anti-you choice only some of the time.
    return g.rng.random() < g.cfg.get("opp_vote_selfish_agree", 0.6)


def dilemma(g, label="tivit"):
    """COUNCIL'S DILEMMA: every vote has its own effect. Returns (mine, theirs).

    `mine` is the number of votes you cast, `theirs` the number cast against.
    Neither is a winner -- the caller applies the per-vote effect to each.
    Under vote control every vote is yours.
    """
    mine, theirs = my_votes(g), opp_votes(g)
    if vote_control(g):
        mine, theirs = mine + theirs, 0
    else:
        against = sum(1 for _ in range(theirs) if _opp_picks_against(g))
        mine, theirs = mine + (theirs - against), against
    g.m["votes_cast"] += mine + theirs
    g.m["dilemmas"] += 1
    _vote_payoffs(g, theirs)
    return mine, theirs


def council(g, tie_goes_to_you=False) -> bool:
    """WILL OF THE COUNCIL: one outcome. Returns True if YOUR choice happens.

    Most of these cards list your preferred mode second and resolve ties in
    the second mode's favour, but not all -- pass `tie_goes_to_you` per card
    rather than assuming.
    """
    mine, theirs = my_votes(g), opp_votes(g)
    if vote_control(g):
        against = 0
    else:
        against = sum(1 for _ in range(theirs) if _opp_picks_against(g))
    mine += theirs - against
    g.m["votes_cast"] += mine + against
    g.m["councils"] += 1
    won = mine > against or (mine == against and tie_goes_to_you)
    g.m["councils_won"] += int(won)
    _vote_payoffs(g, against)
    return won


def tempting_offer(g) -> int:
    """TEMPTING OFFER: you get it once, plus once more per opponent who takes it.

    Not a vote, so vote control does nothing here and Grudge Keeper does not
    trigger. `tempting_offer_rate` is the share of opponents who accept; the
    default 0.5 is a judgement call, and a generous one -- accepting usually
    helps you more than them, which is the whole design of the mechanic.
    """
    rate = g.cfg.get("tempting_offer_rate", 0.5)
    takers = sum(1 for _ in OPP.living(g) if g.rng.random() < rate)
    g.m["offers_taken"] += takers
    return 1 + takers


def _vote_payoffs(g, votes_against: int):
    """Cards that read the vote itself rather than its outcome."""
    if votes_against and g.has("Grudge Keeper"):
        # "Each opponent who voted for a choice you didn't vote for loses 2."
        g.deal_pod_damage(2.0 * votes_against, each=False)
        g.m["grudge_damage"] += 2.0 * votes_against
    if g.has("Model of Unity"):
        # "You and each opponent who voted for a choice you voted for may
        # scry 2." Scry is modelled as a small draw-quality nudge, not a card.
        g.m["unity_scrys"] += 1
