#!/usr/bin/env python3
"""`tools.where` finds every def, and its ranges are the defs' real lines.

    python -m tests.test_where
    python -m tests.test_where --mutate   # 7 mutations, exact sets

`tools/where.py` exists so a session reads one function instead of a 200 KB
module in guessed `sed -n` ranges. That only saves anything if a range is
the WHOLE def and nothing else, and if a def the index misses does not
exist as far as a session can tell. Every case checks the tool against the
source TEXT, not against the syntax tree the tool itself reads.

CASES
  A every `def`/`class` line in edhmc/*.py is indexed: the count of lines
    matching `^\\s*(async )?(def|class) NAME` equals the index's count
  B every range ENDS on its def's last line: the next line after it that is
    neither blank nor a comment is indented no deeper than the def, or is EOF
  C every decorated def's range STARTS on its first decorator: the start
    line begins with `@` and the line above it does not
  D `--show main_phase` is refused (several modules define it), and
    `--show main_phase --in karlov` prints karlov's
  E `--card "Exquisite Blood"` reports exactly the lines a case-insensitive
    grep finds in the same files
  F `--show AzusaGame` prints an outline under a tenth of the class's bytes
  G `main_phase` finds engine's module function AND `AzusaGame.main_phase`
    (an exact top-level match once hid every method of that name)

MUTATIONS, WRITTEN BEFORE THE RUN, exact sets:
  ranges drop decorators                    -> C
  nested defs are not indexed               -> A
  ranges end one line early                 -> B
  an ambiguous --show picks the first match -> D
  --card reports one line per def           -> E
  --show prints a long class whole          -> F
  lookup stops at an exact qualname         -> G

UNMUTATED (§0z15): nothing here checks the docstring line an outline row
prints, or `module_path`'s spellings beyond the ones D and F use.
"""
import contextlib
import io
import os
import re
import sys

import tools.where as W

MUTATE = "--mutate" in sys.argv
PASS, FAIL = [], []
DEF_LINE = re.compile(r"^(\s*)(?:async\s+)?(?:def|class)\s+\w+")
ENGINES = [os.path.join("edhmc", f) for f in sorted(os.listdir("edhmc"))
           if f.endswith(".py")]


def check(label, got, want):
    ok = got == want
    (PASS if ok else FAIL).append(label.split(" ")[0])
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"   got {got!r}, want {want!r}"))


