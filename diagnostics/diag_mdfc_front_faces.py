#!/usr/bin/env python3
"""What does an MDFC's FRONT face do when it is cast? (§0z249)

    python -m diagnostics.diag_mdfc_front_faces N [DECK ...] [--turns=T]

Every card of the staged list (`build_pending`) with `land_face` set and
`is_land` False is a modal double-faced card cast for its spell face. For
each, over N games at T20 (or `--turns=T`; `DEFAULT_CFG` alone plays 10) on
seeds 5000.., this counts, per card:

  cast        spells reported to `opponents.countered` (the one place every
              engine reports a cast, §0z30), and how many were countered
  resolved    resolutions through the engine's own resolve
              (`ShilgengarGame.resolve`, `lorehold.resolve_spell`,
              `karlov.resolve`, `tivit.resolve`, the azusa and trostani
              methods). Rendmaw resolves inline in `engine.main_phase`, so
              its row reads `cast - countered` there.
  blank       resolutions after which a FINGERPRINT of the game is unchanged
              except the card itself moving to the graveyard: your board,
              tokens, life, hand, library, Treasures, every opponent's life,
              creatures and route pieces. Not taken for rendmaw (no resolve
              call to wrap); its answer row is the evidence there.
  answer      `opponents.answer_pod_threat`'s pieces removed at cast, and
              its whiffs (cast, 0 removed)
  response    casts from hand in a pod-turn window (`_cast_response`): a
              protection spell, an instant answer at a landing piece or at
              the end step. These do not reach `countered`.
              A cast TRIGGER (prowess, Guttersnipe, magecraft) changes the
              fingerprint, so `blank` is a FLOOR on resolutions where the
              card's own text did nothing: read `via` and the code too.
  via         which function called the resolve, per resolution
  life        life charged by `opponents.spell_life_loss` at resolution
  land face   the card played as its land face (`engine.play_land`, which
              every engine with an MDFC calls, builds a "<name> (land)" Card)

Installed in each worker's initializer (§0u). Prints one row per card.
"""
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 100
ACTIVE = ("rendmaw", "lorehold", "karlov", "tivit", "shilgengar", "azusa",
          "trostani")
_D = {}


def _fingerprint(g):
    import edhmc.opponents as O
    opp = tuple((round(o.life, 6), round(o.creatures, 6),
                 len(O.present_pieces(g, o)) if hasattr(o, "pieces") else 0)
                for o in g.opponents)
    board = tuple(sorted((p.card.name, p.is_token, bool(p.tapped))
                         for p in g.board))
    return (board, round(g.your_life, 6), len(g.hand), len(g.library),
            getattr(g, "treasures", 0), opp,
            tuple(sorted(c.name for c in g.graveyard)))


def _wrap_resolve(fn, get_g, get_card):
    def wrapped(*a, **k):
        g, card = get_g(a, k), get_card(a, k)
        if card is None or card.name not in _D["names"]:
            return fn(*a, **k)
        before = _fingerprint(g)
        out = fn(*a, **k)
        after = _fingerprint(g)
        row = _D["rows"][card.name]
        row["resolved"] += 1
        row["via_" + sys._getframe(1).f_code.co_name] += 1
        # The card itself going to the graveyard is not an effect.
        b = list(before)
        b[6] = tuple(sorted(list(before[6]) + [card.name]))
        if tuple(b) == after or before == after:
            row["blank"] += 1
        return out
    return wrapped


