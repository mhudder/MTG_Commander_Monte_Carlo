#!/usr/bin/env python3
"""Lorehold's rummage, counted; and the off-turn float it is paid from (§0z166).

    python -m diagnostics.run_lorehold_rummage census N OUT.txt
    python -m diagnostics.run_lorehold_rummage float N OUT.txt
    python -m diagnostics.run_lorehold_rummage pick N OUT.txt

The owner, 2026-11-03: "how often is it using the discard ability to cycle
through low power cards?" Lorehold: "At the beginning of each opponent's
upkeep, you may discard a card. If you do, draw a card." Artist's Talent's
level 1 is the same rummage on every noncreature spell. Both give up
`rummage_discard_choice`'s card: the lowest MIRACLE VALUE in hand, lands
spared below `land_floor` (8) lands. With Library of Leng the pod's rummage
puts the best miracle on top instead, when the window can pay for it.

`census` -- READ-ONLY. Wrappers that call straight through record each
rummage: what was given up (a land, a permanent -- miracle value -1 -- or a
spell and its value), where it ranked in the hand by the pilot's own
priority, and whether the card drawn was miracled. Every game is played
twice, wrapped and bare, and compared whole: a wrapper that moved one game
makes the run refuse to print (§0z35). Under both today's policy and §0z164's
(`miracle_reserve` 0, `hold_min_value` 99), since the rummage is what that
change would feed. Also the off-turn FLOAT's composition at each end of
turn, which is where the two defects below live.

`float` -- an A/B. `your_turn` ends `g.float_mana = len(mana_units(g))`, and
`mana_units` is board + Apex + Treasures. So (1) every Treasure is in the
float AND in `g.treasures`, which every off-turn payment adds again -- and,
the float spent first, the Treasure survives a payment it made; (2) Apex of
Power's and Explosive Welcome's unspent mana floats into the pod's turns,
where CR 106.4 empties it at the end of the step. The arm `fix` corrects
the float to the board's untapped units after `your_turn` returns -- the
engine is not edited -- paired against today's, under both policies.

`pick` -- an A/B of the rummage's own choice, swapped in for
`rummage_discard_choice` (both rummages read it). Every rule keeps today's
land rule (lands spared below `land_floor`); only the key changes:
  miracle   today: the lowest miracle value. Every permanent is -1, so an
            engine (Arcane Bombardment, Sunbird's Invocation) goes before a
            one-mana removal spell, and a tie falls to hand order
  priority  the lowest cast priority -- the pilot's own ranking
  mv        the lowest mana value
  guard     today's, but never a permanent of priority 8.5+ while another
            card can go
Today's rule is also run REWRITTEN through the same swap, and must reproduce
today's games on every metric (§0z35), or the run says so.
"""
import os
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())

SEED0 = 5000
CHUNK = 250
DECK = "lorehold"
POLICIES = {"today": {}, "R0H99": {"miracle_reserve": 0,
                                   "hold_min_value": 99.0}}
_D = {}


def _init():
    from edhmc.pending import build_pending
    _D["deck"], _D["cmd"] = build_pending(DECK)


def _cfg(extra, turns):
    from edhmc.experiment import DEFAULT_CFG
    return dict(DEFAULT_CFG, turns=turns, **extra)


def _units_per_treasure(g):
    return 2 if g.has("Goldspan Dragon") else 1


