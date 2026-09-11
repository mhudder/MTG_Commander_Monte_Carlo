#!/usr/bin/env python3
"""Is a card's ablation score measuring its TEXT, or its THREAT NUMBER?

WHY THIS EXISTS. `ablation.py:blank_like()` builds the replacement-level card
by copying the real card's COST and nothing else. Three things it drops are
not cosmetic:

  threat    `Card.threat` defaults to 0.0, which `opponents.threat_of()` reads
            as "derive it" -> `power * 0.8` for a creature, `mv * 0.5`
            otherwise. So a blank sits at 0.8-2.5 against a real card's
            hand-assigned 5-9. threat feeds `board_threat()` -> `your_share()`,
            which sets both the share of pod removal aimed at you AND the
            probability an opponent's clock picks YOU -- the route by which
            most games are lost. It also gates `countered()`, whose threshold
            is 4.0: a card at threat 7.0 is counterable and its blank is
            categorically not.
  priority  `main_phase` is greedy on priority, so a blank at 0.5 is cast only
            when nothing else in hand is affordable. That is a DEAD card, not
            a replacement-level one -- so the real card is charged its full
            tempo against an opponent that never spends any.
  body      a creature blank is 1/1. Blood Artist is a 0/1, so its own blank
            is the better body.

For a card with a big effect the tax is swamped. For a card whose output is
small or diffuse it can be the whole measurement -- which makes the score a
fact about a hand-tuned constant, not about the card. That is worst exactly at
the BOTTOM of each table, which is the region anyone reads when looking for
cuts.

This decomposes each card's score by re-running its ablation against blanks
that match the real card on progressively more of what `blank_like` drops:

    standard        what ablation.py does now (the number in the table)
    +threat         blank carries the real card's threat
    +priority       also cast at the same point in the curve
    +body           also the same power/toughness (creatures only)

The last row is the closest thing to the card's TEXT alone.

SIGN CONVENTION matches the tables: `real - blanked`, so POSITIVE means the
deck is better with the card than with the blank.

CAVEAT, deliberate and not corrected here: a noncreature blank is a Sorcery,
so blanking an artifact in RENDMAW also removes a commander trigger. That is
`BLANK_KEEPS_TYPES`, an existing documented choice, not part of this bug.

    python diag_threat_blank.py [--n 15000] [deck ...] [card ...]
"""
import sys
from dataclasses import replace
from multiprocessing import Pool, cpu_count

import numpy as np

from edhmc.engine import Card, simulate as rendmaw_sim
from edhmc.lorehold import simulate as lh_sim
from edhmc.karlov import simulate as karlov_sim
from edhmc.tivit import simulate as tivit_sim
from edhmc.pending import build_pending
from edhmc.experiment import DEFAULT_CFG

SIMS = {"lorehold": lh_sim, "rendmaw": rendmaw_sim,
        "karlov": karlov_sim, "tivit": tivit_sim}

# `removal_eaten` is the mechanism counter for the threat channel: if the
# threat number is what is being measured, it moves with it.
WANT = ("won", "damage", "removal_eaten")

# The MODEL-EVALUATED bottom of each table at N=15,000 -- everything at or
# below its own deck's noise floor, plus every card that scored significantly
# NEGATIVE. Model-blind cards are excluded: a low score there is already known
# to be about the model.
CASES = {
    "karlov": ["Blood Artist", "Daxos, Blessed by the Sun", "Swiftfoot Boots",
               "Mother of Runes", "Pristine Talisman", "Vizkopa Guildmage"],
    "rendmaw": ["Blood Artist", "Ornithopter of Paradise", "Palladium Myr",
                "Copper Myr", "Leaden Myr", "Dockside Chef"],
    "lorehold": ["Smothering Tithe", "Blasphemous Act", "Lightning Greaves",
                 "Sensei's Divining Top", "Ruby Medallion", "Mother of Runes",
                 "Victory Chimes", "Boros Signet"],
    "tivit": ["Time Sieve", "Tamiyo's Journal", "Revel in Riches",
              "Ephemerate", "Grudge Keeper", "Idyllic Tutor",
              "Teleportation Circle", "Custodi Squire"],
}

HORIZONS = (10, 20)
_W = {}


def std_blank(card):
    """Exactly `ablation.py:blank_like()` with BLANK_KEEPS_TYPES=0 (default)."""
    if card.is_creature:
        types = frozenset({"Creature"})
    elif card.is_land:
        types = card.types
    else:
        types = frozenset({"Sorcery"})
    return Card(name="(blank)", types=types, cost=dict(card.cost),
                power=1 if card.is_creature else 0,
                toughness=1 if card.is_creature else 0,
                priority=0.5)


def arms_for(card):
    """The blank, then the same blank matching one more real attribute each."""
    b = std_blank(card)
    out = [("standard", b),
           ("+threat", replace(b, threat=card.threat)),
           ("+priority", replace(b, threat=card.threat,
                                 priority=card.priority))]
    if card.is_creature:
        out.append(("+body", replace(b, threat=card.threat,
                                     priority=card.priority,
                                     power=card.power,
                                     toughness=card.toughness)))
    return out


