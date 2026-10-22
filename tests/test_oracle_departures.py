#!/usr/bin/env python3
"""Pin queue item 5's last lines -- §0z116's one-liners, lorehold's extra
turns, the Reservoir's timing, both Sorins -- fixed in §0z153.

    python -m tests.test_oracle_departures
    python -m tests.test_oracle_departures --mutate   # 25 mutations, exact sets

On the default pod (POD_V4). Built on `tests.test_oracle_remainder`'s games,
so a mutation set there (`B.CFG`) reaches every engine here.

CASES
  A  lorehold: an extra turn is a whole turn taken before the pod's round
  B  karlov: the Reservoir fires as life reaches 51, not at the next upkeep
  C  karlov: extort cannot be paid from Sol Ring's {C}
  D  ... and is paid from a Swamp
  E  karlov: a countered creature spell is a Syr Konrad trigger
  F  karlov: Syr Konrad's {1}{B} mill on the mana left over
  G  karlov: Sorin, Vengeful Bloodlord enters with 4 loyalty and -2s for a
     two-drop creature card in the graveyard
  H  rendmaw: Verdurous Gearhulk's four counters go on the flier
  I  rendmaw: Ophiomancer makes no Snake while Sakura-Tribe Elder is out
  J  rendmaw: Rendmaw's ETB Birds are doubled by Roaming Throne
  K  rendmaw: Beastmaster Ascension's quest counters carry over
  L  rendmaw: Coat of Arms pumps two Zombies (not Birds) by one each
  M  rendmaw: Ohran Frostfang draws one per attacker that connects -- six
  N  lorehold: Blasphemous Act counts the pod's nine creatures
  O  lorehold: Reforge the Soul is 21 Smothering Tithe Treasures
  P  tivit: ten Treasures mid-turn do not win before the upkeep
  Q  tivit: ... and they win at the upkeep
  R  tivit: Lieutenants of the Guard keeps its strength-vote counter
  S  tivit: Messenger Jays discards one for each card it draws
  T  tivit: Tyrant's Choice -- the pod votes death and sacrifices its
     smallest creature, and loses no life
  U  shilgengar: Speaker of the Heavens taps for its Angel at sorcery speed
  V  shilgengar: Resplendent Angel at an opponent's end step
  W  shilgengar: Revel in Riches wins at the upkeep
  X  shilgengar: Emeria Shepherd off a Swamp returns the card to hand
  Y  azusa: Tireless Provisioner's Treasure is still there next turn
  Z  azusa: Momentous Fall sacrifices the 5/5, not the 1/1 token
  AA azusa: Realms Uncharted -- four different lands, two binned, two kept
  AB azusa: Cultivate shuffles

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  extra_turn_full=False        -> A
  reservoir_any_time=False     -> B
  extort_hybrid=False          -> C
  konrad_text=False            -> E, F
  sorin_loyalty=False          -> G
  gearhulk_best=False          -> H
  snake_types=False            -> I
  throne_etb=False             -> J
  beast_quest=False            -> K
  coat_types=False             -> L
  frostfang_connect=False      -> M
  act_pod_count=False          -> N
  tithe_forced_draws=False     -> O
  alt_win_at_upkeep=False      -> P
  dilemma_counters=False       -> R
  jays_discard=False           -> S
  tyrant_death=False           -> T
  speaker_taps=False           -> U
  resplendent_each_end=False   -> V
  revel_at_upkeep=False        -> W
  shepherd_plains=False        -> X
  provisioner_treasure=False   -> Y
  momentous_biggest=False      -> Z
  realms_text=False            -> AA
  search_shuffle=False         -> AB

UNMUTATED (§0z15): D and Q are the positive controls C and P are measured
against -- a Swamp pays extort, and the upkeep wins, under either rule.
"""
import dataclasses
import sys

import edhmc.azusa as AZ
import edhmc.engine as EN
import edhmc.karlov as KA
import edhmc.lorehold as LO
import edhmc.opponents as OPP
import edhmc.tivit as TI
from edhmc.pending import build_pending
from tests import test_oracle_remainder as B

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
AZUSA = build_pending("azusa")
card, body, lands, perm, fresh = B.card, B.body, B.lands, B.perm, B.fresh


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def acard(name):
    return dataclasses.replace(next(c for c in AZUSA[0] if c.name == name))


