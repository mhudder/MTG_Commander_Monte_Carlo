#!/usr/bin/env python3
"""Is any Card OBJECT in two zones at once? (§0z175; queue item 33)

    python -m diagnostics.diag_zone_census N [DECK ...] [--cfg=k=v,k=v]

At every pod round (`opponents.pod_phase`, wrapped in each worker's
initializer, §0u) collect `id()` of every card in the hand, the graveyard and
the library and of `p.card` for every permanent, and flag an object found in
two of them. Many token permanents sharing ONE token Card is by design --
tokens never reach the graveyard -- so battlefield + battlefield is not
counted. What is: a real card in the graveyard or hand while a permanent still
holds that object (a token copy built from it, §0z175), or a card in hand and
graveyard at once (§0z171's `remove_card` hazard).

N games a deck at T20 on seeds 5000.., the staged list (`build_pending`).
Prints, per deck, the games with any two-zone object, the zone pairs and the
card names. `--cfg` sets knobs (values read as Python literals).
"""
import ast
import os
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 250
ACTIVE = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa",
          "trostani")
_D = {}


def _init(deck, cfg):
    import edhmc.opponents as O
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    _D["deck"], _D["cmd"] = build_pending(deck)
    _D["sim"], _D["cfg"] = DECKS[deck].sim, cfg
    real = O.pod_phase

    def census(g, *a, **k):
        zones = ([("hand", c) for c in g.hand]
                 + [("graveyard", c) for c in g.graveyard]
                 + [("library", c) for c in g.library]
                 + [("battlefield", p.card) for p in g.board])
        seen = {}
        for zone, c in zones:
            seen.setdefault(id(c), (c.name, set()))[1].add(zone)
        for name, zs in seen.values():
            if len(zs) > 1:
                _D["pairs"]["+".join(sorted(zs))] += 1
                _D["names"][name] += 1
                _D["bad"] = True
        return real(g, *a, **k)
    O.pod_phase = census


def _job(args):
    lo, hi = args
    from edhmc.experiment import DEFAULT_CFG
    _D["pairs"], _D["names"], games = Counter(), Counter(), 0
    for s in range(lo, hi):
        _D["bad"] = False
        _D["sim"](_D["deck"], _D["cmd"],
                  dict(DEFAULT_CFG, turns=20, **_D["cfg"]), s)
        games += _D["bad"]
    return games, _D["pairs"], _D["names"]


def main(argv):
    cfg = {}
    for a in list(argv):
        if a.startswith("--cfg="):
            for kv in a.split("=", 1)[1].split(","):
                k, v = kv.split("=", 1)
                try:
                    cfg[k] = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    cfg[k] = v
            argv.remove(a)
    n = int(argv[0])
    decks = tuple(argv[1:]) or ACTIVE
    print(f"zone census: N={n:,} games a deck, T20, seeds {SEED0}.., "
          f"cfg {cfg}, python {sys.version.split()[0]}")
    total = 0
    for deck in decks:
        jobs = [(lo, min(lo + CHUNK, SEED0 + n))
                for lo in range(SEED0, SEED0 + n, CHUNK)]
        games, pairs, names = 0, Counter(), Counter()
        with Pool(initializer=_init, initargs=(deck, cfg)) as pool:
            for g_, p_, n_ in pool.imap_unordered(_job, jobs):
                games += g_
                pairs.update(p_)
                names.update(n_)
        # battlefield + battlefield alone is shared token Cards, by design
        pairs = Counter({k: v for k, v in pairs.items()
                         if k != "battlefield"})
        total += games
        print(f"  {deck:<11} games with an object in two zones: {games:>5}"
              f"  {dict(pairs) or ''}  {dict(names.most_common(6)) or ''}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
