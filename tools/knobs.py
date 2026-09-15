#!/usr/bin/env python3
"""Derive the registry of simulation knobs from the engines that read them.

WHY THIS EXISTS. `CLAUDE.md` carries a standing rule -- "say the knob out loud
when a card's evaluation swings on one" -- and that rule was unfollowable,
because nothing in the repo could enumerate the knobs. There are 107 of them,
read through `cfg.get(...)` in seven engine files, and when this was first
counted THIRTY-SIX of them appeared in no `.md` file at all. A rule you cannot
mechanically check is a wish.

This is `check_scripted_coverage()` pointed at configuration instead of at
cards: the engine already NAMES every knob, so the list is DERIVED from the
engine rather than typed out beside it. §0q is the standing finding that says a
hand-maintained name set rots; a hand-maintained knob list would have been the
fifth instance.

THREE THINGS IT REPORTS THAT A GREP DOES NOT.

  1. CONFLICTING DEFAULTS. A knob read in two places with two different
     defaults is the §0u shape -- the same rule implemented twice, implemented
     two different ways -- and it is silent, because each call site looks
     correct on its own. These are printed first and `--check` fails on them.
  2. UNDOCUMENTED knobs: the name appears in no `.md`. That is not an error
     (most knobs are ordinary internals) but it is the set the "say the knob
     out loud" rule cannot currently be applied to.
  3. UNSWEPT knobs: the name appears nowhere outside `edhmc/`, so no
     diagnostic, test or tool has ever set it. A knob nobody has ever moved is
     a default nobody has ever measured -- `altar_keep` sat there for the life
     of the project until §0z20 swept it 6 -> 0 and found it was not
     load-bearing, which is the result nobody would have believed unmeasured.

WHAT THE `§` COLUMN IS AND IS NOT. It is the nearest section id cited in the
source ABOVE the call site, within the enclosing function. That is PROXIMITY,
not provenance: it is a good pointer and it is not a claim that the knob was
introduced by that finding. Read it as "start here", never as a citation.

    python -m tools.knobs            # print the registry
    python -m tools.knobs --write    # regenerate docs/KNOBS.md
    python -m tools.knobs --check    # exit 1 if docs/KNOBS.md is out of date
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys

OUT = os.path.join("docs", "KNOBS.md")
ENGINE_DIR = "edhmc"
SECTION = re.compile(r"§[0-9][0-9a-z]*")

# Where a knob may be SET rather than read. Used only for the "swept" column.
CALLER_DIRS = ("tools", "diagnostics", "tests")

# A knob read with two different defaults is normally the §0u drift shape and
# `--check` fails on it. An entry here says the split is KNOWN AND DELIBERATE,
# and the value is the reason -- which is the whole point: a check that cries
# wolf is worse than no check (`cache_manifest.py` says the same thing about
# fingerprints), and the way to keep it believable is to make the exceptions
# cost a written justification rather than a silent skip. §0z15's rule applied
# to this checker: when you write an exemption, write down what it is blind to.
ACKNOWLEDGED = {
    "turns": (
        "DORMANT, VERIFIED 2026-09-15. Four engines default it to 20 "
        "(azusa, karlov, shilgengar, tivit) and three to 10 (engine.py, "
        "lorehold, opponents.make_pod). No run consults any of them: "
        "`experiment.py`'s BASE cfg sets `turns: 10` unconditionally and "
        "`run_ab` only overrides it, so every harnessed simulation is handed "
        "an explicit value. The split is a LOADED GUN in §0z12's sense, not a "
        "live defect -- calling an engine's `simulate(cfg={})` directly, as a "
        "new diagnostic easily might, silently gives rendmaw and lorehold a "
        "ten-turn game and everything else a twenty-turn one, and `make_pod` "
        "would size the opponents' clock grid for the wrong horizon. Fixing "
        "it means picking one default, which is an engine decision with a "
        "measurement attached, not a documentation change."),
}


class Read:
    """One `cfg.get("name", default)` call site."""

    __slots__ = ("name", "default", "path", "line", "func", "section")

    def __init__(self, name, default, path, line, func, section):
        self.name = name
        self.default = default
        self.path = path
        self.line = line
        self.func = func
        self.section = section

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


def _is_cfg_get(node: ast.AST) -> bool:
    """Match a read of the config dict, in BOTH spellings the engines use.

    `g.cfg.get(...)` / `self.cfg.get(...)` -- an Attribute named `cfg` -- and
    bare `cfg.get(...)`, where `cfg` arrived as a function parameter. The first
    version of this matcher handled only the Attribute form and silently missed
    NINE knobs, `turns` and `archetype_weights` among them. A registry that
    drops entries is worse than no registry, because the whole point of it is
    that the absence of a name means the knob does not exist.
    """
    if not (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)):
        return False
    recv = node.func.value
    return ((isinstance(recv, ast.Attribute) and recv.attr == "cfg")
            or (isinstance(recv, ast.Name) and recv.id == "cfg"))


def _nearest_section(lines: list[str], call_line: int, func_line: int) -> str:
    """The last section id cited above the call, inside the enclosing function.

    PROXIMITY, NOT PROVENANCE -- see the module docstring. Bounded by the
    function's own `def` so a knob never inherits the id of the function above
    it, which is the way this kind of heuristic normally lies.
    """
    found = ""
    start = max(func_line - 1, 0)
    for raw in lines[start:call_line]:
        hits = SECTION.findall(raw)
        if hits:
            found = hits[-1]
    return found


def scan_file(path: str) -> list[Read]:
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    lines = src.splitlines()
    tree = ast.parse(src, filename=path)

    # Map each line to its enclosing function, innermost wins.
    owner: dict[int, tuple[str, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            for ln in range(node.lineno, end + 1):
                prev = owner.get(ln)
                if prev is None or node.lineno >= prev[1]:
                    owner[ln] = (node.name, node.lineno)

    out: list[Read] = []
    for node in ast.walk(tree):
        if not _is_cfg_get(node):
            continue
        name = node.args[0].value
        default = ast.unparse(node.args[1]) if len(node.args) > 1 else "<none>"
        func, func_line = owner.get(node.lineno, ("<module>", 1))
        out.append(Read(name, default, path, node.lineno, func,
                        _nearest_section(lines, node.lineno, func_line)))
    return out


def engine_sources() -> list[str]:
    found = []
    for root, _dirs, files in os.walk(ENGINE_DIR):
        for f in sorted(files):
            if f.endswith(".py"):
                found.append(os.path.join(root, f))
    return sorted(found)


def scan() -> dict[str, list[Read]]:
    reads: dict[str, list[Read]] = {}
    for path in engine_sources():
        for r in scan_file(path):
            reads.setdefault(r.name, []).append(r)
    for rs in reads.values():
        rs.sort(key=lambda r: (r.path, r.line))
    return dict(sorted(reads.items()))


def _text_of(paths) -> str:
    body = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                body.append(fh.read())
        except OSError:
            pass
    return "\n".join(body)


def _md_paths() -> list[str]:
    out = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f.endswith(".md") and os.path.join(root, f) != os.path.join(".", OUT):
                out.append(os.path.join(root, f))
    return sorted(out)


def _caller_paths() -> list[str]:
    out = []
    for d in CALLER_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in sorted(files):
                if f.endswith((".py", ".sh")):
                    out.append(os.path.join(root, f))
    return sorted(out)


def conflicts(reads: dict[str, list[Read]]) -> dict[str, list[Read]]:
    """Knobs read with more than one default. See the docstring: this is §0u."""
    bad = {}
    for name, rs in reads.items():
        seen = {r.default for r in rs if r.default != "<none>"}
        if len(seen) > 1:
            bad[name] = rs
    return bad


def head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def render() -> str:
    reads = scan()
    docs_text = _text_of(_md_paths())
    calls_text = _text_of(_caller_paths())
    bad = conflicts(reads)

    undocumented = [n for n in reads if n not in docs_text]
    unswept = [n for n in reads if n not in calls_text]

    L: list[str] = []
    w = L.append
    w("# Simulation knobs")
    w("")
    w("GENERATED by `python -m tools.knobs --write`. **Do not edit by hand** —")
    w("every row is derived from a `cfg.get(...)` call site in `edhmc/`, so a")
    w("knob cannot be added to the engines without appearing here, and cannot")
    w("be renamed without this file changing. That is §0q's rule (a")
    w("hand-maintained name set is a claim, and claims rot) applied to")
    w("configuration.")
    w("")
    w(f"Derived at `{head()}` from {len(engine_sources())} engine sources.")
    w("")
    w(f"**{len(reads)} knobs, {sum(len(v) for v in reads.values())} call sites.**")
    w("")
    w("`CLAUDE.md`'s standing rule is to **say the knob out loud** when a")
    w("card's evaluation swings on one — and to say it when it does NOT, which")
    w("is the more useful result. This file is the list that rule ranges over.")
    w("")
    w("**The `§` column is PROXIMITY, not provenance.** It is the nearest")
    w("section id cited above the call site inside the same function. Read it")
    w("as \"start here\", never as \"this finding introduced this knob\".")
    w("")

    w("## Knobs read with more than one default")
    w("")
    if bad:
        w("**These are defects unless a reason is attached.** A knob read in two")
        w("places with two different defaults is §0u — the same rule implemented")
        w("twice, implemented two different ways — and it is silent, because each")
        w("call site is correct on its own. `--check` fails on any entry here")
        w("that is not in `tools/knobs.py`'s `ACKNOWLEDGED`, and an entry there")
        w("costs a written justification.")
        w("")
        for name, rs in sorted(bad.items()):
            note = ACKNOWLEDGED.get(name)
            w(f"- **`{name}`**" + ("  — *acknowledged*" if note else ""))
            for r in rs:
                w(f"  - `{r.default}` at `{r.where}` in `{r.func}()`")
            if note:
                w("")
                w(f"  {note}")
            w("")
    else:
        w("None. Every knob has one default at every site it is read.")
        w("")

    w("## Every knob")
    w("")
    w("`sites` is the number of places the engines read it. A knob read in")
    w("several places is not suspicious on its own — `charge_life_costs` is")
    w("deliberately read at every payment site — but it is where a drift would")
    w("show up first.")
    w("")
    w("| knob | default | sites | first read at | § nearby | in docs | swept |")
    w("|---|---|---|---|---|---|---|")
    for name, rs in reads.items():
        first = rs[0]
        secs = sorted({r.section for r in rs if r.section})
        sec = secs[0] if secs else ""
        in_docs = "yes" if name in docs_text else "**no**"
        swept = "yes" if name in calls_text else "**never**"
        default = "**conflicts**" if name in bad else f"`{first.default}`"
        w(f"| `{name}` | {default} | {len(rs)} | `{first.where}` | {sec} | "
          f"{in_docs} | {swept} |")
    w("")

    w("## The knobs no document mentions")
    w("")
    w(f"**{len(undocumented)} of {len(reads)}.** Not an error — most knobs are")
    w("ordinary internals — but this is exactly the set the \"say the knob out")
    w("loud\" rule cannot currently be applied to, because nobody reading the")
    w("docs knows they exist.")
    w("")
    w(", ".join(f"`{n}`" for n in undocumented) if undocumented else "None.")
    w("")

    w("## The knobs nothing has ever set")
    w("")
    w(f"**{len(unswept)} of {len(reads)}.** The name appears nowhere in")
    w("`tools/`, `diagnostics/` or `tests/`, so no run has ever moved it off")
    w("its default. **A knob nobody has ever moved is a default nobody has")
    w("ever measured.** `altar_keep` sat here for the life of the project;")
    w("§0z20 swept it 6 → 0, found it was not load-bearing, and that is the")
    w("result nobody would have believed unmeasured.")
    w("")
    w(", ".join(f"`{n}`" for n in unswept) if unswept else "None.")
    w("")
    return "\n".join(L) + "\n"


def main() -> int:
    body = render()
    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"wrote {OUT}")
        return 0
    if "--check" in sys.argv:
        try:
            with open(OUT, "r", encoding="utf-8") as fh:
                have = fh.read()
        except OSError:
            print(f"MISSING {OUT} -- run `python -m tools.knobs --write`")
            return 1
        if have != body:
            print(f"STALE {OUT} -- run `python -m tools.knobs --write`")
            return 1
        unknown = sorted(set(conflicts(scan())) - set(ACKNOWLEDGED))
        if unknown:
            print("CONFLICTING DEFAULTS, unacknowledged: " + ", ".join(unknown))
            print("Fix the split, or record it in tools/knobs.py ACKNOWLEDGED "
                  "with the reason it is deliberate.")
            return 1
        print(f"{OUT} is current")
        return 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
