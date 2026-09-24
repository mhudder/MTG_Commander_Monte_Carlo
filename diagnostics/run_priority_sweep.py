#!/usr/bin/env python3
"""Queued item 18's second half: are the `priority` numbers right?

§0z43 built the one-card cast lookahead and measured it as a null in all
twelve deck-horizon cells, which settled that the casting ORDER is not the
leak. What it left is the claim item 18 always made: every deck's `priority`
numbers were tuned while which land got tapped was effectively arbitrary
(§0z8), and nobody has re-tuned them since. `priority` is the only lever that
decides §0z8's own case -- Voice of the Blessed {W}{W} at 7 over Lurrus
{1}{W}{B} at 6 -- because the two cannot both be cast.

WHAT `priority` MEANS IN THIS ENGINE, said before measuring it. It is not only
the cast order in `main_phase`. The same number ranks lorehold's recursion
picks, tivit's pool picks and the sacrifice-to-cast chooser in
`engine.py`. A move here changes every decision that reads it, which is what
the number means; it is said so nobody reads a row as "cast order alone".
Rendmaw adds `+3` to a `ramp` card through turn 5 and that is left alone. The
COMMANDER is never moved: every engine casts it by its own rule.

THE DESIGN IS TRIAGE, because the naive version costs ~40 CPU-hours
(docs/TRIAGE.md: screen cheap, escalate N only for survivors).

  lever    Is the table worth tuning at all? Two whole-table replacements
           against the tuned numbers, N=15,000, both horizons:
             FLAT      every nonland card at the deck's median priority, so
                       the MV tie-break decides ("cast the biggest thing")
             REVERSED  p -> (min + max) - p
           If FLAT costs nothing, per-card tuning cannot find anything.
  screen   Every nonland card moved +DELTA and -DELTA, one at a time.
           N=5,000, T20 only, seeds 1234.. . A survivor is a row whose 95%
           bar excludes zero -- about one row in twenty survives by chance,
           which is what `confirm` is for.
  confirm  Every survivor, N=15,000, BOTH horizons, on a DISJOINT seed block
           (seeds start where the screen's ended), so the selection the
           screen made cannot bias the number that decides.
  joint    Every confirmed move applied together, N=15,000, both horizons,
           on a THIRD seed block that neither selection step has seen.
           Priorities are a RANKING, so two moves interact; the joint row is
           the one an adoption would rest on.

  mechanism  Each confirmed move, and the joint, through `run_ab` itself at
           N=3,000, T20, reporting the deck's own table counters plus a few
           per-deck extras and the share of games won by each WIN ROUTE. It
           exists because a confirmed number whose mechanism nobody can name
           is not a result yet. It uses the confirm block's seeds.

DELTA = 2 IS A JUDGEMENT, said out loud: on a 1-10 scale with 10-14 distinct
levels per deck, two points crosses a few tiers without sending a card to the
top or bottom outright. `--delta=` changes it.

THE A LEG IS SHARED. Every arm of one deck at one horizon on one seed block is
compared with the same unmodified list on the same seeds, so the baseline is
simulated ONCE rather than once per arm (`run_ab` would do it 130 times). That
is only sound if nothing in a game reads `cfg["watch"]` except a counter --
checked by grep on 2026-09-24 -- AND it is checked by the tool itself: the
first arm of every run is NOOP, a card replaced by an identical copy, and it
must change ZERO games. If it does not, every row below it is void and the run
says so.

WHAT IS STORED. Per arm and per game: won, damage, and a hash of every metric
that is not a watch counter -- so "games changed" is exact, not inferred from
win rate. Arrays go to results/.priority_sweep/ (git-ignored, keyed on the
deck's cache fingerprint from tools.cache_manifest, so a code change can never
be resumed onto) and the run resumes from them.

    python -m diagnostics.run_priority_sweep lever   > results/priority_lever.txt
    python -m diagnostics.run_priority_sweep screen  > results/priority_screen.txt
    python -m diagnostics.run_priority_sweep confirm > results/priority_confirm.txt
    python -m diagnostics.run_priority_sweep joint   > results/priority_joint.txt
    python -m diagnostics.run_priority_sweep mechanism > results/priority_mechanism.txt
    python -m diagnostics.run_priority_sweep screen --decks=karlov --n=200  # smoke
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import signal
import sys
import time
from multiprocessing import Pool

import numpy as np

from edhmc.experiment import DEFAULT_CFG, analyse
from edhmc.pending import build_pending
from edhmc.registry import DECKS as REGISTRY

CACHE = os.path.join("results", ".priority_sweep")
SEED0 = 1234
CHUNK = 2500              # games per job; one leg, one horizon
JOB_TIMEOUT = 1800        # seconds; §0z37 -- a hung job is a failure, not a slow one
DELTA = 2.0
# `--mutate`: NOOP moves its card for real. The run must then report the gate
# as fired (exit 0) -- a gate that cannot fail certifies nothing.
MUTATE = "--mutate" in sys.argv
N_DEFAULT = {"lever": 15000, "screen": 5000, "confirm": 15000, "joint": 15000,
             "mechanism": 3000}
HORIZONS = {"lever": (10, 20), "screen": (20,), "confirm": (10, 20),
            "joint": (10, 20), "mechanism": (20,)}
# Counters worth reading beside the table's own, per deck, for `mechanism`.
EXTRA_METRICS = {
    "karlov": ("life_gained", "combo_assembled"),
    "tivit": ("token_drain", "treasures_made", "extra_turns", "cards_drawn"),
}
# Metrics that differ between the legs because the B leg WATCHES a card, not
# because the game differed. Everything else goes into the per-game hash.
WATCH_KEYS = ("cast_test_card", "test_card_")


# ---------------------------------------------------------------- arms ------

def nonland(deck):
    return [c for c in deck if not c.is_land]


def apply_moves(deck, moves: dict):
    """The same list with some priorities changed, IN PLACE -- same slots,
    same objects everywhere else, so CRN pairs every other card exactly."""
    return [dataclasses.replace(c, priority=moves[c.name])
            if c.name in moves else c for c in deck]


def card_arm(arm: str) -> tuple[str, float]:
    """"card:<name>:<delta>" -> (name, delta). Split from the RIGHT: a card
    name can contain a colon ("Vault 11: Voter's Dilemma"), and splitting from
    the left crashed the first screen on exactly that card."""
    name, d = arm[len("card:"):].rsplit(":", 1)
    return name, float(d)


def arm_moves(deck, arm: str) -> dict:
    """Arm label -> {card name: new priority}. Labels:
         base | noop | flat | reversed | card:<name>:<+d|-d> | joint:<json>"""
    nl = nonland(deck)
    ps = [c.priority for c in nl]
    if arm == "base":
        return {}
    if arm == "noop":
        # --mutate makes NOOP a real move, and the gate MUST then fire.
        c = max(nl, key=lambda c: c.priority)
        return {c.name: c.priority - (6.0 if MUTATE else 0.0)}
    if arm == "flat":
        med = float(np.median(ps))
        return {c.name: med for c in nl}
    if arm == "reversed":
        lo, hi = min(ps), max(ps)
        return {c.name: lo + hi - c.priority for c in nl}
    if arm.startswith("card:"):
        name, d = card_arm(arm)
        c = next(c for c in nl if c.name == name)
        return {name: c.priority + d}
    if arm.startswith("joint:"):
        return json.loads(arm[len("joint:"):])
    raise KeyError(arm)


def watched(deck, arm: str) -> frozenset:
    """NOOP watches EVERY nonland card: that exercises every `watch` read site
    in the engine at once, so a zero there is the evidence that the shared,
    unwatched A leg is the A leg `run_ab` would have simulated."""
    if arm.startswith("card:"):
        return frozenset([card_arm(arm)[0]])
    if arm == "noop":
        return frozenset(c.name for c in nonland(deck))
    return frozenset()


# ---------------------------------------------------------------- jobs ------

def row_hash(r: dict) -> int:
    items = sorted((k, repr(v)) for k, v in r.items()
                   if not k.startswith(WATCH_KEYS))
    return int.from_bytes(hashlib.blake2b(repr(items).encode(),
                                          digest_size=8).digest(), "little")


def _alarm(_sig, _frm):
    raise TimeoutError(f"job exceeded {JOB_TIMEOUT}s")


def job(args):
    deck_name, arm, turns, seed_lo, n = args
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(JOB_TIMEOUT)
    t0 = time.time()
    try:
        deck, cmd = build_pending(deck_name)
        cfg = dict(DEFAULT_CFG, turns=turns, watch=watched(deck, arm))
        deck = apply_moves(deck, arm_moves(deck, arm))
        sim = REGISTRY[deck_name].sim
        won = np.zeros(n, np.int8)
        dmg = np.zeros(n, np.float32)
        cast = np.zeros(n, np.int8)
        hsh = np.zeros(n, np.uint64)
        for i in range(n):
            r = sim(deck, cmd, dict(cfg), seed_lo + i)
            won[i] = r["won"]
            dmg[i] = r["damage"]
            cast[i] = r.get("cast_test_card", 0)
            hsh[i] = row_hash(r)
        return args, (won, dmg, cast, hsh), time.time() - t0, None
    except Exception as e:                      # reported, never swallowed
        return args, None, time.time() - t0, f"{type(e).__name__}: {e}"
    finally:
        signal.alarm(0)


# --------------------------------------------------------------- cache ------

_FP = {}


def fingerprint(deck_name: str) -> str:
    if deck_name not in _FP:
        from tools.cache_manifest import fingerprint as fp
        _FP[deck_name] = fp(deck_name)[0]
    return _FP[deck_name]


def key(deck_name, arm, turns, seed0, n) -> str:
    arm = arm + ("|MUTATED" if MUTATE and arm == "noop" else "")
    raw = f"{deck_name}|{arm}|T{turns}|s{seed0}|n{n}|{fingerprint(deck_name)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def load(k):
    p = os.path.join(CACHE, k + ".npz")
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return z["won"], z["dmg"], z["cast"], z["hsh"]


def save(k, arrays, meta):
    os.makedirs(CACHE, exist_ok=True)
    won, dmg, cast, hsh = arrays
    np.savez(os.path.join(CACHE, k + ".npz"), won=won, dmg=dmg, cast=cast,
             hsh=hsh)
    with open(os.path.join(CACHE, k + ".json"), "w") as f:
        json.dump(meta, f)


def run_arms(cells, procs):
    """cells: [(deck, arm, turns, seed0, n)]. Simulates what is not cached,
    in CHUNK-game jobs, and returns {cell: arrays}."""
    out, todo, parts = {}, [], {}
    for cell in cells:
        k = key(*cell)
        got = load(k)
        if got is not None:
            out[cell] = got
            continue
        deck_name, arm, turns, seed0, n = cell
        chunks = [(deck_name, arm, turns, seed0 + lo, min(CHUNK, n - lo))
                  for lo in range(0, n, CHUNK)]
        parts[cell] = {c: None for c in chunks}
        todo += chunks
    if not todo:
        return out
    owner = {ch: cell for cell, d in parts.items() for ch in d}
    t0 = time.time()
    print(f"  simulating {len(todo)} jobs ({sum(t[4] for t in todo):,} games, "
          f"one leg each) on {procs} workers", file=sys.stderr)
    failures = []
    with Pool(procs) as pool:
        for i, (args, arrays, secs, err) in enumerate(
                pool.imap_unordered(job, todo), 1):
            cell = owner[args]
            if err:
                failures.append((args, err))
                print(f"  FAILED {args}: {err}", file=sys.stderr)
                continue
            parts[cell][args] = arrays
            if all(v is not None for v in parts[cell].values()):
                ordered = [parts[cell][c] for c in sorted(parts[cell],
                                                          key=lambda c: c[3])]
                arrays = tuple(np.concatenate([o[j] for o in ordered])
                               for j in range(4))
                out[cell] = arrays
                save(key(*cell), arrays,
                     dict(zip(("deck", "arm", "turns", "seed0", "n"), cell),
                          fingerprint=fingerprint(cell[0])))
            if i % 20 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  {i}/{len(todo)} jobs, {el/60:.1f} min elapsed, "
                      f"last job {secs:.0f}s", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} JOB(S) FAILED -- their arms are missing "
              f"below, not zero.", file=sys.stderr)
    return out


# ------------------------------------------------------------ analysis ------

def compare(base, arm):
    """Paired B - A on the shared seeds, through experiment.analyse so the CI
    is the project's own bootstrap and not a second implementation of it."""
    bw, bd, _bc, bh = base
    aw, ad, ac, ah = arm
    rows_a = [{"won": int(w), "damage": float(d)} for w, d in zip(bw, bd)]
    rows_b = [{"won": int(w), "damage": float(d)} for w, d in zip(aw, ad)]
    res = {r.metric: r for r in analyse(rows_a, rows_b,
                                        metrics=("won", "damage"))}
    return dict(win=float(res["won"].mean_diff),
                half=float((res["won"].ci_high - res["won"].ci_low) / 2),
                sig=bool(res["won"].significant),
                dmg=float(res["damage"].mean_diff),
                dmg_sig=bool(res["damage"].significant),
                changed=int((bh != ah).sum()), n=len(bw),
                cast=float(ac.mean()), base_win=float(bw.mean()))


