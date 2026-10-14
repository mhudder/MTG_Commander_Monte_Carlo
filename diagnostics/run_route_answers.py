#!/usr/bin/env python3
"""Item 24's last four route answers, measured (§0z138).

    python -m diagnostics.run_route_answers                 # N=15000, POD_V4
    python -m diagnostics.run_route_answers --n=2000 --decks=tivit
    python -m diagnostics.run_route_answers --out=results/x.txt

Each piece is taken out of `experiment.POD_V4` (which carries all four,
since they are read only under `pod_threats`) and the full pod is paired
against it on the same seeds: the cell is full minus piece-off, so a
positive number is what the piece is worth to that deck. A piece a deck
does not hold is not run for it (the arm would be bit-identical). The two
knobs with no data are swept against their defaults too, said out loud:

  damn       overload_single_target=False    karlov, shilgengar, tivit
  votes      vote_answers=False               tivit
  tax        attack_tax_deflect=0.0           tivit
  gate       wipe_gate_pieces=False           every deck
  none       all four off                     every deck
  tax=0.25 / 0.75     attack_tax_deflect      tivit (default 0.5)
  gate_w=0.5 / 2.0    wipe_gate_piece_weight  every deck (default 1.0)

STAGED lists, T20 with a T10 snapshot, seeds 5000 + s.
"""
import sys
from multiprocessing import Pool

import numpy as np

from edhmc.registry import ACTIVE, DECKS as REGISTRY

N = 15000
OFF = {
    "damn": dict(overload_single_target=False),
    "votes": dict(vote_answers=False),
    "tax": dict(attack_tax_deflect=0.0),
    "gate": dict(wipe_gate_pieces=False),
    "none": dict(overload_single_target=False, vote_answers=False,
                 attack_tax_deflect=0.0, wipe_gate_pieces=False),
}
SWEEP = {
    "tax=0.25": dict(attack_tax_deflect=0.25),
    "tax=0.75": dict(attack_tax_deflect=0.75),
    "gate_w=0.5": dict(wipe_gate_piece_weight=0.5),
    "gate_w=2.0": dict(wipe_gate_piece_weight=2.0),
}
NEEDS = {"damn": {"Damn"},
         "votes": {"Council's Judgment", "Vault 11: Voter's Dilemma"},
         "tax": {"Ghostly Prison", "Propaganda"},
         "tax=0.25": {"Ghostly Prison", "Propaganda"},
         "tax=0.75": {"Ghostly Prison", "Propaganda"}}


def arms_for(deck):
    """The arms that can move this deck: a card-specific piece only where
    the deck holds the card, and the gate only where it holds a sweeper
    (azusa holds none, so its gate arms would be zero by construction)."""
    from edhmc.pending import build_pending
    cards = build_pending(deck)[0]
    names = {c.name for c in cards}
    sweeps = any("wipe" in c.tags for c in cards)
    return ["full"] + [a for a in list(OFF) + list(SWEEP)
                       if (not NEEDS.get(a) or NEEDS[a] & names)
                       and (sweeps or not a.startswith("gate"))]


def measure(args):
    deck, arm, n = args
    from edhmc.pending import build_pending
    from edhmc.experiment import DEFAULT_CFG, POD_V4
    deck_list, cmd = build_pending(deck)
    extra = OFF.get(arm) or SWEEP.get(arm) or {}
    cfg = dict(DEFAULT_CFG, turns=20, snapshot_rounds=(10,),
               watch=frozenset(), **dict(POD_V4, **extra))
    sim = REGISTRY[deck].sim
    w10, w20 = np.empty(n), np.empty(n)
    for s in range(n):
        r = sim(deck_list, cmd, cfg, 5000 + s)
        w10[s] = float(r["at_rounds"][10]["won"])
        w20[s] = float(r["won"])
    return (deck, arm), (w10, w20)


def cell(d, n):
    hw = 1.96 * d.std(ddof=1) / np.sqrt(n)
    star = "*" if hw > 0 and abs(d.mean()) > hw else " "
    return f"{d.mean():+.4f} ±{hw:.4f}{star}"


def main():
    args = sys.argv[1:]
    n = next((int(a.split("=")[1]) for a in args if a.startswith("--n=")), N)
    decks = next((a.split("=")[1].split(",") for a in args
                  if a.startswith("--decks=")), list(ACTIVE))
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")),
               None)
    jobs = [(d, a, n) for d in decks for a in arms_for(d)]
    with Pool() as pool:
        res = dict(pool.imap_unordered(measure, jobs))
    lines = [f"Item 24's last four route answers (§0z138): POD_V4, STAGED "
             f"lists, N={n} paired, seeds 5000..{5000 + n - 1}", "",
             "Off arms: full minus the arm -- what the piece is worth. Sweep "
             "arms: the arm minus full -- what moving the knob does. "
             "* = outside its 95% interval.", ""]
    for d in decks:
        f10, f20 = res[(d, "full")]
        lines.append(f"{d}   full: T10 {f10.mean():.4f}   T20 {f20.mean():.4f}")
        for a in arms_for(d)[1:]:
            a10, a20 = res[(d, a)]
            sign = 1 if a in SWEEP else -1
            lines.append(f"   {a:<11} T10 {cell(sign * (a10 - f10), n)}"
                         f"   T20 {cell(sign * (a20 - f20), n)}")
        lines.append("")
    text = "\n".join(lines) + "\n"
    print(text)
    if out:
        with open(out, "w") as fh:
            fh.write(text)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