def _init(deck):
    import edhmc.opponents as O
    from edhmc.pending import build_pending
    from edhmc.registry import DECKS
    _D["deck"], _D["cmd"] = build_pending(deck)
    _D["sim"] = DECKS[deck].sim
    _D["names"] = {c.name for c in _D["deck"]
                   if c.land_face and not c.is_land}
    _D["engine"] = deck

    real_countered = O.countered

    def countered(g, card, idx):
        out = real_countered(g, card, idx)
        if card.name in _D["names"]:
            row = _D["rows"][card.name]
            row["cast"] += 1
            row["countered"] += bool(out)
        return out
    O.countered = countered

    real_answer = O.answer_pod_threat

    def answer(g, card):
        done = real_answer(g, card)
        if card.name in _D["names"] and card.name in O.ANSWERS:
            row = _D["rows"][card.name]
            row["answer_cast"] += 1
            row["answer_pieces"] += done
            row["answer_whiffs"] += not done
        return done
    O.answer_pod_threat = answer

    real_resp = O._cast_response

    def resp(g, card, kind):
        ok = real_resp(g, card, kind)
        if ok and card.name in _D["names"]:
            _D["rows"][card.name][f"response_{kind}"] += 1
        return ok
    O._cast_response = resp

    real_life = O.spell_life_loss

    def life(g, card):
        before = g.your_life
        real_life(g, card)
        if card.name in _D["names"]:
            _D["rows"][card.name]["life"] += before - g.your_life
    O.spell_life_loss = life

    import edhmc.engine as E
    real_land = E.play_land

    def play_land(g, *a, **k):
        faces = {n + " (land)" for n in _D["names"]}
        before = sum(1 for p in g.board if p.card.name in faces)
        out = real_land(g, *a, **k)
        for p in g.board[-1:]:
            if p.card.name in faces and sum(
                    1 for q in g.board if q.card.name in faces) > before:
                _D["rows"][p.card.name[:-7]]["land_face"] += 1
        return out
    E.play_land = play_land
    import importlib
    for mod in ACTIVE:
        M = importlib.import_module(f"edhmc.{mod if mod != 'rendmaw' else 'engine'}")
        if getattr(M, "play_land", None) is real_land:
            M.play_land = play_land

    first = lambda a, k: a[0]                       # noqa: E731
    second = lambda a, k: a[1] if len(a) > 1 else k.get("card")  # noqa: E731
    if deck == "shilgengar":
        import edhmc.shilgengar as S
        S.ShilgengarGame.resolve = _wrap_resolve(
            S.ShilgengarGame.resolve, first, second)
    elif deck == "lorehold":
        import edhmc.lorehold as L
        L.resolve_spell = _wrap_resolve(L.resolve_spell, first, second)
    elif deck in ("karlov", "tivit"):
        import importlib
        M = importlib.import_module(f"edhmc.{deck}")
        M.resolve = _wrap_resolve(M.resolve, first, second)
    elif deck in ("azusa", "trostani"):
        import importlib
        M = importlib.import_module(f"edhmc.{deck}")
        cls = next(v for k, v in vars(M).items()
                   if isinstance(v, type) and k.endswith("Game")
                   and "resolve" in vars(v))
        cls.resolve = _wrap_resolve(cls.resolve, first, second)


def _job(args):
    lo, hi, turns = args
    from edhmc.experiment import DEFAULT_CFG
    _D["rows"] = defaultdict(Counter)
    for s in range(lo, hi):
        _D["sim"](_D["deck"], _D["cmd"], dict(DEFAULT_CFG, turns=turns), s)
    return {k: dict(v) for k, v in _D["rows"].items()}


def main(argv):
    turns = 20
    for a in list(argv):
        if a.startswith("--turns="):
            turns = int(a.split("=", 1)[1])
            argv.remove(a)
    n = int(argv[0])
    decks = tuple(argv[1:]) or ACTIVE
    print(f"MDFC front faces: N={n:,} games a deck, T{turns}, seeds "
          f"{SEED0}..{SEED0 + n - 1}, build_pending, "
          f"python {sys.version.split()[0]}")
    for deck in decks:
        from edhmc.pending import build_pending
        names = [c.name for c in build_pending(deck)[0]
                 if c.land_face and not c.is_land]
        if not names:
            continue
        jobs = [(lo, min(lo + CHUNK, SEED0 + n), turns)
                for lo in range(SEED0, SEED0 + n, CHUNK)]
        rows = defaultdict(Counter)
        with Pool(initializer=_init, initargs=(deck,)) as pool:
            for part in pool.imap_unordered(_job, jobs):
                for k, v in part.items():
                    rows[k].update(v)
        print(f"\n{deck}")
        for name in names:
            r = rows[name]
            resp = {k[9:]: v for k, v in sorted(r.items())
                    if k.startswith("response_")}
            via = {k[4:]: v for k, v in sorted(r.items(),
                                                  key=lambda kv: (-kv[1], kv[0]))
                   if k.startswith("via_")}
            res = ("--" if deck == "rendmaw"
                   else f"{r['resolved']} ({r['blank']} blank)")
            print(f"  {name}\n    cast {r['cast']} (countered "
                  f"{r['countered']}), resolved {res}, answer "
                  f"{r['answer_cast']} casts / {r['answer_pieces']} pieces /"
                  f" {r['answer_whiffs']} whiffs, responses {resp or 0}, "
                  f"life {r['life']:g}, land face {r['land_face']}"
                  + (f"\n    via {via}" if via else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
