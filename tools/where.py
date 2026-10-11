#!/usr/bin/env python3
"""Find a function, outline a module, or print one function, without reading
the file.

    python -m tools.where engine                   # outline: every def, its lines
    python -m tools.where main_phase               # every def of that name
    python -m tools.where --show Game.make_tokens  # one def's source, numbered
    python -m tools.where --show main_phase --in karlov   # disambiguate by module
    python -m tools.where --card "Exquisite Blood" # every def naming a card
    python -m tools.where --card Sunbird --all     # ... in tools/, decks/, ledger/ too

WHY THIS EXISTS. The engine modules are the largest files in the repo --
`engine.py` and `azusa.py` are about 200 KB each, and `AzusaGame` alone is
three thousand lines -- and the session transcripts showed them read in
hundreds of `sed -n` ranges and greps per session, each one a guess at where
a function starts and ends. This answers the question directly: which file,
which lines, and the source of the one function and nothing around it.

DERIVED ON EVERY CALL from the syntax tree, never written to a file, so it
cannot go stale and there is nothing for `check_docs` to keep current (§0q:
a hand-maintained index is a claim, and claims rot). A def's range runs from
its first decorator to the last line of its body, so `--show` prints the
whole of it and the `Read offset=/limit=` it prints reads the same lines.

`--card` searches lines, comments included, case-insensitively, and groups
them by the innermost def around them (§0z25: behaviour attaches BY NAME at
least as often as by `script=`). BLIND TO, said out loud (§0z15): without
`--all` it reads only the top-level modules of `edhmc/` other than
`pending.py`. That leaves out the deck lists (`edhmc/decks/`), the ledger's
entries and prose (`edhmc/ledger/`, `edhmc/pending.py`) and `tools/`, whose
`ablation.py` holds the scripted/blind classification. It is also blind to a
card the code names by a SET or a tag rather than by its name.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass

ROOTS = ("edhmc", "tools")
# `--show` on a class longer than this prints its outline instead: the point
# is to read one method, and `AzusaGame` is three thousand lines.
SHOW_CLASS_MAX = 120


@dataclass(frozen=True)
class Def:
    path: str
    qualname: str       # Class.method, outer.inner
    kind: str           # "def" or "class"
    start: int          # first decorator line, 1-based
    end: int            # last body line, inclusive
    doc: str            # the docstring's first line, or ""
    depth: int


def _start(node: ast.AST) -> int:
    decos = getattr(node, "decorator_list", None)
    return min([d.lineno for d in decos] + [node.lineno]) if decos else node.lineno


def _end(node: ast.AST) -> int:
    return node.end_lineno


def _defs_in(path: str) -> list[Def]:
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    out: list[Def] = []

    def walk(node: ast.AST, prefix: str, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                q = f"{prefix}{child.name}"
                doc = (ast.get_docstring(child) or "").strip().split("\n")[0]
                kind = "class" if isinstance(child, ast.ClassDef) else "def"
                out.append(Def(path, q, kind, _start(child), _end(child),
                               doc, depth))
                walk(child, q + ".", depth + 1)
            else:
                walk(child, prefix, depth)

    walk(tree, "", 0)
    return sorted(out, key=lambda d: (d.start, d.depth))


def py_files(roots=ROOTS) -> list[str]:
    out = []
    for root in roots:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            out += [os.path.join(dirpath, f) for f in sorted(files)
                    if f.endswith(".py")]
    return out


def card_files(everything: bool) -> list[str]:
    if everything:
        return py_files()
    return [os.path.join("edhmc", f) for f in sorted(os.listdir("edhmc"))
            if f.endswith(".py") and f != "pending.py"]


def index(paths=None) -> list[Def]:
    return [d for p in (paths or py_files()) for d in _defs_in(p)]


def module_path(arg: str) -> str | None:
    """`engine`, `edhmc.engine`, `tools.ablation`, `edhmc/engine.py` -> a path."""
    cands = [arg, arg.replace(".", os.sep) + ".py"]
    cands += [os.path.join(r, arg + ".py") for r in ROOTS]
    for c in cands:
        if c.endswith(".py") and os.path.isfile(c):
            return c
    return None


def lookup(name: str, defs: list[Def], within: str = "") -> list[Def]:
    """Exact qualname or exact last component (so `main_phase` finds the
    module functions AND `AzusaGame.main_phase`), else a case-insensitive
    substring of the qualname. `within` keeps defs whose path contains it."""
    defs = [d for d in defs if within in d.path]
    for match in (lambda d: name in (d.qualname, d.qualname.rsplit(".", 1)[-1]),
                  lambda d: name.lower() in d.qualname.lower()):
        hits = [d for d in defs if match(d)]
        if hits:
            return hits
    return []


def pick(hits: list[Def]) -> Def | None:
    """The one def `--show` prints, or None when the name is ambiguous or
    unknown: a guess between two engines' `main_phase` is a wrong answer."""
    return hits[0] if len(hits) == 1 else None


