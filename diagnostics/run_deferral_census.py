#!/usr/bin/env python3
"""How often each deferral site fires, and whether it changed what was cast.

    python -m diagnostics.run_deferral_census N OUT.txt [DECK ...]

The second half of the deferral protocol (the owner, 2026-11-02; the first
half is `tools/deferrals.py`, which says WHERE). READ-ONLY: no engine code is
touched and no knob is set. A `sys.settrace` hook watches the exact lines
`tools.deferrals.scan()` derives -- a veto's `continue`, a reserve's `if` --
and every traced game is compared, whole output dict, with the same seed
played untraced. A trace that moved one game would make every count below a
count of some other game, so the run refuses to print if any differs (§0z35).

PER SITE, counted once per (turn, card) and never for a land:
  held      card-turns the site left a nonland card out of the options
  fits      ... of which the card's mana value fit in the pool the main
            phase was reading. A PROXY for "affordable": it ignores colours,
            cost reductions and every other veto. Under it, "held" counts
            cards no veto was needed to stop.
  shadow    ... of which a LATER veto in the same loop would have stopped
            the card too (its test read at the first one's fire line; only
            tests whose names are bound before the loop body, so a cost or
            mode the body computes is never read stale). A card is credited
            to the FIRST veto that fires, so without this a wipe
            hold_for_miracle holds is a wipe the wipe gate also holds.
  joint     ... a shadowed card that would otherwise bind: removing THIS veto
            alone would not change the pass, removing it with the later one
            would. Reported apart from binding, never added to it.
  binding   ... of which the site CHANGED THE PASS: the card fit, was not
            shadowed, and it
            outranked what `lookahead_pick` chose instead (the engines' own
            `rank`), or nothing was cast at all. The number the protocol is
            about. For a reserve the test itself is re-read with `reserve`
            = 0, so "held" is exact there: the reserve, and only the
            reserve, kept the card out.
  fate      what became of each card on its first binding turn: cast later
            through the main phase's pick, hand or flashback (and how many turns
            later), miracled (lorehold), or where it ended the game.

BLIND TO: a pick made by `max(options)` without `lookahead_pick` (engine
and azusa have one such branch); its vetoes are reported as "unresolved",
never as binding. Casts outside the main phase (free casts, tutors) are not
seen as a fate unless they leave the hand through `engine.remove_card`
(reported as "left hand: <the function that removed it>") or
`opponents._cast_response`; otherwise the card's end zone is reported.
"""
import importlib
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 250
TURNS = 20
_D = {}


def _codes(sites):
    """{code: {"veto": {line: site}, "reserve": {line: (site, code)},
    "reset": line}} for every function that holds a site."""
    import ast
    by = {}
    for s in sites:
        obj = importlib.import_module(f"edhmc.{s.module}")
        for part in s.qualname.split("."):
            obj = getattr(obj, part)
        code = obj.__code__
        ent = by.setdefault(code, {"veto": {}, "reserve": {}, "reset": None,
                                   "fn": obj})
        if s.kind == "veto":
            ent["veto"][s.fire_line] = s
        else:
            ent["reserve"][s.line] = (
                s, compile(ast.Expression(ast.parse(s.cond, mode="eval").body),
                           "<reserve>", "eval"))
    # Each main phase's `options = []`: a pass boundary.
    for code, ent in by.items():
        import inspect
        src_lines, start = inspect.getsourcelines(ent["fn"])
        import textwrap
        tree = ast.parse(textwrap.dedent("".join(src_lines)))
        # SHADOWING: the later vetoes of the same hand loop, each test
        # compiled, kept only if every name it reads is bound BEFORE the loop
        # body runs (a name the body assigns would be read stale, from the
        # previous card). Read at a veto's fire line, a true later test means
        # the card was stopped twice and the first veto changed nothing.
        lines_of = {st.line: st for st in ent["veto"].values()}
        for loop in ast.walk(tree):
            if not (isinstance(loop, ast.For)
                    and ast.unparse(loop.iter) in ("g.hand", "self.hand")):
                continue
            body_names = {n.id for st in loop.body for n in ast.walk(st)
                          if isinstance(n, ast.Name)
                          and isinstance(n.ctx, ast.Store)}
            ifs = sorted((start + n.lineno - 1, n) for n in ast.walk(loop)
                         if isinstance(n, ast.If)
                         and start + n.lineno - 1 in lines_of)
            for i, (ln, _n) in enumerate(ifs):
                later = []
                for ln2, n2 in ifs[i + 1:]:
                    read = {x.id for x in ast.walk(n2.test)
                            if isinstance(x, ast.Name)}
                    if read & body_names:
                        continue
                    later.append((lines_of[ln2], compile(
                        ast.Expression(n2.test), "<later>", "eval")))
                ent.setdefault("later", {})[lines_of[ln].fire_line] = later
        for n in ast.walk(tree):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == "options"
                    and isinstance(n.value, ast.List) and not n.value.elts):
                ent["reset"] = start + n.lineno - 1
    return by