# --------------------------------------------------------------------------
# census
# --------------------------------------------------------------------------
class Spy:
    """Call-through wrappers on lorehold's module globals. Nothing they do
    writes to the game; `install` / `remove` restore the originals."""
    NAMES = ("remove_card", "miracle_window", "opponent_upkeep_windows",
             "your_turn")

    def __init__(self):
        from edhmc import lorehold as L
        self.L = L
        self.real = {n: getattr(L, n) for n in self.NAMES}
        self.c = Counter()
        self.names = Counter()        # nonland cards given up, by name
        self.pending = None           # the pod rummage awaiting its draw

    def install(self):
        L, real, spy = self.L, self.real, self

        def remove_card(cards, card):
            f = sys._getframe(1)
            who = f.f_code.co_name
            g = f.f_locals.get("g")
            if g is not None and cards is g.hand and who in (
                    "opponent_upkeep_windows", "artist_rummage"):
                spy.discard(g, who, card, f.f_locals)
            return real["remove_card"](cards, card)

        def miracle_window(g, off_turn=False):
            drawn, cast = real["miracle_window"](g, off_turn)
            if off_turn and spy.pending is not None:
                kind = spy.pending
                spy.c[f"{kind}: draw miracled"] += bool(cast)
                spy.pending = None
            return drawn, cast

        def opponent_upkeep_windows(g):
            if g.commander_cast:
                spy.c["pod windows, Lorehold out"] += len(L.OPP.acting(g))
            before = g.m["miracle_windows"]
            r = real["opponent_upkeep_windows"](g)
            spy.c["pod rummages taken"] += g.m["miracle_windows"] - before
            return r

        def your_turn(g, extra=False):
            r = real["your_turn"](g, extra)
            per = _units_per_treasure(g)
            t_units = min(g.treasures * per, g.float_mana)
            apex = min(g.apex_mana, g.float_mana - t_units)
            spy.c["ends of turn"] += 1
            spy.c["float total"] += g.float_mana
            spy.c["float from Treasures (counted twice)"] += t_units
            spy.c["float from Apex / Welcome mana (106.4)"] += apex
            spy.c["ends with a Treasure"] += g.treasures > 0
            spy.c["ends with Apex mana left"] += apex > 0
            return r

        for n, fn in (("remove_card", remove_card),
                      ("miracle_window", miracle_window),
                      ("opponent_upkeep_windows", opponent_upkeep_windows),
                      ("your_turn", your_turn)):
            setattr(L, n, fn)

    def remove(self):
        for n, fn in self.real.items():
            setattr(self.L, n, fn)

    def discard(self, g, who, card, loc):
        L = self.L
        src = "pod" if who == "opponent_upkeep_windows" else "artist"
        leng = (src == "pod" and g.has("Library of Leng")
                and loc.get("afford") and loc.get("best") is card
                and L.miracle_value(g, card) > 0)
        if leng:
            self.c["pod: Library of Leng, best miracle to the top"] += 1
            self.pending = "pod/Leng"
            return
        kind = f"{src}: discard"
        self.c[kind] += 1
        if src == "pod":
            self.pending = "pod/discard"
        lands = sum(1 for p in g.board if p.card.is_land)
        if card.is_land:
            self.c[f"{kind} -> a land"] += 1
            self.c[f"{kind} -> a land, with {'8+' if lands >= 8 else '<8'} lands out"] += 1
            return
        v = L.miracle_value(g, card)
        if v < 0:
            self.c[f"{kind} -> a permanent (no miracle)"] += 1
        elif v <= 1:
            self.c[f"{kind} -> a spell worth <= 1 as a miracle"] += 1
        elif v <= 3:
            self.c[f"{kind} -> a spell worth 2-3"] += 1
        else:
            self.c[f"{kind} -> a spell worth 4+"] += 1
        others = [c for c in g.hand if c is not card and not c.is_land]
        if others and card.priority > min(c.priority for c in others):
            self.c[f"{kind} -> nonland the pilot ranked ABOVE another in hand"] += 1
        if card.priority >= 8.5:
            self.c[f"{kind} -> nonland of priority 8.5+"] += 1
        if lands < 8 and any(c.is_land for c in g.hand):
            self.c[f"{kind} -> nonland, a land kept (under land_floor)"] += 1
        self.names[card.name] += 1


def _census_job(args):
    pol, lo, hi = args
    from edhmc.lorehold import simulate
    cfg = _cfg(POLICIES[pol], 20)
    spy = Spy()
    bad = []
    games = Counter()
    for s in range(lo, hi):
        plain = simulate(_D["deck"], _D["cmd"], dict(cfg), s)
        spy.install()
        try:
            traced = simulate(_D["deck"], _D["cmd"], dict(cfg), s)
        finally:
            spy.remove()
        if traced != plain:
            bad.append(s)
        games["games"] += 1
        games["won"] += bool(plain.get("won"))
        for k in ("miracles_cast", "artist_rummages", "leng_to_top",
                  "leng_miracled"):
            games[k] += plain.get(k, 0)
    return pol, spy.c, spy.names, games, bad