def fresh_azusa(board=(), hand=(), library=None):
    d, cmd = AZUSA
    g = AZ.AzusaGame(list(d), cmd, B.cfg(), 1234)
    g.board = EN.Board()
    g.hand = list(hand)
    g.graveyard = []
    g.library = (library if library is not None
                 else [B.filler(i) for i in range(30)])
    g.your_life = 40.0
    g.turn = 7
    for o in g.opponents:
        o.life, o.creatures, o.bodies = 40.0, 0.0, []
        o.pieces, o.piece_lands = (), []
    for c in board:
        g.board.append(EN.Permanent(card=c))
    return g


def run_cases():
    PASS.clear()
    FAIL.clear()

    # -- lorehold's extra turn, karlov ----------------------------------------
    g = fresh("lorehold")
    g.m["extra_turns"] = 1
    LO.take_turn(g)
    check("A lorehold: the extra turn is a whole turn, before the pod",
          (g.turn, g.m["extra_turns_taken"]), (9, 1))
    g = fresh("karlov", board=[card("karlov", "Aetherflux Reservoir")])
    g.your_life = 50.0
    KA.gain_life(g, 1)
    check("B karlov: the Reservoir fires at 51 life", g.your_life, 1.0)
    obey = card("karlov", "Blind Obedience")
    g = fresh("karlov", board=[card("karlov", "Sol Ring"), obey])
    KA.cast_triggers(g, B.filler(1))
    check("C karlov: Sol Ring's {C} pays no extort",
          g.m["extort_triggers"], 0)
    g = fresh("karlov", board=lands("karlov", "Swamp") + [obey])
    KA.cast_triggers(g, B.filler(1))
    check("D ... a Swamp does", g.m["extort_triggers"], 1)
    konrad = card("karlov", "Syr Konrad, the Grim")
    g = fresh("karlov", board=lands("karlov", "Plains", "Plains", "Plains")
              + [konrad], hand=[body("Bear")])
    B.force_counters(g)
    KA.main_phase(g)
    check("E karlov: a countered creature spell triggers Syr Konrad",
          (g.m["countered"], [o.life for o in g.opponents]),
          (1, [39.0, 39.0, 39.0]))
    g = fresh("karlov", board=lands("karlov", "Swamp", "Swamp") + [konrad])
    KA.konrad_mill(g)
    check("F karlov: Syr Konrad mills on the mana left over",
          (g.m["konrad_mills"], len(g.graveyard)), (1, 1))
    g = fresh("karlov")
    two = body("Two-Drop")
    two.cost = {"gen": 2}
    g.graveyard = [two]
    KA.enter_permanent(g, card("karlov", "Sorin, Vengeful Bloodlord"))
    sorin = perm(g, "Sorin, Vengeful Bloodlord")
    entered = sorin.counters
    KA.sorin_bloodlord_step(g)
    check("G karlov: Sorin enters with 4 and -2s for the two-drop",
          (entered, sorin.counters, any(p.card is two for p in g.board)),
          (4, 2, True))

    # -- rendmaw ----------------------------------------------------------------
    flier = body("Flier", 1)
    flier.flying = True
    hulk = card("rendmaw", "Verdurous Gearhulk")
    g = fresh("rendmaw", board=[body("Ground", 5), flier, hulk])
    EN.run_etb(g, perm(g, "Verdurous Gearhulk"))
    check("H rendmaw: Gearhulk's four counters on the flier",
          perm(g, "Flier").counters, 4)
    g = fresh("rendmaw", board=[card("rendmaw", "Ophiomancer"),
                                card("rendmaw", "Sakura-Tribe Elder")])
    EN.upkeep(g)
    check("I rendmaw: no Snake token while Sakura-Tribe Elder is out",
          sum(1 for p in g.board if p.card.name == "Snake token"), 0)
    g = fresh("rendmaw", board=lands("rendmaw", "Swamp", "Forest", "Swamp",
                                     "Forest", "Swamp")
              + [card("rendmaw", "Roaming Throne")])
    EN.main_phase(g)
    check("J rendmaw: Roaming Throne doubles Rendmaw's ETB",
          sum(1 for p in g.board if p.card.name == "Bird token"), 2)
    asc = card("rendmaw", "Beastmaster Ascension")
    g = fresh("rendmaw", board=[asc, body("Bear"), body("Wolf")])
    perm(g, "Beastmaster Ascension").quest = 5
    EN.combat(g)
    check("K rendmaw: quest counters carry over, seven with two attackers",
          g.beast_active, True)
    zombies = []
    for i in range(2):
        zombies.append(EN.Permanent(card=EN.Card(
            name="Zombie token", types=frozenset({"Creature"}), power=2,
            toughness=2), is_token=True, sick=False, base_p=2, base_t=2))
    dealt = []
    for extra in ([], [card("rendmaw", "Coat of Arms")]):
        g = fresh("rendmaw", board=extra)
        for z in zombies:
            g.board.append(dataclasses.replace(z))
        EN.combat(g)
        dealt.append(g.m["damage"])
    check("L rendmaw: Coat of Arms pumps two Zombies by one each",
          dealt[1] - dealt[0], 2.0)
    fang = card("rendmaw", "Ohran Frostfang")
    g = fresh("rendmaw", board=[fang] + [body(f"Bear {i}") for i in range(6)],
              sick=(fang,))
    EN.combat(g)
    check("M rendmaw: Frostfang draws one per connecting attacker",
          len(g.hand), 6)

    # -- lorehold, tivit ----------------------------------------------------------
    g = fresh("lorehold")
    for o in g.opponents:
        o.creatures = 3.0
    check("N lorehold: Blasphemous Act counts the pod's nine",
          LO.reduce_cost(g, card("lorehold", "Blasphemous Act")).get("gen"),
          0)
    g = fresh("lorehold", board=[card("lorehold", "Smothering Tithe")])
    before = g.treasures
    LO.apply_spell_effects(g, card("lorehold", "Reforge the Soul"))
    check("O lorehold: Reforge the Soul is 21 Tithe Treasures",
          g.treasures - before, 21)
    revel = card("tivit", "Revel in Riches")
    g = fresh("tivit", board=[revel])
    g.tokens["Treasure"] = 12
    TI.convert_the_pile(g)
    check("P tivit: a mid-turn pile does not win yet", g.result, None)
    TI.upkeep(g)
    check("Q ... it wins at the upkeep", g.result, "win")
    g = fresh("tivit")
    TI.resolve(g, card("tivit", "Lieutenants of the Guard"))
    check("R tivit: Lieutenants keeps its strength-vote counter",
          perm(g, "Lieutenants of the Guard").counters, 1)
    g = fresh("tivit")
    TI.resolve(g, card("tivit", "Messenger Jays"))
    check("S tivit: Messenger Jays discards what it draws", len(g.hand), 0)
    g = fresh("tivit")
    for o in g.opponents:
        o.bodies = [OPP.PodBody(1, 1), OPP.PodBody(3, 3)]
        o.creatures = 2.0
    TI.resolve(g, card("tivit", "Tyrant's Choice"))
    check("T tivit: the pod votes death and sacrifices its smallest",
          ([[b.toughness for b in o.bodies] for o in g.opponents],
           [o.life for o in g.opponents]),
          ([[3], [3], [3]], [40.0, 40.0, 40.0]))

    # -- shilgengar -----------------------------------------------------------------
    g = fresh("shilgengar", board=[card("shilgengar", "Speaker of the Heavens")])
    g.your_life = 48.0
    g.speaker_step()
    check("U shilgengar: Speaker taps for its Angel",
          (perm(g, "Speaker of the Heavens").tapped,
           g.m["speaker_angels"]), (True, 1))
    g = fresh("shilgengar", board=[card("shilgengar", "Resplendent Angel")])
    g.gain_life(5)
    g.pod_end_step(0)
    check("V shilgengar: Resplendent Angel at an opponent's end step",
          g.m["resplendent_pod_angels"], 1)
    g = fresh("shilgengar", board=[card("shilgengar", "Revel in Riches")])
    g.treasures = 10
    g.upkeep()
    check("W shilgengar: Revel in Riches wins at the upkeep", g.result, "win")
    gone = card("shilgengar", "Sol Ring")
    g = fresh("shilgengar", board=[card("shilgengar", "Emeria Shepherd")],
              hand=lands("shilgengar", "Swamp"))
    g.graveyard = [gone]
    g.land_step()
    check("X shilgengar: Emeria Shepherd off a Swamp returns to hand",
          (any(c is gone for c in g.hand),
           any(p.card is gone for p in g.board)), (True, False))

    # -- azusa ----------------------------------------------------------------------
    forests = [acard("Forest") for _ in range(30)]
    g = fresh_azusa(board=[acard("Tireless Provisioner")], library=forests)
    g.land_entered(acard("Forest"))
    AZ.take_turn(g)
    check("Y azusa: Provisioner's Treasure survives the turn",
          any(isinstance(f, AZ.TreasureMana) for f in g.bonus_mana), True)
    big = body("Big", 5)
    tok = EN.Permanent(card=body("Saproling token", 1), is_token=True)
    g = fresh_azusa(board=[big])
    g.board.append(tok)
    g.sac_for_value(momentous=True)
    check("Z azusa: Momentous Fall sacrifices the 5/5", len(g.hand), 5)
    pool = [acard(n) for n in ("Forest", "Forest", "Windswept Heath",
                               "Wooded Foothills", "Evolving Wilds",
                               "Crystal Vein")]
    g = fresh_azusa(library=[B.filler(i) for i in range(20)] + pool)
    g.resolve(acard("Realms Uncharted"))
    check("AA azusa: Realms Uncharted -- two binned, two kept",
          (sum(c.is_land for c in g.graveyard), sum(c.is_land for c in g.hand),
           len({c.name for c in g.graveyard + g.hand if c.is_land})),
          (2, 2, 4))
    g = fresh_azusa(library=[acard("Forest") for _ in range(10)]
                    + [B.filler(i) for i in range(20)])
    g.resolve(acard("Cultivate"))
    check("AB azusa: Cultivate shuffles", g.m["library_shuffles"], 1)
    return set(FAIL)