class Tracer:
    def __init__(self, sites):
        from edhmc import engine as E
        self.by = _codes(sites)
        from edhmc import opponents as O
        self.pick_code = E.lookahead_pick.__code__
        self.remove_code = E.remove_card.__code__
        self.response_code = O._cast_response.__code__
        self.miracle_code = None
        try:
            from edhmc import lorehold as L
            self.miracle_code = L.miracle_window.__code__
        except Exception:
            pass
        self.main_codes = {c for c, e in self.by.items() if e["veto"]}

    # ---- per game -------------------------------------------------------
    def begin(self):
        self.g = None
        self.pending = defaultdict(dict)   # main frame id -> {(key, cid): rec}
        self.recs = {}                     # (key, cid) -> record
        self.card_recs = defaultdict(list)  # cid -> [(key, cid)]
        self.cards = {}                    # cid -> card (held alive)

    def _rec(self, site, card, g, fits):
        k = (site.key, id(card))
        r = self.recs.get(k)
        if r is None:
            r = self.recs[k] = {"site": site.key, "name": card.name,
                                "held": set(), "fits": set(),
                                "binding": set(), "unresolved": set(),
                                "shadowed": set(), "joint": set(),
                                "by": Counter(),
                                "fate": None, "first_bind": None}
            self.card_recs[id(card)].append(k)
            self.cards[id(card)] = card
        t = g.turn
        r["held"].add(t)
        if fits:
            r["fits"].add(t)
        return k

    def _main_frame(self, frame):
        f = frame
        for _ in range(4):
            if f is None:
                return None
            if f.f_code in self.main_codes:
                return f
            f = f.f_back
        return None

    def _settle(self, mframe, picked, rank):
        """The pass in `mframe` ended: with `picked` (a card), with nothing
        (None), or unknown ("?")."""
        pend = self.pending.pop(id(mframe), {})
        for k, (card, t, fits, joint) in pend.items():
            r = self.recs[k]
            if picked == "?":
                r["unresolved"].add(t)
                continue
            if not fits:
                continue
            if picked is None or (picked is not card
                                  and rank(card) > rank(picked)):
                if joint:
                    r["joint"].add(t)    # binds only with the later veto
                    continue
                r["binding"].add(t)
                if r["first_bind"] is None:
                    r["first_bind"] = t

    def _fate(self, card, what, provisional=False):
        """A definitive fate (a cast, a miracle) is final. Leaving the hand
        is PROVISIONAL: Library of Leng's redirect removes the card from hand
        on its way to the top, and the miracle that follows is the fate."""
        g = self.g
        if card is None or g is None:
            return
        for k in self.card_recs.get(id(card), ()):
            r = self.recs[k]
            if r["first_bind"] is None or g.turn < r["first_bind"]:
                continue
            if r["fate"] is None or (r.get("prov") and not provisional):
                r["fate"] = (what, g.turn - r["first_bind"])
                r["prov"] = provisional

    # ---- the hook -------------------------------------------------------
    def global_trace(self, frame, event, arg):
        code = frame.f_code
        if code in self.by:
            if self.g is None:
                loc = frame.f_locals
                self.g = loc.get("g", loc.get("self"))
            return self.local_trace
        if code is self.pick_code or code is self.miracle_code \
                or code is self.response_code:
            return self.local_trace
        if code is self.remove_code and self.g is not None:
            loc = frame.f_locals
            if loc.get("cards") is self.g.hand and frame.f_back is not None:
                self._fate(loc.get("card"),
                           f"left hand: {frame.f_back.f_code.co_name}",
                           provisional=True)
        return None

    def local_trace(self, frame, event, arg):
        code = frame.f_code
        if code is self.pick_code:
            if event == "return" and arg is not None:
                mframe = frame.f_back
                if mframe is not None and mframe.f_code in self.main_codes:
                    rank = frame.f_locals.get("rank")
                    card = arg[0] if isinstance(arg, tuple) else arg

                    def rk(c, rank=rank):
                        try:
                            return rank((c, None, None))
                        except Exception:
                            return (c.priority, c.mv)
                    self._settle(mframe, card, rk)
                    self._fate(card, "cast later by the main phase")
            return self.local_trace
        if code is self.response_code:
            if event == "return" and arg:
                self._fate(frame.f_locals.get("card"),
                           "cast as a response on the pod's turn")
            return self.local_trace
        if code is self.miracle_code:
            if event == "return" and isinstance(arg, tuple) and len(arg) == 2:
                drawn, cast = arg
                if cast and drawn is not None:
                    self._fate(drawn, "miracled")
            return self.local_trace
        ent = self.by.get(code)
        if ent is None:
            return None
        if event == "return":
            if code in self.main_codes:
                self._settle(frame, None, None)
            return self.local_trace
        if event != "line":
            return self.local_trace
        ln = frame.f_lineno
        if ln == ent["reset"] and id(frame) in self.pending:
            self._settle(frame, "?", None)
            return self.local_trace
        site = ent["veto"].get(ln)
        if site is not None:
            loc = frame.f_locals
            card = loc.get(site.loop_var)
            if card is None or getattr(card, "is_land", False):
                return self.local_trace
            shadow = None
            for later, test in ent.get("later", {}).get(ln, ()):
                try:
                    if eval(test, frame.f_globals, dict(loc)):
                        shadow = later
                        break
                except Exception:
                    continue
            self._held(frame, site, card, loc, shadow=shadow)
            return self.local_trace
        res = ent["reserve"].get(ln)
        if res is not None:
            site, test = res
            loc = dict(frame.f_locals)
            if not loc.get("reserve"):
                return self.local_trace
            try:
                a = bool(eval(test, frame.f_globals, loc))
                loc["reserve"] = 0
                b = bool(eval(test, frame.f_globals, loc))
            except Exception:
                return self.local_trace
            if a == b:
                return self.local_trace
            card = loc.get(site.loop_var) if site.loop_var else None
            if card is None:
                card = next((loc[n] for n in ("c", "card")
                             if hasattr(loc.get(n), "priority")), None)
            if card is None:
                card = _Pseudo(f"{site.qualname} (no card)")
            self._held(frame, site, card, loc, exact=True)
        return self.local_trace

    def _held(self, frame, site, card, loc, exact=False, shadow=None):
        g = self.g
        pool = loc.get("pool", loc.get("units"))
        fits = True if exact else (pool is not None
                                   and card.mv <= len(pool))
        k = self._rec(site, card, g, fits)
        if shadow is not None:           # a later veto stops it too
            r = self.recs[k]
            if g.turn not in r["shadowed"]:          # once per card-turn
                r["by"][shadow.where] += 1
            r["shadowed"].add(g.turn)
        mframe = self._main_frame(frame)
        if mframe is not None and not isinstance(card, _Pseudo):
            self.pending[id(mframe)][k] = (card, g.turn, fits,
                                           shadow is not None)

    def end(self):
        """Close open fates on the game's end zones; return the records."""
        g = self.g
        out = []
        for k, r in self.recs.items():
            prov = r.get("prov") and r["fate"] is not None
            if r["first_bind"] is not None and (r["fate"] is None or prov) \
                    and g:
                card = self.cards[k[1]]
                if any(c is card for c in g.hand):
                    zone = "still in hand at the end"
                elif any(c is card for c in g.library):
                    zone = "in the library at the end"
                elif any(c is card for c in g.graveyard):
                    zone = "in the graveyard at the end"
                elif any(p.card is card for p in g.board):
                    zone = "on the battlefield (another path)"
                else:
                    zone = "elsewhere (exile, stack)"
                if prov:
                    # Left the hand and nothing definitive followed: say where
                    # it went, so a Leng card drawn back unmiracled reads as
                    # back in hand, not as rummaged away.
                    zone = (zone if zone.startswith("still in hand")
                            else f"{r['fate'][0]}, then {zone.split(' at the')[0]}")
                r["fate"] = (zone, None)
            out.append({"site": r["site"], "name": r["name"],
                        "held": len(r["held"]), "fits": len(r["fits"]),
                        "shadowed": len(r["shadowed"]),
                        "joint": len(r["joint"]), "by": dict(r["by"]),
                        "binding": len(r["binding"]),
                        "unresolved": len(r["unresolved"]),
                        "fate": r["fate"]})
        return out