def fmt(c):
    star = " *" if c["sig"] else "  "
    return (f"{c['win']:>+8.4f} +-{c['half']:.4f}{star} "
            f"dmg {c['dmg']:>+6.2f}{'*' if c['dmg_sig'] else ' '} "
            f"chg {c['changed']:>5}")


def noop_gate(results, cells) -> bool:
    """The tool's own A/A control. A NOOP arm that changes a game means the
    shared baseline is not the A leg run_ab would have simulated."""
    ok = True
    for cell in cells:
        if cell[1] != "noop" or cell not in results:
            continue
        base = results.get((cell[0], "base") + cell[2:])
        if base is None:
            continue
        changed = int((base[3] != results[cell][3]).sum())
        mark = "OK" if changed == 0 else "VOID -- the shared baseline leaks"
        print(f"  NOOP {cell[0]:<11} T{cell[2]}  games changed: {changed}   "
              f"{mark}")
        ok &= changed == 0
    return ok


# -------------------------------------------------------------- phases ------

def phase_cells(phase, decks, n, delta, horizons):
    cells, arms_by_deck = [], {}
    # Three seed blocks, never overlapping: the screen SELECTED on the first
    # and the confirmation selected on the second, so the joint row -- the
    # number an adoption rests on -- is measured on seeds neither has seen.
    seed0 = {"confirm": SEED0 + N_DEFAULT["screen"],
             "joint": SEED0 + N_DEFAULT["screen"] + N_DEFAULT["confirm"],
             }.get(phase, SEED0)
    for d in decks:
        deck, _cmd = build_pending(d)
        if phase == "lever":
            arms = ["flat", "reversed"]
        elif phase == "screen":
            arms = [f"card:{c.name}:{s}{delta:g}" for c in nonland(deck)
                    for s in "+-"]
        elif phase == "confirm":
            arms = survivors(d, delta)
        elif phase == "joint":
            moves = confirmed_moves(d, delta)
            arms = [f"joint:{json.dumps(moves, sort_keys=True)}"] if moves else []
        else:
            raise SystemExit(f"unknown phase {phase}")
        arms_by_deck[d] = arms
        for t in horizons:
            for a in ["base", "noop"] + arms:
                cells.append((d, a, t, seed0, n))
    return cells, arms_by_deck, seed0


