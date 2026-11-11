#!/usr/bin/env python3
"""Queue item 39 (§0z192, finding 2): which rows rest on their `threat` number?

`threat` says how the TABLE sees a card -- how much of the pod's aim it draws
(`opponents.your_share`) -- and lower always wins more. So this is NOT a
tuning sweep and nothing here is ever adopted because it scored better (item
18 tuned `priority`, which a pilot does choose; `threat` is not the pilot's).
The question is the reverse: for which cards is the table's row a fact about
a typed constant (§0j's wording) rather than about the card's text?

A card's ablation row is (list with the card) - (list with a blank in its
slot). The blank leg does not contain the card, so moving the card's `threat`
moves its row by exactly (list, threat moved) - (list). That paired difference
is what is measured here, one card at a time, every other card as staged.

THE SURVIVOR RULE, written before the first run (§0z11, §0z170):

  screen   Every card in each ACTIVE deck's staged list with a hand-typed
           `threat` (non-zero; a 0.0 is DERIVED by `opponents.threat_of` and
           is not a typed number), the COMMANDER included, moved +3 and -3,
           one at a time. N=5,000, seeds 100000.., T20 with T10 read off the
           same game (`snapshot_rounds`, §0z93). A move SURVIVES when its T20
           win-rate 95% bar excludes zero, in either direction. About one
           move in twenty survives by chance alone, which `confirm` is for.
  confirm  Every survivor, N=15,000, on the DISJOINT block 105000.. (where
           the screen's ended), T20 and T10 off the same game. A move is
           CONFIRMED when its T20 bar excludes zero with the SAME SIGN as its
           screen row. T10 is printed beside it and is not part of the rule.
  list     A card is ON THE LIST -- its row rests on its threat -- when at
           least one of its two moves is CONFIRMED. With ~26 chance survivors
           out of ~520 moves, a 5% confirm lets about one false card through;
           a card confirmed in BOTH directions is the strong form.

  -3 IS CLAMPED AT 0.1, said out loud: 0.0 would hand the card to
  `threat_of`'s derivation, a different rule. Three staged cards sit at 3.0
  (one shilgengar, two azusa); their -3 move is 2.9.

THE A LEG IS SHARED, as in `run_priority_sweep` (whose cache, timeout and
paired statistic this reuses): every arm of one deck on one seed block is
compared with the same unmodified list on the same seeds. The tool's own A/A
control is the NOOP arm: every card that carries a threat (and the commander)
replaced by a fresh copy with the SAME threat. It must change ZERO games --
new objects through every id-keyed table the engine keeps (§0z98) -- or every
row is void. `--mutate` makes NOOP move one card's threat by +3 for real; the
gate must then fire.

    python -m diagnostics.run_threat_sweep screen  > results/threat_screen.txt
    python -m diagnostics.run_threat_sweep confirm > results/threat_confirm.txt
    python -m diagnostics.run_threat_sweep list    > results/threat_list.txt
    python -m diagnostics.run_threat_sweep screen --decks=karlov --n=200  # smoke
    python -m diagnostics.run_threat_sweep --mutate

BLIND TO, said out loud (§0z15): a card's threat moved ALONE. Two cards whose
threats are both high draw the aim together, and moving one leaves the other
-- the redundancy §0z27 warns about for rows. `diag_core_review threat`'s
whole-list scale is the other end of that, and the two between them bracket
it. The ablation's blank keeps no threat of its own (`BLANK_PRIORITY`'s blank
is a do-nothing sorcery), which is why the row moves with the card's number
at all.

Arrays are cached under results/.threat_sweep/ (git-ignored), keyed on the
deck's cache fingerprint, so a code change is never resumed onto.
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

from diagnostics.run_priority_sweep import compare, fingerprint, row_hash
from edhmc.experiment import DEFAULT_CFG
from edhmc.pending import build_pending
from edhmc.registry import ACTIVE, DECKS as REGISTRY

CACHE = os.path.join("results", ".threat_sweep")
SEED0 = 100000
CHUNK = 1250              # games per job
JOB_TIMEOUT = 1800        # seconds; §0z37
DELTA = 3.0
FLOOR = 0.1               # never 0.0: that is `threat_of`'s derived value
MUTATE = "--mutate" in sys.argv
N_DEFAULT = {"screen": 5000, "confirm": 15000}
TOP, SHORT = 20, 10       # T10 is the T20 game at round 10 (§0z93)


# ---------------------------------------------------------------- arms ------

def carriers(deck, cmd):
    """Names of every card with a hand-typed threat, the commander first."""
    names = [cmd.name] if cmd.threat else []
    return names + sorted({c.name for c in deck if c.threat} - set(names))


def card_arm(arm):
    """"card:<name>:<delta>". Split from the RIGHT: names hold colons."""
    name, d = arm[len("card:"):].rsplit(":", 1)
    return name, float(d)


def apply(deck, cmd, arm):
    """The same list with the arm's threat moved, IN PLACE (same slots, same
    objects elsewhere). NOOP copies every carrier with its threat unchanged."""
    if arm == "base":
        return deck, cmd
    if arm == "noop":
        names = set(carriers(deck, cmd))
        bump = (sorted(names)[0] if MUTATE else None)

        def f(c):
            return dataclasses.replace(
                c, threat=c.threat + (DELTA if c.name == bump else 0.0))
        return ([f(c) if c.name in names else c for c in deck],
                f(cmd) if cmd.name in names else cmd)
    name, d = card_arm(arm)

    def g(c):
        if c.name != name:
            return c
        return dataclasses.replace(c, threat=max(FLOOR, c.threat + d))
    if name != cmd.name and not any(c.name == name and c.threat for c in deck):
        raise KeyError(f"{name}: no hand-typed threat in the staged list")
    return [g(c) for c in deck], g(cmd)


# ---------------------------------------------------------------- jobs ------

def _alarm(_sig, _frm):
    raise TimeoutError(f"job exceeded {JOB_TIMEOUT}s")


def job(args):
    deck_name, arm, seed_lo, n = args
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(JOB_TIMEOUT)
    t0 = time.time()
    try:
        deck, cmd = build_pending(deck_name)
        deck, cmd = apply(deck, cmd, arm)
        cfg = dict(DEFAULT_CFG, turns=TOP, watch=frozenset(),
                   snapshot_rounds=(SHORT,))
        sim = REGISTRY[deck_name].sim
        won = np.zeros((2, n), np.int8)
        dmg = np.zeros((2, n), np.float32)
        hsh = np.zeros(n, np.uint64)
        for i in range(n):
            r = sim(deck, cmd, dict(cfg), seed_lo + i)
            s = r["at_rounds"][SHORT]
            won[0, i], dmg[0, i] = r["won"], r["damage"]
            won[1, i], dmg[1, i] = s["won"], s["damage"]
            hsh[i] = row_hash(r)
        return args, (won, dmg, hsh), time.time() - t0, None
    except Exception as e:                      # reported, never swallowed
        return args, None, time.time() - t0, f"{type(e).__name__}: {e}"
    finally:
        signal.alarm(0)


def key(deck_name, arm, seed0, n):
    arm = arm + ("|MUTATED" if MUTATE and arm == "noop" else "")
    raw = (f"threat|{deck_name}|{arm}|d{DELTA:g}|T{TOP}+{SHORT}|s{seed0}|n{n}"
           f"|{fingerprint(deck_name)}")
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def load(k):
    p = os.path.join(CACHE, k + ".npz")
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return z["won"], z["dmg"], z["hsh"]


def save(k, arrays, meta):
    os.makedirs(CACHE, exist_ok=True)
    won, dmg, hsh = arrays
    np.savez(os.path.join(CACHE, k + ".npz"), won=won, dmg=dmg, hsh=hsh)
    with open(os.path.join(CACHE, k + ".json"), "w") as f:
        json.dump(meta, f)


def run_cells(cells, procs):
    """cells: [(deck, arm, seed0, n)] -> {cell: (won, dmg, hsh)}."""
    out, todo, parts = {}, [], {}
    for cell in cells:
        got = load(key(*cell))
        if got is not None:
            out[cell] = got
            continue
        d, arm, seed0, n = cell
        chunks = [(d, arm, seed0 + lo, min(CHUNK, n - lo))
                  for lo in range(0, n, CHUNK)]
        parts[cell] = {c: None for c in chunks}
        todo += chunks
    if not todo:
        return out
    owner = {ch: cell for cell, p in parts.items() for ch in p}
    t0 = time.time()
    print(f"  simulating {len(todo)} jobs ({sum(t[3] for t in todo):,} games)"
          f" on {procs} workers", file=sys.stderr)
    failures = 0
    with Pool(procs) as pool:
        for i, (args, arrays, secs, err) in enumerate(
                pool.imap_unordered(job, todo), 1):
            cell = owner[args]
            if err:
                failures += 1
                print(f"  FAILED {args}: {err}", file=sys.stderr)
                continue
            parts[cell][args] = arrays
            if all(v is not None for v in parts[cell].values()):
                ordered = [parts[cell][c]
                           for c in sorted(parts[cell], key=lambda c: c[2])]
                arrays = (np.concatenate([o[0] for o in ordered], axis=1),
                          np.concatenate([o[1] for o in ordered], axis=1),
                          np.concatenate([o[2] for o in ordered]))
                out[cell] = arrays
                save(key(*cell), arrays,
                     dict(zip(("deck", "arm", "seed0", "n"), cell),
                          fingerprint=fingerprint(cell[0])))
            if i % 40 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} jobs, {(time.time() - t0) / 60:.1f}"
                      f" min, last {secs:.0f}s", file=sys.stderr)
    if failures:
        print(f"\n{failures} JOB(S) FAILED -- their arms are missing below, "
              f"not zero.", file=sys.stderr)
    return out


def paired(base, got, h):
    """`compare` for horizon index h (0 = T20, 1 = T10)."""
    bw, bd, bh = base
    aw, ad, ah = got
    z = np.zeros(bw.shape[1], np.int8)
    return compare((bw[h], bd[h], z, bh), (aw[h], ad[h], z, ah))


# ----------------------------------------------------------- summaries ------

def summary_path(phase, n):
    return os.path.join(CACHE, f"summary_{phase}_n{n}.json")


def read_summary(phase):
    p = summary_path(phase, N_DEFAULT[phase])
    if not os.path.exists(p):
        raise SystemExit(f"{p} missing -- run the `{phase}` phase first")
    with open(p) as f:
        return json.load(f)


def survivors(deck_name):
    return sorted(v["arm"] for v in read_summary("screen").values()
                  if v["deck"] == deck_name and v["T20"]["sig"])


def fmt(c):
    return (f"{c['win']:>+8.4f} +-{c['half']:.4f}{' *' if c['sig'] else '  '}"
            f" chg {c['changed']:>5}")


# -------------------------------------------------------------- phases ------

def phase_list():
    """The deliverable: the cards whose row rests on their threat."""
    scr = {(v["deck"], v["arm"]): v for v in read_summary("screen").values()}
    con = {(v["deck"], v["arm"]): v for v in read_summary("confirm").values()}
    print(f"threat sweep, `list`: a move is CONFIRMED when its confirm-block "
          f"T20 bar excludes zero with its screen sign (rule in the module "
          f"docstring). Delta {DELTA:g}, floor {FLOOR:g}.\n")
    total = 0
    for d in ACTIVE:
        deck, cmd = build_pending(d)
        thr = {c.name: c.threat for c in deck if c.threat}
        thr[cmd.name] = cmd.threat
        by_card = {}
        for (dd, arm), v in con.items():
            if dd != d:
                continue
            s = scr[(d, arm)]["T20"]
            ok = v["T20"]["sig"] and np.sign(v["T20"]["win"]) == np.sign(s["win"])
            if ok:
                by_card.setdefault(card_arm(arm)[0], []).append((arm, v))
        print(f"== {d}: {len(by_card)} of {len(thr)} carriers on the list, "
              f"{sum(1 for k in scr if k[0] == d)} moves screened, "
              f"{sum(1 for k in con if k[0] == d)} confirmed-phase")
        for name in sorted(by_card, key=lambda nm: -max(
                abs(v["T20"]["win"]) for _a, v in by_card[nm])):
            for arm, v in sorted(by_card[name]):
                dlt = card_arm(arm)[1]
                both = " BOTH" if len(by_card[name]) == 2 else ""
                print(f"  {name + (' (commander)' if name == cmd.name else ''):<44}"
                      f" {thr[name]:g}->{max(FLOOR, thr[name] + dlt):g}  "
                      f"T20 {fmt(v['T20'])}   T10 {fmt(v['T10'])}{both}")
        total += len(by_card)
        print()
    print(f"{total} cards on the list across {len(ACTIVE)} decks.\n")
    return phase_strict(scr, con)


def phase_strict(scr, con):
    """Queue item 39's own wording: the cards whose ROW moves by more than
    its own bar -- the T20 win-rate CI half-width in the deck's committed
    ablation cache -- under a CONFIRMED move. The commander has no row (it is
    never ablated) and every row is measured against it, so it is listed
    apart. The caches are whatever is on disk (SUSPECT ones included, item
    35): a bar is a property of N and the deck, and moves little with an
    engine fix."""
    import tools.ablation as AB
    print("STRICT: confirmed moves larger than the row's own T20 bar in the "
          "table\n")
    total = 0
    for d in ACTIVE:
        deck, cmd = build_pending(d)
        with open(AB.Run(d, 15000, (10, 20)).cache) as fh:
            res = json.load(fh)
        thr = {c.name: c.threat for c in deck if c.threat}
        thr[cmd.name] = cmd.threat
        hits = []
        for (dd, arm), v in con.items():
            s = scr[(dd, arm)]["T20"]
            if dd != d or not (v["T20"]["sig"] and np.sign(v["T20"]["win"])
                               == np.sign(s["win"])):
                continue
            name, dlt = card_arm(arm)
            w = v["T20"]["win"]
            if name == cmd.name:
                hits.append((name, dlt, w, "commander: no row; every row is "
                             "measured against it"))
            elif name in res and abs(w) > res[name]["20"]["won"][1]:
                row, bar = res[name]["20"]["won"]
                flip = (" SIGN" if abs(row) <= bar or np.sign(row + w)
                        != np.sign(row) else "")
                hits.append((name, dlt, w, f"row {row:+.4f} +-{bar:.4f}"
                             f"{flip}"))
        cards = {h[0] for h in hits} - {cmd.name}
        total += len(cards)
        print(f"== {d}: {len(cards)} rows beyond their bar")
        for name, dlt, w, note in sorted(hits, key=lambda h: -abs(h[2])):
            print(f"  {name:<44} {thr[name]:g}->{max(FLOOR, thr[name] + dlt):g}"
                  f"  {w:+.4f}   {note}")
        print()
    print(f"{total} non-commander rows beyond their own bar across "
          f"{len(ACTIVE)} decks, plus every commander. SIGN: the row is "
          f"inside its bar, or the move would carry it across zero.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if MUTATE:
        args = ["screen", "--n=200", "--decks=karlov"]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 2
    phase = args[0]
    if phase == "list":
        return phase_list()
    if phase not in N_DEFAULT:
        raise SystemExit(f"unknown phase {phase}")
    opt = dict(a[2:].split("=", 1) for a in args[1:] if "=" in a)
    decks = opt["decks"].split(",") if "decks" in opt else list(ACTIVE)
    n = int(opt.get("n", N_DEFAULT[phase]))
    procs = int(opt.get("procs", os.cpu_count() or 4))
    seed0 = SEED0 + (N_DEFAULT["screen"] if phase == "confirm" else 0)

    arms_by_deck, cells = {}, []
    for d in decks:
        deck, cmd = build_pending(d)
        if phase == "screen":
            arms = [f"card:{nm}:{s}{DELTA:g}" for nm in carriers(deck, cmd)
                    for s in "+-"]
        else:
            arms = survivors(d)
        arms_by_deck[d] = arms
        cells += [(d, a, seed0, n) for a in ["base", "noop"] + arms]
    print(f"threat sweep, phase `{phase}`. N={n:,} paired per arm, seeds "
          f"{seed0}..{seed0 + n - 1}, T{TOP} with T{SHORT} off the same game, "
          f"delta {DELTA:g} (floor {FLOOR:g}), staged lists. A leg shared per "
          f"deck.")
    print(f"{sum(map(len, arms_by_deck.values()))} arms across {len(decks)} "
          f"deck(s), plus BASE and NOOP per deck.\n")
    sys.stdout.flush()
    res = run_cells(cells, procs)

    print("THE TOOL'S OWN A/A CONTROL -- NOOP must change zero games:")
    gate = True
    for d in decks:
        b, nz = res.get((d, "base", seed0, n)), res.get((d, "noop", seed0, n))
        if b is None or nz is None:
            gate = False
            print(f"  NOOP {d:<11} MISSING")
            continue
        ch = int((b[2] != nz[2]).sum())
        print(f"  NOOP {d:<11} games changed: {ch}   "
              f"{'OK' if ch == 0 else 'VOID -- the shared baseline leaks'}")
        gate &= ch == 0
    if MUTATE:
        print("\n--mutate: NOOP moved a threat, so the gate MUST have fired: "
              + ("it did -- PASS" if not gate else "it did NOT -- FAIL"))
        return 0 if not gate else 1
    if not gate:
        print("\nNOOP CHANGED GAMES. Every row below is VOID.")
        return 1
    print()

    summary = {}
    for d in decks:
        deck, cmd = build_pending(d)
        thr = {c.name: c.threat for c in deck if c.threat}
        thr[cmd.name] = cmd.threat
        base = res[(d, "base", seed0, n)]
        rows = []
        for arm in arms_by_deck[d]:
            got = res.get((d, arm, seed0, n))
            if got is None:
                continue
            c20, c10 = paired(base, got, 0), paired(base, got, 1)
            rows.append((arm, c20, c10))
            summary[key(d, arm, seed0, n)] = dict(deck=d, arm=arm,
                                                  seed0=seed0, T20=c20,
                                                  T10=c10)
        print(f"== {d}   (base won T20 {base[0][0].mean():.4f}, "
              f"T10 {base[0][1].mean():.4f})")
        rows.sort(key=lambda r: -abs(r[1]["win"]))
        for arm, c20, c10 in rows:
            name, dlt = card_arm(arm)
            label = f"{name} {thr[name]:g}->{max(FLOOR, thr[name] + dlt):g}"
            print(f"  {label:<52} T20 {fmt(c20)}   T10 {fmt(c10)}")
        nsig = sum(1 for _a, c, _ in rows if c["sig"])
        print(f"  -> {nsig} of {len(rows)} moves exclude zero at T20; "
              f"~{0.05 * len(rows):.1f} expected by chance alone.\n")
        sys.stdout.flush()
    if n == N_DEFAULT[phase] and set(decks) == set(ACTIVE):
        os.makedirs(CACHE, exist_ok=True)
        with open(summary_path(phase, n), "w") as f:
            json.dump(summary, f, indent=1, sort_keys=True)
    else:
        print("(not the full phase: no summary written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
