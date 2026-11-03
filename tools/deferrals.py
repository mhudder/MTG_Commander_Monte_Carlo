#!/usr/bin/env python3
"""Every place a pilot DECLINES a spell it holds, derived from the engines.

    python -m tools.deferrals            # the inventory, by category
    python -m tools.deferrals --check    # exit 1 if a site is unclassified,
                                         # or a classification names no site

WHY (the owner, 2026-11-02, after §0z164): "the pilot in this condition may
be declining to cast a game changing spell for a chance to save mana ... this
type of thinking should be the exception rather than the norm." A deferral is
a bet that a better use comes later. §0t, §0z134 and §0z164 measured three of
them and all three lost; the biggest corrections in this project were
policies written as conservatism (CLAUDE.md, "Where the big errors came
from"). This tool is the first half of a protocol: WHERE the pilot waits.
`diagnostics/run_deferral_census.py` is the second: HOW OFTEN, and whether
the wait changed what was cast.

WHAT IS DERIVED (§0q: a hand-kept list of sites is a claim, and claims rot):

  hand veto   in every function that picks a cast through
              `engine.lookahead_pick` (the seven main phases), every
              `if COND: ... continue` -- a body ENDING in `continue` that
              never reads `options`, no else -- inside a `for X in g.hand` /
              `self.hand` loop. The card X is left out of that pass's options.
  reserve     in every engine function with a parameter named `reserve`,
              every `if` whose test compares against `reserve`. Where the
              test reads differently with `reserve` = 0, the reserve, and
              nothing else, kept the card from being an option.

WHAT IS HAND-KEPT, AND CHECKED: `CLASSES`, one category and one line of
reason per site. `--check` fails if a scanned site has no entry or an entry
names no scanned site, so a new veto cannot arrive unclassified and a removed
one cannot linger. Sites are keyed by function and condition TEXT, not line,
so an edit elsewhere in a module does not move them.

BLIND TO (§0z15), written down so nobody reads the inventory as complete:
  * casts outside the main phases' option loops: `engine.altar_enable`,
    tutors, free casts, flashback's own option list (`lorehold.
    flashback_options` IS scanned for its reserve, not for vetoes), and every
    `pilot_may_cast`-style gate called from somewhere else;
  * activated abilities a knob holds back (`altar_keep`, `karlov_exile_keep`,
    `gingerbrute_keep`, `zuran_keep`, `vault_hold`), life floors (§0z160-
    §0z163 forked those), and the pod's-turn responses (`response_reserve`,
    which is "leftover" by default and holds nothing);
  * a veto written as anything but an `if` ending in `continue` -- an `if`
    whose body appends the option (the cost checks below are read that way only where
    they are a reserve), a filter in a comprehension, an early `return`.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKER = "lookahead_pick"
# Named so `tests/test_deferrals.py --mutate` can turn each rule off and
# prove a case stops it (a check that cannot fail is worse than none).
ONE_LINE_GUARD = True       # refuse `if X: continue` on one line
CHECK_STALE = True          # a classification naming no site is a problem

# ---------------------------------------------------------------------------
# Categories. The order is the protocol's: the first four are not bets.
# ---------------------------------------------------------------------------
CATEGORIES = {
    "NOT_A_CHOICE": "the card cannot be cast here: a land, a cost that does "
                    "not pay, a rule on the card",
    "SAFETY": "casting would deck you -- a loss the rules make possible "
              "(§0z42)",
    "ROUTED": "cast by its own path elsewhere, which pays a cost this loop "
              "cannot",
    "WASTE_GUARD": "the card would do nothing now: an answer with nothing to "
                   "hit, a blink with nothing to blink",
    "SAME_TURN": "deferred to a later phase of THIS turn; nothing is held "
                 "past the end step",
    "JUDGEMENT": "a situational read of the board, measured where cited",
    "SPECULATIVE": "held past this turn on a bet that a better use comes -- "
                   "the protocol's subject",
}

# key: "module.qualname | condition" (ast.unparse spelling).
# value: (category, reason with its §).
CLASSES: dict[str, tuple[str, str]] = {
    # --- engine.main_phase (rendmaw) --------------------------------------
    "engine.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "engine.main_phase | precombat and 'pump' not in c.tags": (
        "SAME_TURN", "precombat casts only pumps; the rest waits for the "
        "main phase after combat"),
    "engine.main_phase | 'wipe' in c.tags and (not OPP.should_cast_own_wipe(g, c))": (
        "JUDGEMENT", "the wipe gate: do not wrath a board you are winning "
        "(§0z104, §0z106)"),
    "engine.main_phase | OPP.hold_answer(g, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit, or a pure response "
        "kept for the pod's turn (§0z131, §0z134)"),
    "engine.main_phase | c.name == 'Proft, Sinister Mastermind' and len(g.graveyard) < PROFT_THRESHOLD": (
        "NOT_A_CHOICE", "Proft's threshold: \"you can't cast this spell "
        "unless\" (CR 601.3)"),
    "engine.main_phase | not main_phase_may_cast(g, c)": (
        "ROUTED", "Village Rites is cast by its sacrifice outlet, which pays "
        "its creature (§0z73)"),
    # --- karlov -------------------------------------------------------------
    "karlov.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "karlov.main_phase | not OPP.own_wipe_castable(g, c)": (
        "JUDGEMENT", "the wipe gate, or a single-target mode ready "
        "(§0z104, §0z138)"),
    "karlov.main_phase | OPP.hold_answer(g, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit, or a pure response "
        "(§0z131, §0z134)"),
    # --- tivit --------------------------------------------------------------
    "tivit.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "tivit.main_phase | not OPP.own_wipe_castable(g, c)": (
        "JUDGEMENT", "the wipe gate (§0z104, §0z138)"),
    "tivit.main_phase | OPP.hold_answer(g, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit; tivit's "
        "counterspells (§0z131, §0z134)"),
    "tivit.main_phase | 'blink' in c.tags and (not c.is_permanent) and (not g.has('Tivit, Seller of Secrets'))": (
        "WASTE_GUARD", "a one-shot blink with no Tivit to blink"),
    # --- lorehold -----------------------------------------------------------
    "lorehold._main_phase | c.is_land or hold_for_miracle(g, c)": (
        "SPECULATIVE", "hold_for_miracle: a spell worth `hold_min_value` as "
        "a miracle waits for Library of Leng to put it on top. OFF since "
        "2026-11-03 (99, the owner; was 3): never holding measured +0.0043 / "
        "+0.0050 (§0z164, §0z168). The census skips the land half"),
    "lorehold._main_phase | c.land_face and n_lands < g.cfg.get('mdfc_land_floor', 5)": (
        "SPECULATIVE", "an MDFC is kept for its land face while under "
        "`mdfc_land_floor` (5) lands, even with the land drop used; "
        "unmeasured"),
    "lorehold._main_phase | 'wipe' in c.tags and (not OPP.should_cast_own_wipe(g, c))": (
        "JUDGEMENT", "the wipe gate (§0z104, §0z106)"),
    "lorehold._main_phase | OPP.hold_answer(g, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit (§0z131, §0z134)"),
    "lorehold._main_phase | c.name in TURN_ENDERS and g.precombat and g.cfg.get('own_wipe_scope', True)": (
        "SAME_TURN", "a spell that ends the turn waits for after combat "
        "(§0z118)"),
    "lorehold._main_phase | not pilot_may_cast(g, c)": (
        "SAFETY", "the spell would draw the library empty (§0z42) -- and, "
        "one predicate for every optional cast, the wipe gate again "
        "(§0z104), no legal target (601.2c), Gamble under "
        "`gamble_min_hand` (2) other cards"),
    "lorehold._main_phase | mode is None": (
        "NOT_A_CHOICE", "no mode of the card pays"),
    "lorehold._main_phase | len(units) - sum(cost.values()) >= reserve": (
        "SPECULATIVE", "miracle_reserve: mana kept for the pod's miracle "
        "windows past the end step. 0 since 2026-11-03 (the owner; was 2): "
        "reserve 0 measured +0.0120 / +0.0059 (§0t, §0z164, §0z168)"),
    "lorehold.flashback_options | idx is not None and len(units) - len(idx) >= reserve": (
        "SPECULATIVE", "the same miracle reserve, on a card's own flashback "
        "(§0z164)"),
    "lorehold.artist_level_up | idx is None or len(units) - len(idx) < reserve": (
        "SPECULATIVE", "the same miracle reserve, on Artist's Talent's level "
        "(§0z164)"),
    # --- shilgengar ---------------------------------------------------------
    "shilgengar.ShilgengarGame.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "shilgengar.ShilgengarGame.main_phase | not OPP.own_wipe_castable(self, c)": (
        "JUDGEMENT", "the wipe gate (§0z104, §0z138)"),
    "shilgengar.ShilgengarGame.main_phase | OPP.hold_answer(self, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit (§0z131, §0z134)"),
    "shilgengar.ShilgengarGame.main_phase | _m is not None and len(pool) - sum(_m[0].values()) >= reserve": (
        "SAME_TURN", "shilgengar_ult_reserve (3): mana for the ultimate in "
        "`activations()`, after combat this turn; 0 when Treasures cover it "
        "(§0t)"),
    # --- azusa --------------------------------------------------------------
    "azusa.AzusaGame.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "azusa.AzusaGame.main_phase | enablers_only and c.name not in LAND_ENABLERS": (
        "SAME_TURN", "the pre-land phase casts only land enablers; the rest "
        "is cast after the lands this turn"),
    "azusa.AzusaGame.main_phase | 'wipe' in c.tags and (not OPP.should_cast_own_wipe(self, c))": (
        "JUDGEMENT", "the wipe gate (§0z104, §0z106)"),
    "azusa.AzusaGame.main_phase | OPP.hold_answer(self, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit (§0z131, §0z134)"),
    "azusa.AzusaGame.main_phase | n_draw and (not draw_is_safe(self, n_draw))": (
        "SAFETY", "the spell's draw would deck you (§0z42)"),
    # --- trostani (SUSPENDED, scanned all the same) ------------------------
    "trostani.TrostaniGame.main_phase | c.is_land": (
        "NOT_A_CHOICE", "a land is played by the land step"),
    "trostani.TrostaniGame.main_phase | 'wipe' in c.tags and (not OPP.should_cast_own_wipe(self, c))": (
        "JUDGEMENT", "the wipe gate (§0z104, §0z106)"),
    "trostani.TrostaniGame.main_phase | OPP.hold_answer(self, c)": (
        "WASTE_GUARD", "a pure answer with nothing to hit (§0z131, §0z134)"),
    "trostani.TrostaniGame.main_phase | plan is None": (
        "NOT_A_CHOICE", "Chord of Calling / Green Sun's Zenith: no X that "
        "pays and finds a target"),
    "trostani.TrostaniGame.main_phase | not self.worth_casting(c)": (
        "WASTE_GUARD", "Sundering Growth with no token to populate; "
        "Phyrexian Processor paying under 4 life"),
    "trostani.TrostaniGame.main_phase | _m is None": (
        "NOT_A_CHOICE", "no mode of the card pays"),
}


@dataclass(frozen=True)
class Site:
    kind: str           # "veto" or "reserve"
    module: str         # edhmc module name
    qualname: str       # function, Class.method for a method
    cond: str           # ast.unparse of the test
    line: int           # the `if`
    fire_line: int      # the line that executes when it fires: the
                        # `continue` for a veto, the `if` for a reserve
    loop_var: str       # the hand loop's target; "" for a reserve outside one

    @property
    def key(self) -> str:
        return f"{self.module}.{self.qualname} | {self.cond}"

    @property
    def where(self) -> str:
        return f"edhmc/{self.module}.py:{self.line}"


def engine_modules() -> list[str]:
    """Every module a deck's `simulate` lives in, from the registry."""
    from edhmc.registry import DECKS
    seen = []
    for spec in DECKS.values():
        if spec.engine not in seen:
            seen.append(spec.engine)
    return seen