class _Pseudo:
    def __init__(self, name):
        self.name, self.mv, self.priority, self.is_land = name, 0, 0, False


def _init(deck):
    from edhmc.pending import build_pending
    from tools.deferrals import scan
    _D["deck_name"] = deck
    _D["deck"], _D["cmd"] = build_pending(deck)
    _D["sites"] = scan()


def _job(args):
    lo, hi = args
    from edhmc.experiment import DEFAULT_CFG
    from edhmc.registry import DECKS
    sim = DECKS[_D["deck_name"]].sim
    cfg = dict(DEFAULT_CFG, turns=TURNS)
    tr = Tracer(_D["sites"])
    games, diverged = [], []
    for s in range(lo, hi):
        plain = sim(_D["deck"], _D["cmd"], dict(cfg), s)
        tr.begin()
        sys.settrace(tr.global_trace)
        try:
            traced = sim(_D["deck"], _D["cmd"], dict(cfg), s)
        finally:
            sys.settrace(None)
        if traced != plain:
            diverged.append(s)
        games.append((s, bool(plain.get("won")), tr.end()))
    return games, diverged


def census(deck, n, procs=4):
    jobs = [(SEED0 + i, min(SEED0 + n, SEED0 + i + CHUNK))
            for i in range(0, n, CHUNK)]
    with Pool(procs, initializer=_init, initargs=(deck,)) as pool:
        parts = pool.map(_job, jobs)
    games = [g for p, _ in parts for g in p]
    diverged = [s for _, d in parts for s in d]
    return games, diverged