def main() -> int:
    if not MUTATE:
        print("Queue item 5's last lines (§0z153)\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0
    mutations = [
        ({"extra_turn_full": False}, {"A"}),
        ({"reservoir_any_time": False}, {"B"}),
        ({"extort_hybrid": False}, {"C"}),
        ({"konrad_text": False}, {"E", "F"}),
        ({"sorin_loyalty": False}, {"G"}),
        ({"gearhulk_best": False}, {"H"}),
        ({"snake_types": False}, {"I"}),
        ({"throne_etb": False}, {"J"}),
        ({"beast_quest": False}, {"K"}),
        ({"coat_types": False}, {"L"}),
        ({"frostfang_connect": False}, {"M"}),
        ({"act_pod_count": False}, {"N"}),
        ({"tithe_forced_draws": False}, {"O"}),
        ({"alt_win_at_upkeep": False}, {"P"}),
        ({"dilemma_counters": False}, {"R"}),
        ({"jays_discard": False}, {"S"}),
        ({"tyrant_death": False}, {"T"}),
        ({"speaker_taps": False}, {"U"}),
        ({"resplendent_each_end": False}, {"V"}),
        ({"revel_at_upkeep": False}, {"W"}),
        ({"shepherd_plains": False}, {"X"}),
        ({"provisioner_treasure": False}, {"Y"}),
        ({"momentous_biggest": False}, {"Z"}),
        ({"realms_text": False}, {"AA"}),
        ({"search_shuffle": False}, {"AB"}),
    ]
    print("MUTATION RUN -- exact sets\n")
    bad = 0
    for over, want in mutations:
        B.CFG.update(over)
        try:
            broke = run_cases()
        finally:
            B.CFG.clear()
        ok = broke == want
        bad += not ok
        print(f"   {over}: broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(mutations) - bad} passed, {bad} failed "
          f"({len(mutations)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
