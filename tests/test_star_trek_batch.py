#!/usr/bin/env python3
"""Pin the five cards of the owner's Reality Fracture / Star Trek review,
2026-10-23, one per deck.

    python -m tests.test_star_trek_batch
    python -m tests.test_star_trek_batch --mutate   # 9 mutations, exact sets

Oracle text from api.scryfall.com, 2026-10-23, verbatim on each Proposal.

  karlov      Dr. Beverly Crusher      lifegain triggers of permanents fire
                                       an additional time
  shilgengar  Avacyn, Angel of Horror  a nontoken creature that dies returns
                                       at the next end step; the feed policy
  azusa       Captain Pike             lands from the top; */* = differently
                                       named lands
  tivit       Mr. Spock                every draw is two
  lorehold    Join the Collective      destroy all creatures; X Borgs for the
                                       nonartifact creatures destroyed

CASES
  A  Crusher: one lifegain event puts FOUR counters on Karlov, two on Crusher
  B  no Crusher: two on Karlov (the control)
  C  Crusher + Archangel of Thune: every creature gets two counters an event
  D  Crusher doubles TRIGGERS, not the amount: 5 life is 5, one event
  F  Avacyn: an Angel fed to Shilgengar makes its toughness in Blood and is
     back on the battlefield after your end step
  G  a TOKEN that dies is not returned
  H  a queued card that left the graveyard first is not returned (§0z19)
  I  Avacyn's own death returns her (she sees it, CR 603.10a)
  J  a death on an opponent's turn returns at THAT end step (pod_end_step)
  K  the feed policy: every nontoken non-commander creature is sacrificed,
     Blood is made, and all are back after the end step
  L  Pike grants top-of-library land plays
  M  without Pike (nor any other grant) the top is not playable
  N  Pike is a */* of DIFFERENTLY NAMED lands: three Forests and a Mountain
     make a 2/2
  O  Spock: draw(1) draws two
  P  no Spock: draw(1) draws one (the control)
  Q  Spock with one card left: draw(1) decks you (704.5b)
  R  Spock: a Clue is NOT cracked into the last `decking_reserve` cards; the
     same library without Spock cracks it, as tivit always has
  S  Join the Collective, the pod's six creatures die: six Borgs
  T  yours: two nonartifact creatures and one artifact creature die: two
     Borgs
  U  THE WIPE GATE prices the Borgs: five 2/2s against the pod's six
     creatures -- Farewell's gate stays shut, Join the Collective's opens
     (`opponents.wipe_refund`)

MUTATIONS, WRITTEN BEFORE THE FIRST RUN, exact sets:
  crusher_text off                       -> A, C
  Avacyn's returns never happen          -> F, I, J, K
  avacyn_feed off                        -> K
  Pike's */* reads nothing               -> N
  Pike grants no top access              -> L
  spock_text off                         -> O, Q, R
  Spock's optional-draw guard removed    -> R
  Borgs count artifact creatures too     -> T
  wipe_gate_refund off                   -> U

U WAS ADDED AFTER THE FIRST SMOKE RUN, with its mutation written before it
ran: the smoke cast the card in 3.9% of games because the gate priced it as
Farewell.

UNMUTATED: B, D, G, H, M, P are controls -- what must not move.
"""
import sys

import edhmc.engine as EN
import edhmc.karlov as K
import edhmc.shilgengar as SH
import edhmc.azusa as AZ
import edhmc.tivit as TV
import edhmc.lorehold as LH
from edhmc import opponents as OPP
from edhmc.engine import Card, Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc.decks import karlov_v2 as KM, shilgengar_v1 as SM
from edhmc.decks import azusa_v1 as AM, tivit_v1 as TM, lorehold_v17 as LM

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
EXTRA = {}                 # a mutation's cfg, read by every game below


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def cfg():
    return dict(DEFAULT_CFG, turns=20, **EXTRA)


def card(mod_deck, name):
    return next(c for c in mod_deck if c.name == name)


def body(name, types=("Creature",), p=2, t=2):
    return Card(name=name, types=frozenset(types), power=p, toughness=t)


def land(name, colour):
    return Card(name=name, types=frozenset({"Land"}), is_land=True,
                produces=frozenset({colour}))


def perm(c, **kw):
    return Permanent(card=c, sick=False, **kw)


# ---------------------------------------------------------------- karlov --
KDECK, KCMD = KM.build()


def kgame(*cards):
    g = K.KarlovGame(list(KDECK), KCMD, cfg(), 1)
    g.board = EN.Board()
    for c in cards:
        g.board.append(perm(c))
    g.commander_cast = True
    return g


# ------------------------------------------------------------ shilgengar --
SDECK, SCMD = SM.build()
AVACYN = SM.AVACYN_ANGEL_OF_HORROR


def sgame(*cards):
    g = SH.ShilgengarGame(list(SDECK), SCMD, cfg(), 1)
    g.board = EN.Board()
    for c in cards:
        g.board.append(perm(c))
    return g