def summary_path(phase, n):
    """Keyed on N as well as phase, so a smoke run's rows can never be read
    as the screen's survivors."""
    return os.path.join(CACHE, f"summary_{phase}_n{n}.json")


def write_summary(phase, n, rows):
    os.makedirs(CACHE, exist_ok=True)
    old = {}
    if os.path.exists(summary_path(phase, n)):
        with open(summary_path(phase, n)) as f:
            old = json.load(f)
    old.update(rows)
    with open(summary_path(phase, n), "w") as f:
        json.dump(old, f, indent=1, sort_keys=True)


def read_summary(phase, n=None):
    p = summary_path(phase, n or N_DEFAULT[phase])
    if not os.path.exists(p):
        raise SystemExit(f"{p} missing -- run the `{phase}` phase first")
    with open(p) as f:
        return json.load(f)


def survivors(deck_name, delta):
    """Screen rows whose bar excluded zero, IN EITHER DIRECTION -- a
    significantly negative move is confirmed too, because "the current number
    beats this move" is also a finding about the number."""
    steps = (f"+{delta:g}", f"-{delta:g}")
    return sorted(v["arm"] for v in read_summary("screen").values()
                  if v["deck"] == deck_name and v["sig"]
                  and v["arm"].rsplit(":", 1)[-1] in steps)