def run(*argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = W.main(list(argv))
    return rc, buf.getvalue()


def lines_of(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def def_line_count(path):
    """`def`/`class` lines outside string literals: a line inside a
    triple-quoted string is skipped by tracking the quote parity."""
    n, in_str = 0, False
    for text in lines_of(path):
        if not in_str and DEF_LINE.match(text):
            n += 1
        if (text.count('"""') + text.count("'''")) % 2:
            in_str = not in_str
    return n


def run_cases():
    global PASS, FAIL
    PASS, FAIL = [], []
    defs = {p: W._defs_in(p) for p in ENGINES}

    short = [p for p in ENGINES if def_line_count(p) != len(defs[p])]
    check("A every def/class line in edhmc/ is indexed", short, [])

    overrun = []
    for p, ds in defs.items():
        src = lines_of(p)
        for d in ds:
            first = next(i for i in range(d.start, d.end + 1)
                         if DEF_LINE.match(src[i - 1]))
            indent = len(DEF_LINE.match(src[first - 1]).group(1))
            nxt = next((t for t in src[d.end:]
                        if t.strip() and not t.strip().startswith("#")), None)
            if nxt is not None and len(nxt) - len(nxt.lstrip()) > indent:
                overrun.append(f"{p}:{d.qualname}")
    check("B every range ends on its def's last line", overrun[:3], [])

    bad_start = []
    for p, ds in defs.items():
        src = lines_of(p)
        for d in ds:
            line = src[d.start - 1].strip()
            above = src[d.start - 2].strip() if d.start > 1 else ""
            decorated = line.startswith("@")
            if not DEF_LINE.match(src[d.start - 1]) and not decorated:
                bad_start.append(f"{p}:{d.qualname}")
            elif above.startswith("@"):
                bad_start.append(f"{p}:{d.qualname}")
    check("C every range starts on its first decorator", bad_start[:3], [])

    rc_amb, _ = run("--show", "main_phase")
    rc_one, out = run("--show", "main_phase", "--in", "karlov")
    check("D an ambiguous --show is refused; --in picks one",
          (rc_amb, rc_one, out.startswith("edhmc/karlov.py:")), (1, 0, True))

    name = "Exquisite Blood"
    want = sorted((p, n) for p in W.card_files(False)
                  for n, t in enumerate(lines_of(p), 1)
                  if name.lower() in t.lower())
    got = sorted((p, n) for (p, _q), ns in W.card_hits(name).items()
                 for n in ns)
    check("E --card reports exactly the grep's lines", got == want, True)

    azusa = next(d for d in defs[os.path.join("edhmc", "azusa.py")]
                 if d.qualname == "AzusaGame")
    cls_bytes = len("\n".join(lines_of(azusa.path)[azusa.start - 1:azusa.end]))
    _rc, out = run("--show", "AzusaGame")
    check("F --show on a long class prints an outline",
          len(out) * 10 < cls_bytes, True)

    found = {(d.path, d.qualname) for d in W.lookup("main_phase", W.index())}
    check("G main_phase finds the function and the method",
          {(os.path.join("edhmc", "engine.py"), "main_phase"),
           (os.path.join("edhmc", "azusa.py"), "AzusaGame.main_phase")}
          <= found, True)
    return set(FAIL)


def main():
    if not MUTATE:
        print("tools.where\n")
        run_cases()
        print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
        return 1 if FAIL else 0

    print("MUTATION RUN -- exact sets\n")
    real = {k: getattr(W, k) for k in
            ("_start", "_end", "_defs_in", "pick", "card_hits",
             "SHOW_CLASS_MAX", "lookup")}

    def flat_defs(path):
        ds = real["_defs_in"](path)
        funcs = {d.qualname for d in ds if d.kind == "def"}
        return [d for d in ds
                if not any(d.qualname.startswith(q + ".") for q in funcs)]

    def one_line_each(name, everything=False):
        return {k: v[:1] for k, v in real["card_hits"](name, everything).items()}

    def exact_first(name, defs, within=""):
        defs = [d for d in defs if within in d.path]
        for match in (lambda d: d.qualname == name,
                      lambda d: d.qualname.rsplit(".", 1)[-1] == name):
            hits = [d for d in defs if match(d)]
            if hits:
                return hits
        return real["lookup"](name, defs, within)

    muts = {
        "ranges drop decorators": ({"C"}, "_start", lambda n: n.lineno),
        "nested defs are not indexed": ({"A"}, "_defs_in", flat_defs),
        "ranges end one line early":
            ({"B"}, "_end", lambda n: n.end_lineno - 1),
        "an ambiguous --show picks the first match":
            ({"D"}, "pick", lambda hits: hits[0] if hits else None),
        "--card reports one line per def": ({"E"}, "card_hits", one_line_each),
        "--show prints a long class whole":
            ({"F"}, "SHOW_CLASS_MAX", 10 ** 9),
        "lookup stops at an exact qualname": ({"G"}, "lookup", exact_first),
    }
    bad = 0
    for label, (want, name, val) in muts.items():
        print(f"-- {label}")
        setattr(W, name, val)
        try:
            broke = run_cases()
        finally:
            setattr(W, name, real[name])
        ok = broke == want
        bad += (not ok)
        print(f"   broke {sorted(broke) or 'nothing'}  expected "
              f"{sorted(want)}  {'OK' if ok else '!!! UNEXPECTED'}\n")
    print(f"{len(muts) - bad} passed, {bad} failed "
          f"({len(muts)} mutations, exact sets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