def render(deck, n, games, diverged, sites):
    from tools.deferrals import CLASSES
    lines = [f"{deck}: deferral census, {n:,} games from seed {SEED0}, "
             f"T{TURNS}, python {sys.version.split()[0]}",
             f"traced games identical to untraced, whole output: "
             f"{'YES' if not diverged else 'NO -- ' + str(diverged[:5])}",
             "per game: card-turns held / fits (mv <= pool) / shadow (a "
             "LATER veto stops it too) / JOINT (would bind, but only with "
             "that later veto) / BINDING (fit, not shadowed, and outranked "
             "the pick or nothing was cast) / unresolved; games = share of "
             "games with >= 1 binding", ""]
    agg = defaultdict(Counter)
    games_bind = Counter()
    fates = defaultdict(Counter)
    delays = defaultdict(list)
    names = defaultdict(Counter)
    shadow_by = defaultdict(Counter)
    for _s, _won, recs in games:
        hit = set()
        for r in recs:
            a = agg[r["site"]]
            for f in ("held", "fits", "shadowed", "joint", "binding",
                      "unresolved"):
                a[f] += r[f]
            shadow_by[r["site"]].update(r["by"])
            if r["binding"]:
                hit.add(r["site"])
                names[r["site"]][r["name"]] += r["binding"]
                what, d = r["fate"]
                fates[r["site"]][what] += 1
                if d is not None:
                    delays[r["site"]].append(d)
        for k in hit:
            games_bind[k] += 1
    deck_mods = None
    from edhmc.registry import DECKS
    deck_mods = {DECKS[deck].engine}
    rows = [s for s in sites if s.module in deck_mods
            or (s.module == "engine" and DECKS[deck].engine == "engine")]
    lines.append(f"{'site':<34} {'category':<12} {'held':>6} {'fits':>6} "
                 f"{'shadow':>6} {'JOINT':>6} {'BIND':>6} {'unres':>6} "
                 f"{'games':>6}")
    for s in rows:
        cat = CLASSES.get(s.key, ("?",))[0]
        if cat == "NOT_A_CHOICE":
            continue
        a = agg.get(s.key, Counter())
        lines.append(
            f"{s.where:<34} {cat:<12} {a['held']/n:6.2f} {a['fits']/n:6.2f} "
            f"{a['shadowed']/n:6.2f} {a['joint']/n:6.2f} {a['binding']/n:6.2f} {a['unresolved']/n:6.2f} "
            f"{games_bind[s.key]/n:6.1%}")
        lines.append(f"    if {s.cond[:100]}")
        if shadow_by.get(s.key):
            by = ", ".join(f"{w} {c / n:.2f}"
                           for w, c in shadow_by[s.key].most_common(3))
            lines.append(f"    shadowed by: {by}")
    lines.append("")
    lines.append("FATES of each card on its first binding turn, and the "
                 "cards held most (binding card-turns)")
    for s in rows:
        if not fates.get(s.key) or CLASSES.get(s.key, ("?",))[0] == "NOT_A_CHOICE":
            continue
        tot = sum(fates[s.key].values())
        lines.append(f"  {s.where}  {s.module}.{s.qualname}: {tot:,} cards")
        for what, c in fates[s.key].most_common():
            extra = ""
            if what == "cast later by the main phase" and delays[s.key]:
                d = delays[s.key]
                extra = (f"   mean {sum(d)/len(d):.2f} turns later; "
                         f"same turn {sum(1 for x in d if x == 0)/len(d):.0%}")
            lines.append(f"      {c/tot:6.1%}  {what}{extra}")
        top = ", ".join(f"{nm} {c/n:.3f}" for nm, c
                        in names[s.key].most_common(8))
        lines.append(f"      per game: {top}")
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    n, out = int(argv[0]), argv[1]
    from edhmc.registry import ACTIVE
    from tools.deferrals import scan
    decks = argv[2:] or list(ACTIVE)
    sites = scan()
    text = []
    bad = False
    for d in decks:
        games, diverged = census(d, n)
        bad |= bool(diverged)
        block = render(d, n, games, diverged, sites)
        print(block, flush=True)
        text.append(block)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(text))
    if bad:
        print("REFUSED: a traced game differs from its untraced twin; the "
              "counts above describe other games.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