def on_board(g, name):
    return any(p.card.name == name for p in g.board)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []

    # ---- A-D: Dr. Beverly Crusher ----------------------------------------
    g = kgame(KM.DR_BEVERLY_CRUSHER)
    K.gain_life(g, 1)
    crusher = next(p for p in g.board if p.card is KM.DR_BEVERLY_CRUSHER)
    check("A Crusher: four counters on Karlov, two on Crusher, one event",
          (g.karlov_counters, crusher.counters, g.m["lifegain_triggers"]),
          (4, 2, 1))
    g = kgame()
    K.gain_life(g, 1)
    check("B no Crusher: two counters on Karlov", g.karlov_counters, 2)
    g = kgame(KM.DR_BEVERLY_CRUSHER, card(KDECK, "Archangel of Thune"))
    K.gain_life(g, 1)
    thune = next(p for p in g.board if p.card.name == "Archangel of Thune")
    check("C Crusher + Thune: two counters on each creature an event",
          thune.counters, 2)
    g = kgame(KM.DR_BEVERLY_CRUSHER)
    life = g.your_life
    K.gain_life(g, 5)
    check("D the amount is not doubled: 5 life, one event",
          (g.your_life - life, g.m["lifegain_triggers"]), (5, 1))

    # ---- F-K: Avacyn, Angel of Horror ------------------------------------
    # Named, not searched: the first Angel in the list is Avacyn, Angel of
    # Hope, and the first non-Angel Elesh Norn, whose +2/+2 to others moved
    # the Blood count on the first run (12, not 17) -- the test's choice of
    # bodies, not the engine. Neither of these two reads the other.
    angel = card(SDECK, "Angel of Despair")
    g = sgame(AVACYN, angel)
    g.commander_cast = True
    victim = next(p for p in g.board if p.card is angel)
    blood = g.blood
    g.sacrifice(victim, to_shilgengar=True)
    g.end_step()
    check("F fed Angel: toughness in Blood, back after the end step",
          (g.blood - blood, on_board(g, angel.name),
           any(c is angel for c in g.graveyard)),
          (angel.toughness, True, False))

    g = sgame(AVACYN)
    tok = Permanent(card=body("Spirit token", p=1, t=1), sick=False,
                    is_token=True)
    g.board.append(tok)
    g.sacrifice(tok)
    check("G a token is not queued", len(g.avacyn_queue), 0)

    g = sgame(AVACYN, angel)
    OPP.destroy(g, next(p for p in g.board if p.card is angel))
    EN.remove_card(g.graveyard, angel)        # something else took it
    g.end_step()
    check("H a card gone from the graveyard is not returned",
          (on_board(g, angel.name), g.m["avacyn_returns"]), (False, 0))

    g = sgame(AVACYN)
    OPP.destroy(g, next(p for p in g.board if p.card is AVACYN))
    g.end_step()
    check("I Avacyn's own death returns her", on_board(g, AVACYN.name), True)

    g = sgame(AVACYN, angel)
    OPP.destroy(g, next(p for p in g.board if p.card is angel))
    g.pod_end_step(0)
    check("J a death on an opponent's turn returns at that end step",
          on_board(g, angel.name), True)

    other = card(SDECK, "Blood Artist")
    g = sgame(AVACYN, angel, other)
    g.commander_cast = True
    blood = g.blood
    g.avacyn_feed()
    fed = g.m["avacyn_fed"]
    g.end_step()
    check("K the feed: three fed, Blood made, all three back",
          (fed, g.blood - blood,
           all(on_board(g, n) for n in (AVACYN.name, angel.name, other.name))),
          (3, 8 + angel.toughness + 1, True))

    # ---- L-N: Captain Pike -----------------------------------------------
    adeck, acmd = AM.build()
    g = AZ.AzusaGame(list(adeck), acmd, cfg(), 1)
    g.board = EN.Board()
    g.board.append(perm(AM.CAPTAIN_PIKE))
    top = land("Forest", "G")
    g.library.append(top)
    check("L Pike: the top land is playable",
          any(c is top and z == "library" for c, z in g.playable_lands()),
          True)
    g.board = EN.Board()
    check("M no grant: the top is not playable", g.top_access(), False)
    g.board = EN.Board()
    pike = perm(AM.CAPTAIN_PIKE)
    g.board.append(pike)
    for c in (land("Forest", "G"), land("Forest", "G"), land("Forest", "G"),
              land("Mountain", "R")):
        g.board.append(perm(c))
    check("N Pike is a 2/2 on three Forests and a Mountain",
          (g.power_of(pike), g.toughness_of(pike)), (2, 2))

    # ---- O-R: Mr. Spock ---------------------------------------------------
    tdeck, tcmd = TM.build()

    def tgame(spock):
        g = TV.TivitGame(list(tdeck), tcmd, cfg(), 1)
        g.board = EN.Board()
        if spock:
            g.board.append(perm(TM.MR_SPOCK))
        return g

    g = tgame(True)
    hand = len(g.hand)
    g.draw(1)
    check("O Spock: one draw is two cards", len(g.hand) - hand, 2)
    g = tgame(False)
    hand = len(g.hand)
    g.draw(1)
    check("P no Spock: one draw is one card", len(g.hand) - hand, 1)
    g = tgame(True)
    g.library = g.library[-1:]
    g.draw(1)
    check("Q Spock with one card left decks you", g.result, "loss")
    cracked = []
    for spock in (True, False):
        g = tgame(spock)
        g.library = g.library[-6:]             # 6 - 2 < decking_reserve 5
        g.tokens["Clue"] = 1
        for c in (land("Island", "U"), land("Island", "U")):
            g.board.append(perm(c))
        cracked.append(TV.crack_clues(g, 1))
    check("R a Clue is held with Spock, cracked without", cracked, [0, 1])

    # ---- S-T: Join the Collective ----------------------------------------
    ldeck, lcmd = LM.build()
    jtc = LM.JOIN_THE_COLLECTIVE

    def borgs(g):
        return sum(1 for p in g.board if p.card.name == "Borg token")

    g = LH.LoreholdGame(list(ldeck), lcmd, cfg(), 1)
    g.board = EN.Board()
    for o in OPP.living(g):
        o.creatures = 2.0
    LH.apply_spell_effects(g, jtc)
    check("S the pod's six creatures die: six Borgs", borgs(g), 6)
    g = LH.LoreholdGame(list(ldeck), lcmd, cfg(), 1)
    g.board = EN.Board()
    for o in OPP.living(g):
        o.creatures = 0.0
    for c in (body("Bear A"), body("Bear B"),
              body("Thopter", types=("Artifact", "Creature"), p=1, t=1)):
        g.board.append(perm(c))
    LH.apply_spell_effects(g, jtc)
    check("T yours: two nonartifact and one artifact creature die: two Borgs",
          (borgs(g), sum(1 for p in g.board if p.card.name != "Borg token")),
          (2, 0))
    g = LH.LoreholdGame(list(ldeck), lcmd, cfg(), 1)
    g.board = EN.Board()
    for i in range(5):
        g.board.append(perm(body(f"Bear {i}")))
    for o in OPP.living(g):
        o.creatures = 2.0
    farewell = card(ldeck, "Farewell")
    check("U the gate: shut for Farewell, open for Join the Collective",
          (OPP.should_cast_own_wipe(g, farewell),
           OPP.should_cast_own_wipe(g, jtc)), (False, True))
    return set(FAIL)


