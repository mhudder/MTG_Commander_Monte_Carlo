#!/usr/bin/env python3
"""The finality-aware ultimate (§0z82) and five named floors closed (§0z83).

    python -m tests.test_floors_batch
    python -m tests.test_floors_batch --mutate   # 6 mutations, exact sets

    Vault 11: Voter's Dilemma  I - a 1/1 per opponent. II, III - a vote.
    Trial of a Time Lord       I-III - exile. IV - a vote. (Sagas: a lore
                               counter as it enters and after your draw step.)
    Dragon's Rage Channeler    Delirium - +2/+2, flying, attacks if able.
    Pinnacle Monk              ETB: return an instant or sorcery card from
                               your graveyard to your hand.
    Sakura-Tribe Elder         Sacrifice: a basic land, tapped; shuffle.
    Solemn Simulacrum          ETB: a basic land, tapped; shuffle. Dies: may
                               draw a card.
    Gloomshrieker              ETB: return a permanent card from your
                               graveyard to your hand. Would die: exiled
                               instead.               (Scryfall, 2026-09-29)

CASES
  A  shilgengar: a finality creature does not return if fed; a plain card
     does; a token does not
  B  `ult_fodder` puts a plain card ahead of a finality creature with MORE
     Blood -- it is grouped with the bodies that do not come back
  C  `ult_plan` with one creature in the yard and only a finality card to
     feed: no plan (it would not come back, so feeding it is no gain)
  D  tivit Vault 11: no vote as it enters, its Soldiers made; a vote on each
     of the next two draw steps; then it is sacrificed
  E  Trial of a Time Lord: its one vote on the THIRD draw step (chapter IV)
  F  `saga_chapters=False`: Vault 11 votes as it enters (the old engine)
  G  lorehold Dragon's Rage Channeler: 3/3 with four card types in the
     graveyard, 1/1 with three
  H  Pinnacle Monk enters: the largest instant or sorcery comes back to hand
  I  rendmaw `fetch_basics`: the basic of the scarcer colour, tapped, and the
     library one card shorter
  J  Sakura-Tribe Elder at the end step: sacrificed (Blood Artist drains), a
     basic fetched, the Elder in the graveyard
  K  Solemn Simulacrum: a land and no card as it enters; a card when it dies
  L  Gloomshrieker: returns a permanent card as it enters; destroyed, it is
     exiled -- not in the graveyard, and Blood Artist does not drain
  M  NEIGHBOUR: a plain creature destroyed with Blood Artist out drains

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  returns_if_fed ignores finality          -> A, B, C
  saga_step does nothing                   -> D, E
  delirium_bonus is always 0               -> G
  regrow_best_spell returns nothing        -> H
  fetch_basics fetches nothing             -> I, J, K
  rendmaw's Gloomshrieker is never exiled  -> L

UNMUTATED (§0z15): F is the knob reproducing the old engine; M is the
neighbour the exile must not touch.
"""
import random
import sys

import edhmc.engine as EN
import edhmc.lorehold as L
import edhmc.opponents as OPP
import edhmc.shilgengar as SH
import edhmc.tivit as T
from edhmc.decks import lorehold_v16 as LM
from edhmc.decks import rendmaw_v12 as RM
from edhmc.decks import shilgengar_v1 as SM
from edhmc.decks import tivit_v1 as TM
from edhmc.experiment import DEFAULT_CFG

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def pool(module):
    deck, cmd = module.build()
    cards = list(deck) + [v for v in vars(module).values()
                          if isinstance(v, EN.Card)]
    return deck, cmd, {c.name: c for c in cards}


SDECK, SCMD, S_ = pool(SM)
TDECK, TCMD, T_ = pool(TM)
LDECK, LCMD, L_ = pool(LM)
RDECK, RCMD, R_ = pool(RM)


def body(name, p=2, t=2, types=("Creature",)):
    return EN.Card(name=name, types=frozenset(types), power=p, toughness=t)


def perm(c, **kw):
    return EN.Permanent(card=c, sick=False, base_p=c.power,
                        base_t=c.toughness, **kw)


