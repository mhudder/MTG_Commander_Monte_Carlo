#!/usr/bin/env python3
"""The core review's four measurements (§0z192): what decides a game in this
model, and how much of a win rate is the hand-typed `threat` number.

    python -m diagnostics.diag_core_review anatomy [N]   (default 1500)
    python -m diagnostics.diag_core_review threat  [N]   (default 3000)
    python -m diagnostics.diag_core_review rows

READ-ONLY: no knob is set and nothing is written. Games are the staged lists
(`build_pending`) of the ACTIVE decks at T20 under `DEFAULT_CFG`, seeds
5000.., the tables' own block. A rerun prints the same numbers.

  anatomy  Each deck twice: as staged ("real"), and with every NONLAND card
           replaced by a do-nothing sorcery of its cost ("nothing"), which is
           the floor a model must give a deck that does not play. Per leg:
           win / loss / timeout, the loss route, game length, and -- with
           `opponents._clock_seat` wrapped -- how many opponents were
           eliminated by ANOTHER opponent's clock, the share of wins that had
           at least one such elimination, and `your_share` at the moment a
           clock fires with three opponents alive (two rivals; 1/3 is the
           share of a board no scarier than theirs).
  threat   Paired by seed against the staged list: (a) every explicit
           `Card.threat` in a deck, the commander's included, scaled x0.5
           and x1.5; (b) ONE card's threat moved -3 and +3 (karlov, the
           cards in ONE_CARD). The difference is win rate with a 95% bar.
  rows     From the committed caches, no games: how many win-rate rows at
           T20 clear their own bar, how many of those are negative, how many
           survive Benjamini-Hochberg at 5% within the table, and the median
           absolute row.

BLIND TO, said out loud (§0z15):
  - "nothing" still casts the COMMANDER -- every engine does, by its own
    rule -- and still plays its lands; its few wins are the commander's.
  - a card whose `threat` is 0.0 is DERIVED (`opponents.threat_of`) and is
    not moved by `threat`'s scale; only hand-typed numbers are.
  - `threat` (b) is one deck and five cards at an N whose bar is about
    +-0.004: it sizes the effect, it is not a sweep (queue item 39 is).
  - `anatomy` counts a clock's victim only inside `_clock_seat`; an opponent
    your own damage finished is yours, whoever softened them.
  - `rows` reads whatever cache is on disk, CURRENT or SUSPECT.

The wrap is installed inside each worker (§0u): under a spawned pool a
module-level patch would exist in the parent only.
"""
import collections
import dataclasses
import json
import multiprocessing as mp
import os
import sys

sys.path.insert(0, os.getcwd())

SEED0 = 5000
ROUTES = {1: "life", 2: "clock", 3: "decked", 4: "paid-life"}
SCALE_DECKS = ("karlov", "rendmaw", "tivit", "azusa")
SCALES = (0.5, 1.5)
ONE_CARD = ("Blind Obedience", "Soul Warden", "Exquisite Blood", "Sol Ring",
            "Dawn of Hope")
ONE_DELTAS = (-3, +3)
CHUNK = 500


def _cfg():
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=20, watch=frozenset())


# --- anatomy ---------------------------------------------------------------

_STATE = {"wrapped": False, "kills": 0, "fires": []}


def _wrap_clock():
    """Count what `_clock_seat` does, without changing it. Idempotent."""
    import edhmc.opponents as OPP
    if _STATE["wrapped"]:
        return
    real = OPP._clock_seat

    def counting(g, i, rolls_t):
        opp = g.opponents[i]
        due = (opp.alive and not opp.clock_fired and g.result is None
               and OPP.pod_turn(g) >= opp.kill_turn)
        if due:
            others = [o for j, o in enumerate(g.opponents)
                      if j != i and o.alive]
            _STATE["fires"].append((len(others),
                                    OPP.your_share(g, opp, others)))
        before = sum(1 for o in g.opponents if o.alive)
        out = real(g, i, rolls_t)
        _STATE["kills"] += before - sum(1 for o in g.opponents if o.alive)
        return out

    OPP._clock_seat = counting
    _STATE["wrapped"] = True


def _do_nothing(deck):
    from edhmc.engine import Card
    return [c if c.is_land else
            Card(name="(blank)", types=frozenset({"Sorcery"}),
                 cost=dict(c.cost), priority=1.0) for c in deck]


def _anatomy_job(args):
    deck, leg, n = args
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    _wrap_clock()
    lst, cmd = build_pending(deck)
    if leg == "nothing":
        lst = _do_nothing(lst)
    cfg, sim = _cfg(), DECKS[deck].sim
    games, fires = [], []
    for s in range(n):
        _STATE["kills"] = 0
        _STATE["fires"] = []
        r = sim(lst, cmd, cfg, SEED0 + s)
        games.append((r["result"], r["loss_route"], r["turns_played"],
                      _STATE["kills"], r["opponents_killed"]))
        fires.extend(_STATE["fires"])
    return deck, leg, games, fires


