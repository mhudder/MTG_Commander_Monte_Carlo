#!/usr/bin/env python3
"""What the cleanup step discards, and what that moves (§0z171).

    python -m diagnostics.run_hand_size census N OUT.txt [DECK ...]
    python -m diagnostics.run_hand_size keys N OUT.txt [DECK ...]

`census`: N games a deck at T20, the staged list, seeds 5000.., the rule on
(`hand_size_rule`, the default): per game, the turns that end over the
maximum, the cards discarded (lands, and the mana value of the spells), the
discards Necropotence exiled, and the cards discarded most often by name --
counted by wrapping `engine.put_discarded` in each worker, the one place every
cleanup discard lands (installed in the worker's initializer, §0u).

`keys`: the same seeds, rule on minus rule off, paired, for EVERY numeric
output key: which mechanisms the discards reach. A card discarded to the
graveyard is where reanimation, regrowth, flashback, delirium and every
"cards in your graveyard" count look, so this is where the synergy shows
(and where its absence would). Keys whose 95% CI excludes 0 are printed, plus
`won` always.
"""
import os
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 250
ACTIVE = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa")
_D = {"names": Counter()}


def _init(deck):
    import edhmc.engine as EN
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    _D["deck"], _D["cmd"] = build_pending(deck)
    _D["sim"] = DECKS[deck].sim
    real = EN.put_discarded

    def counting(g, card):
        _D["names"][card.name] += 1
        return real(g, card)
    EN.put_discarded = counting


def _job(args):
    lo, hi, rule = args
    from edhmc.experiment import DEFAULT_CFG
    cfg = dict(DEFAULT_CFG, turns=20, hand_size_rule=rule)
    _D["names"].clear()
    rows = [dict(_D["sim"](_D["deck"], _D["cmd"], dict(cfg), s))
            for s in range(lo, hi)]
    return lo, rule, rows, Counter(_D["names"])


def _run(deck, n, rules):
    jobs = [(lo, r, ) for r in rules for lo in range(SEED0, SEED0 + n, CHUNK)]
    jobs = [(lo, min(lo + CHUNK, SEED0 + n), r) for lo, r in jobs]
    out, names = {r: {} for r in rules}, Counter()
    with Pool(initializer=_init, initargs=(deck,)) as pool:
        for lo, rule, rows, cnt in pool.imap_unordered(_job, jobs):
            out[rule][lo] = rows
            if rule:
                names.update(cnt)
    return ({r: sum((v[lo] for lo in sorted(v)), []) for r, v in out.items()},
            names)


def census(n, decks):
    lines = [f"§0z171 cleanup census: N={n:,} games a deck, T20, the staged "
             f"list, seeds {SEED0}.., python {sys.version.split()[0]}", ""]
    for deck in decks:
        rows, names = _run(deck, n, (True,))
        rows = rows[True]
        per = lambda k: np.mean([r.get(k, 0) for r in rows])
        turns = per("turns_played")
        lines.append(
            f"{deck:<11} turns over seven {per('cleanup_turns'):.2f} a game "
            f"({per('cleanup_turns') / turns:.1%} of {turns:.1f} turns); "
            f"discards {per('cleanup_discards'):.2f} a game "
            f"(lands {per('cleanup_lands'):.2f}, spells' mana value "
            f"{per('cleanup_mv'):.1f}); Necropotence exiled "
            f"{per('necro_discard_exiled'):.2f}; games with any "
            f"{np.mean([r.get('cleanup_discards', 0) > 0 for r in rows]):.1%}")
        top = ", ".join(f"{k} {v / n:.2f}" for k, v in names.most_common(10))
        lines.append(f"            most discarded (a game): {top}")
    return lines


def keys(n, decks):
    lines = [f"§0z171 rule on minus rule off, paired, N={n:,}, T20, seeds "
             f"{SEED0}.., python {sys.version.split()[0]}; every numeric key "
             "whose 95% CI excludes 0, and `won`", ""]
    for deck in decks:
        rows, _ = _run(deck, n, (True, False))
        on, off = rows[True], rows[False]
        ks = sorted({k for r in on + off for k, v in r.items()
                     if isinstance(v, (int, float)) and not isinstance(v, bool)})
        lines.append(f"== {deck}")
        for k in ks:
            d = np.array([float(a.get(k, 0)) - float(b.get(k, 0))
                          for a, b in zip(on, off)])
            mu = d.mean()
            ci = 1.96 * d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else 0
            if k == "won" or (ci > 0 and abs(mu) > ci) or (ci == 0 and mu):
                base = np.mean([float(b.get(k, 0)) for b in off])
                lines.append(f"  {k:<34} off {base:>9.3f}  on-off {mu:>+9.4f}"
                             f" +-{ci:.4f}{' *' if abs(mu) > ci else ''}")
        lines.append("")
    return lines


def main(argv):
    mode, n, out = argv[0], int(argv[1]), argv[2]
    decks = tuple(argv[3:]) or ACTIVE
    lines = census(n, decks) if mode == "census" else keys(n, decks)
    text = "\n".join(lines) + "\n"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