def confirmed_moves(deck_name, delta):
    """A move is CONFIRMED when its confirm-phase row is significant at BOTH
    horizons with the same sign as its screen row -- the project's staging
    bar. Only positive moves are adopted: a confirmed negative says the
    current number is better than that move, which is not a move to make."""
    s = read_summary("confirm")
    by_arm = {}
    for v in s.values():
        if v["deck"] == deck_name:
            by_arm.setdefault(v["arm"], {})[v["turns"]] = v
    deck, _ = build_pending(deck_name)
    moves = {}
    for arm, cells in by_arm.items():
        if all(t in cells and cells[t]["sig"] and cells[t]["win"] > 0
               for t in (10, 20)):
            moves.update(arm_moves(deck, arm))
    return moves


def phase_mechanism(decks, n, delta, procs) -> int:
    """Each confirmed move alone, then the joint, via run_ab -- so this phase
    is also a second, independent route to the confirm phase's sign."""
    seed0 = SEED0 + N_DEFAULT["screen"]
    jobs = []
    for d in decks:
        deck, _ = build_pending(d)
        moves = confirmed_moves(d, delta)
        if not moves:
            continue
        for name, pr in sorted(moves.items()):
            jobs.append((d, {name: pr}, n, seed0))
        if len(moves) > 1:
            jobs.append((d, moves, n, seed0))
    print(f"priority sweep, phase `mechanism`. N={n:,} paired via run_ab, "
          f"T20, seeds {seed0}.. . win_route_k = share of games WON by "
          f"route k (karlov: 2 combo, 3 Felidar, 4 Aetherflux; tivit: 1 "
          f"combat, 2 Revel, 3 Mechanized, 4 drain, 5 Torment, 6 Time "
          f"Sieve; 0 = damage/other).\n")
    with Pool(procs) as pool:
        for d, moves, rows in pool.imap(_mech_job, jobs):
            deck, _ = build_pending(d)
            pri = {c.name: c.priority for c in nonland(deck)}
            print(f"== {d}: " + "; ".join(f"{k} {pri[k]:g}->{v:g}"
                                          for k, v in sorted(moves.items())))
            for metric, diff, lo, hi, sig in rows:
                print(f"    {metric:<20}{diff:>+9.4f}  [{lo:>+8.4f}, "
                      f"{hi:>+8.4f}]{' *' if sig else '  '}")
            print()
            sys.stdout.flush()
    return 0


