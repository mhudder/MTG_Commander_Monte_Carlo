#!/usr/bin/env python3
"""Did a shared-code change move a deck it was not supposed to move?

`edhmc/opponents.py` is in EVERY deck's cache fingerprint, so any edit to it
moves all six fingerprints whether or not it moves any numbers. This project
has been wrong about that distinction once already -- `regen_tables.sh`'s
header argued Karlov was unaffected by the 2026-09-05 work, which was true of
the Grist change and false of the "another creature you control" one -- so the
rule since then has been to CHECK rather than argue, with a git worktree at the
previous commit running the same seeds through both versions.

    git worktree add ../edhmc_at <ref>
    python -m tools.check_unchanged_decks --out=new.json
    (cd ../edhmc_at && python -m tools.check_unchanged_decks --out=old.json)
    python -m tools.check_unchanged_decks --diff old.json new.json --old-at=<ref>

WHICH TREES (§0z137). Each `--out` records the commit it was measured at,
whether that tree had uncommitted changes, and its N, turns and `--cfg`;
`--diff` prints both. `--old-at=<ref>` makes the comparison refuse (exit 2)
unless the old side was measured at exactly that commit, clean, with the
new side's N and turns. It exists because `git worktree add` FAILS when the
directory is already there -- left by an earlier session -- and the old
side is then measured in whatever commit that tree was left at: a diff
against a stale tree reads "MOVED" (or worse, "BIT-IDENTICAL") about the
wrong change, and nothing in the output said so.

`--include-suspended` adds the decks `edhmc/registry.py` SUSPENDS, which are
otherwise left out of both the measurement and the diff.

`--cfg=k=v,k=v` sets knobs on the side it is passed to. A change that ships
behind a knob claims the knob's OLD value reproduces the old code; running
the new tree with `--cfg=<old values>` against a worktree at the old commit
is that claim checked (2026-09-22: `decking_loss=False,
horn_doubled_legacy=True` against the commit before queued item 17).

Prints a per-metric diff. BIT-IDENTICAL is the pass condition for a deck the
change was not meant to touch; anything else means its table needs
regenerating, whatever the argument for why it should not.
"""
import json
import subprocess
import sys

from edhmc.registry import ACTIVE, DECKS as REGISTRY, SUSPENDED

# The decks a review covers. A SUSPENDED deck (edhmc/registry.py) is left out
# unless `--include-suspended` is passed -- its cache reads SUSPENDED, not
# SUSPECT, so there is nothing for this check to clear.
DECKS = ACTIVE
METRICS = ("won", "lost", "damage", "cards_drawn", "turns_played",
           "final_life", "mana_spent", "stranded_mv")


def sim_for(deck):
    return REGISTRY[deck].sim


def build(deck):
    # The deck MODULE, deliberately: this compares CODE, and a staged swap
    # is not code (see CLAUDE.md, "more than one right check").
    return REGISTRY[deck].build()


def measure(n, turns, extra=None):
    from edhmc.experiment import DEFAULT_CFG
    extra = extra or {}
    out = {}
    for deck in DECKS:
        deck_list, cmd = build(deck)
        sim = sim_for(deck)
        totals = {m: 0.0 for m in METRICS}
        for s in range(n):
            # The same seeds both sides. Not a statistical comparison: the
            # answer wanted here is "identical" or "not", not "close".
            r = sim(deck_list, cmd, dict(DEFAULT_CFG, turns=turns,
                                         watch=frozenset(), **extra),
                    3000 + s)
            for m in METRICS:
                totals[m] += float(r.get(m, 0.0))
        out[deck] = {m: totals[m] / n for m in METRICS}
        print(f"  measured {deck}", file=sys.stderr)
    return out


PROVENANCE = "_provenance"


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def provenance(n, turns, extra):
    """The tree this side was measured in: its commit, whether it had
    uncommitted changes to tracked files, and how it was measured."""
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {"commit": _git("rev-parse", "HEAD"),
            "dirty": None if status is None else bool(status),
            "n": n, "turns": turns,
            "cfg": {k: repr(v) for k, v in sorted(extra.items())}}


def resolve(ref):
    sha = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if not sha:
        raise SystemExit(f"--old-at: {ref!r} is not a commit here")
    return sha