def spell(name, kind, mv):
    return EN.Card(name=name, types=frozenset({kind}), cost={"gen": mv})


def land(name, col):
    return EN.Card(name=name, types=frozenset({"Land"}), is_land=True,
                   produces=frozenset({col}))


# ---------------------------------------------------------------- shilgengar
def sgame(**cfg):
    g = SH.ShilgengarGame(list(SDECK), SCMD, dict(DEFAULT_CFG, turns=20, **cfg), 7)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(20)]
    g.turn = 6
    return g


def case_shilgengar():
    g = sgame()
    fin, plain = body("Returned", 2, 5), body("Plain", 2, 1)
    tok = EN.Permanent(card=body("Spirit", 1, 1), sick=False, is_token=True)
    g.finality.add(id(fin))
    pf, pp = perm(fin), perm(plain)
    g.board += [pf, pp, tok]
    check("A fed: finality no, plain yes, token no",
          (g.returns_if_fed(pf), g.returns_if_fed(pp), g.returns_if_fed(tok)),
          (False, True, False))
    check("B the plain card sorts ahead of the finality creature",
          g.ult_fodder()[0] is pp, True)
    g = sgame()
    g.commander_cast = True
    g.board.append(EN.Permanent(card=SCMD, sick=False))
    fin = body("Returned", 2, 2)
    g.finality.add(id(fin))
    g.board.append(perm(fin))
    g.graveyard = [body("Dead")]
    g.blood = 5
    check("C one yard creature, only a finality card to feed: no plan",
          g.ult_plan(), None)


# --------------------------------------------------------------------- tivit
def tgame(**cfg):
    g = T.TivitGame(list(TDECK), TCMD, dict(DEFAULT_CFG, turns=20, **cfg), 1)
    for o in g.opponents:
        o.life = float(10 ** 9)
    g.board = type(g.board)()
    g.hand, g.graveyard = [], []
    g.library = [body(f"L{i}") for i in range(30)]
    g.turn = 5
    return g


def case_tivit():
    vault = T_["Vault 11: Voter's Dilemma"]
    g = tgame()
    T.resolve(g, vault)
    at_cast = (g.m["votes_cast"], g.soldier_tokens > 0 or any(
        p.is_token for p in g.board) or g.m["tokens_made"] > 0)
    T.saga_step(g)
    one = g.m["saga_votes"]
    T.saga_step(g)
    two = g.m["saga_votes"]
    gone = (any(p.card is vault for p in g.board), vault in g.graveyard)
    check("D Vault 11: no vote as it enters; II and III vote; then sacrificed",
          (at_cast[0], one, two, gone), (0, 1, 2, (False, True)))
    trial = T_["Trial of a Time Lord"]
    g = tgame()
    T.resolve(g, trial)
    votes = []
    for _ in range(3):
        T.saga_step(g)
        votes.append(g.m["saga_votes"])
    check("E Trial votes on the third draw step only", votes, [0, 0, 1])
    g = tgame(saga_chapters=False)
    T.resolve(g, vault)
    check("F saga_chapters off: Vault 11 votes as it enters",
          g.m["votes_cast"] > 0, True)


# ------------------------------------------------------------------ lorehold
def lgame(**cfg):
    g = L.LoreholdGame(list(LDECK), LCMD, dict(DEFAULT_CFG, **cfg), 1)
    g.board = L.Board()
    g.hand, g.graveyard = [], []
    g.treasures = 0
    g.turn = 6
    return g


def case_lorehold():
    drc = L_["Dragon's Rage Channeler"]
    g = lgame()
    p = EN.Permanent(card=drc, sick=False)
    g.board.append(p)
    g.graveyard = [land("Mountain", "R"), spell("Bolt", "Instant", 1),
                   spell("Wrath", "Sorcery", 4), body("Bear")]
    four = (g.power_of(p), g.toughness_of(p))
    g.graveyard.pop()
    three = (g.power_of(p), g.toughness_of(p))
    check("G Channeler: 3/3 with delirium, 1/1 without",
          (four, three), ((3, 3), (1, 1)))
    g = lgame()
    small, big = spell("Small", "Instant", 1), spell("Big", "Sorcery", 7)
    g.graveyard = [small, big]
    L.resolve_spell(g, L_["Pinnacle Monk"], paid=5)
    check("H Pinnacle Monk returns the largest instant or sorcery",
          (big in g.hand, small in g.graveyard), (True, True))