def _mech_job(args):
    d, moves, n, seed0 = args
    from edhmc.experiment import run_ab
    deck, cmd = build_pending(d)
    names = sorted(moves)
    new = apply_moves(deck, moves)
    ins = [next(c for c in new if c.name == nm) for nm in names]
    ra, rb, _cfg = run_ab(deck, cmd, names, ins, n=n, turns=20,
                          base_seed=seed0, sim=REGISTRY[d].sim)
    routes = sorted({r["win_route"] for r in ra + rb if r["won"]})
    for rows in (ra, rb):
        for r in rows:
            for k in routes:
                r[f"win_route_{k}"] = int(bool(r["won"]) and r["win_route"] == k)
    metrics = (tuple(REGISTRY[d].metrics) + EXTRA_METRICS.get(d, ())
               + tuple(f"win_route_{k}" for k in routes))
    res = analyse(ra, rb, metrics=metrics)
    return d, moves, [(r.metric, r.mean_diff, r.ci_low, r.ci_high,
                       r.significant) for r in res]


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 2
    phase = args[0]
    opt = dict(a[2:].split("=", 1) for a in args[1:] if "=" in a)
    if MUTATE:
        phase = "lever"                         # cheapest arms; only NOOP matters
    decks = opt["decks"].split(",") if "decks" in opt else list(REGISTRY)
    n = int(opt.get("n", N_DEFAULT[phase]))
    delta = float(opt.get("delta", DELTA))
    procs = int(opt.get("procs", os.cpu_count() or 4))
    horizons = HORIZONS[phase]
    if phase == "mechanism":
        return phase_mechanism(decks, n, delta, procs)

    cells, arms_by_deck, seed0 = phase_cells(phase, decks, n, delta, horizons)
    print(f"priority sweep, phase `{phase}`. N={n:,} paired per arm, seeds "
          f"{seed0}..{seed0 + n - 1}, horizons {horizons}, delta {delta:g}, "
          f"staged lists (build_pending). A leg shared per deck/horizon.")
    print(f"{sum(len(a) for a in arms_by_deck.values())} arms across "
          f"{len(decks)} deck(s), plus BASE and NOOP per deck/horizon.\n")
    sys.stdout.flush()
    results = run_arms(cells, procs)

    print("THE TOOL'S OWN A/A CONTROL -- NOOP must change zero games:")
    gate = noop_gate(results, cells)
    if MUTATE:
        print("\n--mutate: NOOP moved its card, so the gate MUST have fired: "
              + ("it did -- PASS" if not gate else "it did NOT -- FAIL"))
        return 0 if not gate else 1
    if not gate:
        print("\nNOOP CHANGED GAMES. Every row below is VOID.")
        return 1
    print()

    summary = {}
    for d in decks:
        deck, _ = build_pending(d)
        pri = {c.name: c.priority for c in nonland(deck)}
        rows = []
        for arm in arms_by_deck[d]:
            per_t = {}
            for t in horizons:
                base = results.get((d, "base", t, seed0, n))
                got = results.get((d, arm, t, seed0, n))
                if base is None or got is None:
                    continue
                c = compare(base, got)
                per_t[t] = c
                summary[key(d, arm, t, seed0, n)] = dict(
                    c, deck=d, arm=arm, turns=t, seed0=seed0)
            rows.append((arm, per_t))
        if not rows:
            print(f"== {d}: nothing to measure in this phase\n")
            continue
        base_line = ", ".join(
            f"T{t} base won {results[(d, 'base', t, seed0, n)][0].mean():.4f}"
            for t in horizons if (d, "base", t, seed0, n) in results)
        print(f"== {d}   ({base_line})")
        if phase == "screen":
            rows.sort(key=lambda r: -abs(r[1].get(20, {}).get("win", 0)))
        for arm, per_t in rows:
            label = arm
            if arm.startswith("card:"):
                name, dd = card_arm(arm)
                label = f"{name} {pri[name]:g}->{pri[name] + dd:g}"
            elif arm.startswith("joint:"):
                mv = json.loads(arm[len("joint:"):])
                label = "JOINT " + "; ".join(
                    f"{k} {pri[k]:g}->{v:g}" for k, v in sorted(mv.items()))
            cols = "   ".join(f"T{t} {fmt(per_t[t])}" for t in horizons
                              if t in per_t)
            if arm.startswith("card:"):
                cast = per_t.get(horizons[-1], {}).get("cast", 0)
                cols += f"   cast {cast:.3f}"
            print(f"  {label:<58} {cols}")
        if phase == "screen":
            nsig = sum(1 for _a, pt in rows if pt.get(20, {}).get("sig"))
            print(f"  -> {nsig} of {len(rows)} rows exclude zero at 95%; "
                  f"~{0.05 * len(rows):.1f} expected by chance alone.")
        print()
        sys.stdout.flush()
    write_summary(phase, n, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