def _init(deck_name):
    _W["deck"], _W["cmd"] = build_pending(deck_name)
    _W["sim"] = SIMS[deck_name]


def _run(task):
    """One slice of one arm's games. `repl=None` is the untouched deck."""
    key, card_name, repl, turns, lo, hi = task
    deck = _W["deck"]
    if repl is not None:
        deck = list(deck)
        for i, c in enumerate(deck):
            if c.name == card_name:
                deck[i] = repl
                break
        else:
            raise KeyError(card_name)
    cfg = dict(DEFAULT_CFG, turns=turns, watch=frozenset())
    rows = [_W["sim"](deck, _W["cmd"], cfg, 5000 + i) for i in range(lo, hi)]
    keep = [m for m in WANT if m in rows[0]]
    return key, turns, lo, {m: np.array([r[m] for r in rows], float)
                            for m in keep}


def chunks(n, parts):
    step, extra = divmod(n, parts)
    lo, out = 0, []
    for k in range(parts):
        hi = lo + step + (1 if k < extra else 0)
        if hi > lo:
            out.append((lo, hi))
        lo = hi
    return out


def paired(a, b):
    """{metric: (mean, 95% CI half-width)} for a - b, as ablation.py does it."""
    return {m: ((a[m] - b[m]).mean(),
                1.96 * (a[m] - b[m]).std(ddof=1) / np.sqrt(len(a[m])))
            for m in a if m in b}


def run_deck(deck_name, names, n, procs):
    """All arms for all requested cards in one deck, one shared baseline.

    The A leg is the untouched deck and does not depend on which card is under
    test, so it is simulated once per horizon rather than once per card --
    the same hoist `ablation.py:measure_baseline()` makes, and the same games
    either way: `simulate` copies the deck it is handed and nothing in edhmc
    mutates a Card.
    """
    deck, _ = build_pending(deck_name)
    by_name = {c.name: c for c in deck}
    missing = [x for x in names if x not in by_name]
    if missing:
        raise SystemExit(f"{deck_name}: not in the deck: {missing}")

    slices = chunks(n, procs)
    tasks, arms_of = [], {}
    for turns in HORIZONS:
        for lo, hi in slices:
            tasks.append(("real", None, None, turns, lo, hi))
    for name in names:
        arms_of[name] = arms_for(by_name[name])
        for arm, repl in arms_of[name]:
            for turns in HORIZONS:
                for lo, hi in slices:
                    tasks.append((f"{name}|{arm}", name, repl, turns, lo, hi))

    parts = {}
    with Pool(procs, initializer=_init, initargs=(deck_name,)) as pool:
        for key, turns, lo, cols in pool.imap_unordered(_run, tasks):
            parts.setdefault((key, turns), {})[lo] = cols

    def cols_for(key, turns):
        got = parts[(key, turns)]
        return {m: np.concatenate([got[lo][m] for lo, _ in slices])
                for m in got[slices[0][0]]}

    for name in names:
        card = by_name[name]
        b0 = std_blank(card)
        derived = b0.power * 0.8 if b0.is_creature else b0.mv * 0.5
        print("=" * 78)
        print(f"{deck_name}: {name}")
        print(f"    real   MV {card.mv}, {card.power}/{card.toughness}, "
              f"threat {card.threat}, priority {card.priority}")
        print(f"    blank  MV {b0.mv}, {b0.power}/{b0.toughness}, "
              f"threat {derived:.1f} (derived), priority {b0.priority}")
        for turns in HORIZONS:
            real = cols_for("real", turns)
            mets = [x for x in WANT if x in real]
            print(f"\n  T{turns}" + "".join(f"{m:>24}" for m in mets))
            for arm, _ in arms_of[name]:
                cell = paired(real, cols_for(f"{name}|{arm}", turns))
                line = f"    {arm:<14}"
                for m in mets:
                    mu, ci = cell[m]
                    star = "*" if abs(mu) > ci else " "
                    p = 4 if m == "won" else 2
                    line += f"{mu:>+12.{p}f}+-{ci:<8.{p}f}{star}"
                print(line)
        print()
        sys.stdout.flush()


def main():
    argv = sys.argv[1:]
    n = 15000
    if "--n" in argv:
        i = argv.index("--n")
        n = int(argv[i + 1])
        del argv[i:i + 2]
    wanted = [a for a in argv if not a.startswith("--")]
    procs = max(1, cpu_count())

    print(f"n={n:,} paired games, seeds 5000..{5000 + n - 1}, pod v3, "
          f"build_pending() lists, {procs} procs.")
    print("Sign convention: real - blanked. POSITIVE = the card beats the "
          "blank.")
    print("'+body' is the closest row to the card's TEXT alone.\n")

    for deck_name, names in CASES.items():
        if wanted:
            if deck_name in wanted:
                pass
            else:
                names = [x for x in names if x in wanted]
                if not names:
                    continue
        run_deck(deck_name, names, n, procs)


if __name__ == "__main__":
    main()