def _functions(tree):
    """(qualname, FunctionDef) for module functions and class methods."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    yield f"{node.name}.{sub.name}", sub


def _own_nodes(fn):
    """Every node inside `fn` that is not inside a nested def or lambda."""
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.Lambda, ast.ClassDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def _is_hand(it) -> bool:
    return (isinstance(it, ast.Attribute) and it.attr == "hand"
            and isinstance(it.value, ast.Name)
            and it.value.id in ("g", "self"))


def _calls(fn, name) -> bool:
    for node in _own_nodes(fn):
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == name) or (
                    isinstance(f, ast.Attribute) and f.attr == name):
                return True
    return False


def _touches_options(body) -> bool:
    """A branch that builds an option (trostani's Chord dispatch appends one
    and continues) is not a veto: it reads the name `options`."""
    return any(isinstance(n, ast.Name) and n.id == "options"
               for st in body for n in ast.walk(st))


def _names_reserve(test) -> bool:
    return any(isinstance(n, ast.Compare) and any(
        isinstance(x, ast.Name) and x.id == "reserve"
        for x in [n.left, *n.comparators]) for n in ast.walk(test))


def scan_source(module: str, src: str) -> list[Site]:
    tree = ast.parse(src)
    sites: list[Site] = []
    for qual, fn in _functions(tree):
        picks = _calls(fn, PICKER)
        has_reserve = any(a.arg == "reserve" for a in fn.args.args
                          + fn.args.kwonlyargs)
        if not (picks or has_reserve):
            continue
        loops = [n for n in _own_nodes(fn)
                 if isinstance(n, ast.For) and _is_hand(n.iter)]
        loop_of = {}
        for loop in loops:
            for n in ast.walk(loop):
                loop_of.setdefault(id(n), loop)
        for node in _own_nodes(fn):
            if not isinstance(node, ast.If):
                continue
            loop = loop_of.get(id(node))
            var = (loop.target.id if loop is not None
                   and isinstance(loop.target, ast.Name) else "")
            if has_reserve and _names_reserve(node.test):
                sites.append(Site("reserve", module, qual,
                                  ast.unparse(node.test), node.lineno,
                                  node.lineno, var))
                continue
            if (picks and loop is not None and not node.orelse
                    and isinstance(node.body[-1], ast.Continue)
                    and not _touches_options(node.body)):
                cont = node.body[-1].lineno
                if ONE_LINE_GUARD and cont == node.lineno:
                    # One line: the trace cannot tell the test from the
                    # body, so the census could not count it. Refuse.
                    raise ValueError(
                        f"edhmc/{module}.py:{node.lineno}: a one-line "
                        "`if ...: continue` -- put the continue on its own "
                        "line so run_deferral_census can see it fire")
                sites.append(Site("veto", module, qual,
                                  ast.unparse(node.test), node.lineno, cont,
                                  var))
        if has_reserve:
            # A reserve read anywhere but an `if` test is a reserve this scan
            # cannot see fire. Refuse rather than go blind (§0z15).
            in_if = {id(n) for s in _own_nodes(fn) if isinstance(s, ast.If)
                     for n in ast.walk(s.test)}
            for n in _own_nodes(fn):
                if (isinstance(n, ast.Compare) and id(n) not in in_if
                        and _names_reserve(n)):
                    raise ValueError(
                        f"edhmc/{module}.py:{n.lineno}: `reserve` compared "
                        "outside an `if` test; tools/deferrals.py cannot "
                        "classify it")
    sites.sort(key=lambda s: s.line)
    return sites


def scan(modules=None) -> list[Site]:
    out = []
    for mod in modules or engine_modules():
        with open(os.path.join(ROOT, "edhmc", f"{mod}.py"),
                  encoding="utf-8") as fh:
            out.extend(scan_source(mod, fh.read()))
    keys = [s.key for s in out]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise ValueError(f"two sites share a key, so one classification "
                         f"would cover both: {dup}")
    return out


def check(sites=None, classes=None) -> list[str]:
    """Problems, empty when the inventory and `CLASSES` agree."""
    sites = scan() if sites is None else sites
    classes = CLASSES if classes is None else classes
    keys = {s.key for s in sites}
    probs = [f"UNCLASSIFIED {s.where}  {s.key}" for s in sites
             if s.key not in classes]
    if CHECK_STALE:
        probs += [f"NAMES NO SITE  {k}" for k in classes if k not in keys]
    probs += [f"UNKNOWN CATEGORY {cat!r}  {k}"
              for k, (cat, _) in classes.items() if cat not in CATEGORIES]
    return probs


def render(sites) -> str:
    lines = ["Deferral sites -- every place a main phase declines a spell it "
             "holds (tools/deferrals.py)", ""]
    for cat, desc in CATEGORIES.items():
        rows = [s for s in sites if CLASSES.get(s.key, ("?",))[0] == cat]
        if not rows:
            continue
        lines.append(f"{cat} ({len(rows)}): {desc}")
        for s in rows:
            lines.append(f"  {s.where:<26} {s.kind:<7} {s.module}.{s.qualname}")
            lines.append(f"      if {s.cond}")
            lines.append(f"      -- {CLASSES[s.key][1]}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sites = scan()
    probs = check(sites)
    if "--check" in argv:
        for p in probs:
            print(p)
        print(f"{len(sites)} sites, {len(probs)} problems")
        return 1 if probs else 0
    print(render(sites))
    for p in probs:
        print(p)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
