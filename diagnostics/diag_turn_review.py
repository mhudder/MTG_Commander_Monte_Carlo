#!/usr/bin/env python3
"""Your board as the pod's round begins: how much of it is tapped, and how
much of its power is until-end-of-turn pumps (§0z184, findings 1 and 2).

    python -m diagnostics.diag_turn_review N [DECK ...] [--out=PATH]

READ-ONLY: `opponents.pod_phase` is wrapped, every count is read before the
real round runs, and no knob is set. N games a deck at T20, seeds 5000.., the
staged list (`build_pending`). Per round, at its start:

  creatures   your creatures (`counts_as_creature` where the engine has it,
              else `is_creature_now`) -- what `combat_share` counts as blockers
  untapped    ... of which untapped: what could block (CR 508.1f, 509.1a)
  share       `combat_share`'s weight for the first living seat's attack at
              you, from each of those two counts (the other seats' boards as
              they are)
  threat      `board_threat` as the round begins, and again with the
              until-end-of-turn pumps zeroed (azusa's `eot_pt`,
              `craterhoof_bonus`, `wildspeaker_bonus`; rendmaw's
              `stampede_bonus`), which the engines reset only at their next
              untap, not at cleanup (CR 514.2)

BLIND TO: whether a creature tapped for mana or an ability rather than for an
attack (either way it cannot block), and to any pump the four attributes
above do not hold.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())

EOT_ATTRS = ("eot_pt", "craterhoof_bonus", "wildspeaker_bonus",
             "stampede_bonus")
ACTIVE = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")


def census(deck, n):
    import edhmc.opponents as OPP
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    c = Counter()
    real = OPP.pod_phase

    def weight(g, mine, rest):
        w = 1.0 / (1.0 + mine)
        return w / (w + sum(1.0 / (1.0 + o.creatures) for o in rest))

    def wrapped(g, *a, **k):
        if g.result is None:
            ask = getattr(g, "counts_as_creature", None)
            mine = [p for p in g.board
                    if (ask(p) if ask else OPP.is_creature_now(g, p))]
            unt = [p for p in mine if not p.tapped]
            c["rounds"] += 1
            c["mine"] += len(mine)
            c["untapped"] += len(unt)
            living = OPP.living(g)
            if living:
                rest = living[1:]
                c["share_all"] += weight(g, len(mine), rest)
                c["share_unt"] += weight(g, len(unt), rest)
                c["share_n"] += 1
            c["threat"] += OPP.board_threat(g)
            saved = {}
            for attr in EOT_ATTRS:
                if hasattr(g, attr):
                    saved[attr] = getattr(g, attr)
                    setattr(g, attr, {} if isinstance(saved[attr], dict)
                            else 0)
            c["threat_no_eot"] += OPP.board_threat(g)
            for attr, v in saved.items():
                setattr(g, attr, v)
        return real(g, *a, **k)

    OPP.pod_phase = wrapped
    try:
        lst, cmd = build_pending(deck)
        sim = DECKS[deck].sim
        for s in range(n):
            sim(lst, cmd, dict(DEFAULT_CFG, turns=20, watch=frozenset()),
                5000 + s)
    finally:
        OPP.pod_phase = real
    r = max(1, c["rounds"])
    sn = max(1, c["share_n"])
    return (f"{deck:11s} {c['rounds'] / n:6.2f} {c['mine'] / r:9.2f} "
            f"{c['untapped'] / r:9.2f} {c['share_all'] / sn:10.3f} "
            f"{c['share_unt'] / sn:10.3f} {c['threat'] / r:9.1f} "
            f"{c['threat_no_eot'] / r:9.1f}")


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:]
                if a.startswith("--") and "=" in a)
    if not pos:
        print(__doc__)
        return 2
    n = int(pos[0])
    decks = pos[1:] or list(ACTIVE)
    py = sys.version.split()[0]
    lines = [f"your board as the pod's round begins: N={n} a deck, T20, seeds "
             f"5000.., the staged list, python {py}", "",
             f"{'deck':11s} {'rounds':>6s} {'creatures':>9s} {'untapped':>9s} "
             f"{'share all':>10s} {'share unt':>10s} {'threat':>9s} "
             f"{'no eot':>9s}"]
    for d in decks:
        lines.append(census(d, n))
        print(lines[-1], file=sys.stderr)
    text = "\n".join(lines)
    print(text)
    out = opts.get("--out")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