def anatomy(n):
    from edhmc.registry import ACTIVE
    jobs = [(d, leg, n) for d in ACTIVE for leg in ("real", "nothing")]
    print(f"anatomy: N={n} a leg, T20, seeds {SEED0}..{SEED0 + n - 1}\n")
    print(f"{'deck':<11}{'leg':<9}{'win':>6}{'loss':>6}{'t/o':>6}{'turns':>7}"
          f"{'by clock':>10}{'by life':>9}{'rival kills':>13}"
          f"{'wins helped':>13}{'share@fire':>12}")
    with mp.Pool() as pool:
        for deck, leg, games, fires in pool.imap(_anatomy_job, jobs):
            res = collections.Counter(g[0] for g in games)
            wins = [g for g in games if g[0] == "win"]
            losses = [g for g in games if g[0] == "loss"]
            route = collections.Counter(g[1] for g in losses)
            dead = sum(g[4] for g in games)
            rival = sum(g[3] for g in games)
            three = [s for k, s in fires if k == 2]
            helped = sum(1 for g in wins if g[3]) / max(1, len(wins))
            print(f"{deck:<11}{leg:<9}{res['win'] / n:>6.3f}"
                  f"{res['loss'] / n:>6.3f}{res['timeout'] / n:>6.3f}"
                  f"{sum(g[2] for g in games) / n:>7.1f}"
                  f"{route[2] / max(1, len(losses)):>10.2f}"
                  f"{route[1] / max(1, len(losses)):>9.2f}"
                  f"{rival / max(1, dead):>13.2f}{helped:>13.2f}"
                  f"{sum(three) / max(1, len(three)):>12.2f}")
    print("\nby clock / by life: share of LOSSES.  rival kills: share of ALL "
          "opponent eliminations made by another opponent's clock.\n"
          "wins helped: share of WINS with at least one such elimination.  "
          "share@fire: mean `your_share` when a clock fires with three "
          "opponents alive (1/3 = a board no scarier than theirs).")


# --- threat ----------------------------------------------------------------

def _threat_job(args):
    deck, label, kind, arg, lo, hi = args
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    lst, cmd = build_pending(deck)
    if kind == "scale":
        lb = [dataclasses.replace(c, threat=c.threat * arg) if c.threat else c
              for c in lst]
        cb = (dataclasses.replace(cmd, threat=cmd.threat * arg)
              if cmd.threat else cmd)
    else:
        name, delta = arg
        if not any(c.name == name and c.threat for c in lst):
            raise KeyError(f"{name}: not in {deck}'s staged list with a "
                           f"hand-typed threat")
        lb = [dataclasses.replace(c, threat=max(0.1, c.threat + delta))
              if c.name == name else c for c in lst]
        cb = cmd
    cfg, sim = _cfg(), DECKS[deck].sim
    pairs = [(sim(lst, cmd, cfg, SEED0 + s)["won"],
              sim(lb, cb, cfg, SEED0 + s)["won"]) for s in range(lo, hi)]
    return deck, label, pairs


def threat(n):
    import numpy as np
    jobs = [(d, f"every explicit threat x{k}", "scale", k)
            for d in SCALE_DECKS for k in SCALES]
    jobs += [("karlov", f"{name}: threat {dlt:+d}", "one", (name, dlt))
             for name in ONE_CARD for dlt in ONE_DELTAS]
    chunks = [j + (lo, min(n, lo + CHUNK))
              for j in jobs for lo in range(0, n, CHUNK)]
    got = collections.defaultdict(list)
    with mp.Pool() as pool:
        for deck, label, pairs in pool.imap_unordered(_threat_job, chunks):
            got[deck, label].extend(pairs)
    print(f"threat: N={n} paired games a row, T20, seeds {SEED0}.."
          f"{SEED0 + n - 1}; B is the staged list with the threat moved\n")
    print(f"{'deck':<10}{'move':<34}{'base win':>9}{'B - A':>10}{'95%':>9}")
    for deck, label, _kind, _arg in jobs:
        d = np.array(got[deck, label], dtype=float)
        diff = d[:, 1] - d[:, 0]
        bar = 1.96 * diff.std(ddof=1) / np.sqrt(len(diff))
        mark = "  *" if abs(diff.mean()) > bar else ""
        print(f"{deck:<10}{label:<34}{d[:, 0].mean():>9.3f}"
              f"{diff.mean():>+10.4f}{bar:>9.4f}{mark}")
    print("\n* = the 95% bar excludes zero")


# --- rows ------------------------------------------------------------------

def rows():
    import numpy as np
    from scipy import stats
    import tools.ablation as AB
    from edhmc.registry import ACTIVE
    print("rows: win rate at T20, from the caches on disk\n")
    print(f"{'deck':<11}{'rows':>5}{'clear 95%':>11}{'negative':>10}"
          f"{'|z|<2.6':>9}{'pass BH 5%':>12}{'median |row|':>14}")
    for deck in ACTIVE:
        run = AB.Run(deck, 15000, (10, 20))
        with open(run.cache) as fh:
            res = json.load(fh)
        won = [v["20"]["won"] for v in res.values() if "20" in v]
        z = np.array([w / (ci / 1.96) if ci else 0.0 for w, ci in won])
        p = 2 * stats.norm.sf(abs(z))
        sig = abs(z) > 1.96
        m = len(p)
        ok = np.sort(p) <= 0.05 * np.arange(1, m + 1) / m
        bh = int(np.max(np.flatnonzero(ok)) + 1) if ok.any() else 0
        print(f"{deck:<11}{m:>5}{int(sig.sum()):>11}"
              f"{int((sig & (z < 0)).sum()):>10}"
              f"{int((sig & (abs(z) < 2.6)).sum()):>9}{bh:>12}"
              f"{np.median([abs(w) for w, _ in won]):>14.4f}")


def main(argv):
    part = argv[0] if argv else ""
    n = int(argv[1]) if len(argv) > 1 else None
    if part == "anatomy":
        anatomy(n or 1500)
    elif part == "threat":
        threat(n or 3000)
    elif part == "rows":
        rows()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