def main() -> int:
    global EXTRA
    if not MUTATE:
        print("Reality Fracture / Star Trek review -- one card per deck\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {
        "returns": SH.ShilgengarGame.avacyn_returns,
        "named": AZ.DYNAMIC_PT_NAMED_LANDS,
        "top": AZ.AzusaGame.top_access,
        "safe": TV.spock_draw_safe,
        "before": LH.collective_before,
    }

    def all_creatures(g):
        mine, pod = real["before"](g)
        return ([p for p in g.board if OPP.is_creature_now(g, p)], pod)

    muts = {
        "crusher_text off": ({"A", "C"}, {"crusher_text": False}, None),
        "Avacyn's returns never happen": (
            {"F", "I", "J", "K"}, {},
            lambda: setattr(SH.ShilgengarGame, "avacyn_returns",
                            lambda self: None)),
        "avacyn_feed off": ({"K"}, {"avacyn_feed": False}, None),
        "Pike's */* reads nothing": (
            {"N"}, {}, lambda: setattr(AZ, "DYNAMIC_PT_NAMED_LANDS",
                                       frozenset())),
        "Pike grants no top access": (
            {"L"}, {}, lambda: setattr(AZ.AzusaGame, "top_access",
                                       lambda self: False)),
        "spock_text off": ({"O", "Q", "R"}, {"spock_text": False}, None),
        "Spock's optional-draw guard removed": (
            {"R"}, {}, lambda: setattr(TV, "spock_draw_safe",
                                       lambda g, n=1: True)),
        "Borgs count artifact creatures too": (
            {"T"}, {}, lambda: setattr(LH, "collective_before", all_creatures)),
        "wipe_gate_refund off": ({"U"}, {"wipe_gate_refund": False}, None),
    }
    bad = 0
    for label, (want, extra, patch) in muts.items():
        print(f"-- {label}")
        EXTRA = extra
        if patch:
            patch()
        try:
            broke = run_cases()
        finally:
            EXTRA = {}
            SH.ShilgengarGame.avacyn_returns = real["returns"]
            AZ.DYNAMIC_PT_NAMED_LANDS = real["named"]
            AZ.AzusaGame.top_access = real["top"]
            TV.spock_draw_safe = real["safe"]
            LH.collective_before = real["before"]
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