def fmt(d: Def, path: bool = True, doc: int = 70) -> str:
    where = f"{d.path}:" if path else ""
    tail = f"  -- {d.doc[:doc]}" if d.doc and doc else ""
    return (f"{where}{d.start}-{d.end}  {'  ' * d.depth}"
            f"{d.qualname}{' (class)' if d.kind == 'class' else ''}{tail}")


def outline(path: str, under: str = "") -> list[str]:
    defs = _defs_in(path)
    if under:
        defs = [d for d in defs if d.qualname.startswith(under + ".")]
    return [fmt(d, path=False) for d in defs]


def show(d: Def) -> str:
    with open(d.path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    body = "\n".join(f"{n:>6}  {lines[n - 1]}" for n in range(d.start, d.end + 1))
    return (f"{d.path}:{d.start}-{d.end}  {d.qualname}   "
            f"(Read offset={d.start} limit={d.end - d.start + 1})\n{body}")


def enclosing(defs: list[Def], line: int) -> str:
    inner = [d for d in defs if d.start <= line <= d.end]
    return max(inner, key=lambda d: d.depth).qualname if inner else "<module>"


def card_hits(name: str, everything: bool = False) -> dict[tuple[str, str], list[int]]:
    """{(path, enclosing qualname): [line numbers naming the card]}."""
    rx = re.compile(re.escape(name), re.I)
    out: dict[tuple[str, str], list[int]] = {}
    for path in card_files(everything):
        defs = _defs_in(path)
        with open(path, encoding="utf-8") as fh:
            for n, text in enumerate(fh, 1):
                if rx.search(text):
                    out.setdefault((path, enclosing(defs, n)), []).append(n)
    return out


def _opt(argv: list[str], flag: str) -> str:
    if flag in argv:
        i = argv.index(flag)
        val = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
        return val
    return ""


def main(argv: list[str]) -> int:
    argv = list(argv)
    if not argv:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    everything = "--all" in argv
    if everything:
        argv.remove("--all")
    within = _opt(argv, "--in")

    card = _opt(argv, "--card")
    if card:
        hits = card_hits(card, everything)
        if not hits:
            print(f"no line names {card!r} in "
                  + ("edhmc/ and tools/" if everything else
                     "the edhmc/ engine modules (try --all)"))
            return 1
        for (path, q), lines in hits.items():
            print(f"{path}  {q}  lines {', '.join(map(str, lines))}")
        return 0

    target = _opt(argv, "--show")
    if target:
        hits = lookup(target, index(), within)
        d = pick(hits)
        if d is None:
            print(f"--show {target!r}: "
                  + (f"{len(hits)} matches; name one with Class.method or --in MODULE"
                     if hits else "no such def"))
            for d in hits:
                print("  " + fmt(d, doc=0))
            return 1
        if d.kind == "class" and d.end - d.start + 1 > SHOW_CLASS_MAX:
            print(f"{fmt(d)}\n{d.end - d.start + 1} lines -- its methods; "
                  f"--show {d.qualname}.NAME for one:")
            print("\n".join(outline(d.path, under=d.qualname)))
            return 0
        print(show(d))
        return 0

    arg = argv[0]
    path = module_path(arg)
    if path and not within:
        print(f"{path}  ({sum(1 for _ in open(path, encoding='utf-8'))} lines)")
        print("\n".join(outline(path)))
        return 0
    hits = lookup(arg, index(), within)
    if not hits:
        print(f"no def matches {arg!r}")
        return 1
    print("\n".join(fmt(d) for d in hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