def census(n, out):
    jobs = [(p, lo, min(lo + CHUNK, SEED0 + n)) for p in POLICIES
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    agg = {p: [Counter(), Counter(), Counter(), []] for p in POLICIES}
    with Pool(initializer=_init) as pool:
        for pol, c, names, games, bad in pool.imap_unordered(_census_job, jobs):
            a = agg[pol]
            a[0].update(c), a[1].update(names), a[2].update(games)
            a[3].extend(bad)
    lines = [f"Lorehold's rummage (§0z166): {n:,} games a policy, seeds "
             f"{SEED0}.., T20, the staged list, python "
             f"{sys.version.split()[0]}", ""]
    refused = False
    for pol, (c, names, games, bad) in agg.items():
        g = games["games"]
        refused |= bool(bad)
        lines.append(f"== {pol} {POLICIES[pol] or '(the defaults)'}")
        lines.append(f"   wrapped games identical to bare, whole output: "
                     f"{'YES' if not bad else 'NO ' + str(sorted(bad)[:5])}")
        lines.append(f"   per game:")
        for k in sorted(c):
            if not k.startswith(("float", "ends")):
                lines.append(f"     {c[k] / g:7.3f}  {k}")
        lines.append("   the off-turn float, per end of turn:")
        e = max(1, c["ends of turn"])
        for k in ("float total", "float from Treasures (counted twice)",
                  "float from Apex / Welcome mana (106.4)"):
            lines.append(f"     {c[k] / e:7.3f}  {k}")
        for k in ("ends with a Treasure", "ends with Apex mana left"):
            lines.append(f"     {c[k] / e:7.1%}  {k}")
        lines.append(f"   win {games['won'] / g:.4f}; miracles "
                     f"{games['miracles_cast'] / g:.3f}; Leng to top "
                     f"{games['leng_to_top'] / g:.3f}, miracled "
                     f"{games['leng_miracled'] / g:.3f}")
        tot = sum(names.values())
        top = ", ".join(f"{nm} {k / g:.3f}" for nm, k in names.most_common(12))
        lines.append(f"   nonland cards given up, per game ({tot / g:.2f}): {top}")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if refused:
        print("REFUSED: a wrapped game differs from its bare twin.")
        return 1
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0


# --------------------------------------------------------------------------
# float: today's float against the corrected one, paired
# --------------------------------------------------------------------------
MET = ("won", "miracles_cast", "damage", "spells_cast", "mana_floated")


def _float_job(args):
    pol, fix, turns, lo, hi = args
    from edhmc import lorehold as L
    real = L.your_turn

    def corrected(g, extra=False):
        r = real(g, extra)
        # The board's untapped units only: no Treasure (it is in
        # g.treasures), no Apex / Welcome mana (106.4: the pool empties).
        per = _units_per_treasure(g)
        g.float_mana = max(0, g.float_mana - g.treasures * per - g.apex_mana)
        return r
    if fix:
        L.your_turn = corrected
    try:
        cfg = _cfg(POLICIES[pol], turns)
        out = np.zeros((hi - lo, len(MET)))
        for i, s in enumerate(range(lo, hi)):
            r = L.simulate(_D["deck"], _D["cmd"], dict(cfg), s)
            out[i] = [r.get(m, 0) for m in MET]
    finally:
        L.your_turn = real
    return pol, fix, turns, lo, out


def float_ab(n, out):
    jobs = [(p, f, t, lo, min(lo + CHUNK, SEED0 + n)) for p in POLICIES
            for f in (False, True) for t in (10, 20)
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    res = {}
    with Pool(initializer=_init) as pool:
        for p, f, t, lo, block in pool.imap_unordered(_float_job, jobs):
            res.setdefault((p, f, t), {})[lo] = block
    col = {k: np.vstack([v[lo] for lo in sorted(v)]) for k, v in res.items()}

    def cell(a, b, j=0):
        d = col[a][:, j] - col[b][:, j]
        mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
        return f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}"
    lines = [f"Lorehold's off-turn float corrected (§0z166): N={n:,} paired, "
             f"seeds {SEED0}.., the staged list, python "
             f"{sys.version.split()[0]}", "* = 95% CI excludes 0", ""]
    for p in POLICIES:
        lines.append(f"{p}: fix minus today's float")
        for t in (10, 20):
            lines.append(f"  T{t}  win {cell((p, True, t), (p, False, t))}"
                         f"   miracles {cell((p, True, t), (p, False, t), 1)}"
                         f"   spells {cell((p, True, t), (p, False, t), 3)}")
    lines.append("")
    lines.append("§0z164's change (R0H99 minus today), with and without the fix")
    for f in (False, True):
        for t in (10, 20):
            lines.append(f"  {'fixed float' if f else 'today float'} T{t}  "
                         f"win {cell(('R0H99', f, t), ('today', f, t))}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0


# --------------------------------------------------------------------------
# pick: the rummage's choice
# --------------------------------------------------------------------------
RULES = ("miracle", "priority", "mv", "guard")


def _rule(name, L):
    def pool_of(g):
        my_lands = sum(1 for p in g.board if p.card.is_land)
        pool = g.hand
        if my_lands < g.cfg.get("land_floor", 8):
            nonlands = [c for c in g.hand if not c.is_land]
            if nonlands:
                pool = nonlands
        return pool

    def pick(g):
        pool = pool_of(g)

        def mval(c):
            return L.miracle_value(g, c)
        if name == "priority":
            return min(pool, key=lambda c: (c.priority, mval(c)))
        if name == "mv":
            return min(pool, key=lambda c: (c.mv, mval(c)))
        if name == "guard":
            keep = [c for c in pool if c.is_land or mval(c) >= 0
                    or c.priority < 8.5]
            return min(keep or pool, key=mval)
        return min(pool, key=mval)
    return pick


def _pick_job(args):
    pol, rule, turns, lo, hi = args
    from edhmc import lorehold as L
    real = L.rummage_discard_choice
    # "rewritten" is today's rule through the swap: the self-check.
    if rule != "miracle":
        L.rummage_discard_choice = _rule(
            "miracle" if rule == "rewritten" else rule, L)
    try:
        cfg = _cfg(POLICIES[pol], turns)
        out = np.zeros((hi - lo, len(MET)))
        for i, s in enumerate(range(lo, hi)):
            r = L.simulate(_D["deck"], _D["cmd"], dict(cfg), s)
            out[i] = [r.get(m, 0) for m in MET]
    finally:
        L.rummage_discard_choice = real
    return pol, rule, turns, lo, out


def pick_ab(n, out):
    rules = RULES + ("rewritten",)
    jobs = [(p, r, t, lo, min(lo + CHUNK, SEED0 + n)) for p in POLICIES
            for r in rules for t in (10, 20)
            for lo in range(SEED0, SEED0 + n, CHUNK)]
    res = {}
    with Pool(initializer=_init) as pool:
        for p, r, t, lo, block in pool.imap_unordered(_pick_job, jobs):
            res.setdefault((p, r, t), {})[lo] = block
    col = {k: np.vstack([v[lo] for lo in sorted(v)]) for k, v in res.items()}

    def cell(a, b, j=0):
        d = col[a][:, j] - col[b][:, j]
        mu, ci = d.mean(), 1.96 * d.std(ddof=1) / np.sqrt(len(d))
        return f"{mu:+.4f} +-{ci:.4f}{'*' if abs(mu) > ci else ' '}"
    same = all(np.array_equal(col[(p, "rewritten", t)], col[(p, "miracle", t)])
               for p in POLICIES for t in (10, 20))
    lines = [f"Lorehold's rummage pick (§0z166): N={n:,} paired, seeds "
             f"{SEED0}.., the staged list, python {sys.version.split()[0]}",
             "today's rule rewritten through the swap reproduces today's "
             f"games, every metric: "
             f"{'YES' if same else 'NO -- the rows below are not trustworthy'}",
             "row = rule minus today's (miracle); * = 95% CI excludes 0", ""]
    for p in POLICIES:
        lines.append(f"{p} {POLICIES[p] or '(the defaults)'}")
        for r in RULES[1:]:
            lines.append(
                f"  {r:<9} T10 {cell((p, r, 10), (p, 'miracle', 10))}   "
                f"T20 {cell((p, r, 20), (p, 'miracle', 20))}   miracles T20 "
                f"{cell((p, r, 20), (p, 'miracle', 20), 1)}")
    text = "\n".join(lines)
    print(text)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0 if same else 1


def main(argv):
    modes = {"census": census, "float": float_ab, "pick": pick_ab}
    if len(argv) < 3 or argv[0] not in modes:
        print(__doc__)
        return 2
    n, out = int(argv[1]), argv[2]
    return modes[argv[0]](n, out)



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