def describe(p):
    if not p:
        return "provenance not recorded (written before §0z137)"
    commit = (p.get("commit") or "?")[:12]
    return (f"{commit}{' + UNCOMMITTED CHANGES' if p.get('dirty') else ''}"
            f"  N={p.get('n')} turns={p.get('turns')}"
            + (f"  cfg {p['cfg']}" if p.get("cfg") else ""))


def check_sides(old_p, new_p, old_at=None):
    """Why this pair of files is not a comparison of what it claims to
    compare, as a list of reasons; empty when it is. A different `--cfg` on
    the two sides is the point of `--cfg`, so it is printed, never refused."""
    bad = []
    if old_p and new_p:
        for k in ("n", "turns"):
            if old_p.get(k) != new_p.get(k):
                bad.append(f"the sides were measured at different {k}: "
                           f"{old_p.get(k)} and {new_p.get(k)}")
    if old_at is not None:
        if not old_p:
            bad.append("the old side records no commit, so --old-at cannot "
                       "be checked: re-measure it")
        else:
            if old_p.get("commit") != old_at:
                bad.append(f"the old side was measured at "
                           f"{(old_p.get('commit') or '?')[:12]}, not at "
                           f"{old_at[:12]} -- a stale worktree? `git -C "
                           f"<worktree> checkout --detach {old_at[:12]}` and "
                           f"measure it again")
            if old_p.get("dirty"):
                bad.append("the old side's tree had uncommitted changes")
    return bad


def diff(old_path, new_path, old_at=None):
    """Print the per-deck diff. Returns the reasons the two files are not a
    valid comparison (empty when they are)."""
    old = json.load(open(old_path))
    new = json.load(open(new_path))
    print(f"  old: {describe(old.get(PROVENANCE))}")
    print(f"  new: {describe(new.get(PROVENANCE))}")
    problems = check_sides(old.get(PROVENANCE), new.get(PROVENANCE), old_at)
    for why in problems:
        print(f"  !!! NOT A VALID COMPARISON: {why}")
    if problems:
        print("  !!! Nothing below is evidence about the change.")
    print()
    bad = 0
    for deck in DECKS:
        if deck not in old or deck not in new:
            print(f"  {deck:<12} not in both files, skipped")
            continue
        moved = {m: (old[deck][m], new[deck][m]) for m in METRICS
                 if old[deck][m] != new[deck][m]}
        if not moved:
            print(f"  {deck:<12} BIT-IDENTICAL on all {len(METRICS)} metrics")
            continue
        bad += 1
        print(f"  {deck:<12} MOVED on {len(moved)} of {len(METRICS)} metrics")
        for m, (a, b) in moved.items():
            print(f"      {m:<16}{a:>14.5f} ->{b:>14.5f}   {b - a:>+12.5f}")
    print(f"\n  {bad} deck(s) moved.")
    return problems


def main():
    global DECKS
    args = sys.argv[1:]
    if "--include-suspended" in args:
        DECKS = tuple(REGISTRY)
    elif SUSPENDED:
        print(f"  suspended, not checked: {', '.join(sorted(SUSPENDED))} "
              f"(--include-suspended to add them)", file=sys.stderr)
    if "--diff" in args:
        i = args.index("--diff")
        old_at = next((resolve(a.split("=", 1)[1]) for a in args
                       if a.startswith("--old-at=")), None)
        problems = diff(args[i + 1], args[i + 2], old_at)
        # Exit 0 whatever MOVED: a deck that moved is not necessarily a
        # failure -- the decks whose own engine changed are supposed to move,
        # and reading which ones did is the whole output. Exit 2 only when
        # the two files are not the comparison they claim to be (§0z137).
        return 2 if problems else 0
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), 400)
    turns = next((int(a.split("=")[1]) for a in args
                  if a.startswith("--turns=")), 20)
    out = next((a.split("=")[1] for a in args if a.startswith("--out=")),
               "baselines.json")
    extra = {}
    for a in args:
        if a.startswith("--cfg="):
            from diagnostics.run_shared_code_shift import parse_cfg
            extra = parse_cfg(a.split("=", 1)[1])
    result = measure(n, turns, extra)
    result[PROVENANCE] = provenance(n, turns, extra)
    json.dump(result, open(out, "w"), indent=1, sort_keys=True)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