# ------------------------------------------------------------------- rendmaw
def rgame(*cards, **cfg):
    g = EN.Game(list(RDECK), RCMD, dict(DEFAULT_CFG, **cfg),
                random.Random(1), seed_for_pod=1)
    g.board = EN.Board()
    g.hand, g.graveyard = [], []
    g.library = ([land("Forest", "G")] * 3 + [land("Swamp", "B")] * 3
                 + [body(f"L{i}") for i in range(10)])
    g.turn = 6
    for o in g.opponents:
        o.life = 40.0
    for c in cards:
        g.board.append(perm(c))
    return g


def case_rendmaw():
    forest = land("Forest", "G")
    g = rgame(forest, forest)
    n = len(g.library)
    EN.fetch_basics(g, 1)
    got = [p for p in g.board if p.card.name == "Swamp"]
    check("I fetch_basics: the scarcer colour, tapped, library one shorter",
          (len(got), got[0].tapped if got else None, len(g.library)),
          (1, True, n - 1))
    artist = R_["Blood Artist"]
    elder = R_["Sakura-Tribe Elder"]
    g = rgame(artist, elder)
    EN.sakura_tribe_elder(g)
    check("J Elder: sacrificed, drains, a basic fetched, in the graveyard",
          (g.m["drain_damage"], g.m["basics_fetched"], elder in g.graveyard,
           any(p.card is elder for p in g.board)), (1.0, 1, True, False))
    solemn = R_["Solemn Simulacrum"]
    g = rgame()
    hand = len(g.hand)
    p = perm(solemn)
    g.board.append(p)
    EN.run_etb(g, p)
    entered = (len(g.hand) - hand, g.m["basics_fetched"])
    OPP.destroy(g, p, destroys=True)
    check("K Solemn: a land and no card entering; a card when it dies",
          (entered, len(g.hand) - hand), ((0, 1), 1))
    gloom = R_["Gloomshrieker"]
    g = rgame(artist)
    good = R_["Grave Titan"]
    g.graveyard = [land("Forest", "G"), good]
    p = perm(gloom)
    g.board.append(p)
    EN.run_etb(g, p)
    returned = good in g.hand
    OPP.destroy(g, p, destroys=True)
    check("L Gloomshrieker: returns a card; destroyed, exiled without a drain",
          (returned, gloom in g.graveyard, g.m["drain_damage"]),
          (True, False, 0))
    g = rgame(artist)
    q = perm(body("Bear"))
    g.board.append(q)
    OPP.destroy(g, q, destroys=True)
    check("M a plain creature destroyed: Blood Artist drains",
          g.m["drain_damage"], 1.0)


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    case_shilgengar()
    case_tivit()
    case_lorehold()
    case_rendmaw()
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Finality-aware ultimate; five floors closed\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    muts = {
        "returns_if_fed ignores finality":
            ({"A", "B", "C"}, SH.ShilgengarGame, "returns_if_fed",
             lambda self, p: not p.is_token),
        "saga_step does nothing":
            ({"D", "E"}, T, "saga_step", lambda g: None),
        "delirium_bonus is always 0":
            ({"G"}, L.LoreholdGame, "delirium_bonus", lambda self, p: 0),
        "regrow_best_spell returns nothing":
            ({"H"}, L, "regrow_best_spell", lambda g: None),
        "fetch_basics fetches nothing":
            ({"I", "J", "K"}, EN, "fetch_basics", lambda g, n: 0),
        "rendmaw's Gloomshrieker is never exiled":
            ({"L"}, EN.Game, "exiled_instead_of_dying", lambda self, p: False),
    }
    bad = 0
    for label, (want, owner, name, fn) in muts.items():
        print(f"-- {label}")
        real = getattr(owner, name)
        setattr(owner, name, fn)
        try:
            broke = run_cases()
        finally:
            setattr(owner, name, real)
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
