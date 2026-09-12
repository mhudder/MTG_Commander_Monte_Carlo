#!/usr/bin/env python3
"""The land-animation pillar was untested, not disproved. Four fixes, measured.

THE CLAIMS UNDER TEST, all facts about the cards rather than about this model.
Verified against Scryfall 2026-09-07:

    Sylvan Awakening  {2}{G}  "UNTIL YOUR NEXT TURN, all lands you control
        become 2/2 Elemental creatures with reach, indestructible, and haste.
        They're still lands."
    Rude Awakening  {4}{G}  "Choose one -- Untap all lands you control; or
        UNTIL END OF TURN, lands you control become 2/2 creatures that are
        still lands.  Entwine {2}{G}"
    Nissa, Worldwaker  {3}{G}{G}  loyalty 3
        "+1: Target land you control becomes a 4/4 Elemental creature with
         trample.  +1: Untap up to four target Forests.
         -7: Search your library for any number of basic land cards, put them
         onto the battlefield, then shuffle. Those lands become 4/4s."
    Nissa, Vastwood Seer  "Whenever a land you control enters, IF YOU CONTROL
        SEVEN OR MORE LANDS, exile Nissa, then return her transformed."
    Nissa, Sage Animist  loyalty 3
        "+1: Reveal the top card. If it's a land, put it onto the
         battlefield. Otherwise, put it into your hand.  -7: Untap up to six
         target lands. They become 6/6s."

`ablation_azusa.txt` scored Sylvan Awakening +0.0017 and Rude Awakening
+0.0019 -- both inside their own bars -- on an engine where Sylvan set a
turn-scoped flag, Rude Awakening was implemented as its untap mode only, and
BOTH NISSAS HAD NO ABILITIES AT ALL. This is the "a card scoring like a blank
usually means the engine has made it a blank" check for those rows.

    python diag_azusa_animation.py [--n=4000] [--procs=N]

PART A  forced boards -- one property of one card per case.
PART B  real games: how often each piece fires and what it produces.
PART C  the four fixes as separate paired CFG flips.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.decks import azusa_v1
from edhmc.engine import Permanent
from edhmc.experiment import DEFAULT_CFG
from edhmc import azusa as A
from edhmc import opponents as OPP

DECK, CMD = azusa_v1.build()

# THREE OF THE CARDS THIS DIAGNOSTIC MEASURES WERE CUT FROM THE DECK ON
# 2026-09-10, AND IT STOPPED RUNNING AT ALL.
#
# `BY_NAME` was built from the deck, so the first `cast(g, "Sylvan Awakening")`
# died with `KeyError: 'Sylvan Awakening'` and took `--mutate` -- which
# CLAUDE.md tells the reader to run, and which is the only thing that says
# these cases can fail -- down with it. §0y cut the whole land-animation
# pillar (Sylvan Awakening, Rude Awakening and Nissa, Worldwaker) for Ancient
# Greenwarden, Greensleeves and Springheart Nantuko.
#
# THE CARDS LEFT; THE ENGINE DID NOT. `azusa.sylvan_awakening`,
# `azusa.rude_awakening` and Nissa's loyalty abilities are all still live code
# on the default path, still reachable by any future green list, and still
# exactly what PART A pins. A diagnostic about a MECHANISM should not be
# deleted because one list stopped playing it -- so the three definitions are
# restored here, verbatim from `d158724^`, the commit before the cut.
#
# This is §0q's failure mode one level up: a hand-maintained name set that
# rotted, inside the mutation check whose whole job is to notice rot. The
# check below is the derivation-shaped fix -- the names are declared once and
# verified to resolve, so the NEXT cut fails loudly at import with a sentence
# instead of a KeyError forty lines into a case.
CUT_2026_09_10 = [
    azusa_v1.C("Nissa, Worldwaker", "Planeswalker", {"gen": 3, "G": 2}, 0, 0,
               priority=6, threat=8.0, tags=("Legendary",)),
    azusa_v1.C("Rude Awakening", "Sorcery", {"gen": 4, "G": 1}, priority=7,
               threat=6.0, script="rude_awakening"),
    azusa_v1.C("Sylvan Awakening", "Sorcery", {"gen": 2, "G": 1}, priority=7,
               threat=6.5, script="sylvan_awakening"),
]

# The deck wins on any name it still carries, so a card that comes BACK into
# the list is measured as the list defines it, not as this stale copy does.
BY_NAME = {c.name: c for c in list(CUT_2026_09_10) + list(DECK)}

# Every card name this file reaches for, declared in one place.
REQUIRED = ("Forest",
            "Nissa, Vastwood Seer // Nissa, Sage Animist",
            "Nissa, Worldwaker",
            "Rude Awakening",
            "Sylvan Awakening")
_missing = [n for n in REQUIRED if n not in BY_NAME]
if _missing:
    raise SystemExit(
        f"\ndiag_azusa_animation names {len(_missing)} card(s) that are in "
        f"neither the azusa deck nor CUT_2026_09_10:\n"
        + "".join(f"    {n}\n" for n in _missing)
        + "A card this diagnostic measures has been cut from the list. Either\n"
          "add its definition to CUT_2026_09_10 (from git history, verbatim),\n"
          "or drop the cases that use it -- but do not leave the name here\n"
          "unresolved, which is how this file spent a day raising KeyError\n"
          "from inside its own mutation check.")

# "legacy" is the engine as it stood in the committed ablation table: Sylvan
# Awakening as an attack-only flag, Rude Awakening as its untap mode, no
# loyalty abilities. See the note under CASES about the one correction that
# has no flag.
OLD = {"land_animation": "legacy", "animated_lands_block": False,
       "rude_awakening_modes": False, "planeswalker_abilities": False}
NEW = {"land_animation": "full", "animated_lands_block": True,
       "rude_awakening_modes": True, "planeswalker_abilities": True}


# ---------------------------------------------------------------------------
# PART A -- forced boards
# ---------------------------------------------------------------------------

def game(flags=NEW, lands=0, turns=20, tapped=False):
    """An AzusaGame with `lands` Forests already on the battlefield."""
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)
    g = A.AzusaGame(DECK, CMD, cfg, 1)
    g.opening_hand()
    forest = BY_NAME["Forest"]
    for _ in range(lands):
        g.board.append(Permanent(card=forest, sick=False, tapped=tapped,
                                 base_p=0, base_t=0))
    return g


def cast(g, name):
    """Resolve a card by name, as the engine would."""
    g.resolve(BY_NAME[name])


def a_capture():
    """The animated set is fixed AT RESOLUTION, not a static ability."""
    g = game(lands=4)
    cast(g, "Sylvan Awakening")
    before = sum(1 for p in g.board if g.counts_as_creature(p))
    g.board.append(Permanent(card=BY_NAME["Forest"], sick=True,
                             base_p=0, base_t=0))
    after = sum(1 for p in g.board if g.counts_as_creature(p))
    # `before == 4` is not decoration: without it this case passes when
    # NOTHING is animated at all, which is the state the engine was already
    # in and the state a broken fix would leave it in.
    return ("a land played AFTER Sylvan Awakening is not animated",
            f"{before} animated, still {after} after a 5th land",
            before == 4 and after == before)


def a_haste():
    """Sylvan grants haste, so a land played this turn can attack."""
    out = {}
    for label, card in (("Sylvan", "Sylvan Awakening"),
                        ("Rude", "Rude Awakening")):
        g = game(lands=4)
        # a land that entered THIS turn -- make_permanent forces sick=True
        g.make_permanent(BY_NAME["Forest"])
        cast(g, card)
        g.combat()
        out[label] = g.m["animated_attacks"]
    return ("haste: Sylvan lets a land played this turn attack, Rude does not",
            f"Sylvan {out['Sylvan']} attackers, Rude {out['Rude']}",
            out["Sylvan"] == 5 and out["Rude"] == 4)


def a_blocks():
    """Sylvan lasts through the pod's round; Rude's mode does not."""
    out = {}
    for label, card in (("Sylvan", "Sylvan Awakening"),
                        ("Rude", "Rude Awakening")):
        g = game(lands=6)
        cast(g, card)
        g.expire_animations(end_of_turn=True)      # the pod is about to act
        out[label] = OPP.your_creatures(g)
    return ("blockers: Sylvan's lands survive to the pod's round, Rude's do not",
            f"Sylvan {out['Sylvan']} blockers, Rude {out['Rude']}",
            out["Sylvan"] == 6 and out["Rude"] == 0)


def a_taps():
    """An animated land that attacks is tapped and cannot pay for a spell."""
    g = game(lands=6)
    cast(g, "Sylvan Awakening")
    before = len(g.available_mana())
    g.combat()
    after = len(g.available_mana())
    return ("attacking with lands spends them: mana before vs after combat",
            f"{before} -> {after}",
            after == 0 and before == 6)


def a_entwine():
    """Entwine takes both modes: untap AND animate."""
    g = game(lands=9, tapped=True)
    g.board[0].tapped = False
    g.board[1].tapped = False
    g.board[2].tapped = False        # {2}{G} available for the entwine
    cast(g, "Rude Awakening")
    untapped = sum(1 for p in g.board if p.card.is_land and not p.tapped)
    animated = sum(1 for p in g.board if g.counts_as_creature(p))
    return ("Rude Awakening entwined: untaps AND animates",
            f"{untapped}/9 untapped, {animated} animated, "
            f"entwines={g.m['entwines']}",
            g.m["entwines"] == 1 and untapped == 9 and animated == 9)


def a_transform():
    """Vastwood Seer transforms on the seventh land, not before."""
    g = game(lands=5)
    g.make_permanent(BY_NAME["Nissa, Vastwood Seer // Nissa, Sage Animist"])
    g.make_permanent(BY_NAME["Forest"])          # 6 lands
    g.land_entered(BY_NAME["Forest"], played=True)
    six = g.m["nissa_transforms"]
    g.make_permanent(BY_NAME["Forest"])          # 7 lands
    g.land_entered(BY_NAME["Forest"], played=True)
    return ("Nissa, Vastwood Seer transforms at SEVEN lands",
            f"transforms at 6 lands: {six}, at 7: {g.m['nissa_transforms']}",
            six == 0 and g.m["nissa_transforms"] == 1)


def a_loyalty():
    """A walker ticks up once a turn and ultimates at seven."""
    g = game(lands=8)
    g.make_permanent(BY_NAME["Nissa, Worldwaker"], sick=False)
    perm = next(p for p in g.board if p.card.name == "Nissa, Worldwaker")
    start = perm.counters
    g.planeswalker_step()
    g.planeswalker_step()            # same turn: must be a no-op
    once = perm.counters
    perm.counters = 7
    g.pw_used = set()
    g.planeswalker_step()
    return ("Nissa, Worldwaker: enters at 3, +1 once a turn, -7 at seven",
            f"{start} -> {once} after two calls in one turn; "
            f"ultimates={g.m['pw_ultimates']}, loyalty now {perm.counters}",
            start == 3 and once == 4 and g.m["pw_ultimates"] == 1
            and perm.counters == 0)


def a_legacy_off():
    """With the old flags nothing animates, which is what OLD must mean."""
    g = game(flags=OLD, lands=6)
    cast(g, "Sylvan Awakening")
    blocks = OPP.your_creatures(g)
    g.combat()
    mana = len(g.available_mana())
    return ("legacy: Sylvan attacks but never blocks and never taps a land",
            f"{blocks} blockers, {mana} mana still up after attacking",
            blocks == 0 and mana == 6)


CASES = [a_capture, a_haste, a_blocks, a_taps, a_entwine, a_transform,
         a_loyalty, a_legacy_off]


def part_a():
    print("=" * 78)
    print("PART A -- forced boards, one property of one card per case.")
    print("=" * 78)
    print("  Each case asserts a specific line of oracle text, and each was")
    print("  checked to FAIL when the behaviour it pins is removed.\n")
    bad = 0
    for fn in CASES:
        label, detail, ok = fn()
        bad += not ok
        print(f"  {'.' if ok else 'FAIL'}  {label}")
        print(f"        {detail}")
    print(f"\n  {len(CASES)} cases, {bad} failing.\n")
    return bad


# ---------------------------------------------------------------------------
# PART B / C -- real games
# ---------------------------------------------------------------------------

_W = {}
OBS = ("won", "damage", "landfall_triggers", "lands_played", "lands_animated",
       "animated_attacks", "animated_damage", "animated_blocker_turns",
       "pw_activations", "pw_ultimates", "nissa_transforms", "entwines",
       "final_life", "final_board_power")


def _init(flags, turns):
    _W["cfg"] = dict(DEFAULT_CFG, turns=turns, watch=frozenset(), **flags)


def _one(seed):
    r = A.simulate(DECK, CMD, _W["cfg"], seed)
    return [r[m] for m in OBS]


def observe(flags, n, turns, procs):
    with Pool(procs, initializer=_init, initargs=(flags, turns)) as pool:
        rows = pool.map(_one, range(5000, 5000 + n), chunksize=64)
    return np.array(rows, float)


def part_b(n, procs, turns=20):
    print("=" * 78)
    print(f"PART B -- real games, N = {n:,}, T{turns}, default pod.")
    print("=" * 78)
    print("  Per-game means. `anim dmg` is the animation's MARGINAL damage:")
    print("  what got through with the lands attacking minus what would have")
    print("  without them, so chump blocks are already priced in.")
    print("  READ THE LEGACY ROW'S ZEROES AS 'NOT MEASURED', NOT AS 'NEVER")
    print("  HAPPENED'. The legacy engine did attack with its lands -- it")
    print("  fabricated throwaway 2/2s to do it -- and none of these counters")
    print("  existed to see it. PART C is where the two are compared.\n")
    print(f"  {'engine':<9}{'animated':>10}{'attacks':>9}{'anim dmg':>10}"
          f"{'blk turns':>11}{'pw acts':>9}{'ults':>7}{'damage':>10}{'win':>8}")
    for label, flags in (("legacy", OLD), ("full", NEW)):
        a = observe(flags, n, turns, procs)
        col = {m: a[:, i] for i, m in enumerate(OBS)}
        print(f"  {label:<9}{col['lands_animated'].mean():>10.2f}"
              f"{col['animated_attacks'].mean():>9.2f}"
              f"{col['animated_damage'].mean():>10.2f}"
              f"{col['animated_blocker_turns'].mean():>11.2f}"
              f"{col['pw_activations'].mean():>9.2f}"
              f"{col['pw_ultimates'].mean():>7.3f}"
              f"{col['damage'].mean():>10.1f}{col['won'].mean():>8.3f}")
    print()


# Cumulative, so the four deltas add up to ALL FOUR.
#
# ONE CORRECTION IN THIS SET HAS NO FLAG and is present in both columns: lands
# now enter summoning sick (`make_permanent`), which they always should have.
# It is unobservable unless a land is a creature -- `available_mana` never read
# `sick` for a land -- with the single exception of Dryad Arbor, which used to
# be able to attack the turn it was played and now cannot. So "legacy" here
# reproduces the old ANIMATION behaviour, not the old engine bit for bit.
CASES_C = [
    ("land_animation        (a real continuous effect, and attacking taps it)",
     dict(OLD), dict(OLD, land_animation="full")),
    ("animated_lands_block  (Sylvan lasts until YOUR NEXT TURN, so they block)",
     dict(OLD, land_animation="full"),
     dict(OLD, land_animation="full", animated_lands_block=True)),
    ("rude_awakening_modes  (the animate mode and the entwine did not exist)",
     dict(OLD, land_animation="full", animated_lands_block=True),
     dict(NEW, planeswalker_abilities=False)),
    ("planeswalker_abilities  (both Nissas were inert permanents)",
     dict(NEW, planeswalker_abilities=False), dict(NEW)),
    ("ALL FOUR", dict(OLD), dict(NEW)),
]


def part_c(n, procs, turns=20):
    print("=" * 78)
    print(f"PART C -- each fix as a paired CFG flip, N = {n:,}, T{turns}.")
    print("=" * 78)
    print("  Same deck, same seeds, flag off vs on, so common random numbers")
    print("  are intact and nothing but the flag differs. Applied")
    print("  CUMULATIVELY, so the four deltas add up to ALL FOUR.")
    print("  NOTE: this deck's damage column is unusable -- Scute Swarm's")
    print("  doubling gives it a tail with CIs of the same order as the point")
    print("  estimates. Read the win-rate row. (ablation_azusa.txt says so in")
    print("  its own header.)\n")
    for label, off, on in CASES_C:
        a = observe(off, n, turns, procs)
        b = observe(on, n, turns, procs)
        print(f"  {label}")
        for i, m in enumerate(OBS):
            d = b[:, i] - a[:, i]
            hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
            if abs(d.mean()) < 1e-9 and hw < 1e-9:
                continue
            star = " *" if abs(d.mean()) > hw else "  "
            print(f"      {m:<24}{a[:, i].mean():>10.3f} ->"
                  f"{b[:, i].mean():>10.3f}   {d.mean():>+9.4f} "
                  f"+-{hw:<8.4f}{star}")
        print()


def mutate():
    """Run PART A with every fix turned OFF. The seven cases that pin new
    behaviour MUST fail and the one that pins the old behaviour must pass.

    A check that cannot fail is worse than no check, because it reads like
    assurance (KNOWN_ISSUES.md 0q). This is that proof, kept in the tool
    rather than done once in a shell and asserted in a comment -- `NEW` is
    mutated in place because `game(flags=NEW)` bound the dict as a default
    argument at definition time, and rebinding the name does nothing.
    """
    print("=" * 78)
    print("MUTATION CHECK -- PART A with every fix disabled.")
    print("=" * 78)
    NEW.clear()
    NEW.update(OLD)
    bad = part_a()
    want = len(CASES) - 1        # a_legacy_off asserts the OLD behaviour
    if bad == want:
        print(f"  OK: {bad} of {len(CASES)} cases fail with the fixes off, "
              f"and the legacy case still passes.\n")
        return 0
    print(f"  MUTATION CHECK FAILED: expected {want} failures, got {bad}. "
          f"Some case above passes whether the fix is there or not.\n")
    return 1


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 4000)
    procs = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--procs=")), None)
    if "--mutate" in args:
        return mutate()
    bad = part_a()
    part_b(n, procs)
    part_c(n, procs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
